"""Local convex surface clusters for concave exterior CAD shells.

Convexifying a complete hollow body fills its motor openings. These small
surface clusters retain the openings approximately; exact BREP sweeps remain
the assembly authority. Cell size is a collision approximation, not tolerance.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull,QhullError
import trimesh


def surface_hulls(mesh_path,cell_m=.02):
    mesh=trimesh.load_mesh(mesh_path,process=False)
    vertices=np.asarray(mesh.vertices)*.001;triangles=vertices[np.asarray(mesh.faces)]
    bins=np.floor(triangles.mean(axis=1)/cell_m).astype(int)
    for key in np.unique(bins,axis=0):
        faces=triangles[np.all(bins==key,axis=1)];points=np.unique(faces.reshape(-1,3),axis=0)
        if len(points)<3:continue
        if np.linalg.matrix_rank(points-points.mean(axis=0),tol=1e-10)<3:
            normals=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]);normal=normals.sum(axis=0)
            if np.linalg.norm(normal)<1e-12:normal=normals[np.argmax(np.linalg.norm(normals,axis=1))]
            if np.linalg.norm(normal)<1e-12:continue
            normal=normal/np.linalg.norm(normal)*.00005
            points=np.vstack([points+normal,points-normal])
        try:hull=ConvexHull(points)
        except QhullError as exc:raise ValueError('Degenerate collision surface cluster') from exc
        if hull.volume<1e-15:continue
        yield trimesh.Trimesh(vertices=points,faces=hull.simplices,process=False)
