"""Build an exploratory SI model from the unscaled-hardware, original-proportion layout.

Thin armor skins are integrated as surfaces. Frame and drive placements remain
estimated envelopes. This is an editable demand model, not a manufacturing CAD.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/gorilla_v0_1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numbers(values):
    return ' '.join(f'{float(x):.12g}' for x in values)


def inertia6(matrix):
    return matrix[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]].tolist()


def rotation_axis(axis):
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    reference = np.eye(3)[np.argmin(np.abs(axis))]
    u = np.cross(reference, axis)
    u /= np.linalg.norm(u)
    return np.column_stack([u, np.cross(axis, u), axis])


def surface_properties(vertices, faces, density, thickness):
    """Exact triangle surface mass, centroid, and inertia (quad diagonal is explicit)."""
    vertices = np.asarray(vertices, dtype=float)
    if (not np.isfinite(vertices).all() or not np.isfinite([density,thickness]).all() or
            density < 0 or thickness < 0):
        raise ValueError('Surface coordinates and physical skin parameters must be finite and nonnegative')
    area, first, second = 0., np.zeros(3), np.zeros((3, 3))
    for face in faces:
        for k in range(1, len(face) - 1):
            triangle = vertices[[face[0], face[k], face[k + 1]]]
            weight = .5 * np.linalg.norm(np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0]))
            summed = triangle.sum(axis=0)
            area += weight
            first += weight * summed / 3
            second += weight * (np.outer(summed, summed) + triangle.T @ triangle) / 12
    if area <= 0:
        raise ValueError('Armor mesh has zero surface area')
    com = first / area
    mass = area * density * thickness
    centered = second * density * thickness - mass * np.outer(com, com)
    inertia = np.trace(centered) * np.eye(3) - centered
    return mass, com, inertia, area


def component_inertia(component):
    mass = component['mass_kg']
    if not np.isfinite(mass) or mass <= 0:
        raise ValueError('Explicit physical component mass must be finite and positive')
    if component['shape'] == 'box':
        a, b, c = component['size_m']
        return np.diag([b*b+c*c, a*a+c*c, a*a+b*b]) * mass / 12
    r, length = component['radius_m'], component['length_m']
    local = np.diag([mass*(3*r*r+length*length)/12]*2 + [mass*r*r/2])
    rotation = rotation_axis(component['axis_world'])
    return rotation @ local @ rotation.T


def aggregate(components, origin):
    mass = sum(c['mass_kg'] for c in components)
    com = sum((c['mass_kg'] * np.array(c['position_world_m']) for c in components), np.zeros(3)) / mass
    inertia = np.zeros((3, 3))
    for c in components:
        offset = np.asarray(c['position_world_m']) - com
        inertia += np.asarray(c['inertia_world_kg_m2']) + c['mass_kg'] * (
            np.dot(offset, offset) * np.eye(3) - np.outer(offset, offset))
    eigen = np.linalg.eigvalsh(inertia)
    if eigen[0] <= 0 or eigen[-1] > eigen[:2].sum() + 1e-8:
        raise ValueError(f'Invalid physical inertia: {eigen}')
    return {'mass_kg': mass, 'com_local_m': (com-origin).tolist(),
            'com_world_neutral_m': com.tolist(), 'inertia_body_frame_kg_m2': inertia.tolist(),
            'fullinertia_kg_m2': inertia6(inertia), 'principal_inertia_kg_m2': eigen.tolist(),
            'components': components}


def build(spec_path, scene_path, out):
    spec = json.loads(spec_path.read_text())
    scene = json.loads(scene_path.read_text())
    if scene['spec_sha256'] != sha(spec_path):
        raise ValueError('Geometry was generated from a different specification')
    if scene['checkpoint_id'] != spec['checkpoint_id']:
        raise ValueError('Geometry and physics checkpoint identities differ')
    if scene['image_sha256'] != spec['appearance_authority']['sha256']:
        raise ValueError('Geometry uses a different appearance authority')
    joints = spec['joints']
    if any(j['qpos_neutral_rad'] != 0 for j in joints):
        raise ValueError('This reconstruction requires zero hinge coordinates in the bent neutral geometry')
    origins = {spec['root_body']: np.asarray(spec['root_position_world_m'])}
    origins.update({j['child']: np.asarray(j['position_world_m']) for j in joints})
    components = {name: [] for name in origins}
    for c in spec['mass_components']:
        component = {'name': c['name'], 'body': c['body'], 'shape': 'box',
                     'mass_kg': c['mass_kg'], 'position_world_m': c['position_world_m'],
                     'size_m': c['box_size_m'], 'basis': 'estimated component/frame allocation; not solid material volume',
                     'uncertainty_fraction': .3}
        component['inertia_world_kg_m2'] = component_inertia(component).tolist()
        components[c['body']].append(component)
    for j in joints:
        drive = spec['drive_classes'][j['drive_class']]
        diameter, _, length = drive['complete_module_envelope_m']
        for name, mass in drive['mass_components_kg'].items():
            component = {'name': j['name']+'_'+name, 'body': j['child'], 'shape': 'cylinder',
                'mass_kg': mass, 'position_world_m': j['position_world_m'],
                'axis_world': j['axis_parent'], 'radius_m': diameter/2, 'length_m': length,
                'basis': 'complete-module cylinder proxy; all drive mass lumped to child; internal allocation unresolved',
                'uncertainty_fraction': drive['mass_uncertainty_fraction']}
            component['inertia_world_kg_m2'] = component_inertia(component).tolist()
            components[j['child']].append(component)
    armor_properties = {}
    for part in scene['parts']:
        if part['body'] not in origins or part['role'] not in ('armor','decoration'):
            raise ValueError('Geometry mass role or body allocation is unsupported')
        if part['role'] == 'decoration' and part.get('shell_thickness_m', 0) != 0:
            raise ValueError('Decorative drive/frame representations cannot be counted as a second armor skin')
        edges = {}
        for face in part['faces']:
            for a,b in zip(face,face[1:]+face[:1]):
                edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
        if any(count != 2 for count in edges.values()):
            raise ValueError(f"Part {part['name']} is not an edge-closed surface")
        density = part.get('shell_density_kg_m3', spec['shell_estimation']['density_kg_m3'])
        thickness = part.get('shell_thickness_m', 0 if part['role']=='decoration' else spec['shell_estimation']['thickness_m'])
        mass, com, inertia, area = surface_properties(part['vertices_world_m'], part['faces'], density, thickness)
        armor_properties[part['name']] = {'area_m2': area, 'mass_kg': mass,
            'method': 'triangle surface integration; closed armor skin thickness; not filled mesh volume'}
        if mass > 0:
            components[part['body']].append({'name': part['name'], 'body': part['body'],
                'shape': 'surface_skin', 'mass_kg': mass, 'position_world_m': com.tolist(),
                'inertia_world_kg_m2': inertia.tolist(), 'area_m2': area,
                'thickness_m': thickness, 'density_kg_m3': density,
                'uncertainty_fraction': spec['shell_estimation']['uncertainty_fraction'],
                'basis': 'independent thin surface approximation; no strength or fabrication proof'})
    bodies = {name: aggregate(parts, origins[name]) for name, parts in components.items()}
    out.mkdir(parents=True, exist_ok=True)
    (out/'assets').mkdir(exist_ok=True)
    expected_asset_names = {f"{part['name']}.obj" for part in scene['parts']}
    for stale in (out/'assets').glob('*.obj'):
        if stale.name not in expected_asset_names:
            if not stale.read_text().startswith('# Independent Gorilla armor; SI body-local vertices\n'):
                raise ValueError(f'Refusing to remove an unrecognized asset: {stale}')
            stale.unlink()
    mj = ET.Element('mujoco', model=spec['checkpoint_id'])
    ET.SubElement(mj, 'compiler', angle='radian', autolimits='true', inertiafromgeom='false', meshdir='assets')
    ET.SubElement(mj, 'option', timestep='.002', gravity='0 0 -9.81', integrator='implicitfast',
                  iterations='100', tolerance='1e-10')
    default = ET.SubElement(mj, 'default')
    ET.SubElement(default, 'joint', limited='true', damping='2', armature='0')
    ET.SubElement(default, 'geom', friction='.7 .005 .0001', condim='3', solref='.02 1', solimp='.9 .95 .001')
    asset = ET.SubElement(mj, 'asset')
    world = ET.SubElement(mj, 'worldbody')
    ET.SubElement(world, 'geom', name='ground', type='plane', size='8 8 .1', rgba='.86 .86 .86 1')
    elements = {}
    root = ET.SubElement(world, 'body', name=spec['root_body'], pos=numbers(origins[spec['root_body']]))
    ET.SubElement(root, 'freejoint', name='floating_root')
    elements[spec['root_body']] = root
    # Topological order is independent of policy joint-order indexing.
    pending = list(joints)
    while pending:
        ready = [j for j in pending if j['parent'] in elements]
        if not ready:
            raise ValueError('Joint parent graph is not a rooted tree')
        for j in ready:
            body = ET.SubElement(elements[j['parent']], 'body', name=j['child'],
                pos=numbers(origins[j['child']]-origins[j['parent']]))
            ET.SubElement(body, 'joint', name=j['name'], type='hinge', axis=numbers(j['axis_parent']),
                          range=numbers(j['range_rad']))
            elements[j['child']] = body
            pending.remove(j)
    for name, properties in bodies.items():
        ET.SubElement(elements[name], 'inertial', pos=numbers(properties['com_local_m']),
                      mass=f"{properties['mass_kg']:.12g}", fullinertia=numbers(properties['fullinertia_kg_m2']))
    for part in scene['parts']:
        origin = origins[part['body']]
        obj_path = out/'assets'/f"{part['name']}.obj"
        lines = ['# Independent Gorilla armor; SI body-local vertices']
        lines.extend('v '+numbers(np.asarray(v)-origin) for v in part['vertices_world_m'])
        lines.extend('f '+' '.join(str(i+1) for i in face) for face in part['faces'])
        obj_path.write_text('\n'.join(lines)+'\n')
        ET.SubElement(asset, 'mesh', name=part['name'], file=obj_path.name)
        hand = any(part['body'].startswith(s+'_'+kind) for s in ('left','right')
                   for kind in ('palm','finger_','thumb_'))
        ET.SubElement(elements[part['body']], 'geom', name=part['name']+('_contact_mesh' if hand else '_visual'), type='mesh',
            mesh=part['name'], rgba=numbers(part['rgba']), contype='1' if hand else '0',
            conaffinity='1' if hand else '0', group='2')
    collision_sources = []
    def box(body, name, position, size):
        ET.SubElement(elements[body], 'geom', name=name, type='box',
            pos=numbers(np.asarray(position)-origins[body]), size=numbers(np.asarray(size)/2), group='3', rgba='.3 .3 .3 .2')
        collision_sources.append({'body': body, 'name': name, 'type': 'box', 'position_world_m': position, 'size_m': size})
    def capsule(body, name, start, end, radius):
        ET.SubElement(elements[body], 'geom', name=name, type='capsule',
            fromto=numbers(np.r_[np.asarray(start)-origins[body], np.asarray(end)-origins[body]]),
            size=str(radius), group='3', rgba='.3 .3 .3 .2')
        collision_sources.append({'body':body,'name':name,'type':'capsule','from_world_m':start,'to_world_m':end,'radius_m':radius})
    points = spec['points_world_m']
    box('torso','torso_core_contact',[-.08,0,2.25],[.66,.82,.63])
    # Central keel proxy leaves the actual hip and thumb openings unfilled.
    box('pelvis','pelvis_contact',[0,0,1.60],[.36,.30,.23])
    for side, sign in (('left',1),('right',-1)):
        def p(kind):
            point = np.asarray(points['left_'+kind]).copy();point[1]*=sign;return point
        for body, start, end, radius in (
            ('upper_arm','shoulder','elbow',.115),
            ('thigh','hip','knee',.14), ('middle_shank','knee','fold',.125),
            ('distal_shank','fold','ankle',.085)):
            a,b=p(start),p(end)
            # Leave real joint openings; this proxy does not cover omitted armor.
            capsule(side+'_'+body,side+'_'+body+'_contact',(a+.20*(b-a)).tolist(),(a+.80*(b-a)).tolist(),radius)
        forearm_center=.5*(p('elbow')+p('wrist'))
        ET.SubElement(elements[side+'_forearm'],'geom',name=side+'_forearm_contact',type='ellipsoid',
            pos=numbers(forearm_center-origins[side+'_forearm']),size='.18 .16 .26',group='3',rgba='.3 .3 .3 .2')
        collision_sources.append({'body':side+'_forearm','name':side+'_forearm_contact','type':'ellipsoid',
            'position_world_m':forearm_center.tolist(),'semiaxes_m':[.18,.16,.26]})
        foot=p('foot');size=np.array(spec['appearance_dimensions']['foot_size_m'])
        foot[2]=.03
        box(side+'_foot',side+'_sole_contact',foot.tolist(),[size[0],size[1],.06])
        for part in scene['parts']:
            if part['body'].startswith((side+'_palm',side+'_finger_',side+'_thumb_')):
                collision_sources.append({'body':part['body'],'name':part['name']+'_contact_mesh',
                    'type':'convex_mesh','asset':f"assets/{part['name']}.obj",
                    'scope':'same-source hand exterior, convex approximation per independently closed part'})
    for sensor in spec['sensors']:
        body=elements[sensor['body']]
        ET.SubElement(body, 'site', name=sensor['name']+'_mount', pos=numbers(
            np.asarray(sensor['position_world_m'])-origins[sensor['body']]), size='.008', rgba='1 .2 .1 1')
    actuator = ET.SubElement(mj, 'actuator')
    for j in joints:
        limit=spec['drive_classes'][j['drive_class']]['design_torque_nm']
        kp={'large':2500,'medium':1500,'small':500,'finger':80}[j['drive_class']]
        ET.SubElement(actuator,'position',name=j['name']+'_drive',joint=j['name'],kp=str(kp),
            ctrllimited='true',ctrlrange=numbers(j['range_rad']),forcelimited='true',forcerange=numbers([-limit,limit]))
    ET.indent(mj)
    xml_path=out/'robot.xml';ET.ElementTree(mj).write(xml_path,encoding='unicode')
    model=mujoco.MjModel.from_xml_path(str(xml_path));data=mujoco.MjData(model);mujoco.mj_forward(model,data)
    # Read back full compiled body-frame inertia, rather than trusting the export.
    max_error=0.
    for name, properties in bodies.items():
        bid=model.body(name).id;rotation=np.zeros(9);mujoco.mju_quat2Mat(rotation,model.body_iquat[bid])
        rotation=rotation.reshape(3,3)
        actual=rotation @ np.diag(model.body_inertia[bid]) @ rotation.T
        max_error=max(max_error,float(np.max(np.abs(actual-np.array(properties['inertia_body_frame_kg_m2'])))))
        if not np.allclose(model.body_mass[bid],properties['mass_kg'],rtol=1e-9):raise ValueError('Compiled mass mismatch')
        if not np.allclose(model.body_ipos[bid],properties['com_local_m'],atol=1e-8):raise ValueError('Compiled COM mismatch')
        tensor_scale=float(np.linalg.norm(properties['inertia_body_frame_kg_m2'],ord=2))
        if np.max(np.abs(actual-np.asarray(properties['inertia_body_frame_kg_m2']))) > 1e-9 + 2e-6*tensor_scale:
            raise ValueError(f'Compiled full inertia mismatch for {name}: expected={properties["inertia_body_frame_kg_m2"]}, actual={actual.tolist()}')
    total=sum(b['mass_kg'] for b in bodies.values())
    assets_manifest={str(p.relative_to(out)):sha(p) for p in sorted(out/'assets'/n for n in expected_asset_names)}
    generators={str(p.relative_to(ROOT)):sha(p) for p in (
        Path(__file__),ROOT/'scripts/models/build_gorilla_proportion_layout.py')}
    physical={'schema':'gorilla_si_contract_v1','robot_id':'gorilla_v0_1','checkpoint_id':spec['checkpoint_id'],
        'spec_sha256':sha(spec_path),'scene_sha256':sha(scene_path),'model_sha256':sha(xml_path),
        'appearance_image_sha256':spec['appearance_authority']['sha256'],
        'asset_manifest':assets_manifest,'generator_sha256':generators,
        'maturity':'exploratory_layout; not stable control or manufacturing baseline',
        'coordinates':spec['coordinate_frame'],'gravity_m_s2':[0,0,-9.81],
        'total_robot_mass_kg':total,'body_count':len(bodies),'active_joint_count':model.nu,'free_root_dof':6,
        'joint_order':[j['name'] for j in joints],'joints':joints,'bodies':bodies,'body_origins_world_m':{n:o.tolist() for n,o in origins.items()},
        'drive_classes':spec['drive_classes'],'collisions':collision_sources,'sensors':spec['sensors'],'timing':spec['timing'],
        'control_contract':{'actions':'named output-joint position targets in radians, native force-clamped position hold only',
            'qpos_addresses':{j['name']:int(model.jnt_qposadr[model.joint(j['name']).id]) for j in joints},
            'dof_addresses':{j['name']:int(model.jnt_dofadr[model.joint(j['name']).id]) for j in joints},
            'learning_observation_contract':None,'learning_policy':None,'latency_and_bevy_adapter_verified':False},
        'collision_scope':'Same-source convex compound hand contacts and sparse body primitive rejection proxies. Other armor/internal modules not cleared. Central keel preserves hip gap. No welded payload/root support.',
        'mass_allocation_scope':'Complete estimated drive mass including stator and rotor attached to child cylinder; parent/child mass split, rotor reflection and internal part motion unresolved RED gate; stable handoff blocked.',
        'armor_properties':armor_properties,'compiled_full_inertia_max_error_kg_m2':max_error,
        'compiled_inertia_readback_tolerance':'1e-9 kg*m2 + 2e-6 * tensor spectral norm; MuJoCo eigen/quaternion precision',
        'physical_hard_freeze':False,'bevy_acceptance':False,'hardware_validation':False}
    (out/'robot.json').write_text(json.dumps(physical,indent=2,ensure_ascii=False)+'\n')
    ledger=ROBOT/'hardware/layout_b_mass_components.csv'
    with ledger.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['body','name','mass_kg','shape','position_world_m','basis','uncertainty_fraction'])
        writer.writeheader()
        for parts in components.values():
            for c in parts:writer.writerow({k:json.dumps(c[k]) if k=='position_world_m' else c.get(k,'') for k in writer.fieldnames})
    evidence={'schema':'gorilla_layout_build_v1','checkpoint_id':spec['checkpoint_id'],
        'spec_sha256':sha(spec_path),'scene_sha256':sha(scene_path),'model_sha256':sha(xml_path),
        'asset_manifest':assets_manifest,'generator_sha256':generators,'contract_sha256':sha(out/'robot.json'),
        'model_load':True,'inertia_readback':True,'compiled_inertia_error_max_kg_m2':max_error,
        'mass_kg':total,'active_joints':model.nu,'free_root_dof':6,
        'mass_breakdown_kg':{'drive_modules':sum(sum(d['mass_components_kg'].values()) for j in joints for d in [spec['drive_classes'][j['drive_class']]]),
            'frames_electrical_reserves':sum(c['mass_kg'] for c in spec['mass_components']),
            'armor':sum(p['mass_kg'] for p in armor_properties.values())},
        'module_packaging':'not checked; coincident gimbal envelopes overlap; RED OPEN',
        'closed_surface_edges_verified':True,'actual_internal_assembly_verified':False,
        'drive_parent_child_mass_split_verified':False,'rotor_reflected_inertia_verified':False,
        'geometry_fidelity':'requires same-model four-view visual review, cannot be inferred from model load',
        'manufacturing_release':False,'physical_hard_freeze':False}
    (ROBOT/'evidence/layout_b_build.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'out':str(out),'mass_kg':total,'active_joints':model.nu,'inertia_max_error':max_error}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,default=ROBOT/'configs/layout_b_spec.json')
    p.add_argument('--scene',type=Path,default=ROBOT/'cad/source/layout_b_scene.json')
    p.add_argument('--out',type=Path,default=ROBOT/'models/full')
    a=p.parse_args();build(a.spec,a.scene,a.out)


if __name__=='__main__':main()
