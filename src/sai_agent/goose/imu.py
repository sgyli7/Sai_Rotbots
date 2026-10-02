"""Read-only WIT standard frames; freshness and mount calibration are explicit.

Protocol provenance is recorded in Goose design/imu_protocol_facts.md. Native
quaternion values are preserved without guessing their scalar position. Host
receipt times are not claimed to be chip sampling timestamps.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct
import numpy as np
from scipy.spatial.transform import Rotation


@dataclass(frozen=True)
class WitFrame:
    type_code:int
    received_s:float
    values:np.ndarray
    raw:bytes
    auxiliary:float|int|None=None


class WitParser:
    def __init__(self):
        self.buffer=bytearray();self.latest={};self.valid_counts={}
        self.bad_checksums=0;self.discarded_bytes=0

    def feed(self,chunk:bytes,received_s:float)->list[WitFrame]:
        if not np.isfinite(received_s) or received_s<0:raise ValueError('Invalid host clock')
        self.buffer.extend(chunk);out=[]
        while len(self.buffer)>=11:
            if self.buffer[0]!=0x55:
                del self.buffer[0];self.discarded_bytes+=1;continue
            raw=bytes(self.buffer[:11])
            if sum(raw[:10])&255!=raw[10]:
                del self.buffer[0];self.bad_checksums+=1;continue
            del self.buffer[:11];code=raw[1];words=np.array(struct.unpack('<4h',raw[2:10]),float)
            aux=None
            if code==0x51:values=words[:3]/32768*16*9.81;aux=float(words[3]/100)
            elif code==0x52:values=words[:3]/32768*2000*np.pi/180
            elif code==0x53:
                values=words[:3]/32768*np.pi;aux=int.from_bytes(raw[8:10],'little')
            elif code==0x59:values=words/32768
            else:continue
            frame=WitFrame(code,float(received_s),values,raw,aux)
            self.latest[code]=frame;self.valid_counts[code]=self.valid_counts.get(code,0)+1;out.append(frame)
        return out

    def controller_imu(self,now_s:float,calibration:dict):
        if calibration.get('attitude_mapping_verified') is not True:
            raise ValueError('Physical IMU axes/rotation commissioning required')
        if calibration.get('euler_convention')!='active_zyx_world_from_sensor':
            raise ValueError('Unknown commissioned Euler convention')
        rbs=np.asarray(calibration['rotation_body_from_sensor'],float)
        if (rbs.shape!=(3,3) or not np.isfinite(rbs).all() or
                not np.allclose(rbs.T@rbs,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(rbs),1)):
            raise ValueError('Invalid IMU mounting rotation')
        if not np.isfinite(now_s) or now_s<0:raise ValueError('Invalid host clock')
        try:gyro=self.latest[0x52];angles=self.latest[0x53]
        except KeyError as exc:raise RuntimeError('Gyro/Euler frames not received') from exc
        if any(not 0<=now_s-f.received_s<=.04 for f in (gyro,angles)):
            raise TimeoutError('IMU fields are stale')
        if abs(gyro.received_s-angles.received_s)>.02:raise TimeoutError('IMU fields are too far apart')
        roll,pitch,yaw=angles.values
        rws=Rotation.from_euler('ZYX',[yaw,pitch,roll]).as_matrix()
        gravity=rbs@rws.T@np.array([0.,0.,-1.])
        return {'gyro_body_rad_s':rbs@gyro.values,'gravity_body_unit':gravity,
                'gyro_host_received_s':gyro.received_s,'attitude_host_received_s':angles.received_s,
                'timestamp_basis':'host_monotonic_receipt_not_chip_sample'}
