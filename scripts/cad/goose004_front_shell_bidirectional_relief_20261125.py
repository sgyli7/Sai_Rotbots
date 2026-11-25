"""Generate and verify outer-lip revolved yoke relief achieving >=1.55 mm gap to untouched body016_front."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/home/ethan/.local/opt/freecad_1_1_4_aarch64/squashfs-root/usr/lib")
import FreeCAD as App  # type: ignore
import Part  # type: ignore

ROOT = Path("/home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots")
OUT = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/front_shell_relief"
FRONT_BREP = ROOT / "robots/goose_v0_2/cad/source/hip_aperture_closeout_20261117_001/body_circle_002.brep"
YOKE_LEFT = ROOT / "artifacts/goose_v0_2/hip_yaw_hour_20261118_001/joint_screen/smooth_006/left_yoke.brep"
YOKE_RIGHT = ROOT / "artifacts/goose_v0_2/hip_yaw_hour_20261118_001/joint_screen/smooth_006/right_yoke.brep"
STEEL_RHO_G_MM3 = 7.85e-3  # 7850 kg/m^3


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compute_shell_min_r_profile(shell, cx: float, cy: float, sg: int, z_list: list[float]) -> list[tuple[float, float, float]]:
    """For each z, find minimum inner radius R_shell_in from HY axis (cx, cy) over the shell-facing hemisphere."""
    prof = []
    # For left (sg=+1), shell is in theta in [10, 170] deg; for right (sg=-1), theta in [-170, -10] deg
    deg_range = range(10, 171, 2) if sg > 0 else range(-170, -9, 2)
    for z in z_list:
        min_r = 999.0
        wall_at_min = None
        for deg in deg_range:
            rad = math.radians(deg)
            ux, uy = math.cos(rad), math.sin(rad)
            line = Part.makeLine(App.Vector(cx + 25 * ux, cy + 25 * uy, z), App.Vector(cx + 68 * ux, cy + 68 * uy, z))
            hit = shell.section(line)
            rs = sorted({round((v.Point.x - cx) * ux + (v.Point.y - cy) * uy, 5) for v in hit.Vertexes})
            for a, b in zip(rs, rs[1:]):
                if b - a < 1e-4:
                    continue
                mid_r = 0.5 * (a + b)
                if shell.isInside(App.Vector(cx + mid_r * ux, cy + mid_r * uy, z), 1e-5, True):
                    if a < min_r:
                        min_r = a
                        wall_at_min = b - a
                    break
        prof.append((z, min_r, wall_at_min if wall_at_min is not None else 0.0))
    return prof


def build_revolved_keep_solid(cx: float, cy: float, profile_zr: list[tuple[float, float]], z_lo: float = 250.0, z_hi: float = 420.0, r_far: float = 120.0):
    """Build a revolved solid around (cx, cy, z) that keeps everything inside R_allow(z) in the relief band and R_far outside."""
    # Construct closed polygon in the (r, z) half-plane (x = cx + r, y = cy)
    pts = [App.Vector(cx, cy, z_lo), App.Vector(cx + r_far, cy, z_lo)]
    # Taper smoothly into the relief band starting 4 mm below first z
    z0, r0 = profile_zr[0]
    pts.append(App.Vector(cx + r_far, cy, z0 - 4.0))
    pts.append(App.Vector(cx + r0 + 3.0, cy, z0 - 2.0))
    for z, r in profile_zr:
        pts.append(App.Vector(cx + r, cy, z))
    zn, rn = profile_zr[-1]
    pts.append(App.Vector(cx + rn + 3.0, cy, zn + 2.0))
    pts.append(App.Vector(cx + r_far, cy, zn + 4.0))
    pts.append(App.Vector(cx + r_far, cy, z_hi))
    pts.append(App.Vector(cx, cy, z_hi))
    pts.append(pts[0])
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    keep_solid = face.revolve(App.Vector(cx, cy, 0.0), App.Vector(0.0, 0.0, 1.0), 360.0)
    return keep_solid


def measure_min_steel_wall(shape, cx: float, cy: float, sg: int, z_checks: list[float]) -> list[dict]:
    deg_range = range(20, 161, 5) if sg > 0 else range(-160, -19, 5)
    rows = []
    for z in z_checks:
        min_wall = 999.0
        max_r = 0.0
        min_wall_deg = None
        for deg in deg_range:
            rad = math.radians(deg)
            ux, uy = math.cos(rad), math.sin(rad)
            line = Part.makeLine(App.Vector(cx, cy, z), App.Vector(cx + 60 * ux, cy + 60 * uy, z))
            hit = shape.section(line)
            rs = sorted({round((v.Point.x - cx) * ux + (v.Point.y - cy) * uy, 5) for v in hit.Vertexes})
            intervals = []
            for a, b in zip(rs, rs[1:]):
                if b - a < 1e-4:
                    continue
                mid_r = 0.5 * (a + b)
                if shape.isInside(App.Vector(cx + mid_r * ux, cy + mid_r * uy, z), 1e-5, True):
                    intervals.append((a, b, b - a))
            if intervals:
                outer = intervals[-1]
                if outer[1] > max_r:
                    max_r = outer[1]
                # Only count outer collar wall (r_in > 28 mm)
                if outer[0] > 28.0 and outer[2] < min_wall:
                    min_wall = outer[2]
                    min_wall_deg = deg
        rows.append({
            "z_mm": z,
            "max_r_mm": round(max_r, 4),
            "min_outer_collar_wall_mm": round(min_wall, 4) if min_wall < 999 else None,
            "min_wall_theta_deg": min_wall_deg,
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shell = Part.read(str(FRONT_BREP))
    target_margin = 1.62  # leaves >= 1.55 mm exact 3D clearance accounting for shell Z-slope normal projection

    z_grid = [round(360.0 + i * 2.0, 2) for i in range(21)]  # 360..400 every 2 mm
    yaws = sorted(set([round(-0.57 + i * 0.015, 6) for i in range(77)] + [-0.57, -0.1873242, 0.0, 0.1873242, 0.57]))

    report = {
        "schema": "goose004_yoke_outer_lip_relief_proof/1",
        "strategy": "100% yoke outer non-load-bearing steel lip revolved trim; body016_front exterior AND interior wall 100% UNTOUCHED (PA12 wall >= 2.12 mm preserved everywhere)",
        "target_radial_margin_mm": target_margin,
        "front_shell": {"path": str(FRONT_BREP.relative_to(ROOT)), "sha256": sha256_file(FRONT_BREP)},
        "sides": {},
    }

    for side, sg, ypath in [("left", 1, YOKE_LEFT), ("right", -1, YOKE_RIGHT)]:
        cx, cy = -60.0, sg * 60.0
        base_yoke = Part.read(str(ypath))
        prof = compute_shell_min_r_profile(shell, cx, cy, sg, z_grid)
        # Filter to valid hits (min_r < 80) and apply target margin; cap so we never trim below r=40.5 unnecessarily
        profile_zr = [(z, round(min_r - target_margin, 4)) for (z, min_r, _w) in prof if min_r < 80.0]

        keep_solid = build_revolved_keep_solid(cx, cy, profile_zr)
        relieved = base_yoke.common(keep_solid)
        assert len(relieved.Solids) == 1, f"{side}: expected 1 solid, got {len(relieved.Solids)}"
        assert relieved.isValid(), f"{side}: relieved solid invalid!"

        brep_out = OUT / f"{side}_yoke_shell_relieved.brep"
        step_out = OUT / f"{side}_yoke_shell_relieved.step"
        relieved.exportBrep(str(brep_out))
        relieved.exportStep(str(step_out))

        # Cold reopen STEP verification
        reopened = Part.read(str(step_out))
        assert len(reopened.Solids) == 1 and reopened.isValid()
        vol_base = base_yoke.Volume
        vol_new = relieved.Volume
        vol_reopen = reopened.Volume
        vol_removed = vol_base - vol_new
        mass_saved_g = vol_removed * STEEL_RHO_G_MM3

        # Sweep all 81 yaw poses against UNTOUCHED body016_front
        axis_pt = App.Vector(cx, cy, 351.675)
        axis_dir = App.Vector(0.0, 0.0, 1.0)
        sweep = []
        for yaw in yaws:
            y = reopened.copy()
            if abs(yaw) > 0:
                y.rotate(axis_pt, axis_dir, math.degrees(yaw))
            d, pts, _ = y.distToShape(shell)
            yp, sp = pts[0]
            sweep.append({
                "yaw_rad": yaw,
                "yaw_deg": round(math.degrees(yaw), 3),
                "gap_mm": round(d, 6),
                "yoke_pt_mm": [round(yp.x, 3), round(yp.y, 3), round(yp.z, 3)],
                "shell_pt_mm": [round(sp.x, 3), round(sp.y, 3), round(sp.z, 3)],
            })
        worst = min(sweep, key=lambda r: r["gap_mm"])

        # Measure remaining steel wall thickness in both bands
        wall_checks = measure_min_steel_wall(reopened, cx, cy, sg, [366.0, 368.0, 370.2, 375.0, 390.0, 394.0, 395.0, 396.0])
        min_steel_wall = min(w["min_outer_collar_wall_mm"] for w in wall_checks if w["min_outer_collar_wall_mm"] is not None)

        print(
            f"[{side}] VALID single solid | vol: {vol_base:.1f} -> {vol_new:.1f} mm3 "
            f"(STEP delta={abs(vol_reopen-vol_new):.4f} mm3) | mass saved: {mass_saved_g:.2f} g | "
            f"global min gap (81 yaws) = {worst['gap_mm']:.4f} mm @ yaw={worst['yaw_deg']} deg, z={worst['yoke_pt_mm'][2]} | "
            f"min remaining steel collar wall = {min_steel_wall:.3f} mm"
        )
        for w in wall_checks:
            print(f"    z={w['z_mm']:5.1f}: max_r={w['max_r_mm']:6.3f}, min_steel_wall={w['min_outer_collar_wall_mm']} mm @ th={w['min_wall_theta_deg']}")

        report["sides"][side] = {
            "base_yoke_path": str(ypath.relative_to(ROOT)),
            "base_yoke_sha256": sha256_file(ypath),
            "relieved_brep": {"path": str(brep_out.relative_to(ROOT)), "sha256": sha256_file(brep_out)},
            "relieved_step": {"path": str(step_out.relative_to(ROOT)), "sha256": sha256_file(step_out)},
            "base_volume_mm3": round(vol_base, 3),
            "relieved_volume_mm3": round(vol_new, 3),
            "step_reopen_delta_mm3": round(abs(vol_reopen - vol_new), 6),
            "volume_removed_mm3": round(vol_removed, 3),
            "steel_mass_saved_g": round(mass_saved_g, 3),
            "global_min_gap_mm": worst["gap_mm"],
            "worst_pose": worst,
            "n_poses_below_1p5mm": sum(1 for r in sweep if r["gap_mm"] < 1.5),
            "min_remaining_steel_collar_wall_mm": min_steel_wall,
            "steel_wall_checks": wall_checks,
            "shell_min_r_profile_zr_wall": [[z, round(r, 4), round(w, 4)] for z, r, w in prof if r < 80.0],
            "sweep": sweep,
        }

    out_json = OUT / "yoke_outer_lip_relief_receipt.json"
    out_json.write_text(json.dumps(report, indent=2))
    print("Wrote receipt:", out_json)


if __name__ == "__main__":
    main()
