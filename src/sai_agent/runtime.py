"""Named-joint adapter for reduced and fully articulated MuJoCo models."""
import numpy as np
import mujoco
from .control import torque_numpy

LEG_NAMES=[f'{leg}_{axis}' for leg in ['front_left','front_right','rear_left','rear_right']
           for axis in ['haa','hip','knee','wheel']]
ARM_NAMES=['so101_'+name for name in ['shoulder_pan','shoulder_lift','elbow_flex',
                                    'wrist_flex','wrist_roll','gripper']]


class JointAdapter:
    def __init__(self,model):
        self.model=model
        self.jids=np.array([model.joint(name).id for name in LEG_NAMES])
        self.qadr=model.jnt_qposadr[self.jids]
        self.vadr=model.jnt_dofadr[self.jids]
        self.aids=[]
        for jid in self.jids:
            matches=np.flatnonzero(model.actuator_trnid[:,0]==jid)
            assert len(matches)==1,model.joint(jid).name
            self.aids.append(int(matches[0]))
        self.held=[]
        for name in ARM_NAMES+['cargo_drive']:
            jid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,name)
            if jid<0:continue
            aids=np.flatnonzero(model.actuator_trnid[:,0]==jid)
            assert len(aids)==1,name
            self.held.append((name,int(model.jnt_qposadr[jid]),int(model.jnt_dofadr[jid]),int(aids[0])))

    def state(self,data):
        return np.r_[data.qpos[:7],data.qpos[self.qadr]],np.r_[data.qvel[:6],data.qvel[self.vadr]]

    def apply(self,data,target):
        q,v=self.state(data)
        data.ctrl[self.aids]=torque_numpy(q,v,target)
        for name,qa,va,act in self.held:
            if name=='cargo_drive':
                data.ctrl[act]=np.clip(-.25*data.qpos[qa]-.015*data.qvel[va],-.12,.12)
            else:
                cap=1.4 if name=='so101_gripper' else 2.94
                data.ctrl[act]=np.clip(-998.22*data.qpos[qa]-2.731*data.qvel[va]+data.qfrc_bias[va],-cap,cap)
