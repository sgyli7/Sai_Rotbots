#!/usr/bin/env python3
"""Couple D's actual endpoint moment arms to pump flow and power hypotheses.

This samples endpoint geometry at constant rates inferred from neutral-to-pose
angles. It is not a trajectory, dynamic force or continuous thermal test.
"""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/gorilla_v0_1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [ROBOT / 'evidence/internal_structure_d_screen.json',
             ROBOT / 'configs/internal_structure_d_spec.json',
             ROBOT / 'configs/internal_structure_d_system_spec.json']
    screen, spec, system = [json.loads(p.read_text()) for p in paths]
    for path, expected in screen['input_hashes'].items():
        assert sha(ROOT / path) == expected, 'Changed static source: ' + path
    assert screen['evaluator_sha256'] == sha(ROOT / 'scripts/evaluation/evaluate_gorilla_distributed_layout.py')
    assert screen['scene_sha256'] == sha(ROBOT / 'cad/source/internal_structure_d_scene.json')
    assert screen['input_hashes'][str(paths[1].relative_to(ROOT))] == sha(paths[1])
    links = {x['id']: x for x in spec['actuator_definitions']}
    pump = system['power_flow_screen']
    available = pump['two_pumps_flow_sensitivity_L_min']
    rows = []
    for pose in screen['poses']:
        if pose['id'] == 'neutral':
            continue
        angles = spec['candidate_pose_angles_deg'][pose['id']]
        for seconds in (2., 4., 8.):
            for case in pose['cases']:
                lp = case['mapped_hydraulic_and_foot_pin_LP']
                if not lp['solver_success']:
                    continue
                terms = []
                for force in lp['force_models']:
                    if force['kind'] != 'hydraulic_pitch':
                        continue
                    link = links[force['id']]
                    family = force['id'].split('_', 1)[1]
                    qdot = math.radians(angles[family]) / seconds
                    velocity = force['effective_arm_m'] * qdot
                    cap_area = math.pi * link['bore_m'] ** 2 / 4
                    annular = cap_area - math.pi * link['rod_m'] ** 2 / 4
                    supply = (cap_area if velocity >= 0 else annular) * abs(velocity)
                    returned = (annular if velocity >= 0 else cap_area) * abs(velocity)
                    terms.append({'id': force['id'], 'joint_rate_rad_s_hypothesis': qdot,
                                  'eye_length_rate_m_s_at_endpoint': velocity,
                                  'supply_flow_L_min': supply * 60000,
                                  'return_flow_L_min': returned * 60000,
                                  'quasistatic_witness_force_N': force['force_N_at_witness'],
                                  'signed_useful_mechanical_power_W': force['force_N_at_witness'] * velocity})
                flow = sum(t['supply_flow_L_min'] for t in terms)
                useful = sum(t['signed_useful_mechanical_power_W'] for t in terms)
                supplied = flow / 60000 * spec['hydraulic_pump_pressure_Pa_hypothesis']
                rows.append({'pose_endpoint_sample': pose['id'], 'nominal_transition_seconds_hypothesis': seconds,
                             'mass_profile': case['mass_profile'], 'payload_kg_hypothesis': case['payload_kg_hypothesis'],
                             'separate_pressure_demand_kg': case['separate_pressure_demand_kg'],
                             'gravity_factor_sensitivity': case['gravity_factor_sensitivity'],
                             'actuators': terms, 'total_supply_flow_L_min': flow,
                             'design_pressure_stream_power_W': supplied,
                             'signed_quasistatic_useful_power_W': useful,
                             'stream_minus_useful_power_W': supplied - useful,
                             'exceeds_both_3000rpm_flow_sensitivity_endpoints': flow > max(available),
                             'within_both_3000rpm_flow_sensitivity_endpoints': flow <= min(available),
                             'physical_acceptance': False})
    result = {'robot_id': 'gorilla_v0_1', 'candidate': 'internal_structure_d',
              'input_hashes': {str(p.relative_to(ROOT)): sha(p) for p in [*paths, Path(__file__)]},
              'pump_working_point': pump, 'samples': rows,
              'formulas': {'stroke_rate': 'dL/dt=(dL/dq)*dq/dt',
                           'supply_flow': 'Acap*dL/dt on extension; Aannular*abs(dL/dt) on retraction',
                           'pressure_stream_power': 'pump design pressure times summed supply flow',
                           'useful_power': 'sum(signed quasistatic actuator witness force times signed eye velocity)'},
              'scope': 'Endpoint samples only, not integrated path or swept collision. Constant neutral-to-pose rates preserve the chosen sagittal ankle angle sum, but closed-chain component dynamics/reactions and acceleration are absent. Same static LP witness does not prove a dynamic contact allocation. Fixed pressure stream minus useful work identifies metering/return/negative-work energy to account for; it is not a qualified heat or regeneration value. Pump efficiencies, inlet, controller, actual duty, valve loss, other rotary motors and cooling remain unclosed. No payload/speed/endurance recommendation is released.',
              'geometry_accepted': False, 'physics_accepted': False, 'stable_physical_contract': False}
    out = ROBOT / 'evidence/internal_structure_d_power.json'
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'samples': len(rows), 'flow_range_L_min': [min(r['total_supply_flow_L_min'] for r in rows), max(r['total_supply_flow_L_min'] for r in rows)],
                      'exceed_3000rpm_upper_endpoint_count': sum(r['exceeds_both_3000rpm_flow_sensitivity_endpoints'] for r in rows),
                      'physical_acceptance': False}))


if __name__ == '__main__':
    main()
