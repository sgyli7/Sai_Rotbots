"""Independent MuJoCo gravity/Jacobian check of neutral static support torques."""
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from sai_agent.goose.double_support import NominalDoubleSupport
from sai_agent.goose.native_linkage import set_passive_linkage
from sai_agent.goose.supported_manipulation import SupportedManipulation

ROOT = Path(__file__).resolve().parents[1]
ROBOT = ROOT/'robots/Goose_V0.1'


@pytest.fixture(scope='module')
def nominal_model():
    contract = json.loads((ROBOT/'configs/tip_grip_physics_contract.json').read_text())
    ledger = json.loads((ROBOT/'evidence/body_bay_mechanical_parameters.json').read_text())
    model_file = ROBOT/'models/tip_grip_physics/robot.xml'
    assert hashlib.sha256(model_file.read_bytes()).hexdigest() == contract['model_sha256']
    model = mujoco.MjModel.from_xml_path(str(model_file))
    helper = NominalDoubleSupport(contract, ledger['contact_center_y_m'], ledger['contact_hulls'])
    low = json.loads((ROBOT/'evidence/tip_grip_finite_reach.json').read_text())['selected_candidate']
    return contract, model, helper, low


@pytest.mark.parametrize('case', ['neutral_tilt', 'low_bare', 'low_payload'])
def test_static_torque_matches_independent_mujoco_jacobian(nominal_model, case):
    contract, model, helper, low = nominal_model
    names = contract['joint_order']
    q = np.zeros(len(names)) if case == 'neutral_tilt' else np.array([low['q_rad'][n] for n in names])
    q[names.index('beak_hinge')] = .30
    r = Rotation.from_rotvec([.03, -.02, 0.]) if case == 'neutral_tilt' else Rotation.identity()
    quat = r.as_quat()[[3, 0, 1, 2]]
    payload = .050 if case == 'low_payload' else 0.
    point = np.array(contract['front_contact_native_world_m'])+[0., 0., .0037]
    estimate = helper.estimate(q, quat, payload, point)
    assert estimate['nominal_support_feasible']
    data = mujoco.MjData(model)
    data.qpos[:3] = estimate['estimated_root_position_m']
    data.qpos[3:7] = quat
    for n, value in zip(names, q):
        data.qpos[model.joint(n).qposadr[0]] = value
    set_passive_linkage(model, data, contract)
    mujoco.mj_forward(model, data)
    applied = np.zeros(model.nv)
    for contact in estimate['contacts']:
        mujoco.mj_applyFT(model, data, contact['force_world_n'], np.zeros(3),
                         contact['point_world_m'], model.body(contact['body']).id, applied)
    if payload:
        hid = model.body('head_roll').id
        pivot = np.array(next(j for j in contract['joints'] if j['name'] == 'head_roll')['pivot_world_at_zero_m'])
        world = data.xpos[hid]+data.xmat[hid].reshape(3, 3)@(point-pivot)
        mujoco.mj_applyFT(model, data, [0., 0., -payload*9.81], np.zeros(3), world, hid, applied)
    required = data.qfrc_bias-applied
    independent = np.array([required[model.joint(n).dofadr[0]] for n in names])
    for j in contract['passive_linkage_joints']:
        independent[names.index(j['mimic_joint'])] += j['mimic_multiplier']*required[model.joint(j['name']).dofadr[0]]
    np.testing.assert_allclose(estimate['torque_nm'], independent, rtol=0, atol=1e-9)
    np.testing.assert_allclose(required[:6], 0., rtol=0, atol=1e-8)


def test_invalid_imu_is_rejected(nominal_model):
    contract, model, helper, low = nominal_model
    with pytest.raises(ValueError, match='IMU'):
        helper.estimate(np.zeros(len(contract['joint_order'])), [0., 0., 0., 0.])


def test_finite_reference_matches_independent_mujoco_fk(nominal_model):
    contract, model, helper, low = nominal_model
    names = contract['joint_order']
    point = np.array(contract['front_contact_native_world_m'])+[0., 0., .0037]
    plan = SupportedManipulation(helper, contract, [low['q_rad'][n] for n in names],
                                 point, low['actual_front_contact_world_m'], 'constant_pitch')
    q = plan.stand.copy()
    data = mujoco.MjData(model)
    head = model.body('head_roll').id
    local = point-helper.pivots['head_roll']
    for t in np.arange(0., plan.duration_s, .020):
        commanded, metadata = plan.reference_at(t, q, [1., 0., 0., 0.])
        for i, joint in enumerate(contract['joints']):
            assert joint['range_rad'][0] <= commanded[i] <= joint['range_rad'][1]
            assert abs(commanded[i]-q[i])/.020 <= joint['speed_limit_rad_s']
            data.qpos[model.joint(names[i]).qposadr[0]] = commanded[i]
        data.qpos[:3] = helper.root_from_supported_feet(commanded, [1., 0., 0., 0.])
        data.qpos[3:7] = [1., 0., 0., 0.]
        set_passive_linkage(model, data, contract)
        # Independent engine kinematics; no contact solver or controller feedforward.
        mujoco.mj_kinematics(model, data)
        if metadata['phase'] not in ['settle', 'crouch', 'rise', 'final_settle']:
            actual = data.xpos[head]+data.xmat[head].reshape(3, 3)@local
            np.testing.assert_allclose(actual, metadata['target_point_world_m'], rtol=0, atol=1e-5)
        q = commanded
