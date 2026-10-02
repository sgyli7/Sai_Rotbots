"""Standalone MuJoCo training environment with the shared 53/10 contract."""
from __future__ import annotations

from pathlib import Path
import hashlib

import mujoco
import numpy as np

from .control import ACTION_POSITION_SCALE_RAD, CONTROL_DT, TORQUE_UPDATE_DT, JointMap, observation
from .rigid import RigidReference
from ..paths import resource_root


class LocomotionEnv:
    def __init__(self, num_envs=8, seed=20260928, model_path: Path | None=None, spec=None):
        self.rng=np.random.default_rng(seed);self.num_envs=num_envs
        self.model_path=model_path or resource_root()/'robots/Goose_V0.1/models/full/robot.xml'
        self.source_model_sha256=hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        self.model=mujoco.MjModel.from_xml_path(str(self.model_path));self.mapping=JointMap(self.model,spec)
        transfer_path=self.model_path.parent/'rigid_transfer.json'
        import json
        transfer=json.loads(transfer_path.read_text())
        if transfer['model_sha256']!=self.source_model_sha256 or transfer['control']['action_reference_pose']!='standing':
            raise ValueError('Training model and standing action reference disagree')
        if transfer['control']['torque_feedforward']!='neutral_rigid_gravity':
            raise ValueError('Training torque profile differs from backend contract')
        self.rigid=RigidReference(transfer_path)
        stance=transfer['reference_poses']['standing']
        self.stance_root=np.array([*stance['root_position_m'],*stance['root_orientation_wxyz']])
        self.stance=np.array([stance['active_joint_positions_rad'][n] for n in self.mapping.names])
        self.data=[mujoco.MjData(self.model) for _ in range(num_envs)]
        self.actions=np.zeros((num_envs,10));self.commands=np.zeros((num_envs,3))
        self.phase=np.zeros(num_envs);self.age=np.zeros(num_envs,dtype=int)
        self.torso=self.model.body('torso').id;self.substeps=round(CONTROL_DT/self.model.opt.timestep)
        self.torque_substeps=round(TORQUE_UPDATE_DT/self.model.opt.timestep)
        if (abs(self.substeps*self.model.opt.timestep-CONTROL_DT)>1e-9 or
                abs(self.torque_substeps*self.model.opt.timestep-TORQUE_UPDATE_DT)>1e-9 or
                self.substeps%self.torque_substeps):
            raise ValueError('Physics, policy and torque periods do not align')
        self.home_root_z=self.stance_root[2];self.last_cost=np.zeros(num_envs)
        for i in range(num_envs):self.reset(i)

    def reset(self,i,command=None,randomize=True):
        d=self.data[i];mujoco.mj_resetDataKeyframe(self.model,d,0)
        d.qpos[:7]=self.stance_root
        d.qpos[self.mapping.qpos]=self.stance
        if randomize:
            d.qpos[self.mapping.qpos[:10]]+=self.rng.uniform(-.015,.015,10)
        mujoco.mj_forward(self.model,d)
        self.actions[i]=0;self.phase[i]=0;self.age[i]=0
        self.commands[i]=command if command is not None else [self.rng.uniform(-.025,.12),0,self.rng.uniform(-.25,.25)]

    def observations(self):
        out=[]
        for i,d in enumerate(self.data):
            r=d.xmat[self.torso].reshape(3,3)
            velocity=np.zeros(6);mujoco.mj_objectVelocity(self.model,d,mujoco.mjtObj.mjOBJ_BODY,self.torso,velocity,1)
            out.append(observation(velocity[:3],r.T@np.array([0,0,-1.]),self.commands[i],
                                   d.qpos[self.mapping.qpos],d.qvel[self.mapping.dof],self.mapping.home,
                                   self.actions[i],self.phase[i]))
        return np.asarray(out,dtype=np.float32)

    def step(self,actions):
        actions=np.clip(np.asarray(actions,dtype=float),-1,1)
        if actions.shape!=(self.num_envs,10) or not np.isfinite(actions).all():raise ValueError('Invalid action batch')
        rewards=np.zeros(self.num_envs,dtype=np.float32);done=np.zeros(self.num_envs,dtype=bool)
        info=[]
        for i,d in enumerate(self.data):
            target=self.stance.copy();target[:10]+=ACTION_POSITION_SCALE_RAD*actions[i]
            cost=0.
            for substep in range(self.substeps):
                if substep%self.torque_substeps==0:
                    q=d.qpos[self.mapping.qpos]
                    rot=d.xmat[self.torso].reshape(3,3)
                    ff=self.rigid.gravity_torque(q,rot)
                    torque=self.mapping.torque(q,d.qvel[self.mapping.dof],target,ff)
                d.ctrl[self.mapping.actuator]=torque;cost+=float(np.mean((torque/self.mapping.limits)**2))
                mujoco.mj_step(self.model,d)
            r=d.xmat[self.torso].reshape(3,3)
            v=np.zeros(6);mujoco.mj_objectVelocity(self.model,d,mujoco.mjtObj.mjOBJ_BODY,self.torso,v,1)
            tilt=float(np.arccos(np.clip(r[2,2],-1,1)))
            # Root velocity is used only to grade training, never in observation.
            tracking=float(np.exp(-np.sum((v[3:5]-self.commands[i,:2])**2)/.015))
            yaw=float(np.exp(-(v[2]-self.commands[i,2])**2/.06))
            height=float(np.exp(-(d.qpos[2]-self.home_root_z)**2/.001))
            action_change=float(np.mean((actions[i]-self.actions[i])**2))
            rewards[i]=1.5*tracking+.5*yaw+.7*height+.5*np.cos(tilt)-.08*cost/self.substeps-.10*action_change-.003*np.mean(d.qvel[self.mapping.dof[:10]]**2)
            self.actions[i]=actions[i];self.phase[i]=(self.phase[i]+2*np.pi*CONTROL_DT/1.2)%(2*np.pi);self.age[i]+=1
            failed=tilt>.65 or d.qpos[2]<self.home_root_z-.08 or not np.isfinite(d.qpos).all()
            done[i]=failed or self.age[i]>=600
            if failed:rewards[i]-=4
            info.append({'failure':bool(failed),'timeout':bool(self.age[i]>=600),'tilt_rad':tilt,'vx':float(v[3]),'yaw_rate':float(v[2])})
            if done[i]:self.reset(i)
        return self.observations(),rewards,done,info
