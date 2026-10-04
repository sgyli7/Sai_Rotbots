"""Regression controls for folded native skins and exact shared-surface trims."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pytest

cad = pytest.importorskip('build123d')
from sai_agent.native_cad_query import native_solid_integrity
from sai_agent.native_cad_skin import shared_surface_skin, shared_surface_quads

ROOT = Path(__file__).resolve().parents[1]


def test_valid_solid_control_and_real_folded_skin_have_distinct_integrity():
    positive = native_solid_integrity(cad.Box(10, 10, 10))
    assert positive['boolean_input_integrity_pass']
    path = ROOT/'robots/Goose_V0.1/cad/source/body_bay_skins/wing_access_cover_right.brep'
    faulty = native_solid_integrity(cad.import_brep(path))
    assert faulty['topology_valid'] and faulty['solid_count'] == 1
    assert not faulty['native_small_edge_and_self_interference_valid']
    assert not faulty['boolean_input_integrity_pass']
    assert any('SelfIntersect' in row['status'] for row in faulty['faults'])


def test_trim_geometry_uses_exact_plane_surfaces_with_closed_quad_exchange():
    import sys
    sys.path.insert(0, str(ROOT/'scripts/cad'))
    from goose_nurbs_skin import surface
    grid = np.array([[[float(i), float(j), 1.] for j in range(4)] for i in range(4)])
    inner = grid.copy()
    inner[:, :, 2] = 0
    out, inside = surface(grid), surface(inner)
    mask = np.ones((2, 2), dtype=bool)
    us, vs = np.array([.2, .45, .8]), np.array([.1, .5, .9])
    shape = shared_surface_skin(out, inside, mask, us, vs)
    assert native_solid_integrity(shape)['boolean_input_integrity_pass']
    assert shape.volume == pytest.approx(3*.6*3*.8)
    bounds = shape.bounding_box()
    assert tuple(bounds.min) == pytest.approx((.6, .3, 0), abs=1e-6)
    assert tuple(bounds.max) == pytest.approx((2.4, 2.7, 1), abs=1e-6)
    vertices, faces = shared_surface_quads(out, inside, mask, us, vs, factor=2)
    import trimesh
    mesh = trimesh.Trimesh(vertices, np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]]), process=False)
    assert faces.shape[1] == 4 and mesh.is_watertight and mesh.is_winding_consistent
    assert mesh.volume == pytest.approx(shape.volume)
    with pytest.raises(ValueError):
        shared_surface_skin(out, inside, mask, [.2, .2, .8], vs)
    with pytest.raises(ValueError):
        shared_surface_skin(out, inside, mask, [-.1, .45, .8], vs)


def test_repaired_six_native_sources_are_healthy_and_closed_doors_are_separated():
    robot = ROOT/'robots/Goose_V0.1'
    manifest = json.loads((robot/'cad/exports/torso_service_skin/manifest.json').read_text())
    shapes = {}
    for record in manifest['parts']:
        file = record['files']['brep']
        path = robot/file['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256']
        shape = cad.import_brep(path)
        assert native_solid_integrity(shape)['boolean_input_integrity_pass'], record['name']
        shapes[record['name']] = shape
    for side in ['right', 'left']:
        for end in ['aft', 'fore']:
            door = shapes['wing_service_door_'+side]
            fixed = shapes['torso_service_shell_'+side+'_'+end]
            assert door.distance_to(fixed) >= .5


def test_rigid_rotation_interval_bound_detects_a_real_obstacle():
    import sys
    sys.path.insert(0, str(ROOT/'scripts/diagnostics'))
    from check_goose_torso_service_skin import certify_rotation_distance
    moving = cad.Pos(0, 0, 10)*cad.Box(1, 1, 1)
    far = cad.Pos(0, 100, 0)*cad.Box(1, 1, 1)
    positive = certify_rotation_distance(moving, far, [0, 0], 1, [0, 90], .1, .1)
    assert positive['bare_skin_rotation_bound_pass']
    intervals = positive['certified_intervals']
    assert intervals[0]['interval_deg'][0] == 0 and intervals[-1]['interval_deg'][1] == 90
    assert all(a['interval_deg'][1] == b['interval_deg'][0] for a, b in zip(intervals, intervals[1:]))
    # Rotation around X sends the centre to (0,-10,0) at90degrees.
    obstacle = cad.Pos(0, -10, 0)*cad.Box(1, 1, 1)
    negative = certify_rotation_distance(moving, obstacle, [0, 0], 1, [0, 90], .1, .1)
    assert not negative['bare_skin_rotation_bound_pass'] and negative['rejected_intervals']


def test_rotation_bound_rejects_query_budget_exhaustion():
    import sys
    sys.path.insert(0, str(ROOT/'scripts/diagnostics'))
    from check_goose_torso_service_skin import certify_rotation_distance
    moving = cad.Pos(0, 0, 10)*cad.Box(1, 1, 1)
    report = certify_rotation_distance(moving, moving, [0, 0], 1, [0, 90], .1, .1, max_queries=1)
    assert report['native_distance_queries'] == 1
    assert not report['bare_skin_rotation_bound_pass']
    assert report['rejected_intervals']
    assert all(row['reason'] == 'DISTANCE_QUERY_BUDGET' for row in report['rejected_intervals'])
