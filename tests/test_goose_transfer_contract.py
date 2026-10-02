"""The neutral transfer must remain usable by independently built adapters."""
import hashlib
import json

from sai_agent.paths import resource_root


def test_goose_neutral_transfer_covers_model_and_task_frames():
    robot = resource_root() / 'robots/Goose_V0.1'
    transfer = json.loads((robot / 'models/full/rigid_transfer.json').read_text())
    spec = json.loads((robot / 'configs/robot_spec.json').read_text())
    assert transfer['schema'] == 'sai_rigid_transfer_v1'
    assert transfer['units'] == spec['units']
    assert transfer['frame'] == 'x_forward_y_left_z_up'
    assert transfer['model_sha256'] == hashlib.sha256((robot / 'models/full/robot.xml').read_bytes()).hexdigest()
    assert transfer['source_spec_sha256'] == hashlib.sha256((robot / 'configs/robot_spec.json').read_bytes()).hexdigest()
    assert [j['name'] for j in transfer['joints'] if j['actuated']] == [j['name'] for j in spec['joints']]
    assert transfer['control']['control_dt_s'] == .02
    assert transfer['control']['torque_update_dt_s'] == .005
    assert transfer['control']['version'] == 'goose_rc2_v5'
    assert transfer['control']['torque_feedforward'] == 'neutral_rigid_gravity'
    assert transfer['control']['action_reference_pose'] == 'standing'
    assert transfer['control']['action_position_scale_rad'] == .30
    assert {'torso_imu', 'left_foot', 'right_foot', 'task_center', 'grasp_center'} <= {
        site['name'] for site in transfer['sites']}
    assert {camera['name'] for camera in transfer['cameras']} == {'head_camera'}
    assert {constraint['type'] for constraint in transfer['constraints']} == {'point_closure'}
    assert set(transfer['reference_poses']) == {'standing', 'ground_side_grasp'}
    stance = transfer['reference_poses']['standing']
    assert len(stance['root_position_m']) == 3
    assert len(stance['root_orientation_wxyz']) == 4
    assert set(stance['active_joint_positions_rad']) == set(transfer['control']['encoder_joint_names'])
    assert {body['name'] for body in stance['bodies']} == {body['name'] for body in transfer['bodies']}
    assert all(min(body['principal_inertia_kg_m2']) > 0 for body in transfer['bodies'])
    assert 'godot_adapter' not in transfer and 'future_adapters' not in transfer
    assert 'mass_unit_scale' not in transfer


def test_training_starts_from_shared_standing_reference():
    import numpy as np

    from sai_agent.goose.locomotion import LocomotionEnv

    robot = resource_root() / 'robots/Goose_V0.1'
    env = LocomotionEnv(1, model_path=robot / 'models/full/robot.xml')
    env.reset(0, command=np.zeros(3), randomize=False)
    d = env.data[0]
    assert np.allclose(d.qpos[:7], env.stance_root)
    assert np.allclose(d.qpos[env.mapping.qpos], env.stance)


def test_training_standing_survives_actual_five_millisecond_torque_cadence():
    import numpy as np

    from sai_agent.goose.locomotion import LocomotionEnv

    env = LocomotionEnv(1)
    env.reset(0, command=np.zeros(3), randomize=False)
    for _ in range(75):
        _, _, done, info = env.step(np.zeros((1, 10)))
        assert not done[0], info[0]


def test_training_and_backend_compute_same_si_torque_at_sensor_state():
    import mujoco
    import numpy as np
    from scipy.spatial.transform import Rotation

    from sai_agent.goose.control import JointMap, metadata
    from sai_agent.goose.protocol import SensorFrame
    from sai_agent.goose.rigid import RigidReference
    from sai_agent.goose.runtime import BackendController

    robot = resource_root() / 'robots/Goose_V0.1'
    transfer_path = robot / 'models/full/rigid_transfer.json'
    mapping = JointMap(mujoco.MjModel.from_xml_path(str(robot / 'models/full/robot.xml')))
    reference = RigidReference(transfer_path)
    controller = BackendController(transfer_path)
    stance = np.array([reference.transfer['reference_poses']['standing']['active_joint_positions_rad'][n]
                       for n in mapping.names])
    q = stance + np.linspace(-.006, .006, len(stance))
    dq = np.linspace(-.02, .02, len(stance))
    rotation = Rotation.from_euler('xyz', [.04, -.07, .16]).as_matrix()
    gravity_body = rotation.T @ np.array([0., 0., -1.])
    torque_training = mapping.torque(q, dq, stance, reference.gravity_torque(q, rotation))
    frame = SensorFrame.from_message({
        'contract': metadata()['version'], 'joint_names': mapping.names,
        'units': 'SI', 'sequence': 1, 'timestamp_s': .005,
        'positions_rad': q.tolist(), 'velocities_rad_s': dq.tolist(),
        'gyro_body_rad_s': [0., 0., 0.], 'gravity_body_unit': gravity_body.tolist(),
    })
    torque_backend = np.array(controller.tick(frame)['torque_Nm'])
    assert np.allclose(torque_training, torque_backend, atol=1e-5)


def test_neutral_gravity_torque_matches_independent_potential_difference():
    import numpy as np
    from scipy.spatial.transform import Rotation

    from sai_agent.goose.rigid import RigidReference

    reference = RigidReference()
    stance = reference.transfer['reference_poses']['standing']['active_joint_positions_rad']
    q = np.array([stance[name] for name in reference.names])
    rotation = Rotation.from_euler('xyz', [.08, -.12, .23]).as_matrix()
    for seed in range(3):
        perturbed = q + np.random.default_rng(seed).uniform(-.1, .1, q.shape)
        analytic = reference.gravity_torque(perturbed, rotation)
        numerical = reference.gravity_torque_finite_difference(perturbed, rotation)
        assert np.allclose(analytic, numerical, atol=1e-7)


def test_backend_rejects_old_policy_after_controller_cadence_fix(tmp_path):
    import pytest

    from sai_agent.goose.control import metadata
    from sai_agent.goose.runtime import BackendController

    transfer = resource_root() / 'robots/Goose_V0.1/models/full/rigid_transfer.json'
    old = metadata()
    old['version'] = 'goose_rc2_v4'
    meta_path = tmp_path / 'old_policy.json'
    policy_path = tmp_path / 'old_policy.onnx'
    meta_path.write_text(json.dumps(old))
    policy_path.write_bytes(b'old-policy-placeholder')
    with pytest.raises(ValueError, match='Policy contract mismatch: version'):
        BackendController(transfer, policy_path, meta_path, allow_experimental=True)
