"""Exact polar geometry & swept clearance map of smooth_006 yoke vs body016_front (z=360..405 mm)."""
from __future__ import annotations

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


def section_polar_stats(shape, cx: float, cy: float, z: float) -> dict:
    """Slice shape at plane z and report radial bounds & outer/inner radii by angle."""
    plane = Part.makePlane(400, 400, App.Vector(-250, -200, z), App.Vector(0, 0, 1))
    sec = shape.section(plane)
    pts = []
    for e in sec.Edges:
        for p in e.discretize(Deflection=0.05):
            r = math.hypot(p.x - cx, p.y - cy)
            th = math.degrees(math.atan2(p.y - cy, p.x - cx))
            pts.append((r, th, p.x, p.y))
    if not pts:
        return {"z": z, "empty": True}
    # Bin outer region theta in [45, 135] deg (facing +Y / body016_front)
    outer_pts = [p for p in pts if 20.0 <= p[1] <= 160.0]
    # Also find inner bore / holes by ray casting radially from (cx, cy, z)
    rays = []
    for deg in range(0, 181, 10):
        rad = math.radians(deg)
        ux, uy = math.cos(rad), math.sin(rad)
        line = Part.makeLine(App.Vector(cx, cy, z), App.Vector(cx + 60 * ux, cy + 60 * uy, z))
        hit = shape.section(line)
        rs = sorted({round((v.Point.x - cx) * ux + (v.Point.y - cy) * uy, 4) for v in hit.Vertexes})
        intervals = []
        for a, b in zip(rs, rs[1:]):
            if b - a < 1e-4:
                continue
            mid_r = 0.5 * (a + b)
            if shape.isInside(App.Vector(cx + mid_r * ux, cy + mid_r * uy, z), 1e-5, True):
                intervals.append([round(a, 3), round(b, 3), round(b - a, 3)])
        if intervals:
            rays.append({"theta_deg": deg, "solid_r_intervals_mm": intervals})
    return {
        "z": z,
        "global_r_min": round(min(p[0] for p in pts), 3),
        "global_r_max": round(max(p[0] for p in pts), 3),
        "outer_20_160_r_max": round(max(p[0] for p in outer_pts), 3) if outer_pts else None,
        "rays": rays,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    yoke = Part.read(str(YOKE_LEFT))
    shell = Part.read(str(FRONT_BREP))
    cx, cy = -60.0, 60.0

    print("=== YOKE BOUNDING BOX ===")
    bb = yoke.BoundBox
    print(f"X=[{bb.XMin:.2f}, {bb.XMax:.2f}], Y=[{bb.YMin:.2f}, {bb.YMax:.2f}], Z=[{bb.ZMin:.2f}, {bb.ZMax:.2f}], vol={yoke.Volume:.1f} mm3")

    slices = {}
    for z in [365.0, 368.0, 370.2, 371.5, 375.0, 380.0, 385.0, 390.0, 394.0, 395.0, 398.0]:
        s = section_polar_stats(yoke, cx, cy, z)
        slices[str(z)] = s
        if not s.get("empty"):
            # Print compact summary of outermost solid interval across theta 40..140 deg
            outer_rays = [r for r in s["rays"] if 40 <= r["theta_deg"] <= 140]
            max_r = max((r["solid_r_intervals_mm"][-1][1] for r in outer_rays), default=0)
            min_thk = min((r["solid_r_intervals_mm"][-1][2] for r in outer_rays), default=0)
            sample_90 = [r["solid_r_intervals_mm"] for r in s["rays"] if r["theta_deg"] in (60, 80, 90, 100)]
            print(f"z={z:5.1f}: r_max(40..140)={max_r:6.3f}, min_outer_wall={min_thk:5.3f}, samples(60/80/90/100)={sample_90}")

    # Now compute the EXACT radial clearance of shell inner wall from HY axis (-60, 60) over z=360..402
    # Since the yoke rotates around (-60, 60, z) by yaw in [-0.57, +0.57] rad, ANY point on the yoke at (r, theta_0, z)
    # sweeps the circular arc theta in [theta_0 - 32.66 deg, theta_0 + 32.66 deg]!
    # So the EXACT shell inner radius R_shell_in(theta_world, z) tells us the exact max allowable yoke radius!
    print("\n=== SHELL INNER RADIUS & WALL THICKNESS FROM LEFT HY AXIS (-60, 60) ===")
    shell_map = []
    for z in [366.0, 368.0, 370.2, 371.2, 373.0, 376.0, 380.0, 385.0, 390.0, 392.0, 394.2, 396.0, 398.0]:
        row = {"z": z, "angles": []}
        min_rin = 999.0
        min_rin_deg = None
        min_wall = 999.0
        for deg in range(10, 171, 2):
            rad = math.radians(deg)
            ux, uy = math.cos(rad), math.sin(rad)
            line = Part.makeLine(App.Vector(cx + 30 * ux, cy + 30 * uy, z), App.Vector(cx + 65 * ux, cy + 65 * uy, z))
            hit = shell.section(line)
            rs = sorted({round((v.Point.x - cx) * ux + (v.Point.y - cy) * uy, 4) for v in hit.Vertexes})
            intervals = []
            for a, b in zip(rs, rs[1:]):
                if b - a < 1e-4:
                    continue
                mid_r = 0.5 * (a + b)
                if shell.isInside(App.Vector(cx + mid_r * ux, cy + mid_r * uy, z), 1e-5, True):
                    intervals.append([round(a, 4), round(b, 4), round(b - a, 4)])
            if intervals:
                rin, rout, w = intervals[0]
                row["angles"].append({"deg": deg, "r_in": rin, "r_out": rout, "wall_rad_mm": w})
                if rin < min_rin:
                    min_rin = rin
                    min_rin_deg = deg
                    min_wall = w
        shell_map.append(row)
        if min_rin < 999:
            print(f"  z={z:5.1f}: min_R_shell_in={min_rin:6.3f} mm @ theta={min_rin_deg:3d} deg (radial_wall={min_wall:.3f} mm, n_angles={len(row['angles'])})")
        else:
            print(f"  z={z:5.1f}: NO SHELL HIT in r=[30..65]")

    (OUT / "yoke_and_shell_polar_sections.json").write_text(
        json.dumps({"yoke_slices": slices, "shell_polar_map": shell_map}, indent=2)
    )
    print("Wrote:", OUT / "yoke_and_shell_polar_sections.json")


if __name__ == "__main__":
    main()
