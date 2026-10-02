"""Separate native lower-hip arch candidate; preserve accepted outer source.

The arch opens downward and removes skin only outside +/-50mm lateral spine.
This is a visible manufacturing candidate, not approved final appearance.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import trimesh
from build123d import Ellipse, extrude, import_step, export_step, export_brep
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh

ROOT = Path(__file__).resolve().parents[2]; R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import transform
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wide', action='store_true', help='Second and last bounded arch comparison; first failed candidate stays intact')
    args = parser.parse_args()
    original = R/'cad/exports/manufacturing_skins/manifest.json'
    manifest = json.loads(original.read_text())
    folder = 'hip_clearance_skins_wide' if args.wide else 'hip_clearance_skins'
    source = R/'cad/source'/folder; dest = R/'cad/exports'/folder
    source.mkdir(exist_ok=True); dest.mkdir(exist_ok=True)
    radius_x = 105 if args.wide else 95
    local = extrude(Ellipse(radius_x, 80), amount=160)
    rotation = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])
    right = transform(local, rotation, [-15., -50., 210.])
    left = transform(local, rotation.T, [-15., 50., 210.])
    # R^T above maps localY to -Z. Ellipse symmetry preserves the same arch.
    records = []; scene = []
    for p in manifest['parts']:
        if p['name'].startswith('goose_head_shell'):
            continue
        name = p['name']; shape = import_step(R/p['files']['step']['path']).solids()[0]
        port = right if name.endswith('right') or '_right_' in name else left
        shape = (shape-port).solids()
        if len(shape) != 1 or not shape[0].is_valid:
            raise ValueError((name, 'native clearance arch disconnected/invalid', len(shape)))
        shape = shape[0]; volume, com, inertia, integration = native_properties(shape)
        paths = {'brep':source/(name+'.brep'), 'step':dest/(name+'.step'),
                 'stl':dest/(name+'.stl'), 'npz':source/(name+'_quad.npz')}
        export_brep(shape, paths['brep']); export_step(shape, paths['step'])
        exchange = import_step(paths['step']); exchange_volume, *_ = native_properties(exchange)
        if not exchange.is_valid or len(exchange.solids()) != 1 or abs(exchange_volume/volume-1) > 1e-5:
            raise ValueError((name, 'STEP native exchange failed'))
        # A relative deflection and binary32 STL collapsed tiny native
        # triangles in the first attempt. Use explicit ABSOLUTE mm meshing,
        # then preserve OCCT doubles in ASCII STL. No patching, triangle
        # removal, normal flipping or manufactured geometry repair.
        BRepTools.Clean_s(shape.wrapped)
        mesher = BRepMesh_IncrementalMesh(shape.wrapped, .12, False, .25, False)
        mesher.Perform()
        if not mesher.IsDone():
            raise ValueError((name, 'native tessellation incomplete'))
        points, triangles = shape.tessellate(.12, .25)
        native_mesh = trimesh.Trimesh(np.array([tuple(v) for v in points]), np.array(triangles), process=True)
        paths['stl'].write_text(trimesh.exchange.stl.export_stl_ascii(native_mesh))
        mesh = trimesh.load(paths['stl'], force='mesh', process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0 or abs(mesh.volume/volume-1) > .005:
            raise ValueError((name, 'native STL gate failed; preserve native geometry, do not fill mesh holes'))
        vertices, faces = quad_sampling(mesh)
        np.savez_compressed(paths['npz'], vertices=vertices, faces=faces)
        files = {key:dict(path=str(path.relative_to(R)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for key,path in paths.items()}
        records.append(dict(name=name, body='torso', material='PETG', density_kg_m3=1270, unit='mm',
            volume_mm3=volume, mass_kg=volume*1270e-9, full_density_mass_kg=volume*1270e-9,
            removed_native_mass_kg=p['full_density_mass_kg']-volume*1270e-9,
            center_of_mass_world_m=(com/1000).tolist(), inertia_at_com_world_kg_m2=(inertia*1270e-15).tolist(),
            files=files, quad_faces=len(faces), native_valid=True, manufacturing_released=False,
            original_part_step_sha256=p['files']['step']['sha256'], original_skin_wall_mm=2.4,
            native_integration_relative_error=integration,
            requested_native_tessellation_absolute_mm=.12, requested_angular_deflection_rad=.25,
            stl_method='ASCII full precision OCCT vertices; no mesh hole filling or face/normal repair',
            notes=['Elliptical downward hip opening; outer surface away from port remains identical nativeNURBS',
                'No collar, joint guard, hinge or latch release; remaining torso attachment/frame allowances retained']))
        scene.append(dict(name=name, body='torso', group='hip_clearance_skins', material='ivory',
            role='native_lower_hip_arch_candidate', geometry_npz=files['npz']['path'], source_sha256=files['npz']['sha256']))
        print(name, 'native arch and exchanges valid', flush=True)
    payload = dict(schema='goose_hip_clearance_skin_candidate_v1', parts=records,
        variant='wide_arch' if args.wide else 'arch_trial',
        arch_geometry_mm=dict(center_x=-15, center_z=210, radius_x=radius_x, radius_z=80, lateral_start_abs_y=50, lateral_depth=160),
        manufacturing_pass=False, final_appearance_pass=False, full_assembly_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [original, Path(__file__)]},
        limitations=['Sixbody/wing skin replacements only; head remains unchanged',
            'Arch visible near lower wing edge requires visual acceptance; no implicit approval or final identity claim',
            'Native shell topology/volume do not release print orientation, port-edge stiffness or mounting details'])
    (dest/'manifest.json').write_text(json.dumps(payload, indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m', status='LOWER_HIP_ARCH_CANDIDATE_UNRELEASED', parts=scene), separators=(',', ':'))+'\n')
    print('removed skin mass kg', sum(p['removed_native_mass_kg'] for p in records))


if __name__ == '__main__':
    main()
