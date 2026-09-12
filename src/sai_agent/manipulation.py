"""Contact-only SO101 pickup/place on a free wheel-leg chassis.

This is a model-state feedback controller following the existing audited path,
not a learned grasp or VLA. The item has a freejoint throughout; only reset may
set initial state. No equality, weld, mocap item or carried-object pose update.
"""
import json,math,time
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation
from .so101_fk import Arm,metre
from .paths import resource_root
ROOT=resource_root()
HERE=ROOT/"models/full"

class Task:
    def __init__(self,no_grip=False,model_dir=HERE):
        self.spec=json.loads((model_dir/'robot.json').read_text())
        self.model=mujoco.MjModel.from_xml_path(str(model_dir/'robot.xml'))
        self.data=mujoco.MjData(self.model);self.ik=mujoco.MjData(self.model)
        self.arm=Arm();self.home=np.array(self.spec['arm_home_source_deg'])
        self.arm_joints=[self.model.joint('so101_'+a['joint_candidate']).id for a in self.arm.axes]
        self.aq=np.array([self.model.jnt_qposadr[j] for j in self.arm_joints]);self.av=np.array([self.model.jnt_dofadr[j] for j in self.arm_joints])
        self.aa=np.array([self.model.actuator('so101_'+a['joint_candidate']+'_motor').id for a in self.arm.axes])
        # Controller ceiling for a 100 g item. The catalogue/upstream 2.94 Nm
        # cap is excessive for this small grasp and drives soft-contact creep.
        self.grip_cap=1.4
        self.leg_joints=[self.model.joint(k+'_'+j).id for k in self.spec['leg_order'] for j in ['haa','hip','knee','wheel']]
        self.lq=np.array([self.model.jnt_qposadr[j] for j in self.leg_joints]);self.lv=np.array([self.model.jnt_dofadr[j] for j in self.leg_joints])
        self.la=np.array([self.model.actuator(k+'_'+j+'_motor').id for k in self.spec['leg_order'] for j in ['haa','hip','knee','wheel']])
        self.gripper=self.model.body('arm_gripper').id;self.item=self.model.body('item').id
        self.site=self.model.site('tool_center').id;self.item_geom=self.model.geom('item_box').id
        self.frames=json.loads((ROOT/'models/tasks/pick-place.json').read_text())
        self.no_grip=no_grip
        self.end=1.5+(len(self.frames)-1)*.22+2
        self.target_arm=np.zeros(6);self.target_leg=np.zeros(16)
        self.last_control=-1;self.label='ready';self.samples=[]
        self.nominal_frame=metre(self.arm.pose(self.home)['gripper'])
        mujoco.mj_forward(self.model,self.data)

    def path(self,t):
        u=np.clip((t-1.5)/.22,0,len(self.frames)-1);i=min(int(u),len(self.frames)-2);alpha=u-i
        a,b=self.frames[i],self.frames[i+1]
        q=(1-alpha)*np.array(a['q'])+alpha*np.array(b['q'])
        drop=(1-alpha)*a['drop_mm']+alpha*b['drop_mm']
        # The geometric first-contact angle has zero compression. A 1.0 degree
        # additional setpoint creates clamp force through the torque-limited servo.
        if a['label'] in ['close','lift','raise_body','front_clearance','transfer_1','transfer_2','transfer_3','transfer_4','over_cargo','place']:
            q[5]+=max(0,min(1,(q[5]-75)/3.6468))*1.0
        if self.no_grip:q[5]=60
        return q,drop,b['label']

    def leg_reference(self,drop_mm):
        out=np.zeros(16)
        for i,(front,side) in enumerate([(1,1),(1,-1),(-1,1),(-1,-1)]):
            down=.172812737-drop_mm*.001
            beta=-front*math.acos(np.clip((down**2-.09**2-.11**2)/(2*.09*.11),-1,1))
            theta=-math.atan2(.11*math.sin(beta),.09+.11*math.cos(beta))
            theta0=front*math.atan2(.05,.074833147);beta0=-front*(math.atan2(.05,.09797959)+math.atan2(.05,.074833147))
            out[4*i+1]=side*(theta0-theta);out[4*i+2]=side*(beta0-beta)
            out[4*i+3]=-out[4*i+1]-out[4*i+2]
        return out

    def control_target(self):
        q,drop,self.label=self.path(self.data.time)
        self.target_leg=self.leg_reference(drop)
        desired=metre(self.arm.pose(q,drop)['gripper'])
        target_point=self.arm.tool(q,drop)[0]*.001
        target_point+=self.path_translation(self.data.time)
        # Counter chassis sag/roll with model-state IK, without editing the
        # simulated chassis or object. Five arm axes do not provide arbitrary 6D poses.
        self.ik.qpos[:]=self.data.qpos;self.ik.qpos[self.aq]=np.deg2rad(q-self.home)
        target_rot=desired[:3,:3]@self.nominal_frame[:3,:3].T
        jp=np.zeros((3,self.model.nv));jr=np.zeros_like(jp)
        for _ in range(5):
            mujoco.mj_fwdPosition(self.model,self.ik)
            mujoco.mj_jacSite(self.model,self.ik,jp,jr,self.site)
            errp=target_point-self.ik.site_xpos[self.site]
            errr=Rotation.from_matrix(target_rot@self.ik.xmat[self.gripper].reshape(3,3).T).as_rotvec()
            a=np.r_[jp[:,self.av[:5]],.05*jr[:,self.av[:5]]];b=np.r_[errp,.05*errr]
            dq=np.linalg.solve(a.T@a+np.eye(5)*1e-7,a.T@b)
            self.ik.qpos[self.aq[:5]]+=np.clip(dq,-.06,.06)
            self.ik.qpos[self.aq]=np.clip(self.ik.qpos[self.aq],self.model.jnt_range[self.arm_joints,0]+.001,self.model.jnt_range[self.arm_joints,1]-.001)
        self.target_arm=self.ik.qpos[self.aq].copy();self.target_point=target_point

    def path_translation(self,time_s):
        """Optional observed-target translation; fixed-path tasks remain unchanged."""
        return np.zeros(3)

    def step(self):
        tick=int((self.data.time+1e-8)*50)
        if tick!=self.last_control:self.last_control=tick;self.control_target()
        q,v=self.data.qpos,self.data.qvel
        leg_u=80*(self.target_leg-q[self.lq])-2*v[self.lv]
        for i in [3,7,11,15]:leg_u[i]=2*(self.target_leg[i]-q[self.lq[i]])-.4*v[self.lv[i]]
        limits=np.tile([8,8,8,1.3],4)
        self.data.ctrl[self.la]=np.clip(leg_u,-limits,limits)
        # Upstream STS3215 simulated servo gains and torque cap, with gravity
        # feedforward from this model. These are not measured servo calibration.
        arm_u=998.22*(self.target_arm-q[self.aq])-2.731*v[self.av]+self.data.qfrc_bias[self.av]
        self.data.ctrl[self.aa]=np.clip(arm_u,-2.94,2.94)
        self.data.ctrl[self.aa[-1]]=np.clip(self.data.ctrl[self.aa[-1]],-self.grip_cap,self.grip_cap)
        mujoco.mj_step(self.model,self.data)
        if tick%2==0 and (not self.samples or self.data.time-self.samples[-1]['time']>.039):self.record()

    def record(self):
        contacts=[];force=np.zeros(6)
        for c in range(self.data.ncon):
            ct=self.data.contact[c]
            if self.item_geom in ct.geom:
                other=int(ct.geom[0] if ct.geom[1]==self.item_geom else ct.geom[1]);mujoco.mj_contactForce(self.model,self.data,c,force)
                contacts.append(dict(other=self.model.geom(other).name,normal_N=float(force[0]),distance_m=float(ct.dist)))
        chassis=self.model.body('chassis').id;r=self.data.xmat[chassis].reshape(3,3)
        local=r.T@(self.data.xpos[self.item]-self.data.xpos[chassis])+np.array(self.spec['bodies']['chassis']['origin_m'])
        self.samples.append(dict(time=float(self.data.time),stage=self.label,object_world_m=self.data.xpos[self.item].tolist(),object_chassis_m=local.tolist(),
            base_world_m=self.data.xpos[chassis].tolist(),upright=float(r[2,2]),tool_m=self.data.site_xpos[self.site].tolist(),
            tool_target_error_m=float(np.linalg.norm(self.target_point-self.data.site_xpos[self.site])),
            arm_source_deg=(np.rad2deg(self.data.qpos[self.aq])+self.home).tolist(),arm_torque_Nm=self.data.actuator_force[self.aa].tolist(),
            contacts=contacts,qpos=self.data.qpos.tolist(),qvel=self.data.qvel.tolist()))

    def run(self):
        start=time.time()
        while self.data.time<self.end:
            self.step()
            if not np.isfinite(self.data.qpos).all() or self.data.xmat[self.model.body('chassis').id,8]<.65:break
        final=self.samples[-1];p=final['object_chassis_m']
        lift=max(x['object_world_m'][2] for x in self.samples)
        held=[x for x in self.samples if any(c['other'].startswith('arm_gripper') for c in x['contacts']) and any(c['other'].startswith('arm_moving_jaw') for c in x['contacts'])]
        placed=(-.14<p[0]<-.038 and abs(p[1])<.11 and .273<p[2]<.30)
        report=dict(status='scripted contact-only physical task; not VLA or learned grasp',no_grip_control=self.no_grip,
            simulation_seconds=float(self.data.time),wall_seconds=time.time()-start,
            max_object_height_m=lift,two_finger_contact_samples=len(held),
            final_object_chassis_m=p,placed_in_cargo=bool(placed),
            success=bool(placed and lift>.20 and len(held)>10 and self.data.time>=self.end),
            max_arm_torque_Nm=np.max(np.abs([s['arm_torque_Nm'] for s in self.samples]),axis=0).tolist(),
            min_upright=min(s['upright'] for s in self.samples),
            gripper_control_cap_Nm=self.grip_cap,
            initial_only_state_assignment=True,total_model_constraints=int(self.model.neq),
            limitations=self.spec['limitations'],samples=self.samples)
        return report
