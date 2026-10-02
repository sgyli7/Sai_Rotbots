"""Necessary box-envelope screen for a sixth ankle axis in the R2 visual shoe.

This uses manufacturer body dimensions and an explicit trial orientation. It
cannot certify a horn, idler, bracket, wire bend, shell hollow, or printability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from check_goose_exterior_reach import pivots_from_manifest


ROLL_SHAFT_MM = np.array([65.0, 88.0, 32.0])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--pitch-servo', choices=['xm430', 'xm540'], default='xm430',
                        help='Use the actual ankle-pitch motor assumed by the physics trial.')
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    pitch_motor = spec['servos'][args.pitch_servo]
    roll_motor = spec['servos']['xm430']
    pitch_width, pitch_height, pitch_depth = np.array(pitch_motor['body_whd_m']) * 1000
    pitch_shaft_from_top = pitch_motor['shaft_from_top_m'] * 1000
    roll_width, roll_height, roll_depth = np.array(roll_motor['body_whd_m']) * 1000
    roll_shaft_from_top = roll_motor['shaft_from_top_m'] * 1000
    pitch_shaft = (pivots_from_manifest(args.appearance_dir)['ankle']
                   + np.array([0.0, 88.0, 0.0]))
    foot = {name: trimesh.load_mesh(args.appearance_dir / f'{name}_1.stl').bounds
            for name in ('foot_sole', 'foot_white', 'ankle')}

    # Pitch shaft along Y; shell width is X, motor height Z. For the roll servo,
    # the output shaft points forward along X; motor height points toward +Y.
    # The latter choice keeps the 28.5 mm width vertical in the low shoe.
    pitch_min = np.array([-pitch_width / 2, pitch_shaft[1] - pitch_depth / 2,
                          pitch_shaft[2] - (pitch_height - pitch_shaft_from_top)])
    pitch_max = np.array([pitch_width / 2, pitch_shaft[1] + pitch_depth / 2,
                          pitch_shaft[2] + pitch_shaft_from_top])
    roll_min = np.array([ROLL_SHAFT_MM[0] - roll_depth,
                         ROLL_SHAFT_MM[1] - (roll_height - roll_shaft_from_top),
                         ROLL_SHAFT_MM[2] - roll_width / 2])
    roll_max = np.array([ROLL_SHAFT_MM[0], ROLL_SHAFT_MM[1] + roll_shaft_from_top,
                         ROLL_SHAFT_MM[2] + roll_width / 2])
    axis_gap = np.maximum(roll_min - pitch_max, pitch_min - roll_max)
    body_separation = float(np.linalg.norm(np.maximum(axis_gap, 0)))
    sole_top = float(foot['foot_sole'][1, 2])
    white_top = float(foot['foot_white'][1, 2])
    sole = foot['foot_sole']
    ankle_box = foot['ankle']
    hub_center_xz = (ankle_box[0, [0, 2]] + ankle_box[1, [0, 2]]) / 2
    hub_radius = float((ankle_box[1, 0] - ankle_box[0, 0]) / 2)
    highest_radial_extent = max(
        float(np.hypot(x - hub_center_xz[0], z - hub_center_xz[1]))
        for x in (pitch_min[0], pitch_max[0])
        for z in (max(white_top, pitch_min[2]), pitch_max[2]))
    hub_radial_gap = hub_radius - highest_radial_extent
    hub_y_gap = min(pitch_min[1] - ankle_box[0, 1],
                    ankle_box[1, 1] - pitch_max[1])
    result = {
        'status': 'necessary_motor_body_box_screen_only_not_mounting_release',
        'appearance_manifest_sha256': sha256(args.appearance_dir / 'manifest.json'),
        'spec_sha256': sha256(args.spec),
        'source_script_sha256': sha256(Path(__file__)),
        'sku': {'pitch': pitch_motor['model'], 'roll': roll_motor['model']},
        'orientation_assumption': {
            'pitch_output_axis': 'world_y',
            'pitch_motor_height_axis': 'world_z',
            'roll_output_axis': 'world_x',
            'roll_motor_height_axis': 'world_y_toward_inner_side',
        },
        'shaft_centres_mm_left': {
            'pitch': pitch_shaft.tolist(), 'roll': ROLL_SHAFT_MM.tolist()},
        'motor_body_boxes_mm_left': {
            'pitch': {'min': pitch_min.tolist(), 'max': pitch_max.tolist()},
            'roll': {'min': roll_min.tolist(), 'max': roll_max.tolist()},
        },
        'minimum_body_box_separation_mm': round(body_separation, 2),
        'nominal_rear_idler_plane_x_mm': round(
            ROLL_SHAFT_MM[0] + roll_motor['rear_idler_plane_m'] * 1000, 2),
        'rear_idler_plane_to_pitch_body_x_gap_mm': round(
            ROLL_SHAFT_MM[0] + roll_motor['rear_idler_plane_m'] * 1000 - pitch_max[0], 2),
        'roll_body_within_sole_xy_bbox': bool(
            np.all(roll_min[:2] >= sole[0, :2]) and
            np.all(roll_max[:2] <= sole[1, :2])),
        'pitch_motor_bottom_above_sole_top_mm': round(float(pitch_min[2] - sole_top), 2),
        'pitch_motor_top_above_white_shell_top_mm': round(float(pitch_max[2] - white_top), 2),
        'roll_motor_bottom_above_sole_top_mm': round(float(roll_min[2] - sole_top), 2),
        'roll_motor_top_above_white_shell_top_mm': round(float(roll_max[2] - white_top), 2),
        'pitch_body_above_white_within_black_hub_nominal': bool(
            hub_radial_gap >= 0 and hub_y_gap >= 0),
        'pitch_body_to_black_hub_radial_gap_above_white_mm': round(hub_radial_gap, 2),
        'pitch_body_to_black_hub_y_gap_each_side_min_mm': round(float(hub_y_gap), 2),
        'release_pass': False,
        'missing_for_release': [
            'The visual shoe is solid; a motor cavity and a raised cover must be designed.',
            'Only motor body boxes are separated; horn, rear idler, brackets, screws and wiring are not placed.',
            'The fore-aft shaft offset needs a stiff load path and whole-range collision sweep.',
            'No fit tolerance, print orientation, wall strength or continuous ankle torque is verified.',
            'The black hub containment check treats the visible solid as a hollowable cylinder; it does not reserve motor walls, horn or fastener access.',
        ],
    }
    if result['pitch_motor_bottom_above_sole_top_mm'] < 0:
        result['missing_for_release'].append(
            'The pitch motor body enters the visual sole; this profile requires a new ankle/foot package, not a shallow cavity.')
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
