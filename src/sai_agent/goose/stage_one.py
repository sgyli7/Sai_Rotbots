"""Isolated 18-axis candidate runtime; does not alter historical 16-axis policies.

Engine-neutral contract defines observable SI state and actuator behavior.
MuJoCo supplies contact dynamics; no forces are applied to the floating root.
"""
from __future__ import annotations
import json,hashlib
from pathlib import Path
import numpy as np
import mujoco
from .stage_one_gravity import NominalNeckGravity,quat_matrix

class StageOneEnv:
 def __init__(self,model_path,contract_path,num_envs=8,seed=17,randomize=True,commands=True,auto_reset=True):
  self.path=Path(model_path);self.contract_path=Path(contract_path);self.contract=json.loads(self.contract_path.read_text())
  self.source_hash=hashlib.sha256(self.path.read_bytes()).hexdigest()
  if self.source_hash!=self.contract['model_sha256']:raise ValueError('Model/contract hash mismatch')
  for rel,digest in self.contract['asset_sha256'].items():
   if hashlib.sha256((self.path.parent/rel).read_bytes()).hexdigest()!=digest:raise ValueError('Asset/contract hash mismatch: '+rel)
  self.auto_reset=auto_reset
  self.rng=np.random.default_rng(seed);self.num_envs=num_envs;self.randomize=randomize;self.command_enabled=commands
  self.models=[mujoco.MjModel.from_xml_path(str(self.path)) for _ in range(num_envs)];self.data=[mujoco.MjData(m) for m in self.models]
  self.gravity=NominalNeckGravity(self.contract)
  self.names=self.contract['joint_order'];j=self.contract['joints'];m=self.models[0]
  if self.names!=[x['name'] for x in j] or m.nu!=18:raise ValueError('Invalid joint contract')
  # Fail closed if a table was edited without regenerating its physics model.
  if (self.contract['physics_dt_s'],self.contract['torque_dt_s'],self.contract['policy_dt_s'])!=(.001,.005,.02):raise ValueError('Unsupported controller timing contract')
  if abs(m.opt.timestep-.001)>1e-12 or not np.allclose(m.opt.gravity,[0,0,-9.81],atol=1e-12,rtol=0):raise ValueError('Model timing/gravity mismatch')
  if not np.allclose(m.body_pos[m.body('torso').id],self.contract['root_origin_at_zero_m'],atol=1e-10,rtol=0):raise ValueError('Root frame mismatch')
  pivots={x['name']:np.array(x['pivot_world_at_zero_m']) for x in j};pivots['torso']=np.array(self.contract['root_origin_at_zero_m'])
  # MuJoCo's principal-axis diagonalization has a small numerical residual;
  # compare full tensors at one-part-per-million relative Frobenius tolerance.
  for b in self.contract['bodies']:
   bid=m.body(b['name']).id;ir=quat_matrix(m.body_iquat[bid]);inertia=ir@np.diag(m.body_inertia[bid])@ir.T
   if not (np.isclose(m.body_mass[bid],b['mass_kg'],rtol=1e-9,atol=1e-12) and np.allclose(m.body_ipos[bid],b['com_local_m'],atol=1e-10,rtol=0) and np.linalg.norm(inertia-np.array(b['inertia_at_com_body_kg_m2']))<=1e-6*np.linalg.norm(b['inertia_at_com_body_kg_m2'])+1e-12):raise ValueError('Body inertia/contract mismatch: '+b['name'])
  for k,item in enumerate(j):
   joint=m.joint(item['name']);bid=m.body(item['name']).id
   if not (np.allclose(m.body_pos[bid],pivots[item['name']]-pivots[item['parent']],atol=1e-10,rtol=0) and np.allclose(joint.axis,item['axis_parent'],atol=1e-10,rtol=0) and np.allclose(joint.range,item['range_rad'],atol=1e-10,rtol=0) and np.isclose(m.dof_armature[int(joint.dofadr[0])],item['armature_kg_m2'],rtol=1e-10,atol=1e-12) and m.actuator_trnid[k,0]==joint.id and np.allclose(m.actuator_ctrlrange[k],[-item['torque_peak_limit_nm'],item['torque_peak_limit_nm']],atol=1e-10,rtol=0)):raise ValueError('Joint/model contract mismatch: '+item['name'])

  self.qidx=np.array([int(m.joint(n).qposadr[0]) for n in self.names]);self.vidx=np.array([int(m.joint(n).dofadr[0]) for n in self.names])
  self.kp=np.array([x['kp_nm_rad'] for x in j]);self.kd=np.array([x['kd_nm_s_rad'] for x in j]);self.peak=np.array([x['torque_peak_limit_nm'] for x in j]);self.cont=np.array([x['continuous_design_limit_nm'] for x in j]);self.speed=np.array([x['speed_limit_rad_s'] for x in j]);self.scale=np.array([x['action_scale_rad'] for x in j]);self.ranges=np.array([x['range_rad'] for x in j]);self.neutral=np.array([x['q_neutral_rad'] for x in j])
  self.actions=np.zeros((num_envs,18));self.delayed=np.zeros_like(self.actions);self.target=np.tile(self.neutral,(num_envs,1));self.thermal=np.zeros_like(self.actions)
  self.commands=np.zeros((num_envs,3));self.age=np.zeros(num_envs,dtype=int);self.phase=np.zeros(num_envs);self.strength=np.ones(num_envs);self.delay=np.zeros(num_envs,dtype=int)
  self.nominal=[dict(mass=m.body_mass.copy(),inertia=m.body_inertia.copy(),ipos=m.body_ipos.copy(),friction=m.geom_friction.copy(),armature=m.dof_armature.copy()) for m in self.models]
  self.foot_ids=[m.geom(s+'_foot_contact').id for s in ('right','left')];self.floor_id=m.geom('floor').id
  self.torso=m.body('torso').id;self.max_episode_length=600;self.last_tau=np.zeros_like(self.actions)
  for i in range(num_envs):self.reset(i)
 def reset(self,i):
  m,d=self.models[i],self.data[i];n=self.nominal[i];m.body_mass[:]=n['mass'];m.body_inertia[:]=n['inertia'];m.body_ipos[:]=n['ipos'];m.geom_friction[:]=n['friction'];m.dof_armature[:]=n['armature']
  if self.randomize:
   for b in self.contract['bodies']:
    k=m.body(b['name']).id;u=b['mass_relative_design_uncertainty'];f=self.rng.uniform(1-u,1+u)
    m.body_mass[k]*=f;m.body_inertia[k]*=f*self.rng.uniform(.8,1.2)
    m.body_ipos[k]+=self.rng.uniform(-b['com_randomization_m'],b['com_randomization_m'],3)
   m.geom_friction[:,0]=self.rng.uniform(*self.contract['foot_friction_range']);self.strength[i]=self.rng.uniform(.85,1.);self.delay[i]=self.rng.integers(0,2)
  else:self.strength[i]=1.;self.delay[i]=0
  mujoco.mj_setConst(m,d);mujoco.mj_resetData(m,d)
  d.qpos[2]+=.002
  if self.randomize:d.qpos[self.qidx]=np.clip(d.qpos[self.qidx]+self.rng.uniform(-.012,.012,18),self.ranges[:,0],self.ranges[:,1])
  mujoco.mj_forward(m,d);self.age[i]=0;self.actions[i]=0;self.delayed[i]=0;self.target[i]=self.neutral;self.thermal[i]=0;self.last_tau[i]=0;self.phase[i]=0
  self.commands[i]=([self.rng.uniform(0,.16),self.rng.uniform(-.035,.035),self.rng.uniform(-.25,.25)] if self.command_enabled else [0,0,0])
  if self.command_enabled and self.rng.random()<.25:self.commands[i]=0
 def observations(self):
  out=[]
  for i,(m,d) in enumerate(zip(self.models,self.data)):
   R=d.xmat[self.torso].reshape(3,3)
   # Free-joint rotational qvel is body-local; gravity projection uses rotation.
   out.append(np.r_[d.qvel[3:6]*.25,R.T@np.array([0.,0.,-1.]),self.commands[i],d.qpos[self.qidx]-self.neutral,d.qvel[self.vidx]*.1,self.actions[i],np.sin(self.phase[i]),np.cos(self.phase[i])])
  obs=np.asarray(out,dtype=np.float32)
  if obs.shape!=(self.num_envs,65) or not np.isfinite(obs).all():raise FloatingPointError('Invalid stage-one observation')
  return np.clip(obs,-20,20)
 def step(self,actions):
  actions=np.asarray(actions,float)
  if actions.shape!=(self.num_envs,18) or not np.isfinite(actions).all():raise ValueError('Invalid actions')
  actions=np.clip(actions,-1,1);rewards=np.zeros(self.num_envs);dones=np.zeros(self.num_envs,dtype=bool);rows=[]
  for i,(m,d) in enumerate(zip(self.models,self.data)):
   command=self.actions[i] if self.delay[i] else actions[i];desired=np.clip(self.neutral+self.scale*command,self.ranges[:,0],self.ranges[:,1]);energy=0.;sat=0.
   for tick in range(4):
    self.target[i]+=np.clip(desired-self.target[i],-self.speed*.005,self.speed*.005)
    q=d.qpos[self.qidx];qd=d.qvel[self.vidx];tau=self.kp*(self.target[i]-q)-self.kd*qd
    # This separate model always keeps the nominal published parameters. Only
    # encoder angles and IMU orientation are read; no randomized mass or contact.
    tau[:5]+=self.gravity(q[:6],d.qpos[3:7])
    # Conservative speed envelope, symmetric braking and driving. Continuous
    # is a design derating; square-torque EWMA is a proxy, not a thermal sensor.
    cap=self.peak*self.strength[i]*np.clip(1-np.abs(qd)/(self.speed*1.3),0,1)
    cap=np.minimum(cap,np.where(self.thermal[i]>(self.cont*self.strength[i])**2,self.cont*self.strength[i],self.peak*self.strength[i]))
    sat+=np.mean(abs(tau)>cap);tau=np.clip(tau,-cap,cap)
    positive=tau*qd>0;power=float(np.sum(tau[positive]*qd[positive]))
    if power>self.contract['positive_mechanical_power_limit_w']:tau[positive]*=self.contract['positive_mechanical_power_limit_w']/power
    self.thermal[i]+=.005/2*(tau*tau-self.thermal[i]);d.ctrl[:]=tau;self.last_tau[i]=tau
    energy+=float(np.sum(np.abs(tau*qd)))*.005
    mujoco.mj_step(m,d,nstep=5)
   R=d.xmat[self.torso].reshape(3,3);velocity=R.T@d.qvel[:3];upright=float(R[2,2]);height=float(d.xpos[self.torso,2]);self.age[i]+=1;self.phase[i]=(self.phase[i]+2*np.pi*1.2*.02)%(2*np.pi)
   nonfoot=False;touch=[False,False]
   for contact in d.contact:
    pair={int(contact.geom1),int(contact.geom2)}
    if self.floor_id in pair:
     g=(pair-{self.floor_id}).pop()
     if g in self.foot_ids:touch[self.foot_ids.index(g)]=True
     else:nonfoot=True
   failure=bool(height<.18 or upright<.65 or nonfoot or not np.isfinite(d.qpos).all());timeout=bool(self.age[i]>=self.max_episode_length)
   error=float(np.sum((velocity[:2]-self.commands[i,:2])**2));yawerror=float((d.qvel[5]-self.commands[i,2])**2)
   reward=1.5*np.exp(-error/.04)+.5*np.exp(-yawerror/.16)+.5*upright-.4*(d.qvel[2]**2)-.05*np.sum(d.qvel[3:5]**2)-.005*energy-.03*np.mean((actions[i]-self.actions[i])**2)-.08*np.mean((d.qpos[self.qidx[:6]]-self.neutral[:6])**2)
   reward-=.02*np.mean((self.last_tau[i]/self.cont)**2)
   if failure:reward-=5
   rewards[i]=reward;dones[i]=failure or timeout;rows.append(dict(failure=failure,timeout=timeout,height_m=height,upright=upright,velocity_body_m_s=velocity.tolist(),command=self.commands[i].tolist(),feet_touch=touch,torque_saturation_fraction=sat/4,torque_nm=self.last_tau[i].tolist(),episode_steps=int(self.age[i])))
   self.actions[i]=actions[i]
   if dones[i] and self.auto_reset:self.reset(i)
  return self.observations(),rewards,dones,rows

