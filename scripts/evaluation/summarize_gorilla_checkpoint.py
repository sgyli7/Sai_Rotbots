"""Summarize a rejected engineering candidate without turning screens into ratings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/gorilla_v0_1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = {
        'spec': ROBOT / 'configs/layout_b_spec.json',
        'scene': ROBOT / 'cad/source/layout_b_scene.json',
        'model': ROBOT / 'models/full/robot.xml',
        'contract': ROBOT / 'models/full/robot.json',
        'build': ROBOT / 'evidence/layout_b_build.json',
        'screen': ROBOT / 'evidence/layout_b_screen.json',
        'render': ROBOT / 'evidence/layout_b_render.json',
        'internal': ROBOT / 'evidence/layout_b_internal_screen.json',
        'visual_review': ROBOT / 'evidence/layout_b_visual_review.json',
        'gates': ROBOT / 'evidence/layout_b_gates.json',
        'resources': ROBOT / 'evidence/layout_b_resource_validation.json',
    }
    data = {k: json.loads(p.read_text()) for k, p in paths.items() if k != 'model'}
    contract, screen = data['contract'], data['screen']
    for key, file in (('model_sha256', 'model'), ('spec_sha256', 'spec')):
        if screen[key] != sha(paths[file]) or contract[key] != sha(paths[file]):
            raise ValueError('Refusing a checkpoint assembled from different candidates')
    if contract['scene_sha256'] != sha(paths['scene']):
        raise ValueError('Geometry source changed after physics generation')
    render = data['render']
    if render['scene_sha256'] != sha(paths['scene']) or render['spec_sha256'] != sha(paths['spec']):
        raise ValueError('Neutral render sources differ from the physical candidate')
    for key, file in (('model_sha256', 'model'), ('model_contract_sha256', 'contract'),
                      ('screen_sha256', 'screen')):
        if render['pose_binding'][key] != sha(paths[file]):
            raise ValueError('Pose render and physical screening versions differ')
    for item in render['images']:
        if sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('Rendered image changed after the recorded review')
    internal = data['internal']
    for key, file in (('spec', 'spec'), ('scene', 'scene'), ('model_xml', 'model'),
                      ('si_contract', 'contract')):
        if internal['source_hashes'][key] != sha(paths[file]):
            raise ValueError('Internal layout screen and physical candidate differ')
    if data['gates']['model_sha256'] != sha(paths['model']):
        raise ValueError('Gate records refer to a different model')
    if data['visual_review']['render_manifest_sha256'] != sha(paths['render']):
        raise ValueError('Visual review refers to a different render set')
    components = [c for b in contract['bodies'].values() for c in b['components']]
    lower = sum(c['mass_kg'] * (1 - c['uncertainty_fraction']) for c in components)
    upper = sum(c['mass_kg'] * (1 + c['uncertainty_fraction']) for c in components)
    neutral = next(s for s in screen['static_samples'] if s['pose'] == 'neutral'
                   and s['payload_proxy_kg'] == 0 and s['robot_mass_scale'] == 1)
    pose_results = []
    for s in screen['static_samples']:
        if s['payload_proxy_kg'] not in (0, 20) or s['robot_mass_scale'] != 1:
            continue
        result = {k: s[k] for k in (
            'pose', 'payload_proxy_kg', 'max_design_torque_utilization',
            'worst_joint', 'worst_joint_demand_nm', 'payload_force_points_m',
            'hand_ik_error_m', 'limited_screen_pass')}
        result['collision'] = s['collision']
        result['robot_potential_energy_j'] = screen['robot_mass_kg'] * 9.81 * s['robot_com_m'][2]
        result['potential_drop_from_neutral_j'] = screen['robot_mass_kg'] * 9.81 * (
            neutral['robot_com_m'][2] - s['robot_com_m'][2])
        # Homogeneous static force scaling is valid only with zero external wrench.
        # This keeps geometry, COM and torque limits fixed; it is NOT a new design.
        if s['payload_proxy_kg'] == 0 and s['door_reaction_force_n'] == 0:
            result['uniform_mass_scaling_torque_only_breakpoint_kg'] = (
                screen['robot_mass_kg'] / s['max_design_torque_utilization'])
        pose_results.append(result)
    report = {
        'schema': 'gorilla_engineering_checkpoint_v1',
        'robot_id': 'gorilla_v0_1', 'checkpoint_id': 'gorilla_layout_b',
        'status': 'REJECTED_CANDIDATE_AVAILABLE_FOR_REVIEW',
        'source_files': {k: {'path': str(p.relative_to(ROOT)), 'sha256': sha(p)}
                         for k, p in paths.items()},
        'summarizer_sha256': sha(Path(__file__)),
        'geometry_dimensions_xyz_m': data['scene']['dimensions_xyz_m'],
        'robot_mass_kg': screen['robot_mass_kg'],
        'mass_component_hypothesis_range_kg': [lower, upper],
        'mass_range_scope': 'Correlated declared +/- assumptions only. Unidentified parts and changes in real procurement are not covered.',
        'mass_breakdown_kg': data['build']['mass_breakdown_kg'],
        'internal_screen_counts': internal['counts'],
        'internal_packaging_pass': internal['internal_packaging_pass'],
        'active_joint_count': contract['active_joint_count'],
        'neutral_com_m': neutral['robot_com_m'],
        'earth_weight_n': screen['robot_mass_kg'] * 9.81,
        'pose_results': pose_results,
        'static_passes': screen['limited_static_pass_count'],
        'static_samples': screen['static_sample_count'],
        'dynamics': [{k: r[k] for k in (
            'dt_s', 'actual_duration_s', 'actual_integrations', 'completed',
            'finite', 'limited_rejection_pass', 'stop_reasons', 'max_contact_penetration_m')}
            for r in screen['diagnostic_rejection_runs']],
        'energy_hypotheses': screen['energy_hypotheses'],
        'rated_payload_kg': None, 'rated_walk_speed_m_s': None,
        'runtime_endurance_verified': False,
        'appearance_acceptance': False,
        'appearance_scope': 'Original reference identity and proportions preserved as reconstruction inputs; simplified shells remain a visual proxy requiring review, not an approved production shape.',
        'physical_hard_freeze': False, 'manufacturing_release': False,
        'hardware_validation': False, 'bevy_acceptance': False,
        'walking_acceptance': False, 'object_pickup_acceptance': False,
        'policy_included': False,
        'next_entry': 'Keep exterior source identity; redesign internal actuation packaging and load path, then rebuild mass/inertia and rerun rejection screens before task or training handoff.',
    }
    out = ROBOT / 'evidence/layout_b_checkpoint.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'out': str(out), 'status': report['status'],
                      'mass_kg': report['robot_mass_kg'], 'mass_range_kg': [lower, upper]}))


if __name__ == '__main__':
    main()
