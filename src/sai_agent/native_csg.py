"""Native containment certificates for recorded subtractive CAD construction.

A caller must establish that each void was actually subtracted from the
placed target solid. This module checks containment, never that provenance.
No mesh, signed-distance approximation or bounding-box-only proof is used.
"""


def contained_in_one_void(part, voids, tolerance_mm3=1e-7):
    """Return a measured certificate if one actual void contains the whole part.

    Bounds only reject impossible candidates. A native CUT of the complete
    part supplies the certificate. Compound children keep their placements.
    Partial coverage by several voids is deliberately not inferred.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer

    if not part.solids():
        raise ValueError('Containment requires a solid part')
    if tolerance_mm3 < 0:
        raise ValueError('Containment tolerance must be non-negative')
    bounds = part.bounding_box(optimal=False)
    for index, void in enumerate(voids):
        if not void.solids():
            raise ValueError('Containment void must be a solid')
        outer = void.bounding_box(optimal=False)
        if any(lo < vlo - 1e-6 or hi > vhi + 1e-6
               for lo, hi, vlo, vhi in zip(bounds.min, bounds.max,
                                           outer.min, outer.max)):
            continue
        operation = BRepAlgoAPI_Cut(part.wrapped, void.wrapped)
        operation.Build()
        if not operation.IsDone():
            raise ValueError('Native containment CUT did not finish')
        explorer = TopExp_Explorer(operation.Shape(), TopAbs_SOLID)
        outside = 0.
        while explorer.More():
            properties = GProp_GProps()
            BRepGProp.VolumeProperties_s(explorer.Current(), properties, True)
            volume = float(properties.Mass())
            if volume < -1e-7:
                raise ValueError('Negative native containment volume')
            outside += max(0., volume)
            explorer.Next()
        if outside <= tolerance_mm3:
            return dict(void_index=index, outside_volume_mm3=outside,
                        tolerance_mm3=tolerance_mm3)
    return None


def subtraction_witness_violations(result, voids):
    """Reject material at seven interior witnesses of each actual cut operand.

    This independently catches the observed OCCT added-cylinder failure even
    for a topologically valid result. It is a sampled semantic rejection gate,
    never a continuous or exhaustive proof that a Boolean result is correct.
    """
    import numpy as np
    if not result.solids():
        raise ValueError('Subtraction result must contain solids')
    violations=[]
    for index,void in enumerate(voids):
        if not void.solids():
            raise ValueError('Subtraction void must contain solids')
        bounds=void.bounding_box(optimal=False)
        low,high=np.array(tuple(bounds.min)),np.array(tuple(bounds.max))
        center=(low+high)/2
        points=[center]
        for axis in range(3):
            for direction in [-1,1]:
                point=center.copy()
                point[axis]+=direction*.2*(high[axis]-low[axis])
                points.append(point)
        for point in points:
            location=tuple(map(float,point))
            if void.is_inside(location) and any(s.is_inside(location) for s in result.solids()):
                violations.append(dict(void_index=index,point_world_mm=list(location)))
    return violations
