"""A packaged exploration model must preserve its SI source identity and force bounds."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil

import mujoco
import numpy as np
import pytest

from sai_agent.cli import prepare_godot
from sai_agent.paths import model_root, robot_catalog


ROOT = Path(__file__).resolve().parents[1]
CHECKER_SPEC = importlib.util.spec_from_file_location(
    'gorilla_resource_check', ROOT / 'scripts/diagnostics/check_distribution.py')
CHECKER = importlib.util.module_from_spec(CHECKER_SPEC)
CHECKER_SPEC.loader.exec_module(CHECKER)


@pytest.fixture
def candidate():
    full = model_root('gorilla_v0_1', ROOT) / 'full'
    contract = json.loads((full / 'robot.json').read_text())
    model = mujoco.MjModel.from_xml_path(str(full / 'robot.xml'))
    return contract, model


def test_source_model_matches_si_contract_and_design_hashes():
    contract = CHECKER.check_gorilla_resource_contract(model_root('gorilla_v0_1', ROOT), ROOT)
    assert contract['coordinates'] == {'forward': '+X', 'left': '+Y', 'up': '+Z', 'units': 'SI'}


def test_gorilla_keeps_existing_defaults_and_has_no_game_policy(tmp_path, monkeypatch):
    monkeypatch.delenv('SAI_ROBOT_ID', raising=False)
    assert model_root(root=ROOT) == model_root('Sai_Agent_001', ROOT)
    assert model_root('Sai_Agent_002', ROOT) == ROOT / 'robots/Sai_Agent_002/models'
    entry = robot_catalog(ROOT)['gorilla_v0_1']
    assert entry['godot_supported'] is False
    assert entry['bevy_acceptance'] is False and entry['policy_included'] is False
    destination = tmp_path / 'gorilla'
    with pytest.raises(ValueError, match='engineering layout'):
        prepare_godot(ROOT, destination, 'gorilla_v0_1')
    assert not destination.exists()


def test_reversed_joint_axis_is_rejected(candidate):
    contract, model = candidate
    joint_id = model.joint(contract['joint_order'][0]).id
    model.jnt_axis[joint_id] *= -1
    with pytest.raises(AssertionError, match='joint axis differs'):
        CHECKER._check_gorilla_model(contract, model)


def test_actuator_mapping_cannot_follow_body_tree_order(candidate):
    contract, model = candidate
    model.actuator_trnid[0, 0] = model.joint(contract['joint_order'][1]).id
    with pytest.raises(AssertionError, match='actuator joint differs'):
        CHECKER._check_gorilla_model(contract, model)


@pytest.mark.parametrize('disabled', [False, True], ids=['raised_force', 'disabled_clamp'])
def test_native_actuator_force_bounds_cannot_be_relaxed(candidate, disabled):
    contract, model = candidate
    if disabled:
        model.actuator_forcelimited[0] = False
    else:
        model.actuator_forcerange[0] *= 2
    with pytest.raises(AssertionError, match='force limit'):
        CHECKER._check_gorilla_model(contract, model)


def test_full_inertia_checks_products_of_inertia(candidate):
    contract, model = candidate
    contract = copy.deepcopy(contract)
    body_name = next(iter(contract['bodies']))
    body = contract['bodies'][body_name]
    tensor = np.asarray(body['inertia_body_frame_kg_m2'])
    tensor[0, 1] += .01
    tensor[1, 0] += .01
    body['inertia_body_frame_kg_m2'] = tensor.tolist()
    body['fullinertia_kg_m2'] = tensor[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]].tolist()
    with pytest.raises(AssertionError, match='full inertia differs'):
        CHECKER._check_gorilla_model(contract, model)


def test_gravity_compensation_cannot_hide_free_root_support(candidate):
    contract, model = candidate
    model.body_gravcomp[model.body(next(iter(contract['bodies']))).id] = 1
    with pytest.raises(AssertionError, match='Gravity compensation'):
        CHECKER._check_gorilla_model(contract, model)


def test_diagnostic_clock_cannot_drift_from_contract(candidate):
    contract, model = candidate
    model.opt.timestep *= 2
    with pytest.raises(AssertionError, match='Diagnostic timestep differs'):
        CHECKER._check_gorilla_model(contract, model)


def test_sensor_mount_identity_is_not_inferred_from_name(candidate):
    contract, model = candidate
    sensor = contract['sensors'][0]
    site_id = model.site(sensor['name'] + '_mount').id
    model.site_bodyid[site_id] = model.body(next(iter(contract['bodies']))).id
    with pytest.raises(AssertionError, match='Sensor mount body differs'):
        CHECKER._check_gorilla_model(contract, model)


def test_old_mesh_cannot_be_hidden_in_manifest(tmp_path):
    source = model_root('gorilla_v0_1', ROOT)
    models = tmp_path / 'models'
    shutil.copytree(source / 'full', models / 'full')
    contract_path = models / 'full/robot.json'
    contract = json.loads(contract_path.read_text())
    orphan = models / 'full/assets/old_orphan.obj'
    orphan.write_text('# Old unreferenced mesh\n')
    contract['asset_manifest']['assets/old_orphan.obj'] = CHECKER._sha256(orphan)
    contract_path.write_text(json.dumps(contract))
    with pytest.raises(AssertionError, match='Mesh manifest differs from XML references'):
        CHECKER.check_gorilla_resource_contract(models)


@pytest.mark.parametrize('target', ['robot.xml', 'asset'], ids=['model_bytes', 'mesh_bytes'])
def test_packaged_model_and_mesh_hashes_reject_stale_bytes(tmp_path, target):
    source = model_root('gorilla_v0_1', ROOT)
    models = tmp_path / 'models'
    shutil.copytree(source / 'full', models / 'full')
    contract = json.loads((models / 'full/robot.json').read_text())
    relative = target if target != 'asset' else next(iter(contract['asset_manifest']))
    path = models / 'full' / relative
    path.write_bytes(path.read_bytes() + b'\n# stale resource\n')
    with pytest.raises(AssertionError, match='hash differs'):
        CHECKER.check_gorilla_resource_contract(models)
