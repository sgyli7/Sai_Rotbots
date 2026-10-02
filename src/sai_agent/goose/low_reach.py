"""Slow two-foot-supported reach reference from encoders and IMU only.

This is a bounded engineering maneuver, not a PPO policy or an object grasp.
A no-slip, level-floor, double-support assumption supplies the base translation.
True simulator root position, contact forces and randomized mass are not inputs.
The SI contract and the standalone source can be reused by other backends.
"""
import numpy as np
from scipy.optimize import least_squares
from .stage_one_gravity import quat_matrix


def smooth5(value):
    u=np.clip(value,0.,1.)
    return u*u*u*(10-15*u+6*u*u)


class SupportedReach:
    def __init__(self, contract, crouch_q, target=(.280,0,.045), pitch_deg=65.):
        self.contract=contract
        self.joints=contract['joints']
        self.names=contract['joint_order']
        self.pivots={j['name']:np.array(j['pivot_world_at_zero_m']) for j in self.joints}
        self.pivots['torso']=np.array(contract['root_origin_at_zero_m'])
        self.skews=[]
        for j in self.joints:
            x,y,z=j['axis_parent']
            self.skews.append(np.array([[0,-z,y],[z,0,-x],[-y,x,0.]]))
        self.feet=['right_ankle_roll','left_ankle_roll']
        self.anchors={n:self.pivots[n].copy() for n in self.feet}
        self.grip_local=np.array([.240,0,.553])-self.pivots['head_roll']
        self.crouch=np.asarray(crouch_q,float)
        self.q_neck=np.zeros(3)
        self.ranges=np.array([j['range_rad'] for j in self.joints])[1:4]
        self.target=np.array(target,float)
        self.pitch=np.deg2rad(pitch_deg)
        # The existing crouch lowers the body by60mm with nominally fixed feet.
        self.start=np.array([.240,0,.493])

    def forward(self,q,imu_wxyz):
        positions={'torso':np.zeros(3)}
        rotations={'torso':quat_matrix(imu_wxyz)}
        for k,j in enumerate(self.joints):
            name,parent=j['name'],j['parent']
            positions[name]=positions[parent]+rotations[parent]@(self.pivots[name]-self.pivots[parent])
            K=self.skews[k]
            rotations[name]=rotations[parent]@(np.eye(3)+np.sin(q[k])*K+(1-np.cos(q[k]))*(K@K))
        return positions,rotations

    def root_from_supported_feet(self,q,imu_wxyz):
        positions,_=self.forward(q,imu_wxyz)
        return np.mean([self.anchors[n]-positions[n] for n in self.feet],axis=0)

    def reference(self,time_s,encoder_q,imu_wxyz):
        q=np.asarray(encoder_q,float)
        if q.shape!=(18,) or not np.isfinite(q).all():
            raise ValueError('Expected18 finite encoder angles')
        # Stand1s, crouch4s, reach7s, hold3s, retract7s, stand4s, settle2s.
        if time_s<22:
            body_fraction=smooth5((time_s-1)/4)
        else:
            body_fraction=1-smooth5((time_s-22)/4)
        target_q=self.crouch*body_fraction
        reach=smooth5((time_s-5)/7) if time_s<15 else 1-smooth5((time_s-15)/7)
        desired=(1-reach)*self.start+reach*self.target
        # Forward bow clears the torso while crossing body height; endpoints
        # stay fixed. Straight interpolation collided in held-out seed903.
        desired[0]+=.060*4*reach*(1-reach)
        pitch=reach*self.pitch
        residual_m=0.
        if 5<time_s<22:
            root=self.root_from_supported_feet(q,imu_wxyz)
            def residual(angles):
                trial=q.copy();trial[1:4]=angles
                p,r=self.forward(trial,imu_wxyz)
                point=root+p['head_roll']+r['head_roll']@self.grip_local
                forward=r['head_roll'][:,0]
                angle=np.arctan2(-forward[2],forward[0])
                return np.r_[(point-desired)[[0,2]],.08*(angle-pitch)]
            solution=least_squares(residual,self.q_neck,bounds=(self.ranges[:,0],self.ranges[:,1]),max_nfev=12,ftol=1e-6,xtol=1e-6,gtol=1e-6)
            self.q_neck=solution.x
            target_q[1:4]=self.q_neck
            residual_m=float(np.linalg.norm(residual(solution.x)))
        return target_q,dict(target_grip_m=desired.tolist(),target_pitch_rad=float(pitch),ik_weighted_residual_m=residual_m,phase=('stand' if time_s<1 else 'crouch' if time_s<5 else 'reach' if time_s<12 else 'hold' if time_s<15 else 'retract' if time_s<22 else 'stand_up'))
