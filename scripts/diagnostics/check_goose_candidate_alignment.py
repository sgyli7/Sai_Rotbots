"""Check whether the selected Goose exterior and runtime assets describe one robot.

This is a necessary handoff gate, not a manufacturing or Sim2Sim validation.
An appearance study must never inherit the successes of a different RC2 model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratio_from_drive(text: str | None) -> float | None:
    match = re.search(r'(?<!\d)(\d+)\s*:\s*(\d+)(?!\d)', text or '')
    if not match or int(match.group(2)) == 0:
        return None
    return int(match.group(1)) / int(match.group(2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-manifest', type=Path,
                        default=ROBOT / 'cad/exports/goose_r2_slim_bill_v73_visual_closed_manifest.json')
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()

    files = {
        'appearance_manifest': args.appearance_manifest,
        'spec': ROBOT / 'configs/robot_spec.json',
        'model_manifest': ROBOT / 'models/full/robot_manifest.json',
        'model_xml': ROBOT / 'models/full/robot.xml',
        'cad_manifest': ROBOT / 'cad/exports/cad_manifest.json',
        'rigid_transfer': ROBOT / 'models/full/rigid_transfer.json',
    }
    data = {name: json.loads(path.read_text()) for name, path in files.items()
            if name != 'model_xml'}
    appearance = data['appearance_manifest']
    spec = data['spec']
    model = data['model_manifest']
    cad = data['cad_manifest']
    transfer = data['rigid_transfer']
    package = appearance.get('beak_drive_package_hypothesis') or {}
    beak_joint = next(j for j in spec['joints'] if j['name'] == 'beak_drive')
    beak_servo = spec['servos'][beak_joint['servo']]['model']
    visual_motor = package.get('motor')
    visual_anchor_mm = appearance['beak_ideal_r2_motion']['fixed_anchor_spacing_mm']
    spec_anchor_mm = spec['beak']['anchor_spacing_m'] * 1000
    visual_ratio = ratio_from_drive(package.get('tentative_drive'))
    spec_ratio = spec['beak']['transmission_ratio']
    appearance_hash = digest(files['appearance_manifest'])
    appearance_builder = ROOT / 'scripts/cad/build_goose_exterior_study.py'

    checks = {
        'appearance_review_pass': appearance.get('appearance_review_pass') is True,
        'appearance_manifest_matches_current_generator': appearance.get('source_sha256') == digest(appearance_builder),
        'beak_anchor_spacing_matches_mm': abs(visual_anchor_mm - spec_anchor_mm) < 1e-6,
        'beak_motor_model_matches': visual_motor == beak_servo,
        'beak_transmission_ratio_matches': visual_ratio is not None and abs(visual_ratio - spec_ratio) < 1e-6,
        'model_manifest_links_this_appearance': model.get('appearance_manifest_sha256') == appearance_hash,
        'cad_manifest_links_this_appearance': cad.get('appearance_manifest_sha256') == appearance_hash,
        'model_manifest_matches_model_file': model.get('model_sha256') == digest(files['model_xml']),
        'model_manifest_matches_spec': model.get('source_spec_sha256') == digest(files['spec']),
        'cad_manifest_matches_spec': cad.get('spec_sha256') == digest(files['spec']),
        'rigid_transfer_matches_model': transfer.get('model_sha256') == digest(files['model_xml']),
    }
    visual_body_mm = [appearance['compact_body_length_mm'], 190,
                      appearance['compact_body_height_mm']] if appearance.get('compact_body_study') else None
    spec_body_mm = [round(v * 1000, 3) for v in spec['body_dimensions_m']]
    result = {
        'status': ('necessary_candidate_alignment_pass_only' if all(checks.values())
                   else 'candidate_assets_not_aligned'),
        'scope': 'Same-candidate provenance and beak contract only; no shape/strength, locomotion, grasp, drag or cross-engine approval.',
        'appearance_manifest_sha256': appearance_hash,
        'source_script_sha256': digest(Path(__file__)),
        'source_files_sha256': {name: digest(path) for name, path in files.items()},
        'current_appearance_builder_sha256': digest(appearance_builder),
        'revisions': {
            'appearance': appearance.get('appearance_revision'),
            'spec': spec.get('engineering_revision'),
            'model': model.get('revision'),
            'cad': cad.get('revision'),
            'rigid_transfer': transfer.get('revision'),
        },
        'body_envelope_comparison_mm': {
            'visual_outer_shell': visual_body_mm,
            'spec_nominal_body': spec_body_mm,
            'difference_visual_minus_spec': ([round(a - b, 3) for a, b in zip(visual_body_mm, spec_body_mm)]
                                             if visual_body_mm else None),
            'interpretation': 'A visual shell and simplified physics body need not match exactly; the large difference requires deliberate remapping and mass/inertia review.',
        },
        'beak_comparison': {
            'visual_anchor_spacing_mm': visual_anchor_mm,
            'spec_anchor_spacing_mm': spec_anchor_mm,
            'visual_motor': visual_motor,
            'spec_motor': beak_servo,
            'visual_nominal_drive_ratio': visual_ratio,
            'spec_drive_ratio': spec_ratio,
        },
        'active_joint_count': len(model['active_joint_names']),
        'checks': checks,
        'pass': all(checks.values()),
        'decision': ('The selected exterior can proceed only to further engineering gates.'
                     if all(checks.values()) else
                     'Do not treat the RC2 CAD/model/transfer as the selected R2 exterior or use their tests to approve it.'),
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'pass': result['pass'],
                      'failed_checks': [name for name, ok in checks.items() if not ok],
                      'beak_comparison': result['beak_comparison']}, ensure_ascii=False))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
