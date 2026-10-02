"""Two finite free-root low-pose trials, isolating leg support feedforward.

Same geometry, joints, gains and continuous torque limits. Compare gravity
bias alone against nominal static gravity-minus-foot-wrench leg torques.
No root forces, pose clamp, object assistance, PPO or gain search.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time

import mujoco
import numpy as np
from build123d import import_brep
from scipy.spatial import ConvexHull

from sai_agent.goose.native_linkage import set_passive_linkage

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/models'), str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'configs/tip_grip_physics_contract.json', R/'models/tip_grip_physics/robot.xml',
             R/'evidence/body_bay_mechanical_parameters.json', R/'evidence/tip_grip_finite_reach.json',
             R/'cad/exports/tip_grip_candidate/manifest.json']
    contract, ledger, reach, kit = [json.loads(paths[i].read_text()) for i in [0, 2, 3, 4]]
    for data in [contract, reach]:
        for relative, expected in data['source_hashes'].items():
            if sha(ROOT/relative) != expected:
                raise ValueError(('stale input', relative))
    assert sha(paths[1]) == contract['model_sha256']
    pose = reach['selected_candidate']
    system = candidate()
    system.pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    system.grip = np.array(contract['front_contact_native_world_m'])+lift
    system.items = [copy.deepcopy(i) for i in ledger['items'] if i['name'] != 'specified_payload_50g']
    parts = {p['name']: p for p in kit['parts']}
    for item in system.items:
        if item['name'] in parts:
            p = parts[item['name']]
            item.update(mass_kg=p['mass_kg'], center_m=(np.array(p['center_of_mass_world_m'])+lift).tolist(),
                        inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'])
    system.contact_hulls = {n: ConvexHull(np.array(v)) for n, v in ledger['contact_hulls'].items()}
    system.contact_center_y_m = ledger['contact_center_y_m']
    q = dict(pose['q_rad'])
    q['beak_hinge'] = .30
    static_model = system.model(0)[0]
    static = system.evaluate('bare_low_support', q, np.array(pose['root_position_m']),
                            np.eye(3), ['right', 'left'], 0, 0., static_model)
    # The helper's opposed bite pair cancels identically at every leg axis.
    # Only twelve leg entries are used; the beak/head values are not used.
    assert static['static_contact_feasible']
    m = mujoco.MjModel.from_xml_path(str(paths[1]))
    names = contract['joint_order']
    qadr = np.array([m.joint(n).qposadr[0] for n in names])
    vadr = np.array([m.joint(n).dofadr[0] for n in names])
    aid = np.array([m.actuator(n+'_motor').id for n in names])
    continuous = np.array([j['continuous_design_limit_nm'] for j in contract['joints']])
    speed = np.array([j['speed_limit_rad_s'] for j in contract['joints']])
    desired = np.array([q[n] for n in names])
    legs = np.array([i for i, n in enumerate(names) if n.startswith(('right_', 'left_'))])
    static_tau = np.array([static['joint_torque_nm'][n] for n in names])
    assert np.all(abs(static_tau[legs]) <= continuous[legs])
    beak = names.index('beak_hinge')
    projected = [(int(m.joint(j['name']).dofadr[0]), j['mimic_multiplier']) for j in contract['passive_linkage_joints']]
    lookup = {g['name']: g['part'] for g in contract['collision_geometries']}
    floor = box([2000., 2000., 500.], [0., 0., -250.])
    source = R/parts['upper_grip_shell']['files']['brep']['path']
    assert sha(source) == parts['upper_grip_shell']['files']['brep']['sha256']
    upper = import_brep(source)
    paths.append(source)
    cases = []
    for mode in ['gravity_bias_only', 'static_foot_support']:
        d = mujoco.MjData(m)
        d.qpos[:3] = pose['root_position_m']
        d.qpos[3:7] = [1, 0, 0, 0]
        d.qpos[qadr] = desired
        set_passive_linkage(m, d, contract)
        started = time.monotonic()
        max_tilt, max_hit = 0., 0.
        worst_pose = None
        samples = []
        peak, peak_speed = np.zeros(18), np.zeros(18)
        clips = np.zeros(18, dtype=int)
        reason = 'FULL_DURATION'
        for k in range(int(np.ceil(.8/m.opt.timestep))):
            mujoco.mj_forward(m, d)
            feedforward = d.qfrc_bias[vadr].copy()
            if mode == 'static_foot_support':
                feedforward[legs] = static_tau[legs]
            tau = 80*(desired-d.qpos[qadr])-4*d.qvel[vadr]+feedforward
            jaw_bias = d.qfrc_bias[vadr[beak]]+sum(mult*d.qfrc_bias[index] for index, mult in projected)
            tau[beak] = 2*(.30-d.qpos[qadr[beak]])-.3*d.qvel[vadr[beak]]+jaw_bias
            clips += abs(tau) > continuous
            tau = np.clip(tau, -continuous, continuous)
            peak = np.maximum(peak, abs(tau))
            d.ctrl[aid] = tau
            mujoco.mj_step(m, d)
            peak_speed = np.maximum(peak_speed, abs(d.qvel[vadr]))
            if not np.isfinite(d.qpos).all() or any(int(w.number) for w in d.warning):
                reason = 'SOLVER_WARNING'
                break
            tilt = float(np.arccos(np.clip(d.xmat[m.body('torso').id].reshape(3, 3)[2, 2], -1., 1.)))
            max_tilt = max(max_tilt, tilt)
            if k % 100 == 0:
                hits = []
                for cc in d.contact:
                    if cc.dist >= -.0002:
                        continue
                    a, b = [m.geom(int(g)).name for g in cc.geom]
                    if 'ground' in (a, b):
                        other = b if a == 'ground' else a
                        if 'sole_pad' in other or lookup.get(other, '').endswith('_flexible_sole'):
                            continue
                    hits.append(dict(parts=[lookup.get(a, a), lookup.get(b, b)], depth_m=float(-cc.dist)))
                    if 'ground' in (a, b) and lookup.get(other) == 'upper_grip_shell' and -cc.dist > max_hit:
                        max_hit = float(-cc.dist)
                        head = m.body('head_roll').id
                        worst_pose = dict(position_world_m=d.xpos[head].tolist(),
                                          rotation_world=d.xmat[head].reshape(3, 3).tolist(),
                                          state_time_s=float(d.time-m.opt.timestep))
                samples.append(dict(time_s=float(d.time), root_tilt_rad=tilt,
                                    maximum_joint_error_rad=float(np.max(abs(d.qpos[qadr]-desired))), contacts=hits))
            if time.monotonic()-started > 30.:
                reason = 'WALL_TIME_BOUND'
                break
        native = None
        if worst_pose:
            rotation = np.array(worst_pose['rotation_world'])
            position = np.array(worst_pose['position_world_m'])
            moved = transform(upper, rotation, (position+rotation@(lift-system.pivots['head_roll']))*1000)
            native = bounded_common(moved, floor, 3.)
        warning = [int(w.number) for w in d.warning]
        complete = reason == 'FULL_DURATION' and d.time >= .799
        passed = bool(complete and not any(warning) and not any(s['contacts'] for s in samples)
                      and max_tilt < np.deg2rad(2) and np.all(peak_speed <= speed)
                      and samples[-1]['maximum_joint_error_rad'] < .08)
        cases.append(dict(mode=mode, status=reason, limited_bare_low_pose_pass=passed,
            simulated_seconds=float(d.time), wall_seconds=time.monotonic()-started,
            maximum_root_tilt_rad=max_tilt, sampled_maximum_upper_shell_floor_penetration_m=max_hit,
            captured_peak_upper_pose=worst_pose, peak_native_floor_common=native,
            peak_motor_torque_nm=dict(zip(names, peak.tolist())),
            peak_joint_speed_rad_s=dict(zip(names, peak_speed.tolist())),
            clipped_step_counts=dict(zip(names, clips.tolist())), solver_warnings=warning, samples=samples))
        print('LOW SUPPORT', mode, 'pass', passed, 'max tilt deg', np.rad2deg(max_tilt), 'native', native, flush=True)
    report = dict(schema='goose_low_pose_support_feedforward_v1', cases=cases,
        declared_nominal_support_joint_torque_nm={names[i]:float(static_tau[i]) for i in legs},
        static_ground_wrench=static['contacts'], nominal_bare_mass_kg=sum(i['mass_kg'] for i in system.items),
        root_clamped=False, root_force_applied=False, object_present=False,
        kp_nm_rad=80., kd_nm_s_rad=4., duration_per_case_s=.8, wall_bound_per_case_s=30.,
        geometry_changed=False, drive_limits_changed=False, physics_dt_changed=False,
        actual_floor_pickup_pass=False, manufacturing_release=False, training_release=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__),ROOT/'scripts/diagnostics/screen_goose_system_loads.py']},
        limitations=['Two nominal short bare-robot trials, not a gait, payload or robust terrain result.',
          'Nominal static contact wrench is scheduled feedforward, not measured force sensing or a closed-loop whole-body controller.',
          'Same fixed PD gains and operational limits; no parameter search, PPO or support force applied to root.',
          'Closed-pose static mass reduction for small jaw linkage; actual runtime passive linkage is retained.',
          'Only sampled collision candidates and the worst upper-shell/floor candidate receive the stated checks.'])
    (R/'evidence/low_pose_support_feedforward.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
