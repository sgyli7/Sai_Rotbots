"""Compare the same Goose exterior with its visual shoes shifted fore/aft.

This is a conditional support/mass screen, not balance, gait, seated contact,
actuator or manufacturing validation. It deliberately checks the pickup pose
as well as the neutral pose before treating a centered shoe as an improvement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from check_goose_exterior_mass_screen import (motor_and_component_items, placed,
                                               printed_parts, summary)
from check_goose_exterior_reach import pivots_from_manifest


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_pair(base_dir: Path, trial_dir: Path, pose: str) -> tuple[dict, dict, list[str]]:
    base = json.loads((base_dir / 'manifest.json').read_text())
    trial = json.loads((trial_dir / 'manifest.json').read_text())
    if base['source_sha256'] != trial['source_sha256']:
        raise ValueError(f'{pose}: exterior generator changed during the comparison')
    manifest_changes = {key for key in base.keys() | trial.keys()
                        if base.get(key) != trial.get(key)}
    if manifest_changes != {'foot_shift_mm'}:
        raise ValueError(f'{pose}: visual parameters changed beyond the shoe offset: {manifest_changes}')
    baseline_parts = {path.name: sha256(path) for path in base_dir.glob('*.stl')}
    trial_parts = {path.name: sha256(path) for path in trial_dir.glob('*.stl')}
    if baseline_parts.keys() != trial_parts.keys():
        raise ValueError(f'{pose}: part lists differ')
    changed = sorted(name for name in baseline_parts
                     if baseline_parts[name] != trial_parts[name])
    if not changed or not all(name.startswith('foot_') for name in changed):
        raise ValueError(f'{pose}: changes are not confined to the shoes')
    if base['foot_shift_mm'] != 0 or trial['foot_shift_mm'] != -20:
        raise ValueError(f'{pose}: expected the documented 0 to -20 mm shoe shift')
    if base['beak_pose'] != trial['beak_pose']:
        raise ValueError(f'{pose}: bill poses differ')
    return base, trial, changed


def mass_case(directory: Path, support: dict, root: Path,
              seated_pose: dict) -> dict:
    pivots = pivots_from_manifest(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    items = (printed_parts(directory, 1.6)
             + motor_and_component_items(root, pivots, manifest))
    standing = summary(placed(items, pivots), support, pivots['hip'])
    angles = seated_pose['pose_pitch_down_deg']
    seated = summary(placed(items, pivots,
                            angles['torso'], angles['neck_lower_relative'],
                            angles['neck_upper_relative'], angles['head_relative']),
                     support, pivots['hip'])
    x_min, x_max = support['double_support_necessary_x_com_interval_mm']
    target = seated_pose['target_bill_tip_visual_datum_mm']
    mass = seated['mass_kg']
    # A point mass after lift is a gravity sensitivity, not an actual grip.
    lifted_x = (mass * seated['projected_com_mm'][0] + .05 * target[0]) / (mass + .05)
    load_half_hip_moment = .05 * 9.81 * (target[0] - pivots['hip'][0]) / 2000
    return {
        'standing': standing,
        'seated_upper_body_pose_with_standing_leg_mass_positions': seated,
        'seated_plus_50g_point_load_proxy': {
            'projected_com_x_mm': round(lifted_x, 2),
            'front_sole_margin_mm': round(x_max - lifted_x, 2),
            'rear_sole_margin_mm': round(lifted_x - x_min, 2),
            'equal_share_hip_gravity_moment_Nm': round(
                seated['equal_share_per_hip_Nm'] + load_half_hip_moment, 3),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-closed', type=Path, required=True)
    parser.add_argument('--base-open', type=Path, required=True)
    parser.add_argument('--trial-closed', type=Path, required=True)
    parser.add_argument('--trial-open', type=Path, required=True)
    parser.add_argument('--base-support', type=Path, required=True)
    parser.add_argument('--trial-support', type=Path, required=True)
    parser.add_argument('--base-seated', type=Path, required=True)
    parser.add_argument('--trial-seated', type=Path, required=True)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    closed_base, closed_trial, closed_changed = inspect_pair(
        args.base_closed, args.trial_closed, 'closed')
    open_base, open_trial, open_changed = inspect_pair(
        args.base_open, args.trial_open, 'open')
    builder = args.project_root / 'scripts/cad/build_goose_exterior_study.py'
    if closed_base['source_sha256'] != open_base['source_sha256'] or closed_base['source_sha256'] != sha256(builder):
        raise ValueError('Compared visual poses must come from the current common exterior generator')
    if not closed_base['beak_pose'].startswith('closed') or not open_base['beak_pose'].startswith('parallel_open'):
        raise ValueError('Expected one closed and one open visual pose per candidate')
    supports = [json.loads(path.read_text()) for path in
                (args.base_support, args.trial_support)]
    seated = [json.loads(path.read_text()) for path in
              (args.base_seated, args.trial_seated)]
    for i, (support, appearance, pose, opened) in enumerate(zip(
            supports, (args.base_closed, args.trial_closed), seated,
            (args.base_open, args.trial_open))):
        if support['source_manifest_sha256'] != sha256(appearance / 'manifest.json'):
            raise ValueError(f'{i}: support belongs to another exterior')
        if pose['source_appearance_xml_sha256'] != sha256(opened / 'appearance.xml'):
            raise ValueError(f'{i}: seated pose belongs to another exterior')
    if seated[0]['pose_pitch_down_deg'] != seated[1]['pose_pitch_down_deg']:
        raise ValueError('Compared seated poses use different joint angles')
    if seated[0]['target_bill_tip_visual_datum_mm'] != seated[1]['target_bill_tip_visual_datum_mm']:
        raise ValueError('Compared seated poses aim at different targets')
    if not all(pose['sampled_stand_to_target_sweep']['necessary_clearance_pass']
               for pose in seated):
        raise ValueError('One candidate failed the sampled visual reach path')

    base_case = mass_case(args.base_closed, supports[0], args.project_root, seated[0])
    trial_case = mass_case(args.trial_closed, supports[1], args.project_root, seated[1])
    before = base_case['standing']['double_support_x_margin_to_nearest_end_mm']
    after = trial_case['standing']['double_support_x_margin_to_nearest_end_mm']
    low_before = base_case['seated_upper_body_pose_with_standing_leg_mass_positions'][
        'double_support_x_margin_to_nearest_end_mm']
    low_after = trial_case['seated_upper_body_pose_with_standing_leg_mass_positions'][
        'double_support_x_margin_to_nearest_end_mm']
    files = {
        'base_closed_manifest': args.base_closed / 'manifest.json',
        'base_open_manifest': args.base_open / 'manifest.json',
        'trial_closed_manifest': args.trial_closed / 'manifest.json',
        'trial_open_manifest': args.trial_open / 'manifest.json',
        'base_support': args.base_support, 'trial_support': args.trial_support,
        'base_seated': args.base_seated, 'trial_seated': args.trial_seated,
    }
    result = {
        'status': 'foot_recenter_trade_screen_only_no_selection_or_balance_release',
        'source_script_sha256': sha256(Path(__file__)),
        'input_sha256': {name: sha256(path) for name, path in files.items()},
        'common_exterior_builder_sha256': closed_base['source_sha256'],
        'shoe_shift_before_after_mm': [closed_base['foot_shift_mm'],
                                       closed_trial['foot_shift_mm']],
        'same_part_geometry_except_shoes': True,
        'changed_stl_parts_by_pose': {'closed': closed_changed, 'open': open_changed},
        'conditional_wall_mm': 1.6,
        'base': base_case, 'trial': trial_case,
        'trade': {
            'standing_nearest_sagittal_margin_change_mm': round(after - before, 2),
            'seated_nearest_sagittal_margin_change_mm': round(low_after - low_before, 2),
            'seated_hip_gravity_screen_pass': bool(
                base_case['seated_upper_body_pose_with_standing_leg_mass_positions'][
                    'per_hip_screening_pass'] and
                trial_case['seated_upper_body_pose_with_standing_leg_mass_positions'][
                    'per_hip_screening_pass']),
        },
        'decision': 'Keep the centered-foot shoe as an unresolved trade; do not freeze the foot or infer stable pickup from improved neutral support.',
        'limitations': [
            'These are visual STL sole patches and assumed 1.6 mm uniform PETG surface masses, not a measured robot or verified contact pressure.',
            'The low-pose mass calculation rotates the upper body but keeps leg mass at its standing locations; seated leg collision and mass relocation are not covered.',
            'The 50 g point load is a post-lift gravity sensitivity only; no object contact, grip force, locomotion or drag is simulated.',
            'The 0.82 Nm per-hip screen is not a continuous thermal torque rating; a failure is a design warning, not a full actuator selection.',
            'The visual candidate has not passed the user appearance review or same-candidate MuJoCo/Godot dynamics.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'trade': result['trade']},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
