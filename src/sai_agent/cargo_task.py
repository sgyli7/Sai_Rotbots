"""Physical pickup -> place -> belt-driven clamp -> original PPO loaded crawl."""
import xml.etree.ElementTree as ET
import numpy as np,mujoco
from .paths import resource_root
from .manipulation import Task
from .legacy_crawl import CrawlTransport
HERE=resource_root()/'models/full'

def load_course(path,height):
    tree=ET.parse(path)
    for mesh in tree.findall(".//asset/mesh"):
        mesh.set("file",str(path.parent/mesh.get("file")))
    for node in tree.iter('geom'):
        if node.get('name','').startswith('course_'):
            p=np.fromstring(node.get('pos'),sep=' ');p[2]=height-.04
            node.set('pos',' '.join(map(str,p)))
    return mujoco.MjModel.from_xml_string(ET.tostring(tree.getroot(),encoding='unicode'))

class CargoTask(Task):
    def __init__(self,height=.018,no_clamp=False,until=None):
        super().__init__(model_dir=HERE)
        self.model=load_course(HERE/'robot.xml',height);self.data=mujoco.MjData(self.model);self.ik=mujoco.MjData(self.model)
        self.height=height;self.no_clamp=no_clamp;self.grip_cap=1.4
        self.grasp_end=self.end;self.clamp_end=self.end+8.;self.transport=CrawlTransport();self.end=self.clamp_end+self.transport.duration
        if until is not None:self.end=until
        self.drive_command=None;self.cargo_target=0.;self.transport_started=False;self.abort_reason=None
        self.cj=[self.model.joint(n).id for n in ['cargo_slide_-1','cargo_slide_1','cargo_drive']]
        self.cq=np.array([self.model.jnt_qposadr[j] for j in self.cj]);self.cv=np.array([self.model.jnt_dofadr[j] for j in self.cj])
        self.ca=self.model.actuator('cargo_drive_motor').id;self.ratio=self.spec['cargo']['drive_metres_per_radian']
        self.pad_geoms=[self.model.geom(f'cargo_slide_{side}_contact_0').id for side in [-1,1]]
        self.wheel_bodies=[self.model.body(k+'_wheel').id for k in self.spec['leg_order']]
        self.course_contacts=set();self.previous_label=None
        self.physics_cargo_checks=0;self.outside_cargo_steps=0;self.unclamped_steps=0;self.max_lateral_m=0.
        mujoco.mj_forward(self.model,self.data)

    def pad_forces(self):
        out=np.zeros(2);force=np.zeros(6)
        for c in range(self.data.ncon):
            ct=self.data.contact[c]
            if self.item_geom not in ct.geom:continue
            for i,g in enumerate(self.pad_geoms):
                if g in ct.geom:mujoco.mj_contactForce(self.model,self.data,c,force);out[i]+=max(0,force[0])
        return out

    def cargo_bounds(self):
        b=self.model.body('chassis').id;r=self.data.xmat[b].reshape(3,3);ir=self.data.xmat[self.item].reshape(3,3)
        half=np.array(self.spec['object']['size_m'])/2
        corners=np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]])*half
        local=(corners@ir.T+self.data.xpos[self.item]-self.data.xpos[b])@r+np.array(self.spec['bodies']['chassis']['origin_m'])
        low,high=local.min(0),local.max(0)
        inside=low[0]>=-.146 and high[0]<=-.037 and low[1]>=-.112 and high[1]<=.112 and low[2]>.254 and high[2]<.315
        return np.array([low,high]),bool(inside)

    def observation(self):
        r=self.data.xmat[self.model.body('chassis').id].reshape(3,3)
        return dict(time=float(self.data.time),q=np.r_[self.data.qpos[self.lq],self.data.qpos[self.aq]].tolist(),
            v=np.r_[self.data.qvel[self.lv],self.data.qvel[self.av]].tolist(),base_position=self.data.qpos[:3].tolist(),
            base_rotation_columns=r.T.tolist(),base_linear_world=self.data.qvel[:3].tolist(),base_angular_world=(r@self.data.qvel[3:6]).tolist())

    def control_target(self):
        now=self.data.time
        if now+1e-6<self.grasp_end:super().control_target()
        elif now+1e-6<self.clamp_end:
            self.label='secure_cargo'
            # Advance a position-mode servo slowly, then hold with torque cap.
            self.cargo_target=0. if self.no_clamp else min(.067,max(0.,now-self.grasp_end)*.01)/self.ratio
        else:
            if not self.transport_started:
                if not self.cargo_bounds()[1] or min(self.pad_forces())<.25:
                    self.abort_reason='Cargo not inside bay with bilateral pad contact';self.end=now;return
                self.transport_started=True
            self.drive_command=self.transport.command(self.observation())
            self.label=self.drive_command['stage'];self.target_arm=np.array(self.drive_command['target_arm']);self.target_leg=np.array(self.drive_command['target_leg'])
        if self.previous_label!=self.label:print('STAGE',round(now,2),self.label,flush=True);self.previous_label=self.label

    def step(self):
        tick=int((self.data.time+1e-8)*50)
        if tick!=self.last_control:self.last_control=tick;self.control_target()
        q,v=self.data.qpos,self.data.qvel
        leg_u=80*(self.target_leg-q[self.lq])-2*v[self.lv]
        for j,i in enumerate([3,7,11,15]):
            leg_u[i]=.4*(self.drive_command['wheel_speed'][j]-v[self.lv[i]]) if self.drive_command else 2*(self.target_leg[i]-q[self.lq[i]])-.4*v[self.lv[i]]
        limits=np.tile([8,8,8,1.3],4);self.data.ctrl[self.la]=np.clip(leg_u,-limits,limits)
        arm_u=998.22*(self.target_arm-q[self.aq])-2.731*v[self.av]+self.data.qfrc_bias[self.av]
        self.data.ctrl[self.aa]=np.clip(arm_u,-2.94,2.94);self.data.ctrl[self.aa[-1]]=np.clip(self.data.ctrl[self.aa[-1]],-self.grip_cap,self.grip_cap)
        self.data.ctrl[self.ca]=np.clip(4*(self.cargo_target-q[self.cq[-1]])-.06*v[self.cv[-1]],-.12,.12)
        mujoco.mj_step(self.model,self.data)
        for ct in self.data.contact:
            names=[self.model.geom(int(g)).name for g in ct.geom]
            if any('_wheel_contact_' in n for n in names):
                for name in names:
                    if name.startswith('course_'):self.course_contacts.add(name)
        if self.transport_started:
            self.physics_cargo_checks+=1
            self.outside_cargo_steps+=not self.cargo_bounds()[1]
            self.unclamped_steps+=int(min(self.pad_forces())<=.25)
            self.max_lateral_m=max(self.max_lateral_m,abs(self.data.qpos[1]))
        if tick%2==0 and (not self.samples or self.data.time-self.samples[-1]['time']>.039):self.record()

    def record(self):
        super().record();s=self.samples[-1];bounds,inside=self.cargo_bounds()
        s.update(cargo_q=self.data.qpos[self.cq].tolist(),cargo_torque_Nm=float(self.data.actuator_force[self.ca]),
            pad_forces_N=self.pad_forces().tolist(),cargo_bounds_m=bounds.tolist(),cargo_inside=inside,
            belt_error_m=(self.data.qpos[self.cq[:2]]-self.ratio*self.data.qpos[self.cq[2]]).tolist(),
            wheel_min_x_m=self.wheel_min_x())
        if self.drive_command:s['transport']=self.drive_command

    def wheel_min_x(self):
        edge=float('inf')
        for key in self.spec['leg_order']:
            g=self.model.geom(key+'_wheel_contact_0').id;axis_x=self.data.geom_xmat[g].reshape(3,3)[0,2]
            extent=.048*np.sqrt(max(0.,1-axis_x*axis_x))+.016*abs(axis_x)
            edge=min(edge,float(self.data.geom_xpos[g,0]-extent))
        return edge

    def run(self):
        report=super().run();rows=[s for s in self.samples if s['time']>=self.clamp_end]
        retained=self.physics_cargo_checks>0 and self.outside_cargo_steps==0
        cleared=bool(rows) and rows[-1]['wheel_min_x_m']>1.295
        bilateral=self.physics_cargo_checks>0 and self.unclamped_steps==0
        report.update(status='Physical grasp, active belt clamp and frozen r21 PPO crawl',terrain_height_m=self.height,
            no_clamp_control=self.no_clamp,abort_reason=self.abort_reason,transport_started=self.transport_started,
            cargo_retained_throughout_transport=retained,bilateral_pad_contact_throughout_transport=bilateral,
            all_wheels_cleared_course=cleared,actual_course_contacts=sorted(self.course_contacts),
            transport_distance_m=self.drive_command['transport_distance_m'] if self.drive_command else 0,
            transport_policy_sha256=self.transport.sha256,max_abs_belt_error_m=float(np.max(np.abs([s['belt_error_m'] for s in self.samples]))),
            equality_constraints=['belt_to_pad_-1','belt_to_pad_1'],object_constraints=0,
            physics_cargo_checks=self.physics_cargo_checks,outside_cargo_steps=self.outside_cargo_steps,unclamped_steps=self.unclamped_steps,
            max_transport_lateral_m=self.max_lateral_m,
            success=bool(report['success'] and retained and bilateral and cleared and len(self.course_contacts)==3 and self.abort_reason is None and self.max_lateral_m<.30))
        return report
