"""Export the current mechanical scene and SI ledger as an inertial/FK reference.

This deliberately has no collision or training release. Hollow skins and
perforated carriers cannot be converted to solid convex hulls without adding
false contacts. That remaining physics task is explicit, rather than inheriting
the old stage-two collision geometry after the joint layout changed.
"""
from pathlib import Path
import copy
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/models'))
from build_goose_stage_two import candidate
from sai_agent.goose.mass_properties import aggregate_rigid_components
from sai_agent.goose.native_linkage import split_linkage

OUT = ROBOT / 'models/mechanical_reference'
CONTRACT = ROBOT / 'configs/mechanical_reference_contract.json'
PALETTE = {
    'ivory': (.78, .78, .74, 1), 'orange': (.95, .19, .002, 1),
    'graphite': (.045, .055, .065, 1), 'rubber': (.025, .03, .035, 1),
    'seam': (.065, .068, .068, 1), 'titanium': (.45, .49, .51, 1),
    'glass': (.01, .025, .04, 1), 'lens': (.003, .009, .016, 1),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vec(value):
    return ' '.join(format(float(x), '.17g') for x in value)


def save_xml(root, path):
    ET.indent(root)
    path.write_text(ET.tostring(root, encoding='unicode') + '\n')


def source_inputs():
    paths = [ROBOT / 'configs/stage_two_contract.json',
             ROBOT / 'evidence/body_bay_mechanical_parameters.json',
             ROBOT / 'cad/source/mechanical_preview/scene.json']
    old, ledger, scene = [json.loads(p.read_text()) for p in paths]
    for data in (ledger, scene):
        for relative, expected in data['source_hashes'].items():
            path = ROOT / relative
            if sha(path) != expected:
                raise ValueError(f'stale body-bay input: {relative}')
    if scene['nominal_conditional_mass_kg'] != ledger['nominal_conditional_mass_kg']:
        raise ValueError('scene and ledger mass mismatch')
    if scene['assembly_translation_m'] != [0, 0, ledger['rigid_coordinate_lift_m']]:
        raise ValueError('physical foot datum mismatch')
    return old, ledger, scene, paths


def make_contract(old, ledger):
    contract = copy.deepcopy(old)
    for key in ('collision_geometries', 'collision_exclusions', 'asset_sha256', 'model_sha256'):
        contract.pop(key, None)
    contract.update(
        schema='goose_mechanical_reference_si_v1',
        status='INERTIAL_FK_VISUAL_REFERENCE_NOT_COLLISION_OR_TRAINING_RELEASE',
        root_origin_at_zero_m=ledger['pivots_world_at_zero_m']['torso'],
        nominal_robot_mass_kg=ledger['nominal_conditional_mass_kg'],
        hardware_freeze=False, manufacturing_pass=False, final_appearance_pass=False,
        training_release=False, physical_collision_model_complete=False,
        model_kind='inertial_kinematic_visual_reference',
        mujoco_inertia_encoding='principal values and wxyz quaternion from numpy.eigh of the full source tensor',
        parent_contract_sha256=sha(ROBOT / 'configs/stage_two_contract.json'),
        items=[copy.deepcopy(i) for i in ledger['items'] if i['name'] != 'specified_payload_50g'],
        contact_hulls_world_at_zero_m=ledger['contact_hulls'],
        source_hashes=dict(ledger['source_hashes']),
        compatibility={name: 'neutral SI data; backend dynamics acceptance pending'
                       for name in ('mujoco', 'godot_jolt', 'unity', 'bevy')},
        limitations=[
            'No collision geometry: this reference must not be used for walking or grasp/drag training.',
            'Actual native ankle/neck replacements are retained; head/button/shoe closures remain explicit candidates.',
            'Joint ranges are inherited candidate ranges; 17 of 25 extreme assembly samples still fail.',
            'Native jaw input rotor and coupler use passive mimic coordinates; backends must enforce the neutral linkage constraints.',
            'Rigid-body inertias do not model compliant soles, cables, backlash or structural flexibility.',
            'Power, output-bearing capacity, full load paths and final appearance remain unreleased.',
        ])
    for joint in contract['joints']:
        joint['pivot_world_at_zero_m'] = ledger['pivots_world_at_zero_m'][joint['name']]
        joint['limits_status'] = 'unreleased candidate ranges; full combined native sweep has not passed'
    by_body = {b['name']: b for b in ledger['bodies']}
    for body in contract['bodies']:
        name = body['name']
        body.update(copy.deepcopy(by_body[name]))
        items = [i for i in contract['items'] if i['body'] == name]
        expected = aggregate_rigid_components(items, ledger['pivots_world_at_zero_m'][name])
        for key in ('mass_kg', 'com_local_m', 'inertia_at_com_body_kg_m2'):
            np.testing.assert_allclose(body[key], expected[key], atol=1e-12, rtol=1e-12)
        body['mass_relative_design_uncertainty'] = sum(
            i['mass_kg'] * i['relative_uncertainty'] for i in items) / body['mass_kg']
    transmission = contract['beak_transmission']
    for name in ('drive_axis_world_m', 'jaw_axis_world_m'):
        transmission[name] = (np.array(transmission[name]) + [0, 0, ledger['rigid_coordinate_lift_m']]).tolist()
    split_linkage(contract, ledger)
    contract['sites'] = {
        'grip': {'body': 'head_roll', 'world_at_zero_m': ledger['grip_world_at_zero_m']},
        'beak_tip': {'body': 'head_roll', 'world_at_zero_m': ledger['tip_world_at_zero_m']},
    }
    return contract


def build():
    old, ledger, scene, paths = source_inputs()
    old_model = ROBOT / 'models/stage_two/robot.xml'
    old_model_hash = sha(old_model)
    contract = make_contract(old, ledger)
    pivots = {name: np.array(value) for name, value in ledger['pivots_world_at_zero_m'].items()}
    passive = contract.get('passive_linkage_joints', [])
    all_joints = contract['joints'] + passive
    pivots.update({j['name']: np.array(j['pivot_world_at_zero_m']) for j in passive})
    parents = {j['name']: j['parent'] for j in all_joints}
    old_system = candidate()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'assets').mkdir(exist_ok=True)

    mj = ET.Element('mujoco', model=contract['schema'])
    ET.SubElement(mj, 'compiler', angle='radian', inertiafromgeom='false', meshdir='assets')
    ET.SubElement(mj, 'option', timestep=str(contract['physics_dt_s']), gravity='0 0 -9.81', integrator='implicitfast')
    ET.SubElement(mj, 'custom').append(ET.Element('text', name='usage', data=contract['status']))
    assets = ET.SubElement(mj, 'asset')
    world = ET.SubElement(mj, 'worldbody')
    ET.SubElement(world, 'light', pos='0 -2 3', dir='0 0 -1')
    nodes = {}
    urdf = ET.Element('robot', name=contract['schema'])
    ET.SubElement(urdf, 'link', name='world')
    root = ET.SubElement(urdf, 'joint', name='root', type='floating')
    ET.SubElement(root, 'parent', link='world')
    ET.SubElement(root, 'child', link='torso')
    ET.SubElement(root, 'origin', xyz=vec(pivots['torso']), rpy='0 0 0')
    links = {}
    for body in contract['bodies']:
        name = body['name']
        parent = parents.get(name)
        offset = pivots[name] - (pivots[parent] if parent else 0)
        node = ET.SubElement(world if parent is None else nodes[parent], 'body', name=name, pos=vec(offset))
        nodes[name] = node
        tensor = np.array(body['inertia_at_com_body_kg_m2'])
        principal, orientation = np.linalg.eigh(tensor)
        if np.linalg.det(orientation) < 0:
            orientation[:, 0] *= -1
        quaternion_xyzw = Rotation.from_matrix(orientation).as_quat()
        quaternion_wxyz = np.r_[quaternion_xyzw[3], quaternion_xyzw[0:3]]
        ET.SubElement(node, 'inertial', mass=str(body['mass_kg']), pos=vec(body['com_local_m']),
                      diaginertia=vec(principal), quat=vec(quaternion_wxyz))
        if parent is None:
            ET.SubElement(node, 'freejoint', name='root')
        else:
            joint = next(j for j in all_joints if j['name'] == name)
            ET.SubElement(node, 'joint', name=name, type='hinge', axis=vec(joint['axis_parent']),
                          range=vec(joint['range_rad']), armature=str(joint.get('armature_kg_m2', 0)),
                          frictionloss=str(joint.get('frictionloss_nm', 0)), damping=str(joint.get('damping_nm_s_rad', .001)))
            u = ET.SubElement(urdf, 'joint', name=name, type='revolute')
            ET.SubElement(u, 'parent', link=parent)
            ET.SubElement(u, 'child', link=name)
            ET.SubElement(u, 'origin', xyz=vec(offset), rpy='0 0 0')
            ET.SubElement(u, 'axis', xyz=vec(joint['axis_parent']))
            ET.SubElement(u, 'limit', lower=str(joint['range_rad'][0]), upper=str(joint['range_rad'][1]),
                          effort=str(joint.get('torque_peak_limit_nm', 100)), velocity=str(joint.get('speed_limit_rad_s', 1)))
            ET.SubElement(u, 'dynamics', damping=str(joint.get('damping_nm_s_rad', .001)), friction=str(joint.get('frictionloss_nm', 0)))
            if 'mimic_joint' in joint:
                ET.SubElement(u, 'mimic', joint=joint['mimic_joint'], multiplier=str(joint['mimic_multiplier']), offset=str(joint['mimic_offset_rad']))
        link = ET.SubElement(urdf, 'link', name=name)
        links[name] = link
        inertia = ET.SubElement(link, 'inertial')
        ET.SubElement(inertia, 'origin', xyz=vec(body['com_local_m']), rpy='0 0 0')
        ET.SubElement(inertia, 'mass', value=str(body['mass_kg']))
        ET.SubElement(inertia, 'inertia', **{key: str(tensor[i, j]) for key, i, j in
                      [('ixx', 0, 0), ('iyy', 1, 1), ('izz', 2, 2), ('ixy', 0, 1), ('ixz', 0, 2), ('iyz', 1, 2)]})
    for name, site in contract['sites'].items():
        local = np.array(site['world_at_zero_m']) - pivots[site['body']]
        ET.SubElement(nodes[site['body']], 'site', name=name, pos=vec(local), size='.003')

    groups, visual_sources = {}, []
    ledger_owners = {item['name']: item['body'] for item in contract['items']}
    for part in scene['parts']:
        name = part['name']
        owner = part.get('body') or ledger_owners.get(name)
        if owner is None:
            owner = old_system.owner(name)
        if owner not in nodes:
            raise ValueError(f'unknown rigid owner: {name}: {owner}')
        if 'geometry_npz' in part:
            path = ROBOT / part['geometry_npz']
            if sha(path) != part['source_sha256']:
                raise ValueError(f'stale geometry: {name}')
            with np.load(path, allow_pickle=False) as data:
                vertices, faces = data['vertices'].copy(), data['faces'].copy()
            paths.append(path)
        else:
            vertices, faces = np.array(part['vertices']), np.array(part['faces'])
        if faces.ndim != 2 or faces.shape[1] != 4:
            raise ValueError(f'non-quad editable source: {name}')
        local = vertices + np.array(scene['assembly_translation_m']) - pivots[owner]
        triangles = np.concatenate((faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]))
        mesh = trimesh.Trimesh(local, triangles, process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise ValueError(f'invalid closed source: {name}')
        groups.setdefault((owner, part['material']), []).append(mesh)
        visual_sources.append(dict(name=name, body=owner, material=part['material'],
                                   role=part['role'], quad_faces=len(faces), vertices=len(vertices)))

    visual_geometries = []
    batches=[]
    for (body,material),meshes in groups.items():
        bucket=[];count=0
        for mesh in meshes:
            if bucket and count+len(mesh.faces)>500000:
                batches.append(((body,material),bucket));bucket=[];count=0
            bucket.append(mesh);count+=len(mesh.faces)
        if bucket:batches.append(((body,material),bucket))
    for number, ((body, material), meshes) in enumerate(batches):
        name = f'visual_{number:02d}'
        combined = trimesh.util.concatenate(meshes)
        path = OUT / 'assets' / (name + '.obj')
        combined.export(path, include_normals=True)
        ET.SubElement(assets, 'mesh', name=name, file=path.name, maxhullvert='32')
        ET.SubElement(nodes[body], 'geom', name=name, type='mesh', mesh=name,
                      rgba=vec(PALETTE[material]), contype='0', conaffinity='0', group='1')
        visual = ET.SubElement(links[body], 'visual', name=name)
        ET.SubElement(visual, 'origin', xyz='0 0 0', rpy='0 0 0')
        ET.SubElement(ET.SubElement(visual, 'geometry'), 'mesh', filename='assets/' + path.name)
        mat = ET.SubElement(visual, 'material', name=material)
        ET.SubElement(mat, 'color', rgba=vec(PALETTE[material]))
        visual_geometries.append(dict(name=name, body=body, material=material, vertices=len(combined.vertices),
                                      triangles=len(combined.faces), asset='assets/' + path.name, collision_enabled=False))
        print('VISUAL', name, body, material, 'triangles', len(combined.faces), flush=True)
    actuators = ET.SubElement(mj, 'actuator')
    for joint in contract['joints']:
        peak = joint['torque_peak_limit_nm']
        ET.SubElement(actuators, 'motor', name=joint['name'] + '_motor', joint=joint.get('actuation_joint', joint['name']), gear='1',
                      ctrllimited='true', ctrlrange=vec([-peak, peak]))
    if passive:
        equality = ET.SubElement(mj, 'equality')
        for joint in passive:
            ET.SubElement(equality, 'joint', name=joint['name']+'_mimic', joint1=joint['name'],
                          joint2=joint['mimic_joint'], polycoef=vec([joint['mimic_offset_rad'],joint['mimic_multiplier'],0,0,0]),
                          solref='.002 1', solimp='.999 .9999 .0001')
    save_xml(mj, OUT / 'robot.xml')
    save_xml(urdf, OUT / 'robot.urdf')
    contract.update(visual_sources=visual_sources, visual_geometries=visual_geometries,
                    collision_geometries=[], collision_exclusions=[],
                    model_sha256=sha(OUT / 'robot.xml'), urdf_sha256=sha(OUT / 'robot.urdf'),
                    asset_sha256={g['asset']: sha(OUT / g['asset']) for g in visual_geometries})
    contract['source_hashes'].update({str(p.relative_to(ROOT)): sha(p) for p in paths + [Path(__file__), ROOT/'src/sai_agent/goose/native_linkage.py']})
    CONTRACT.write_text(json.dumps(contract, indent=2) + '\n')
    for suffix in ('joints', 'bodies'):
        with (ROBOT / 'configs' / f'mechanical_reference_{suffix}.csv').open('w') as stream:
            rows = contract[suffix]
            writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for row in rows for k in row)), lineterminator='\n')
            writer.writeheader()
            writer.writerows({key: json.dumps(value, separators=(',', ':')) if isinstance(value, (dict, list)) else value
                              for key, value in row.items()} for row in rows)
    model = mujoco.MjModel.from_xml_path(str(OUT / 'robot.xml'))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    np.testing.assert_allclose(model.body_mass.sum(), contract['nominal_robot_mass_kg'], atol=1e-12)
    if model.nq != 25+len(passive) or model.nv != 24+len(passive) or model.nu != 18 or np.any(model.geom_contype) or np.any(model.geom_conaffinity):
        raise ValueError('reference-only model interface mismatch')
    if sha(old_model) != old_model_hash:
        raise ValueError('historical stage-two model changed')
    print(json.dumps(dict(mass_kg=model.body_mass.sum(), parts=len(visual_sources), nq=model.nq,
                          nv=model.nv, nu=model.nu, collision_model_complete=False, training_release=False), indent=2))


if __name__ == '__main__':
    build()
