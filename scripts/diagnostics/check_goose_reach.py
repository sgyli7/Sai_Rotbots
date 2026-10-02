"""Solve and check named Goose poses without claiming dynamic task success."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from sai_agent.goose.spec import load_spec
from sai_agent.paths import resource_root


def main():
    root=resource_root();robot=root/'robots/Goose_V0.1'
    spec=load_spec();model=mujoco.MjModel.from_xml_path(str(robot/'models/full/robot.xml'))
    data=mujoco.MjData(model)
    neck=[j for j in spec['joints'] if j['control_group']=='neck']
    adr=[int(model.joint(j['name']).qposadr[0]) for j in neck]
    home=model.key_qpos[0].copy()
    target=np.array([.36,0,.019])
    pitch_target=.35
    orientation=Rotation.from_euler('yx',[pitch_target,np.pi/2]).as_matrix()
    # scipy extrinsic yx produces Rx @ Ry; desired local roll is Ry @ Rx.
    orientation=Rotation.from_rotvec([0,pitch_target,0]).as_matrix() @ Rotation.from_rotvec([np.pi/2,0,0]).as_matrix()
    tip=model.site('task_center').id;head=model.body('head_roll').id
    def pose(x):
        data.qpos[:]=home
        data.qpos[adr]=x[:len(neck)]
        for side in ('left','right'):
            for name,value in [('hip_pitch',-x[-1]),('knee_pitch',2*x[-1]),('ankle_pitch',-x[-1])]:
                data.qpos[model.joint(f'{side}_{name}').qposadr[0]]=value
        gap=.024;closed=spec['beak']['closed_rad'];L=spec['beak']['crank_length_m']
        q=np.arcsin(np.sin(closed)-gap/L)
        for name,value in [('beak_drive',q),('passive_jaw_pin',-q),('passive_follower',q)]:
            data.qpos[model.joint(name).qposadr[0]]=value
        mujoco.mj_forward(model,data)
        height=min(data.site(name).xpos[2] for name in ('left_foot','right_foot'))
        data.qpos[2]-=height
        mujoco.mj_forward(model,data)
    def residual(x):
        pose(x)
        yaw,pitch,roll=Rotation.from_matrix(data.xmat[head].reshape(3,3)).as_euler('ZYX')
        # The agreed 5R neck leaves heading to root yaw/body alignment. Enforce
        # pitch and side-roll while allowing the grasp's feasible heading.
        error=np.array([pitch-pitch_target,roll-np.pi/2])
        return np.r_[10*(data.site_xpos[tip]-target),error,.03*(x[-1]-.35)]
    lo=[j['range_rad'][0] for j in neck]+[0.]
    hi=[j['range_rad'][1] for j in neck]+[.80]
    initial=[0,1.43,1.70,-2.75,np.pi/2,.35]
    result=least_squares(residual,initial,bounds=(lo,hi),xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=1000)
    pose(result.x)
    contacts=[{'geom1':model.geom(c.geom1).name,'geom2':model.geom(c.geom2).name,'depth_m':float(-c.dist)}
              for c in data.contact if c.dist<-.0001]
    record={'scope':'kinematic ground-side-grasp pose only; not dynamic grasp/transport acceptance',
            'model_sha256':hashlib.sha256((robot/'models/full/robot.xml').read_bytes()).hexdigest(),
            'target_m':target.tolist(),'actual_m':data.site_xpos[tip].tolist(),
            'position_error_m':float(np.linalg.norm(data.site_xpos[tip]-target)),
            'orientation_error_rad':float(np.linalg.norm(residual(result.x)[3:5])),
            'orientation_constraint':f'pitch {pitch_target} rad and roll pi/2; heading free within neck root yaw range',
            'actual_head_orientation_world_wxyz':data.xquat[head].tolist(),
            'neck_joint_names':[j['name'] for j in neck],'neck_angles_rad':result.x[:len(neck)].tolist(),
            'crouch_hip_rad':float(result.x[-1]),'root_position_m':data.qpos[:3].tolist(),
            'unexpected_penetrations':contacts,'qpos':data.qpos.tolist(),
            'pass':bool(np.linalg.norm(data.site_xpos[tip]-target)<.001 and not contacts)}
    path=robot/'evidence/ground_reach_check.json';path.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k!='qpos'},indent=2))
    return 0 if record['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
