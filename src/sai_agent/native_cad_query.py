"""Necessary sanity checks for native CAD queries; no manufacture approval."""


def native_point_query(shape, point_mm, tolerance_mm=1e-7):
    """Audit one native material query against independent geometric bounds.

    OCCT validity and a completed classifier do not guarantee a reliable
    containment result for thin trimmed skins. Retain the raw classification;
    an IN/ON result outside conservative bounds is a rejected query, never an
    interference witness. Consistency here is necessary, not sufficient, for
    a clearance or manufacturing claim.
    """
    import math
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRep import BRep_Builder
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS_Compound
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON, TopAbs_OUT, TopAbs_SHELL

    point = tuple(float(v) for v in point_mm)
    if (len(point) != 3 or not all(math.isfinite(v) for v in point)
            or not math.isfinite(tolerance_mm) or tolerance_mm <= 0):
        raise ValueError('Finite millimetre XYZ and positive tolerance required')
    solids = shape.solids()
    if not shape.is_valid or len(solids) != 1:
        raise ValueError('Point audit requires one valid native solid')
    solid = solids[0]
    # Non-optimal OCCT bounds are conservative, including surface poles. A
    # point outside them cannot be in the material, regardless of a classifier.
    bounds = solid.bounding_box(optimal=False)
    low, high = tuple(bounds.min), tuple(bounds.max)
    bounded = all(lo-tolerance_mm <= p <= hi+tolerance_mm
                  for p, lo, hi in zip(point, low, high))
    query_point = gp_Pnt(*point)
    classifier = BRepClass3d_SolidClassifier(solid.wrapped, query_point, tolerance_mm)
    state = classifier.State()
    labels = {TopAbs_IN: 'IN', TopAbs_ON: 'ON', TopAbs_OUT: 'OUT'}
    label = labels.get(state, 'UNKNOWN')
    # A solid can have an outer shell and sealed cavity shells. Keep every
    # placed boundary, without triggering solid-containment distance shortcuts.
    boundary = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(boundary)
    explorer = TopExp_Explorer(solid.wrapped, TopAbs_SHELL)
    while explorer.More():
        builder.Add(boundary, explorer.Current())
        explorer.Next()
    distance = BRepExtrema_DistShapeShape(
        BRepBuilderAPI_MakeVertex(query_point).Vertex(), boundary)
    distance.Perform()
    if not distance.IsDone() or distance.NbSolution() < 1:
        raise ValueError('Native boundary distance did not complete')
    gap = float(distance.Value())
    if not math.isfinite(gap) or gap < 0:
        raise ValueError('Invalid native boundary distance')
    consistent = (label != 'UNKNOWN' and (bounded or label == 'OUT')
                  and (label != 'ON' or gap <= tolerance_mm))
    return dict(point_mm=list(point), raw_native_classification=label,
                conservative_bounds_mm=[list(low), list(high)],
                within_conservative_bounds=bounded, boundary_distance_mm=gap,
                query_consistent=consistent,
                strict_material_witness_candidate=(consistent and bounded
                                                   and label == 'IN'
                                                   and gap > tolerance_mm),
                proves_manufacturing_clearance=False)


def native_difference_witness(source, tool, result, point_mm, tolerance_mm=1e-7):
    """Check the necessary set identity at a declared strict Boolean witness.

    A strict interior point of A and B cannot remain in A minus B. A violated
    identity rejects the query/Boolean combination, without guessing which
    OCCT operation is wrong. It does not certify the rest of a Boolean result.
    """
    probes = {name: native_point_query(shape, point_mm, tolerance_mm)
              for name, shape in [('source', source), ('tool', tool), ('result', result)]}
    query_consistent = all(p['query_consistent'] for p in probes.values())
    applicable = query_consistent and all(
        probes[name]['strict_material_witness_candidate'] for name in ['source', 'tool'])
    identity_violated = applicable and probes['result']['strict_material_witness_candidate']
    return dict(probes=probes, witness_applicable=applicable,
                boolean_query_consistent=query_consistent and not identity_violated,
                difference_identity_violated=identity_violated,
                proves_full_boolean_result=False)
