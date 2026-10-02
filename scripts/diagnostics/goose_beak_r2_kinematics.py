#!/usr/bin/env python3
"""Recompute the ideal Goose R2 parallelogram. No hardware or CAD validation."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

def evaluate(length_mm: float, height_mm: float, closed_deg: float,
             open_deg: float, ratio: float, target_mm: float) -> dict:
    if min(length_mm, height_mm, ratio) <= 0:
        raise ValueError("Link lengths and ratio must be positive.")
    if not -90 < open_deg < closed_deg < 90:
        raise ValueError("This calculation uses one non-singular branch: -90 < open < closed < 90.")
    if target_mm < 0:
        raise ValueError("Target gap must be nonnegative.")
    rad = math.radians
    travel = length_mm * (math.sin(rad(closed_deg))-math.sin(rad(open_deg)))
    if target_mm > travel + 1e-9:
        raise ValueError("Target exceeds reference travel.")
    q = math.degrees(math.asin(math.sin(rad(closed_deg))-target_mm/length_mm))
    closest = min(max(0.0, open_deg), closed_deg)
    result = {
        "L_mm": length_mm, "h_mm": height_mm, "q_closed_deg": closed_deg,
        "q_open_reference_deg": open_deg, "ratio": ratio,
        "reference_travel_mm": travel,
        "max_forward_sweep_mm": length_mm*(math.cos(rad(closest))-math.cos(rad(closed_deg))),
        "target_gap_mm": target_mm, "q_at_target_gap_deg": q,
        "forward_shift_at_target_mm": length_mm*(math.cos(rad(q))-math.cos(rad(closed_deg))),
        "servo_travel_for_30mm_deg": ratio*(closed_deg-q),
        "servo_travel_full_deg": ratio*(closed_deg-open_deg),
        "ideal_min_toggle_margin_deg": 90-max(abs(closed_deg),abs(open_deg)),
        "status": "Ideal planar kinematic calculation only; no hardware/collision validation"
    }
    # Check equal opposite lengths and maintained orientation at 161 points.
    for index in range(161):
        t = closed_deg+(open_deg-closed_deg)*index/160
        bx, bz = length_mm*math.cos(rad(t)), length_mm*math.sin(rad(t))
        cx, cz = bx, bz+height_mm
        assert math.isclose(math.hypot(bx,bz), length_mm, abs_tol=1e-9)
        assert math.isclose(math.hypot(cx,cz-height_mm), length_mm, abs_tol=1e-9)
        assert math.isclose(cz-bz,height_mm,abs_tol=1e-9) and cx == bx
    return result

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length",type=float,default=25.0)
    parser.add_argument("--height",type=float,default=14.0)
    parser.add_argument("--closed",type=float,default=40.0)
    parser.add_argument("--opened",type=float,default=-40.0)
    parser.add_argument("--ratio",type=float,default=2.0)
    parser.add_argument("--target",type=float,default=30.0)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    try:
        value=evaluate(args.length,args.height,args.closed,args.opened,args.ratio,args.target)
    except ValueError as exc:
        parser.error(str(exc))
    text=json.dumps(value,ensure_ascii=False,indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(text+"\n",encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
