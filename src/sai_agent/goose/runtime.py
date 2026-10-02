"""Common SI sensor-to-torque controller for independent backend consumers."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from .control import ACTION_POSITION_SCALE_RAD, ACTION_SIZE, CONTROL_DT, CONTRACT_VERSION, observation
from .protocol import SensorFrame,torque_message
from .rigid import RigidReference


class BackendController:
    def __init__(self,transfer_path:Path,policy_path:Path|None=None,
                 policy_metadata_path:Path|None=None,allow_experimental=False,static_double_support=False):
        self.rigid=RigidReference(transfer_path);transfer=self.rigid.transfer
        self.names=transfer['control']['encoder_joint_names'];self.contract=transfer['control']
        if self.contract['version']!=CONTRACT_VERSION:raise ValueError('Unsupported controller contract')
        by_name={j['name']:j for j in transfer['joints']};joints=[by_name[n] for n in self.names]
        self.home=np.array([j['home'] for j in joints]);self.ranges=np.array([j['range'] for j in joints])
        self.kp=np.array([j['kp'] for j in joints]);self.kd=np.array([j['kd'] for j in joints])
        stance=transfer['reference_poses']['standing']['active_joint_positions_rad']
        self.stance=np.array([stance[name] for name in self.names],dtype=float)
        if self.contract['action_reference_pose']!='standing' or self.contract['action_position_scale_rad']!=ACTION_POSITION_SCALE_RAD:
            raise ValueError('Unsupported action reference')
        if self.contract.get('torque_feedforward')!='neutral_rigid_gravity':
            raise ValueError('Unsupported torque feedforward')
        self.limits=np.array([j['torque_limit_Nm'] for j in joints]);self.targets=self.stance.copy()
        self.speed_limits=np.array([j['speed_limit_rad_s'] for j in joints])
        self.action_indices=np.array([self.names.index(n) for n in self.contract['action_joint_names']])
        self.previous_action=np.zeros(ACTION_SIZE);self.command=np.zeros(3)
        self.last_sequence=-1;self.last_timestamp=-1.;self.static_double_support=static_double_support
        self.last_policy_timestamp=-1.
        self.session=None
        if policy_path is not None:
            import hashlib
            import onnxruntime as ort
            if policy_metadata_path is None:raise ValueError('Policy metadata required')
            meta=json.loads(policy_metadata_path.read_text())
            for key in ('version','encoder_joint_names','action_joint_names','observation_size','action_size',
                        'action_reference_pose','action_position_scale_rad','torque_feedforward'):
                if meta[key]!=self.contract[key]:raise ValueError('Policy contract mismatch: '+key)
            if meta['model_sha256']!=transfer['model_sha256']:raise ValueError('Policy model differs from backend model')
            if hashlib.sha256(policy_path.read_bytes()).hexdigest()!=meta['policy_sha256']:raise ValueError('Policy hash mismatch')
            if not meta.get('walking_acceptance',False) and not allow_experimental:
                raise ValueError('Experimental walking policy needs explicit experimental mode')
            self.session=ort.InferenceSession(str(policy_path),providers=['CPUExecutionProvider'])

    def tick(self,frame:SensorFrame):
        if frame.sequence<=self.last_sequence or frame.timestamp_s<=self.last_timestamp:
            raise ValueError('Stale/out-of-order sensor frame')
        if self.last_timestamp>=0 and frame.timestamp_s-self.last_timestamp>.08:
            raise TimeoutError('Sensor gap exceeds control watchdog')
        self.last_sequence=frame.sequence;self.last_timestamp=frame.timestamp_s
        q=frame.positions_rad;dq=frame.velocities_rad_s
        if np.any(q<self.ranges[:,0]-.08) or np.any(q>self.ranges[:,1]+.08):
            raise ValueError('Encoder position outside configured joint envelope')
        gravity=np.asarray(frame.gravity_body_unit)
        rotation=Rotation.align_vectors(np.array([[0.,0.,-1.]]),gravity[None,:])[0].as_matrix()
        tilt=np.arccos(np.clip(-gravity[2],-1,1))
        if self.static_double_support and tilt>.18:raise RuntimeError('Static stance lost; controller stopped')
        if self.session is not None and (self.last_policy_timestamp<0 or
                frame.timestamp_s-self.last_policy_timestamp>=CONTROL_DT-1e-6):
            obs=observation(frame.gyro_body_rad_s,gravity,self.command,q,dq,self.home,
                            self.previous_action,2*np.pi*frame.timestamp_s/1.2)
            action=self.session.run(None,{'observation':obs[None,:]})[0][0]
            if action.shape!=(ACTION_SIZE,) or not np.isfinite(action).all():raise FloatingPointError('Invalid policy output')
            self.previous_action=np.clip(action,-1,1)
            self.targets[self.action_indices]=self.stance[self.action_indices]+ACTION_POSITION_SCALE_RAD*self.previous_action
            self.last_policy_timestamp=frame.timestamp_s
        targets=np.clip(self.targets,self.ranges[:,0],self.ranges[:,1])
        ff=self.rigid.gravity_torque(q,rotation)
        if self.static_double_support:ff+=self.rigid.double_support_torque(q,rotation)
        torque=np.clip(self.kp*(targets-q)-self.kd*dq+ff,-self.limits,self.limits)
        overspeed=(np.abs(dq)>self.speed_limits) & (torque*dq>0)
        torque[overspeed]=0
        return torque_message(frame,self.names,torque,self.limits,3*CONTROL_DT)
