"""Actual hollow load-path members for the current Gorilla candidate.

All members have finite material walls. Section and centerline data travel
with their native control meshes so the statics cannot use a separate drawing.
"""
from __future__ import annotations

import numpy as np

from sai_agent.structural_statics import hollow_section


def _unit(v):
    v = np.asarray(v, float)
    return v/np.linalg.norm(v)


def _outline(width, depth, corner):
    w, d = width/2, depth/2
    return np.array([[-w+corner,-d],[w-corner,-d],[w,-d+corner],
                     [w,d-corner],[w-corner,d],[-w+corner,d],
                     [-w,d-corner],[-w,-d+corner]])


def hollow_member(g, name, body, path, width, depth, wall, palette,
                  *, distal_body=None, width_hint=(0,1,0)):
    path = np.asarray(path, float)
    corner = min(width, depth)*.16
    outer = _outline(width, depth, corner)
    inner = _outline(width-2*wall, depth-2*wall, corner-(2-np.sqrt(2))*wall)
    sections = hollow_section(outer, inner)
    vertices, frames = [], []
    for i, p in enumerate(path):
        tangent = _unit(path[min(i+1,len(path)-1)]-path[max(i-1,0)])
        u = np.asarray(width_hint, float)
        u = _unit(u-tangent*np.dot(tangent,u))
        v = _unit(np.cross(tangent,u))
        frames.append([tangent.tolist(),u.tolist(),v.tolist()])
        for profile in (outer,inner):
            vertices.extend(p+uv[0]*u+uv[1]*v for uv in profile)
    n, stride = len(outer), 2*len(outer)
    faces=[]
    for k in range(len(path)-1):
        for i in range(n):
            j=(i+1)%n; a=k*stride; b=(k+1)*stride
            faces.extend([[a+i,a+j,b+j,b+i], [a+n+j,a+n+i,b+n+i,b+n+j]])
    for k in (0,len(path)-1):
        a=k*stride
        for i in range(n):
            j=(i+1)%n
            f=[a+i,a+n+i,a+n+j,a+j]
            faces.append(f if k==0 else list(reversed(f)))
    g.part(name,body,vertices,faces,palette['dark'],True,
           "Finite-wall primary box-member candidate. Material, weld/flange/shaft joins and drive holding capacity remain unapproved.")
    g.parts[-1].update({"role":"primary_structure_candidate", "edge_bevel_m":0,
        "structural_member":{"id":name,"body":body,"distal_body":distal_body or body,
            "centerline_world_m":path.tolist(),"station_basis_axis_u_v":frames,
            "outer_polygon_uv_m":outer.tolist(),"inner_polygon_uv_m":inner.tolist(),
            "wall_m":wall,"section":sections,"perforations":False,
            "connections_status":"End annulus/mount envelope only; bolted/welded flange and bearing interfaces not certified",
            "screen_scope":"Nominal elastic section stress along this actual centerline; excludes bend/connection concentration and joint/drive stiffness."}})


def add_primary_structure(g, points, palette):
    """A branched spine/pelvis/limb path; no arbitrary filled torso wall."""
    root=np.array([0,0,1.66]); waist=np.array([0,0,1.74]);hub=np.array([-.08,0,2.29])
    hollow_member(g,"structure_waist_pedestal","pelvis",[root,waist],
                  .180,.180,.008,palette,distal_body='torso')
    hollow_member(g,"structure_spine_box","torso",[waist,[-.025,0,1.93],hub],
                  .260,.220,.008,palette)
    for side,s in (("left",1),("right",-1)):
        p={k:np.asarray(points[side+"_"+k],float) for k in ("shoulder","elbow","wrist","hip","knee","fold","ankle","foot")}
        hollow_member(g,side+"_structure_shoulder_crossmember","torso",[hub,p['shoulder']],
                      .140,.160,.006,palette,distal_body=side+"_upper_arm",width_hint=(0,0,1))
        hollow_member(g,side+"_structure_pelvis_crossmember","pelvis",[root,p['hip']],
                      .140,.180,.008,palette,distal_body=side+"_thigh",width_hint=(0,0,1))
        # The original white sleeve contains the mid-arm frame. The previous
        # straight rear strut ran outside that envelope all the way to the elbow.
        hollow_member(g,side+"_structure_upper_arm_box",side+"_upper_arm",
                      [p['shoulder'],[-.042,s*.640,2.035],p['elbow']],
                      .105,.090,.006,palette)
        hollow_member(g,side+"_structure_forearm_box",side+"_forearm",[p['elbow'],p['wrist']],
                      .105,.120,.006,palette)
        # Full primary Z members are replaced by the reviewed leg assembly
        # when present. This initial path is intentionally transparent in the
        # isolated structure views and is not an invisible strength proxy.
        for label,body,a,b,width,depth in (
            ('thigh','thigh',p['hip'],p['knee'],.145,.180),
            ('middle','middle_shank',p['knee'],p['fold'],.135,.160),
            ('distal','distal_shank',p['fold'],p['ankle'],.130,.145)):
            existing=[q for q in g.parts if q.get('structural_member',{}).get('body')==side+'_'+body]
            if not existing:
                hollow_member(g,side+'_structure_'+label+'_box',side+'_'+body,[a,b],width,depth,.008,palette)
        if not any(q.get('structural_member',{}).get('body')==side+'_foot' for q in g.parts):
            hollow_member(g,side+"_structure_ankle_sole_bridge",side+"_foot",
                          [p['ankle'],[-.04,s*.56,.12],[.12,s*.60,.060]],
                          .175,.090,.008,palette)
            hollow_member(g,side+"_structure_sole_rail",side+"_foot",
                          [[-.20,s*.60,.065],[.12,s*.60,.065],[.38,s*.60,.065]],
                          .230,.065,.006,palette)
    for part in g.parts:
        if part.get('structural_member'):
            part['structure_view_visible']=True
        elif part['role']=='visible_mechanism' and any(x in part['name'] for x in
                ('inner_barrel','wide_inner_bridge','support_cheek','bridge_shoulder','support_thrust')):
            part['structure_view_visible']=True
