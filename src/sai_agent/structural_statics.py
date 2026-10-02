"""SI section properties, point-load wrenches and unilateral static contacts.

These helpers do not provide an actuator model, joint stiffness, or certification.
"""
from __future__ import annotations

from itertools import combinations
from functools import lru_cache

import numpy as np
from scipy.optimize import linprog


def polygon_integrals(points):
    """Area, centroid and centroidal second moments for a simple polygon."""
    p = np.asarray(points, float)
    q = np.roll(p, -1, axis=0)
    cross = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
    if cross.sum() < 0:
        return polygon_integrals(p[::-1])
    area = cross.sum() / 2
    if area <= 0:
        raise ValueError("Nonpositive polygon area")
    centroid = ((p + q) * cross[:, None]).sum(0) / (6 * area)
    iu = ((p[:, 1]**2 + p[:, 1]*q[:, 1] + q[:, 1]**2)*cross).sum()/12
    iv = ((p[:, 0]**2 + p[:, 0]*q[:, 0] + q[:, 0]**2)*cross).sum()/12
    iuv = ((2*p[:, 0]*p[:, 1] + p[:, 0]*q[:, 1] + q[:, 0]*p[:, 1]
            + 2*q[:, 0]*q[:, 1])*cross).sum()/24
    return area, centroid, np.array([iu, iv, iuv])


def hollow_section(outer, inner):
    """Exact polygon subtraction; moments about the material centroid."""
    outer,inner=np.asarray(outer,float),np.asarray(inner,float)
    def convex_ccw(p):
        q=np.roll(p,-1,axis=0)
        signed=np.sum(p[:,0]*q[:,1]-q[:,0]*p[:,1])/2
        if signed<0:p=p[::-1]
        edges=np.roll(p,-1,axis=0)-p;next_edges=np.roll(edges,-1,axis=0)
        turns=edges[:,0]*next_edges[:,1]-edges[:,1]*next_edges[:,0]
        if np.any(turns<-1e-12):raise ValueError("Convex box section required")
        return p
    outer,inner=convex_ccw(outer),convex_ccw(inner)
    edges=np.roll(outer,-1,axis=0)-outer
    offsets=inner[:,None,:]-outer[None,:,:]
    crosses=edges[None,:,0]*offsets[:,:,1]-edges[None,:,1]*offsets[:,:,0]
    if np.any(crosses<=1e-12):raise ValueError("Inner polygon must be strictly inside outer polygon")
    ao, co, io = polygon_integrals(outer)
    ai, ci, ii = polygon_integrals(inner)
    area = ao-ai
    if area <= 0:
        raise ValueError("Inner section exceeds outer section")
    center = (ao*co-ai*ci)/area
    inertia = io-ii-np.array([area*center[1]**2, area*center[0]**2,
                             area*center[0]*center[1]])
    if min(inertia[:2])<=0 or inertia[0]*inertia[1]<=inertia[2]**2:
        raise ValueError("Section inertia is not positive definite")
    median = (np.asarray(outer)+np.asarray(inner))/2
    return {"area_m2": float(area), "centroid_uv_m": center.tolist(),
            "Iuu_m4": float(inertia[0]), "Ivv_m4": float(inertia[1]),
            "Iuv_m4": float(inertia[2]),
            "median_enclosed_area_m2": float(polygon_integrals(median)[0])}


def resultant(loads, origin):
    """Sum actual force and moment vectors at a specified world origin."""
    origin = np.asarray(origin, float)
    force, moment = np.zeros(3), np.zeros(3)
    for load in loads:
        f = np.asarray(load["force_world_N"], float)
        force += f
        moment += np.cross(np.asarray(load["position_world_m"])-origin, f)
        moment += np.asarray(load.get("moment_world_Nm", [0, 0, 0]), float)
    return force, moment


def normal_contacts(vertices, loads):
    """Find nonnegative vertical forces satisfying full gravity equilibrium.

    No foot is welded to the world and no arbitrary ground torque is allowed.
    This solver rejects horizontal forces and free yaw moments; frictional
    dynamics must be evaluated separately.
    """
    vertices = np.asarray(vertices, float)
    if np.ptp(vertices[:,2])>1e-8:
        return {"feasible":False,"reason":"Candidate soles are not on the common flat ground plane"}
    force, moment = resultant(loads, [0, 0, 0])
    if np.linalg.norm(force[:2]) > 1e-7 or abs(moment[2]) > 1e-7:
        return {"feasible": False, "reason": "Horizontal/frictional contact not modeled"}
    matrix = np.vstack([np.ones(len(vertices)), vertices[:, 1], -vertices[:, 0]])
    target = np.array([-force[2], -moment[0], -moment[1]])
    scale = max(abs(force[2]), 1)
    solution = linprog(np.zeros(len(vertices)), A_eq=matrix, b_eq=target/scale,
                       bounds=(0, None), method="highs")
    if not solution.success:
        return {"feasible": False, "reason": "No unilateral sole contact equilibrium",
                "required_total_CoP_xy_m": [float(moment[1]/force[2]),
                                             float(-moment[0]/force[2])]}
    values = solution.x*scale
    contacts = [{"position_world_m": p.tolist(), "force_world_N": [0, 0, float(f)]}
                for p, f in zip(vertices, values)]
    residual_force, residual_moment = resultant([*loads, *contacts], [0, 0, 0])
    return {"feasible": True, "contacts": contacts,
            "force_residual_N": residual_force.tolist(),
            "moment_residual_Nm": residual_moment.tolist()}


