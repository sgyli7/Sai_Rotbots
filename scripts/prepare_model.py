"""Derive a traceable locomotion model from the existing articulated r24 model.

Arm and cargo joints are fixed at their recorded zero pose for locomotion
training. Their masses and inertias are retained. The full articulated model
must be used again for the final transfer and manipulation acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    tree = ET.parse(source / 'train.xml')
    root = tree.getroot()
    original = mujoco.MjModel.from_xml_path(str(source / 'train.xml'))
    data = mujoco.MjData(original)
    mujoco.mj_forward(original, data)
    spec = json.loads((source / 'robot.json').read_text())
    names = [leg + '_' + joint for leg in spec['leg_order'] for joint in ['haa', 'hip', 'knee', 'wheel']]
    world = root.find('worldbody')
    for child in list(world):
        if child.tag == 'body' and child.get('name') == 'item':
            world.remove(child)
        elif child.tag == 'geom' and child.get('name', '').startswith('course_'):
            world.remove(child)
    removed = []
    for body in root.findall('.//body'):
        for j in list(body.findall('joint')):
            if j.get('name') not in names:
                removed.append(j.get('name'))
                body.remove(j)
    actuator = root.find('actuator')
    for a in list(actuator):
        if a.get('joint') not in names:
            actuator.remove(a)
    if root.find('equality') is not None:
        root.remove(root.find('equality'))
    if root.find('keyframe') is not None:
        root.remove(root.find('keyframe'))
    # Preserve source primitive contacts, replace each body's convex mesh
    # contacts with one conservative AABB in that body's coordinate system.
    # These proxies are explicit approximations, not source CAD redistribution.
    approximations = []
    for body in root.findall('.//body'):
        mesh_geoms = [g for g in body.findall('geom') if g.get('type') == 'mesh' or g.get('mesh')]
        if not mesh_geoms:
            continue
        bid = original.body(body.get('name')).id
        points = []
        for g in mesh_geoms:
            gid = original.geom(g.get('name')).id
            mid = original.geom_dataid[gid]
            start, count = original.mesh_vertadr[mid], original.mesh_vertnum[mid]
            vertex = original.mesh_vert[start:start + count].astype(float)
            vertex = vertex @ data.geom_xmat[gid].reshape(3, 3).T + data.geom_xpos[gid]
            vertex = (vertex - data.xpos[bid]) @ data.xmat[bid].reshape(3, 3)
            points.append(vertex)
            body.remove(g)
        xyz = np.concatenate(points)
        low, high = xyz.min(0), xyz.max(0)
        ET.SubElement(body, 'geom', name=body.get('name') + '_locomotion_envelope', type='box',
                      pos=' '.join(map(str, (low + high) / 2)),
                      size=' '.join(map(str, np.maximum((high - low) / 2, .001))),
                      rgba='.16 .24 .42 1')
        approximations.append({'body': body.get('name'), 'source_contacts': len(mesh_geoms),
                               'aabb_body_m': [low.tolist(), high.tolist()]})
    asset = root.find('asset')
    if asset is not None:
        for child in list(asset):
            if child.tag == 'mesh':
                asset.remove(child)
    root.find('compiler').set('fusestatic', 'true')
    option = root.find('option')
    option.set('timestep', '.002')
    option.set('iterations', '20')
    option.set('ls_iterations', '8')
    option.set('cone', 'pyramidal')
    root.set('model', 'Sai_Agent_001_locomotion')
    ET.indent(tree)
    output = destination / 'locomotion.xml'
    tree.write(output, encoding='unicode')
    model = mujoco.MjModel.from_xml_path(str(output))
    robot_mass = float(original.body_mass.sum() - original.body_mass[original.body('item').id])
    assert np.isclose(model.body_mass.sum(), robot_mass, atol=1e-8)
    assert model.nu == 16 and model.nq == 23 and model.nv == 22
    manifest = dict(robot_id='Sai_Agent_001', schema_version=1,
        source_CAD_sha256=spec['CAD_STEP_sha256'], source_model_sha256=digest(source / 'train.xml'),
        model_sha256=digest(output), source_total_robot_mass_kg=robot_mass,
        model_total_mass_kg=float(model.body_mass.sum()), fixed_joints=removed,
        locomotion_joint_order=names, joint_qpos_addresses=[int(model.joint(n).qposadr[0]) for n in names],
        joint_dof_addresses=[int(model.joint(n).dofadr[0]) for n in names],
        units=dict(length='m', angle='rad', mass='kg', time='s', quaternion='wxyz'),
        coordinates='right-handed source robot: +X forward, +Y left, +Z up',
        collision_approximations=approximations,
        limitations=['Arm/cargo fixed at zero pose for locomotion training; validate full articulation separately',
                     'Source robot self collision is disabled',
                     '2 ms implicitfast/pyramidal training solver differs from 1 ms elliptic source',
                     'Uncalibrated mass/inertia/servo/friction estimates remain',
                     'Body-frame AABBs replace convex meshes for GPU training; not manufacturing geometry'])
    (destination / 'robot_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k:v for k,v in manifest.items() if k != 'collision_approximations'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[1] / 'models')
    args = parser.parse_args()
    prepare(args.source, args.destination)
