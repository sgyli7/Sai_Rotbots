"""Collision-only reductions. Never derive a body's mass from these meshes.

Planar extrusions preserve their section holes. Curved surfaces are bounded
local patches, not the convex hull of an entire hollow component. All error
measurements are sampled diagnostics, not certified Hausdorff bounds.
"""
import numpy as np
import trimesh
from scipy.spatial import ConvexHull


def convex_mesh(points, planar_skin_m=1e-5):
    # Runtime collision coordinates only: remove sub-nanometre duplicates
    # before Qhull triangulates coplanar faces. Native source is untouched.
    points = np.unique(np.round(np.asarray(points), 10), axis=0)
    centered = points-points.mean(axis=0)
    _, singular, vectors = np.linalg.svd(centered, full_matrices=False)
    if len(singular) < 2 or singular[1] < 1e-10:
        return None
    if len(singular) < 3 or singular[2] < 1e-10:
        # A documented 10um numerical skin, never a whole-part AABB.
        normal = vectors[-1]*planar_skin_m/2
        points = np.vstack([points-normal, points+normal])
    # Centre before Qhull/Trimesh cleanup. A sub-mm patch at Z=.6m must
    # not lose faces through absolute-coordinate numerical cancellation.
    center = points.mean(axis=0)
    qhull = ConvexHull(points-center, qhull_options='Qx')
    faces = qhull.simplices.copy()
    triangles = qhull.points[faces]
    cross = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    reverse = np.einsum('ij,ij->i', cross, qhull.equations[:, :3]) < 0
    faces[reverse] = faces[reverse][:, [0, 2, 1]]
    # Keep Qhull's exact shared indices. Trimesh's generic convex helper
    # merges short edges and can open small curved patches in SI coordinates.
    hull = trimesh.Trimesh(qhull.points, faces, process=False)
    hull.remove_unreferenced_vertices()
    if hull.is_watertight and not hull.is_winding_consistent:
        # Qt can introduce zero-area coplanar facets whose cross-product
        # cannot choose orientation. Fix INDEX winding only, not coordinates.
        trimesh.repair.fix_winding(hull)
    hull.apply_translation(center)
    if not hull.is_watertight or not hull.is_winding_consistent or hull.volume <= 0:
        raise ValueError(f'invalid local convex patch: closed={hull.is_watertight} '
                         f'winding={hull.is_winding_consistent} volume={hull.volume}')
    return hull


def merge_convex_polygons(polygons):
    """Merge only exact convex unions. A hole cannot be covered by a merge."""
    polys = list(polygons)
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(polys):
            for j in range(i+1, len(polys)):
                b = polys[j]
                if a.boundary.intersection(b.boundary).length < 1e-10:
                    continue
                union = a.union(b)
                if union.geom_type != 'Polygon' or len(union.interiors):
                    continue
                if union.convex_hull.area-union.area > 1e-13:
                    continue
                polys[i] = union.convex_hull; polys.pop(j)
                changed = True
                break
            if changed:
                break
    return polys


