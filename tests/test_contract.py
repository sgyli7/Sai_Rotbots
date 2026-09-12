from pathlib import Path
import hashlib
import json
import numpy as np
import mujoco
from sai_agent.control import observation_numpy,targets_numpy,torque_numpy,filter_action_numpy
from sai_agent.runtime import JointAdapter

ROOT=Path(__file__).resolve().parents[1]


def test_sensor_frame_is_body_relative_and_si():
    # Body faces world +Y, travelling 1 m/s forward. No world-XY substitution.
    q=np.zeros(23);q[2]=.2192;q[3]=q[6]=np.sqrt(.5)
    v=np.zeros(22);v[1]=1.;v[5]=.4
    obs=observation_numpy(q,v,[.2,.4],0.,np.zeros(16),0.,np.zeros(24))
    assert obs.shape==(82,) and obs.dtype==np.float32
    np.testing.assert_allclose(obs[:9],[0,0,1,1,0,0,0,0,.4],atol=1e-6)
    np.testing.assert_allclose(obs[58:],0,atol=1e-6)


def test_wheel_speed_control_ignores_wheel_revolution_position():
    q=np.zeros(23);q[3]=1.;v=np.zeros(22)
    target=targets_numpy(np.zeros(16),[.12,0],0)
    expected=torque_numpy(q,v,target)
    q[10::4]=[100.,-200.,300.,-400.]
    np.testing.assert_allclose(torque_numpy(q,v,target),expected)
    np.testing.assert_allclose(expected[3::4],[1.,-1.,1.,-1.])


def test_stop_uses_physical_brake_and_crouch_reference():
    raw=np.ones(16)*20
    np.testing.assert_array_equal(filter_action_numpy(raw,[0,0]),np.zeros(16))
    stand=targets_numpy(raw,[0,0],0)
    crouch=targets_numpy(raw,[0,0],1)
    np.testing.assert_allclose(stand,0,atol=1e-6)
    assert np.linalg.norm(crouch)>1
    np.testing.assert_array_equal(crouch[3::4],np.zeros(4))


def test_full_model_retains_articulation_and_policy_uses_named_joints():
    model=mujoco.MjModel.from_xml_path(str(ROOT/'models/full/robot.xml'))
    adapter=JointAdapter(model)
    assert model.nu==23 and model.neq==2
    assert len(set(adapter.aids))==16 and len(adapter.held)==7
    robot_mass=model.body_mass.sum()-model.body_mass[model.body('item').id]
    manifest=json.loads((ROOT/'models/robot_manifest.json').read_text())
    assert abs(robot_mass-manifest['model_total_mass_kg'])<1e-10
    assert model.joint('cargo_slide_-1').type==mujoco.mjtJoint.mjJNT_SLIDE
    assert model.joint('cargo_slide_1').type==mujoco.mjtJoint.mjJNT_SLIDE


def test_public_actor_hash_matches_its_contract():
    metadata=json.loads((ROOT/'policies/flat-v1.json').read_text())
    assert metadata['contract_id']=='sai-flat-v1'
    assert metadata['normalization_included']
    assert hashlib.sha256((ROOT/'policies/flat-v1.onnx').read_bytes()).hexdigest()==metadata['onnx_sha256']
