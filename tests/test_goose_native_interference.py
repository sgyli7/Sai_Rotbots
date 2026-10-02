"""Analytical volumes and rigid-motion invariance, independent of robot layout."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from sai_agent.native_cad import common_solid_volume_mm3, boundary_surface_distance_mm

build123d = pytest.importorskip('build123d')


@pytest.mark.parametrize('offset,expected', [(0., 1000.), (5., 500.), (10., 0.)])
@pytest.mark.parametrize('angle', [0., -.6, .6])
def test_placed_assembly_common_matches_analytical_volume(offset, expected, angle):
    # Compound children retain their own placement, then a common arbitrary
    # rigid rotation/translation acts on both assembly roots.
    a = build123d.Compound(children=[build123d.Box(10, 10, 10)])
    b = build123d.Compound(children=[build123d.Pos(offset, 0, 0)*build123d.Box(10, 10, 10)])
    from OCP.gp import gp_Trsf
    matrix = np.eye(4); matrix[:3, :3] = Rotation.from_rotvec([.17, -.29, angle]).as_matrix()
    matrix[:3, 3] = [23, -15, 90]
    trsf = gp_Trsf(); trsf.SetValues(*[float(v) for v in matrix[:3].ravel()])
    location = build123d.Location(trsf)
    assert common_solid_volume_mm3(a.moved(location), b.moved(location)) == pytest.approx(expected, abs=1e-6)


def test_shell_volume_is_not_a_clearance_proof():
    solid = build123d.Box(10, 10, 10)
    shell = build123d.Shell(solid.faces())
    assert shell.distance_to(solid) == pytest.approx(0, abs=1e-6)
    with pytest.raises(ValueError, match='requires solids'):
        common_solid_volume_mm3(shell, solid)


@pytest.mark.parametrize('angle',[0.,.7])
def test_boundary_distance_distinguishes_an_empty_cavity_from_material(angle):
    hollow=build123d.Box(20,20,20)-build123d.Box(16,16,16)
    inner=build123d.Box(10,10,10)
    from OCP.gp import gp_Trsf
    matrix=np.eye(4);matrix[:3,:3]=Rotation.from_rotvec([.2,-.3,angle]).as_matrix();matrix[:3,3]=[20,-30,11]
    trsf=gp_Trsf();trsf.SetValues(*[float(v) for v in matrix[:3].ravel()]);location=build123d.Location(trsf)
    assert boundary_surface_distance_mm(hollow.moved(location),inner.moved(location))==pytest.approx(3,abs=1e-6)
    crossing=build123d.Pos(8,0,0)*build123d.Box(4,4,4)
    assert boundary_surface_distance_mm(hollow.moved(location),crossing.moved(location))==pytest.approx(0,abs=1e-6)
    assert common_solid_volume_mm3(hollow.moved(location),crossing.moved(location))==pytest.approx(32,abs=1e-6)