# Import torch/RSL only when the training boundary is used.
def rsl_environment(base):
 import torch
 from tensordict import TensorDict
 from rsl_rl.env import VecEnv
 class Environment(VecEnv):
  def __init__(self):
   self.num_envs=base.num_envs;self.num_actions=18;self.device='cpu';self.max_episode_length=base.max_episode_length;self.episode_length_buf=torch.as_tensor(base.age.copy(),dtype=torch.long);self.cfg={'schema':base.contract['schema'],'model_sha256':base.source_hash};self.failures=0;self.steps=0
  def pack(self,x):return TensorDict({'policy':torch.as_tensor(x,dtype=torch.float32)},batch_size=[self.num_envs])
  def get_observations(self):return self.pack(base.observations())
  def step(self,a):
   obs,rew,done,rows=base.step(a.detach().cpu().numpy());self.episode_length_buf.copy_(torch.as_tensor(base.age));self.steps+=self.num_envs;self.failures+=sum(r['failure'] for r in rows)
   return self.pack(obs),torch.as_tensor(rew,dtype=torch.float32),torch.as_tensor(done),{'time_outs':torch.tensor([r['timeout'] and not r['failure'] for r in rows]),'log':{'/goose/failure_rate':np.mean([r['failure'] for r in rows])}}
 return Environment()
