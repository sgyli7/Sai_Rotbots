"""Shared-surface CAD skin construction; native units pass through unchanged.

UV boundaries use the original surfaces directly. They are never resampled
and refit to obtain a trim, which would silently change mating surfaces.
"""
from collections import Counter, defaultdict
import numpy as np


def _coordinates(mask, us, vs):
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2 or not mask.any():
        raise ValueError('A nonempty two-dimensional cell mask is required')
    coords = []
    for count, supplied in zip(mask.shape, (us, vs)):
        values = np.linspace(0, 1, count+1) if supplied is None else np.asarray(supplied, dtype=float)
        if (values.shape != (count+1,) or not np.isfinite(values).all()
                or np.any(np.diff(values) <= 0)):
            raise ValueError('Finite, strictly ascending coordinates for every grid boundary required')
        coords.append(values)
    return mask, *coords


def _rectangles(mask):
    work = mask.copy()
    while work.any():
        i, j = np.argwhere(work)[0]
        width = 1
        while j+width < work.shape[1] and work[i, j+width]:
            width += 1
        height = 1
        while i+height < work.shape[0] and work[i+height, j:j+width].all():
            height += 1
        yield i, i+height, j, j+width
        work[i:i+height, j:j+width] = False


def shared_surface_skin(outer, inner, cell_mask, u_coordinates=None, v_coordinates=None):
    """Build a closed solid from exact trimmed outer/inner CAD surfaces.

    The caller must check topology AND self-interference, mass, minimum wall,
    fit and exchange fidelity. Sewing a solid alone does not certify them.
    """
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge,
                                   BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid)
    from OCP.BRepFill import BRepFill
    from OCP.TopoDS import TopoDS
    from OCP.ShapeFix import ShapeFix_Solid
    from build123d import Solid

    mask, us, vs = _coordinates(cell_mask, u_coordinates, v_coordinates)
    for sf in (outer, inner):
        u0, u1, v0, v1 = sf.Bounds()
        if us[0] < u0 or us[-1] > u1 or vs[0] < v0 or vs[-1] > v1:
            raise ValueError('Trim coordinates extend outside the native surface domain')
    sewing = BRepBuilderAPI_Sewing(1e-5)
    for i, I, j, J in _rectangles(mask):
        for sf in (outer, inner):
            sewing.Add(BRepBuilderAPI_MakeFace(sf, float(us[i]), float(us[I]),
                                               float(vs[j]), float(vs[J]), 1e-7).Face())
    edges = Counter()
    for i, j in np.argwhere(mask):
        p = [(i, j), (i+1, j), (i+1, j+1), (i, j+1)]
        for a, b in zip(p, p[1:]+p[:1]):
            edges[tuple(sorted((a, b)))] += 1
    rows = defaultdict(list)
    for (a, b), count in edges.items():
        if count != 1:
            continue
        if a[0] == b[0]:
            rows[(0, int(a[0]))].append((int(a[1]), int(b[1])))
        else:
            rows[(1, int(a[1]))].append((int(a[0]), int(b[0])))
    for (axis, fixed), segments in rows.items():
        joined = []
        for a, b in sorted(segments):
            if joined and joined[-1][1] == a:
                joined[-1] = (joined[-1][0], b)
            else:
                joined.append((a, b))
        for a, b in joined:
            curves = []
            for sf in (outer, inner):
                c = sf.UIso(float(us[fixed])) if axis == 0 else sf.VIso(float(vs[fixed]))
                values = vs if axis == 0 else us
                curves.append(BRepBuilderAPI_MakeEdge(c, float(values[a]), float(values[b])).Edge())
            sewing.Add(BRepFill.Face_s(*curves))
    sewing.Perform()
    wrapped = sewing.SewedShape()
    if wrapped.ShapeType().name != 'TopAbs_SHELL':
        raise ValueError('Skin boundary did not sew into exactly one shell')
    solid = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(wrapped)).Solid()
    fix = ShapeFix_Solid(solid)
    fix.Perform()
    return Solid(fix.Solid())


def shared_surface_quads(outer, inner, cell_mask, u_coordinates=None, v_coordinates=None, factor=5):
    """Closed all-quad sampling of those exact CAD surfaces and trim boundaries."""
    from .native_cad import sampled_skin_quads
    mask, us, vs = _coordinates(cell_mask, u_coordinates, v_coordinates)

    class ParameterMap:
        def __init__(self, sf):
            self.sf = sf

        def Value(self, u, v):
            return self.sf.Value(float(np.interp(u, np.linspace(0, 1, len(us)), us)),
                                 float(np.interp(v, np.linspace(0, 1, len(vs)), vs)))

    return sampled_skin_quads(ParameterMap(outer), ParameterMap(inner), mask, factor=factor)
