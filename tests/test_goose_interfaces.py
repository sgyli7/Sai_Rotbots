"""Failures at the engine/hardware boundary must stop before motion."""
import copy
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from sai_agent.goose.control import metadata,observation,OBS_SIZE
from sai_agent.goose.control import JointMap
from sai_agent.goose.protocol import SensorFrame,torque_message,encode_message
from sai_agent.goose.behavior import TaskSequencer,TaskSignals,PerceivedTarget,Phase
from sai_agent.goose.hardware import signed,DynamixelRobot
from sai_agent.goose.spec import load_spec
from sai_agent.paths import resource_root


def message():
    contract=metadata();n=len(contract['encoder_joint_names'])
    return {'contract':contract['version'],'joint_names':contract['encoder_joint_names'],
            'units':'SI','sequence':1,'timestamp_s':.02,'positions_rad':[0.]*n,
            'velocities_rad_s':[0.]*n,'gyro_body_rad_s':[0.,0.,0.],
            'gravity_body_unit':[0.,0.,-1.]}


@pytest.mark.parametrize('change',[{'units':'engine_native'}, {'sequence':True},
    {'sequence':-1},{'timestamp_s':float('nan')},{'gravity_body_unit':[0,0,0]},
    {'positions_rad':[0.]},{'gyro_body_rad_s':[float('inf'),0,0]}])
def test_bad_sensor_boundary_is_rejected(change):
    value=message();value.update(change)
    with pytest.raises(ValueError):SensorFrame.from_message(value)


def test_joint_order_and_torque_envelope_are_enforced():
    value=message();names=value['joint_names'].copy();value['joint_names']=names[::-1]
    with pytest.raises(ValueError):SensorFrame.from_message(value)
    frame=SensorFrame.from_message(message());n=len(names)
    for torque,limits in [(np.ones(n)*1.01,np.ones(n)),(np.zeros(n),np.zeros(n)),
                         (np.zeros(n),np.full(n,float('nan')))]:
        with pytest.raises(ValueError):torque_message(frame,names,torque,limits)
    with pytest.raises(ValueError):torque_message(frame,names,np.zeros(n),np.ones(n),.101)
    result=torque_message(frame,names,np.ones(n)*.3,np.ones(n))
    assert result['units']=='SI' and b'NaN' not in encode_message(result)


def test_53_observations_are_sensor_only():
    spec=load_spec();home=np.array([j['home_rad'] for j in spec['joints']]);n=len(home)
    obs=observation([.4,0,0],[0,0,-1],[.05,0,0],home+.1,np.ones(n),home,np.zeros(10),0.)
    assert obs.shape==(OBS_SIZE,) and obs[0]==pytest.approx(.1)
    assert np.allclose(obs[9:9+n],.1) and np.allclose(obs[9+n:9+2*n],.05)
    assert obs[-2:].tolist()==[0.,1.]


def test_actuator_speed_guard_does_not_drive_overspeed():
    import mujoco
    path=resource_root()/'robots/Goose_V0.1/models/full/robot.xml'
    mapping=JointMap(mujoco.MjModel.from_xml_path(str(path)))
    q=mapping.home.copy();velocity=np.zeros(len(q));velocity[3]=mapping.speed_limits[3]+.5
    targets=q.copy();targets[3]+=.2
    torque=mapping.torque(q,velocity,targets)
    assert torque[3]<=0
    assert np.all(np.abs(torque)<=mapping.limits+1e-12)


def test_drag_waits_for_executor_and_force_measurement():
    task=TaskSequencer();task.start(7,'drag',0.,destination_marker_id=9)
    target=PerceivedTarget(7,.01,np.array([.32,0,-.2]),60.,.1)
    assert task.update(TaskSignals(.01,0,0),target)['velocity_command_m_s_rad_s']==[0.,0.,0.]
    for now in (.02,.03):
        task.update(TaskSignals(now,0,0,executor_ready=True),target)
    task.update(TaskSignals(.04,0,0,executor_ready=True,motion_complete=True),target)
    task.update(TaskSignals(.05,0,0,executor_ready=True,grip_confirmed=True),target)
    assert task.phase==Phase.DRAG
    result=task.update(TaskSignals(.06,0,0,executor_ready=True,grip_confirmed=True),target)
    assert result['phase']=='stop' and result['reason']=='calibrated_drag_force_observer_required'


def test_honk_is_one_event_on_completion():
    task=TaskSequencer();task._enter(Phase.DONE,1.)
    assert task.update(TaskSignals(1.,0,0),None)['honk']
    assert not task.update(TaskSignals(1.02,0,0),None)['honk']


def test_motor_signed_conversion_and_preflight_before_enable():
    assert signed(0xffff,16)==-1 and signed(0x80000000,32)==-2147483648
    robot=object.__new__(DynamixelRobot);robot.spec=load_spec();robot.joints=robot.spec['joints']
    n=len(robot.joints);robot.calibration={'commissioning_passed':True,
        'joint_names':[j['name'] for j in robot.joints], 'zero_ticks':[2048]*n,
        'sign':[1]*n,'Nm_per_A':[1.]*n}
    statuses=[]
    for j in robot.joints:
        statuses.append({'operating_mode':0,'current_limit_ticks':100,'hardware_error':0,
                        'torque_enabled':0,'voltage_tenths':120 if j['bus']=='12v' else 50,
                        'temperature_C':25})
    statuses[-1]['hardware_error']=4
    robot.inspect=lambda:statuses;writes=[];robot._write=lambda *args:writes.append(args)
    robot.disarm=lambda:None
    with pytest.raises(ValueError):robot.arm()
    assert not any(args[1]==64 and args[3]==1 for args in writes)
