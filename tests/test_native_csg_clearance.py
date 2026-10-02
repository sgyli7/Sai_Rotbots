"""A subtraction void proves clearance only when it contains the whole part."""
import numpy as np
import pytest

from sai_agent.native_csg import contained_in_one_void, subtraction_witness_violations

cad = pytest.importorskip('build123d')


def test_inside_removed_material_is_certified_but_crossing_it_is_rejected():
    void = cad.Box(12, 12, 12)
    inside = cad.Box(10, 10, 10)
    proof = contained_in_one_void(inside, [void])
    assert proof['outside_volume_mm3'] < 1e-7
    assert proof['void_index'] == 0
    crossing = cad.Pos(5, 0, 0) * cad.Box(4, 4, 4)
    assert contained_in_one_void(crossing, [void]) is None


def test_void_bbox_alone_cannot_certify_a_part_in_retained_material():
    # A bored cut has the same outside bounds as a full box, but the centre
    # column remains material. This catches replacing containment with AABB.
    void = cad.Box(12, 12, 12) - cad.Cylinder(2, 16)
    assert contained_in_one_void(cad.Box(2, 2, 2), [void]) is None


def test_certificate_preserves_placement_and_checks_disconnected_children():
    void = cad.Box(12, 12, 12)
    assembly = cad.Compound(children=[cad.Box(2, 2, 2),
                                    cad.Pos(20, 0, 0) * cad.Box(2, 2, 2)])
    assert contained_in_one_void(assembly, [void]) is None
    matrix = np.eye(4)
    from scipy.spatial.transform import Rotation
    from OCP.gp import gp_Trsf
    matrix[:3, :3] = Rotation.from_rotvec([.2, -.4, .7]).as_matrix()
    matrix[:3, 3] = [20, 31, -5]
    transform = gp_Trsf()
    transform.SetValues(*map(float, matrix[:3].ravel()))
    location = cad.Location(transform)
    assert contained_in_one_void(cad.Box(10, 10, 10).moved(location),
                                 [void.moved(location)]) is not None
    assert contained_in_one_void(cad.Box(10, 10, 10),
                                 [void.moved(location)]) is None


def test_surface_only_inputs_cannot_claim_volume_clearance():
    box = cad.Box(10, 10, 10)
    with pytest.raises(ValueError, match='solid'):
        contained_in_one_void(cad.Shell(box.faces()), [cad.Box(12, 12, 12)])


def test_semantic_gate_rejects_an_added_solid_inside_a_real_subtraction():
    void=cad.Box(12,12,12)
    correct=cad.Box(20,20,20)-void
    assert subtraction_witness_violations(correct,[void])==[]
    # Validity, closed winding and positive volume alone would accept this
    # erroneous result. The centre was empty, yet now contains added material.
    wrong=correct+cad.Box(2,2,2)
    assert wrong.is_valid
    violations=subtraction_witness_violations(wrong,[void])
    assert any(row['point_world_mm']==[0.,0.,0.] for row in violations)
