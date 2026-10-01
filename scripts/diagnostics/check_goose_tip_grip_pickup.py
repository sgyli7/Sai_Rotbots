"""One bounded free-root floor-grasp/lift rejection trial; no PPO or tuning loop."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys
import time
import xml.etree.ElementTree as ET

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
    parser = argparse.ArgumentParser()
    parser.add_argument('--lift-mm', type=int, choices=[50, 80], default=50)
    parser.add_argument('--capture-native-contacts', action='store_true')
    args = parser.parse_args()
    lift_m = args.lift_mm/1000.
    source = R/'models/tip_grip_physics/robot.xml'
    paths = [source, R/'configs/tip_grip_physics_contract.json', R/'evidence/tip_grip_finite_reach.json',
             R/'evidence/body_bay_mechanical_parameters.json', R/'evidence/tip_grip_floor_object_geometry.json']
    contract, reach, ledger, approach = [json.loads(p.read_text()) for p in paths[1:]]
    for info in [contract, reach, approach]:
        for relative, expected in info['source_hashes'].items():
            if sha(ROOT/relative) != expected:
                raise ValueError(('stale source', relative))
    if not reach['selected_native_floor_pass']:
        raise ValueError('native floor pose required')
    pose = reach['selected_candidate']
    center = np.array(approach['object_center_world_m'])
    size = np.array(approach['object_size_m'])
    mass = approach['object_mass_kg']
    tree = ET.parse(source).getroot()
    for mesh in tree.find('asset').findall('mesh'):
        mesh.set('file', str((source.parent/mesh.get('file')).resolve()))
    obj = ET.SubElement(tree.find('worldbody'), 'body', name='floor_50g_object', pos=' '.join(map(str, center)))
    ET.SubElement(obj, 'freejoint', name='object_root')
    diagonal = mass*(sum(size**2)-size**2)/12
    ET.SubElement(obj, 'inertial', mass=str(mass), pos='0 0 0', diaginertia=' '.join(map(str, diagonal)))
    ET.SubElement(obj, 'geom', name='floor_50g_object', type='box', size=' '.join(map(str, size/2)),
                  density='0', contype='2', conaffinity='3', friction='.65 .01 .002', solref='.005 1')
    xml = ET.tostring(tree, encoding='unicode')
    suffix = '_contact_probe' if args.capture_native_contacts else ''
    out = ROOT/'artifacts/Goose_V0.1'/('tip_grip_pickup_'+str(args.lift_mm)+'mm'+suffix)
    out.mkdir(parents=True, exist_ok=True)
    (out/'task.xml').write_text(xml)
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    names = contract['joint_order']
    qadr = np.array([m.joint(n).qposadr[0] for n in names])
    vadr = np.array([m.joint(n).dofadr[0] for n in names])
    aid = np.array([m.actuator(n+'_motor').id for n in names])
    limits = np.array([j['continuous_design_limit_nm'] for j in contract['joints']])
    speed = np.array([j['speed_limit_rad_s'] for j in contract['joints']])
    beak = names.index('beak_hinge')
    desired = np.array([pose['q_rad'][n] for n in names])
    desired[beak] = .30
    d.qpos[:3] = pose['root_position_m']
    d.qpos[3:7] = [1, 0, 0, 0]
    d.qpos[qadr] = desired
    set_passive_linkage(m, d, contract)
    mujoco.mj_forward(m, d)
    lookup = {g['name']: g['part'] for g in contract['collision_geometries']}
    initial = []
    for cc in d.contact:
        a, b = [m.geom(int(g)).name for g in cc.geom]
        if 'floor_50g_object' in (a, b):
            initial.append(dict(a=a, b=b, penetration_m=max(0., float(-cc.dist))))
    if max((c['penetration_m'] for c in initial), default=0.) > .0002:
        raise ValueError('Initial object penetration; no dynamics run')
    system = candidate()
    system.pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
    reference = np.array(contract['front_contact_native_world_m']) + [0., 0., ledger['rigid_coordinate_lift_m']]
    neck = ['neck_pitch', 'neck_mid_pitch', 'head_pitch']
    neck_index = [names.index(n) for n in neck]
    joints = {j['name']: j for j in contract['joints']}
    bounds = np.array([joints[n]['range_rad'] for n in neck])
    target = np.array(pose['actual_front_contact_world_m'])+[0., 0., lift_m]

    def point_at(angles):
        q = dict(pose['q_rad'])
        q.update(zip(neck, angles))
        fk, _ = system.fk(q, root_p=np.array(pose['root_position_m']))
        return system.point(fk, 'head_roll', reference)

    def residual(angles):
        return np.r_[(point_at(angles)-target)[[0, 2]], .1*(sum(angles)-pose['head_pitch_target_rad'])]

    solve = least_squares(residual, desired[neck_index], bounds=(bounds[:, 0], bounds[:, 1]), max_nfev=80)
    if np.linalg.norm(point_at(solve.x)-target) > .001:
        raise ValueError('Lift endpoint IK failed')
    final_target = desired.copy()
    final_target[neck_index] = solve.x
    kit_path = R/'cad/exports/tip_grip_candidate/manifest.json'
    paths.append(kit_path)
    kit = json.loads(kit_path.read_text())
    native_parts = {p['name']: p for p in kit['parts']}
    system.items = copy.deepcopy(ledger['items'])
    for item in system.items:
        if item['name'] in native_parts:
            p = native_parts[item['name']]
            item.update(mass_kg=p['mass_kg'],
                center_m=(np.array(p['center_of_mass_world_m'])+[0., 0., ledger['rigid_coordinate_lift_m']]).tolist(),
                inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'])
        elif item['name'] == 'specified_payload_50g':
            item['center_m'] = reference.tolist()
    system.grip = reference
    system.contact_hulls = {n: ConvexHull(np.array(v)) for n, v in ledger['contact_hulls'].items()}
    system.contact_center_y_m = ledger['contact_center_y_m']
    endpoint_q = dict(pose['q_rad'])
    endpoint_q.update(zip(neck, solve.x.tolist()))
    endpoint_fk, axes = system.fk(endpoint_q, root_p=np.array(pose['root_position_m']))
    endpoint_grip = system.point(endpoint_fk, 'head_roll', reference)
    normal = endpoint_fk['head_roll'][1]@np.array([0., 0., 1.])
    correction = 30.*float(axes['beak_hinge']@np.cross(endpoint_grip-endpoint_fk['beak_hinge'][0], normal))
    endpoint_static = []
    for variant in [-1, 0, 1]:
        static_model = system.model(variant)[0]
        for drag in [-2., 0., 2.]:
            result = system.evaluate('tip_grip_lift_endpoint', endpoint_q, np.array(pose['root_position_m']),
                np.eye(3), ['right', 'left'], variant, drag, static_model)
            torque = dict(result['joint_torque_nm'])
            torque['beak_hinge'] -= correction
            overload = [n for n in names if abs(torque[n]) > joints[n]['continuous_design_limit_nm']]
            endpoint_static.append(dict(mass_variant=variant, drag_x_n=drag, tip_clamp_n=20.,
                joint_torque_nm=torque, overloaded_axes=overload,
                contact_wrench_feasible=result['static_contact_feasible'],
                minimum_foot_edge_margin_m=min(c['edge_margin_m'] for c in result['contacts']),
                static_screen_pass=result['static_contact_feasible'] and not overload))
    if not all(c['static_screen_pass'] for c in endpoint_static):
        raise ValueError(('Lift endpoint static gate failed', endpoint_static))
    oid = m.body('floor_50g_object').id
    torso = m.body('torso').id
    head = m.body('head_roll').id
    projected = [(int(m.joint(j['name']).dofadr[0]), j['mimic_multiplier']) for j in contract['passive_linkage_joints']]
    duration = 2.2
    started = time.monotonic()
    records = []
    peak = np.zeros(18)
    clips = np.zeros(18, dtype=int)
    peak_speed = np.zeros(18)
    nonobject_hits = {}
    contact_pose_samples = []
    frames = []
    max_tilt = 0.
    reason = 'FULL_DURATION'
    target_state = desired.copy()
    pad_names = {'upper_grip_cassette_pad', 'lower_grip_cassette_pad'}
    confirmed_grip_before_lift = False
    corners = np.array([[x, y, z] for x in [-1, 1] for y in [-1, 1] for z in [-1, 1]])*size/2
    for k in range(int(np.ceil(duration/m.opt.timestep))):
        mujoco.mj_forward(m, d)
        fraction = np.clip((d.time-1.2)/.6, 0., 1.)
        blend = fraction*fraction*(3.-2.*fraction)
        commanded = desired*(1-blend)+final_target*blend
        target_state += np.clip(commanded-target_state, -speed*m.opt.timestep, speed*m.opt.timestep)
        tau = 80*(target_state-d.qpos[qadr])-4*d.qvel[vadr]+d.qfrc_bias[vadr]
        jaw_bias = d.qfrc_bias[vadr[beak]]+sum(mult*d.qfrc_bias[index] for index, mult in projected)
        if d.time < .2:
            jaw_command = 2.*(.30-d.qpos[qadr[beak]])-.3*d.qvel[vadr[beak]]
        else:
            jaw_command = np.clip(2.*(-.15-d.qvel[vadr[beak]]), -.6, .6)
        tau[beak] = jaw_command+jaw_bias
        clips += abs(tau) > limits
        tau = np.clip(tau, -limits, limits)
        peak = np.maximum(peak, abs(tau))
        d.ctrl[aid] = tau
        mujoco.mj_step(m, d)
        peak_speed = np.maximum(peak_speed, abs(d.qvel[vadr]))
        if not np.isfinite(d.qpos).all() or any(int(w.number) for w in d.warning):
            reason = 'SOLVER_WARNING_OR_NONFINITE'
            break
        tilt = float(np.arccos(np.clip(d.xmat[torso].reshape(3, 3)[2, 2], -1., 1.)))
        max_tilt = max(max_tilt, tilt)
        if tilt > np.deg2rad(20):
            reason = 'ROOT_TILT_REJECTION'
            break
        if k % 100 == 0:
            forces = {}
            contact_sample_pairs = {}
            for index, cc in enumerate(d.contact):
                a, b = [m.geom(int(g)).name for g in cc.geom]
                if 'floor_50g_object' not in (a, b):
                    if cc.dist < -.0002:
                        other = b if a == 'ground' else a
                        allowed_foot = 'ground' in (a, b) and ('sole_pad' in other or lookup.get(other, '').endswith('_flexible_sole'))
                        if not allowed_foot:
                            pair = '|'.join(sorted([lookup.get(a, a), lookup.get(b, b)]))
                            nonobject_hits[pair] = max(nonobject_hits.get(pair, 0.), float(-cc.dist))
                            if args.capture_native_contacts and pair not in contact_sample_pairs:
                                poses = {}
                                for geom_id in cc.geom:
                                    body_id = int(m.geom(int(geom_id)).bodyid[0])
                                    body_name = m.body(body_id).name
                                    poses[body_name] = dict(position_world_m=d.xpos[body_id].tolist(),
                                        rotation_world=d.xmat[body_id].reshape(3, 3).tolist())
                                contact_sample_pairs[pair] = dict(pair=pair,
                                    parts=[lookup.get(a, a), lookup.get(b, b)], native_body_poses=poses,
                                    state_time_s=float(d.time-m.opt.timestep), convex_penetration_m=float(-cc.dist))
                            elif args.capture_native_contacts and pair in contact_sample_pairs:
                                contact_sample_pairs[pair]['convex_penetration_m'] = max(
                                    contact_sample_pairs[pair]['convex_penetration_m'], float(-cc.dist))
                    continue
                other = b if a == 'floor_50g_object' else a
                part = lookup.get(other, other)
                force = np.zeros(6)
                mujoco.mj_contactForce(m, d, index, force)
                forces[part] = forces.get(part, 0.)+float(force[0])
            contact_pose_samples.extend(contact_sample_pairs.values())
            obj_r = d.xmat[oid].reshape(3, 3)
            minimum_z = float((corners@obj_r.T+d.xpos[oid])[:, 2].min())
            local = d.xmat[head].reshape(3, 3).T@(d.xpos[oid]-d.xpos[head])+system.pivots['head_roll']
            grip = pad_names <= {n for n, force in forces.items() if force > .05}
            if grip and .2 < d.time < 1.2:
                confirmed_grip_before_lift = True
            records.append(dict(time_s=float(d.time), jaw_q_rad=float(d.qpos[qadr[beak]]),
                                object_com_world_m=d.xpos[oid].tolist(), object_min_z_m=minimum_z,
                                object_com_head_neutral_m=local.tolist(), root_tilt_rad=tilt,
                                object_normal_contact_n_by_part=forces, two_actual_pad_contacts=grip,
                                nominal_lift_blend=float(blend)))
        if k % 2000 == 0:
            frames.append((float(d.time), d.qpos.copy()))
        if time.monotonic()-started > 55.:
            reason = 'WALL_TIME_BOUND'
            break
    warning = [int(w.number) for w in d.warning]
    final = records[-1] if records else {}
    full = reason == 'FULL_DURATION' and d.time >= duration-.001
    other_contact = {n: f for n, f in final.get('object_normal_contact_n_by_part', {}).items()
                     if n not in pad_names and f > .05}
    passed = bool(full and not any(warning) and confirmed_grip_before_lift
                  and final.get('two_actual_pad_contacts') and final.get('object_min_z_m', -1) > .025
                  and not other_contact and not nonobject_hits and max_tilt < np.deg2rad(10)
                  and np.all(peak_speed <= speed))
    trajectory = out/'sampled_qpos.npz'
    np.savez_compressed(trajectory, time_s=np.array([t for t, q in frames]),
                        qpos=np.array([q for t, q in frames]))
    report = dict(schema='goose_tip_grip_floor_pickup_rejection_v1', status=reason,
        bounded_specified_block_floor_grasp_lift_pass=passed, simulated_seconds=float(d.time),
        wall_seconds=time.monotonic()-started, object_size_m=size.tolist(), object_mass_kg=mass,
        initial_object_center_m=center.tolist(), initial_object_contacts=initial,
        actual_pads_contacted_before_lift=confirmed_grip_before_lift,
        final_nonpad_object_normal_contacts_n=other_contact,
        maximum_root_tilt_rad=max_tilt, final=final, records=records,
        nominal_lift_endpoint_static_cases=endpoint_static,
        observed_nonobject_collision_candidates_max_depth_m=nonobject_hits,
        nonobject_contact_native_pose_samples=contact_pose_samples,
        peak_active_joint_speed_rad_s=dict(zip(names, peak_speed.tolist())),
        declared_speed_limit_rad_s=dict(zip(names, speed.tolist())),
        sampled_qpos_sha256=sha(trajectory), sampled_qpos_frames=len(frames),
        solver_warnings=warning, continuous_torque_clipped_steps=dict(zip(names, clips.tolist())),
        peak_motor_torque_nm=dict(zip(names, peak.tolist())),
        jaw_velocity_target_rad_s=-.15, jaw_feedback_cap_nm=.6, nominal_head_lift_m=lift_m,
        root_clamped=False, object_clamped=False, root_force_applied=False, object_force_applied=False,
        object_starts_on_floor=True, object_starts_between_closed_pads=False,
        approach_from_standing_pass=False, release_return_pass=False, arbitrary_item_pickup_pass=False,
        floor_pickup_release=False, training_release=False, manufacturing_release=False,
        task_xml_sha256=hashlib.sha256(xml.encode()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
        limitations=['One2.2s nominal fixed-gain free-root trial; no PPO, tuning sweep, perturbation or thermal proof.',
          'Robot starts in a separately screened floor reach pose, not a standing-to-floor approach sequence.',
          '0.65 friction and sole/contact compliance are assumed; contact forces are simulated, not calibrated hardware.',
          'Ideal jaw passive constraints and model gravity feedforward; no backlash, electronics or hardware bandwidth test.',
          'Any nonpad final support invalidates this soft-pad lift criterion. No daily-item drag or gait is inferred.'])
    evidence_name = ('tip_grip_floor_pickup_rejection.json' if args.lift_mm == 50 else 'tip_grip_floor_pickup_80mm.json')
    if args.capture_native_contacts:
        evidence_name = 'tip_grip_floor_pickup_'+str(args.lift_mm)+'mm_contact_probe.json'
    (R/'evidence'/evidence_name).write_text(json.dumps(report, indent=2)+'\n')
    print('TIP PICKUP', reason, 'pass', passed, 'seconds', d.time, 'final', final, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
