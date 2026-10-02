"""Free-base, torque-limited standing evaluation for Goose's current model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from sai_agent.goose.control import CONTRACT_VERSION, TORQUE_UPDATE_DT, JointMap
from sai_agent.goose.rigid import RigidReference
from sai_agent.paths import resource_root


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=4.)
    pose_group=parser.add_mutually_exclusive_group()
    pose_group.add_argument('--ground-pose',action='store_true')
    pose_group.add_argument('--standing-pose',action='store_true')
    parser.add_argument('--shared-controller',action='store_true',help='SI neutral-model gravity feedforward')
    parser.add_argument('--no-double-support',action='store_true',
                        help='With shared controller, use gravity only to match normal policy mode')
    parser.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/stand/result.json'))
    args=parser.parse_args()
    if args.no_double_support and not args.shared_controller:
        parser.error('--no-double-support requires --shared-controller')
    robot=resource_root()/'robots/Goose_V0.1';path=robot/'models/full/robot.xml'
    model=mujoco.MjModel.from_xml_path(str(path));data=mujoco.MjData(model);mapping=JointMap(model)
    rigid=RigidReference() if args.shared_controller else None
    if rigid is not None and rigid.transfer['model_sha256']!=hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Neutral controller model hash differs from evaluation model')
    mujoco.mj_resetDataKeyframe(model,data,0)
    if args.ground_pose or args.standing_pose:
        ground=np.asarray(json.loads((robot/'evidence/ground_reach_check.json').read_text())['qpos'])
        if args.ground_pose:data.qpos[:]=ground
        else:
            data.qpos[:7]=ground[:7]
            for name in mapping.names[:10]:
                address=model.joint(name).qposadr[0];data.qpos[address]=ground[address]
    mujoco.mj_forward(model,data)
    target=data.qpos[mapping.qpos].copy();start=data.qpos[:3].copy()
    maximum_joint_error=0.;maximum_tilt=0.;saturation=np.zeros(model.nu,dtype=int);bad_contact_steps=0
    torque_period=round(TORQUE_UPDATE_DT/model.opt.timestep) if rigid is not None else 1
    if rigid is not None and abs(torque_period*model.opt.timestep-TORQUE_UPDATE_DT)>1e-9:
        raise ValueError('Physics and shared-controller torque periods do not align')
    for step in range(round(args.duration/model.opt.timestep)):
        if step%torque_period==0:
            q=data.qpos[mapping.qpos]
            rot=data.xmat[model.body('torso').id].reshape(3,3)
            ff=(rigid.gravity_torque(q,rot)+
                (np.zeros(len(q)) if args.no_double_support else rigid.double_support_torque(q,rot))) if rigid is not None else data.qfrc_bias[mapping.dof]
            u=mapping.torque(q,data.qvel[mapping.dof],target,ff)
        data.ctrl[mapping.actuator]=u
        saturation+=abs(u)>=mapping.limits-1e-6
        mujoco.mj_step(model,data)
        if step%10==0:
            maximum_joint_error=max(maximum_joint_error,float(np.max(abs(data.qpos[mapping.qpos]-target))))
            rot=data.xmat[model.body('torso').id].reshape(3,3)
            maximum_tilt=max(maximum_tilt,float(np.arccos(np.clip(rot[2,2],-1,1))))
            for c in data.contact:
                names=(model.geom(c.geom1).name,model.geom(c.geom2).name)
                if c.dist<-.002 and not (names[0]=='floor' and names[1].endswith('_foot')):
                    bad_contact_steps+=1
    result={'scope':'free-base standing only, not walking or grasp task acceptance','duration_s':args.duration,
            'pose_name':'ground_side_grasp' if args.ground_pose else 'standing' if args.standing_pose else 'home',
            'ground_pose':args.ground_pose,'shared_controller':args.shared_controller,'root_start_m':start.tolist(),'root_end_m':data.qpos[:3].tolist(),
            'root_displacement_m':float(np.linalg.norm(data.qpos[:3]-start)),
            'max_torso_tilt_deg':float(np.degrees(maximum_tilt)),
            'max_joint_error_deg':float(np.degrees(maximum_joint_error)),
            'torque_saturation_steps':dict(zip(mapping.names,map(int,saturation))),
            'unexpected_contact_count':bad_contact_steps,'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'control_contract_version':CONTRACT_VERSION,
            'torque_update_dt_s':torque_period*model.opt.timestep,
            'control_source_sha256':hashlib.sha256((resource_root()/'src/sai_agent/goose/control.py').read_bytes()).hexdigest(),
            'neutral_transfer_sha256':hashlib.sha256((robot/'models/full/rigid_transfer.json').read_bytes()).hexdigest() if rigid is not None else None,
            'robot_root_free':True,'external_root_support':False,
            'gravity_compensation':('SI neutral-model gravity only' if args.no_double_support else
                                    'SI neutral-model gravity + encoder/IMU estimated static two-foot support')
                if rigid is not None else 'model bias at measured joint/root state',
            'pass':bool(maximum_tilt<np.radians(5) and maximum_joint_error<np.radians(5) and np.linalg.norm(data.qpos[:3]-start)<.02
                        and np.max(saturation)/round(args.duration/model.opt.timestep)<.10 and bad_contact_steps==0)}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
