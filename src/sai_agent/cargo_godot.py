"""Current Godot state -> manipulation targets and cargo/load interlock."""
import numpy as np,mujoco
from scipy.spatial.transform import Rotation
from .paths import resource_root
from .manipulation import Task
from .legacy_crawl import CrawlTransport
from .godot_controller import GodotController
HERE=resource_root()/'models/full'

class CargoGodotController(GodotController):
    def __init__(self,no_grip=False,grip_cap=1.4,until=None,no_clamp=False,task_factory=Task,model_dir=HERE):
        self.task=task_factory(no_grip,model_dir=model_dir);self.task.grip_cap=grip_cap
        self.active_clamp=self.task.spec['cargo'].get('active_clamp',True)
        self.grasp_end=self.task.end;self.clamp_end=self.grasp_end+(8. if self.active_clamp else 1.);self.transport=CrawlTransport()
        self.end=until if until is not None else self.clamp_end+self.transport.duration
        self.no_clamp=no_clamp;self.last_stage=None;self.target=0.
        js=[self.task.model.joint(x).id for x in (['cargo_slide_-1','cargo_slide_1','cargo_drive'] if self.active_clamp else [])]
        self.cq=[self.task.model.jnt_qposadr[j] for j in js];self.cv=[self.task.model.jnt_dofadr[j] for j in js]

    def command(self,state):
        t=self.task;d=t.data;r=np.array(state['base_rotation_columns']).T
        d.time=state['time'];d.qpos[:3]=state['base_position'];d.qpos[3:7]=Rotation.from_matrix(r).as_quat(scalar_first=True)
        d.qpos[t.lq]=state['q'][:16];d.qpos[t.aq]=state['q'][16:22];d.qpos[self.cq]=state['q'][22:25]
        d.qvel[:3]=state['base_linear_world'];d.qvel[3:6]=r.T@state['base_angular_world']
        d.qvel[t.lv]=state['v'][:16];d.qvel[t.av]=state['v'][16:22];d.qvel[self.cv]=state['v'][22:25]
        mujoco.mj_forward(t.model,d)
        tool_error=float(np.linalg.norm(d.site_xpos[t.site]-state['tool_m']))
        if d.time+1e-6<self.grasp_end:
            t.control_target();result=dict(mode='manipulation',stage=t.label,target_leg=t.target_leg.tolist(),target_arm=t.target_arm.tolist())
        elif d.time+1e-6<self.clamp_end:
            self.target=0. if self.no_clamp or not self.active_clamp else min(.067,max(0.,d.time-self.grasp_end)*.01)/t.spec['cargo']['drive_metres_per_radian']
            result=dict(mode='securing',stage='secure_cargo' if self.active_clamp else 'settle_cargo',target_leg=t.target_leg.tolist(),target_arm=t.target_arm.tolist())
        elif self.transport.start is None and not (state['cargo_inside'] and (state['cargo_bilateral'] or not self.active_clamp)):
            self.end=d.time
            result=dict(mode='abort',stage='cargo_not_secured',target_leg=t.target_leg.tolist(),target_arm=t.target_arm.tolist())
        else:result=self.transport.command(state)
        result.update(arm_bias=d.qfrc_bias[t.av].tolist(),grip_cap=t.grip_cap,end=self.end,FK_tool_error_m=tool_error,
            cargo_target_rad=self.target,physics_advanced_by_controller=False,transport_required=self.transport.start is not None)
        if self.last_stage!=result['stage']:print('STAGE',round(d.time,2),result['stage'],flush=True);self.last_stage=result['stage']
        return result
