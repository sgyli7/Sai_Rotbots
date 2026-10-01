"""Bounded posture rejection after replacing the old grip proxy with real pads.

Finite IK candidates, static wrench/torque checks and three jaw endpoints.
No PPO, geometry changes, controller, physical pickup or global optimum claim.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull

from sai_agent.goose.native_linkage import set_passive_linkage

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'evidence/body_bay_mechanical_parameters.json',
             R/'configs/mechanical_physics_contract.json',
             R/'models/mechanical_physics/robot.xml',
             R/'configs/mechanical_grip_reference.json',
             R/'configs/mechanical_task_poses.json']
    ledger, contract = [json.loads(p.read_text()) for p in paths[:2]]
    for relative, digest in contract['source_hashes'].items():
        if sha(ROOT/relative) != digest:
            raise ValueError(('stale model', relative))
    if sha(paths[2]) != contract['model_sha256']:
        raise ValueError('physics XML identity mismatch')
    s = candidate()
    s.pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
    s.grip = np.array(ledger['grip_world_at_zero_m'])
    s.tip = np.array(ledger['tip_world_at_zero_m'])
    s.items = ledger['items']
    s.contact_hulls = {n: ConvexHull(np.array(v)) for n, v in ledger['contact_hulls'].items()}
    s.contact_center_y_m = ledger['contact_center_y_m']
    static_models = {variant: s.model(variant)[0] for variant in [-1, 0, 1]}
    model = mujoco.MjModel.from_xml_path(str(paths[2]))
    data = mujoco.MjData(model)
    order = contract['joint_order']
    qadr = [model.joint(n).qposadr[0] for n in order]
    joints = {j['name']: j for j in contract['joints']}
    part_lookup = {g['name']: g['part'] for g in contract['collision_geometries']}
    neck = ['neck_pitch', 'neck_mid_pitch', 'head_pitch']
    bounds = np.array([joints[n]['range_rad'] for n in neck])
    started = time.monotonic()
    records = []
    completed = True
    for drop in [70, 80, 90, 100]:
        for target_x in [.22, .26, .30]:
            for pitch in [.6, .85, 1.1]:
                if time.monotonic()-started > 60:
                    completed = False
                    break
                q, root, rotation = s.pose(drop)
                target = np.array([target_x, 0., .015])

                def grip_at(angles):
                    pose = dict(q)
                    pose.update(zip(neck, angles))
                    poses, _ = s.fk(pose, root_p=root, root_r=rotation)
                    hp, hr = poses['head_roll']
                    return hp+hr@(s.grip-s.pivots['head_roll'])

                def residual(angles):
                    return np.r_[(grip_at(angles)-target)[[0, 2]], .10*(sum(angles)-pitch)]

                sol = least_squares(residual, [2.17, .08, -.95],
                                    bounds=(bounds[:, 0], bounds[:, 1]), max_nfev=80)
                q.update(zip(neck, sol.x.tolist()))
                grip = grip_at(sol.x)
                position_error = float(np.linalg.norm(grip-target))
                pitch_error = float(abs(sum(sol.x)-pitch))
                violations = [n for n in order if not joints[n]['range_rad'][0] <= q[n] <= joints[n]['range_rad'][1]]
                ik_pass = not violations and position_error < .001 and pitch_error < .01
                static = []
                endpoints = []
                if ik_pass:
                    for variant, sm in static_models.items():
                        for drag in [-2, 0, 2]:
                            result = s.evaluate('native_pad_ground_candidate', q, root, rotation,
                                                ['right', 'left'], variant, drag, sm)
                            overloads = [n for n in order if abs(result['joint_torque_nm'][n]) > joints[n]['continuous_design_limit_nm']]
                            static.append(dict(mass_variant=variant, drag_x_n=drag,
                                               contact_wrench_feasible=result['static_contact_feasible'],
                                               minimum_foot_edge_margin_m=min(x['edge_margin_m'] for x in result['contacts']),
                                               joint_torque_nm=result['joint_torque_nm'],
                                               overloaded_axes=overloads,
                                               static_screen_pass=result['static_contact_feasible'] and not overloads))
                    for angle in [0., .22, .55]:
                        mujoco.mj_resetData(model, data)
                        data.qpos[:3] = root
                        data.qpos[3:7] = [1, 0, 0, 0]
                        data.qpos[qadr] = [q[n] for n in order]
                        data.qpos[model.joint('beak_hinge').qposadr[0]] = angle
                        set_passive_linkage(model, data, contract)
                        mujoco.mj_forward(model, data)
                        hits = []
                        for cc in data.contact:
                            if cc.dist >= -.0002:
                                continue
                            a, b = [model.geom(int(g)).name for g in cc.geom]
                            if 'ground' in (a, b):
                                other = b if a == 'ground' else a
                                if 'sole_pad' in other or part_lookup.get(other, '').endswith('_flexible_sole'):
                                    continue
                            hits.append(dict(part_a=part_lookup.get(a, a), part_b=part_lookup.get(b, b),
                                             depth_m=float(-cc.dist)))
                        endpoints.append(dict(jaw_angle_rad=angle, contacts=hits,
                                              endpoint_geometry_screen_pass=not hits))
                passed = bool(ik_pass and static and all(x['static_screen_pass'] for x in static)
                              and endpoints and all(x['endpoint_geometry_screen_pass'] for x in endpoints))
                record = dict(index=len(records), crouch_drop_mm=drop, target_grip_world_m=target.tolist(),
                              target_head_pitch_rad=pitch, joint_q_rad=q, root_position_m=root.tolist(),
                              actual_grip_world_m=grip.tolist(), grip_position_error_m=position_error,
                              head_pitch_error_rad=pitch_error, limit_violations=violations, ik_pass=ik_pass,
                              static_cases=static, jaw_endpoints=endpoints, finite_candidate_screen_pass=passed)
                records.append(record)
                print('GROUND CANDIDATE', record['index'], 'IK', ik_pass, 'finite screen', passed, flush=True)
            if not completed:
                break
        if not completed:
            break
    report = dict(schema='goose_native_pad_ground_pose_screen_v1', requested_candidates=36,
                  completed_candidates=len(records), finite_search_complete=completed and len(records) == 36,
                  passed_candidates=[x['index'] for x in records if x['finite_candidate_screen_pass']],
                  records=records, wall_seconds_after_model_load=time.monotonic()-started,
                  active_task_config_changed=False, architecture_changed=False, floor_pickup_pass=False,
                  continuous_path_pass=False, manufacturing_release=False, training_release=False,
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
                  limitations=['Bounded 36-candidate local least-squares screen; no global morphology/posture optimum is claimed.',
                               'Target is the actual closed-pad contact reference at15mm, not the old out-of-pad proxy.',
                               'Three discrete jaw endpoints and approximate convex contacts; no continuous swept CAD, cable or object approach check.',
                               'Static50g lump/50N opposed bite/±2N and declared mass uncertainty; no closed-loop balance, thermal or gait proof.',
                               'Finite candidates are not installed and do not alter the active task config or frozen scene identity.'])
    (R/'evidence/mechanical_grip_ground_pose_screen.json').write_text(json.dumps(report, indent=2)+'\n')
    print('GROUND FINITE SCREEN', len(records), '/36', 'passed', report['passed_candidates'], flush=True)
    return 0 if report['finite_search_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
