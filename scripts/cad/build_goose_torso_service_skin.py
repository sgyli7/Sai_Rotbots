"""Repair the folded torso skin in a separate candidate; no model adoption.

Exact profile input is preserved, but the lower exit and door seams change.
Native CAD and all-quad/STL samples share the same trimmed surfaces. Fixed
roof mounts, circular neck trim, real hinges and latch are later integration.
"""
from pathlib import Path
import hashlib
import io
import json
import platform
import sys
import numpy as np
import trimesh
import build123d
import OCP
from build123d import export_brep, export_step, import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from goose_nurbs_skin import surface, native_properties
from sai_agent.goose.torso_service_skin import service_skin_grids, service_skin_domains
from sai_agent.native_cad_skin import shared_surface_skin, shared_surface_quads
from sai_agent.native_cad_query import native_solid_integrity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config_path = R / 'configs/torso_service_skin.json'
    cfg = json.loads(config_path.read_text())
    layout_path = R / cfg['layout_path']
    layout = json.loads(layout_path.read_text())
    source = R / 'cad/source/torso_service_skin'
    exports = R / 'cad/exports/torso_service_skin'
    source.mkdir(exist_ok=True)
    exports.mkdir(exist_ok=True)
    records, scene = [], []
    domains = service_skin_domains(cfg['door_trim_uv'], cfg['fixed_seam_trim_u'])
    for side, label in [(-1, 'right'), (1, 'left')]:
        outer, inner = service_skin_grids(layout['body_profile_x_cz_ry_rz_mm'], side,
            layout['body_wall_mm'], layout['lower_limb_exit_boundary_u_v'])
        so, si = surface(outer), surface(inner)
        for suffix, (mask, us, vs) in domains.items():
            name = 'wing_service_door_'+label if suffix == 'door' else 'torso_service_shell_'+label+'_'+suffix
            shape = shared_surface_skin(so, si, mask, us, vs)
            integrity = native_solid_integrity(shape)
            if not integrity['boolean_input_integrity_pass']:
                raise ValueError((name, 'native integrity', integrity))
            volume, com, inertia, integration_error = native_properties(shape)
            for factor in [5, 8, 12]:
                vertices, faces = shared_surface_quads(so, si, mask, us, vs, factor=factor)
                tri = np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]])
                mesh = trimesh.Trimesh(vertices, tri, process=False)
                relative_error = abs(mesh.volume/volume-1)
                if (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
                        and relative_error <= cfg['maximum_quad_native_volume_relative_error']):
                    break
            else:
                raise ValueError((name, 'structured surface fidelity', relative_error))
            paths = dict(brep=source/(name+'.brep'), step=exports/(name+'.step'),
                         stl=exports/(name+'.stl'), npz=source/(name+'_quad.npz'))
            export_brep(shape, paths['brep'])
            export_step(shape, paths['step'])
            back = import_step(paths['step'])
            exchange_integrity = native_solid_integrity(back)
            back_volume, *_ = native_properties(back)
            if not exchange_integrity['boolean_input_integrity_pass'] or abs(back_volume/volume-1) > 1e-5:
                raise ValueError((name, 'STEP exchange', exchange_integrity))
            binary = trimesh.exchange.stl.export_stl(mesh)
            stl_back = trimesh.load(io.BytesIO(binary), file_type='stl', force='mesh', process=True)
            if (stl_back.is_watertight and stl_back.is_winding_consistent
                    and abs(stl_back.volume/volume-1) <= cfg['maximum_quad_native_volume_relative_error']):
                paths['stl'].write_bytes(binary)
                stl_encoding = 'binary32; closed/winding/volume readback verified'
            else:
                paths['stl'].write_text(trimesh.exchange.stl.export_stl_ascii(mesh))
                stl_back = trimesh.load(paths['stl'], force='mesh', process=True)
                stl_encoding = 'ASCII full precision; binary32 rejected'
            if (not stl_back.is_watertight or not stl_back.is_winding_consistent
                    or abs(stl_back.volume/volume-1) > cfg['maximum_quad_native_volume_relative_error']):
                raise ValueError((name, 'STL exchange'))
            np.savez_compressed(paths['npz'], vertices=vertices/1000, faces=faces)
            files = {k:dict(path=str(p.relative_to(R)), sha256=sha(p)) for k, p in paths.items()}
            records.append(dict(name=name, body='torso', unit='mm', density_kg_m3=cfg['density_kg_m3'],
                volume_mm3=volume, mass_kg=volume*cfg['density_kg_m3']*1e-9,
                center_of_mass_world_m=(com/1000).tolist(),
                inertia_at_com_world_kg_m2=(inertia*cfg['density_kg_m3']*1e-15).tolist(),
                native_integrity=integrity, step_integrity=exchange_integrity,
                files=files, quad_faces=len(faces), quad_sampling_factor=factor,
                quad_volume_relative_error=relative_error, step_volume_relative_error=abs(back_volume/volume-1),
                stl_volume_relative_error=abs(stl_back.volume/volume-1), stl_encoding=stl_encoding,
                adaptive_integration_error=integration_error,
                manufacturing_released=False))
            scene.append(dict(name=name, body='torso', group='torso_service_skin',
                material='ivory', role='experimental_torso_skin_not_integrated',
                geometry_npz=files['npz']['path'], source_sha256=files['npz']['sha256']))
            print(name, 'native/self-interference/STEP/quad/STL pass', 'mass_g', volume*cfg['density_kg_m3']*1e-6, flush=True)
    inputs = [config_path, layout_path, Path(__file__),
        ROOT / 'src/sai_agent/goose/torso_service_skin.py',
        ROOT / 'src/sai_agent/native_cad_skin.py', ROOT / 'src/sai_agent/native_cad_query.py',
        ROOT / 'src/sai_agent/native_cad.py', ROOT / 'scripts/cad/goose_nurbs_skin.py']
    manifest = dict(schema='goose_torso_service_skin_v1', parts=records,
        environment=dict(python=platform.python_version(), build123d=build123d.__version__,
                         ocp=OCP.__version__, numpy=np.__version__, trimesh=trimesh.__version__),
        profile_input_unchanged=True, lower_exit_and_seam_geometry_changed=True,
        mass_basis='Native adaptive CAD integration; nominal full-density PETG1270kg/m3',
        authoring_unit='mm; Xforward Yleft Zup before physical rigid lift',
        total_skin_mass_kg=sum(p['mass_kg'] for p in records),
        manufacturing_release=False, integrated_assembly_modified=False,
        physical_parameters_modified=False, runtime_model_modified=False,
        collision_proxy_modified=False, full_assembly_pass=False,
        limitations=['This is only the refitted skin pair; roof bosses, circular neck cut, actual hinges/latch are absent.',
                     'No minimum-wall, strength, tool/wiring, full assembly or current-model dynamics release.',
                     'Quad source samples the native CAD; it is not a subdivision-art control cage.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    (exports/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',
        status='EXPERIMENTAL_GEOMETRY_REPAIR_NOT_INTEGRATED', parts=scene), separators=(',', ':'))+'\n')


if __name__ == '__main__':
    main()
