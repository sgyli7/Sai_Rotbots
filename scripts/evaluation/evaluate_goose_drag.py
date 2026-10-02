"""Free-body contact-only pull of a high-friction specified sample.

This tests mouth grip and a short head/neck pull while both feet remain on
the floor. It is not a claim of walking while dragging or arbitrary objects.
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--grip-torque',type=float,default=.15)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    robot=resource_root()/'robots/Goose_V0.1';source=robot/'models/full/robot.xml'
    model_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    pose=json.loads((robot/'evidence/ground_reach_check.json').read_text())
    if not pose['pass'] or pose['model_sha256']!=model_sha:raise ValueError('Current passing ground pose required')
    tree=ET.parse(source);world=tree.getroot().find('worldbody')
    sample=ET.SubElement(world,'body',name='drag_sample',pos='.36 0 .019')
    ET.SubElement(sample,'freejoint',name='drag_sample_free')
    ET.SubElement(sample,'geom',name='drag_block',type='box',size='.010 .010 .018',mass='.30',
                  rgba='.17 .47 .82 1',friction='.7 .005 .0001',condim='4')
    for key in list(tree.getroot().findall('./keyframe')):tree.getroot().remove(key)
    for mesh in tree.getroot().findall('./asset/mesh'):
        mesh.set('file',str((source.parent/mesh.get('file')).resolve()))
    ET.indent(tree);task=args.output/'task.xml';tree.write(task,encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(task));d=mujoco.MjData(m);mapping=JointMap(m)
    d.qpos[:len(pose['qpos'])]=pose['qpos'];d.qpos[-7:]=[.36,0,.019,1,0,0,0]
    mujoco.mj_forward(m,d);start=d.qpos.copy();targets=d.qpos[mapping.qpos].copy()
    ni=mapping.neck_indices;adr=mapping.qpos[ni];tip=m.site('task_center').id
    head=m.body('head_roll').id;initial_tip=d.site_xpos[tip].copy()
    _,pitch,roll=Rotation.from_matrix(d.xmat[head].reshape(3,3)).as_euler('ZYX')
    planning=mujoco.MjData(m);planning.qpos[:]=start;angles=[];x=targets[ni].copy()
    for distance in np.linspace(0,.09,31):
        desired=initial_tip+np.array([distance,0,0])
        def residual(q):
            planning.qpos[adr]=q;mujoco.mj_forward(m,planning)
            _,p,r=Rotation.from_matrix(planning.xmat[head].reshape(3,3)).as_euler('ZYX')
            return np.r_[10*(planning.site_xpos[tip]-desired),p-pitch,r-roll]
        solved=least_squares(residual,x,bounds=(mapping.ranges[ni,0],mapping.ranges[ni,1]),max_nfev=100)
        if np.linalg.norm(residual(solved.x)[:3])>.01:raise RuntimeError(f'Drag IK failed at {distance:.3f} m')
        x=solved.x;angles.append(x.copy())
    (args.output/'planned_neck_path.json').write_text(json.dumps({
        'joint_names':[mapping.names[i] for i in ni],'angles_rad':np.asarray(angles).tolist(),
        'model_sha256':model_sha},indent=2)+'\n')
    rigid=RigidReference();objid=m.body('drag_sample').id;rootid=m.body('torso').id
    initial_obj=d.xpos[objid].copy();initial_root=d.qpos[:3].copy()
    object_x_velocity_adr=int(m.joint('drag_sample_free').dofadr[0])
    duration=8.;steps=round(duration/m.opt.timestep)
    max_tilt=0.;maxheight=0.;max_loop=0.;pad_contacts=0;drag_forces=[];trace=[]
    saturations=np.zeros(len(mapping.names),dtype=int)
    for step in range(steps):
        t=step*m.opt.timestep
        targets[-1]=mapping.home[-1] if .5<=t<6.5 else start[mapping.qpos[-1]]
        if t>=1.5:
            u=min(1.,(t-1.5)/4.);fraction=10*u**3-15*u**4+6*u**5
            index=min(29,int(fraction*30));mix=fraction*30-index
            targets[ni]=(1-mix)*angles[index]+mix*angles[index+1]
        ff=d.qfrc_bias[mapping.dof].copy()
        ff+=rigid.double_support_torque(d.qpos[mapping.qpos],d.xmat[rootid].reshape(3,3))
        torque=mapping.torque(d.qpos[mapping.qpos],d.qvel[mapping.dof],targets,ff)
        torque[-1]=np.clip(torque[-1],-args.grip_torque,args.grip_torque)
        saturations+=abs(torque)>=mapping.limits-1e-6;d.ctrl[mapping.actuator]=torque
        mujoco.mj_step(m,d)
        max_tilt=max(max_tilt,float(np.arccos(np.clip(d.xmat[rootid].reshape(3,3)[2,2],-1,1))))
        maxheight=max(maxheight,float(d.xpos[objid,2]))
        max_loop=max(max_loop,float(np.linalg.norm(d.site('jaw_loop').xpos-d.site('follower_loop').xpos)))
        for ci,c in enumerate(d.contact):
            names=(m.geom(c.geom1).name,m.geom(c.geom2).name)
            if 'drag_block' in names and any('pad' in name for name in names):pad_contacts+=1
            if 2.<t<5.5 and abs(d.qvel[object_x_velocity_adr])>.005 and set(names)=={'floor','drag_block'}:
                contact_force=np.zeros(6);mujoco.mj_contactForce(m,d,ci,contact_force)
                f_world=c.frame.reshape(3,3).T@contact_force[:3]
                drag_forces.append(float(np.linalg.norm(f_world[:2])))
        if step%200==0:trace.append({'time_s':t,'sample_m':d.xpos[objid].tolist(),'root_m':d.qpos[:3].tolist()})
    displacement=float(d.xpos[objid,0]-initial_obj[0])
    median_force=float(np.median(drag_forces)) if drag_forces else 0.
    result={'scope':'specified 90 mm neck-pull, both feet grounded; not walking drag or autonomous task acceptance',
            'model_sha256':model_sha,'sample_mass_kg':.30,'floor_friction_input':.8,
            'sample_friction_input':.7,'nominal_mu_mg_N':.7*.30*9.81,
            'median_observed_floor_tangent_N':median_force,'drag_force_samples':len(drag_forces),
            'sample_displacement_m':displacement,'max_sample_center_height_m':maxheight,
            'grasp_pad_contact_samples':pad_contacts,'max_torso_tilt_deg':float(np.degrees(max_tilt)),
            'root_displacement_m':float(np.linalg.norm(d.qpos[:3]-initial_root)),
            'max_loop_residual_mm':max_loop*1000,'grip_torque_limit_Nm':args.grip_torque,
            'root_free':True,'sample_free':True,'object_attachment_constraints':0,'vision_used':False,
            'trace':trace,'torque_saturation_steps':dict(zip(mapping.names,map(int,saturations))),
            'pass':bool(displacement>.05 and maxheight<.04 and pad_contacts>0 and
                        np.degrees(max_tilt)<5 and max_loop<.0005 and median_force>=1.8)}
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='trace'},indent=2))
    return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
