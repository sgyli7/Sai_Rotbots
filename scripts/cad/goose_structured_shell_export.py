"""Local boss/hole mesh booleans preserve the existing sampled NURBS shell.

Native BREP/STEP remain authoritative. This avoids globally retessellating a
trimmed thin shell when only a small interior attachment changes.
"""
import hashlib
from pathlib import Path

import numpy as np
import trimesh
import manifold3d
from build123d import export_brep, export_step, export_stl, import_step
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties


def emit_structured_shell(export, name, shape, old_npz, boss, pilot):
    if not shape.is_valid or len(shape.solids()) != 1:
        raise ValueError((name, 'Invalid native shell'))
    v, c, inertia, _ = native_properties(shape)
    data = np.load(old_npz)
    vertices, faces = data['vertices']*1000, data['faces']
    if faces.shape[1] != 4:
        raise ValueError('Non-quad predecessor')
    old = trimesh.Trimesh(vertices, np.concatenate([faces[:, [0,1,2]], faces[:, [0,2,3]]]), process=True)
    private = export.robot.parents[1] / 'artifacts/Goose_V0.1/torso_shell_mesh_operations'
    private.mkdir(parents=True, exist_ok=True)
    def local_mesh(solid, suffix):
        path = private / (name+'_'+suffix+'.stl')
        export_stl(solid, path, tolerance=.015, angular_tolerance=.06)
        mesh = trimesh.load(path, force='mesh', process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid primitive mesh')
        return mesh
    def as_manifold64(mesh):
        result=manifold3d.Manifold(manifold3d.Mesh64(
            vert_properties=np.ascontiguousarray(mesh.vertices,dtype=np.float64),
            tri_verts=np.ascontiguousarray(mesh.faces,dtype=np.uint64)))
        if result.status()!=manifold3d.Error.NoError:
            raise ValueError(('Invalid Boolean input',result.status()))
        return result
    # Preserve thin-shell coordinates at the Boolean input, not only export.
    # The trimesh adapter uses float32 Mesh and can collapse inherited edges.
    result=(as_manifold64(old)+as_manifold64(local_mesh(boss,'boss')))-as_manifold64(local_mesh(pilot,'pilot'))
    if result.status()!=manifold3d.Error.NoError:
        raise ValueError(('Invalid Boolean result',result.status()))
    converted=result.to_mesh64()
    mesh=trimesh.Trimesh(np.asarray(converted.vert_properties)[:,:3],
                       np.asarray(converted.tri_verts),process=False)
    unsimplified_triangles=len(mesh.faces)
    # Keep surface movement below0.00001mm while removing edges too short for
    # binary32 STL near400mm coordinates. This is a bounded tessellation step;
    # it does not change the native CAD source or manufacturing dimensions.
    tolerance_mm=.00001
    simplified=result.simplify(tolerance_mm).to_mesh64()
    mesh=trimesh.Trimesh(np.asarray(simplified.vert_properties)[:,:3],
                       np.asarray(simplified.tri_verts),process=False)
    error = abs(mesh.volume/v-1)
    if not mesh.is_watertight or not mesh.is_winding_consistent or error > .005:
        raise ValueError((name,'Local boolean mesh mismatch', error))
    paths = dict(brep=export.source/(name+'.brep'), step=export.out/(name+'.step'),
                 stl=export.out/(name+'.stl'), npz=export.source/(name+'_quad.npz'))
    export_brep(shape, paths['brep']); export_step(shape, paths['step'])
    rt = import_step(paths['step']); rv, *_ = native_properties(rt)
    if not rt.is_valid or len(rt.solids()) != 1 or abs(rv/v-1)>1e-5:
        raise ValueError('Native STEP round trip mismatch')
    paths['stl'].write_bytes(trimesh.exchange.stl.export_stl(mesh))
    back = trimesh.load(paths['stl'], force='mesh', process=True)
    stl_encoding='binary32 after bounded0.00001mm simplification'
    if not back.is_watertight or not back.is_winding_consistent:
        paths['stl'].write_text(trimesh.exchange.stl.export_stl_ascii(mesh))
        back=trimesh.load(paths['stl'],force='mesh',process=True)
        stl_encoding='ASCII full precision; binary32 closure failed and is not delivered'
    if not back.is_watertight or not back.is_winding_consistent or abs(back.volume/v-1)>.005:
        raise ValueError('STL round trip mismatch')
    qv, qf = quad_sampling(mesh)
    np.savez_compressed(paths['npz'], vertices=qv, faces=qf)
    files = {k:dict(path=str(p.relative_to(export.robot)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
             for k,p in paths.items()}
    export.parts.append(dict(name=name,body='torso',unit='mm',density_kg_m3=1270.,
        mass_kg=v*1270e-9,volume_mm3=v,center_of_mass_world_m=(c/1000).tolist(),
        inertia_at_com_world_kg_m2=(inertia*1270e-15).tolist(),files=files,quad_faces=len(qf),
        native_valid=True,stl_watertight=True,manufacturing_released=False,
        mass_basis='native density estimate',
        mesh_basis='Existing shared sampled NURBS shell; local double-precision Manifold boss union/pilot difference; closed quad subdivision',
        stl_encoding=stl_encoding,unsimplified_triangle_count=unsimplified_triangles,
        simplification_surface_movement_bound_mm=tolerance_mm,
        predecessor_quad_sha256=hashlib.sha256(Path(old_npz).read_bytes()).hexdigest(),
        exchange_validation=dict(step_volume_relative_error=abs(rv/v-1),stl_volume_relative_error=error,
                                 local_primitive_tolerance_mm=.015,local_primitive_angular_tolerance_rad=.06),
        notes=['Printed9.2OD internal boss,4mm blind pilot depth6.7mm for RX-M3x5.7.',
               'Native source preserved; sampled mesh is approximate, not a new exact native surface.',
               'Print direction, heat setting, pullout, local strength and full shell seams remain gates.']))
    export.scene.append(dict(name=name,body='torso',group=export.folder,material='ivory',
        role='native_shell_attachment_candidate_not_released',geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))
    print('STRUCTURED SHELL',name,len(qf),'quad',error,'relative volume error',flush=True)