def contact_extreme_allocations(vertices, loads):
    """All basic feasible allocations of this finite gravity contact model.

    Three independent balance equations imply at most three nonzero vertex
    reactions at a basic solution. Taking every valid triplet covers extrema
    of the convex force/moment/stress envelope, without selecting a favorable
    left/right load split. This is not a compliant pressure distribution.
    """
    vertices=np.asarray(vertices,float)
    if np.ptp(vertices[:,2])>1e-8:
        raise ValueError("Contact extremes require the common flat ground plane")
    force,moment=resultant(loads,[0,0,0])
    if np.linalg.norm(force[:2])>1e-7 or abs(moment[2])>1e-7:
        raise ValueError("Only vertical gravity/contact loads are supported")
    scale=max(-force[2],1)
    a=np.vstack([np.ones(len(vertices)),vertices[:,1],-vertices[:,0]])
    target=np.array([-force[2],-moment[0],-moment[1]])/scale
    allocations={}
    for indices in combinations(range(len(vertices)),3):
        sub=a[:,indices]
        if abs(np.linalg.det(sub))<1e-12:continue
        weights=np.linalg.solve(sub,target)
        if np.min(weights)<-1e-11:continue
        candidate=np.zeros(len(vertices));candidate[list(indices)]=np.maximum(weights,0)
        if np.max(np.abs(a@candidate-target))>1e-10:continue
        key=tuple(np.round(candidate,10));allocations[key]=candidate*scale
    return np.asarray(list(allocations.values())).reshape(-1,len(vertices))


def _clip_greater(points, axis, value):
    out=[]
    for p,q in zip(points,np.roll(points,-1,axis=0)):
        ip,iq=p[axis]>=value,q[axis]>=value
        if ip:out.append(p)
        if ip!=iq:out.append(p+(q-p)*(value-p[axis])/(q[axis]-p[axis]))
    return np.asarray(out)


def _slice_width(points,axis,value):
    other=1-axis;crossings=[]
    for p,q in zip(points,np.roll(points,-1,axis=0)):
        if abs(q[axis]-p[axis])<1e-14:continue
        if min(p[axis],q[axis])<=value<=max(p[axis],q[axis]):
            crossings.append(p[other]+(q[other]-p[other])*(value-p[axis])/(q[axis]-p[axis]))
    return max(crossings)-min(crossings) if crossings else 0.0


@lru_cache(maxsize=256)
def _shear_coefficients(outer_tuple,inner_tuple):
    """Elementary VQ/Ib on 81 cuts and all polygon corner abscissae.

    Both wall strips at a hollow-section cut contribute to b. Values are
    sampled beam-theory profiles, not certified local/corner stress extrema.
    """
    outer,inner=np.asarray(outer_tuple),np.asarray(inner_tuple)
    section=hollow_section(outer,inner);out=[]
    for axis,inertia_key in ((0,'Ivv_m4'),(1,'Iuu_m4')):
        lo,hi=outer[:,axis].min(),outer[:,axis].max()
        cuts=np.unique(np.r_[np.linspace(lo+1e-8,hi-1e-8,81),
                             outer[:,axis],inner[:,axis]])
        peak=0.0
        for cut in cuts:
            b=_slice_width(outer,axis,cut)-_slice_width(inner,axis,cut)
            if b<=1e-12:continue
            q=0.0
            for sign,poly in ((1,outer),(-1,inner)):
                clipped=_clip_greater(poly,axis,cut)
                nxt=np.roll(clipped,-1,axis=0)
                signed_area=(np.sum(clipped[:,0]*nxt[:,1]-nxt[:,0]*clipped[:,1])/2
                             if len(clipped)>=3 else 0)
                if abs(signed_area)>1e-14:
                    area,center,_=polygon_integrals(clipped)
                    q+=sign*area*(center[axis]-section['centroid_uv_m'][axis])
            peak=max(peak,abs(q)/(section[inertia_key]*b))
        out.append(peak)
    return tuple(out)


def nominal_section_stress(section, outer, basis, force, moment, thickness, inner=None):
    """Elastic bending and sampled VQ/Ib plus thin-wall Bredt torsion.

    Local peaks, welds, bolts, bearing seats and local/global buckling are not
    resolved. Adding the component peaks bounds the sampled profiles only.
    """
    axial, u_axis, v_axis = np.asarray(basis, float)
    n, vu, vv = np.dot([axial, u_axis, v_axis], force)
    torque, mu, mv = np.dot([axial, u_axis, v_axis], moment)
    p = np.asarray(outer)-section["centroid_uv_m"]
    tensor = np.array([[section["Ivv_m4"], section["Iuv_m4"]],
                       [section["Iuv_m4"], section["Iuu_m4"]]])
    coefficients = np.linalg.solve(tensor, [-mv, mu])
    stress = n/section["area_m2"]+p@coefficients
    torsion = abs(torque)/(2*section["median_enclosed_area_m2"]*thickness)
    if inner is None:
        raise ValueError("Actual inner polygon required for shear stress")
    coefficients=_shear_coefficients(tuple(map(tuple,outer)),tuple(map(tuple,inner)))
    transverse=abs(vu)*coefficients[0]+abs(vv)*coefficients[1]
    sigma = float(np.abs(stress).max())
    return {"axial_force_N": float(n), "shear_uv_N": [float(vu), float(vv)],
            "bending_uv_Nm": [float(mu), float(mv)], "torsion_Nm": float(torque),
            "max_abs_normal_stress_Pa": sigma,
            "sampled_transverse_shear_coefficients_per_m2": list(coefficients),
            "shear_method":"VQ/Ib at 81 cuts plus polygon corner cuts, actual outer-minus-inner material width; Bredt torsion, summed component peaks. Local/bend/corner FEA excluded.",
            "shear_envelope_Pa": float(torsion+transverse),
            "equivalent_stress_envelope_Pa": float(np.hypot(sigma, np.sqrt(3)*(torsion+transverse)))}
