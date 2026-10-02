"""Contact-only 50 g block pickup/release diagnostic with a free robot base.

Starts from a precomputed side-ground-grasp pose; target/trajectory are known.
This grades mechanics, not vision/autonomous navigation, and never welds or
attaches the object to the beak with a hidden constraint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from sai_agent.goose.control import JointMap
from sai_agent.goose.rigid import RigidReference
from sai_agent.paths import resource_root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/grasp_block'))
    p.add_argument('--grip-torque',type=float,default=.1);p.add_argument('--stance-feedforward',action='store_true')
    p.add_argument('--lift-forward',type=float,default=.03);p.add_argument('--lift-pitch',type=float,default=.3)
    p.add_argument('--lift-seconds',type=float,default=4.)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    robot=resource_root()/'robots/Goose_V0.1';path=robot/'models/full/robot.xml'
    model_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if not np.isfinite(a.lift_seconds) or a.lift_seconds<2.:raise ValueError('Lift duration must be finite and >=2 seconds')
    tree=ET.parse(path);root=tree.getroot();world=root.find('worldbody')
    obj=ET.SubElement(world,'body',name='sample_object',pos='.36 0 .019')
    ET.SubElement(obj,'freejoint',name='sample_object_free')
    ET.SubElement(obj,'geom',name='sample_block',type='box',size='.010 .010 .018',mass='.05',
                  rgba='.17 .47 .82 1',friction='.8 .005 .0001',condim='4')
    for key in list(root.findall('./keyframe')):root.remove(key)
    # Mesh references stay absolute in this temporary artifact model.
    for mesh in root.findall('./asset/mesh'):mesh.set('file',str((path.parent/mesh.get('file')).resolve()))
    ET.indent(tree);taskpath=a.output/'task.xml';tree.write(taskpath,encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(taskpath));d=mujoco.MjData(m);mapping=JointMap(m)
    pose=json.loads((robot/'evidence/ground_reach_check.json').read_text())
    if not pose['pass'] or pose['model_sha256']!=model_sha:raise ValueError('A passing reach pose for this exact model is required')
    rigid=RigidReference() if a.stance_feedforward else None
    d.qpos[:len(pose['qpos'])]=pose['qpos'];d.qpos[-7:]=[.36,0,.019,1,0,0,0]
    mujoco.mj_forward(m,d);initial=d.qpos.copy();target=d.qpos[mapping.qpos].copy()
    objid=m.body('sample_object').id;tip=m.site('task_center').id;head=m.body('head_roll').id
    ni=mapping.neck_indices;neck=mapping.qpos[ni];orientation=d.xmat[head].reshape(3,3).copy();initial_tip=d.site_xpos[tip].copy()
    planning=mujoco.MjData(m);planning.qpos[:]=initial
    trajectory=[];x=target[ni].copy()
    for height in np.linspace(0,.08,41):
        # A small forward arc and 17-degree bill pitch change avoid the folded
        # neck's wrist limit. This is a planned, visible motion, not object
        # support; the object remains fully free throughout.
        desired=initial_tip+np.array([a.lift_forward*height/.08,0,height])
        def residual(q):
            planning.qpos[neck]=q;mujoco.mj_forward(m,planning)
            # Five neck axes constrain position, pitch and roll. Body heading
            # may align before approach; a small free yaw during lift is valid.
            _,pitch,roll=Rotation.from_matrix(planning.xmat[head].reshape(3,3)).as_euler('ZYX')
            _,initial_pitch,initial_roll=Rotation.from_matrix(orientation).as_euler('ZYX')
            return np.r_[10*(planning.site_xpos[tip]-desired),pitch-(initial_pitch+a.lift_pitch*height/.08),roll-initial_roll]
        solved=least_squares(residual,x,bounds=(mapping.ranges[ni,0],mapping.ranges[ni,1]),max_nfev=100)
        if np.linalg.norm(residual(solved.x)[:3])>.01:raise RuntimeError(f'Lift IK failed at {height:.3f} m')
        x=solved.x;trajectory.append(x.copy())
    (a.output/'planned_neck_path.json').write_text(json.dumps({'joint_names':[mapping.names[i] for i in ni],
        'angles_rad':np.array(trajectory).tolist(),'base_qpos':initial[:len(pose['qpos'])].tolist(),
        'model_sha256':model_sha},indent=2)+'\n')
    lift_end=1.5+a.lift_seconds;release_at=lift_end+2.
    duration=release_at+2.5;steps=round(duration/m.opt.timestep);maxheight=0.;lastheldheight=0.;graspcontacts=0;max_tilt=0.;trace=[];maxclosure=0.
    object_start=d.xpos[objid].copy();root_start=d.qpos[:3].copy();saturation=np.zeros(len(mapping.names),dtype=int)
    for step in range(steps):
        t=step*m.opt.timestep
        if t<.5:target[-1]=initial[mapping.qpos[-1]]
        elif t<release_at:target[-1]=mapping.home[-1]
        else:target[-1]=initial[mapping.qpos[-1]]
        if 1.5<=t<lift_end:
            u=(t-1.5)/a.lift_seconds;fraction=10*u**3-15*u**4+6*u**5
            position=fraction*40;index=min(39,int(position));mix=position-index
            target[ni]=(1-mix)*trajectory[index]+mix*trajectory[index+1]
        elif t>=lift_end:target[ni]=trajectory[-1]
        ff=d.qfrc_bias[mapping.dof].copy()
        if rigid is not None:
            ff+=rigid.double_support_torque(d.qpos[mapping.qpos],d.xmat[m.body('torso').id].reshape(3,3))
        u=mapping.torque(d.qpos[mapping.qpos],d.qvel[mapping.dof],target,ff)
        u[-1]=np.clip(u[-1],-a.grip_torque,a.grip_torque)
        saturation+=abs(u)>=mapping.limits-1e-6;d.ctrl[mapping.actuator]=u;mujoco.mj_step(m,d)
        maxheight=max(maxheight,float(d.xpos[objid,2]));max_tilt=max(max_tilt,float(np.arccos(np.clip(d.xmat[m.body('torso').id].reshape(3,3)[2,2],-1,1))))
        if release_at-.9<t<release_at-.1:lastheldheight=float(d.xpos[objid,2])
        for contact in d.contact:
            names=(m.geom(contact.geom1).name,m.geom(contact.geom2).name)
            if 'sample_block' in names and any('pad' in name for name in names):graspcontacts+=1
        maxclosure=max(maxclosure,float(np.linalg.norm(d.site('jaw_loop').xpos-d.site('follower_loop').xpos)))
        if step%100==0:trace.append({'t_s':t,'object_position_m':d.xpos[objid].tolist(),
                                     'root_position_m':d.qpos[:3].tolist(),'beak_q_rad':float(d.qpos[mapping.qpos[-1]])})
    release_height=float(d.xpos[objid,2]);held=lastheldheight>object_start[2]+.05;released=release_height<.025
    result={'scope':'specified trajectory, initial side-ground pose; contact-only free-base mechanics diagnostic, not autonomous task acceptance',
            'object_mass_kg':.05,'object_dimensions_m':[.020,.020,.036],'grip_torque_limit_Nm':a.grip_torque,
            'object_start_m':object_start.tolist(),'max_object_center_height_m':maxheight,
            'object_height_before_release_m':lastheldheight,'final_object_height_m':release_height,
            'grasp_pad_contact_samples':graspcontacts,'max_torso_tilt_deg':float(np.degrees(max_tilt)),
            'root_displacement_m':float(np.linalg.norm(d.qpos[:3]-root_start)),
            'max_loop_residual_mm':maxclosure*1000,'pickup_pass':bool(held),'release_pass':bool(released),
            'root_free':True,'object_free':True,'object_attachment_constraints':0,'extra_equality_count':m.neq-1,
            'vision_used':False,'model_sha256':model_sha,
            'stance_feedforward':a.stance_feedforward,'world_support_forces_applied':False,
            'lift_forward_m':a.lift_forward,'lift_pitch_change_rad':a.lift_pitch,
            'lift_duration_s':a.lift_seconds,'lift_time_interpolation':'continuous quintic progress with linear interpolation between IK nodes',
            'lift_orientation_constraint':'position arc and pitch/roll targets; heading free',
            'trace':trace,'torque_saturation_steps':dict(zip(mapping.names,map(int,saturation))),
            'pass':bool(held and released and max_tilt<np.radians(5) and maxclosure<.0005)}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='trace'},indent=2));return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
