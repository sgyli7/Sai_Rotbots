"""Real CAD controls for necessary containment and subtraction invariants."""
import pytest

cad = pytest.importorskip('build123d')

from sai_agent.native_cad_query import native_point_query, native_difference_witness


def test_box_material_boundary_and_exterior_queries():
    box = cad.Box(10, 10, 10)
    interior = native_point_query(box, [0, 0, 0])
    assert interior['strict_material_witness_candidate']
    assert interior['boundary_distance_mm'] == pytest.approx(5)
    boundary = native_point_query(box, [5, 0, 0])
    assert boundary['raw_native_classification'] == 'ON'
    assert boundary['query_consistent'] and not boundary['strict_material_witness_candidate']
    exterior = native_point_query(box, [6, 0, 0])
    assert not exterior['within_conservative_bounds']
    assert exterior['raw_native_classification'] == 'OUT'
    assert exterior['query_consistent'] and not exterior['strict_material_witness_candidate']


def test_subtraction_identity_rejects_unchanged_input():
    source, tool = cad.Box(10, 10, 10), cad.Box(2, 2, 12)
    correct = native_difference_witness(source, tool, source-tool, [0, 0, 0])
    assert correct['witness_applicable'] and correct['boolean_query_consistent']
    wrong = native_difference_witness(source, tool, source, [0, 0, 0])
    assert wrong['witness_applicable'] and wrong['difference_identity_violated']
    assert not wrong['boolean_query_consistent']


def test_boundary_distance_includes_sealed_cavity_shell():
    shape = cad.Box(10, 10, 10)-cad.Box(2, 2, 2)
    assert len(shape.solids()) == 1 and len(shape.solids()[0].shells()) == 2
    result = native_point_query(shape, [0, 0, 0])
    assert result['raw_native_classification'] == 'OUT'
    assert result['boundary_distance_mm'] == pytest.approx(1)
    assert result['query_consistent'] and not result['strict_material_witness_candidate']


def test_nonfinite_points_and_nonpositive_tolerance_are_rejected():
    box = cad.Box(10, 10, 10)
    for point, tolerance in [([float('nan'), 0, 0], 1e-7), ([0, 0], 1e-7), ([0, 0, 0], 0)]:
        with pytest.raises(ValueError):
            native_point_query(box, point, tolerance)


def test_trimmed_goose_skin_never_accepts_out_of_bounds_material_witness():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    shape = cad.import_brep(root / 'robots/Goose_V0.1/cad/source/body_bay_skins/wing_access_cover_right.brep')
    moved = shape.rotate(cad.Axis((0, -110, 359), (1, 0, 0)), -45)
    result = native_point_query(moved, [-90.8761614465459, -82.9033091617219, 368.747414902875])
    assert not result['within_conservative_bounds']
    assert not result['strict_material_witness_candidate']
    if result['raw_native_classification'] != 'OUT':
        assert not result['query_consistent']
