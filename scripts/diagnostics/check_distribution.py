"""Check a wheel's exact resource inventory using its freshly installed Python."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib
import xml.etree.ElementTree as ET
import zipfile

import mujoco
import numpy as np
import sai_agent
from sai_agent.paths import resource_root, model_root, robot_catalog
from sai_agent.godot_controller import GodotController
from sai_agent.cargo_godot import CargoGodotController
from sai_agent.cargo_task import CargoTask
from sai_agent.legacy_crawl import CrawlTransport


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_gorilla_model(contract, model):
    """Check the compiled candidate against its own SI contract, not Goose's ABI."""
    order = contract['joint_order']
    joints = contract['joints']
    bodies = contract['bodies']
    assert order == [joint['name'] for joint in joints], 'Joint contract order differs'
    assert len(set(order)) == len(order), 'Duplicate contract joint names'
    count = len(order)
    assert model.nu == count == contract['active_joint_count'], 'Actuator count differs'
    assert contract['free_root_dof'] == 6
    assert model.nv == count + 6 and model.nq == count + 7, 'Free-root dimensions differ'
    free = np.flatnonzero(model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)
    assert len(free) == 1 and free[0] == 0, 'Exactly one free root is required'
    assert model.jnt_qposadr[free[0]] == 0 and model.jnt_dofadr[free[0]] == 0
    assert model.neq == 0, 'Equality constraints may provide hidden support'
    assert model.ntendon == 0, 'Candidate must not contain tendon assistance'
    assert model.nmocap == 0, 'Candidate must not contain mocap root support'
    assert not np.any(model.body_gravcomp), 'Gravity compensation may provide hidden support'
    assert not np.any(model.jnt_stiffness), 'Passive springs may conceal motor demand'
    assert not np.any(model.dof_damping[:6]), 'Free root must not have damping assistance'
    assert not model.opt.disableflags & mujoco.mjtDisableBit.mjDSBL_GRAVITY, 'Gravity is disabled'
    np.testing.assert_allclose(model.opt.gravity, contract['gravity_m_s2'], atol=1e-12)
    np.testing.assert_allclose(model.opt.timestep, contract['timing']['mujoco_diagnostic_dt_s'],
                               atol=1e-12, err_msg='Diagnostic timestep differs')
    assert model.nbody - 1 == len(bodies) == contract['body_count'], 'Body inventory differs'
    assert {model.body(i).name for i in range(1, model.nbody)} == set(bodies)
    np.testing.assert_allclose(model.body_mass.sum(), contract['total_robot_mass_kg'], rtol=1e-10)
    np.testing.assert_allclose(sum(body['mass_kg'] for body in bodies.values()),
                               contract['total_robot_mass_kg'], rtol=1e-12)

    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    addresses = contract['control_contract']
    for actuator_id, joint in enumerate(joints):
        name = joint['name']
        joint_id = model.joint(name).id
        child_id = model.body(joint['child']).id
        assert model.jnt_type[joint_id] == mujoco.mjtJoint.mjJNT_HINGE, name
        assert model.jnt_bodyid[joint_id] == child_id, f'{name}: child body differs'
        assert model.body_parentid[child_id] == model.body(joint['parent']).id, name
        np.testing.assert_allclose(model.jnt_axis[joint_id], joint['axis_parent'],
                                   atol=1e-12, err_msg=f'{name}: joint axis differs')
        np.testing.assert_allclose(data.xanchor[joint_id], joint['position_world_m'],
                                   atol=1e-9, err_msg=f'{name}: neutral anchor differs')
        assert model.jnt_limited[joint_id], f'{name}: joint limit is disabled'
        np.testing.assert_allclose(model.jnt_range[joint_id], joint['range_rad'], atol=1e-12)
        assert model.jnt_qposadr[joint_id] == addresses['qpos_addresses'][name], name
        assert model.jnt_dofadr[joint_id] == addresses['dof_addresses'][name], name
        assert data.qpos[model.jnt_qposadr[joint_id]] == joint['qpos_neutral_rad'], name
        assert model.actuator(actuator_id).name == name + '_drive', 'Actuator order differs'
        assert model.actuator_trntype[actuator_id] == mujoco.mjtTrn.mjTRN_JOINT
        assert model.actuator_trnid[actuator_id, 0] == joint_id, f'{name}: actuator joint differs'
        np.testing.assert_allclose(model.actuator_gear[actuator_id], [1, 0, 0, 0, 0, 0], atol=1e-12)
        assert model.actuator_ctrllimited[actuator_id], f'{name}: control limit is disabled'
        np.testing.assert_allclose(model.actuator_ctrlrange[actuator_id], joint['range_rad'], atol=1e-12)
        assert model.actuator_forcelimited[actuator_id], f'{name}: force limit is disabled'
        drive = contract['drive_classes'][joint['drive_class']]
        limit = drive['design_torque_nm']
        assert np.isfinite(limit) and limit > 0
        np.testing.assert_allclose(model.actuator_forcerange[actuator_id], [-limit, limit],
                                   rtol=1e-12, err_msg=f'{name}: force limit differs')
        assert model.dof_armature[model.jnt_dofadr[joint_id]] == drive['armature_kg_m2']

    for name, body in bodies.items():
        body_id = model.body(name).id
        tensor = np.asarray(body['inertia_body_frame_kg_m2'])
        assert tensor.shape == (3, 3) and np.isfinite(tensor).all(), name
        np.testing.assert_allclose(tensor, tensor.T, atol=1e-12)
        eigenvalues = np.linalg.eigvalsh(tensor)
        assert eigenvalues[0] > 0 and eigenvalues[-1] <= eigenvalues[:2].sum() + 1e-9, name
        np.testing.assert_allclose(body['fullinertia_kg_m2'],
                                   tensor[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]], atol=1e-12)
        np.testing.assert_allclose(model.body_mass[body_id], body['mass_kg'], rtol=1e-10)
        np.testing.assert_allclose(model.body_ipos[body_id], body['com_local_m'], atol=1e-9)
        rotation = np.zeros(9)
        mujoco.mju_quat2Mat(rotation, model.body_iquat[body_id])
        rotation = rotation.reshape(3, 3)
        compiled = rotation @ np.diag(model.body_inertia[body_id]) @ rotation.T
        tolerance = 1e-9 + 2e-6 * np.linalg.norm(tensor, ord=2)
        assert np.max(np.abs(compiled - tensor)) <= tolerance, f'{name}: full inertia differs'
        np.testing.assert_allclose(data.xipos[body_id], body['com_world_neutral_m'], atol=1e-9)
        np.testing.assert_allclose(data.xpos[body_id], contract['body_origins_world_m'][name], atol=1e-9)

    for sensor in contract['sensors']:
        site_id = model.site(sensor['name'] + '_mount').id
        assert model.site_bodyid[site_id] == model.body(sensor['body']).id, 'Sensor mount body differs'
        np.testing.assert_allclose(data.site_xpos[site_id], sensor['position_world_m'], atol=1e-9)
    assert model.ncam == 0 and model.nsensor == 0, 'Mount sites are not implemented cameras or sensors'
    assert contract['physical_hard_freeze'] is False
    assert contract['bevy_acceptance'] is False and contract['hardware_validation'] is False
    assert 'exploratory' in contract['maturity'], 'Candidate must retain exploratory maturity'
    assert addresses['learning_policy'] is None and addresses['learning_observation_contract'] is None
    assert addresses['latency_and_bevy_adapter_verified'] is False
    for control in (model.actuator_ctrlrange[:, 0] - 1e6, model.actuator_ctrlrange[:, 1] + 1e6):
        data.ctrl[:] = control
        mujoco.mj_forward(model, data)
        assert np.isfinite(data.actuator_force).all(), 'Nonfinite native actuator force'
        assert np.all(data.actuator_force >= model.actuator_forcerange[:, 0] - 1e-8)
        assert np.all(data.actuator_force <= model.actuator_forcerange[:, 1] + 1e-8)


