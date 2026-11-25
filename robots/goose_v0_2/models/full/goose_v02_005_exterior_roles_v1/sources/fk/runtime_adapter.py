#!/usr/bin/env python3
"""21-owner development adapter; no implicit support, policy or training claims."""
from __future__ import annotations
import argparse,hashlib,json,math
from parent_runtime_adapter import FrozenPhysics
from pathlib import Path
import mujoco,numpy as np

class RuntimeAdapter:
 def __init__(self,package=None,bus_voltage_v=None):
  self.package=Path(package or Path(__file__).resolve().parent).resolve()
  self._reference=FrozenPhysics
  self.contract=json.loads((self.package/'physical_contract.json').read_text());self.drive=json.loads((self.package/'actuator_contract.json').read_text());self.model=mujoco.MjModel.from_xml_path(str(self.package/'robot.xml'));self.data=mujoco.MjData(self.model);self.joints=self.contract['joints'];self.names=self.contract['joint_order'];self.entries=self.drive['axes']
  assert self.names==[j['name'] for j in self.joints]==[x['name'] for x in self.entries] and self.model.nu==18 and self.model.nv>=26
  self.dt=self.contract['physics_dt_s'];self.drive_dt=self.contract['torque_dt_s'];self.policy_dt=self.contract['policy_dt_s'];self.substeps=round(self.drive_dt/self.dt);self.ticks=round(self.policy_dt/self.drive_dt);
  if (self.substeps,self.ticks)!=(10,4) or abs(self.model.opt.timestep-self.dt)>=1e-12: raise ValueError('Invalid model clock')
  self.qidx=np.array([int(self.model.joint(n).qposadr[0]) for n in self.names]);self.vidx=np.array([int(self.model.joint(n).dofadr[0]) for n in self.names]);self.drive_vidx=self.vidx.copy() # HY belt is represented by the direct 1:1 joint in this fixture, not old helper rotors.
  self.actidx=np.array([mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_ACTUATOR,n+'_motor') for n in self.names]);assert np.all(self.actidx>=0) and len(set(self.actidx))==18
  self.ranges=np.array([self.model.jnt_range[self.model.joint(n).id] for n in self.names]);self.neutral=np.array([j['q_neutral_rad'] for j in self.joints]);self.kp=np.array([j['kp_nm_rad'] for j in self.joints]);self.kd=np.array([j['kd_nm_s_rad'] for j in self.joints]);self.cont=np.array([j['continuous_design_limit_nm'] for j in self.joints]);self.speed=np.array([j['speed_limit_rad_s'] for j in self.joints]);self.bus_voltage_v=float(self.drive['power_supply']['nominal_bus_v'] if bus_voltage_v is None else bus_voltage_v)
  if not 20<=self.bus_voltage_v<=25.2:raise ValueError('Bus voltage outside source design window')
  self.voltage_speed_factor=min(self.bus_voltage_v/24,1.);f=np.array([j.get('reference_slew_speed_factor',1.) for j in self.entries]);assert np.all((f>0)&(f<=1));self.slew_speed=self.speed*np.array([1. if j['reference_voltage_v']==5. else self.voltage_speed_factor for j in self.entries])*f;self.target=self.neutral.copy();self.last_tau=np.zeros(18);self.hold_config=json.loads((self.package/'named_reset.json').read_text());self.q0_feedforward=np.array([self.hold_config['motor_feedforward_Nm'][n] for n in self.names]);assert self.q0_feedforward.shape==(18,);self.feedforward_eligible=True;self.feedforward_active=False;self.policy_updates=0;self.controller_updates=0;self.max_pin_m=0.;self.max_observed_speed_ratio=0.;self.max_positive_power_w=0.;self.reset()
 def linkage(self,q):return self._reference.linkage(self,q)
 def jaw_from_input(self,q):return self._reference.jaw_from_input(self,q)
 def internal_pin_residual(self):return self._reference.internal_pin_residual(self)
 def limit_torque(self,requested,velocity):return self._reference.limit_torque(self,requested,velocity)
 def reset(self,named_q=None):
  mujoco.mj_resetData(self.model,self.data);q=self.neutral.copy()
  if named_q:
   for name,value in named_q.items():
    if name not in self.names:raise ValueError('Unknown joint '+name)
    q[self.names.index(name)]=value
  if not np.isfinite(q).all() or np.any(q<self.ranges[:,0]-1e-12) or np.any(q>self.ranges[:,1]+1e-12):raise ValueError('Reset joint positions outside candidate ROM')
  self.data.qpos[self.qidx]=q;jaw=self.jaw_from_input(float(q[5]));self.data.qpos[int(self.model.joint('beak_hinge').qposadr[0])]=jaw;self.data.qpos[int(self.model.joint('beak_coupler_link').qposadr[0])]=self.linkage(jaw)[1];self.data.ctrl[:]=0;self.target=q.copy();self.last_tau[:]=0;self.feedforward_eligible=bool(np.allclose(q,self.neutral,atol=1e-12));self.feedforward_active=False;self.policy_updates=self.controller_updates=0;self.max_pin_m=self.max_observed_speed_ratio=self.max_positive_power_w=0.;mujoco.mj_forward(self.model,self.data);assert self.internal_pin_residual()<1e-10;return self.observe()
 def step(self,position_targets):
  v=np.asarray(position_targets,dtype=float)
  if v.shape!=(18,) or not np.isfinite(v).all():raise ValueError('Expected 18 finite position targets in radians')
  desired=np.clip(v,self.ranges[:,0],self.ranges[:,1]);self.feedforward_eligible=self.feedforward_eligible and bool(np.allclose(desired,self.neutral,atol=1e-12));self.feedforward_active=False;before=self.data.time
  for _ in range(self.ticks):
   self.target+=np.clip(desired-self.target,-self.slew_speed*self.drive_dt,self.slew_speed*self.drive_dt);vel=self.data.qvel[self.vidx];req=self.kp*(self.target-self.data.qpos[self.qidx])-self.kd*vel;self.last_tau=self.limit_torque(req,vel);self.data.ctrl[self.actidx]=self.last_tau;power=float(np.sum(np.maximum(self.last_tau*vel,0)));self.max_positive_power_w=max(self.max_positive_power_w,power)
   for _ in range(self.substeps):
    if np.any(self.data.qfrc_applied) or np.any(self.data.xfrc_applied):raise RuntimeError('External forces are disabled for development smoke')
    mujoco.mj_step(self.model,self.data);mujoco.mj_forward(self.model,self.data)
    if not all(np.isfinite(getattr(self.data,n)).all() for n in ('qpos','qvel','qacc','ctrl')) or any(w.number for w in self.data.warning):raise FloatingPointError('Simulator warning or nonfinite state')
    self.max_pin_m=max(self.max_pin_m,self.internal_pin_residual());self.max_observed_speed_ratio=max(self.max_observed_speed_ratio,float(np.max(np.abs(self.data.qvel[self.vidx])/self.speed)))
   self.controller_updates+=1
  self.policy_updates+=1;assert abs(self.data.time-before-self.policy_dt)<1e-10;return self.observe()
 def observe(self):
  # Explicit fields only, not an inherited policy observation vector or contract.
  bid=self.model.body('torso').id;R=self.data.xmat[bid].reshape(3,3);return {'time_s':float(self.data.time),'joint_names':list(self.names),'joint_position_rad':self.data.qpos[self.qidx].copy(),'joint_velocity_rad_s':self.data.qvel[self.vidx].copy(),'position_target_rad':self.target.copy(),'commanded_torque_Nm':self.last_tau.copy(),'root_xyz_quat_wxyz':self.data.qpos[:7].copy(),'torso_com_world_m':self.data.xipos[bid].copy(),'torso_up_world':R[:,2].copy(),'jaw_rad':float(self.data.qpos[int(self.model.joint('beak_hinge').qposadr[0])]),'beak_pin_residual_m':self.internal_pin_residual(),'contact_count':int(self.data.ncon),'speed_is_torque_curve_and_reference_slew_limited_not_a_physical_velocity_clamp':True,'external_forces':False,'mocap_support':False,'q0_motor_feedforward_active':self.feedforward_active,'feedforward_scope':'source-bound empty q0 only; permanently disabled until reset if target changes'}

