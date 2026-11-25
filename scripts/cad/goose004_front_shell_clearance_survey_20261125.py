"""Survey full-yaw hip yoke vs body016_front clearance, height bands, and split-relief budgets."""
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


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ray_thickness(shape, pt: App.Vector, normal: App.Vector, span: float = 20.0) -> tuple[float | None, list[float]]:
    """Measure local solid thickness along `normal` starting from surface point `pt`."""
    line = Part.makeLine(pt - normal * span, pt + normal * span)
    sec = shape.section(line)
    ts = sorted({round((v.Point - pt).dot(normal), 6) for v in sec.Vertexes})
    intervals = []
    for a, b in zip(ts, ts[1:]):
        if b - a < 1e-4:
            continue
        mid = pt + normal * (0.5 * (a + b))
        if shape.isInside(mid, 1e-5, True):
            intervals.append((a, b, b - a))
    if not intervals:
        return None, ts
    # Pick interval touching 0
    best = min(intervals, key=lambda iv: min(abs(iv[0]), abs(iv[1])))
    return best[2], ts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shell = Part.read(str(FRONT_BREP))
    yokes = {
        "left": (1, Part.read(str(YOKE_LEFT)), YOKE_LEFT),
        "right": (-1, Part.read(str(YOKE_RIGHT)), YOKE_RIGHT),
    }

    # Scan full hip yaw range [-0.57, +0.57] rad at 0.015 rad (~0.86 deg) + exact ±0.1873242 rad
    yaws = sorted(set(
        [round(-0.57 + i * 0.015, 6) for i in range(77)]
        + [-0.57, -0.1873242, 0.0, 0.1873242, 0.57]
    ))

    results = {}
    for side, (sg, base_yoke, ypath) in yokes.items():
        axis_pt = App.Vector(-60.0, sg * 60.0, 351.675)
        axis_dir = App.Vector(0.0, 0.0, 1.0)
        rows = []
        for yaw in yaws:
            y = base_yoke.copy()
            if abs(yaw) > 0:
                y.rotate(axis_pt, axis_dir, math.degrees(yaw))
            dist, pts, _ = y.distToShape(shell)
            yp, sp = pts[0]
            # Transform witness point back to neutral yoke frame to see WHICH feature on the yoke hits!
            rel_v = yp - axis_pt
            c, s = math.cos(-yaw), math.sin(-yaw)
            yp_neutral = App.Vector(
                axis_pt.x + c * rel_v.x - s * rel_v.y,
                axis_pt.y + s * rel_v.x + c * rel_v.y,
                yp.z,
            )
            r_xy = math.hypot(yp_neutral.x - axis_pt.x, yp_neutral.y - axis_pt.y)
            ang_deg = math.degrees(math.atan2(yp_neutral.y - axis_pt.y, yp_neutral.x - axis_pt.x))
            n = sp - yp
            if n.Length > 1e-9:
                n.normalize()
                shell_thk, _ = ray_thickness(shell, sp, n, span=15.0)
                yoke_thk, _ = ray_thickness(y, yp, n * (-1.0), span=25.0)
            else:
                shell_thk, yoke_thk = None, None
            rows.append({
                "yaw_rad": yaw,
                "yaw_deg": round(math.degrees(yaw), 4),
                "gap_mm": round(dist, 6),
                "yoke_pt_world_mm": [round(yp.x, 4), round(yp.y, 4), round(yp.z, 4)],
                "yoke_pt_neutral_mm": [round(yp_neutral.x, 4), round(yp_neutral.y, 4), round(yp_neutral.z, 4)],
                "yoke_r_from_hy_mm": round(r_xy, 4),
                "yoke_theta_deg": round(ang_deg, 3),
                "shell_pt_world_mm": [round(sp.x, 4), round(sp.y, 4), round(sp.z, 4)],
                "shell_wall_mm": round(shell_thk, 4) if shell_thk is not None else None,
                "yoke_local_depth_mm": round(yoke_thk, 4) if yoke_thk is not None else None,
            })

        below_1p5 = [r for r in rows if r["gap_mm"] < 1.5]
        # Cluster height bands
        z_vals = sorted(r["yoke_pt_world_mm"][2] for r in below_1p5)
        bands = []
        for r in sorted(below_1p5, key=lambda x: x["yoke_pt_world_mm"][2]):
            z = r["yoke_pt_world_mm"][2]
            if not bands or z - bands[-1]["z_max"] > 10.0:
                bands.append({"z_min": z, "z_max": z, "count": 1, "min_gap": r["gap_mm"], "min_shell_wall": r["shell_wall_mm"], "rows": [r]})
            else:
                b = bands[-1]
                b["z_max"] = z
                b["count"] += 1
                b["min_gap"] = min(b["min_gap"], r["gap_mm"])
                if r["shell_wall_mm"] is not None:
                    b["min_shell_wall"] = min(b["min_shell_wall"], r["shell_wall_mm"]) if b["min_shell_wall"] is not None else r["shell_wall_mm"]
                b["rows"].append(r)

        band_summaries = []
        for idx, b in enumerate(bands):
            worst = min(b["rows"], key=lambda x: x["gap_mm"])
            band_summaries.append({
                "band_index": idx,
                "z_range_mm": [round(b["z_min"], 3), round(b["z_max"], 3)],
                "yaw_deg_range": [round(min(x["yaw_deg"] for x in b["rows"]), 2), round(max(x["yaw_deg"] for x in b["rows"]), 2)],
                "count_below_1p5mm": b["count"],
                "min_gap_mm": b["min_gap"],
                "worst_pose": worst,
                "min_shell_wall_mm": b["min_shell_wall"],
                "yoke_r_range_mm": [round(min(x["yoke_r_from_hy_mm"] for x in b["rows"]), 3), round(max(x["yoke_r_from_hy_mm"] for x in b["rows"]), 3)],
                "yoke_theta_deg_range": [round(min(x["yoke_theta_deg"] for x in b["rows"]), 2), round(max(x["yoke_theta_deg"] for x in b["rows"]), 2)],
            })
            print(
                f"[{side}] Band {idx}: z={band_summaries[-1]['z_range_mm']} mm, "
                f"n={b['count']}, min_gap={b['min_gap']:.4f} mm @ yaw={worst['yaw_deg']:.2f} deg, "
                f"shell_wall={worst['shell_wall_mm']} mm, yoke_depth={worst['yoke_local_depth_mm']} mm, "
                f"r_HY={worst['yoke_r_from_hy_mm']} mm, neutral={worst['yoke_pt_neutral_mm']}"
            )

        results[side] = {
            "yoke_path": str(ypath.relative_to(ROOT)),
            "yoke_sha256": sha256_file(ypath),
            "n_samples": len(rows),
            "n_below_1p5mm": len(below_1p5),
            "global_min_gap_mm": min(r["gap_mm"] for r in rows),
            "bands_below_1p5mm": band_summaries,
            "samples": rows,
        }

    # Also check ALL points on the yoke that come within 2.0 mm of the shell across yaw!
    summary = {
        "schema": "goose004_front_shell_clearance_survey/1",
        "front_shell_path": str(FRONT_BREP.relative_to(ROOT)),
        "front_shell_sha256": sha256_file(FRONT_BREP),
        "sides": results,
    }
    out_json = OUT / "front_shell_clearance_survey.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print("Wrote:", out_json)


if __name__ == "__main__":
    main()
