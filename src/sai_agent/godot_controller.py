"""Godot observations to motor targets; this process never advances physics."""
import json
import socket
import numpy as np
import mujoco
import onnxruntime as ort
from scipy.spatial.transform import Rotation
from .control import observation_numpy,targets_numpy,targets_stairs_numpy,filter_action_numpy,HeadingHold
from .runtime import JointAdapter,ARM_NAMES


class GodotController:
    def __init__(self,root):
        self.spec=json.loads((root/'models/full/robot.json').read_text())
        self.model=mujoco.MjModel.from_xml_path(str(root/'models/full/robot.xml'))
        self.data=mujoco.MjData(self.model)
        self.adapter=JointAdapter(self.model)
        names=[b['joint']['name'] for b in self.spec['bodies'].values() if b.get('parent') is not None]
        self.qadr=np.array([self.model.jnt_qposadr[self.model.joint(name).id] for name in names])
        self.vadr=np.array([self.model.jnt_dofadr[self.model.joint(name).id] for name in names])
        self.armv=np.array([self.model.jnt_dofadr[self.model.joint(name).id] for name in ARM_NAMES])
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        self.policy=ort.InferenceSession(str(root/'policies/flat-v1.onnx'),options,providers=['CPUExecutionProvider'])
        stair_path=root/'policies/stairs-dev40.onnx'
        self.stair_policy=ort.InferenceSession(str(stair_path),options,providers=['CPUExecutionProvider']) if stair_path.is_file() else None
        self.previous=np.zeros(16)
        self.crouch=0.
        self.heading=HeadingHold()

    def command(self,state):
        if state.get('robot_id')!='Sai_Agent_001' or state.get('physics_owner')!='Godot/Jolt':
            raise ValueError('Unexpected robot or physics owner')
        q=np.asarray(state['q']);v=np.asarray(state['v'])
        if q.shape!=(25,) or v.shape!=(25,) or not np.isfinite(np.r_[q,v]).all():
            raise ValueError('Invalid articulated joint state')
        rotation=np.asarray(state['base_rotation_columns']).T
        self.data.qpos[:3]=state['base_position']
        self.data.qpos[3:7]=Rotation.from_matrix(rotation).as_quat(scalar_first=True)
        self.data.qvel[:3]=state['base_linear_world']
        self.data.qvel[3:6]=rotation.T@state['base_angular_world']
        self.data.qpos[self.qadr]=q
        self.data.qvel[self.vadr]=v
        # Forward kinematics/bias only. No mj_step and no body pose returned.
        mujoco.mj_forward(self.model,self.data)
        command=np.asarray(state['command'],dtype=float)
        scan=np.asarray(state['terrain_heights'])
        stairs=self.stair_policy is not None and np.ptp(scan)>.004 and command[0]>.015
        if stairs:command[0]=min(command[0],.12)
        self.crouch+=np.clip(command[2]-self.crouch,-.04,.04)
        flatq,flatv=self.adapter.state(self.data)
        obs=observation_numpy(flatq,flatv,command[:2],self.crouch,self.previous,
            float(state['time'])*2*np.pi/(3.2 if stairs else 2.4),scan)
        selected=self.stair_policy if stairs else self.policy
        action=filter_action_numpy(selected.run(None,{'obs':obs[None]})[0][0],command)
        target=targets_stairs_numpy(action,command,self.crouch,float(state['time'])/3.2,scan) if stairs else targets_numpy(action,command,self.crouch)
        yaw=np.arctan2(rotation[1,0],rotation[0,0])
        target=self.heading.apply(target,command,yaw,flatv[5])
        self.previous=action
        return dict(mode='transport',stage='stairs' if stairs else 'crouched' if self.crouch>.5 else 'rolling',
            target_leg=target.tolist(),wheel_speed=target[3::4].tolist(),
            target_arm=[0.]*6,arm_bias=self.data.qfrc_bias[self.armv].tolist(),
            grip_cap=1.4,cargo_target_rad=0.,policy_action=action.tolist(),
            policy_observation=obs.tolist(),physics_advanced_by_controller=False,
            contract_id='sai-flat-v1+heading-v1')

    def serve(self,listener,stop):
        while not stop.is_set():
            try:client,_=listener.accept();break
            except socket.timeout:continue
        else:return
        with client:
            client.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
            client.settimeout(.25)
            buffer=b''
            while not stop.is_set():
                try:packet=client.recv(65536)
                except socket.timeout:continue
                if not packet:return
                buffer+=packet
                if len(buffer)>1048576:raise ValueError('Oversized simulation message')
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1)
                    state=json.loads(line)
                    if state.get('finish'):return
                    response=self.command(state)
                    client.sendall((json.dumps(response,separators=(',',':'))+'\n').encode())
