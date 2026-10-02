"""Map visual seated bill reach and sampled torso/head clearances.

This is a geometry-only filter for candidate points, not a grasp, controller,
joint-package, cable or walking validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from check_goose_exterior_reach import (pivots_from_manifest, sampled_geometry,
                                         solve_pose, tip_datum_from_mesh)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_target(appearance_dir: Path, pivots: dict, tip: np.ndarray,
                   x_mm: float, z_mm: float, sit_drop_mm: float,
                   torso_deg: float, head_global_deg: float, steps: int) -> dict:
    try:
        lower, upper, head = solve_pose(
            np.array([x_mm, 0.0, z_mm + sit_drop_mm]), torso_deg,
            head_global_deg, tip, pivots)
    except ValueError as exc:
        return {'x_mm': x_mm, 'z_mm': z_mm, 'ik_reached': False,
                'reason': str(exc), 'sampled_clearance_pass': False}
    samples = []
    for fraction in np.linspace(0.0, 1.0, steps):
        geometry = sampled_geometry(appearance_dir / 'appearance.xml',
                                    torso_deg * fraction, lower * fraction,
                                    upper * fraction, head * fraction, pivots)
        beak_low = min(geometry['beak_min_height_world_mm'].values())
        samples.append({
            'lower_to_body_mm': geometry['lower_fairing_to_body_sampled_min_mm'],
            'upper_to_body_mm': geometry['upper_fairing_to_body_sampled_min_mm'],
            'head_to_body_mm': geometry['head_shell_to_body_sampled_min_mm'],
            'body_floor_mm': geometry['body_min_height_world_mm']
                             - sit_drop_mm * fraction,
            'beak_floor_mm': beak_low - sit_drop_mm * fraction,
        })
    minimum = {key: round(min(row[key] for row in samples), 2)
               for key in samples[0]}
    clearance_pass = bool(minimum['lower_to_body_mm'] >= 5
                          and minimum['upper_to_body_mm'] >= 5
                          and minimum['head_to_body_mm'] >= 5
                          and minimum['body_floor_mm'] >= 10
                          and minimum['beak_floor_mm'] >= 2)
    return {
        'x_mm': x_mm, 'z_mm': z_mm, 'ik_reached': True,
        'pose_relative_pitch_deg': {'lower_neck': round(lower, 2),
                                    'upper_neck': round(upper, 2),
                                    'head': round(head, 2)},
        'sampled_path_minimum_clearance_mm': minimum,
        'sampled_clearance_pass': clearance_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--x-mm', type=float, nargs='+', required=True)
    parser.add_argument('--z-mm', type=float, nargs='+', required=True)
    parser.add_argument('--sit-drop-mm', type=float, default=90)
    parser.add_argument('--torso-deg', type=float, default=20)
    parser.add_argument('--head-global-deg', type=float, default=60)
    parser.add_argument('--steps', type=int, default=21)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if args.steps < 2 or args.sit_drop_mm < 0:
        parser.error('A sampled seated path needs at least two steps and a nonnegative drop')
    pivots = pivots_from_manifest(args.appearance_dir)
    tip = tip_datum_from_mesh(args.appearance_dir)
    rows = [inspect_target(args.appearance_dir, pivots, tip, x, z,
                           args.sit_drop_mm, args.torso_deg,
                           args.head_global_deg, args.steps)
            for z in args.z_mm for x in args.x_mm]
    result = {
        'status': 'visual_seated_workspace_geometry_only_not_grasp_release',
        'appearance_manifest_sha256': sha256(args.appearance_dir / 'manifest.json'),
        'appearance_xml_sha256': sha256(args.appearance_dir / 'appearance.xml'),
        'source_script_sha256': sha256(Path(__file__)),
        'pose_basis': {'sit_drop_mm': args.sit_drop_mm,
                       'torso_pitch_down_deg': args.torso_deg,
                       'head_global_pitch_down_deg': args.head_global_deg,
                       'visual_bill_tip_datum_mm': tip.tolist()},
        'path_sample_count': args.steps,
        'necessary_thresholds_mm': {'neck_or_head_to_body': 5,
                                    'body_to_floor': 10, 'beak_to_floor': 2},
        'targets': rows,
        'passing_target_count': sum(row['sampled_clearance_pass'] for row in rows),
        'limitations': [
            'Only a straight joint-space interpolation to each pose is sampled; untested paths may collide.',
            'The test omits leg-link and knee-cover floor collision, mechanical joint stops, R2 lower-jaw opening/floor sweep, motor/body installation, wiring and manufacturing tolerances.',
            'No joint torque, continuous thermal load, contact grip, object or dynamic transition is simulated here.',
            'The current appearance shells are visual solids and have not passed the user exterior review.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passing_target_count': result['passing_target_count'],
                      'target_count': len(rows),
                      'passing_targets_xz_mm': [[r['x_mm'], r['z_mm']] for r in rows
                                                if r['sampled_clearance_pass']]},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
