"""Reproduce wing-door fit rejection and native query contradictions.

No accepted CAD, physical parameters or runtime collision files are changed.
The resampled cover is a diagnostic construction, not a manufacturing part.
"""
from pathlib import Path
import hashlib
import json
import platform
import sys

import numpy as np
import trimesh
import build123d
import OCP
from build123d import Axis, import_brep

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad'), str(ROOT / 'scripts/diagnostics')]
from goose_nurbs_skin import skin, surface, native_properties
from check_goose_grip_cassettes import bounded_common
from sai_agent.goose.morphology import body_grids
from sai_agent.native_cad import sampled_skin_quads
from sai_agent.native_cad_query import native_point_query


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_from_npz(path):
    data = np.load(path)
    v, f = data['vertices']*1000, data['faces']
    mesh = trimesh.Trimesh(v, np.concatenate([f[:, [0, 1, 2]], f[:, [0, 2, 3]]]), process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError('Diagnostic source mesh is not closed/oriented')
    return mesh


def main():
    sources = [ROBOT / p for p in [
        'configs/body_bay_layout_candidate.json',
        'cad/source/one_piece_head_service_fixture/assembly_scene.json',
        'cad/source/body_bay_skins/wing_access_cover_right.brep',
        'cad/source/body_bay_skins/wing_access_cover_right_quad.npz',
        'cad/source/torso_shell_mounts/torso_mounted_shell_right_fore.brep',
        'cad/source/torso_shell_mounts/torso_mounted_shell_right_aft.brep',
        'cad/source/torso_shell_mounts/torso_mounted_shell_right_aft_quad.npz']]
    cfg = json.loads(sources[0].read_text())
    door, fore, aft = [import_brep(sources[i]) for i in [2, 4, 5]]
    source_case = dict(
        pair=['wing_access_cover_right', 'torso_mounted_shell_right_fore'],
        pose='closed_source_assembly',
        common=bounded_common(door, fore, 15),
        point_queries=[native_point_query(s, [68.3893354918588, -108.41674744685972, 273.4040630641006])
                       for s in [door, fore]])
    # Failed exploratory trim: use the declared parent surface, not a guessed
    # primitive or a stored scratch file. Refit after UV resampling exactly as
    # in the experiment that gave misleading zero-common-volume readings.
    outer, inner = body_grids(cfg['body_profile_x_cz_ry_rz_mm'], -1,
                             cfg['body_wall_mm'], cfg['lower_limb_exit_boundary_u_v'])
    construction = dict(outer_u_bounds=[10/64+.004, 48/64-.004],
                        outer_v_bounds=[14/48+.008, 36/48-.008],
                        sample_grid=[39, 23], outward_y_shift_mm=.25,
                        central_y_bulge_mm=1.2, hinge_axis_yz_mm=[-110, 359])
    grids = []
    for sf in [surface(outer), surface(inner)]:
        grid = np.array([[sf.Value(float(u), float(v)).Coord()
                          for v in np.linspace(*construction['outer_v_bounds'], 23)]
                         for u in np.linspace(*construction['outer_u_bounds'], 39)])
        ii, jj = np.meshgrid(np.arange(39)/38, np.arange(23)/22, indexing='ij')
        grid[:, :, 1] -= .25+1.2*np.sin(ii*np.pi)*np.sin(jj*np.pi)
        grids.append(grid)
    candidate = skin(*grids, np.ones((38, 22), dtype=bool))
    if not candidate.is_valid or len(candidate.solids()) != 1:
        raise ValueError('Diagnostic candidate is not a valid single native solid')
    v, f = sampled_skin_quads(surface(grids[0]), surface(grids[1]),
                              np.ones((38, 22), dtype=bool), factor=3)
    mesh = trimesh.Trimesh(v, np.concatenate([f[:, [0, 1, 2]], f[:, [0, 2, 3]]]), process=False)
    point = [-121.025714449275, -102.852046607637, 302.818235463254]
    trim_case = dict(construction=construction, native_volume_mm3=native_properties(candidate)[0],
                     common=bounded_common(candidate, aft, 15),
                     point_queries=[native_point_query(s, point) for s in [candidate, aft]],
                     independent_sampled_mesh_contains=[bool(m.contains([point])[0])
                                                        for m in [mesh, mesh_from_npz(sources[6])]],
                     independent_mesh_scope='One point, CAD surface sampling3x; not a global clearance certificate')
    strict_candidates = all(p['strict_material_witness_candidate'] for p in trim_case['point_queries'])
    trim_case['zero_common_conflicts_with_material_queries'] = (
        trim_case['common'].get('volume_mm3') == 0 and strict_candidates
        and all(trim_case['independent_sampled_mesh_contains']))
    moved = candidate.rotate(Axis((0, -110, 359), (1, 0, 0)), -45)
    outside_case = native_point_query(moved, [-88.97004, -79.13337, 364.36332])
    report = dict(schema='goose_wing_door_geometry_rejection_v1',
                  environment=dict(python=platform.python_version(), build123d=build123d.__version__,
                                   ocp=OCP.__version__, numpy=np.__version__, trimesh=trimesh.__version__),
                  source_closed_case=source_case, rejected_resampled_trim=trim_case,
                  rotated_native_point_query=outside_case,
                  original_cad_modified=False, physical_parameters_modified=False,
                  collision_proxy_modified=False, new_manufacturing_parts_generated=False,
                  manufacturing_release=False, manual_door_assembly_pass=False,
                  integrations=0, optimizer_steps=0,
                  limitations=[
                      'This diagnoses one original closed pair and one rejected trim, not the full wing mechanism.',
                      'Completed Common/is_valid flags alone do not release thin trimmed skin fit.',
                      'Contradictory kernel/classifier/distance results remain rejected; no guess about the kernel root cause.',
                      'No hinge/latch, continuous sweep, local strength, print fit or complete assembly acceptance.'],
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in sources + [
                      Path(__file__), ROOT / 'src/sai_agent/native_cad_query.py',
                      ROOT / 'src/sai_agent/native_cad.py', ROOT / 'src/sai_agent/goose/morphology.py',
                      ROOT / 'scripts/cad/goose_nurbs_skin.py',
                      ROOT / 'scripts/diagnostics/check_goose_grip_cassettes.py']})
    output = ROBOT / 'evidence/wing_door_geometry_rejection.json'
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(report=str(output), original_common=source_case['common'],
                         failed_trim_common=trim_case['common'],
                         contradictory_trim=trim_case['zero_common_conflicts_with_material_queries'],
                         outside_query_consistent=outside_case['query_consistent'],
                         manual_door_assembly_pass=False)), flush=True)


if __name__ == '__main__':
    main()
