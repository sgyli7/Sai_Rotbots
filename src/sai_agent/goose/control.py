"""Named-joint control contract; SI inputs/outputs for every physics adapter."""
from __future__ import annotations

import numpy as np

from .spec import load_spec

CONTRACT_VERSION = 'goose_rc2_v5'
CONTROL_DT = .02
TORQUE_UPDATE_DT = .005
ACTION_SIZE = 10
OBS_SIZE = 53
ACTION_POSITION_SCALE_RAD = .30


class JointMap:
    def __init__(self, model, spec=None):
        self.spec = spec or load_spec()
        self.names = [j['name'] for j in self.spec['joints']]
        self.neck_indices=np.array([i for i,j in enumerate(self.spec['joints']) if j['control_group']=='neck'],dtype=int)
        self.qpos = np.array([model.joint(n).qposadr[0] for n in self.names], dtype=int)
        self.dof = np.array([model.joint(n).dofadr[0] for n in self.names], dtype=int)
        self.actuator = np.array([model.actuator(n+'_actuator').id for n in self.names], dtype=int)
        self.home = np.array([j['home_rad'] for j in self.spec['joints']])
        self.ranges = np.array([j['range_rad'] for j in self.spec['joints']])
        self.limits = np.array([self.spec['servos'][j['servo']]['torque_screening_Nm'] for j in self.spec['joints']])
        self.speed_limits = np.array([self.spec['servos'][j['servo']]['speed_limit_rad_s'] for j in self.spec['joints']])
        self.kp = np.array([15 if j['control_group']=='locomotion' else
                            20 if j['servo']=='xm540' else
                            8 if j['servo']=='xm430' else .65 if j['control_group']=='beak' else 2.0
                            for j in self.spec['joints']])
        self.kd = np.array([.10 if j['control_group']=='locomotion' else
                            .6 if j['servo']=='xm540' else
                            .15 if j['servo']=='xm430' else .008 if j['control_group']=='beak' else .025
                            for j in self.spec['joints']])
        self.previous_target = self.home.copy()

    def torque(self, positions, velocities, targets, gravity_ff=None):
        positions, velocities, targets = map(lambda x:np.asarray(x,dtype=float), (positions, velocities, targets))
        if any(x.shape != (len(self.names),) or not np.isfinite(x).all() for x in (positions,velocities,targets)):
            raise ValueError('Invalid named-joint state/target')
        targets=np.clip(targets,self.ranges[:,0],self.ranges[:,1])
        torque=self.kp*(targets-positions)-self.kd*velocities
        if gravity_ff is not None:
            gravity_ff=np.asarray(gravity_ff,dtype=float)
            if gravity_ff.shape!=torque.shape or not np.isfinite(gravity_ff).all():raise ValueError('Invalid gravity feedforward')
            torque+=gravity_ff
        torque=np.clip(torque,-self.limits,self.limits)
        overspeed=(np.abs(velocities)>self.speed_limits) & (torque*velocities>0)
        torque[overspeed]=0
        return torque


def observation(gyro_body, gravity_body, command, joint_q, joint_v, home, previous_action, phase):
    """IMU, encoders and commands only. No root velocity/object truth/contacts."""
    result=np.concatenate([np.asarray(gyro_body)*.25, gravity_body, command,
                           np.asarray(joint_q)-home,np.asarray(joint_v)*.05,
                           previous_action,[np.sin(phase),np.cos(phase)]]).astype(np.float32)
    if result.shape!=(OBS_SIZE,) or not np.isfinite(result).all():
        raise ValueError('Observation contract mismatch')
    return result


def metadata(spec=None):
    spec=spec or load_spec()
    return {'version':CONTRACT_VERSION,'units':'SI','frame':'x_forward_y_left_z_up',
            'quaternion_order':'wxyz','control_dt_s':CONTROL_DT,
            'torque_update_dt_s':TORQUE_UPDATE_DT,
            'torque_feedforward':'neutral_rigid_gravity',
            'observation_size':OBS_SIZE,
            'action_size':ACTION_SIZE,'action_reference_pose':'standing',
            'action_position_scale_rad':ACTION_POSITION_SCALE_RAD,
            'action_joint_names':[j['name'] for j in spec['joints'] if j['control_group']=='locomotion'],
            'encoder_joint_names':[j['name'] for j in spec['joints']],
            'observation_fields':[{'name':'gyro_body_scaled','size':3,'scale':.25},
                                  {'name':'gravity_body_unit','size':3},
                                  {'name':'vx_vy_yawrate_command','size':3},
                                  {'name':'encoder_position_minus_home','size':len(spec['joints'])},
                                  {'name':'encoder_velocity_scaled','size':len(spec['joints']),'scale':.05},
                                  {'name':'previous_leg_action','size':10},
                                  {'name':'sin_cos_gait_phase','size':2}],
            'separate_neck_beak_control':True,'privileged_observations':False,
            'policy_status':'training_interface_no_accepted_policy_yet'}
