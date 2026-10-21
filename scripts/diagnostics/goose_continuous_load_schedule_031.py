"""Pure monotonic mass schedule, no MuJoCo/runtime state API."""
import math
class ContinuousLoadRamp:
 def __init__(self,initial_total_kg,start_time,maximum_kg=20.):
  self.initial=float(initial_total_kg);self.start=float(start_time);self.maximum=float(maximum_kg);self.last_t=self.start;self.qualified_top_s=0.
  if not 0<self.initial<self.maximum:raise ValueError('positiveinitialmass below20required')
  self.segments=int(math.ceil(self.maximum-self.initial));self.duration=.5*self.segments
 def update(self,time,qualified):
  t=float(time)
  if t<self.last_t-1e-10:raise ValueError('monotonicfeedbacktime')
  dt=max(0.,t-max(self.last_t,self.start+self.duration));self.last_t=t;elapsed=max(0.,t-self.start)
  if elapsed<self.duration:
   n=int(elapsed/.5);u=(elapsed-.5*n)/.5;step=min(1.,self.maximum-(self.initial+n));s=u*u*u*(10+u*(-15+6*u));mass=min(self.maximum,self.initial+n+step*s);mode='ramp';self.qualified_top_s=0.
  else:
   mass=self.maximum;mode='top_hold';self.qualified_top_s=self.qualified_top_s+dt if qualified else 0.
  return dict(total_mass_goal_kg=mass,mode=mode,qualified_top_hold_s=self.qualified_top_s,stop=self.qualified_top_s>=5.,continuous_ramp_elapsed_s=elapsed,slip_is_observation_only=True)