def uniform_extrusion_hulls(mesh, tolerance_m=.00012, installed_fastener_holes=False):
    """Recognize uniform source extrusions; refuse stepped/cross-drilled parts.

Source quad sampling adds face midpoints, so a uniform depth coordinate has
two end values and sometimes one middle value. Volume is independently checked.
"""
    import shapely
    from shapely.geometry import Polygon
    points = mesh.vertices
    for axis in range(3):
        depths = np.unique(np.round(points[:, axis], 9))
        thickness = points[:, axis].ptp() if hasattr(points[:, axis], 'ptp') else np.ptp(points[:, axis])
        if thickness < 1e-6 or len(depths) > 9:
            continue
        levels = (depths-depths[0])/(depths[-1]-depths[0])
        # Quad sampling of two end faces and side triangles creates sixths.
        if np.max(np.abs(levels*6-np.round(levels*6))) > 1e-5:
            continue
        other = [i for i in range(3) if i != axis]
        normal = np.eye(3)[axis]
        origin = points.mean(axis=0)
        path = mesh.section(plane_origin=origin, plane_normal=normal)
        if path is None:
            continue
        polygon = None
        for loop in path.discrete:
            p = Polygon(loop[:, other])
            if not p.is_valid:
                p = shapely.make_valid(p)
            polygon = p if polygon is None else polygon.symmetric_difference(p)
        if polygon is None or polygon.geom_type not in ['Polygon', 'MultiPolygon']:
            continue
        source_volume = abs(mesh.volume)
        if source_volume < 1e-14 or abs(polygon.area*thickness/source_volume-1) > 1e-6:
            continue
        removed = []
        collision_polygon = polygon
        if installed_fastener_holes:
            import math
            from shapely.geometry import MultiPolygon
            components = []
            for component in ([polygon] if polygon.geom_type=='Polygon' else polygon.geoms):
                keep = []
                for ring in component.interiors:
                    hole = Polygon(ring)
                    span = np.ptp(np.array(ring.coords),axis=0)
                    circularity = 4*math.pi*hole.area/hole.length**2
                    if max(span) <= .0065 and circularity >= .85:
                        removed.append(dict(center_uv_m=list(hole.centroid.coords)[0],
                            span_uv_m=span.tolist(), reason='installed_small_round_fastener_port_contact_abstraction'))
                    else:
                        keep.append(ring)
                components.append(Polygon(component.exterior,keep))
            collision_polygon = components[0] if len(components)==1 else MultiPolygon(components)
        simplified = collision_polygon.simplify(tolerance_m, preserve_topology=True)
        # Simplification must retain every section hole, including small ones.
        def holes(p):
            return sum(len(x.interiors) for x in ([p] if p.geom_type=='Polygon' else p.geoms))
        if holes(collision_polygon) != holes(simplified):
            raise ValueError('section simplification changed hole count')
        triangles = shapely.constrained_delaunay_triangles(simplified)
        regions = merge_convex_polygons(triangles.geoms)
        hulls = []
        for region in regions:
            uv = np.array(region.exterior.coords)[:-1]
            vertices = np.zeros((2*len(uv), 3))
            vertices[:len(uv), axis] = points[:, axis].min()
            vertices[len(uv):, axis] = points[:, axis].max()
            vertices[:len(uv), other] = uv
            vertices[len(uv):, other] = uv
            hulls.append(convex_mesh(vertices))
        return hulls, dict(method='uniform_source_extrusion_convex_partition', axis=axis,
                          section_holes=holes(polygon), simplification_tolerance_m=tolerance_m,
                          retained_section_holes=holes(simplified), installed_fastener_ports_abstracted=removed,
                          source_section_volume_relative_error=abs(polygon.area*thickness/source_volume-1),
                          simplified_section_area_relative_error=abs(simplified.area/collision_polygon.area-1),
                          whole_hollow_hull=False)
    return None