def check_gorilla_resource_contract(models, source_root=None):
    """Verify packaged runtime bytes; optionally bind them to checked-out design sources."""
    full = models / 'full'
    contract = json.loads((full / 'robot.json').read_text())
    assert contract['schema'] == 'gorilla_si_contract_v1'
    assert contract['robot_id'] == 'gorilla_v0_1'
    assert _sha256(full / 'robot.xml') == contract['model_sha256'], 'Model hash differs'
    xml = ET.parse(full / 'robot.xml').getroot()
    assert not xml.findall('.//include'), 'Runtime model must be self-contained'
    compiler = xml.find('compiler')
    mesh_directory = compiler.get('meshdir', '') if compiler is not None else ''
    meshes = xml.findall('asset/mesh')
    referenced_assets = {str(Path(mesh_directory) / mesh.attrib['file']) for mesh in meshes}
    assert referenced_assets == set(contract['asset_manifest']), 'Mesh manifest differs from XML references'
    used_meshes = {geom.attrib['mesh'] for geom in xml.findall('.//geom') if 'mesh' in geom.attrib}
    assert used_meshes == {mesh.attrib['name'] for mesh in meshes}, 'Unused mesh declarations are orphan assets'
    assert contract['asset_manifest'], 'Runtime asset manifest is empty'
    for relative, expected_hash in contract['asset_manifest'].items():
        asset = full / relative
        assert asset.resolve().is_relative_to(full.resolve()), 'Asset escapes model bundle'
        assert asset.is_file() and _sha256(asset) == expected_hash, f'Asset hash differs: {relative}'
    actual_assets = {str(path.relative_to(full)) for path in (full / 'assets').rglob('*') if path.is_file()}
    assert actual_assets == set(contract['asset_manifest']), 'Asset inventory differs from contract'
    if source_root is not None:
        robot = source_root / 'robots/gorilla_v0_1'
        specs = [path for path in (robot / 'configs').glob('*_spec.json')
                 if _sha256(path) == contract['spec_sha256']]
        assert len(specs) == 1, 'No unique source specification matches the contract hash'
        spec = json.loads(specs[0].read_text())
        assert spec['checkpoint_id'] == contract['checkpoint_id']
        assert spec['joints'] == contract['joints'], 'Source joint contract differs'
        assert spec['drive_classes'] == contract['drive_classes'], 'Source drive contract differs'
        assert spec['sensors'] == contract['sensors'], 'Source sensor contract differs'
        assert spec['timing'] == contract['timing'], 'Source timing contract differs'
        assert spec['coordinate_frame'] == contract['coordinates']
        assert spec['appearance_authority']['sha256'] == contract['appearance_image_sha256']
        components = {component['name']: component for body in contract['bodies'].values()
                      for component in body['components']}
        count = sum(len(body['components']) for body in contract['bodies'].values())
        assert len(components) == count, 'Duplicate mass component allocation'
        for expected in spec['mass_components']:
            actual = components[expected['name']]
            assert actual['body'] == expected['body']
            assert actual['mass_kg'] == expected['mass_kg']
            np.testing.assert_allclose(actual['position_world_m'], expected['position_world_m'], atol=1e-12)
        for joint in spec['joints']:
            drive = spec['drive_classes'][joint['drive_class']]
            for suffix, mass in drive['mass_components_kg'].items():
                actual = components[joint['name'] + '_' + suffix]
                assert actual['body'] == joint['child'] and actual['mass_kg'] == mass
                np.testing.assert_allclose(actual['position_world_m'], joint['position_world_m'], atol=1e-12)
        assert contract['generator_sha256'], 'Generator identity is missing'
        for relative, expected_hash in contract['generator_sha256'].items():
            generator = source_root / relative
            assert generator.resolve().is_relative_to(source_root.resolve())
            assert _sha256(generator) == expected_hash, f'Generator hash differs: {relative}'
        scenes = [path for path in (robot / 'cad/source').glob('*_scene.json')
                  if _sha256(path) == contract['scene_sha256']]
        assert len(scenes) == 1, 'No unique geometry source matches the contract hash'
        np.testing.assert_allclose(
            contract['body_origins_world_m'][spec['root_body']], spec['root_position_world_m'], atol=1e-12)
    model = mujoco.MjModel.from_xml_path(str(full / 'robot.xml'))
    _check_gorilla_model(contract, model)
    return contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    args = parser.parse_args()
    checkout = Path(__file__).resolve().parents[2]
    package = Path(sai_agent.__file__).resolve().parent
    root = resource_root()
    assert root == package / 'bundle', 'Run this with the installed wheel, not editable source'
    assert package != checkout / 'src/sai_agent'
    assert model_root() == model_root('Sai_Agent_001')

    config = tomllib.loads((checkout / 'pyproject.toml').read_text())
    includes = config['tool']['hatch']['build']['targets']['wheel']['force-include']
    tracked = subprocess.check_output(
        ['git', '-C', str(checkout), 'ls-files', '-z'], text=True,
    ).split('\0')
    expected = {}
    for source, target in includes.items():
        for path in tracked:
            if path == source or path.startswith(source + '/'):
                expected[target + path[len(source):]] = checkout / path
    assert expected, 'No tracked runtime resources found'
    expected_modules = {path.removeprefix('src/') for path in tracked
                        if path.startswith('src/sai_agent/') and path.endswith('.py')}
    with zipfile.ZipFile(args.wheel) as wheel:
        names = {name for name in wheel.namelist() if not name.endswith('/')}
        bundled = {name for name in names if name.startswith('sai_agent/bundle/')}
        assert bundled == set(expected), (
            f'Missing resources: {sorted(set(expected) - bundled)}; '
            f'Unexpected resources: {sorted(bundled - set(expected))}'
        )
        modules = {name for name in names if name.startswith('sai_agent/')
                   and not name.startswith('sai_agent/bundle/') and name.endswith('.py')}
        assert modules == expected_modules, 'Wheel Python module inventory differs from checkout'
        for name in names:
            if name in expected:
                source = expected[name]
            elif name.startswith('sai_agent/'):
                source = checkout / 'src' / name
            else:
                continue  # Wheel metadata is generated by the build backend.
            data = wheel.read(name)
            assert data == source.read_bytes(), f'Wheel differs from checkout: {name}'
            installed = package.parent / name
            assert installed.read_bytes() == data, f'Installed resource differs: {name}'
        print(f'Exact tracked resource inventory and hashes passed ({len(names)} wheel entries)')

    for robot_id, actuators in [('Sai_Agent_001', 23), ('Sai_Agent_002', 22)]:
        models = model_root(robot_id)
        for xml in ['full/robot.xml', 'full/visual.xml', 'locomotion.xml']:
            model = mujoco.MjModel.from_xml_path(str(models / xml))
            assert model.nu == (16 if xml == 'locomotion.xml' else actuators)
        assert GodotController(root, robot_id=robot_id).model.nu == actuators
        for name in ['ascent60', 'descent60']:
            profile = root / 'shared/policies/experimental' / f'{name}.json'
            metadata = json.loads(profile.read_text())
            actor = profile.parent / metadata['actor']
            assert hashlib.sha256(actor.read_bytes()).hexdigest() == metadata['onnx_sha256']
            GodotController(root, stair_profile=profile, robot_id=robot_id)
        CargoTask(model_dir=models / 'full')
        CargoGodotController(model_dir=models / 'full')
        print(f'{robot_id}: installed models, default/experimental policies and cargo passed')
    CrawlTransport()
    catalog = robot_catalog(root)
    gorilla = catalog['gorilla_v0_1']
    assert gorilla['godot_supported'] is False and gorilla['bevy_acceptance'] is False
    assert gorilla['policy_included'] is False
    policies = root / 'robots/gorilla_v0_1/policies'
    assert not policies.exists() or not any(path.is_file() for path in policies.rglob('*'))
    contract = check_gorilla_resource_contract(model_root('gorilla_v0_1', root), checkout)
    print(f"gorilla_v0_1: installed SI model and hashes passed ({len(contract['joint_order'])} candidate joints); "
          'no policy or game-controller acceptance')
    goose = model_root('Goose_V0.1')
    historical = mujoco.MjModel.from_xml_path(str(goose / 'full/robot.xml'))
    assert historical.nu == 16, 'Preserved RC2 actuator count changed'
    from sai_agent.goose.stage_one import StageOneEnv
    checkpoint = StageOneEnv(
        goose / 'training_checkpoint/robot.xml',
        root / 'robots/Goose_V0.1/configs/training_checkpoint_contract.json',
        num_envs=1, randomize=False, commands=False, auto_reset=False,
    )
    assert checkpoint.models[0].nu == 18
    assert checkpoint.observations().shape == (1, 65)
    print('Goose_V0.1: installed historical model and current 65/18 checkpoint passed (loading only)')
    print('Installed distribution checks passed')


if __name__ == '__main__':
    main()
