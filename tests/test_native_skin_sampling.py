"""Independent planar-prism volume and topology checks for CAD quad sampling."""
from collections import Counter
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from sai_agent.native_cad import sampled_skin_quads


class Point:
    def __init__(self, xyz): self.xyz = xyz
    def Coord(self): return tuple(self.xyz)


class Plane:
    def __init__(self, z, rotation, translation):
        self.z, self.rotation, self.translation = z, rotation, translation
    def Value(self, u, v):
        return Point(self.rotation @ np.array([20*u, 10*v, self.z]) + self.translation)


@pytest.mark.parametrize('factor', [1, 3])
@pytest.mark.parametrize('hole', [False, True])
@pytest.mark.parametrize('rotation_vector', [[0, 0, 0], [.4, -.3, .9]])
def test_planar_mask_prism_is_closed_oriented_and_has_analytical_volume(factor, hole, rotation_vector):
    mask = np.ones((4, 4), dtype=bool)
    if hole: mask[1:3, 1:3] = False
    rotation = Rotation.from_rotvec(rotation_vector).as_matrix()
    translation = np.array([79., -21., 113.])
    v, f = sampled_skin_quads(Plane(0, rotation, translation), Plane(2, rotation, translation), mask, factor)
    assert f.shape[1] == 4
    edges = Counter((int(a), int(b)) for face in f for a, b in zip(face, np.roll(face, -1)))
    assert all(n == 1 and edges[(b, a)] == 1 for (a, b), n in edges.items())
    triangles = np.concatenate([f[:, [0, 1, 2]], f[:, [0, 2, 3]]])
    area = np.linalg.norm(np.cross(v[triangles[:, 1]]-v[triangles[:, 0]], v[triangles[:, 2]]-v[triangles[:, 0]]), axis=1)/2
    assert area.min() > 0
    volume = np.einsum('ij,ij->i', v[triangles[:, 0]], np.cross(v[triangles[:, 1]], v[triangles[:, 2]])).sum()/6
    assert volume == pytest.approx(300 if hole else 400, abs=1e-8)


def test_skin_sampling_rejects_zero_thickness():
    plane = Plane(0, np.eye(3), np.zeros(3))
    with pytest.raises(ValueError, match='signed volume'):
        sampled_skin_quads(plane, plane, np.ones((2, 2), bool))
