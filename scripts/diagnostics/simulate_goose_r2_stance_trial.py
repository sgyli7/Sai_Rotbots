"""Run a bounded MuJoCo stance trial for the pointed-beak exterior geometry.

This independent physics candidate shares the appearance landmarks and mass
screen, but its shell, contact and controller remain provisional. It must not
replace the released robot or be used as a walking/ground-grasp result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import trimesh

from check_goose_exterior_mass_screen import motor_and_component_items, printed_parts
from check_goose_exterior_reach import (YOKE, pitch_matrix, sampled_geometry, solve_pose,
                                         solve_seated_legs, tip_datum_from_mesh,
                                         pivots_from_manifest)


# Trial packaging hypothesis: move the roll shaft into the shoe, ahead of the
# pitch shaft. These are not released mounting coordinates.
ANKLE_ROLL_PIVOT = np.array([65.0, 0.0, 32.0])
TORQUE_NM = {'hip_yaw': .82, 'hip_roll': .82, 'hip_pitch': .82,
             'knee_pitch': .82, 'ankle_pitch': .82, 'ankle_roll': .82,
             'neck_lower_pitch': 2.12, 'neck_upper_pitch': 2.12,
             'head_pitch': .82}


def vec(values):
    return ' '.join(f'{float(x):.9g}' for x in values)


def locate_segments(items, ankle_roll_servo):
    groups = {'torso': [], 'neck_lower': [], 'neck_upper': [], 'head': []}
    for side in (-1, 1):
        for segment in ('thigh', 'shin', 'foot'):
            groups[f'{side}_{segment}'] = []
        if ankle_roll_servo != 'none':
            groups[f'{side}_foot_pitch'] = []
    for name, group, mass, center in items:
        if group != 'legs':
            key = {'lower': 'neck_lower', 'upper': 'neck_upper'}.get(group, group)
        else:
            side = 1 if center[1] > 0 else -1
            if name.startswith('leg_hip_'):
                key = 'torso'
            elif name.startswith(('thigh_', 'leg_knee_')):
                key = f'{side}_thigh'
            elif name.startswith('leg_ankle_roll_'):
                key = f'{side}_foot_pitch'
            elif name.startswith(('shin_', 'leg_ankle_')):
                key = f'{side}_shin'
            elif name.startswith('foot_'):
                key = f'{side}_foot'
            else:
                raise ValueError(f'Unallocated trial mass item: {name}')
        groups[key].append((name, mass, center))
    if any(not value for value in groups.values()):
        raise ValueError('Missing segment mass group')
    return groups


def inertial(body, origin_mm, items, appearance_dir):
    total = sum(m for _, m, _ in items)
    center = sum(m * p for _, m, p in items) / total
    inertia = np.zeros(3)
    for name, mass, position in items:
        mesh_path = appearance_dir / f'{name}.stl'
        dimensions = (trimesh.load_mesh(mesh_path).bounds[1]
                      - trimesh.load_mesh(mesh_path).bounds[0]) / 1000 if mesh_path.exists() else np.array([.04,.04,.04])
        dimensions = np.maximum(dimensions, .008)
        intrinsic = mass / 12 * np.array([
            dimensions[1] ** 2 + dimensions[2] ** 2,
            dimensions[0] ** 2 + dimensions[2] ** 2,
            dimensions[0] ** 2 + dimensions[1] ** 2,
        ])
        r = (position - center) / 1000
        inertia += intrinsic + mass * np.array([r[1]**2+r[2]**2,
                                               r[0]**2+r[2]**2,
                                               r[0]**2+r[1]**2])
    ET.SubElement(body, 'inertial', pos=vec((center-origin_mm)/1000),
                  mass=f'{total:.9g}', diaginertia=vec(inertia))


def joint(body, name, axis, limit, actuator):
    ET.SubElement(body, 'joint', name=name, axis=vec(axis), range=vec(limit),
                  damping='.03', armature='.00005')
    torque = TORQUE_NM[actuator]
    return name, torque


def make_model(directory, wall_mm, foot_shift_mm, heel_extension_mm,
               toe_shortening_mm,
               torque_scale, knee_servo, hip_pitch_servo, hip_roll_servo,
               ankle_pitch_servo, ankle_roll_servo,
               tip_datum, layout, body_scale_xyz, extra_torso_mass_kg, output):
    hip_axis, knee_axis, ankle_axis, root_axis, elbow_axis, yoke_axis = (
        layout[name] for name in ('hip', 'knee', 'ankle', 'root', 'elbow', 'yoke'))
    body_center = layout['body_center']
    items = (printed_parts(directory, wall_mm)
             + motor_and_component_items(Path.cwd(), layout))
    if extra_torso_mass_kg:
        items.append(('extra_torso_structure_reserve', 'torso',
                      extra_torso_mass_kg, body_center.copy()))
    upgraded = []
    for name,group,mass,center in items:
        if knee_servo == 'xm540' and name.startswith('leg_knee_'):
            mass = .165
        if hip_pitch_servo == 'xm540' and name.startswith('leg_hip_') and name.endswith('_2'):
            mass = .165
        if hip_roll_servo == 'xm540' and name.startswith('leg_hip_') and name.endswith('_1'):
            mass = .165
        if ankle_pitch_servo == 'xm540' and name.startswith('leg_ankle_'):
            mass = .165
        upgraded.append((name,group,mass,center))
    items = upgraded
    if ankle_roll_servo != 'none':
        for side in (-1, 1):
            items.append((f'leg_ankle_roll_{side}', 'legs', .082,
                          layout['ankle_roll'] + np.array([-17.0, side * 76.0, 0])))
    groups = locate_segments(items, ankle_roll_servo)
    xml = ET.Element('mujoco', model='goose_r2_stance_trial')
    ET.SubElement(xml, 'compiler', angle='radian', autolimits='true')
    ET.SubElement(xml, 'option', timestep='.001', gravity='0 0 -9.81',
                  integrator='implicitfast', iterations='80')
    world = ET.SubElement(xml, 'worldbody')
    ET.SubElement(world, 'geom', name='floor', type='plane', size='2 2 .1',
                  friction='.8 .005 .0001', rgba='.7 .7 .7 1')
    torso = ET.SubElement(world, 'body', name='torso', pos=vec(body_center/1000))
    ET.SubElement(torso, 'freejoint', name='root')
    inertial(torso, body_center, groups['torso'], directory)
    ET.SubElement(torso, 'geom', name='body_collision', type='ellipsoid',
                  size=vec(np.array([.175,.1025,.115]) * body_scale_xyz), mass='0',
                  rgba='.91 .9 .86 1')
    actuators = []
    for side in (-1, 1):
        label = 'left' if side == 1 else 'right'
        hip_point = hip_axis + np.array([0,side*88.0,0])
        knee_point = knee_axis + np.array([0,side*88.0,0])
        ankle_point = ankle_axis + np.array([0,side*88.0,0])
        thigh = ET.SubElement(torso, 'body', name=f'{label}_thigh',
                              pos=vec((hip_point-body_center)/1000))
        for suffix, axis, limit in [('hip_yaw',(0,0,1),(-.7,.7)),
                                    ('hip_roll',(1,0,0),(-.7,.7)),
                                    ('hip_pitch',(0,1,0),(-1.5,1.5))]:
            actuators.append(joint(thigh,f'{label}_{suffix}',axis,limit,suffix))
        inertial(thigh, hip_point, groups[f'{side}_thigh'], directory)
        ET.SubElement(thigh,'geom',name=f'{label}_thigh_link',type='capsule',
                      fromto=vec([0,0,0,*((knee_point-hip_point)/1000)]),
                      size='.019',mass='0',contype='0',conaffinity='0',rgba='.9 .9 .85 1')
        shin = ET.SubElement(thigh,'body',name=f'{label}_shin',
                             pos=vec((knee_point-hip_point)/1000))
        actuators.append(joint(shin,f'{label}_knee_pitch',(0,1,0),(-1.8,1.8),'knee_pitch'))
        inertial(shin,knee_point,groups[f'{side}_shin'],directory)
        ET.SubElement(shin,'geom',name=f'{label}_shin_link',type='capsule',
                      fromto=vec([0,0,0,*((ankle_point-knee_point)/1000)]),
                      size='.017',mass='0',contype='0',conaffinity='0',rgba='.9 .9 .85 1')
        pitch_body = ET.SubElement(shin,'body',
            name=f'{label}_foot_pitch' if ankle_roll_servo != 'none' else f'{label}_foot',
            pos=vec((ankle_point-knee_point)/1000))
        actuators.append(joint(pitch_body,f'{label}_ankle_pitch',(0,1,0),(-1.5,1.5),'ankle_pitch'))
        if ankle_roll_servo != 'none':
            inertial(pitch_body, ankle_point, groups[f'{side}_foot_pitch'], directory)
            roll_point = layout['ankle_roll'] + np.array([0, side * 88.0, 0])
            foot = ET.SubElement(pitch_body,'body',name=f'{label}_foot',
                                 pos=vec((roll_point-ankle_point)/1000))
            actuators.append(joint(foot,f'{label}_ankle_roll',(1,0,0),(-.6,.6),'ankle_roll'))
        else:
            foot = pitch_body
            roll_point = ankle_point
        inertial(foot,roll_point,groups[f'{side}_foot'],directory)
        length = 179.0 + heel_extension_mm - toe_shortening_mm
        center_x = 75.0 + foot_shift_mm - heel_extension_mm/2 - toe_shortening_mm/2
        ET.SubElement(foot,'geom',name=f'{label}_sole_contact',type='box',
                      size=vec([length/2000,.046,.0065]),
                      pos=vec([(center_x-roll_point[0])/1000,0,(7-roll_point[2])/1000]),
                      mass='0',friction='.9 .005 .0001',rgba='.1 .1 .1 1')
    lower = ET.SubElement(torso,'body',name='neck_lower',pos=vec((root_axis-body_center)/1000))
    actuators.append(joint(lower,'neck_lower_pitch',(0,1,0),(-.8,1.5),'neck_lower_pitch'))
    inertial(lower,root_axis,groups['neck_lower'],directory)
    ET.SubElement(lower,'geom',type='capsule',fromto=vec([0,0,0,*((elbow_axis-root_axis)/1000)]),
                  size='.02',mass='0',contype='0',conaffinity='0',rgba='.9 .9 .85 1')
    upper = ET.SubElement(lower,'body',name='neck_upper',pos=vec((elbow_axis-root_axis)/1000))
    actuators.append(joint(upper,'neck_upper_pitch',(0,1,0),(-1.5,1.5),'neck_upper_pitch'))
    inertial(upper,elbow_axis,groups['neck_upper'],directory)
    ET.SubElement(upper,'geom',type='capsule',fromto=vec([0,0,0,*((yoke_axis-elbow_axis)/1000)]),
                  size='.018',mass='0',contype='0',conaffinity='0',rgba='.9 .9 .85 1')
    head = ET.SubElement(upper,'body',name='head',pos=vec((yoke_axis-elbow_axis)/1000))
    actuators.append(joint(head,'head_pitch',(0,1,0),(-2,2),'head_pitch'))
    inertial(head,yoke_axis,groups['head'],directory)
    head_mesh = trimesh.load_mesh(directory / 'head.stl')
    head_half_size = (head_mesh.bounds[1] - head_mesh.bounds[0]) / 2000
    ET.SubElement(head,'geom',type='box',size=vec(head_half_size),
                  pos=vec((np.array([140 + yoke_axis[0] - YOKE[0],0,
                                     730 + yoke_axis[2]-YOKE[2]])-yoke_axis)/1000),mass='0',
                  contype='0',conaffinity='0',rgba='.9 .9 .85 1')
    ET.SubElement(head,'site',name='beak_tip_visual_datum',
                  pos=vec((tip_datum-yoke_axis)/1000),size='.002')
    beak_start=np.array([220.0 + yoke_axis[0] - YOKE[0],0.0,
                         510.0+(yoke_axis[2]-YOKE[2])])
    ET.SubElement(head,'geom',name='beak_floor_probe',type='capsule',
                  fromto=vec([*((beak_start-yoke_axis)/1000),
                              *((tip_datum-yoke_axis)/1000)]),
                  size='.009',mass='0',friction='.9 .005 .0001',
                  rgba='.94 .38 .04 .5')
    motors = ET.SubElement(xml,'actuator')
    for name,torque in actuators:
        torque *= torque_scale
        ET.SubElement(motors,'motor',name=name+'_motor',joint=name,
                      ctrllimited='true',ctrlrange=vec([-torque,torque]))
    ET.indent(xml)
    path=output/'trial.xml'
    ET.ElementTree(xml).write(path,encoding='unicode')
    return path,groups


def pose_data(model,pose,tip_datum,layout,ground_torso_deg=40.0,
              ground_head_global_deg=80.0,sit_drop_mm=0.0,
              sit_torso_deg=20.0,sit_head_global_deg=60.0,
              target_tip_z_mm=20.0,target_tip_x_mm=300.0):
    data=mujoco.MjData(model)
    data.qpos[:3]=layout['body_center']/1000
    data.qpos[3:7]=[1,0,0,0]
    if pose in ('ground_reach','seated_ground_reach'):
        seated=pose=='seated_ground_reach'
        torso_deg=sit_torso_deg if seated else ground_torso_deg
        head_global=sit_head_global_deg if seated else ground_head_global_deg
        drop_mm=sit_drop_mm if seated else 0.0
        lower,upper,head=solve_pose(np.array([target_tip_x_mm,0,target_tip_z_mm+drop_mm]),torso_deg,
                                    head_global,
                                    tip_datum, layout)
        theta=math.radians(torso_deg)
        data.qpos[:3]=(layout['hip']+pitch_matrix(torso_deg)@
                       (layout['body_center']-layout['hip'])-
                       np.array([0.0,0.0,drop_mm]))/1000
        data.qpos[3:7]=[math.cos(theta/2),0,math.sin(theta/2),0]
        leg_angles=(solve_seated_legs(layout,drop_mm,torso_deg)[0]
                    if seated else (-torso_deg,0.0,0.0))
        for side in ('left','right'):
            for joint_name,value in zip(('hip_pitch','knee_pitch','ankle_pitch'),leg_angles):
                data.qpos[model.joint(f'{side}_{joint_name}').qposadr[0]]=math.radians(value)
        for name,value in [('neck_lower_pitch',lower),('neck_upper_pitch',upper),('head_pitch',head)]:
            data.qpos[model.joint(name).qposadr[0]]=math.radians(value)
    mujoco.mj_forward(model,data)
    return data


def trial(model,pose,duration_s,torque_scale,kp,kd,tip_datum,torque_joints,layout,
          ground_torso_deg,ground_head_global_deg,sit_drop_mm=0.0,
          sit_torso_deg=20.0,sit_head_global_deg=60.0,
          target_tip_z_mm=20.0,target_tip_x_mm=300.0,
          foot_equilibrium_torques=None,appearance_geometry_screen=None,
          tip_downward_load_N=0.0):
    data=pose_data(model,pose,tip_datum,layout,ground_torso_deg,
                   ground_head_global_deg,sit_drop_mm,sit_torso_deg,
                   sit_head_global_deg,target_tip_z_mm,target_tip_x_mm)
    q_target={name:data.qpos[model.joint(name).qposadr[0]] for name in torque_joints}
    feedforward=(foot_equilibrium_torques or {}) if pose=='seated_ground_reach' else {}
    steps=int(duration_s/model.opt.timestep)
    time_to_fall=None
    saturation_count=0
    total_cmd=0
    saturation_by_joint={name:0 for name in torque_joints}
    settled_saturation_by_joint={name:0 for name in torque_joints}
    settled_steps=0
    head_control_trace=[]
    head_saturation_signs_after_0p5s={'positive':0,'negative':0}
    max_demand_by_joint={name:0.0 for name in torque_joints}
    min_root_z=float(data.qpos[2])
    max_pitch=0.0
    tip_id=model.site('beak_tip_visual_datum').id
    head_body_id=model.body('head').id
    initial_tip=np.round(data.site_xpos[tip_id],4).tolist()
    floor_id=model.geom('floor').id
    beak_geom_id=model.geom('beak_floor_probe').id
    foot_geom_ids={model.geom(f'{side}_sole_contact').id for side in ('left','right')}
    target_tip=np.array(initial_tip)
    min_tip_z=float(data.site_xpos[tip_id,2])
    max_tip_error=0.0
    beak_contact_steps=0
    both_foot_contact_steps=0
    beak_peak_normal_n=0.0
    tip_near_target_steps=0
    hold_steps=0
    for step in range(steps):
        if pose=='seated_ground_reach' and tip_downward_load_N:
            force=np.array([0.0,0.0,-tip_downward_load_N])
            moment_arm=data.site_xpos[tip_id]-data.xipos[head_body_id]
            data.xfrc_applied[head_body_id,:3]=force
            data.xfrc_applied[head_body_id,3:]=np.cross(moment_arm,force)
        settled=step*float(model.opt.timestep)>=.5
        settled_steps+=settled
        for index,name in enumerate(torque_joints):
            joint=model.joint(name)
            q=data.qpos[joint.qposadr[0]]
            qd=data.qvel[joint.dofadr[0]]
            torque=torque_scale*TORQUE_NM[name.split('_',1)[1] if name.startswith(('left_','right_')) else name]
            demand=feedforward.get(name,0.0)+kp*(q_target[name]-q)-kd*qd
            saturated=abs(demand)>torque
            saturation_count += saturated
            saturation_by_joint[name] += saturated
            if settled:
                settled_saturation_by_joint[name] += saturated
                if name=='head_pitch' and saturated:
                    head_saturation_signs_after_0p5s['positive' if demand>0 else 'negative']+=1
            if name=='head_pitch' and step%max(1,int(.1/float(model.opt.timestep)))==0:
                head_control_trace.append({
                    'time_s':round(step*float(model.opt.timestep),3),
                    'target_error_deg':round(math.degrees(q_target[name]-q),3),
                    'joint_velocity_rad_s':round(float(qd),3),
                    'demand_Nm':round(float(demand),3),
                    'saturated':bool(saturated),
                })
            max_demand_by_joint[name]=max(max_demand_by_joint[name],abs(float(demand)))
            total_cmd += 1
            data.ctrl[index]=np.clip(demand,-torque,torque)
        mujoco.mj_step(model,data)
        tip=data.site_xpos[tip_id]
        min_tip_z=min(min_tip_z,float(tip[2]))
        max_tip_error=max(max_tip_error,float(np.linalg.norm(tip-target_tip)))
        ground_contacts=set()
        for contact_index in range(data.ncon):
            contact=data.contact[contact_index]
            pair={contact.geom1,contact.geom2}
            if floor_id not in pair:
                continue
            other=(pair-{floor_id}).pop()
            ground_contacts.add(other)
            if other==beak_geom_id:
                force=np.zeros(6)
                mujoco.mj_contactForce(model,data,contact_index,force)
                beak_peak_normal_n=max(beak_peak_normal_n,float(force[0]))
        beak_contact_steps+=beak_geom_id in ground_contacts
        both_foot_contact_steps+=foot_geom_ids.issubset(ground_contacts)
        if step*model.opt.timestep>=.2:
            hold_steps+=1
            tip_near_target_steps+=(abs(float(tip[0]-target_tip[0]))<=.03 and
                                    abs(float(tip[2]-target_tip[2]))<=.03)
        min_root_z=min(min_root_z,float(data.qpos[2]))
        quat=data.qpos[3:7]
        pitch=math.degrees(math.asin(np.clip(2*(quat[0]*quat[2]-quat[3]*quat[1]),-1,1)))
        max_pitch=max(max_pitch,abs(pitch))
        root_floor_limit=.12 if pose=='seated_ground_reach' else .19
        if time_to_fall is None and (data.qpos[2]<root_floor_limit or abs(pitch)>65):
            time_to_fall=(step+1)*model.opt.timestep
    return {'pose':pose,'duration_s':duration_s,'time_to_fall_s':time_to_fall,
            'final_root_position_m':np.round(data.qpos[:3],4).tolist(),
            'minimum_root_height_m':round(min_root_z,4),
            'maximum_absolute_root_pitch_deg':round(max_pitch,2),
            'actuator_saturation_fraction':round(saturation_count/total_cmd,3),
            'saturation_fraction_by_joint':{name:round(count/steps,3)
                                             for name,count in saturation_by_joint.items()},
            'saturation_fraction_by_joint_after_0p5s':{
                name:round(count/settled_steps,3)
                for name,count in settled_saturation_by_joint.items()},
            'head_saturation_signs_after_0p5s':head_saturation_signs_after_0p5s,
            'head_control_trace_0p1s':head_control_trace,
            'peak_unclipped_control_demand_Nm_by_joint':{name:round(value,2)
                                                    for name,value in max_demand_by_joint.items()},
            'foot_only_equilibrium_feedforward_used':bool(feedforward),
            'final_joint_target_error_deg':{name:round(math.degrees(q_target[name]-data.qpos[model.joint(name).qposadr[0]]),2)
                                            for name in torque_joints},
            'initial_beak_tip_visual_datum_m':initial_tip,
            'final_beak_tip_visual_datum_m':np.round(data.site_xpos[tip_id],4).tolist(),
            'minimum_beak_tip_height_m':round(min_tip_z,4),
            'maximum_beak_tip_error_m':round(max_tip_error,4),
            'beak_tip_near_initial_target_fraction_after_0p2s':round(tip_near_target_steps/hold_steps,3) if hold_steps else None,
            'beak_floor_contact_fraction':round(beak_contact_steps/steps,3),
            'beak_floor_peak_normal_N':round(beak_peak_normal_n,2),
            'both_feet_floor_contact_fraction':round(both_foot_contact_steps/steps,3),
            'tip_downward_load_N':tip_downward_load_N if pose=='seated_ground_reach' else 0.0,
            'valid_unloaded_ground_reach_screen':(
                time_to_fall is None and tip_near_target_steps/hold_steps >= .95
                and beak_contact_steps/steps < .01 and beak_peak_normal_n < 1.0
                and both_foot_contact_steps/steps >= .95
                and bool(max(settled_saturation_by_joint.values())/settled_steps < .1)
                and appearance_geometry_screen is not None
                and appearance_geometry_screen['necessary_clearance_pass'])
                if pose!='standing' and hold_steps and not tip_downward_load_N else None,
            'valid_tip_load_hold_screen':(
                time_to_fall is None and tip_near_target_steps/hold_steps >= .95
                and beak_contact_steps/steps < .01 and beak_peak_normal_n < 1.0
                and both_foot_contact_steps/steps >= .95
                and bool(max(settled_saturation_by_joint.values())/settled_steps < .1)
                and appearance_geometry_screen is not None
                and appearance_geometry_screen['necessary_clearance_pass'])
                if pose=='seated_ground_reach' and hold_steps and tip_downward_load_N else None,
            'appearance_geometry_screen':appearance_geometry_screen,
            'final_com_m':np.round(data.subtree_com[model.body('torso').id],4).tolist(),
            'final_contacts':int(data.ncon)}


def torque_joint_names(ankle_roll_servo):
    leg_names = ['hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch']
    if ankle_roll_servo != 'none':
        leg_names.append('ankle_roll')
    names = [f'{side}_{name}' for side in ('right','left') for name in leg_names]
    return names + ['neck_lower_pitch','neck_upper_pitch','head_pitch']


def appearance_screen_for_pose(appearance_dir, pose, tip_datum, layout,
                               ground_torso_deg, ground_head_global_deg,
                               sit_drop_mm, sit_torso_deg, sit_head_global_deg,
                               target_tip_x_mm, target_tip_z_mm):
    if pose=='standing':
        return None
    seated=pose=='seated_ground_reach'
    drop=sit_drop_mm if seated else 0.0
    torso=sit_torso_deg if seated else ground_torso_deg
    head_global=sit_head_global_deg if seated else ground_head_global_deg
    lower,upper,head=solve_pose(np.array([target_tip_x_mm,0,
                                         target_tip_z_mm+drop]),
                                torso,head_global,tip_datum,layout)
    geometry=sampled_geometry(appearance_dir/'appearance.xml',torso,lower,
                              upper,head,layout)
    geometry['body_min_height_world_mm']=round(
        geometry['body_min_height_world_mm']-drop,2)
    geometry['beak_min_height_world_mm']={name:round(value-drop,2)
        for name,value in geometry['beak_min_height_world_mm'].items()}
    clearance=min(geometry['lower_fairing_to_body_sampled_min_mm'],
                  geometry['upper_fairing_to_body_sampled_min_mm'],
                  geometry['head_shell_to_body_sampled_min_mm'])
    geometry['necessary_clearance_pass']=(
        clearance>=5.0 and geometry['body_min_height_world_mm']>=30.0 and
        min(geometry['beak_min_height_world_mm'].values())>=0.0)
    geometry['method']='Sampled visible shell/body rounded-box gap, not continuous full-joint sweep.'
    return geometry


def lateral_shift_trial(model, torque_joints, torque_scale, kp, kd,
                        compensate_ankle, layout):
    """Bounded double-support lateral shift, comparing foot-roll compensation."""
    data = pose_data(model, 'standing', np.zeros(3), layout)
    steps = int(2.0 / model.opt.timestep)
    floor_id = model.geom('floor').id
    foot_geom_ids = {side: model.geom(f'{side}_sole_contact').id
                     for side in ('left', 'right')}
    foot_body_ids = {side: model.body(f'{side}_foot').id
                     for side in ('left', 'right')}
    contact_steps = {side: 0 for side in ('left', 'right')}
    saturation_steps = {name: 0 for name in torque_joints}
    initial_com_y = float(data.subtree_com[model.body('torso').id, 1])
    fall_time = None
    max_root_roll = 0.0
    for step in range(steps):
        ramp = min((step + 1) * model.opt.timestep / 0.8, 1.0)
        for index, name in enumerate(torque_joints):
            target = 0.0
            if name.endswith('_hip_roll'):
                target = -0.25 * ramp
            elif name.endswith('_ankle_roll') and compensate_ankle:
                target = 0.25 * ramp
            joint = model.joint(name)
            q = data.qpos[joint.qposadr[0]]
            qd = data.qvel[joint.dofadr[0]]
            torque = torque_scale * TORQUE_NM[name.split('_', 1)[1]
                if name.startswith(('left_', 'right_')) else name]
            demand = kp * (target - q) - kd * qd
            saturation_steps[name] += abs(demand) > torque
            data.ctrl[index] = np.clip(demand, -torque, torque)
        mujoco.mj_step(model, data)
        for side, geom_id in foot_geom_ids.items():
            if any({data.contact[i].geom1, data.contact[i].geom2} ==
                   {floor_id, geom_id} for i in range(data.ncon)):
                contact_steps[side] += 1
        root_rotation = np.empty(9)
        mujoco.mju_quat2Mat(root_rotation, data.qpos[3:7])
        root_roll = math.degrees(math.atan2(root_rotation[7], root_rotation[8]))
        max_root_roll = max(max_root_roll, abs(root_roll))
        if fall_time is None and (data.qpos[2] < .19 or abs(root_roll) > 65):
            fall_time = round((step + 1) * model.opt.timestep, 3)
    foot_roll_deg = {}
    for side, body_id in foot_body_ids.items():
        matrix = data.xmat[body_id].reshape(3, 3)
        foot_roll_deg[side] = round(math.degrees(math.atan2(matrix[2, 1],
                                                         matrix[2, 2])), 2)
    com = data.subtree_com[model.body('torso').id]
    return {
        'pose': 'double_support_lateral_shift',
        'ankle_roll_compensation': compensate_ankle,
        'duration_s': 2.0,
        'commanded_hip_roll_deg': round(math.degrees(-.25), 2),
        'commanded_ankle_roll_deg': round(math.degrees(.25 if compensate_ankle else 0), 2),
        'time_to_fall_s': fall_time,
        'final_com_y_m': round(float(com[1]), 4),
        'com_y_shift_m': round(float(com[1]) - initial_com_y, 4),
        'final_root_y_m': round(float(data.qpos[1]), 4),
        'maximum_absolute_root_roll_deg': round(max_root_roll, 2),
        'final_foot_roll_deg': foot_roll_deg,
        'foot_ground_contact_fraction': {side: round(n / steps, 3)
                                         for side, n in contact_steps.items()},
        'roll_joint_saturation_fraction': {name: round(saturation_steps[name] / steps, 3)
                                           for name in torque_joints
                                           if name.endswith(('_hip_roll', '_ankle_roll'))},
    }


def single_support_trial(model, torque_joints, torque_scale, kp, kd,
                         layout, hip_roll_target=-0.30, lift_scale=1.0,
                         release_swing_roll=False):
    """Shift over the left sole, lift the right foot, then hold briefly.

    This open-loop diagnostic is a necessary contact check, not a gait policy.
    The foot lift angles were first checked kinematically on this exact model.
    """
    data = pose_data(model, 'standing', np.zeros(3), layout)
    timestep = model.opt.timestep
    duration_s = 3.0
    steps = int(duration_s / timestep)
    floor_id = model.geom('floor').id
    left_geom = model.geom('left_sole_contact')
    right_geom = model.geom('right_sole_contact')
    torso_id = model.body('torso').id
    initial_com_y = float(data.subtree_com[torso_id, 1])
    phase = {'shift_s': 0.9, 'settle_s': 0.2, 'lift_s': 0.6}
    hold_start_s = sum(phase.values())
    counters = {'left_contact': 0, 'right_contact': 0,
                'right_clearance_10mm': 0, 'com_inside_left_sole': 0,
                'clean_single_support': 0}
    hold_steps = 0
    maximum_right_sole_corner_clearance_m = -1.0
    minimum_hold_right_sole_corner_clearance_m = 1.0
    minimum_hold_com_margin_m = 1.0
    saturation_steps = {name: 0 for name in torque_joints}
    fall_time = None
    samples = []
    for step in range(steps):
        elapsed = (step + 1) * timestep
        shift = min(elapsed / phase['shift_s'], 1.0)
        lift = min(max((elapsed - phase['shift_s'] - phase['settle_s']) /
                       phase['lift_s'], 0.0), 1.0)
        for index, name in enumerate(torque_joints):
            target = 0.0
            if name.endswith('_hip_roll'):
                target = hip_roll_target * shift * (
                    1-lift if release_swing_roll and name.startswith('right_') else 1)
            elif name.endswith('_ankle_roll'):
                target = -hip_roll_target * shift * (
                    1-lift if release_swing_roll and name.startswith('right_') else 1)
            elif name == 'right_hip_pitch':
                target = 0.2 * lift_scale * lift
            elif name == 'right_knee_pitch':
                target = -0.4 * lift_scale * lift
            elif name == 'right_ankle_pitch':
                target = 0.2 * lift_scale * lift
            joint = model.joint(name)
            q = data.qpos[joint.qposadr[0]]
            qd = data.qvel[joint.dofadr[0]]
            torque = torque_scale * TORQUE_NM[name.split('_', 1)[1]
                if name.startswith(('left_', 'right_')) else name]
            demand = kp * (target - q) - kd * qd
            saturation_steps[name] += abs(demand) > torque
            data.ctrl[index] = np.clip(demand, -torque, torque)
        mujoco.mj_step(model, data)
        contacts = {}
        for side, geom_id in [('left', left_geom.id), ('right', right_geom.id)]:
            contacts[side] = any({data.contact[i].geom1, data.contact[i].geom2}
                                 == {floor_id, geom_id}
                                 for i in range(data.ncon))
        right_rotation = data.geom_xmat[right_geom.id].reshape(3, 3)
        right_center = data.geom_xpos[right_geom.id]
        right_size = model.geom_size[right_geom.id]
        right_corner_clearance = min(float((right_center + right_rotation @
            np.array([x, y, -right_size[2]]))[2])
            for x in (-right_size[0], right_size[0])
            for y in (-right_size[1], right_size[1]))
        com = data.subtree_com[torso_id]
        left_local_com = (data.geom_xmat[left_geom.id].reshape(3, 3).T @
                          (com - data.geom_xpos[left_geom.id]))
        left_size = model.geom_size[left_geom.id]
        com_margin = min(float(left_size[0] - abs(left_local_com[0])),
                         float(left_size[1] - abs(left_local_com[1])))
        if elapsed >= hold_start_s:
            hold_steps += 1
            counters['left_contact'] += contacts['left']
            counters['right_contact'] += contacts['right']
            counters['right_clearance_10mm'] += right_corner_clearance >= .01
            counters['com_inside_left_sole'] += com_margin >= 0
            counters['clean_single_support'] += (contacts['left'] and
                not contacts['right'] and right_corner_clearance >= .01 and
                com_margin >= 0)
            minimum_hold_right_sole_corner_clearance_m = min(
                minimum_hold_right_sole_corner_clearance_m,
                right_corner_clearance)
            minimum_hold_com_margin_m = min(minimum_hold_com_margin_m,
                                             com_margin)
        maximum_right_sole_corner_clearance_m = max(
            maximum_right_sole_corner_clearance_m, right_corner_clearance)
        root_rotation = np.empty(9)
        mujoco.mju_quat2Mat(root_rotation, data.qpos[3:7])
        root_roll = math.degrees(math.atan2(root_rotation[7], root_rotation[8]))
        if fall_time is None and (data.qpos[2] < .19 or abs(root_roll) > 65):
            fall_time = round(elapsed, 3)
        if step % int(.1 / timestep) == 0 or step == steps - 1:
            samples.append({'t_s': round(elapsed, 3),
                            'com_y_m': round(float(com[1]), 4),
                            'com_margin_left_sole_m': round(com_margin, 4),
                            'right_sole_corner_clearance_m': round(
                                right_corner_clearance, 4),
                            'left_contact': contacts['left'],
                            'right_contact': contacts['right'],
                            'root_roll_deg': round(root_roll, 2)})
    return {
        'pose': 'shift_left_then_lift_right_open_loop',
        'duration_s': duration_s,
        'phase_s': phase,
        'commanded_hip_roll_deg': round(math.degrees(hip_roll_target), 2),
        'commanded_ankle_roll_deg': round(math.degrees(-hip_roll_target), 2),
        'release_swing_leg_roll_during_lift':release_swing_roll,
        'commanded_right_leg_lift_rad': {'hip_pitch': round(0.2*lift_scale,4),
                                         'knee_pitch': round(-0.4*lift_scale,4),
                                         'ankle_pitch': round(0.2*lift_scale,4)},
        'time_to_fall_s': fall_time,
        'final_com_y_m': round(float(data.subtree_com[torso_id, 1]), 4),
        'com_y_shift_m': round(float(data.subtree_com[torso_id, 1]) - initial_com_y, 4),
        'maximum_right_sole_corner_clearance_m': round(
            maximum_right_sole_corner_clearance_m, 4),
        'minimum_hold_right_sole_corner_clearance_m': round(
            minimum_hold_right_sole_corner_clearance_m, 4),
        'minimum_hold_com_margin_m': round(minimum_hold_com_margin_m, 4),
        'hold_fraction': {name: round(count / hold_steps, 3)
                          for name, count in counters.items()},
        'saturation_fraction_by_joint': {name: round(count / steps, 3)
                                         for name, count in saturation_steps.items()
                                         if name.endswith(('_hip_roll', '_ankle_roll',
                                                           '_hip_pitch', '_knee_pitch',
                                                           '_ankle_pitch'))},
        'samples_10hz': samples,
        'valid_single_support_screen': fall_time is None and
            counters['clean_single_support'] / hold_steps >= .95,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir',type=Path,required=True)
    parser.add_argument('--wall-mm',type=float,default=1.6)
    parser.add_argument('--extra-torso-mass-kg',type=float,default=0.0)
    parser.add_argument('--torque-scale',type=float,default=1.0)
    parser.add_argument('--kp',type=float,default=24.0)
    parser.add_argument('--kd',type=float,default=1.1)
    parser.add_argument('--knee-servo',choices=['xm430','xm540'],default='xm430')
    parser.add_argument('--hip-pitch-servo',choices=['xm430','xm540'],default='xm430')
    parser.add_argument('--hip-roll-servo',choices=['xm430','xm540'],default='xm430')
    parser.add_argument('--ankle-pitch-servo',choices=['xm430','xm540'],default='xm430')
    parser.add_argument('--ground-torso-deg',type=float,default=40.0)
    parser.add_argument('--ground-head-global-deg',type=float,default=80.0)
    parser.add_argument('--sit-drop-mm',type=float,default=0.0)
    parser.add_argument('--sit-torso-deg',type=float,default=20.0)
    parser.add_argument('--sit-head-global-deg',type=float,default=60.0)
    parser.add_argument('--target-tip-z-mm',type=float,default=20.0)
    parser.add_argument('--target-tip-x-mm',type=float,default=300.0)
    parser.add_argument('--tip-downward-load-N',type=float,default=0.0,
                        help='Apply a vertical tip wrench during seated hold; no object or clamp contact is modeled.')
    parser.add_argument('--only-sit',action='store_true')
    parser.add_argument('--foot-equilibrium-evidence',type=Path)
    parser.add_argument('--single-support-hip-roll-rad',type=float,nargs='+',
                        default=[-.25,-.30,-.35])
    parser.add_argument('--single-support-lift-scale',type=float,default=1.0)
    parser.add_argument('--release-swing-roll',action='store_true')
    parser.add_argument('--ankle-roll-servo',choices=['none','xm430'],default='none')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    if args.extra_torso_mass_kg<0:
        parser.error('--extra-torso-mass-kg must be nonnegative')
    if not 0<=args.tip_downward_load_N<=2.0:
        parser.error('--tip-downward-load-N must be between 0 and 2')
    if args.tip_downward_load_N and not args.only_sit:
        parser.error('--tip-downward-load-N requires --only-sit')
    if not 0<args.single_support_lift_scale<=2.0:
        parser.error('--single-support-lift-scale must be in (0, 2]')
    if args.only_sit and args.sit_drop_mm<=0:
        parser.error('--only-sit requires --sit-drop-mm > 0')
    if args.knee_servo=='xm540':TORQUE_NM['knee_pitch']=2.12
    if args.hip_pitch_servo=='xm540':TORQUE_NM['hip_pitch']=2.12
    if args.hip_roll_servo=='xm540':TORQUE_NM['hip_roll']=2.12
    if args.ankle_pitch_servo=='xm540':TORQUE_NM['ankle_pitch']=2.12
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((args.appearance_dir/'manifest.json').read_text())
    tip_datum=tip_datum_from_mesh(args.appearance_dir)
    layout=pivots_from_manifest(args.appearance_dir)
    layout['ankle_roll']=ANKLE_ROLL_PIVOT.copy()
    model_path,groups=make_model(args.appearance_dir,args.wall_mm,
        manifest['foot_shift_mm'],manifest['heel_extension_mm'],
        manifest.get('foot_toe_shortening_mm',0.0),args.torque_scale,
        args.knee_servo,args.hip_pitch_servo,args.hip_roll_servo,
        args.ankle_pitch_servo,args.ankle_roll_servo,
        tip_datum,layout,np.array(manifest.get('body_scale_xyz',[1,1,1])),
        args.extra_torso_mass_kg,args.output)
    model=mujoco.MjModel.from_xml_path(str(model_path))
    torque_joints=torque_joint_names(args.ankle_roll_servo)
    foot_equilibrium_torques=None
    if args.foot_equilibrium_evidence:
        equilibrium=json.loads(args.foot_equilibrium_evidence.read_text())
        if equilibrium['trial_xml_sha256']!=hashlib.sha256(model_path.read_bytes()).hexdigest():
            raise ValueError('Foot equilibrium evidence belongs to a different trial model')
        pose=equilibrium['pose']
        for key,actual in (('sit_drop_mm',args.sit_drop_mm),
                           ('torso_pitch_down_deg',args.sit_torso_deg),
                           ('head_global_pitch_down_deg',args.sit_head_global_deg),
                           ('target_tip_z_mm',args.target_tip_z_mm)):
            if abs(pose[key]-actual)>1e-6:
                raise ValueError(f'Foot equilibrium pose mismatch: {key}')
        load=equilibrium['beak_tip_external_force_N']
        if abs(load[0])>1e-6 or abs(load[1])>1e-6 or abs(load[2]+args.tip_downward_load_N)>1e-6:
            raise ValueError('Foot equilibrium tip load mismatch')
        case=equilibrium['cases_by_target_tip_x_mm'][str(args.target_tip_x_mm)]
        if not case['within_trial_torque_caps']:
            raise ValueError('Foot equilibrium requires more than the trial actuator caps')
        foot_equilibrium_torques=case['foot_only_equilibrium_torque_Nm_by_joint']
        if set(foot_equilibrium_torques)!=set(torque_joints):
            raise ValueError('Foot equilibrium joint contract mismatch')
    poses=(('seated_ground_reach',) if args.only_sit else
           ('standing','ground_reach')+
           (('seated_ground_reach',) if args.sit_drop_mm else ()))
    geometry_screens={pose:appearance_screen_for_pose(
        args.appearance_dir,pose,tip_datum,layout,args.ground_torso_deg,
        args.ground_head_global_deg,args.sit_drop_mm,args.sit_torso_deg,
        args.sit_head_global_deg,args.target_tip_x_mm,args.target_tip_z_mm)
        for pose in poses}
    results=[trial(model,pose,2.0,args.torque_scale,args.kp,args.kd,
                   tip_datum,torque_joints,layout,args.ground_torso_deg,
                   args.ground_head_global_deg,args.sit_drop_mm,
                   args.sit_torso_deg,args.sit_head_global_deg,
                   args.target_tip_z_mm,args.target_tip_x_mm,
                   foot_equilibrium_torques,geometry_screens[pose],
                   args.tip_downward_load_N)
             for pose in poses]
    lateral_results = ([lateral_shift_trial(model, torque_joints, args.torque_scale,
                                          args.kp, args.kd, compensate_ankle,layout)
                        for compensate_ankle in (False, True)]
                       if args.ankle_roll_servo != 'none' and not args.only_sit else [])
    single_support_results = ([single_support_trial(model, torque_joints,
        args.torque_scale, args.kp, args.kd, layout, hip_roll_target,
        args.single_support_lift_scale,args.release_swing_roll)
        for hip_roll_target in args.single_support_hip_roll_rad]
        if args.ankle_roll_servo != 'none' and not args.only_sit else [])
    output={'status':'provisional_mujoco_contact_and_torque_trial_not_release',
            'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
            'appearance_manifest_sha256':hashlib.sha256((args.appearance_dir/'manifest.json').read_bytes()).hexdigest(),
            'source_bill_tip_visual_datum_mm':np.round(tip_datum,3).tolist(),
            'visual_pivots_mm':{name:np.round(value,3).tolist()
                                for name,value in layout.items()},
            'wall_mm':args.wall_mm,'mass_kg':round(float(model.body_mass.sum()),3),
            'extra_torso_mass_kg':args.extra_torso_mass_kg,
            'torque_scale':args.torque_scale,'kp':args.kp,'kd':args.kd,
            'tip_downward_load_N':args.tip_downward_load_N,
            'knee_servo':args.knee_servo,'hip_pitch_servo':args.hip_pitch_servo,
            'hip_roll_servo':args.hip_roll_servo,
            'ankle_pitch_servo':args.ankle_pitch_servo,
            'ground_reach_command_deg':{'torso':args.ground_torso_deg,
                                        'head_global':args.ground_head_global_deg},
            'seated_reach_command':{'drop_mm':args.sit_drop_mm,
                                    'torso_deg':args.sit_torso_deg,
                                    'head_global_deg':args.sit_head_global_deg,
                                    'target_tip_x_mm':args.target_tip_x_mm,
                                    'target_tip_z_mm':args.target_tip_z_mm}
                                    if args.sit_drop_mm else None,
            'ankle_roll_servo':args.ankle_roll_servo,
            'ankle_roll_trial_pivot_mm': layout['ankle_roll'].tolist() if
                args.ankle_roll_servo != 'none' else None,
            'contact_friction':'.9 .005 .0001',
            'controller':('joint PD plus fixed foot-only static-equilibrium feedforward; '
                          'no free-root support' if foot_equilibrium_torques else
                          'joint PD with stated gains and torque scale, no free-root support'),
            'foot_equilibrium_evidence_sha256':(
                hashlib.sha256(args.foot_equilibrium_evidence.read_bytes()).hexdigest()
                if args.foot_equilibrium_evidence else None),
            'trials':results,
            'lateral_shift_trials':lateral_results,
            'single_support_trials':single_support_results,
            'limitations':['Thin-shell printed mass, center and inertia are approximate; motor placements are trial reservations.',
                           'No thermal/current/voltage derating, cable or hardware joint package has been verified.',
                           'Beak-floor contact is a single capsule probe; it is not an R2 clamp, object or payload model.',
                           'Tip downward force is a massless external wrench proxy; it cannot prove beak grasp or object retention.',
                           'Single-support trial is open-loop and uses a simplified rectangular sole; it is not a gait or ZMP validation.',
                           'No continuous self-collision, gait, grip, drag or cross-engine training result.',
                           'A failed PD stand can reflect controller tuning as well as hardware; a passed stand is not walking validation.']}
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    args.evidence.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
