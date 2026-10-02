"""One bounded stand-to-floor-to-stand cycle; preserve failures, no tuning loop."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from sai_agent.goose.double_support import NominalDoubleSupport
from sai_agent.goose.native_linkage import set_passive_linkage
from sai_agent.goose.supported_manipulation import SupportedManipulation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--controller', choices=['uniform', 'contract'], default='contract')
    parser.add_argument('--path', choices=['initial', 'constant_pitch'], default='initial')
    args = parser.parse_args()
    source = ROBOT/'models/tip_grip_physics/robot.xml'
    paths = [source, ROBOT/'configs/tip_grip_physics_contract.json',
             ROBOT/'evidence/tip_grip_finite_reach.json',
             ROBOT/'evidence/body_bay_mechanical_parameters.json',
             ROBOT/'evidence/tip_grip_floor_object_geometry.json']
    contract, reach, ledger, object_spec = [json.loads(p.read_text()) for p in paths[1:]]
    for record in [contract, reach, object_spec]:
        for relative, expected in record['source_hashes'].items():
            if sha(ROOT/relative) != expected:
                raise ValueError(('stale source', relative))
    tree = ET.parse(source).getroot()
    for mesh in tree.find('asset').findall('mesh'):
        mesh.set('file', str((source.parent/mesh.get('file')).resolve()))
    center = np.array(object_spec['object_center_world_m'])
    size = np.array(object_spec['object_size_m'])
    mass = object_spec['object_mass_kg']
    obj = ET.SubElement(tree.find('worldbody'), 'body', name='floor_50g_object',
                        pos=' '.join(map(str, center)))
    ET.SubElement(obj, 'freejoint', name='object_root')
    diagonal = mass*(sum(size**2)-size**2)/12
    ET.SubElement(obj, 'inertial', mass=str(mass), pos='0 0 0',
                  diaginertia=' '.join(map(str, diagonal)))
    ET.SubElement(obj, 'geom', name='floor_50g_object', type='box',
                  size=' '.join(map(str, size/2)), density='0', contype='2',
                  conaffinity='3', friction='.65 .01 .002', solref='.005 1')
    xml = ET.tostring(tree, encoding='unicode')
    run_name = 'supported_manipulation_cycle_'+args.controller+'_'+args.path
    out = ROOT/'artifacts/Goose_V0.1'/run_name
    out.mkdir(parents=True, exist_ok=True)
    (out/'task.xml').write_text(xml)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    names = contract['joint_order']
    qadr = np.array([model.joint(n).qposadr[0] for n in names])
    vadr = np.array([model.joint(n).dofadr[0] for n in names])
    aid = np.array([model.actuator(n+'_motor').id for n in names])
    limits = np.array([j['continuous_design_limit_nm'] for j in contract['joints']])
    speed = np.array([j['speed_limit_rad_s'] for j in contract['joints']])
    kp = np.array([j['kp_nm_rad'] for j in contract['joints']]) if args.controller == 'contract' else np.full(18, 80.)
    kd = np.array([j['kd_nm_s_rad'] for j in contract['joints']]) if args.controller == 'contract' else np.full(18, 4.)
    jaw = names.index('beak_hinge')
    helper = NominalDoubleSupport(contract, ledger['contact_center_y_m'], ledger['contact_hulls'])
    crouch = np.array([reach['selected_candidate']['q_rad'][n] for n in names])
    front = np.array(contract['front_contact_native_world_m'])+[0., 0., ledger['rigid_coordinate_lift_m']]
    reference = SupportedManipulation(helper, contract, crouch, front,
                                      reach['selected_candidate']['actual_front_contact_world_m'], args.path)
    # Reject unreachable references before spending time on dynamics. Use
    # perfect encoders only for this separate, explicitly nominal preflight.
    preflight_q = reference.stand.copy()
    preflight_max_residual, preflight_peak_speed = 0., np.zeros(18)
    for t in np.arange(0., reference.duration_s, .020):
        trial, note = reference.reference_at(t, preflight_q, [1., 0., 0., 0.])
        preflight_max_residual = max(preflight_max_residual, note['ik_weighted_residual_m'])
        preflight_peak_speed = np.maximum(preflight_peak_speed, abs(trial-preflight_q)/.020)
        preflight_q = trial
    reference.q_neck[:] = 0.
    preflight = dict(maximum_ik_weighted_residual_m=preflight_max_residual,
        peak_reference_joint_speed_rad_s=dict(zip(names, preflight_peak_speed.tolist())),
        pass_=bool(preflight_max_residual < .001 and np.all(preflight_peak_speed <= speed)))
    (out/'reference_preflight.json').write_text(json.dumps(preflight, indent=2)+'\n')
    if not preflight['pass_']:
        raise ValueError(('nominal IK/speed preflight rejected path', preflight))
    data.qpos[3:7] = [1., 0., 0., 0.]
    data.qpos[qadr[jaw]] = .30
    set_passive_linkage(model, data, contract)
    mujoco.mj_forward(model, data)
    oid, torso = model.body('floor_50g_object').id, model.body('torso').id
    lookup = {g['name']:g['part'] for g in contract['collision_geometries']}
    pads = {'upper_grip_cassette_pad', 'lower_grip_cassette_pad'}
    corners = np.array([[x, y, z] for x in [-1, 1] for y in [-1, 1] for z in [-1, 1]])*size/2
    commanded = data.qpos[qadr].copy()
    state, previous_state = commanded.copy(), commanded.copy()
    desired_velocity = np.zeros(len(names))
    segment_start = state.copy()
    control_steps = round(.005/model.opt.timestep)
    reference_steps = round(.020/model.opt.timestep)
    sample_steps = round(.010/model.opt.timestep)
    if abs(control_steps*model.opt.timestep-.005) > 1e-12:
        raise ValueError('physics timestep must divide the 200 Hz control cycle')
    metadata = {}
    peak, max_speed = np.zeros(18), np.zeros(18)
    clips = np.zeros(18, dtype=int)
    max_tilt, worst_ik, min_margin = 0., 0., float('inf')
    infeasible_support_ticks = 0
    records, frames, phases = [], [], []
    collision_samples = {}
    status = 'FULL_DURATION'
    started = time.monotonic()
    for step in range(int(np.ceil(reference.duration_s/model.opt.timestep))):
        if step % reference_steps == 0:
            # Root orientation is an ideal IMU input. Translation, actual
            # object motion and contact forces are never controller inputs.
            commanded, metadata = reference.reference_at(data.time, data.qpos[qadr], data.qpos[3:7])
            segment_start[:] = state
            worst_ik = max(worst_ik, metadata['ik_weighted_residual_m'])
            if not phases or phases[-1]['phase'] != metadata['phase']:
                phases.append(dict(phase=metadata['phase'], start_time_s=float(data.time)))
                print('PHASE', metadata['phase'], round(data.time, 4), flush=True)
        if step % control_steps == 0:
            previous_state[:] = state
            fraction = (step % reference_steps+control_steps)/reference_steps
            interpolated = segment_start*(1-fraction)+commanded*fraction
            state += np.clip(interpolated-state, -speed*.005, speed*.005)
            desired_velocity[:] = (state-previous_state)/.005
            estimate = helper.estimate(data.qpos[qadr], data.qpos[3:7],
                metadata['declared_payload_kg'], front)
            min_margin = min(min_margin, *(c['edge_margin_m'] for c in estimate['contacts']))
            infeasible_support_ticks += not estimate['nominal_support_feasible']
            tau = kp*(state-data.qpos[qadr])+kd*(desired_velocity-data.qvel[vadr])+estimate['torque_nm']
            if metadata['grip_velocity_control']:
                jaw_feedback = np.clip(2.*(-.15-data.qvel[vadr[jaw]]), -.6, .6)
            else:
                jaw_feedback = 2.*(.30-data.qpos[qadr[jaw]])-.3*data.qvel[vadr[jaw]]
            tau[jaw] = jaw_feedback+estimate['torque_nm'][jaw]
            clips += abs(tau) > limits
            data.ctrl[aid] = np.clip(tau, -limits, limits)
            peak = np.maximum(peak, abs(data.ctrl[aid]))
        mujoco.mj_step(model, data)
        max_speed = np.maximum(max_speed, abs(data.qvel[vadr]))
        if not np.isfinite(data.qpos).all() or any(int(w.number) for w in data.warning):
            status = 'SOLVER_WARNING_OR_NONFINITE'
            break
        tilt = float(np.arccos(np.clip(data.xmat[torso].reshape(3, 3)[2, 2], -1., 1.)))
        max_tilt = max(max_tilt, tilt)
        if tilt > np.deg2rad(20.):
            status = 'ROOT_TILT_REJECTION'
            break
        if step % sample_steps == 0:
            forces = {}
            for index, contact in enumerate(data.contact):
                a, b = [model.geom(int(g)).name for g in contact.geom]
                if 'floor_50g_object' in (a, b):
                    other = b if a == 'floor_50g_object' else a
                    force = np.zeros(6)
                    mujoco.mj_contactForce(model, data, index, force)
                    part = lookup.get(other, other)
                    forces[part] = forces.get(part, 0.)+float(force[0])
                elif contact.dist < -.0002:
                    other = b if a == 'ground' else a
                    foot = 'ground' in (a, b) and ('sole_pad' in other or lookup.get(other, '').endswith('_flexible_sole'))
                    if foot:
                        continue
                    parts = sorted([lookup.get(a, a), lookup.get(b, b)])
                    pair = '|'.join(parts)
                    if pair not in collision_samples or -contact.dist > collision_samples[pair]['convex_penetration_m']:
                        poses = {}
                        for geom in contact.geom:
                            bid = int(model.geom(int(geom)).bodyid[0])
                            poses[model.body(bid).name] = dict(position_world_m=data.xpos[bid].tolist(),
                                rotation_world=data.xmat[bid].reshape(3, 3).tolist())
                        collision_samples[pair] = dict(parts=parts, phase=metadata['phase'],
                            time_s=float(data.time-model.opt.timestep), convex_penetration_m=float(-contact.dist),
                            native_body_poses=poses)
            minimum_z = float((corners@data.xmat[oid].reshape(3, 3).T+data.xpos[oid])[:, 2].min())
            two_pads = pads <= {part for part, force in forces.items() if force > .05}
            records.append(dict(time_s=float(data.time), phase=metadata['phase'],
                object_com_world_m=data.xpos[oid].tolist(), object_min_z_m=minimum_z,
                object_speed_m_s=float(np.linalg.norm(data.qvel[model.joint('object_root').dofadr[0]:
                    model.joint('object_root').dofadr[0]+3])),
                object_normal_contact_n_by_part=forces, two_actual_pad_contacts=two_pads,
                root_tilt_rad=tilt, jaw_q_rad=float(data.qpos[qadr[jaw]])))
        if step % (sample_steps*10) == 0:
            frames.append((float(data.time), data.qpos.copy()))
        if time.monotonic()-started > 420.:
            status = 'WALL_TIME_BOUND'
            break
    warnings = [int(w.number) for w in data.warning]
    phase_records = {name:[r for r in records if r['phase'] == name] for name, _ in reference.phases}
    held = phase_records['carry_hold']
    lifted = bool(held and all(r['two_actual_pad_contacts'] and r['object_min_z_m'] > .025
                     and r['object_normal_contact_n_by_part'].get('ground', 0.) < .05 for r in held))
    final = records[-1] if records else {}
    settled_on_floor = bool(final.get('phase') == 'final_settle' and not final.get('two_actual_pad_contacts')
        and abs(final.get('object_min_z_m', 1.)) < .001
        and final.get('object_speed_m_s', 1.) < .02
        and final.get('object_normal_contact_n_by_part', {}).get('ground', 0.) > .05)
    placed = phase_records['place']
    remained_held_into_place = bool(placed and placed[0]['two_actual_pad_contacts'])
    premature_drops = [row for row in placed if not row['two_actual_pad_contacts']
        and row['object_min_z_m'] > .001 and row['object_normal_contact_n_by_part'].get('ground', 0.) < .05]
    returned = bool(lifted and remained_held_into_place and settled_on_floor and not premature_drops)
    full = status == 'FULL_DURATION' and data.time >= reference.duration_s-.001
    passed = bool(full and lifted and returned and not collision_samples and not any(warnings)
                  and max_tilt < np.deg2rad(10.) and np.all(max_speed <= speed)
                  and not np.any(clips) and not infeasible_support_ticks and worst_ik < .001)
    trajectory = out/'sampled_qpos.npz'
    np.savez_compressed(trajectory, time_s=np.array([t for t, q in frames]), qpos=np.array([q for t, q in frames]))
    paths += [Path(__file__), ROOT/'src/sai_agent/goose/double_support.py',
              ROOT/'src/sai_agent/goose/supported_manipulation.py', ROOT/'src/sai_agent/goose/low_reach.py']
    report = dict(schema='goose_supported_manipulation_cycle_v1', status=status,
        bounded_nominal_stand_pick_place_stand_pass=passed, lifted_during_hold=lifted,
        returned_to_floor_after_release=returned, object_settled_on_floor_at_end=settled_on_floor,
        remained_held_into_place=remained_held_into_place, simulated_seconds=float(data.time),
        premature_unheld_above_floor_place_samples=len(premature_drops),
        requested_seconds=reference.duration_s, wall_seconds=time.monotonic()-started,
        reference_phases_s=reference.phases, observed_phases=phases,
        object_mass_kg=mass, object_size_m=size.tolist(), initial_object_center_m=center.tolist(),
        torque_control_hz=200, reference_hz=50, physics_timestep_s=model.opt.timestep,
        controller_profile=args.controller, path_profile=args.path, nominal_reference_preflight=preflight,
        reference_interpolated_between_50hz_ticks=True, pd_kp_nm_rad=dict(zip(names, kp.tolist())),
        pd_kd_nm_s_rad=dict(zip(names, kd.tolist())), jaw_velocity_target_rad_s=-.15,
        jaw_feedback_cap_nm=.6, maximum_root_tilt_rad=max_tilt,
        worst_ik_weighted_residual_m=worst_ik, minimum_nominal_foot_margin_m=min_margin,
        nominal_support_infeasible_control_ticks=int(infeasible_support_ticks),
        continuous_torque_clipped_control_ticks=dict(zip(names, clips.tolist())),
        peak_motor_torque_nm=dict(zip(names, peak.tolist())),
        peak_active_joint_speed_rad_s=dict(zip(names, max_speed.tolist())),
        declared_speed_limit_rad_s=dict(zip(names, speed.tolist())), solver_warnings=warnings,
        nonobject_contact_native_pose_samples=list(collision_samples.values()), records=records, final=final,
        root_clamped=False, object_clamped=False, root_force_applied=False, object_force_applied=False,
        contact_truth_used_by_controller=False, root_translation_truth_used_by_controller=False,
        ideal_encoders_and_imu=True, ground_friction_assumption=.65,
        training_release=False, manufacturing_release=False, arbitrary_item_pickup_pass=False,
        sampled_qpos_sha256=sha(trajectory), sampled_qpos_frames=len(frames),
        task_xml_sha256=hashlib.sha256(xml.encode()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},
        limitations=['One finite nominal flat-floor cycle with draft fixed gains, ideal encoders/IMU and no-slip foot-anchor assumption.',
            'Control consumes no measured foot force or object pose; known nominal payload is introduced by scheduled phase, not grasp detection.',
            'Any observed convex collision candidate prevents pass pending native confirmation; no contact exclusions were added.',
            'No hardware timing, quantization, backlash, thermal test, gait, turning, drag or arbitrary-object perception is proven.'])
    (ROBOT/'evidence'/(run_name+'.json')).write_text(json.dumps(report, indent=2)+'\n')
    print('CYCLE', status, 'PASS', passed, 'LIFT', lifted, 'RETURN', returned,
          'TILT_DEG', np.rad2deg(max_tilt), 'COLLISION_CANDIDATES', len(collision_samples), flush=True)


if __name__ == '__main__':
    main()
