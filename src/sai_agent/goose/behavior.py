"""Specified-object task sequencing and small, coordinated goose expressions.

This module emits SI motion requests. A validated locomotion/neck executor must
accept them; sequencing alone is not a successful autonomous task evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class Phase(str,Enum):
    IDLE='idle';SEARCH='search';APPROACH='approach';PROBE='probe';GRASP='grasp'
    LIFT='lift';CARRY='carry';DRAG='drag';RELEASE='release';DONE='done';STOP='stop'


@dataclass(frozen=True)
class PerceivedTarget:
    marker_id:int
    timestamp_s:float
    grasp_point_torso_m:np.ndarray
    minimum_edge_px:float
    reprojection_error_px:float

    def usable(self,now_s,precision=False):
        point=np.asarray(self.grasp_point_torso_m,float)
        return (point.shape==(3,) and np.isfinite(point).all() and
                0<=now_s-self.timestamp_s<.15 and self.reprojection_error_px<1.5 and
                self.minimum_edge_px>=(40 if precision else 15))


@dataclass(frozen=True)
class TaskSignals:
    now_s:float
    torso_tilt_rad:float
    gyro_norm_rad_s:float
    motion_complete:bool=False
    grip_confirmed:bool=False
    release_confirmed:bool=False
    destination_reached:bool=False
    drag_force_estimate_N:float|None=None
    telemetry_healthy:bool=True
    executor_ready:bool=False


class TaskSequencer:
    def __init__(self):
        self.phase=Phase.IDLE;self.entered_s=0.;self.request=None;self.reason='';self.last_point=None;self._honk_pending=False

    def start(self,marker_id:int,mode:str,now_s:float,destination_marker_id:int|None=None):
        if mode not in ('bring','drag'):raise ValueError('Unknown specified-object task')
        if destination_marker_id is None:raise ValueError('Task destination must be explicit')
        if self.phase not in (Phase.IDLE,Phase.DONE,Phase.STOP):raise RuntimeError('Task already running')
        self.request={'marker_id':int(marker_id),'mode':mode,'destination_marker_id':int(destination_marker_id)}
        self.last_point=None;self.reason='';self._enter(Phase.SEARCH,now_s)

    def _enter(self,phase,now):
        self.phase=phase;self.entered_s=now
        self._honk_pending=phase==Phase.DONE

    def stop(self,reason,now_s):self.reason=reason;self._enter(Phase.STOP,now_s)

    def update(self,signals:TaskSignals,target:PerceivedTarget|None):
        s=signals
        numeric=[s.now_s,s.torso_tilt_rad,s.gyro_norm_rad_s]
        if not np.isfinite(numeric).all() or s.now_s<self.entered_s:
            raise ValueError('Invalid task clock/IMU')
        if not s.telemetry_healthy or s.torso_tilt_rad>.18:
            self.stop('telemetry_or_stability',s.now_s)
        if self.phase in (Phase.IDLE,Phase.DONE,Phase.STOP):return self._request()
        if not s.executor_ready:
            return self._request(wait_reason='validated_motion_executor_required')
        seen=target is not None and target.marker_id==self.request['marker_id'] and target.usable(s.now_s)
        precise=seen and target.usable(s.now_s,precision=True)
        if self.phase in (Phase.APPROACH,Phase.PROBE) and not seen:
            self._enter(Phase.SEARCH,s.now_s)
        if seen:self.last_point=np.asarray(target.grasp_point_torso_m,float).copy()
        elapsed=s.now_s-self.entered_s
        if self.phase==Phase.SEARCH:
            if seen:self._enter(Phase.APPROACH,s.now_s)
            elif elapsed>10:self.stop('specified_marker_not_found',s.now_s)
        elif self.phase==Phase.APPROACH:
            # Base motion is requested only when the object exceeds the
            # commissioned neck workspace. Executor applies real gait limits.
            if precise and .20<self.last_point[0]<.38 and abs(self.last_point[1])<.03:
                self._enter(Phase.PROBE,s.now_s)
        elif self.phase==Phase.PROBE:
            if precise and s.motion_complete and s.gyro_norm_rad_s<.12:self._enter(Phase.GRASP,s.now_s)
            elif elapsed>8:self.stop('probe_motion_timeout',s.now_s)
        elif self.phase==Phase.GRASP:
            if s.grip_confirmed:self._enter(Phase.LIFT if self.request['mode']=='bring' else Phase.DRAG,s.now_s)
            elif elapsed>2:self.stop('grip_not_confirmed',s.now_s)
        elif self.phase==Phase.LIFT:
            if s.motion_complete:self._enter(Phase.CARRY,s.now_s)
            elif elapsed>6:self.stop('lift_timeout',s.now_s)
        elif self.phase in (Phase.CARRY,Phase.DRAG):
            if not s.grip_confirmed:self.stop('grip_lost',s.now_s)
            elif self.phase==Phase.DRAG and (s.drag_force_estimate_N is None or not np.isfinite(s.drag_force_estimate_N)):
                self.stop('calibrated_drag_force_observer_required',s.now_s)
            elif self.phase==Phase.DRAG and s.drag_force_estimate_N>4:
                self.stop('drag_resistance_above_envelope',s.now_s)
            elif s.destination_reached:self._enter(Phase.RELEASE,s.now_s)
            elif elapsed>30:self.stop('transport_timeout',s.now_s)
        elif self.phase==Phase.RELEASE:
            if s.release_confirmed:self._enter(Phase.DONE,s.now_s)
            elif elapsed>3:self.stop('release_not_confirmed',s.now_s)
        return self._request()

    def _request(self,wait_reason=''):
        action={'phase':self.phase.value,'velocity_command_m_s_rad_s':[0.,0.,0.],
                'neck_skill':'hold','beak_skill':'hold','honk':False,'reason':self.reason or wait_reason}
        if wait_reason:return action
        if self.phase==Phase.SEARCH:action['neck_skill']='look_left_right'
        elif self.phase==Phase.APPROACH and self.last_point is not None:
            x,y,_=self.last_point
            action['velocity_command_m_s_rad_s']=[float(np.clip((x-.32)*.3,-.025,.05)),0.,float(np.clip(y*.7,-.15,.15))]
            action['neck_skill']='look_at_marker'
        elif self.phase==Phase.PROBE:action.update(neck_skill='side_ground_reach',beak_skill='open')
        elif self.phase==Phase.GRASP:action['beak_skill']='current_limited_close'
        elif self.phase==Phase.LIFT:action['neck_skill']='lift_50mm'
        elif self.phase in (Phase.CARRY,Phase.DRAG):
            action['velocity_command_m_s_rad_s']=[.035 if self.phase==Phase.CARRY else -.025,0.,0.]
            action['neck_skill']='carry_hold' if self.phase==Phase.CARRY else 'low_drag_hold'
        elif self.phase==Phase.RELEASE:action.update(neck_skill='place',beak_skill='open')
        elif self.phase==Phase.DONE:
            action.update(neck_skill='small_look_back',honk=self._honk_pending)
            self._honk_pending=False
        elif self.phase==Phase.STOP:action['neck_skill']='stability_hold'
        return action


def expression_offsets(name:str,elapsed_s:float):
    """Subtle expression offsets, applied only after workspace/stability checks."""
    if elapsed_s<0 or not np.isfinite(elapsed_s):raise ValueError('Invalid expression time')
    if name=='curious':return {'head_roll':.10*np.sin(np.pi*min(elapsed_s,1.)), 'head_pitch':-.07*np.sin(np.pi*min(elapsed_s,1.))}
    if name=='look_back':return {'neck_yaw':.30*np.sin(np.pi*min(elapsed_s/1.4,1.))}
    if name=='honk':return {'head_pitch':-.05*np.sin(2*np.pi*min(elapsed_s,.6)/.6)}
    if name=='idle':return {}
    raise ValueError('Unknown expression')
