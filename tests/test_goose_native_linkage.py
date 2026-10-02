"""Physical jaw-linkage invariants and unchanged eighteen-action SI interface."""
import json
from pathlib import Path

import mujoco
import numpy as np
import pytest

from sai_agent.goose.native_linkage import set_passive_linkage
from sai_agent.goose.stage_one import StageOneEnv
from sai_agent.goose.stage_one_gravity import NominalNeckGravity

ROBOT = Path(__file__).resolve().parents[1] / 'robots/Goose_V0.1'


@pytest.fixture(scope='module')
def reference():
    contract = json.loads((ROBOT/'configs/mechanical_reference_contract.json').read_text())
    model = mujoco.MjModel.from_xml_path(str(ROBOT/'models/mechanical_reference/robot.xml'))
    return contract, model


def test_both_real_coupler_pins_remain_concentric_through_opening(reference):
    contract, model = reference
    data = mujoco.MjData(model)
    linkage = contract['beak_transmission']
    motor, jaw = map(np.array, [linkage['drive_axis_world_m'], linkage['jaw_axis_world_m']])
    phase, radius = linkage['closed_crank_angle_in_xz_rad'], linkage['crank_radius_m']
    crank = radius*np.array([np.cos(phase), 0., np.sin(phase)])
    for angle in np.linspace(0., .55, 29):
        data.qpos[model.joint('beak_hinge').qposadr[0]] = angle
        set_passive_linkage(model, data, contract)
        mujoco.mj_forward(model, data)
        ri = data.xmat[model.body('beak_input_rotor').id].reshape(3,3)
        ro = data.xmat[model.body('beak_hinge').id].reshape(3,3)
        rc = data.xmat[model.body('beak_coupler_link').id].reshape(3,3)
        pi = data.xpos[model.body('beak_input_rotor').id] + ri@crank
        pc = data.xpos[model.body('beak_coupler_link').id]
        po = data.xpos[model.body('beak_hinge').id] + ro@crank
        np.testing.assert_allclose(pi, pc, atol=1e-12)
        np.testing.assert_allclose(po, pc+rc@(jaw-motor), atol=1e-12)
        np.testing.assert_allclose(rc, data.xmat[model.body('head_roll').id].reshape(3,3), atol=1e-12)
    assert model.actuator('beak_hinge_motor').trnid[0] == model.joint('beak_input_rotor').id


def test_moving_body_split_preserves_full_zero_pose_mass_com_and_tensor(reference):
    contract, model = reference
    ledger = json.loads((ROBOT/'evidence/body_bay_mechanical_parameters.json').read_text())
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    mass = float(model.body_mass.sum())
    com = sum(model.body_mass[k]*data.xipos[k] for k in range(1,model.nbody))/mass
    expected_mass = sum(b['mass_kg'] for b in ledger['bodies'])
    centers = {b['name']:np.array(ledger['pivots_world_at_zero_m'][b['name']])+b['com_local_m'] for b in ledger['bodies']}
    expected_com = sum(b['mass_kg']*centers[b['name']] for b in ledger['bodies'])/expected_mass
    tensor = np.zeros((3,3))
    for k in range(1,model.nbody):
        rotation = data.ximat[k].reshape(3,3)
        delta = data.xipos[k]-com
        tensor += rotation@np.diag(model.body_inertia[k])@rotation.T + model.body_mass[k]*(delta@delta*np.eye(3)-np.outer(delta,delta))
    expected_tensor = sum(np.array(b['inertia_at_com_body_kg_m2'])+b['mass_kg']*((centers[b['name']]-expected_com)@(centers[b['name']]-expected_com)*np.eye(3)-np.outer(centers[b['name']]-expected_com,centers[b['name']]-expected_com)) for b in ledger['bodies'])
    assert mass == pytest.approx(expected_mass,abs=1e-11)
    np.testing.assert_allclose(com,expected_com,atol=1e-12)
    np.testing.assert_allclose(tensor,expected_tensor,atol=1e-12)


def test_neck_feedforward_includes_actual_moving_crank_and_coupler(reference):
    contract, model = reference
    data = mujoco.MjData(model)
    feedforward = NominalNeckGravity(contract)
    rng = np.random.default_rng(412)
    names = contract['joint_order'][:6]
    qadr = [model.joint(n).qposadr[0] for n in names]
    vadr = [model.joint(n).dofadr[0] for n in names[:5]]
    for _ in range(12):
        q = rng.uniform(-.4,.4,6);q[5]=rng.uniform(0,.55)
        data.qpos[qadr] = q
        data.qpos[3:7] = rng.normal(size=4);data.qpos[3:7]/=np.linalg.norm(data.qpos[3:7])
        set_passive_linkage(model,data,contract);mujoco.mj_forward(model,data)
        np.testing.assert_allclose(feedforward(q,data.qpos[3:7]),data.qfrc_bias[vadr],atol=1e-10)


def test_current_soft_sole_model_loads_without_changing_policy_dimensions():
    environment = StageOneEnv(ROBOT/'models/mechanical_physics/robot.xml',
                              ROBOT/'configs/mechanical_physics_contract.json',
                              num_envs=1,randomize=False,commands=False,auto_reset=False)
    observation,reward,done,rows=environment.step(np.zeros((1,18)))
    assert observation.shape == (1,65)
    assert np.isfinite(observation).all() and np.isfinite(reward).all()
    assert environment.models[0].nu == 18
    assert environment.models[0].opt.timestep == pytest.approx(.0001)
    assert not done[0]  # A zero-height frame must not be mistaken for a fall.
    assert rows[0]['height_m'] > .18
