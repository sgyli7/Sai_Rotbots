"""Exact native CAD interference, with optional CAD dependencies loaded on use."""


def common_solid_volume_mm3(a, b):
    """Volume common to two mm-native OCCT shapes, retaining assembly placement.

    Imported STEP compounds can contain independently located children. Use
    OCCT directly rather than wrapper algebra that reconstructs the assembly.
    Only closed solids contribute. Reject surface-only inputs rather than
    reporting a misleading zero volume as a clearance proof.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer

    if not a.solids() or not b.solids():
        raise ValueError('Common solid volume requires solids; use surface distance for vendor shells')

    aa = a.bounding_box(); bb = b.bounding_box()
    low = [max(x, y) for x, y in zip(aa.min, bb.min)]
    high = [min(x, y) for x, y in zip(aa.max, bb.max)]
    if any(hi-lo <= 1e-6 for lo, hi in zip(low, high)):
        return 0.
    common = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    common.Build()
    if not common.IsDone():
        raise ValueError('OCCT common did not finish')
    explorer = TopExp_Explorer(common.Shape(), TopAbs_SOLID)
    volume = 0.
    while explorer.More():
        properties = GProp_GProps()
        BRepGProp.VolumeProperties_s(explorer.Current(), properties, True)
        volume += float(properties.Mass())
        explorer.Next()
    if volume < -1e-7:
        raise ValueError('Negative common-solid volume')
    return volume


def sampled_skin_quads(outer_surface, inner_surface, cell_mask, factor=5):
    """Sample shared CAD parameters into a directed, closed quad skin.

    Surfaces provide Value(u,v). Callers separately validate CAD fidelity.
    This closes authoring-mask boundaries; it never repairs a broken STL.
    Coordinates retain the input surface unit, normally millimetres.
    """
    from collections import Counter
    import numpy as np
    if factor < 1 or int(factor) != factor:
        raise ValueError('positive integer sampling factor required')
    mask = np.asarray(cell_mask, dtype=bool)
    if mask.ndim != 2 or not mask.any():
        raise ValueError('nonempty2D authoring mask required')
    refined = np.repeat(np.repeat(mask, factor, axis=0), factor, axis=1)
    nu, nv = refined.shape; arrays = []
    for surface in (outer_surface, inner_surface):
        array = np.empty((nu+1, nv+1, 3))
        for i in range(nu+1):
            for j in range(nv+1):
                array[i, j] = surface.Value(i/nu, j/nv).Coord()
        arrays.append(array.reshape(-1, 3))
    raw = [(i*(nv+1)+j, (i+1)*(nv+1)+j, (i+1)*(nv+1)+j+1, i*(nv+1)+j+1)
           for i, j in np.argwhere(refined)]
    used = sorted({v for face in raw for v in face}); remap = {v:i for i,v in enumerate(used)}
    faces = [tuple(remap[v] for v in face) for face in raw]; n = len(used)
    edges = Counter(tuple(sorted((a,b))) for face in faces for a,b in zip(face, face[1:]+face[:1]))
    boundary = [(a,b) for face in faces for a,b in zip(face, face[1:]+face[:1]) if edges[tuple(sorted((a,b)))] == 1]
    closed = faces+[tuple(v+n for v in reversed(face)) for face in faces]
    closed += [(b,a,a+n,b+n) for a,b in boundary]
    vertices = np.vstack([array[used] for array in arrays]); closed = np.asarray(closed, dtype=np.int64)
    tri = np.concatenate([closed[:, [0,1,2]], closed[:, [0,2,3]]])
    volume = np.einsum('ij,ij->i', vertices[tri[:,0]], np.cross(vertices[tri[:,1]], vertices[tri[:,2]])).sum()/6
    if not np.isfinite(volume) or volume == 0:
        raise ValueError('skin construction has no signed volume')
    if volume < 0: closed = closed[:, ::-1]
    return vertices, closed


def boundary_surface_distance_mm(a, b):
    """Distance between placed boundary faces, without solid containment tests.

    This measures geometric surfaces only: containment/material classification
    remains a separate gate. Preserve native face locations via OCCT directly.
    """
    from OCP.BRep import BRep_Builder
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS_Compound
    surfaces=[]
    for shape in (a,b):
        builder=BRep_Builder();compound=TopoDS_Compound();builder.MakeCompound(compound)
        explorer=TopExp_Explorer(shape.wrapped,TopAbs_FACE);count=0
        while explorer.More():
            builder.Add(compound,explorer.Current());count+=1;explorer.Next()
        if not count:raise ValueError('surface distance requires boundary faces')
        surfaces.append(compound)
    extrema=BRepExtrema_DistShapeShape(*surfaces);extrema.Perform()
    if not extrema.IsDone() or extrema.NbSolution()<1:raise ValueError('native boundary distance did not finish')
    return float(extrema.Value())
