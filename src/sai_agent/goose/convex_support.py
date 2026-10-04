"""Explicit bounded collision polytopes; no mass or controller derivation.

The support graph layout below is pinned to MuJoCo 3.10.0, matching the
engine_collision_convex native graph selection. Raw mesh vertices are not the
same thing as the support hull after maxhullvert cooking.
"""
import mujoco
import numpy as np
import trimesh
from scipy.spatial import ConvexHull,QhullError
from scipy.spatial.transform import Rotation

from .task_collision import convex_mesh as original_convex_mesh,sampled_error


def closest_distance_m(mesh,points):
    # Trimesh's absolute triangle tolerances misclassify very fine SI facets.
    # Compute in mm without changing any authoritative runtime coordinate.
    scaled=mesh.copy();scaled.apply_scale(1000)
    distances=trimesh.proximity.closest_point(scaled,np.asarray(points)*1000)[1]/1000
    if not np.all(np.isfinite(distances)):
        raise ValueError('non-finite collision distance; geometry remains unqualified')
    return distances


def source_surface_error(mesh,lod,hulls,samples=1024):
    scaled=[]
    for item in [mesh,lod,*hulls]:
        copy=item.copy();copy.apply_scale(1000);scaled.append(copy)
    result=sampled_error(scaled[0],scaled[1],scaled[2:],samples)
    for key in result:
        if key.endswith('_m'):result[key]/=1000
    if any(not np.isfinite(value) for value in result.values() if isinstance(value,float)):
        raise ValueError('non-finite surface distance; candidate rejected')
    result['distance_computation_units']='mm_then_explicit_conversion_to_m'
    return result


def convex_mesh(points):
    """Reject first; one documented numerical perturbation for tiny facets.

    Only runtime collision coordinates change, by at most 2 nm per axis.
    This is not mesh repair, material smoothing or a native CAD modification.
    """
    try:
        return original_convex_mesh(points)
    except (ValueError,QhullError) as error:
        if not isinstance(error,QhullError) and not str(error).startswith('invalid local convex patch'):
            raise
        points=np.asarray(points,dtype=float)
        phase=np.arange(points.size,dtype=float).reshape(points.shape)
        perturbation=2e-9*np.sin(phase*1.618033988749895+0.5)
        return original_convex_mesh(points+perturbation)


def source_surface_patches(mesh,cell_m=.003,separate_normals=False):
    vertices,faces=trimesh.remesh.subdivide_to_size(mesh.vertices,mesh.faces,max_edge=cell_m*.6,max_iter=10)
    triangles=vertices[faces];bins=np.floor((triangles.mean(1)-mesh.bounds[0])/cell_m).astype(np.int64)
    if separate_normals:
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        axis=np.argmax(np.abs(normals),axis=1)
        orientation=axis*2+(normals[np.arange(len(axis)),axis]>=0).astype(int)
        bins=np.c_[bins,orientation]
    _,ids=np.unique(bins,axis=0,return_inverse=True);order=np.argsort(ids)
    cuts=np.r_[0,np.flatnonzero(np.diff(ids[order]))+1,len(order)];hulls=[]
    for a,b in zip(cuts[:-1],cuts[1:]):
        hull=convex_mesh(triangles[order[a:b]].reshape(-1,3))
        if hull is not None:hulls.append(hull)
    return hulls,dict(cell_m=cell_m,separate_opposing_surface_normal_groups=separate_normals,
                      maximum_fallback_coordinate_perturbation_per_axis_m=2e-9,
                      planar_numerical_skin_m=1e-5,whole_hollow_hull=False)


def feature_surface_patches(mesh,cell_m=.008,local_sample_budget_m=.0015):
    """One local refinement at holes/concave corners, not a parameter scan.

    Open triangle patches are distance references, not solids. Every local
    hull face centroid is tested; final full-source samples must still pass.
    """
    vertices,faces=trimesh.remesh.subdivide_to_size(mesh.vertices,mesh.faces,max_edge=cell_m*.6,max_iter=10)
    triangles=vertices[faces];normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    axis=np.argmax(np.abs(normals),axis=1);group=axis*2+(normals[np.arange(len(axis)),axis]>=0).astype(int)
    bins=np.c_[np.floor((triangles.mean(1)-mesh.bounds[0])/cell_m).astype(np.int64),group]
    _,ids=np.unique(bins,axis=0,return_inverse=True);order=np.argsort(ids)
    cuts=np.r_[0,np.flatnonzero(np.diff(ids[order]))+1,len(order)];output=[];refined=0
    for a,b in zip(cuts[:-1],cuts[1:]):
        selected=order[a:b];hull=convex_mesh(triangles[selected].reshape(-1,3))
        if hull is None:continue
        patch=trimesh.Trimesh(vertices,faces[selected],process=False);patch.remove_unreferenced_vertices()
        errors=closest_distance_m(patch,hull.triangles_center)
        if max(errors)>local_sample_budget_m:
            pieces,_=source_surface_patches(patch,cell_m=cell_m/2,separate_normals=True)
            output.extend(pieces);refined+=1
        else:output.append(hull)
    return output,dict(cell_m=cell_m,local_refinement_cell_m=cell_m/2,refined_regions=refined,
                       hull_face_centroid_budget_m=local_sample_budget_m,
                       separate_opposing_surface_normal_groups=True,maximum_refinement_depth=1,
                       maximum_fallback_coordinate_perturbation_per_axis_m=2e-9,planar_numerical_skin_m=1e-5,
                       finite_only=True,whole_hollow_hull=False)


