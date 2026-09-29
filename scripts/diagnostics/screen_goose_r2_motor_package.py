"""Screen the selected R2 visual four-bar axis against an XL330 motor box.

This tests a coaxial motor-at-A package hypothesis only. A remote drive can
move the motor into the head, but needs its own belt/gears, bearings, frame,
assembly and mass review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


XL330_BODY_WHD_MM = np.array([20.0, 34.0, 26.0])
XL330_SHAFT_FROM_TOP_ASSUMPTION_MM = 9.5
ROBOTIS_SOURCE = 'https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/'
VISUAL_FIXED_A_PRE_HEAD_TRANSFORM_MM = np.array([302.85, 0.0, 493.0])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.appearance_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['beak_pose'] != 'closed_visual_only':
        parser.error('Use the closed pose to screen the installed motor')
    if manifest['beak_ideal_r2_motion']['fixed_anchor_spacing_mm'] != 14:
        parser.error('Unexpected R2 four-bar axis layout')
    profile = manifest.get('vertical_profile_mm') or {}
    a = VISUAL_FIXED_A_PRE_HEAD_TRANSFORM_MM.copy()
    a[0] -= 125 + manifest['head_assembly_back_mm']
    a[2] += 150 + profile.get('head_z_shift', 0) - manifest['neck_assembly_drop_mm']
    half_x = XL330_BODY_WHD_MM[0] / 2
    half_y = XL330_BODY_WHD_MM[2] / 2
    motor_min = a + np.array([-half_x, -half_y,
                               -(XL330_BODY_WHD_MM[1] - XL330_SHAFT_FROM_TOP_ASSUMPTION_MM)])
    motor_max = a + np.array([half_x, half_y, XL330_SHAFT_FROM_TOP_ASSUMPTION_MM])
    skins = {}
    for name in ('head', 'beak_upper', 'beak_lower', 'beak_hinge',
                 'beak_mechanism_cover'):
        path = args.appearance_dir / f'{name}.stl'
        skins[name] = trimesh.load_mesh(path).bounds.round(3).tolist()
    head_min_z = skins['head'][0][2]
    hinge_min_z = skins['beak_hinge'][0][2]
    lowest_bill_z = min(skins[name][0][2] for name in ('beak_upper', 'beak_lower'))
    result = {
        'status': 'coaxial_xl330_at_visual_A_envelope_rejected_not_remote_drive_review',
        'appearance_manifest_sha256': sha256(manifest_path),
        'source_script_sha256': sha256(Path(__file__)),
        'vendor_source': ROBOTIS_SOURCE,
        'vendor_motor_total_whd_mm': XL330_BODY_WHD_MM.tolist(),
        'shaft_from_one_end_layout_assumption_mm': XL330_SHAFT_FROM_TOP_ASSUMPTION_MM,
        'orientation_assumption': 'Motor output axis along visual Y; width along X, height along Z; 26 mm total depth centred about the visual axis for this necessary screen.',
        'visual_fixed_A_axis_mm': a.round(3).tolist(),
        'motor_box_min_mm': motor_min.round(3).tolist(),
        'motor_box_max_mm': motor_max.round(3).tolist(),
        'visible_skin_axis_aligned_boxes_mm': skins,
        'motor_top_below_head_shell_bottom_mm': round(head_min_z - motor_max[2], 2),
        'motor_top_below_visual_hinge_bottom_mm': round(hinge_min_z - motor_max[2], 2),
        'motor_bottom_below_lowest_existing_bill_shell_mm': round(lowest_bill_z - motor_min[2], 2),
        'coaxial_A_motor_concealed_by_existing_visual_head_or_hinge': False,
        'next_required_alternatives': [
            'Move the single XL330 into the head and design/clear a 2:1 remote drive to axis A.',
            'Or redesign fixed axes, lower-jaw rigid carrier and cheek shell together so a coaxial drive fits without changing the selected pointed silhouette.',
        ],
        'limitations': [
            'Axis-aligned boxes cannot prove detailed interference or assembly access.',
            'The visual fixed A is an appearance mechanism landmark, not a frozen bearing or gear-axis datum.',
            'The motor envelope omits plug bend, screw heads, horn, idler and case tolerances.',
            'A remote drive has not been designed or screened here.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in (
        'visual_fixed_A_axis_mm', 'motor_top_below_head_shell_bottom_mm',
        'motor_top_below_visual_hinge_bottom_mm',
        'motor_bottom_below_lowest_existing_bill_shell_mm')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
