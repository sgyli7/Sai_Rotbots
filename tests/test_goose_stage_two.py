"""Cross-check supported reach and reject unsafe parameter reuse."""
import copy
import importlib.util
import json
from pathlib import Path

import mujoco
import numpy as np
import pytest

from sai_agent.goose.low_reach import SupportedReach

ROOT = Path(__file__).resolve().parents[1]
ROBOT = ROOT / 'robots/Goose_V0.1'


def load_script(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def contract():
    return json.loads((ROBOT / 'configs/stage_two_contract.json').read_text())


def test_supported_reach_fk_matches_mujoco_for_nonzero_root_and_joints(contract):
    reference = SupportedReach(contract, np.zeros(18))
    model = mujoco.MjModel.from_xml_path(str(ROBOT / 'models/stage_two/robot.xml'))
    data = mujoco.MjData(model)
    rng = np.random.default_rng(425)
    for _ in range(20):
        data.qpos[:3] = rng.uniform(-.2, .2, 3)
        data.qpos[3:7] = rng.normal(size=4)
        data.qpos[3:7] /= np.linalg.norm(data.qpos[3:7])
        q = np.array([rng.uniform(*j['range_rad']) for j in contract['joints']])
        data.qpos[7:] = q
        mujoco.mj_forward(model, data)
        positions, rotations = reference.forward(q, data.qpos[3:7])
        for name in contract['joint_order']:
            body = model.body(name).id
            np.testing.assert_allclose(positions[name] + data.qpos[:3], data.xpos[body], atol=1e-12)
            np.testing.assert_allclose(rotations[name], data.xmat[body].reshape(3, 3), atol=1e-12)


def test_supported_reach_completes_return_in_nominal_and_previous_failing_seed():
    evaluation = load_script('scripts/evaluation/evaluate_goose_supported_reach.py')
    result = evaluation.evaluate(seeds=(903,))
    assert result['all_passed']
    for case in result['cases']:
        assert case['steps'] == 1400
        assert case['final_joint_error_max_rad'] < .06
        assert case['final_root_upright'] > .99
        assert abs(case['final_root_height_m'] - .29) < .01
        assert case['both_feet_contact_fraction'] > .98


def test_change_budget_accepts_identical_parameters_but_never_certifies_policy(contract):
    comparison = load_script('scripts/diagnostics/compare_goose_parameter_versions.py')
    result = comparison.compare(contract, copy.deepcopy(contract))
    assert not result['requires_new_training_version']
    assert not result['policy_reuse_approved']


@pytest.mark.parametrize('mutation', ['redistribute_mass', 'contact', 'clock', 'action_scale', 'remove_body'])
def test_change_budget_detects_changes_hidden_by_equal_total_mass(contract, mutation):
    comparison = load_script('scripts/diagnostics/compare_goose_parameter_versions.py')
    changed = copy.deepcopy(contract)
    if mutation == 'redistribute_mass':
        changed['bodies'][0]['mass_kg'] += .8
        changed['bodies'][1]['mass_kg'] -= .8
    elif mutation == 'contact':
        next(g for g in changed['collision_geometries'] if int(g.get('contype', 1)))['pos'] = '0 0 0.1'
    elif mutation == 'clock':
        changed['torque_dt_s'] *= 2
    elif mutation == 'action_scale':
        changed['joints'][0]['action_scale_rad'] *= .8
    else:
        changed['bodies'].pop()
    assert changed['nominal_robot_mass_kg'] == contract['nominal_robot_mass_kg']
    assert comparison.compare(contract, changed)['requires_new_training_version']
