"""MJCF serialization of a frozen SI table and explicit owned contact meshes."""
from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco


def vec(x):
    return ' '.join(format(float(v), '.17g') for v in x)


def write_model(contract, collisions, destination, *, cold_root_z_m=0., excludes=None, contact_pairs=None):
    r = ET.Element('mujoco', model=contract['release_id'])
    ET.SubElement(r, 'compiler', angle='radian', meshdir='.', balanceinertia='false', inertiafromgeom='false')
    opt = ET.SubElement(r, 'option', timestep=str(contract['physics_dt_s']), gravity='0 0 -9.81',
                        integrator='implicitfast', iterations='100', cone='elliptic', jacobian='dense')
    ET.SubElement(opt, 'flag', autoreset='disable')
    asset = ET.SubElement(r, 'asset')
    for g in collisions:
        ET.SubElement(asset, 'mesh', name=g['name'], file=g['asset'], maxhullvert='-1')
    world = ET.SubElement(r, 'worldbody')
    ET.SubElement(world, 'geom', name='ground', type='plane', size='2 2 .01', contype='1', conaffinity='2',
                  friction='.65 .01 .002', solref='.005 1', rgba='.9 .9 .9 1')
    specs = {j['name']: j for j in contract['joints'] + contract['passive_linkage_joints']}
    props = {b['name']: b for b in contract['bodies']}
    nodes = {}

    def add_body(name):
        if name in nodes:
            return nodes[name]
        b = props[name]
        if name == 'torso':
            node = ET.SubElement(world, 'body', name=name, pos=vec([0, 0, cold_root_z_m]))
            ET.SubElement(node, 'freejoint', name='root')
        else:
            j = specs[name]
            parent = add_body(j['parent'])
            delta = np.array(b['origin_world_zero_m']) - props[j['parent']]['origin_world_zero_m']
            node = ET.SubElement(parent, 'body', name=name, pos=vec(delta))
            ET.SubElement(node, 'joint', name=name, type='hinge', axis=vec(j['axis_parent']), range=vec(j['range_rad']),
                          limited='false' if j.get('physical_angular_stop') is False else 'true',
                          armature=str(j.get('armature_kg_m2', 0.)), frictionloss=str(j.get('frictionloss_nm', 0.)),
                          damping=str(j.get('damping_nm_s_rad', .01)))
        I = np.array(b['inertia_at_com_body_kg_m2'])
        principal, basis = np.linalg.eigh(I)
        if np.linalg.det(basis) < 0:
            basis[:, 0] *= -1
        q = np.empty(4)
        mujoco.mju_mat2Quat(q, basis.ravel())
        ET.SubElement(node, 'inertial', mass=str(b['mass_kg']), pos=vec(b['com_local_m']),
                      diaginertia=vec(principal), quat=vec(q))
        for g in collisions:
            if g['body'] != name:
                continue
            bits = g.get('native_collision_bits', {})
            rgba = '.95 .65 .05 1' if ('bill' in g['name'] or 'beak_hinge' in g['name']) else '.8 .79 .76 1'
            if 'sole' in g['name']:
                rgba = '.12 .14 .15 1'
            attrs = dict(name=g['name'], type='mesh', mesh=g['name'], density='0',
                         contype=str(bits.get('contype', 2)), conaffinity=str(bits.get('conaffinity', 3)),
                         condim=str(g.get('condim', 3)), friction=vec(g.get('friction', [.65, .01, .002])),
                         solref=vec(g.get('solref', [.005, 1.])), margin=str(g.get('margin', 0.)), rgba=rgba)
            if 'solimp' in g:
                attrs['solimp'] = vec(g['solimp'])
            ET.SubElement(node, 'geom', **attrs)
        nodes[name] = node
        return node

    for b in contract['bodies']:
        add_body(b['name'])
    exclusions = excludes if excludes is not None else [('beak_coupler_link', 'beak_hinge')]
    contact = ET.SubElement(r, 'contact')
    for a, b in exclusions:
        ET.SubElement(contact, 'exclude', body1=a, body2=b)
    for pair in contact_pairs or []:
        ET.SubElement(contact, 'pair', **{k: str(v) for k, v in pair.items()})
    eq = ET.SubElement(r, 'equality')
    delta = np.array(specs['beak_coupler_link']['pivot_world_at_zero_m']) - specs['beak_input_rotor']['pivot_world_at_zero_m']
    ET.SubElement(eq, 'connect', name='beak_distal_pin', body1='beak_hinge', body2='beak_coupler_link',
                  anchor=vec(delta), solref='.002 1', solimp='.9999 .9999 .0001')
    for j in contract['passive_linkage_joints']:
        if j['name'].endswith('yaw_input_rotor'):
            ET.SubElement(eq, 'joint', name=j['name']+'_belt_relation', joint1=j['name'], joint2=j['mimic_joint'],
                          polycoef='0 1 0 0 0', solref='.002 1', solimp='.9999 .9999 .0001')
    act = ET.SubElement(r, 'actuator')
    for j in contract['joints']:
        cap = j['continuous_design_limit_nm']
        ET.SubElement(act, 'motor', name=j['name']+'_motor', joint=j.get('actuation_joint', j['name']), gear='1',
                      ctrllimited='true', ctrlrange=vec([-cap, cap]), forcelimited='true', forcerange=vec([-cap, cap]))
    ET.indent(r)
    ET.ElementTree(r).write(Path(destination), encoding='utf-8', xml_declaration=True)
    return exclusions
