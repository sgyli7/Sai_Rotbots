"""Two-voltage DYNAMIXEL TTL driver with explicit commissioning and fail-stop.

Verified control-table facts: ROBOTIS eManual XM430-W350, XM540-W270,
XC330-M288. Nm/A coefficients are stall-based initial estimates, not calibrated
output torque. No ports are opened, EEPROM written or motors armed at import.
"""
from __future__ import annotations

import math
import time

import numpy as np

from .spec import load_spec

MODEL_NUMBERS={'xm430':1020,'xm540':1120,'xc330':1240}
CURRENT_UNIT_A={'xm430':.00269,'xm540':.00269,'xc330':.001}
INITIAL_NM_PER_A={'xm430':4.1/2.3,'xm540':10.6/4.4,'xc330':.93/1.8}


def signed(value:int,bits:int) -> int:
    return value-(1<<bits) if value&(1<<(bits-1)) else value


class DynamixelRobot:
    def __init__(self,ports:dict[str,str],calibration:dict|None=None,spec:dict|None=None):
        import dynamixel_sdk as sdk
        self.sdk=sdk;self.spec=spec or load_spec();self.joints=self.spec['joints']
        self.calibration=calibration;self.packet=sdk.PacketHandler(2.0)
        self.ports={};self.readers={};self.writers={};self.armed=False;self.last_command_s=None
        if set(ports)!=set(self.spec['motor_bus']) or len(set(ports.values()))!=len(ports):
            raise ValueError('12V and 5V require distinct named USB interfaces')
        try:
            for bus,path in ports.items():
                port=sdk.PortHandler(path)
                if not port.openPort() or not port.setBaudRate(self.spec['motor_bus'][bus]['baud']):
                    port.closePort();raise OSError('Cannot open bus '+bus)
                self.ports[bus]=port
                reader=sdk.GroupSyncRead(port,self.packet,126,21)
                writer=sdk.GroupSyncWrite(port,self.packet,102,2)
                for j in self.joints:
                    if j['bus']==bus and not reader.addParam(j['motor_id']):raise OSError('Cannot register motor')
                self.readers[bus]=reader;self.writers[bus]=writer
        except Exception:
            self.close();raise

    def _read(self,j,address,size):
        value,comm,error=getattr(self.packet,f'read{size}ByteTxRx')(self.ports[j['bus']],j['motor_id'],address)
        if comm!=self.sdk.COMM_SUCCESS or error:raise OSError(f"{j['name']} read {address}: comm={comm},error={error}")
        return value

    def _write(self,j,address,size,value):
        comm,error=getattr(self.packet,f'write{size}ByteTxRx')(self.ports[j['bus']],j['motor_id'],address,int(value)&((1<<(8*size))-1))
        if comm!=self.sdk.COMM_SUCCESS or error:raise OSError(f"{j['name']} write {address}: comm={comm},error={error}")

    def inspect(self):
        out=[]
        for j in self.joints:
            values={name:self._read(j,address,size) for name,address,size in
                    [('model_number',0,2),('firmware',6,1),('operating_mode',11,1),
                     ('current_limit_ticks',38,2),('torque_enabled',64,1),('hardware_error',70,1),
                     ('watchdog_ticks',98,1),('voltage_tenths',144,2),('temperature_C',146,1)]}
            values.update(joint=j['name'],bus=j['bus'],motor_id=j['motor_id'])
            if values['model_number']!=MODEL_NUMBERS[j['servo']]:raise ValueError('Wrong motor model on '+j['name'])
            out.append(values)
        return out

    def commission_limits(self):
        """Explicit bench operation. Leaves torque OFF; never called by arm."""
        self.disarm();self.inspect()
        for j in self.joints:
            unit=CURRENT_UNIT_A[j['servo']];servo=self.spec['servos'][j['servo']]
            limit=math.floor(servo['current_limit_initial_A']/unit)
            self._write(j,11,1,0)  # EEPROM current control, shared by simulation PD.
            self._write(j,38,2,limit)
            self._write(j,9,1,10)  # 20 us return delay, EEPROM, bench-only.
            self._write(j,98,1,0);self._write(j,102,2,0)
            if self._read(j,11,1)!=0 or self._read(j,38,2)!=limit:raise OSError('Commissioning readback failed')
        return self.inspect()

    def arm(self):
        if not self.calibration or self.calibration.get('commissioning_passed') is not True:
            raise ValueError('Physical joint sign/zero, current/torque and IMU commissioning required')
        names=[j['name'] for j in self.joints]
        if self.calibration.get('joint_names')!=names:raise ValueError('Calibration joint order mismatch')
        for key in ('zero_ticks','sign','Nm_per_A'):
            values=np.asarray(self.calibration[key],float)
            if values.shape!=(len(names),) or not np.isfinite(values).all():raise ValueError('Incomplete calibration '+key)
        if any(v not in (-1,1) for v in self.calibration['sign']) or min(self.calibration['Nm_per_A'])<=0:
            raise ValueError('Invalid motor calibration')
        try:
            for j,status in zip(self.joints,self.inspect()):
                cap=math.floor(self.spec['servos'][j['servo']]['current_limit_initial_A']/CURRENT_UNIT_A[j['servo']])
                if status['operating_mode']!=0 or not 0<status['current_limit_ticks']<=cap:
                    raise ValueError('Hardware current limit/mode not commissioned: '+j['name'])
                if status['hardware_error'] or status['torque_enabled']:raise ValueError('Motor not in healthy torque-off state')
                voltage=status['voltage_tenths']/10
                if not ((10.6<=voltage<=14.0) if j['bus']=='12v' else (4.75<=voltage<=5.25)):
                    raise ValueError('Voltage outside commissioning envelope')
                if status['temperature_C']>=60:raise ValueError('Motor above initial commissioning temperature gate')
            # Validate every bus and motor before enabling any actuator.
            for j in self.joints:
                self._write(j,98,1,0);self._write(j,102,2,0);self._write(j,98,1,5)
            for j in self.joints:
                self._write(j,64,1,1)
            self.armed=True;self.last_command_s=time.monotonic()
        except Exception:
            self.disarm();raise

    def read_encoders(self):
        q=[];dq=[];current=[];voltage=[];temperature=[]
        try:
            for reader in self.readers.values():
                if reader.txRxPacket()!=self.sdk.COMM_SUCCESS:raise OSError('Encoder bus timeout')
            for i,j in enumerate(self.joints):
                reader=self.readers[j['bus']];mid=j['motor_id']
                if not reader.isAvailable(mid,126,21):raise OSError('Missing motor telemetry')
                get=lambda address,size:reader.getData(mid,address,size)
                zero=self.calibration['zero_ticks'][i] if self.calibration else j['motor_zero_ticks']
                sign=self.calibration['sign'][i] if self.calibration else j['motor_sign']
                q.append(sign*(signed(get(132,4),32)-zero)*2*math.pi/4096)
                dq.append(sign*signed(get(128,4),32)*.229*2*math.pi/60)
                current.append(sign*signed(get(126,2),16)*CURRENT_UNIT_A[j['servo']])
                voltage.append(get(144,2)*.1);temperature.append(get(146,1))
            if self.armed:
                for i,j in enumerate(self.joints):
                    lo,hi=j['range_rad']
                    if not lo-.04<=q[i]<=hi+.04 or temperature[i]>=60:raise ValueError('Joint/thermal stop')
                    if not ((10.6<=voltage[i]<=14.0) if j['bus']=='12v' else (4.75<=voltage[i]<=5.25)):
                        raise ValueError('Supply stop')
                    if self._read(j,70,1):raise ValueError('Motor hardware fault')
            return {key:np.asarray(value,float) for key,value in zip(
                ('positions_rad','velocities_rad_s','motor_current_A','supply_voltage_V','temperature_C'),(q,dq,current,voltage,temperature))}
        except Exception:
            if self.armed:self.disarm()
            raise

    def write_torques(self,torque_Nm):
        if not self.armed:raise RuntimeError('Robot is not armed')
        torque=np.asarray(torque_Nm,float)
        if torque.shape!=(len(self.joints),) or not np.isfinite(torque).all():self.disarm();raise ValueError('Invalid torque command')
        if time.monotonic()-self.last_command_s>.08:self.disarm();raise TimeoutError('Control stream expired; deliberate re-arm required')
        try:
            for writer in self.writers.values():writer.clearParam()
            for i,j in enumerate(self.joints):
                servo=self.spec['servos'][j['servo']];unit=CURRENT_UNIT_A[j['servo']]
                current=np.clip(torque[i]/self.calibration['Nm_per_A'][i],-servo['current_limit_initial_A'],servo['current_limit_initial_A'])
                ticks=int(np.trunc(current*self.calibration['sign'][i]/unit))&0xffff
                if not self.writers[j['bus']].addParam(j['motor_id'],[ticks&255,ticks>>8]):raise OSError('Cannot enqueue current')
            for writer in self.writers.values():
                if writer.txPacket()!=self.sdk.COMM_SUCCESS:raise OSError('Current command transmission failed')
            self.last_command_s=time.monotonic()
        except Exception:self.disarm();raise

    def disarm(self):
        for j in self.joints:
            if j['bus'] not in self.ports:continue
            try:self._write(j,64,1,0)
            except OSError:pass  # Hardware watchdog/physical stop remain necessary on bus loss.
        self.armed=False;self.last_command_s=None

    def close(self):
        if self.armed:self.disarm()
        for port in self.ports.values():port.closePort()
        self.ports.clear()

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
