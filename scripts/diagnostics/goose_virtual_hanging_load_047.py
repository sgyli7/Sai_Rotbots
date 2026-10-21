"""Explicit virtualpayload open-system mass law. No mj_step, no live pose writes."""
import numpy as np
import mujoco as mj
class VirtualPayload:
 def __init__(self,model,max_total_kg=20.):
  self.m=model;self.bid=model.body('calibrated_304_ballast').id
  root=model.body('calibrated_hanging_assembly').id
  self.fixed=float(sum(model.body_mass[i] for i in range(model.nbody) if model.body_rootid[i]==root)-model.body_mass[self.bid])
  self.base_m=float(model.body_mass[self.bid]);self.unit_I=model.body_inertia[self.bid].copy()/self.base_m
  self.max_total=max_total_kg;self.scratch=mj.MjData(model)
 def set_total_mass(self,live,total_kg):
  total=float(total_kg);ballast=total-self.fixed
  if not np.isfinite(total) or ballast<.05-1e-9 or total>self.max_total+1e-9:raise ValueError('virtualpayload mass domain')
  before={k:getattr(live,k).copy() for k in ('qpos','qvel','ctrl','qfrc_applied','xfrc_applied')};t=float(live.time)
  mj.mj_energyPos(self.m,live);mj.mj_energyVel(self.m,live);oldE=live.energy.copy();oldm=float(self.m.body_mass[self.bid]);oldI=self.m.body_inertia[self.bid].copy()
  self.m.body_mass[self.bid]=ballast;self.m.body_inertia[self.bid]=ballast*self.unit_I
  mj.mj_setConst(self.m,self.scratch);mj.mj_forward(self.m,live)
  mj.mj_energyPos(self.m,live);mj.mj_energyVel(self.m,live)
  diff={k:float(np.max(abs(getattr(live,k)-v))) for k,v in before.items()}
  if any(diff.values()) or float(live.time)!=t:raise RuntimeError('massupdate altered live state')
  return dict(time=t,total_mass_kg=total,ballast_mass_kg=ballast,fixed_fixture_mass_kg=self.fixed,delta_mass_kg=ballast-oldm,delta_principal_I_kgm2=(self.m.body_inertia[self.bid]-oldI).tolist(),parameter_energy_change_J=float(sum(live.energy)-sum(oldE)),parameter_energy_components_J=(live.energy-oldE).tolist(),state_change=diff,note='VirtualfixedCOMpayload,addedmaterialassumedco-moving;parameterenergychange isnotmotorworkorconstraintinjectionmeasurement')
class LoadSchedule:
 """Called on realfeedback. Holds progression wheneligibility missing; never lowersmass."""
 def __init__(self,total,time):
  self.mass=float(total);self.mode='dwell';self.start=float(time);self.last=float(time);self.qualified_clock=0.;self.slip_clock=0.;self.final_observe=False
 def update(self,time,qualified,outward_speed_m_s):
  t=float(time);dt=max(0.,t-self.last);self.last=t
  if self.mode in ('complete','persistent_slide_observed'):return self.result()
  slip=float(outward_speed_m_s)>.002
  self.slip_clock=self.slip_clock+dt if slip else 0.
  if self.mode=='ramp':
   if not qualified or self.slip_clock>=.5:self.mode='pause';self.start=t;self.qualified_clock=0.
   else:
    u=min(1.,max(0.,(t-self.start)/.5));s=u*u*u*(10+u*(-15+6*u));self.mass=self.from_mass+(self.to_mass-self.from_mass)*s
    if u>=1:self.mode='dwell';self.start=t;self.qualified_clock=0.
  elif self.mode=='dwell':
   self.qualified_clock=self.qualified_clock+dt if qualified else 0.
   if self.slip_clock>=.5:self.mode='pause';self.start=t;self.qualified_clock=0.
   elif self.qualified_clock>=5.:
    if self.mass>=20-1e-9:self.mode='complete'
    else:self.from_mass=self.mass;self.to_mass=min(20.,self.mass+1.);self.start=t;self.mode='ramp'
  elif self.mode=='pause':
   if t-self.start>=2.:
    if qualified and not slip:self.mode='dwell';self.start=t;self.qualified_clock=0.;self.slip_clock=0.
    else:self.mode='observe_slide';self.start=t
  elif self.mode=='observe_slide':
   if qualified and not slip:self.mode='dwell';self.start=t;self.qualified_clock=0.;self.slip_clock=0.
   elif t-self.start>=5.:self.mode='persistent_slide_observed'
  return self.result()
 def result(self):return dict(total_mass_goal_kg=self.mass,mode=self.mode,qualified_dwell_s=self.qualified_clock,slip_clock_s=self.slip_clock,stop=self.mode in ('complete','persistent_slide_observed'))

class BoundedHoldLedger:
 """Same043holdobserver semantics, O(1) amortized1s window; rawlogs external."""
 def __init__(self):
  from collections import deque
  self.rows=deque();self.since=None;self.longest=0.;self.start_nativeX=None
 def add(self,o):
  t=float(o['time']);x=float(o['native_workpiece_center_mm'][0]);self.start_nativeX=x if self.start_nativeX is None else self.start_nativeX
  if self.rows and t<=self.rows[-1]['time_s']:raise ValueError('Fresh strictly increasingactualsubsteps required')
  if o['hold_eligibility']:self.since=t if self.since is None else self.since
  else:self.since=None
  clock=0. if self.since is None else t-self.since;self.longest=max(self.longest,clock)
  self.rows.append(dict(time_s=t,nativeX_mm=x,eligible=o['hold_eligibility']))
  while self.rows and self.rows[0]['time_s']<t-1.:self.rows.popleft()
  speed=None if len(self.rows)<2 else(x-self.rows[0]['nativeX_mm'])/(t-self.rows[0]['time_s'])
  return dict(current_full_load_hold_s=clock,longest_full_load_hold_s=self.longest,retained5s=clock>=5.,total_outward_slide_mm=x-self.start_nativeX,last_up_to1s_outward_rate_mm_s=speed,last_rate_window_s=t-self.rows[0]['time_s'],retention_is_not_stability_or_material_qualification=True,required_disclosure='A5s massretained result must separately disclose full outwardslide/contactpolygon/last1screep; sustaineddescent isnotstableceiling.')
