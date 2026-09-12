"""Use the frozen r21 actor and its explicit gait on current engine state."""
import json,hashlib,math
import numpy as np
from .paths import resource_root
ROOT=resource_root()

class CrawlTransport:
    def __init__(self,duration=22.):
        self.previous=np.zeros(16);self.duration=duration;self.start=None;self.arm_hold=None;self.start_base=None
        self.wheel=np.array([3,7,11,15]);self.leg=np.array([i for i in range(16) if i%4!=3]);self.sides=np.array([1,-1,1,-1])
        path=ROOT/'policies/legacy-crawl57.json';self.actor=json.loads(path.read_text());self.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        self.layers=[None if x['kind']=='tanh' else (np.array(x['weight']),np.array(x['bias'])) for x in self.actor['layers']]

    def reference(self,t,speed):
        ref=np.zeros(16)
        if t<.3-1e-8 or abs(speed)<.01:return ref
        sample=math.floor((t+1e-8)*50)/50;phase=(max(0.,sample-.3)+.01)/2.4
        for i,(front,side,offset) in enumerate([(1,1,0),(1,-1,.5),(-1,1,.75),(-1,-1,.25)]):
            s=(phase-offset)%1
            h=.045*math.sin(math.pi*s/.25)**2 if s<.25 else 0.
            dx=-.03*math.cos(math.pi*s/.25) if s<.25 else .06*(.5-(s-.25)/.75)
            down=.172812737-h
            beta=-front*math.acos(np.clip((down*down+dx*dx-.09**2-.11**2)/(2*.09*.11),-1,1))
            theta=math.atan2(dx,down)-math.atan2(.11*math.sin(beta),.09+.11*math.cos(beta))
            theta0=front*math.atan2(.05,.074833147);beta0=-front*(math.atan2(.05,.09797959)+math.atan2(.05,.074833147))
            ref[4*i+1]=side*(theta0-theta);ref[4*i+2]=side*(beta0-beta)
        return ref

    def command(self,state):
        if self.start is None:
            self.start=state['time'];self.arm_hold=np.array(state['q'][16:22]);self.start_base=np.array(state['base_position'])
        t=state['time']-self.start;r=np.array(state['base_rotation_columns']).T
        speed=.12*min(1.,max(0.,t))*min(1.,max(0.,self.duration-2-t))
        yaw=math.atan2(r[1,0],r[0,0]);yaw_command=np.clip(-1.5*yaw-.5*(state['base_position'][1]-self.start_base[1]),-.18,.18)
        q=np.array(state['q'][:16]);v=np.array(state['v'][:16]);phase=2*math.pi*max(0.,t-.3)/2.4
        obs=np.r_[r.T@[0,0,-1],r.T@state['base_linear_world'],r.T@state['base_angular_world'],speed,yaw_command,
            q[self.leg],v[self.leg]*.1,v[self.wheel]*self.sides*.1,self.previous,math.sin(phase),math.cos(phase)]
        assert len(obs)==57
        action=obs
        for layer in self.layers:action=np.tanh(action) if layer is None else layer[0]@action+layer[1]
        action=np.clip(action,-1,1);self.previous=action.copy()
        target=self.reference(t,speed)+.18*action
        wheel_speed=self.sides*((speed-yaw_command*self.sides*.146)/.048+6*action[self.wheel])
        return dict(mode='transport',stage='loaded_crawl' if speed>.001 else 'loaded_settle',target_leg=target.tolist(),target_arm=self.arm_hold.tolist(),
            wheel_speed=wheel_speed.tolist(),policy_action=action.tolist(),policy_observation=obs.tolist(),policy_sha256=self.sha256,
            transport_distance_m=float(state['base_position'][0]-self.start_base[0]),speed_command_mps=speed,yaw_command_rads=float(yaw_command))
