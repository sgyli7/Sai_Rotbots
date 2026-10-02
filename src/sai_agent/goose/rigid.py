"""Engine-independent rigid kinematics and static gravity compensation in SI."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from ..paths import resource_root


class RigidReference:
    def __init__(self,path: Path|None=None):
        path=path or resource_root()/'robots/Goose_V0.1/models/full/rigid_transfer.json'
        self.transfer=json.loads(path.read_text())
        if self.transfer['schema']!='sai_rigid_transfer_v1':raise ValueError('Unsupported rigid schema')
        self.bodies=self.transfer['bodies'];self.joints={j['child']:j for j in self.transfer['joints']}
        self.names=self.transfer['control']['encoder_joint_names'];self.home={j['name']:j['home'] for j in self.transfer['joints']}
        self.gravity=np.asarray(self.transfer['gravity_m_s2'])

    def positions(self,encoder_q,torso_rotation=np.eye(3),torso_position=np.zeros(3)):
        q=dict(self.home);q.update(zip(self.names,map(float,encoder_q)))
        q['passive_jaw_pin']=-q['beak_drive'];q['passive_follower']=q['beak_drive']
        frames={'world':(np.eye(3),np.zeros(3))}
        for b in self.bodies:
            if b['name']=='torso':frames[b['name']]=(np.asarray(torso_rotation),np.asarray(torso_position));continue
            rp,pp=frames[b['parent']]
            rot=Rotation.from_quat([*b['local_orientation_wxyz'][1:],b['local_orientation_wxyz'][0]]).as_matrix()
            r=rp@rot;p=pp+rp@np.asarray(b['local_position_m']);j=self.joints.get(b['name'])
            if j:
                axis=np.asarray(j['axis_local_child']);value=q[j['name']]
                if j['type']=='hinge':
                    rotation=Rotation.from_rotvec(axis*value).as_matrix()
                    anchor=np.asarray(j['anchor_local_child_m'])
                    p=p+r@(anchor-rotation@anchor);r=r@rotation
                elif j['type']=='slide':p=p+r@axis*value
                else:raise ValueError('Unsupported reference joint')
            frames[b['name']]=(r,p)
        return frames

    def potential(self,q,torso_rotation=np.eye(3)):
        frames=self.positions(q,torso_rotation);u=0.
        for b in self.bodies:
            r,p=frames[b['name']];u-=float(b['mass_kg'])*self.gravity@(p+r@np.asarray(b['com_local_m']))
        return u

    def gravity_torque(self,q,torso_rotation=np.eye(3)):
        """Analytic SI gravity torque, including dependent four-bar angles."""
        q=np.asarray(q,dtype=float)
        if q.shape!=(len(self.names),) or not np.isfinite(q).all():raise ValueError('Invalid encoder vector')
        frames=self.positions(q,torso_rotation);parents={b['name']:b['parent'] for b in self.bodies}
        effort={j['name']:0. for j in self.joints.values()}
        for b in self.bodies:
            r,p=frames[b['name']];com=p+r@np.asarray(b['com_local_m'])
            force=float(b['mass_kg'])*self.gravity;body=b['name']
            while body!='torso':
                j=self.joints[body];rj,pj=frames[body];axis=rj@np.asarray(j['axis_local_child'])
                anchor=pj+rj@np.asarray(j['anchor_local_child_m'])
                effort[j['name']]-=float(axis@np.cross(com-anchor,force)) if j['type']=='hinge' else float(axis@force)
                body=parents[body]
        effort['beak_drive']+=-effort['passive_jaw_pin']+effort['passive_follower']
        return np.array([effort[name] for name in self.names])

    def gravity_torque_finite_difference(self,q,torso_rotation=np.eye(3)):
        q=np.asarray(q,dtype=float)
        if q.shape!=(len(self.names),) or not np.isfinite(q).all():raise ValueError('Invalid encoder vector')
        out=np.zeros_like(q);epsilon=1e-5
        for i in range(len(q)):
            plus=q.copy();minus=q.copy();plus[i]+=epsilon;minus[i]-=epsilon
            out[i]=(self.potential(plus,torso_rotation)-self.potential(minus,torso_rotation))/(2*epsilon)
        return out

    def double_support_torque(self,q,torso_rotation=np.eye(3)):
        """Estimated stance load, from encoders/IMU and the SI mass model.

        This returns joint feedforward only; it applies no world/root forces.
        Use only during a verified, stationary two-foot stance. The assumed
        vertical ground loads are not measured contact forces or an accepted
        walking balance controller.
        """
        frames=self.positions(q,torso_rotation)
        mass=sum(b['mass_kg'] for b in self.bodies)
        com=sum(b['mass_kg']*(frames[b['name']][1]+frames[b['name']][0]@np.asarray(b['com_local_m']))
                for b in self.bodies)/mass
        feet=[frames[side+'_ankle_pitch'] for side in ('left','right')]
        centers=[p+r@np.array([.015,0,-.034]) for r,p in feet]
        separation=centers[0][1]-centers[1][1]
        if abs(separation)<.05:raise ValueError('Double-support foot separation invalid')
        left_fraction=float(np.clip((com[1]-centers[1][1])/separation,.1,.9))
        parents={b['name']:b['parent'] for b in self.bodies}
        result=np.zeros(len(self.names))
        for side,(r,p),fraction in zip(('left','right'),feet,(left_fraction,1-left_fraction)):
            local=r.T@(np.array([com[0],(p+r@np.array([.015,0,-.034]))[1],centers[0][2]])-p)
            local[0]=np.clip(local[0],-.04,.07);local[1]=0.;local[2]=-.034
            cop=p+r@local;force=-self.gravity*mass*fraction
            body=side+'_ankle_pitch'
            while body!='torso':
                j=self.joints[body];rb,pb=frames[body]
                if j['name'] in self.names:
                    axis=rb@np.asarray(j['axis_local_child']);anchor=pb+rb@np.asarray(j['anchor_local_child_m'])
                    result[self.names.index(j['name'])]-=axis@np.cross(cop-anchor,force)
                body=parents[body]
        return result