def local_surface_hulls(mesh, cell_m=.012, lod_triangles=6000):
    """Single fixed local-patch construction, with ports retained by the LOD.

Triangulation is a runtime representation. Native quad/CAD files are untouched.
Subdividing long triangles limits patch span; no enclosing whole-part box.
"""
    lod = mesh
    if len(mesh.faces) > lod_triangles:
        lod = mesh.simplify_quadric_decimation(face_count=lod_triangles)
    lod_fallback = False
    if not lod.is_watertight or not lod.is_winding_consistent or lod.volume <= 0:
        # Manifold64 preserves source precision and closed topology. One
        # fixed 50um simplification replaces the rejected QEM candidate;
        # no convex-decomposition scan or mesh repair is performed.
        import manifold3d
        solid = manifold3d.Manifold(manifold3d.Mesh64(
            vert_properties=np.ascontiguousarray(mesh.vertices,dtype=np.float64),
            tri_verts=np.ascontiguousarray(mesh.faces,dtype=np.uint64)))
        if solid.status()==manifold3d.Error.NoError:
            simplified = solid.simplify(.00005).to_mesh64()
            lod = trimesh.Trimesh(np.asarray(simplified.vert_properties)[:,:3],
                                  np.asarray(simplified.tri_verts),process=False)
            lod_fallback = True
        elif len(mesh.faces)<=120000:
            lod = mesh; lod_fallback = True
        else:
            raise ValueError('topology-preserving LOD failed; source too large for direct local patches')
        if not lod.is_watertight or not lod.is_winding_consistent or lod.volume<=0:
            raise ValueError('topology-preserving LOD failed; Manifold candidate rejected')
    vertices, faces = trimesh.remesh.subdivide_to_size(lod.vertices, lod.faces, max_edge=cell_m*.6, max_iter=10)
    triangles = vertices[faces]
    bins = np.floor((triangles.mean(axis=1)-lod.bounds[0])/cell_m).astype(np.int64)
    _, indices = np.unique(bins, axis=0, return_inverse=True)
    order = np.argsort(indices)
    cuts = np.r_[0, np.flatnonzero(np.diff(indices[order]))+1, len(order)]
    hulls = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        hull = convex_mesh(triangles[order[a:b]].reshape(-1, 3))
        if hull is not None:
            hulls.append(hull)
    return hulls, lod, dict(method='bounded_local_surface_patches', cell_m=cell_m,
        lod_triangle_limit=lod_triangles, actual_lod_triangles=len(lod.faces),
        rejected_qem_topology_preserving_fallback=lod_fallback,
        topology_preserving_simplification_tolerance_m=.00005 if lod_fallback and lod is not mesh else None,
        planar_numerical_skin_m=1e-5, whole_hollow_hull=False,
        collision_coordinate_quantization_m=1e-10,
        accuracy_certified=False, ports_and_cavities_require_witness_validation=True)


def deterministic_surface_samples(mesh, count=2048):
    # Fixed area-distributed triangle samples, including deterministic edge/face
    # barycentrics; no RNG state can make a failed sample disappear on rerun.
    areas = mesh.area_faces
    cumulative = np.cumsum(areas)
    positions = (np.arange(count)+.5)/count*cumulative[-1]
    faces = mesh.triangles[np.searchsorted(cumulative, positions)]
    u = ((np.arange(count)*.6180339887498949) % 1)**.5
    v = (np.arange(count)*.4142135623730951) % 1
    bary = np.c_[1-u, u*(1-v), u*v]
    return np.einsum('ij,ijk->ik', bary, faces)


def sampled_error(mesh, lod, hulls, samples=2048):
    points = deterministic_surface_samples(mesh, samples)
    proxy = trimesh.util.concatenate(hulls)
    distances = trimesh.proximity.closest_point(proxy, points)[1]
    lod_errors = trimesh.proximity.closest_point(lod, points)[1]
    candidates = deterministic_surface_samples(proxy, samples)
    proxy_to_lod = trimesh.proximity.closest_point(lod, candidates)[1]
    return dict(samples_per_direction=samples,
        source_to_proxy_surface_max_m=float(np.max(distances)),
        source_to_proxy_surface_p95_m=float(np.quantile(distances, .95)),
        source_to_lod_surface_max_m=float(np.max(lod_errors)),
        proxy_to_lod_surface_max_m=float(np.max(proxy_to_lod)),
        sampled_only=True, certified_Hausdorff_bound=False)


def point_inside_hulls(point, hulls, tolerance_m=1e-9):
    point = np.asarray(point)
    for hull in hulls:
        if np.any(point < hull.bounds[0]-tolerance_m) or np.any(point > hull.bounds[1]+tolerance_m):
            continue
        planes = ConvexHull(hull.vertices).equations
        if np.all(planes[:, :3] @ point+planes[:, 3] <= tolerance_m):
            return True
    return False
