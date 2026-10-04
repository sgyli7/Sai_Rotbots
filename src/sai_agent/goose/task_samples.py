"""Versioned virtual task samples; never a source of robot hardware SI.

The body frame is the graspable crossbar centre. Composite primitive inertia
is a declared virtual mass distribution, not a measured manufactured object.
"""
from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def primitives(family: str, mass_kg: float):
    if family not in ('cylinder_weight', 'handle_weight') or mass_kg < .05:
        raise ValueError('Unknown sample family or insufficient declared mass')
    bar = {'role': 'grip', 'type': 'cylinder', 'size': [.006, .044 if family == 'cylinder_weight' else .030],
        'pos': [0., 0., 0.], 'quat': [2**-.5, 2**-.5, 0., 0.], 'mass_kg': .004}
    if family == 'cylinder_weight':
        parts = [bar] + [{'role': f'weight_{side}', 'type': 'cylinder',
            'size': [.040, .008], 'pos': [0., side*.050, 0.],
            'quat': bar['quat'], 'mass_kg': (mass_kg-.004)/2} for side in [-1, 1]]
    else:
        parts = [bar] + [{'role': f'post_{side}', 'type': 'cylinder',
            'size': [.003, .012], 'pos': [0., side*.025, -.016],
            'quat': [1., 0., 0., 0.], 'mass_kg': .002} for side in [-1, 1]]
        parts.append({'role': 'weight', 'type': 'box', 'size': [.020, .030, .015],
            'pos': [0., 0., -.036], 'quat': [1., 0., 0., 0.], 'mass_kg': mass_kg-.008})
    return parts


def rotation(quat):
    result = np.zeros(9)
    mujoco.mju_quat2Mat(result, np.asarray(quat, float))
    return result.reshape(3, 3)


def aggregate_si(parts):
    mass = sum(p['mass_kg'] for p in parts)
    com = sum(p['mass_kg'] * np.asarray(p['pos']) for p in parts) / mass
    inertia = np.zeros((3, 3))
    bounds = []
    for p in parts:
        weight = p['mass_kg']; size = np.asarray(p['size']); R = rotation(p['quat'])
        if p['type'] == 'cylinder':
            r, h = size
            diag = weight * np.array([(3*r*r+4*h*h)/12, (3*r*r+4*h*h)/12, r*r/2])
            axis = R[:, 2]
            extent = r*np.sqrt(np.maximum(0., 1-axis*axis)) + h*np.abs(axis)
        else:
            diag = weight/3 * np.array([size[1]**2+size[2]**2, size[0]**2+size[2]**2, size[0]**2+size[1]**2])
            extent = np.abs(R) @ size
        delta = np.asarray(p['pos']) - com
        inertia += R @ np.diag(diag) @ R.T + weight*(delta@delta*np.eye(3)-np.outer(delta, delta))
        bounds.extend([np.asarray(p['pos'])-extent, np.asarray(p['pos'])+extent])
    bounds = np.array(bounds)
    return {'mass_kg': mass, 'com_body_m': com.tolist(), 'inertia_at_com_body_kg_m2': inertia.tolist(),
        'bounds_body_m': [bounds.min(axis=0).tolist(), bounds.max(axis=0).tolist()]}


def sample_body(sample_id, family, mass_kg, friction=.65, position=None):
    parts = primitives(family, mass_kg); si = aggregate_si(parts)
    if position is None:
        position = [.30, 0., -si['bounds_body_m'][0][2]]
    body = ET.Element('body', name=sample_id, pos=' '.join(map(str, position)))
    ET.SubElement(body, 'freejoint', name=f'{sample_id}_free')
    I = np.asarray(si['inertia_at_com_body_kg_m2'])
    ET.SubElement(body, 'inertial', mass=str(si['mass_kg']), pos=' '.join(map(str, si['com_body_m'])),
        fullinertia=' '.join(map(str, [I[0,0], I[1,1], I[2,2], I[0,1], I[0,2], I[1,2]])))
    for p in parts:
        ET.SubElement(body, 'geom', name=f'{sample_id}_{p["role"]}', type=p['type'],
            size=' '.join(map(str, p['size'])), pos=' '.join(map(str, p['pos'])),
            quat=' '.join(map(str, p['quat'])), density='0', contype='1', conaffinity='3',
            priority='2', friction=f'{friction} .01 .002', condim='3',
            solref='.005 1', solimp='.95 .99 .001', margin='0',
            rgba='.95 .36 .08 1' if p['role']=='grip' else '.20 .48 .67 1')
    return body, parts, si


def isolated_jaw_fixture(source_path, sample_id, family, mass_kg, friction=.65):
    """Fixed-head fixture, explicit and separate from the full robot runtime."""
    source = ET.parse(source_path).getroot()
    tree = ET.Element('mujoco', model='goose_sample_isolated_jaw_bench_v1')
    tree.append(copy.deepcopy(source.find('compiler')))
    tree.append(copy.deepcopy(source.find('option')))
    asset = ET.SubElement(tree, 'asset')
    for element in source.findall('asset/mesh'):
        if element.get('name') not in ('head_upper_bill_envelope', 'lower_bill_envelope'):
            continue
        mesh = copy.deepcopy(element)
        mesh.set('file', str((source_path.parent / element.get('file')).resolve()))
        asset.append(mesh)
    world = ET.SubElement(tree, 'worldbody')
    head = copy.deepcopy(source.find('.//body[@name="head_roll"]'))
    head.set('pos', '.081 0 .5892'); head.remove(head.find('joint')); world.append(head)
    actuator = ET.SubElement(tree, 'actuator')
    actuator.append(copy.deepcopy(source.find('actuator/motor[@name="beak_hinge_motor"]')))
    tree.append(copy.deepcopy(source.find('equality')))
    contact = ET.SubElement(tree, 'contact')
    ET.SubElement(contact, 'exclude', body1='beak_coupler_link', body2='beak_hinge')
    body, parts, si = sample_body(sample_id, family, mass_kg, friction, [.220, 0., .5497])
    world.append(body)
    ET.SubElement(world, 'geom', name='floor', type='plane', size='2 2 .1',
        friction='.65 .01 .002', contype='1', conaffinity='3')
    return tree, parts, si