def compiled_support(model, mesh_id):
    if mujoco.__version__ != '3.10.0':
        raise ValueError('native convex graph interpretation requires MuJoCo 3.10.0')
    start = int(model.mesh_vertadr[mesh_id]); count = int(model.mesh_vertnum[mesh_id])
    vertices = model.mesh_vert[start:start+count].astype(float)
    address = int(model.mesh_graphadr[mesh_id])
    if count >= 10 and address >= 0:
        support_count = int(model.mesh_graph[address])
        first = address+2+support_count
        indices = model.mesh_graph[first:first+support_count]
        if support_count < 4 or len(indices)!=support_count or np.any(indices<0) or np.any(indices>=count):
            raise ValueError('invalid native collision graph')
        vertices = vertices[np.sort(indices)]
    return vertices


def compiled_body_vertices(model, geom_id):
    points = compiled_support(model, int(model.geom_dataid[geom_id]))
    q = model.geom_quat[geom_id]
    rotation = Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
    return points@rotation.T+model.geom_pos[geom_id]


def convex_subset(points, max_vertices=64, budget_m=.0002):
    """Bound directed distance from ALL source polytope vertices.

A convex hull of a subset lies inside its parent polytope. Distance to a
convex set is convex, so the maximum over parent vertices bounds its whole
polytope. This certifies only the parent proxy -> new proxy approximation,
not native CAD fidelity, continuous swept clearance or floating-point exactness.
"""
    points = np.unique(np.asarray(points),axis=0)
    if len(points)<=max_vertices:
        mesh = convex_mesh(points)
        return mesh, dict(parent_support_vertices=len(points),export_support_vertices=len(mesh.vertices),
                          parent_to_subset_vertex_max_m=0.,proxy_polytope_bound_pass=True,
                          native_CAD_error_certified=False)
    center = points.mean(0)
    _,_,basis = np.linalg.svd(points-center,full_matrices=False)
    directions = np.r_[np.eye(3),-np.eye(3),basis,-basis]
    chosen = list(np.unique(np.argmax(points@directions.T,axis=0)))
    while True:
        candidate = convex_mesh(points[chosen])
        distances = closest_distance_m(candidate,points)
        largest = int(np.argmax(distances)); error = float(distances[largest])
        if error<=budget_m or len(chosen)>=max_vertices:
            return candidate, dict(parent_support_vertices=len(points),export_support_vertices=len(candidate.vertices),
                parent_to_subset_vertex_max_m=error,proxy_polytope_bound_pass=error<=budget_m,
                numerical_coordinate_quantization_m=1e-10,budget_m=budget_m,
                native_CAD_error_certified=False)
        if largest in chosen:
            raise ValueError('convex subset distance stalled')
        chosen.append(largest)


def union_contains(points, hulls, tolerance_m=1e-8):
    """Finite material probes; internal faces of a decomposition are not gaps."""
    points = np.asarray(points);inside=np.zeros(len(points),bool)
    for hull in hulls:
        ids=np.flatnonzero(~inside & np.all(points>=hull.bounds[0]-tolerance_m,axis=1)
                          & np.all(points<=hull.bounds[1]+tolerance_m,axis=1))
        if len(ids):
            planes=ConvexHull(hull.vertices).equations
            inside[ids]=np.all(points[ids]@planes[:,:3].T+planes[:,3]<=tolerance_m,axis=1)
    return inside


def bounded_partition(points,max_vertices=64,budget_m=.0002,depth=0):
    hull,record=convex_subset(points,max_vertices,budget_m)
    record['partition_depth']=depth
    if record['proxy_polytope_bound_pass']:
        return [(hull,record)]
    if depth>=2:
        raise ValueError('fixed support partition budget exhausted: '+str(record))
    source=convex_mesh(points)
    axis=int(np.argmax(np.ptp(source.vertices,axis=0)))
    level=float(source.bounds[:,axis].mean())
    edges=source.edges_unique;dist=source.vertices[:,axis]-level
    crossing=edges[dist[edges[:,0]]*dist[edges[:,1]]<0]
    a,b=source.vertices[crossing[:,0]],source.vertices[crossing[:,1]]
    fraction=-dist[crossing[:,0]]/(dist[crossing[:,1]]-dist[crossing[:,0]])
    intersections=a+fraction[:,None]*(b-a)
    output=[]
    for sign in [-1,1]:
        clipped=np.r_[source.vertices[sign*dist>=0],intersections]
        children=bounded_partition(clipped,max_vertices,budget_m,depth+1)
        for _,child in children:
            child['partition_axis']=axis;child['partition_level_m']=level
            child['partition_parent_approximation_rejected']=record
        output.extend(children)
    return output
