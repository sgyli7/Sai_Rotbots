"""Versioned SI sensor/action messages, independent of physics engine APIs."""
from __future__ import annotations

from dataclasses import dataclass
import json

import numpy as np

from .control import CONTRACT_VERSION
from .spec import load_spec


@dataclass(frozen=True)
class SensorFrame:
    sequence: int
    timestamp_s: float
    positions_rad: np.ndarray
    velocities_rad_s: np.ndarray
    gyro_body_rad_s: np.ndarray
    gravity_body_unit: np.ndarray
    motor_current_A: np.ndarray | None = None
    supply_voltage_V: np.ndarray | None = None
    temperature_C: np.ndarray | None = None

    @classmethod
    def from_message(cls,message:dict,expected_names=None):
        names=expected_names or [j['name'] for j in load_spec()['joints']]
        if message.get('contract')!=CONTRACT_VERSION or message.get('joint_names')!=names:
            raise ValueError('Contract or joint-order mismatch')
        if message.get('units')!='SI':raise ValueError('Adapter must convert to SI')
        fields={}
        for name,size in [('positions_rad',len(names)),('velocities_rad_s',len(names)),
                          ('gyro_body_rad_s',3),('gravity_body_unit',3)]:
            value=np.asarray(message[name],float)
            if value.shape!=(size,) or not np.isfinite(value).all():raise ValueError('Invalid sensor '+name)
            fields[name]=value
        norm=np.linalg.norm(fields['gravity_body_unit'])
        if not .9<norm<1.1:raise ValueError('Gravity direction must be normalized')
        for name in ('motor_current_A','supply_voltage_V','temperature_C'):
            value=message.get(name)
            if value is not None:
                value=np.asarray(value,float)
                if value.shape!=(len(names),) or not np.isfinite(value).all():raise ValueError('Invalid motor telemetry')
            fields[name]=value
        timestamp=float(message['timestamp_s']);sequence=message['sequence']
        if (not isinstance(sequence,int) or isinstance(sequence,bool) or
                not np.isfinite(timestamp) or timestamp<0 or sequence<0):raise ValueError('Invalid clock/sequence')
        return cls(sequence,timestamp,**fields)


def torque_message(sensor:SensorFrame,names:list[str],torque_Nm,limits_Nm,valid_for_s=.06) -> dict:
    torque=np.asarray(torque_Nm,float);limits=np.asarray(limits_Nm,float)
    if (torque.shape!=(len(names),) or limits.shape!=torque.shape or
            not np.isfinite(torque).all() or not np.isfinite(limits).all() or np.any(limits<=0)):
        raise ValueError('Invalid torque vector')
    if np.any(abs(torque)>limits+1e-9):raise ValueError('Torque outside commissioned envelope')
    if not 0<valid_for_s<=.1:raise ValueError('Invalid action expiration')
    return {'contract':CONTRACT_VERSION,'units':'SI','sequence':sensor.sequence,
            'timestamp_s':sensor.timestamp_s,'valid_for_s':valid_for_s,
            'joint_names':names,'torque_Nm':torque.tolist()}


def encode_message(message:dict) -> bytes:
    return json.dumps(message,separators=(',',':'),allow_nan=False).encode()
