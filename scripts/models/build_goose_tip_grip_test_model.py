"""Detached collision/physics model for the native tip-grip replacement kit.

Only the six declared replacement surfaces and their actual mass/full inertia
change. Current eighteen axes, limits, motors, passive linkage and sole pads
remain unchanged. This builds a rejection test, not a training release.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time
import xml.etree.ElementTree as ET

import coacd
import mujoco
import numpy as np
import trimesh

from sai_agent.goose.mass_properties import aggregate_rigid_components

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/models'))
from build_goose_mechanical_physics import inertia
from build_goose_mechanical_reference import PALETTE, vec


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'configs/mechanical_physics_contract.json',
             R/'models/mechanical_physics/robot.xml',
             R/'evidence/body_bay_mechanical_parameters.json',
             R/'cad/exports/tip_grip_candidate/manifest.json']
    base = json.loads(paths[0].read_text())
    ledger, kit = [json.loads(p.read_text()) for p in paths[2:]]
    for data in [base, kit]:
        for relative, expected in data['source_hashes'].items():
            if sha(ROOT/relative) != expected:
                raise ValueError(('stale input', relative))
    if sha(paths[1]) != base['model_sha256']:
        raise ValueError('base physics XML identity')
    for relative, expected in base['asset_sha256'].items():
        if sha(paths[1].parent/relative) != expected:
            raise ValueError(('stale inherited collision asset', relative))
    c = copy.deepcopy(base)
    replaced = set(kit['replaces_existing_parts'])
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
    for part in kit['parts']:
        item = next(i for i in c['items'] if i['name'] == part['name'])
        item.update(mass_kg=part['mass_kg'],
                    center_m=(np.array(part['center_of_mass_world_m'])+lift).tolist(),
                    inertia_at_com_kg_m2=part['inertia_at_com_world_kg_m2'],
                    basis='Detached native tip grip replacement; assumed material density')
    out = R/'models/tip_grip_physics'
    collisions = R/'models/tip_grip_collisions'
    (out/'collision_assets').mkdir(parents=True, exist_ok=True)
    (out/'assets').mkdir(exist_ok=True)
    collisions.mkdir(exist_ok=True)
    scene_source = R/'cad/source/mechanical_preview/scene.json'
    kit_scene_source = R/'cad/source/tip_grip_candidate/quad_scene.json'
    scene = json.loads(scene_source.read_text())
    kit_scene = {p['name']: p for p in json.loads(kit_scene_source.read_text())['parts']}
    if set(kit_scene) != replaced:
        raise ValueError('tip visual replacement coverage')
    for index, part in enumerate(scene['parts']):
        if part['name'] in replaced:
            scene['parts'][index] = kit_scene[part['name']]
    for visual in c['visual_sources']:
        if visual['name'] in replaced:
            part = next(p for p in kit['parts'] if p['name'] == visual['name'])
            record = kit_scene[visual['name']]
            npz = R/record['geometry_npz']
            if sha(npz) != record['source_sha256']:
                raise ValueError(('tip quad identity', visual['name']))
            with np.load(npz, allow_pickle=False) as mesh:
                vertices = len(mesh['vertices'])
                if mesh['faces'].shape[1] != 4:
                    raise ValueError('nonquad source')
                quads = len(mesh['faces'])
            if quads != part['quad_faces']:
                raise ValueError('quad count mismatch')
            visual.update(body=part['body'], material=record['material'], role=record['role'],
                          quad_faces=quads, vertices=vertices, geometry_npz=record['geometry_npz'],
                          source_sha256=record['source_sha256'])
    scene.update(status='DETACHED_TIP_GRIP_REJECTION_CANDIDATE',
                 nominal_conditional_mass_kg=base['nominal_robot_mass_kg']+kit['native_mass_kg']-kit['old_replaced_mass_kg'],
                 manufacturing_pass=False, final_appearance_pass=False,
                 source_hashes={str(p.relative_to(ROOT)): sha(p) for p in [scene_source, kit_scene_source, paths[3], Path(__file__)]},
                 scope='Same344part assembly with six detached native tip-grip replacements; not installed or manufacturing released')
    scene_file = R/'cad/source/tip_grip_candidate/assembly_scene.json'
    scene_file.write_text(json.dumps(scene, separators=(',', ':'))+'\n')
    paths.extend([scene_source, kit_scene_source, scene_file])
    tree = ET.parse(paths[1]).getroot()
    tree.set('model', 'goose_detached_tip_grip_rejection_candidate')
    assets = tree.find('asset')
    nodes = {b.get('name'): b for b in tree.find('worldbody').findall('.//body')}
    old_geometry = {g['name'] for g in base['collision_geometries'] if g['part'] in replaced}
    # Reference visuals batch multiple parts by rigid body/material. Removing
    # a part name cannot remove its old triangles from that merged display.
    # Rebuild complete affected groups so no old/new coincident skin remains.
    changed_groups = {(kit_scene[n]['body'], kit_scene[n]['material']) for n in replaced}
    old_visual_names = {g['name'] for g in base['visual_geometries']
                        if (g['body'], g['material']) in changed_groups}
    c['visual_geometries'] = [g for g in base['visual_geometries'] if g['name'] not in old_visual_names]
    removed_meshes = set()
    for node in nodes.values():
        for geom in list(node.findall('geom')):
            if geom.get('name') in old_geometry | old_visual_names:
                removed_meshes.add(geom.get('mesh'))
                node.remove(geom)
    for mesh in list(assets.findall('mesh')):
        if mesh.get('name') in removed_meshes:
            assets.remove(mesh)
        else:
            mesh.set('file', '../mechanical_physics/'+mesh.get('file'))
    for owner in ['head_roll', 'beak_hinge']:
        properties = aggregate_rigid_components([i for i in c['items'] if i['body'] == owner], pivots[owner])
        next(b for b in c['bodies'] if b['name'] == owner).update(properties)
        inertia(nodes[owner].find('inertial'), properties['mass_kg'], properties['com_local_m'],
                np.array(properties['inertia_at_com_body_kg_m2']))
    options = dict(threshold=.0005, preprocess_mode='off', resolution=1000,
                   mcts_nodes=10, mcts_iterations=30, mcts_max_depth=2,
                   merge=True, decimate=True, max_ch_vertex=64, seed=0, real_metric=True)
    coacd.set_log_level('warn')
    geometries = [g for g in c['collision_geometries'] if g['part'] not in replaced]
    parts = []
    files = {}
    for part in kit['parts']:
        name, owner = part['name'], part['body']
        info = part['files']['stl']
        source = R/info['path']
        if sha(source) != info['sha256']:
            raise ValueError(('native STL identity', name))
        mesh = trimesh.load(source, force='mesh', process=True)
        mesh.apply_scale(.001)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise ValueError(('invalid source', name))
        if abs(mesh.volume*1e9/part['volume_mm3']-1) >= .005:
            raise ValueError(('source volume mismatch', name))
        cache = collisions/(name+'.json')
        record = json.loads(cache.read_text()) if cache.exists() else None
        if not (record and record['source_sha256'] == info['sha256'] and record['options'] == options
                and all(sha(R/h['path']) == h['sha256'] for h in record['hulls'])):
            started = time.monotonic()
            values = [(mesh.vertices, mesh.faces)] if mesh.is_convex else coacd.run_coacd(coacd.Mesh(mesh.vertices, mesh.faces), **options)
            hulls, degenerates = [], []
            for k, (points, triangles) in enumerate(values):
                points = np.asarray(points, dtype=float)
                singular = np.linalg.svd(points-points.mean(axis=0), compute_uv=False)
                if singular[-1] <= 1e-12:
                    # CoACD sometimes emits an exactly coplanar boundary
                    # fragment. A zero-volume point set is not a physical
                    # convex solid. Preserve its points and mark the
                    # decomposition unqualified rather than invent thickness.
                    file = collisions/(name+f'_degenerate_{k:03d}.npz')
                    np.savez_compressed(file, vertices=points, faces=np.asarray(triangles))
                    degenerates.append(dict(path=str(file.relative_to(R)), sha256=sha(file),
                        singular_values_m=singular.tolist(), reason='Coplanar zero-volume CoACD point set; not a physical collision hull'))
                    continue
                hull = trimesh.Trimesh(points, triangles, process=True)
                rebuilt = False
                if not hull.is_watertight or not hull.is_winding_consistent or not hull.is_convex:
                    hull = trimesh.convex.convex_hull(np.asarray(points, dtype=float))
                    rebuilt = True
                if not hull.is_watertight or not hull.is_winding_consistent or hull.volume <= 0:
                    raise ValueError(('invalid hull', name, k))
                file = collisions/(name+f'_{k:03d}.obj')
                hull.export(file, include_normals=False)
                hulls.append(dict(path=str(file.relative_to(R)), sha256=sha(file),
                                  coacd_point_hull_rebuilt=rebuilt, volume_m3=float(hull.volume)))
            record = dict(name=name, body=owner, source_sha256=info['sha256'], options=options,
                          source_unit='mm', geometry_unit='m', source_volume_m3=float(mesh.volume),
                          hulls=hulls, zero_volume_decomposition_fragments=degenerates,
                          decomposition_quality_released=False, duration_s=time.monotonic()-started)
            cache.write_text(json.dumps(record, indent=2)+'\n')
        parts.append(record)
        for k, h in enumerate(record['hulls']):
            hull = trimesh.load(R/h['path'], force='mesh', process=False)
            hull.vertices += lift-pivots[owner]
            gname = name+f'_tip_collision_{k:03d}'
            file = out/'collision_assets'/(gname+'.obj')
            hull.export(file, include_normals=False)
            files[str(file.relative_to(out))] = sha(file)
            ET.SubElement(assets, 'mesh', name=gname, file='collision_assets/'+file.name, maxhullvert='64')
            ET.SubElement(nodes[owner], 'geom', name=gname, mesh=gname, type='mesh', density='0',
                          contype='2', conaffinity='3', group='3', rgba='.1 .2 .4 .2',
                          friction='.65 .01 .002', solref='.005 1', solimp='.95 .99 .001', margin='0')
            geometries.append(dict(name=gname, part=name, body=owner,
                                   asset=str(file.relative_to(out)), method='native_tip_stl_separate_metric_hulls'))
        print('TIP MODEL', name, 'hulls', len(record['hulls']), flush=True)
    owners = {p['name']: p['body'] for p in c['visual_sources']}
    groups = {key: [] for key in sorted(changed_groups)}
    visual_coverage = []
    for part in scene['parts']:
        owner = owners[part['name']]
        group = (owner, part['material'])
        if group not in changed_groups:
            continue
        if 'geometry_npz' in part:
            file = R/part['geometry_npz']
            if sha(file) != part['source_sha256']:
                raise ValueError(('affected visual source identity', part['name']))
            with np.load(file, allow_pickle=False) as q:
                vertices, faces = q['vertices'].copy(), q['faces'].copy()
        else:
            vertices, faces = np.array(part['vertices']), np.array(part['faces'])
        triangles = np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]])
        mesh = trimesh.Trimesh(vertices+lift-pivots[owner], triangles, process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise ValueError(('invalid affected display source', part['name']))
        groups[group].append((part['name'], mesh))
        visual_coverage.append(part['name'])
    number = 0
    for (owner, material), meshes in groups.items():
        batches, bucket, count = [], [], 0
        for part_name, mesh in meshes:
            if bucket and count+len(mesh.faces) > 500000:
                batches.append(bucket)
                bucket, count = [], 0
            bucket.append((part_name, mesh))
            count += len(mesh.faces)
        if bucket:
            batches.append(bucket)
        for bucket in batches:
            mesh = trimesh.util.concatenate([m for n, m in bucket])
            name = 'tip_group_visual_'+str(number)
            number += 1
            file = out/'assets'/(name+'.obj')
            mesh.export(file, include_normals=False)
            files[str(file.relative_to(out))] = sha(file)
            ET.SubElement(assets, 'mesh', name=name, file='assets/'+file.name, maxhullvert='32')
            ET.SubElement(nodes[owner], 'geom', name=name, mesh=name, type='mesh', density='0',
                          contype='0', conaffinity='0', group='1', rgba=vec(PALETTE[material]))
            c['visual_geometries'].append(dict(name=name, body=owner, material=material,
                vertices=len(mesh.vertices), triangles=len(mesh.faces), asset=str(file.relative_to(out)),
                part_names=[n for n, m in bucket], collision_enabled=False))
    mesh_assets = {m.get('name'): m.get('file') for m in assets.findall('mesh')}
    for record in c['visual_geometries']:
        record['asset'] = mesh_assets[record['name']]
    if not replaced <= set(visual_coverage) or old_visual_names & {g.get('name') for g in tree.findall('.//geom')}:
        raise ValueError('old merged visual removal or new source coverage failed')
    c.update(rebuilt_visual_part_names=visual_coverage, removed_old_merged_visual_names=sorted(old_visual_names),
             actual_candidate_visual_source_part_count=len(c['visual_sources']))
    file = out/'robot.xml'
    ET.indent(tree)
    file.write_text(ET.tostring(tree, encoding='unicode')+'\n')
    mass_delta = kit['native_mass_kg']-kit['old_replaced_mass_kg']
    c.update(schema='goose_detached_tip_grip_physics_v1', model_sha256=sha(file),
             status='DETACHED_TIP_GRIP_REJECTION_CANDIDATE', collision_geometries=geometries,
             nominal_robot_mass_kg=base['nominal_robot_mass_kg']+mass_delta,
             asset_sha256=files, installed=False, training_release=False, urdf_sha256=None,
             source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
             candidate_scene_sha256=sha(scene_file),
             front_contact_native_world_m=kit['front_contact_native_world_m'],
             replaced_native_parts=sorted(replaced), inherited_geometry_contract_sha256=sha(paths[0]))
    (R/'configs/tip_grip_physics_contract.json').write_text(json.dumps(c, indent=2)+'\n')
    (collisions/'manifest.json').write_text(json.dumps(dict(parts=parts, options=options,
        source_hashes=c['source_hashes'], approximate_convex_collision_release=False), indent=2)+'\n')
    model = mujoco.MjModel.from_xml_path(str(file))
    np.testing.assert_allclose(model.body_mass.sum(), c['nominal_robot_mass_kg'], rtol=0, atol=1e-12)
    assert (model.nq, model.nv, model.nu) == (39, 38, 18)
    print('TIP COMPILED', model.nq, model.nv, model.nu, 'mass', model.body_mass.sum(), flush=True)


if __name__ == '__main__':
    main()
