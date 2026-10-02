"""Cross-check serialized MJCF/URDF against the current body-bay SI ledger.

Forward kinematics and inertia are checked. These checks do not certify
collision-free movement, walking, object manipulation or hardware release.
"""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
MODEL = ROBOT / 'models/body_bay_reference'
CONTRACT = ROBOT / 'configs/body_bay_reference_contract.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def floats(value):
    return np.array([float(x) for x in value.split()])


def validate():
    contract = json.loads(CONTRACT.read_text())
    ledger_path = ROBOT / 'evidence/body_bay_component_parameters.json'
    ledger = json.loads(ledger_path.read_text())
    for relative, expected in contract['source_hashes'].items():
        if sha(ROOT / relative) != expected:
            raise ValueError(f'stale source: {relative}')
    for relative, expected in contract['asset_sha256'].items():
        if sha(MODEL / relative) != expected:
            raise ValueError(f'stale model asset: {relative}')
    if sha(MODEL / 'robot.xml') != contract['model_sha256'] or sha(MODEL / 'robot.urdf') != contract['urdf_sha256']:
        raise ValueError('serialized model hash mismatch')
    model = mujoco.MjModel.from_xml_path(str(MODEL / 'robot.xml'))
    data = mujoco.MjData(model)
    urdf = ET.parse(MODEL / 'robot.urdf')
    mjcf = ET.parse(MODEL / 'robot.xml')
    names = contract['joint_order']
    urdf_joints = {j.attrib['name']: j for j in urdf.findall('./joint')}
    urdf_links = {b.attrib['name']: b for b in urdf.findall('./link')}
    if model.nq != 25 or model.nv != 24 or model.nu != 18:
        raise ValueError('18-axis floating-root interface mismatch')
    if [model.joint(k + 1).name for k in range(18)] != names:
        raise ValueError('serialized joint order mismatch')
    if np.any(model.geom_contype) or np.any(model.geom_conaffinity) or urdf.findall('.//collision'):
        raise ValueError('inertial/FK reference unexpectedly acquired collisions')
    if contract['training_release'] or contract['physical_collision_model_complete']:
        raise ValueError('reference-only release boundary changed')
    if any(i['name'] == 'specified_payload_50g' for i in contract['items']):
        raise ValueError('test object included in bare robot mass')
    np.testing.assert_allclose(model.body_mass.sum(), ledger['nominal_conditional_mass_kg'], atol=1e-12)

    mass_errors, com_errors, tensor_errors = [], [], []
    for body in ledger['bodies']:
        name = body['name']
        b = model.body(name).id
        expected = np.array(body['inertia_at_com_body_kg_m2'])
        quaternion = model.body_iquat[b]
        rotation = Rotation.from_quat(np.r_[quaternion[1:], quaternion[0]]).as_matrix()
        tensor = rotation @ np.diag(model.body_inertia[b]) @ rotation.T
        u = urdf_links[name].find('inertial')
        iu = u.find('inertia').attrib
        urdf_tensor = np.array([[float(iu['ixx']), float(iu['ixy']), float(iu['ixz'])],
                                [float(iu['ixy']), float(iu['iyy']), float(iu['iyz'])],
                                [float(iu['ixz']), float(iu['iyz']), float(iu['izz'])]])
        mass_errors.extend([abs(model.body_mass[b] - body['mass_kg']), abs(float(u.find('mass').attrib['value']) - body['mass_kg'])])
        com_errors.extend([np.max(abs(model.body_ipos[b] - body['com_local_m'])),
                           np.max(abs(floats(u.find('origin').attrib['xyz']) - body['com_local_m']))])
        tensor_errors.extend([np.max(abs(tensor - expected)), np.max(abs(urdf_tensor - expected))])
    np.testing.assert_allclose(mass_errors, 0, atol=1e-12)
    np.testing.assert_allclose(com_errors, 0, atol=1e-12)
    np.testing.assert_allclose(tensor_errors, 0, atol=1e-12)

    rng = np.random.default_rng(90330)
    poses = [(r['name'], np.array([r['joint_q_rad'].get(name, 0) for name in names]),
              np.zeros(3), np.eye(3)) for r in ledger['results'] if r['mass_variant'] == 0 and r['drag_x_n'] == 0]
    for _ in range(32):
        q = np.array([rng.uniform(*j['range_rad']) for j in contract['joints']])
        poses.append(('arbitrary_fk', q, rng.uniform(-.2, .2, 3), Rotation.random(random_state=rng).as_matrix()))
    position_errors, rotation_errors = [], []
    for label, q, root_offset, root_rotation in poses:
        data.qpos[:3] = np.array(contract['root_origin_at_zero_m']) + root_offset
        quaternion = Rotation.from_matrix(root_rotation).as_quat()
        data.qpos[3:7] = np.r_[quaternion[3], quaternion[:3]]
        data.qpos[7:] = q
        mujoco.mj_forward(model, data)
        # Independent FK uses the serialized URDF origins and axes, rather
        # than reading local frames back out of the compiled MuJoCo model.
        p = {'torso': floats(urdf_joints['root'].find('origin').attrib['xyz']) + root_offset}
        r = {'torso': root_rotation}
        for k, name in enumerate(names):
            joint = urdf_joints[name]
            parent = joint.find('parent').attrib['link']
            xyz = floats(joint.find('origin').attrib['xyz'])
            zero_rotation = Rotation.from_euler('xyz', floats(joint.find('origin').attrib['rpy'])).as_matrix()
            p[name] = p[parent] + r[parent] @ xyz
            r[name] = r[parent] @ zero_rotation @ Rotation.from_rotvec(floats(joint.find('axis').attrib['xyz']) * q[k]).as_matrix()
        for name in ['torso'] + names:
            b = model.body(name).id
            position_errors.append(float(np.max(abs(data.xpos[b] - p[name]))))
            rotation_errors.append(float(np.max(abs(data.xmat[b].reshape(3, 3) - r[name]))))
        for name, site in contract['sites'].items():
            body = site['body']
            local = np.array(site['world_at_zero_m']) - np.array(ledger['pivots_world_at_zero_m'][body])
            position_errors.append(float(np.max(abs(data.site_xpos[model.site(name).id] - (p[body] + r[body] @ local)))))
    np.testing.assert_allclose(position_errors, 0, atol=1e-12)
    np.testing.assert_allclose(rotation_errors, 0, atol=1e-12)

    # Runtime triangulation never modifies the editable quad/CAD source.
    if len(contract['visual_sources']) != 262 or sum(x['quad_faces'] for x in contract['visual_sources']) != 1302588:
        raise ValueError('native preview component coverage changed')
    if len(urdf.findall('.//visual')) != len(contract['visual_geometries']):
        raise ValueError('URDF visual coverage mismatch')
    for geom in contract['visual_geometries']:
        if mjcf.find(f"./worldbody//body[@name='{geom['body']}']/geom[@name='{geom['name']}']") is None:
            raise ValueError(f'visual attached to wrong rigid body: {geom["name"]}')
    report = dict(schema='goose_body_bay_reference_validation_v1',
        status='SI_INERTIA_FK_EXPORT_PASS_NOT_PHYSICS_RELEASE',
        bare_robot_mass_kg=float(model.body_mass.sum()), rigid_bodies=19, active_axes=18,
        visual_source_parts=262, visual_quad_source_faces=1302588,
        serialized_visual_groups=len(contract['visual_geometries']), forward_kinematics_cases=len(poses),
        maximum_position_error_m=max(position_errors), maximum_rotation_matrix_error=max(rotation_errors),
        maximum_body_mass_error_kg=max(mass_errors), maximum_com_error_m=max(com_errors),
        maximum_inertia_tensor_error_kg_m2=max(tensor_errors),
        source_and_asset_hashes_pass=True, payload_excluded_from_robot_mass=True,
        physical_collision_model_complete=False, training_release=False, hardware_freeze=False,
        stage_three_complete=False, stage_four_complete=False, final_appearance_pass=False,
        source_hashes={str(path.relative_to(ROOT)): sha(path) for path in
                      [CONTRACT, ledger_path, MODEL / 'robot.xml', MODEL / 'robot.urdf', Path(__file__)]},
        limitations=contract['limitations'])
    output = ROBOT / 'evidence/body_bay_reference_validation.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['status', 'bare_robot_mass_kg', 'rigid_bodies', 'active_axes',
                     'forward_kinematics_cases', 'maximum_position_error_m', 'maximum_inertia_tensor_error_kg_m2',
                     'training_release']}, indent=2))
    return report


if __name__ == '__main__':
    validate()
