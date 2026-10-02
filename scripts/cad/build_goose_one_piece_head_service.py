"""Replace three head skins with one actual native hollow print candidate.

The existing rear and chin access cuts are retained. This is a native union,
not joined Blender objects or a display-only seam patch. Assembly path and
full-motion/strength qualification remain independent gates.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from build123d import Axis, Edge, Wire, Solid, PrecisionMode, import_brep, import_step, export_brep, export_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad')]
from build_goose_cad import box, cylinder, holes, transform
from build_goose_manufacturing_skins import head_grid
from goose_candidate_export import CandidateExport
from goose_nurbs_skin import native_properties
from build_goose_actuator_interfaces import quad_sampling
from sai_agent.goose.mass_properties import aggregate_rigid_components


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit_integral_shell(export, shape):
    """Preserve double-precision native tessellation through STL exchange.

    OCCT can output a triangle with exactly zero area at a periodic boundary.
    Removing only that empty facet creates no missing volume or replacement
    surface. No nonzero facet, hole filling or vertex displacement is allowed.
    """
    name = 'head_integral_print_shell'
    volume, center, inertia, _ = native_properties(shape)
    verts, faces = shape.tessellate(.025, .08)
    mesh = trimesh.Trimesh(np.array([tuple(v) for v in verts]), faces, process=True)
    keep = mesh.area_faces > 0.
    empty = int(np.count_nonzero(~keep))
    mesh.update_faces(keep)
    mesh.remove_unreferenced_vertices()
    if not mesh.is_watertight or not mesh.is_winding_consistent or abs(mesh.volume/volume-1) > .005:
        raise ValueError('Integral native tessellation is not a closed boundary')
    paths = dict(brep=export.source/(name+'.brep'), step=export.out/(name+'.step'),
                 stl=export.out/(name+'.stl'), npz=export.source/(name+'_quad.npz'))
    export_brep(shape,paths['brep']); export_step(shape,paths['step'],precision_mode=PrecisionMode.GREATEST)
    rt = import_step(paths['step']); rv, *_ = native_properties(rt)
    if not rt.is_valid or len(rt.solids()) != 1 or abs(rv/volume-1) > 1e-5:
        raise ValueError('Integral STEP round-trip failed')
    paths['stl'].write_text(trimesh.exchange.stl.export_stl_ascii(mesh))
    back = trimesh.load(paths['stl'],force='mesh',process=True)
    if not back.is_watertight or not back.is_winding_consistent or abs(back.volume/volume-1) > .005:
        raise ValueError('Integral full-precision STL round-trip failed')
    qv,qf = quad_sampling(mesh)
    np.savez_compressed(paths['npz'],vertices=qv,faces=qf)
    files = {key:dict(path=str(path.relative_to(R)),sha256=sha(path)) for key,path in paths.items()}
    export.parts.append(dict(name=name,body='head_roll',unit='mm',density_kg_m3=1270.,
        mass_kg=volume*1270e-9,volume_mm3=volume,center_of_mass_world_m=(center/1000).tolist(),
        inertia_at_com_world_kg_m2=(inertia*1270e-15).tolist(),files=files,quad_faces=len(qf),
        native_valid=True,native_solid_count=1,stl_watertight=True,manufacturing_released=False,
        exchange_validation=dict(step_volume_relative_error=abs(rv/volume-1),
            stl_volume_relative_error=abs(back.volume/volume-1),native_tolerance_mm=.025,
            native_angular_tolerance_rad=.08,zero_area_native_facets_removed=empty,
            nonzero_facets_removed=0,holes_filled=0,vertices_displaced=0,stl_encoding='ASCII full double precision',step_precision_mode='GREATEST_native_declared_tolerances'),
        notes=['One continuous native hollow PETG solid; enlarged underside access100..210mmX, rear opening and shaft/tool ports.',
            'Camera plane, land, face fasteners and OEM driver access unchanged.',
            'Closed CAD-derived quad sampling is not a subdivision artist control cage; BREP remains editable engineering source.',
            'Rear edge deburring/finish, printing supports, installation paths and local strength remain qualification gates.']))
    export.scene.append(dict(name=name,body='head_roll',group='head',material='ivory',
        role='native_integral_print_candidate_not_released',geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))
    print('INTEGRAL EXPORT',len(qf),'quads, removed',empty,'exactly empty facets',flush=True)


def main():
    cfg_path = R / 'configs/one_piece_head_service.json'
    cfg = json.loads(cfg_path.read_text())
    scene_path, parameters_path = [R / cfg[k] for k in ['source_scene', 'source_parameters']]
    if sha(scene_path) != cfg['source_scene_sha256']:
        raise ValueError('Frozen462 source changed')
    scene, old = [json.loads(p.read_text()) for p in [scene_path, parameters_path]]
    old_manifest_path = R / 'cad/exports/camera_head_closure/manifest.json'
    old_manifest = json.loads(old_manifest_path.read_text())
    catalog_path = R / 'evidence/camera_catalog_layout.json'
    catalog = json.loads(catalog_path.read_text())['selected']
    grid_path = R / 'cad/source/stage_two_architecture/scene.json'
    inputs = [cfg_path, scene_path, parameters_path, old_manifest_path, catalog_path,
              grid_path, Path(__file__), ROOT / 'scripts/cad/goose_candidate_export.py',
              ROOT / 'scripts/cad/goose_nurbs_skin.py', ROOT / 'scripts/cad/build_goose_cad.py',
              ROOT / 'scripts/cad/build_goose_manufacturing_skins.py',
              ROOT / 'src/sai_agent/goose/mass_properties.py']
    old_parts = {}
    for part in old_manifest['parts']:
        if part['name'] in cfg['replaced_parts']:
            path = R / part['files']['brep']['path']
            if sha(path) != part['files']['brep']['sha256']:
                raise ValueError('Head input changed')
            old_parts[part['name']] = import_brep(path)
            inputs.append(path)
    optical = np.array(catalog['optical_front_native_world_mm'])
    rotation = Rotation.from_euler('y', catalog['optical_pitch_down_in_head_deg'], degrees=True).as_matrix()
    from goose_serviceable_head_skin import build_continuous_head
    construction_path = R / 'cad/source/one_piece_head_service/construction_surface_grids.npz'
    camera_source = ROOT / 'artifacts/Goose_V0.1/camera_vendor_docs/b0471.step'
    catalog_data = json.loads(catalog_path.read_text())
    if sha(camera_source) != catalog_data['vendor_files']['step']['sha256']:
        raise ValueError('Changed original camera source')
    clearance_evidence = R / 'evidence/one_piece_head_service_internal_reliefs.json'
    shell = build_continuous_head(json.loads(grid_path.read_text()), optical, rotation, construction_path, cfg,
        camera_source, np.array(catalog['vendor_to_native_rotation']), np.array(catalog['vendor_to_native_translation_mm']), clearance_evidence)
    inputs += [camera_source, clearance_evidence] + sorted(construction_path.parent.glob('camera_relief_source_shell_*.brep'))
    inputs += [construction_path, ROOT / 'scripts/cad/goose_serviceable_head_skin.py',
               ROOT / 'scripts/cad/build_goose_head_linkage_skins.py', ROOT / 'scripts/cad/build_goose_jaw_retention.py']
    if not shell.is_valid or len(shell.solids()) != 1:
        raise ValueError(('Integral native shell failure', shell.is_valid, len(shell.solids())))
    export = CandidateExport(R, 'one_piece_head_service')
    name = 'head_integral_print_shell'
    emit_integral_shell(export,shell)
    old_items = {p['name']: copy.deepcopy(p) for p in old['items']}
    removed_mass = sum(old_items.pop(n)['mass_kg'] for n in cfg['replaced_parts'])
    native = export.parts[0]
    lift = old['rigid_coordinate_lift_m']
    old_items[name] = dict(name=name, body='head_roll', mass_kg=native['mass_kg'],
        center_m=(np.array(native['center_of_mass_world_m']) + [0., 0., lift]).tolist(),
        inertia_at_com_kg_m2=native['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
        basis='Single native PETG solid, full density; print and material unqualified')
    items = list(old_items.values())
    mass = sum(p['mass_kg'] for p in items)
    export.save(ROOT, inputs, replaces=cfg['replaced_parts'], extra=dict(
        source_scene_sha256=sha(scene_path), native_single_print_solid=True,
        replaced_native_mass_kg=removed_mass, net_physical_mass_change_kg=mass-old['nominal_conditional_mass_kg'],
        original_optical_plane_unchanged=True, installation_path_verified=False, continuous_main_to_nose_surface=True,
        rear_service_opening_x_mm=cfg['rear_service_opening_x_mm'],
        closed_main_front_seam=True, full_assembly_pass=False, manufacturing_release=False))
    kit_path = R / 'cad/exports/one_piece_head_service/manifest.json'
    parameters = dict(schema='goose_one_piece_head_service_parameters_v1', parts=460, active_axes=18,
        nominal_conditional_mass_kg=mass, delta_from462_kg=mass-old['nominal_conditional_mass_kg'], items=items,
        bodies=[dict(name=b['name'], **aggregate_rigid_components(
            [p for p in items if p['body']==b['name']], old['pivots_world_at_zero_m'][b['name']])) for b in old['bodies']],
        pivots_world_at_zero_m=old['pivots_world_at_zero_m'], rigid_coordinate_lift_m=lift,
        neutral_joint_order=old['neutral_joint_order'], full_assembly_pass=False,
        manufacturing_release=False, training_release=False, final_appearance_pass=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs+[kit_path]})
    parameter_out = R / 'evidence/one_piece_head_service_parameters.json'
    parameter_out.write_text(json.dumps(parameters, indent=2)+'\n')
    parts = [copy.deepcopy(p) for p in scene['parts'] if p['name'] not in cfg['replaced_parts']] + export.scene
    if len(parts) != 460:
        raise ValueError('Incorrect three-to-one replacement scope')
    folder = R / 'cad/source/one_piece_head_service_fixture'
    folder.mkdir(exist_ok=True)
    result = dict(unit='m', parts=parts, assembly_translation_m=scene['assembly_translation_m'],
        nominal_conditional_mass_kg=mass, status='INTEGRAL_HEAD_PRINT_CANDIDATE_NOT_RELEASED',
        manufacturing_pass=False, final_appearance_pass=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [parameter_out, kit_path]},
        review_views=scene.get('review_views',{}), review_ortho_scale_m=scene.get('review_ortho_scale_m',{}))
    (folder/'assembly_scene.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('INTEGRAL HEAD', len(parts), 'objects', mass, 'kg, delta', parameters['delta_from462_kg'], flush=True)


if __name__ == '__main__':
    main()