class CandidateRuntime(RuntimeAdapter):
 def __init__(self, package=None, **kwargs):
  self.domain=json.loads((Path(package or Path(__file__).parent)/'parameters.json').read_text())
  super().__init__(package, **kwargs)
  self.scale=np.maximum(abs(self.ranges[:,0]-self.neutral),abs(self.ranges[:,1]-self.neutral))
  self.last_action=np.zeros(18)
 def reset(self, named_q=None, root_pose=None):
  result=super().reset(named_q)
  if root_pose is not None:
   pose=np.asarray(root_pose,dtype=float)
   if pose.shape!=(7,) or not np.isfinite(pose).all() or abs(np.linalg.norm(pose[3:])-1)>1e-8: raise ValueError('Invalid root pose')
   self.data.qpos[:7]=pose; mujoco.mj_forward(self.model,self.data)
  self.last_action=np.zeros(18)
  return result
 def normalized_targets(self, action, *, action_domain_id):
  if action_domain_id!=self.domain['action_domain_id']: raise ValueError('Policy/action domain mismatch')
  a=np.asarray(action,dtype=float)
  if a.shape!=(18,) or not np.isfinite(a).all(): raise ValueError('Expected 18 finite normalized commands')
  return np.clip(self.neutral+self.scale*np.clip(a,-1,1),self.ranges[:,0],self.ranges[:,1])
 def step(self, action, *, action_domain_id):
  target=self.normalized_targets(action,action_domain_id=action_domain_id)
  self.last_action=np.clip(np.asarray(action,dtype=float),-1,1)
  return super().step(target)
 def observations(self, commands=None, phase_rad=0.):
  commands=np.zeros(3) if commands is None else np.asarray(commands,dtype=float)
  if commands.shape!=(3,) or not np.isfinite(commands).all(): raise ValueError('Invalid commands')
  mujoco.mj_kinematics(self.model,self.data);mujoco.mj_comPos(self.model,self.data)
  bid=self.model.body('torso').id; velocity=np.zeros(6)
  mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,bid,velocity,1)
  R=self.data.xmat[bid].reshape(3,3)
  return np.r_[velocity[:3]*.25,R.T@[0.,0.,-1.],commands,self.data.qpos[self.qidx]-self.neutral,self.data.qvel[self.vidx]*.1,self.last_action,np.sin(phase_rad),np.cos(phase_rad)].astype(np.float32)
