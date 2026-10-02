"""Bounded jaw/object approach geometry before any pickup dynamics.

The50g,20x20x16mm specified block starts on the floor. A kinematic jaw sweep
checks which source surface reaches it first. This is not a pickup success.
"""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from build123d import import_brep

from sai_agent.goose.native_linkage import set_passive_linkage

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/models'), str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = R/'models/tip_grip_physics/robot.xml'
    paths = [source, R/'configs/tip_grip_physics_contract.json', R/'evidence/tip_grip_finite_reach.json',
             R/'evidence/body_bay_mechanical_parameters.json', R/'cad/exports/tip_grip_candidate/manifest.json']
    contract, reach, ledger, kit = [json.loads(p.read_text()) for p in paths[1:]]
    for data in [contract, reach]:
        for relative, expected in data['source_hashes'].items():
            if sha(ROOT/relative) != expected:
                raise ValueError(('stale input', relative))
    if not reach['selected_native_floor_pass']:
        raise ValueError('selected pose lacks native floor clearance')
    selected = reach['selected_candidate']
    point = np.array(selected['actual_front_contact_world_m'])
    size = np.array([.020, .020, .016])
    center = np.array([point[0]-.010, 0., .008])
    mass = .050
    tree = ET.parse(source).getroot()
    for mesh in tree.find('asset').findall('mesh'):
        mesh.set('file', str((source.parent/mesh.get('file')).resolve()))
    obj = ET.SubElement(tree.find('worldbody'), 'body', name='floor_50g_object', pos=' '.join(map(str, center)))
    ET.SubElement(obj, 'freejoint', name='object_root')
    diagonal = mass*(sum(size**2)-size**2)/12
    ET.SubElement(obj, 'inertial', mass=str(mass), pos='0 0 0', diaginertia=' '.join(map(str, diagonal)))
    ET.SubElement(obj, 'geom', name='floor_50g_object', type='box', size=' '.join(map(str, size/2)),
                  density='0', contype='2', conaffinity='3', friction='.65 .01 .002', solref='.005 1')
    xml = ET.tostring(tree, encoding='unicode')
    out = ROOT/'artifacts/Goose_V0.1/tip_grip_floor_object'
    out.mkdir(parents=True, exist_ok=True)
    (out/'task.xml').write_text(xml)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    order = contract['joint_order']
    qadr = [model.joint(n).qposadr[0] for n in order]
    lookup = {g['name']: g['part'] for g in contract['collision_geometries']}
    cases = []
    for angle in np.linspace(.30, 0., 13):
        mujoco.mj_resetData(model, data)
        data.qpos[:3] = selected['root_position_m']
        data.qpos[3:7] = [1, 0, 0, 0]
        data.qpos[qadr] = [selected['q_rad'][n] for n in order]
        data.qpos[model.joint('beak_hinge').qposadr[0]] = angle
        set_passive_linkage(model, data, contract)
        mujoco.mj_forward(model, data)
        contacts = []
        for cc in data.contact:
            a, b = [model.geom(int(g)).name for g in cc.geom]
            if 'floor_50g_object' not in (a, b) or cc.dist >= -.0002:
                continue
            other = b if a == 'floor_50g_object' else a
            if other == 'ground':
                continue
            contacts.append(dict(part=lookup.get(other, other), penetration_m=float(-cc.dist)))
        cases.append(dict(jaw_q_rad=float(angle), approximate_object_contacts=contacts))
        print('TIP OBJECT', round(float(angle), 3), sorted({c['part'] for c in contacts}), flush=True)
    first = next((c for c in cases if c['approximate_object_contacts']), None)
    native = []
    if first:
        system = candidate()
        system.pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
        lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
        q = dict(selected['q_rad'])
        q['beak_hinge'] = first['jaw_q_rad']
        fk, _ = system.fk(q, root_p=np.array(selected['root_position_m']))
        object_solid = box(size*1000, center*1000)
        for part in kit['parts']:
            if not part['name'].endswith(('_shell', '_cassette_pad')):
                continue
            info = part['files']['brep']
            file = R/info['path']
            if sha(file) != info['sha256']:
                raise ValueError(('native identity', part['name']))
            paths.append(file)
            shape = import_brep(file)
            owner = part['body']
            position, rotation = fk[owner]
            moved = transform(shape, rotation, (position+rotation@(lift-system.pivots[owner]))*1000)
            result = bounded_common(moved, object_solid, 3.)
            native.append(dict(part=part['name'], native_common=result,
                               intrusion_confirmed='error' not in result and result['volume_mm3'] > .01))
    report = dict(schema='goose_tip_grip_floor_object_geometry_v1', selected_reach_index=selected['index'],
                  object_center_world_m=center.tolist(), object_size_m=size.tolist(), object_mass_kg=mass,
                  object_equivalent_density_kg_m3=mass/float(np.prod(size)),
                  object_basis='Specified rigid test block; approximately50g steel-sized sample, not arbitrary daily item.',
                  kinematic_cases=cases, first_penetrating_contact=first, native_first_contact=native,
                  native_nonpad_first_intrusion_confirmed=any(c['intrusion_confirmed'] and c['part'].endswith('_shell') for c in native),
                  native_pad_first_intrusion_confirmed=any(c['intrusion_confirmed'] and c['part'].endswith('_cassette_pad') for c in native),
                  unresolved_native_queries=sum('error' in c['native_common'] for c in native),
                  jaw_sweep_is_kinematic=True, dynamic_floor_pickup_pass=False, object_pose_fixed_during_screen=True,
                  installed=False, training_release=False, manufacturing_release=False,
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
                  task_xml_sha256=hashlib.sha256(xml.encode()).hexdigest(),
                  limitations=['Thirteen static jaw poses and selected first intrusion only; not continuous collision certification.',
                    'Object begins on the floor at the declared front/top tangent placement; no visual approach tested.',
                    'Convex penetration requires native confirmation; force, grip, lift and balance are not inferred.'])
    (R/'evidence/tip_grip_floor_object_geometry.json').write_text(json.dumps(report, indent=2)+'\n')
    print('TIP OBJECT NATIVE', native, flush=True)


if __name__ == '__main__':
    main()
