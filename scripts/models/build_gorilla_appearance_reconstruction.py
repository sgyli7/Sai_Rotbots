#!/usr/bin/env python3
"""Reconstruct the sole Gorilla AA3 artwork as editable hard-surface geometry.

This appearance source has no physical approval or inferred hardware mass.
Pixel coordinates refer to the user's original 1280-square sheet; hidden depths
are explicit reconstruction choices, not measurements from calibrated cameras.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from build_gorilla_proportion_layout import Geometry as PrimitiveGeometry

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
SCALE = 2.65 / 516
CX = 325.5
GROUND = 603
PALETTE = {
    "ivory": [0.91, 0.88, 0.80, 1],
    "blue": [0.015, 0.57, 0.88, 1],
    "gold": [1.0, 0.64, 0.13, 1],
    "dark": [0.075, 0.08, 0.084, 1],
    "metal": [0.16, 0.17, 0.17, 1],
    "black": [0.018, 0.022, 0.026, 1],
}
IVORY, BLUE, GOLD, DARK, METAL, BLACK = (PALETTE[k] for k in ("ivory", "blue", "gold", "dark", "metal", "black"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def yz(px, py, rear=False):
    return np.array([(px - CX if rear else CX - px) * SCALE, (GROUND - py) * SCALE])


class Geometry(PrimitiveGeometry):
    """A named control mesh plus explicit surface finish parameters."""

    def part(self, name, body, vertices, faces, color, hardware=False, note=""):
        super().part(name, body, vertices, faces, color, hardware, note)
        part = self.parts[-1]
        part.pop("shell_density_kg_m3")
        part.pop("shell_thickness_m")
        part.pop("mass_basis_note")
        part.update({
            "role": "visible_mechanism" if hardware else "armor_surface",
            "physical_mass_assigned": False,
            "reconstruction_note": note or "Visible shape reconstructed from the sole artwork; hidden depth is a candidate.",
            "edge_bevel_m": 0,
            "bevel_segments": 3,
            "surface_shading": "mechanical_smooth" if hardware else "flat_weighted_normals",
        })

    def cover(self,name,body,vertices,surface_faces,color,thickness=.007,
              reference_closed_faces=None,sharp_outer_edges=None,note=""):
        """A hollow armor cover: outer skin, inner skin and boundary returns.

        Openings remain openings. Only the thin material is a closed volume;
        the assembly cavity is never filled by a colored solid. Thickness is
        an editable appearance construction parameter, not a strength result.
        """
        source=np.asarray(vertices,float)
        faces=[list(f) for f in surface_faces]
        if reference_closed_faces:
            volume=sum(np.dot(source[f[0]],np.cross(source[f[i]],source[f[i+1]]))/6
                for f in reference_closed_faces for i in range(1,len(f)-1))
            if volume<0:faces=[list(reversed(f)) for f in faces]
        used=sorted({v for f in faces for v in f});mapping={v:i for i,v in enumerate(used)}
        outside=source[used];faces=[[mapping[v] for v in f] for f in faces]
        normals=np.zeros_like(outside)
        for f in faces:
            area=sum((np.cross(outside[f[i]]-outside[f[0]],outside[f[i+1]]-outside[f[0]])
                for i in range(1,len(f)-1)),start=np.zeros(3))
            for v in f:normals[v]+=area
        lengths=np.linalg.norm(normals,axis=1)
        if np.any(lengths<1e-12):raise ValueError("Undefined armor surface normal: "+name)
        normals/=lengths[:,None]
        t=np.full(len(outside),thickness) if np.isscalar(thickness) else np.asarray(thickness)[used]
        inside=outside-normals*t[:,None];n=len(outside)
        edge_counts={};directions={}
        for f in faces:
            for a,b in zip(f,f[1:]+f[:1]):
                key=tuple(sorted((a,b)));edge_counts[key]=edge_counts.get(key,0)+1;directions[key]=(a,b)
        if any(v>2 for v in edge_counts.values()):raise ValueError("Branching armor surface: "+name)
        boundary=[directions[k] for k,count in edge_counts.items() if count==1]
        material_faces=faces+[[n+i for i in reversed(f)] for f in faces]
        material_faces += [[b,a,a+n,b+n] for a,b in boundary]
        self.part(name,body,np.concatenate((outside,inside)),material_faces,color,note=note)
        sharp=[]
        for a,b in sharp_outer_edges or []:
            if a in mapping and b in mapping:
                a,b=mapping[a],mapping[b];sharp.extend([[a,b],[a+n,b+n]])
        sharp.extend([[a,b] for a,b in boundary]);sharp.extend([[a+n,b+n] for a,b in boundary])
        self.parts[-1].update({"role":"armor_cover","surface_shading":"curved_hard_surface",
            "edge_bevel_m":0,"auto_smooth_angle_deg":180,
            "sharp_surface_edge_pairs":sharp,"cover_construction":"outer_skin_inner_skin_boundary_returns_open_cavity",
            "appearance_skin_thickness_range_m":[float(t.min()),float(t.max())],
            "skin_thickness_is_manufacturing_spec":False,"open_boundary_edge_count":len(boundary),
            "reconstruction_note":note or "Thin armor cover around an open assembly cavity; hidden return/thickness remain appearance candidates, not load-bearing evidence."})

    def panel(self, name, body, outline, front, depth, color, bevel=.006, rear=False, camber=.012):
        """A shaped plate from an artwork outline, with separately editable rim.

        outline uses original full-sheet FRONT pixels. rear=True reverses lateral
        coordinates and extrusion. Front can be a scalar or f(y,z) surface depth.
        The source is genuine three-dimensional geometry, with no image texture.
        """
        q = np.array([yz(x, z, rear) for x, z in outline])
        center = q.mean(axis=0)
        inward = center + .94 * (q - center)
        sign = -1 if rear else 1
        def position(p, inset=0):
            y, z = p
            x = front(y, z) if callable(front) else front
            return [x + sign * inset, y, z]
        v = [position(p) for p in q]
        v += [position(p, camber) for p in inward]
        v += [position(p, -depth) for p in q]
        n = len(q)
        v.append(position(center, camber))
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces.extend([[i, j, n+j, n+i], [n+i, n+j, 3*n], [i, 2*n+i, 2*n+j, j]])
        faces.append(list(reversed(range(2*n, 3*n))))
        self.part(name, body, v, faces, color)
        self.parts[-1]["edge_bevel_m"] = bevel
        self.parts[-1]["reference_outline_px"] = outline

    def tube(self, name, body, points, radius, color, n=10):
        # Closed constant-section polylines for seams, conduits and trim.
        for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
            self.link(f"{name}_{i:02}", body, a, b, [(0, radius, radius), (1, radius, radius)], color, True, n)
            self.parts[-1]["edge_bevel_m"] = 0

    def seam(self, name, body, pixels, surface, radius=.0013, color=METAL, rear=False):
        line=[]
        for px, py in pixels:
            y,z=yz(px,py,rear)
            x=surface(y,z) if callable(surface) else surface
            line.append([x+(-.003 if rear else .003),y,z])
        self.tube(name,body,line,radius,color,8)

    def bolt(self, name, body, pos, axis=(1,0,0), radius=.006, color=METAL):
        a=np.asarray(pos,float);d=np.asarray(axis,float);d/=np.linalg.norm(d)
        self.link(name,body,a-d*.002,a+d*.002,[(0,radius,radius),(1,radius,radius)],color,True,12)
        self.parts[-1]["edge_bevel_m"] = .0006

    def rounded_rect(self, name, body, center, width, height, thickness, radius, color, rear=False):
        # The rectangle's broad face is in YZ, with actual rounded corners.
        cx,cy,cz=center
        p=[]
        for sy,sz,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
            # Profile generated clockwise in YZ.
            yc=cy+sy*(width/2-radius);zc=cz+sz*(height/2-radius)
            for a in np.linspace(start,start+90,7):
                t=math.radians(a)
                p.append([yc+radius*math.cos(t),zc+radius*math.sin(t)])
        n=len(p);sgn=-1 if rear else 1
        v=[[cx,y,z] for y,z in p]+[[cx-sgn*thickness,y,z] for y,z in p]
        f=[list(reversed(range(n))),list(range(n,2*n))]
        f += [[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        self.part(name,body,v,f,color,True)
        self.parts[-1]["edge_bevel_m"] = .0015


CHEST_CURVE=PchipInterpolator(
    (GROUND-np.array([274,271,248,218,184,162,136,120,106,96,87,85]))*SCALE,
    (971-np.array([918,907,888,871,861,855,876,891,918,949,986,1010]))*SCALE)
CHEST_BACK_CURVE=PchipInterpolator(
    (GROUND-np.array([259,254,232,202,165,135,111,93,85]))*SCALE,
    (971-np.array([1028,1036,1048,1055,1058,1057,1041,1025,1010]))*SCALE)
FRONT_SHIELD_CONFIG={}


def chest_front(y,z):
    x=float(CHEST_CURVE(z))
    py=GROUND-z/SCALE
    if FRONT_SHIELD_CONFIG and py>=FRONT_SHIELD_CONFIG["main_face_start_v"]:
        anchors=FRONT_SHIELD_CONFIG["center_depth_candidate_vx_m"]
        x=float(np.interp(py,[p[0] for p in anchors],[p[1] for p in anchors]))
    return x-.020*(abs(y)/.37)**2


def chest_back(y,z):
    return float(CHEST_BACK_CURVE(z))+.018*(abs(y)/.4)**2


def mirror_outline(outline):
    return [[2*CX-x,y] for x,y in reversed(outline)]


def polygon_span(outline, scan_y):
    crossings=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        if abs(a[1]-b[1])<1e-9:
            if abs(scan_y-a[1])<1e-8:crossings.extend([a[0],b[0]])
        elif min(a[1],b[1])-1e-8<=scan_y<=max(a[1],b[1])+1e-8:
            crossings.append(a[0]+(b[0]-a[0])*(scan_y-a[1])/(b[1]-a[1]))
    if not crossings:raise ValueError(f"No contour at {scan_y}")
    return min(crossings),max(crossings)


def triangulate_outline(points):
    """Ear clipping retains the original yellow guard's bottom notch."""
    q=np.asarray(points,float);remaining=list(range(len(q)));triangles=[]
    orient=np.sign(sum(q[i,0]*q[(i+1)%len(q),1]-q[(i+1)%len(q),0]*q[i,1] for i in range(len(q))))
    while len(remaining)>3:
        for k,i in enumerate(remaining):
            a,b=remaining[k-1],remaining[(k+1)%len(remaining)]
            u,v=q[i]-q[a],q[b]-q[i]
            if orient*(u[0]*v[1]-u[1]*v[0])<=1e-12:continue
            mat=np.column_stack((q[i]-q[a],q[b]-q[a]));blocked=False
            for j in remaining:
                if j in (a,i,b):continue
                uv=np.linalg.solve(mat,q[j]-q[a])
                if min(uv[0],uv[1],1-uv.sum())>=-1e-9:blocked=True;break
            if not blocked:
                triangles.append([a,i,b]);remaining.pop(k);break
        else:raise ValueError("Cannot triangulate reference outline")
    triangles.append(remaining);return triangles


def fitted_guard(g,name,body,outline,front,back,color,rear=False,outer_bevel=.007,inset_height=.005,inset_ratio=.90,open_cover=False):
    """A genuinely three-dimensional guard, preserving a concave rim."""
    q=np.asarray([yz(x,z,rear) for x,z in outline]);center=q.mean(0)
    inset=center+inset_ratio*(q-center);sgn=-1 if rear else 1;n=len(q)
    parameters=[[y,z,1.,-sgn*outer_bevel] for y,z in q]
    parameters += [[y,z,1.,sgn*inset_height] for y,z in inset]
    parameters += [[y,z,0.,0.] for y,z in q]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([[i,j,n+j,n+i],[i,2*n+i,2*n+j,j]])
    faces += [[n+i for i in t] for t in triangulate_outline(inset)]
    faces += [list(reversed([2*n+i for i in t])) for t in triangulate_outline(q)]
    faces=[[f[0],f[i],f[i+1]] for f in faces for i in range(1,len(f)-1)]
    # Refinement happens in the common YZ/layer parameterization before the
    # depth functions are evaluated. Large ear triangles on a curved surface
    # otherwise make star-shaped facets and differ under mirrored diagonals.
    for _ in range(3):
        midpoints={};refined=[]
        def midpoint(a,b):
            edge=tuple(sorted((a,b)))
            if edge not in midpoints:
                midpoints[edge]=len(parameters)
                parameters.append(((np.asarray(parameters[a])+np.asarray(parameters[b]))/2).tolist())
            return midpoints[edge]
        for a,b,c in faces:
            ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
            refined.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
        faces=refined
    vertices=[]
    for y,z,blend,offset in parameters:
        vertices.append([(1-blend)*back(y,z)+blend*front(y,z)+offset,y,z])
    if open_cover:
        outside=[f for f in faces if not all(parameters[v][2]<1e-8 for v in f)]
        g.cover(name,body,vertices,outside,color,.006,faces)
    else:g.part(name,body,vertices,faces,color)
    g.parts[-1].update({"edge_bevel_m":0,"surface_shading":"curved_hard_surface","reference_outline_px":outline,
        "reconstruction_note":"Observed visible region retained as a closed candidate surface with native rim; curved depth and hidden closure are separately inferred."})


def annular_frame_cover(g,name,body,outer,opening,sign,front,back,color,skin):
    """Thin front annulus and outer returns, with a genuine through opening."""
    qo=np.array([yz(u,v) for u,v in outer]);qi=np.array([yz(u,v) for u,v in opening])
    center=qi.mean(axis=0)
    angles=sorted(set([*np.linspace(0,2*math.pi,64,endpoint=False),
        *[math.atan2(*(p-center)[::-1])%(2*math.pi) for p in np.concatenate((qo,qi))]]))
    def radius_point(poly,a):
        d=np.array([math.cos(a),math.sin(a)]);hits=[]
        for p,q in zip(poly,np.roll(poly,-1,axis=0)):
            mat=np.column_stack((d,p-q))
            if abs(np.linalg.det(mat))<1e-13:continue
            t,u=np.linalg.solve(mat,p-center)
            if t>0 and -1e-8<=u<=1+1e-8:hits.append(t)
        if not hits:raise ValueError("Opening/frame radial contour failed: "+name)
        return center+min(hits)*d
    out=[radius_point(qo,a) for a in angles];inside=[radius_point(qi,a) for a in angles]
    n=len(out);vertices=[]
    for contour,surface in ((out,front),(inside,front),(out,back)):
        vertices.extend([[surface(sign*y,z),sign*y,z] for y,z in contour])
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([[i,j,n+j,n+i],[j,i,2*n+i,2*n+j]])
    if sign<0:faces=[list(reversed(f)) for f in faces]
    g.cover(name,body,vertices,faces,color,skin)
    g.parts[-1].update({"reference_front_outer_outline_px":outer,
        "reference_front_through_opening_px":opening,
        "opening_is_real_geometry":True,
        "reconstruction_note":"Thin annular front and outer housing return. No front/back filled plate across the aperture. Skin/depth are editable candidates; no cooling or material capacity approval."})


def fitted_radiator(g,side,sign,profiles):
    """Reference-shaped open intake and provisional turning plenum.

    This geometry reserves a real throat. The side outlet terminates in the
    unverified body bay; fan/core/heat budget and full exhaust are still open.
    """
    side_mount=profiles["left"]["side_vent_ivory_mount"]
    def surface(y,z,rear=False):
        py=np.clip(GROUND-z/SCALE,161.15,222.85)
        a,b=polygon_span(side_mount,float(py))
        return (971-(b if rear else a))*SCALE+(.008 if rear else -.009)
    front_profiles=profiles["front"]
    annular_frame_cover(g,side+"_radiator_ivory_socket","torso",
        front_profiles["left_vent_ivory_mount"],front_profiles["left_vent_gold_bezel"],sign,
        surface,lambda y,z:surface(y,z,True),IVORY,.006)
    annular_frame_cover(g,side+"_radiator_gold_trim","torso",
        front_profiles["left_vent_gold_bezel"],front_profiles["left_vent_black_opening"],sign,
        lambda y,z:surface(y,z)+.013,lambda y,z:surface(y,z)+.005,GOLD,.002)
    aperture=front_profiles["left_vent_black_opening"]
    vertices=[];n=len(aperture)
    for depth in (.012,-.060):
        for u,py in aperture:
            y,z=yz(u,py);y*=sign
            vertices.append([surface(y,z)+depth,y,z])
    wall=[]
    for i in range(n):
        j=(i+1)%n;wall.append([i,j,n+j,n+i])
    if sign<0:wall=[list(reversed(f)) for f in wall]
    g.cover(side+"_radiator_black_well","torso",vertices,wall,BLACK,.003)
    g.parts[-1].update({"opening_is_real_geometry":True,"reference_front_opening_px":aperture,
        "reconstruction_note":"Open-front/open-back dark throat, 72mm candidate axial depth. No black plate across the intake. Full thermal and airflow performance remains unverified."})
    # A rear wall belongs to an actual turning chamber, with an open outside
    # port. It shades the intake while air space can turn through the side;
    # it does not stand in for a released fan, core or complete exhaust route.
    q=np.array([yz(u,v) for u,v in aperture]);yc,zc=q.mean(axis=0)
    y0,y1=q[:,0].min()-.012,q[:,0].max()+.012
    z0,z1=q[:,1].min()-.010,q[:,1].max()+.010
    xf=surface(sign*yc,zc)-.053;xb=xf-.075
    chamber=[[x,sign*y,z] for x in (xf,xb) for y,z in ((y0,z0),(y1,z0),(y1,z1),(y0,z1))]
    chamber_faces=[[4,5,6,7],[0,4,7,3],[1,5,4,0],[3,7,6,2]]
    if sign<0:chamber_faces=[list(reversed(f)) for f in chamber_faces]
    g.cover(side+"_radiator_turning_plenum","torso",chamber,chamber_faces,BLACK,.004)
    g.parts[-1].update({"open_front_and_outside_port":True,
        "outlet_scope":"Provisional outlet into the body bay; external exhaust, obstructions, sealing and recirculation remain unverified red-line items.",
        "reconstruction_note":"Thin three-sided turning plenum plus rear wall, with actual intake and outside-side opening. This is a duct-space candidate, not a thermal release or decorative closed backplate."})
    for i,py in enumerate(np.linspace(167.2,202.3,11)):
        a,b=polygon_span(profiles["front"]["left_vent_black_opening"],float(py))
        y=sign*(CX-(a+b)/2)*SCALE;z=(GROUND-py)*SCALE
        g.box(side+f"_radiator_louver_{i:02}","torso",[surface(y,z)+.024,y,z],
            [.005,(b-a-2.4)*SCALE,.0038],[.29,.29,.25,1],True)
        g.parts[-1]["edge_bevel_m"] = .0008
    for i,(px,py) in enumerate(((253,165),(271,167),(254,204),(269,203))):
        y=sign*(CX-px)*SCALE;z=(GROUND-py)*SCALE
        g.bolt(side+f"_vent_fastener_{i}","torso",[surface(y,z)+.023,y,z],radius=.003)


def edge_u_at_v(edge, py):
    """Read a sampled artwork crease; endpoint continuation is an inference."""
    ordered=sorted(edge,key=lambda p:p[1])
    return float(np.interp(py,[p[1] for p in ordered],[p[0] for p in ordered]))


def dual_view_shell(g,name,body,front_outline,side_outline,color,sign=1,steps=15,
                    front_feature_edges=None,facet_mode=None,shell_sectors=None):
    """A wraparound shell constrained by front and left silhouettes.

    The cross section has broad planes with curved/chamfered transitions. This
    changes the geometry type, rather than thickening a two-dimensional plate.
    Side art is uncalibrated and therefore remains an appearance depth choice.
    """
    # FRONT determines visible height. Intersecting two uncalibrated view
    # ranges previously cut off shoulder/arm overlap and the shank's top.
    lower=min(p[1] for p in front_outline)+.15
    upper=max(p[1] for p in front_outline)-.15
    side_lo=min(p[1] for p in side_outline)+.15
    side_hi=max(p[1] for p in side_outline)-.15
    profile=[(1,-.58),(1,.58),(.82,.87),(.50,1),(-.54,1),(-.91,.77),(-1,.35),
             (-1,-.35),(-.91,-.77),(-.54,-1),(.50,-1),(.82,-.87)]
    vertices=[]
    samples=sorted(set([*np.linspace(lower,upper,steps),
        *[p[1] for p in front_outline if lower<p[1]<upper]]))
    for py in samples:
        fa,fb=polygon_span(front_outline,float(py))
        sa,sb=polygon_span(side_outline,float(np.clip(py,side_lo,side_hi)))
        y0,y1=(CX-fb)*SCALE,(CX-fa)*SCALE
        x0,x1=(971-sb)*SCALE,(971-sa)*SCALE
        cy,ry=(y0+y1)/2,max((y1-y0)/2,.003)
        cx,rx=(x0+x1)/2,max((x1-x0)/2,.004)
        if facet_mode:
            width=fb-fa
            if facet_mode in ("forearm","thigh"):
                first,second=(edge_u_at_v(e,py) for e in front_feature_edges)
            elif facet_mode=="middle_shank":
                first=fa+.14*width;second=edge_u_at_v(front_feature_edges[0],py)
            else:
                first=fa+.14*width;second=edge_u_at_v(front_feature_edges[0],py)
            # Creases may continue into occluded/narrow terminal regions. Keep
            # them ordered within the observed outline without zero-area rims.
            first=float(np.clip(first,fa+.12*width,fb-.35*width))
            second=float(np.clip(second,first+.18*width,fb-.12*width))
            ya=(CX-first)*SCALE;yb=(CX-second)*SCALE
            band=min(.012,.035*(y1-y0))
            xf,xr=x1,x0;depth=max(xf-xr,.008)
            front_drop=min(.018,.065*depth)
            ring=[(xf-.30*depth,y1),(xf-front_drop,ya+band),(xf,ya),
                  (xf-.007*min(1,depth/.16),yb),
                  (xf-front_drop-.007*min(1,depth/.16),yb-band),
                  (xf-.31*depth,y0),(xf-.62*depth,y0),
                  (xr+.12*depth,y0+.10*(y1-y0)),(xr,y0+.32*(y1-y0)),
                  (xr,y1-.32*(y1-y0)),(xr+.12*depth,y1-.10*(y1-y0)),
                  (xf-.62*depth,y1)]
            vertices.extend([[x,sign*y,(GROUND-py)*SCALE] for x,y in ring])
        else:
            for xx,yy in profile:vertices.append([cx+rx*xx,sign*(cy+ry*yy),(GROUND-py)*SCALE])
    n=len(profile);steps=len(samples);faces=[list(reversed(range(n)))]
    for k in range(steps-1):
        for i in range(n):
            j=(i+1)%n;faces.append([k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i])
    faces.append(list(range((steps-1)*n,steps*n)))
    if shell_sectors is not None:sector=shell_sectors
    elif facet_mode=="deltoid":sector=[0,1,2,3,4,10,11]
    elif facet_mode=="white_shoulder":sector=[0,1,2,3,4,5,10,11]
    elif "ivory" in name:sector=[0,1,2,3,9,10,11]
    elif facet_mode=="middle_shank":sector=[0,1,2,3,4,5,9,10,11]
    else:sector=list(range(n))
    outer=[f for k in range(steps-1) for i in sector
        for f in [[k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i]]]
    sharp_rings=[1,2,3,4,6,8,9,11] if facet_mode else []
    sharp_edges=[[k*n+i,(k+1)*n+i] for k in range(steps-1) for i in sharp_rings]
    thickness=[]
    for k in range(steps):
        ring=np.asarray(vertices[k*n:(k+1)*n]);span=ring.ptp(axis=0) if hasattr(ring,"ptp") else np.ptp(ring,axis=0)
        wall=max(.0007,min(.007,.20*min(span[:2])))
        thickness.extend([wall]*n)
    g.cover(name,body,vertices,outer,color,thickness,faces,sharp_edges)
    g.parts[-1].update({"edge_bevel_m":0,"surface_shading":"curved_hard_surface",
        "auto_smooth_angle_deg":180 if facet_mode else 50,
        "ring_vertex_count":n,
        "reference_front_outline_px":front_outline,"reference_left_outline_px":side_outline,
        "reference_front_feature_edges_px":front_feature_edges or [],
        "front_facet_mode":facet_mode,
        "front_height_preserved":True,"left_depth_endpoint_continuation":"clamped, unobserved where outside LEFT outline height",
        "reconstruction_note":"Full FRONT contour retained with part-specific broad face bands. This is a thin open armor cover around mechanisms, not a filled colored volume. LEFT depth/hidden returns are uncalibrated candidates."})


def shoulder_sweep(g,side,sign,profiles):
    """An arched saddle, fitted to the observed SIDE ribbon as an assembly.

    The previous seven generic sections pinched into pointed folded tabs.
    Visible outer/inner blue boundaries now describe one continuous open
    ribbon above the shoulder guard. Lateral depth is still a candidate.
    """
    reference=profiles["front"]["left_blue_shoulder_sweep"]
    outer=np.array([[907,147],[925,131],[954,112],[989,101],[1008,98],
                    [1020,110],[1030,132],[1027,145],[1018,150]],float)
    inner=np.array([[909,161],[925,158],[942,143],[969,129],[995,123],
                    [1008,131],[1018,150]],float)
    def sampled(points):
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        arc/=arc[-1]
        return PchipInterpolator(arc,points,axis=0)
    upper,lower=sampled(outer),sampled(inner)
    rows=48;across=[0,.10,.24,.55,.88,1.];vertices=[]
    for t in np.linspace(0,.991,rows):
        a,b=upper(t),lower(t)
        for w in across:
            uv=(1-w)*a+w*b;u,py=uv
            fa,fb=polygon_span(reference,float(np.clip(py,101.2,154.8)))
            lateral=(CX-fa)*SCALE
            # The aft saddle is partly hidden in FRONT and has its own rear
            # span. Do not clamp that rear continuation to the front notch.
            aft=float(np.clip((u-990)/30,0,1))
            lateral=(1-aft)*lateral+aft*max(lateral,.515)
            lateral-=.018*math.sin(math.pi*w)+.008*w
            vertices.append([(971-u)*SCALE,sign*lateral,(GROUND-py)*SCALE])
    n=len(across);faces=[]
    for k in range(rows-1):
        for i in range(n-1):faces.append([k*n+i,k*n+i+1,(k+1)*n+i+1,(k+1)*n+i])
    if sign<0:faces=[list(reversed(f)) for f in faces]
    g.cover(side+"_blue_continuous_shoulder_sweep","torso",vertices,faces,BLUE,.006,
        sharp_outer_edges=[[k*n+2,(k+1)*n+2] for k in range(rows-1)])
    g.parts[-1].update({"reference_left_outer_ribbon_uv":outer.tolist(),
        "reference_left_inner_ribbon_uv":inner.tolist(),
        "depth_candidate_note":"Observed SIDE blue ribbon; lateral frontage and aft hidden width are unmeasured appearance candidates. Paired arc interpolation does not assert hardware clearance.",
        "reconstruction_note":"Continuous open arched blue saddle with thin material and real inner rim, above the separate white shoulder guard and dark housing. No filled blue pad."})
    # A saddle also has a broad upper return toward the hood, not just the
    # SIDE ribbon. Keep this real material separate from the empty joint bay.
    return_vertices=[];return_faces=[]
    for k in range(rows):
        p=np.asarray(vertices[k*n])
        inner_y=max(.265,abs(p[1])-.18)
        for w in (0,.25,.72,1):
            return_vertices.append([p[0]-.015*w,
                sign*((1-w)*abs(p[1])+w*inner_y),p[2]+.008*math.sin(math.pi*w)-.009*w])
    for k in range(rows-1):
        for i in range(3):return_faces.append([4*k+i,4*(k+1)+i,4*(k+1)+i+1,4*k+i+1])
    if sign<0:return_faces=[list(reversed(f)) for f in return_faces]
    g.cover(side+"_blue_shoulder_upper_return","torso",return_vertices,return_faces,BLUE,.006)
    g.parts[-1]["reconstruction_note"]="Broad curved saddle return toward the hood. Outer arc follows the SIDE ribbon; lateral inner return and 6mm skin are unmeasured candidates, with the joint bay open."
    rear_visible=[[207,725],[222,720],[239,716],[243,721],[249,735],
                  [254,746],[258,756],[256,763],[251,766],[234,763],
                  [224,751],[207,741],[202,735],[203,730]]
    rear_outline=[[u,v-612] for u,v in rear_visible]
    if sign>0:rear_outline=mirror_outline(rear_outline)
    def aft(y,z):
        py=float(np.clip(GROUND-z/SCALE,98.2,160.8))
        a,b=polygon_span(profiles["left"]["shoulder_blue_sweep_visible"],py)
        return (971-b)*SCALE-.009
    fitted_guard(g,side+"_blue_rear_shoulder_guard","torso",rear_outline,aft,
        lambda y,z:aft(y,z)+.045,BLUE,rear=True,outer_bevel=.003,
        inset_height=.002,inset_ratio=.92,open_cover=True)
    g.parts[-1].update({"reference_rear_visible_outline_global_uv":rear_visible,
        "reference_outline_uncertainty_px":4,
        "reconstruction_note":"Observed REAR swept blue wide face, previously missing from the ribbon. Hidden depth and local return follow an uncalibrated SIDE envelope; thin armor, not a filled shoulder block."})
    # The front diagonal wing is its own shallow cover over the saddle end.
    observed_fold=[[215,121],[250,128],[273,144]]
    def wing_surface(y,z):
        u=CX-abs(y)/SCALE;py=GROUND-z/SCALE
        fold_v=float(np.interp(u,[p[0] for p in observed_fold],[p[1] for p in observed_fold]))
        fold_x=float(np.interp(u,[215,250,273],[.135,.20,.325]))
        return fold_x+(.012 if py<fold_v else .004)*(py-fold_v)
    patch_cover(g,side+"_blue_shoulder_diagonal_front_wing","torso",reference,sign,
        wing_surface,BLUE,.006,feature_edge=observed_fold)
    g.parts[-1].update({"reference_front_broad_fold_uv":observed_fold,
        "depth_candidate_note":"Two broad front planes meet along the original diagonal fold. X anchors and plane slopes are appearance depth candidates inside the same hood/shoulder assembly, not calibrated dimensions."})


def shoulder_guard_assembly(g,side,sign,profiles,shape):
    """A rounded open guard and its distinct hollow dark bearing seat.

    FRONT visible blue occlusion is not the hidden white shell outline. This
    reconstructs a curved cover behind the outer blue guard, instead of using
    that occlusion to collapse a generic ring into a pointed white cap.
    """
    visible=(shape["observed_background_or_dark_mechanism_outer_arc"]["points_uv"]+
        list(reversed(shape["observed_outer_blue_occlusion_edge"]["points_uv"]))[1:-1])
    hidden_outer=np.array([[203,126],[190,134],[180,145],[176,158],
                           [179,171],[186,183],[195,193],[201,199]],float)
    hidden_u=PchipInterpolator(hidden_outer[:,1],hidden_outer[:,0])
    side_front=np.array(shape["white_shoulder_left_visible_relation"]["observed_open_white_arc_uv"],float)
    side_rear=np.array([[993,132],[1004,135],[1016,145],[1022,170],
                        [1015,187],[982,198]],float)
    leading=PchipInterpolator(side_front[:,1],side_front[:,0])
    trailing=PchipInterpolator(side_rear[:,1],side_rear[:,0])
    rows=42;n=64;vertices=[];thickness=[]
    for py in np.linspace(126.3,198.5,rows):
        fa,fb=polygon_span(visible,float(py))
        outer=min(fa,float(hidden_u(py)))
        y0,y1=(CX-fb)*SCALE,(CX-outer)*SCALE
        cy,ry=(y0+y1)/2,max((y1-y0)/2,.004)
        # Six-pixel discrepancy in the two artwork heights is not a measured
        # deformation; this explicit range pairing keeps the SIDE open arc.
        side_v=132+(py-126)*(66/73)
        x0,x1=(971-float(trailing(side_v)))*SCALE,(971-float(leading(side_v)))*SCALE
        cx,rx=(x0+x1)/2,max((x1-x0)/2,.004)
        for i in range(n):
            a=2*math.pi*i/n;c,s=math.cos(a),math.sin(a)
            # Broad soft face with rounded perimeter, rather than a repeated
            # angular prism. Blue armor supplies the visible outer occlusion.
            x=cx+rx*math.copysign(abs(c)**.72,c)
            vertices.append([x,sign*(cy+ry*s),(GROUND-py)*SCALE])
            thickness.append(max(.0008,min(.006,.16*min(rx,ry))))
    closed=[list(reversed(range(n)))]
    surface=[]
    for k in range(rows-1):
        for i in range(n):
            q=[k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i]
            closed.append(q);surface.append(q)
    closed.append(list(range((rows-1)*n,rows*n)))
    g.cover(side+"_ivory_shoulder_cap",side+"_upper_arm",vertices,surface,IVORY,thickness,closed)
    g.parts[-1].update({"visible_region_source":"robots/gorilla_v0_1/source/appearance_c_front_shape_constraints.json",
        "reference_front_visible_outline_px":visible,
        "reference_left_visible_open_arc_px":side_front.tolist(),
        "hidden_front_outer_continuation_candidate_uv":hidden_outer.tolist(),
        "hidden_left_rear_continuation_candidate_uv":side_rear.tolist(),
        "view_height_pairing_candidate":"FRONT v126-199 paired with LEFT v132-198; uncalibrated artwork pose/camera discrepancy, not a measured physical transform.",
        "reconstruction_note":"Rounded thin shoulder cover with top/bottom openings behind the separate blue guard. Visible arcs are observed; hidden outer continuation, depth, thickness and range pairing are candidates. No strength or appearance acceptance."})
    # The upper shoulder needs a real dark annulus under the saddle; an empty
    # crown window or dark full wall cannot reproduce the original assembly.
    center=np.array([-.102,sign*.495,2.292])
    angles=np.linspace(math.radians(20),math.radians(155),40)
    v=[]
    for y in (-.047,.047):
        for inside in (False,True):
            rx,rz=(.209,.185) if not inside else (.177,.153)
            for a in angles:v.append([center[0]+rx*math.cos(a),center[1]+sign*y,
                center[2]+rz*math.sin(a)])
    count=len(angles);f=[]
    for i in range(count-1):
        j=i+1
        f.extend([[i,j,2*count+j,2*count+i],
                  [count+j,count+i,3*count+i,3*count+j],
                  [j,i,count+i,count+j],
                  [2*count+i,2*count+j,3*count+j,3*count+i]])
    f.extend([[0,2*count,3*count,count],
              [count-1,2*count-1,4*count-1,3*count-1]])
    g.part(side+"_shoulder_open_bearing_seat",side+"_upper_arm",v,f,DARK,True,
        "Separate hollow open shoulder housing under the curved blue saddle; appearance space only, not an identified actuator or certified load-bearing housing.")


def patch_cover(g,name,body,outline,sign,surface,color,skin=.007,feature_edge=None,left_clip=None):
    samples=sorted(set([*np.linspace(min(p[1] for p in outline)+.12,max(p[1] for p in outline)-.12,28),
        *[p[1] for p in outline][1:-1],*[p[1] for p in feature_edge or []]]))
    samples=[v for v in samples if min(p[1] for p in outline)+.1<=v<=max(p[1] for p in outline)-.1]
    across=[0,.045,.20,.50,.80,.955,1.];vertices=[]
    for py in samples:
        a,b=polygon_span(outline,float(py));z=(GROUND-py)*SCALE
        if left_clip is not None:a=max(a,left_clip(float(py)))
        if a>=b:raise ValueError("Armor aperture removes entire section: "+name)
        if feature_edge:
            fold_u=edge_u_at_v(feature_edge,py)
            split=float(np.clip((fold_u-a)/(b-a),.03,.97))
            row_across=[0,.10*split,.45*split,split,split+.55*(1-split),split+.90*(1-split),1.]
        else:row_across=across
        for t in row_across:
            y=sign*(CX-(a+t*(b-a)))*SCALE
            vertices.append([surface(y,z)+.003*math.sin(math.pi*t),y,z])
    n=len(across);faces=[]
    for k in range(len(samples)-1):
        for i in range(n-1):faces.append([k*n+i,k*n+i+1,(k+1)*n+i+1,(k+1)*n+i])
    # FRONT order above points outward +X (mirroring reverses this winding).
    if sign<0:faces=[list(reversed(f)) for f in faces]
    sharp=[]
    if feature_edge:
        lo,hi=min(p[1] for p in feature_edge),max(p[1] for p in feature_edge)
        sharp=[[k*n+3,(k+1)*n+3] for k in range(len(samples)-1) if lo<=samples[k] and samples[k+1]<=hi]
    g.cover(name,body,vertices,faces,color,skin,sharp_outer_edges=sharp)
    g.parts[-1].update({"reference_front_outline_px":outline,
        "reconstruction_note":"A separate thin broad armor panel with actual open back and boundary return; FRONT profile is observed, surface depth/skin is an appearance candidate."})


def curved_artwork_plate(g,name,body,outline,surface,depth,color,rear=False,camber=.012):
    across=[-1,-.91,-.68,-.30,0,.30,.68,.91,1]
    vertices=[];steps=28
    lo=min(p[1] for p in outline)+.10;hi=max(p[1] for p in outline)-.10
    sign=-1 if rear else 1
    for py in np.linspace(lo,hi,steps):
        a,b=polygon_span(outline,float(py));cy=(CX-(a+b)/2)*SCALE;ry=max((b-a)*SCALE/2,.002)
        for t in across:
            y=sign*(cy+ry*t);z=(GROUND-py)*SCALE
            vertices.append([surface(y,z)+sign*camber*(1-t*t),y,z])
    n=len(across);count=len(vertices)
    vertices += [[x-sign*depth,y,z] for x,y,z in vertices]
    faces=[]
    for k in range(steps-1):
        for i in range(n-1):
            q=[k*n+i,k*n+i+1,(k+1)*n+i+1,(k+1)*n+i]
            faces.append(q);faces.append([v+count for v in reversed(q)])
        for i in (0,n-1):
            q=[k*n+i,(k+1)*n+i,(k+1)*n+i+count,k*n+i+count]
            faces.append(q if i==0 else list(reversed(q)))
    for k in (0,steps-1):
        for i in range(n-1):
            q=[k*n+i,k*n+i+count,k*n+i+1+count,k*n+i+1]
            faces.append(q if k==0 else list(reversed(q)))
    g.part(name,body,vertices,faces,color)
    g.parts[-1].update({"edge_bevel_m":0,"surface_shading":"curved_hard_surface","reference_outline_px":outline})


def continuous_crown(g):
    # Connect front shield and rear shell in actual 3D; no open black slot in TOP.
    sections=[(-.327,2.48,.385),(-.29,2.57,.380),(-.20,2.626,.35),(-.075,2.646,.315),
              (.045,2.597,.335),(.18,2.526,.325),(.30,2.457,.290),(.43,2.38,.250)]
    vertices=[]
    across=[-1,-.91,-.60,0,.60,.91,1]
    for x,z,width in sections:
        for t in across:vertices.append([x,t*width,z-.017*t*t])
    n=len(across);count=len(vertices)
    vertices += [[x,y,z-.025] for x,y,z in vertices]
    faces=[]
    for k in range(len(sections)-1):
        for i in range(n-1):
            q=[k*n+i,(k+1)*n+i,(k+1)*n+i+1,k*n+i+1]
            faces.append(q);faces.append([v+count for v in reversed(q)])
        for i in (0,n-1):
            q=[k*n+i,k*n+i+count,(k+1)*n+i+count,(k+1)*n+i]
            faces.append(q if i==0 else list(reversed(q)))
    for k in (0,len(sections)-1):
        for i in range(n-1):
            q=[k*n+i,k*n+i+1,k*n+i+1+count,k*n+i+count]
            faces.append(q if k==0 else list(reversed(q)))
    g.part("ivory_continuous_crown_bridge","torso",vertices,faces,IVORY)
    g.parts[-1].update({"edge_bevel_m":0,"surface_shading":"curved_hard_surface"})


def hood_side_lip(g,profiles,shape):
    """The observed narrow hood rim around an open shoulder window.

    Removing a colored solid side wall must not remove the visible armor
    flange itself. The strip has genuine inner/outer material surfaces; its
    large assembly window remains open. LEFT contours are visible candidates,
    and lateral placement comes from the corresponding FRONT/REAR widths.
    """
    front=profiles["front"]["chest_ivory_outer"]
    back=[[u,v-612] for u,v in profiles["rear"]["rear_chest_ivory_outer"]]
    observed=shape["hood_left_side_lip"]
    outer=observed["outer_boundary_uv"]
    inner=observed["inner_boundary_uv_candidate"]
    if len(outer)!=len(inner):raise ValueError("Hood rim boundary pairing differs")
    across=[0,.08,.20,.40,.60,.80,.92,1.]
    for side,sign in (("left",1),("right",-1)):
        vertices=[]
        for a,b in zip(outer,inner):
            for t in across:
                u,py=(1-t)*np.asarray(a)+t*np.asarray(b)
                # LEFT's crown peaks 2 px above FRONT on the uncalibrated
                # sheet. Under the agreed FRONT-height template, the added
                # lip fits below its existing crown skin rather than growing
                # the entire robot to match that view's separate pixel top.
                z=float(np.clip((GROUND-py)*SCALE,(GROUND-max(p[1] for p in front))*SCALE+.008,2.6415));x=(971-u)*SCALE
                fpy=np.clip(py,min(p[1] for p in front)+.12,max(p[1] for p in front)-.12)
                b_py=np.clip(py,min(p[1] for p in back)+.12,max(p[1] for p in back)-.12)
                fa,fb=polygon_span(front,float(fpy));ra,rb=polygon_span(back,float(b_py))
                yf=(fb-fa)*SCALE/2;yr=(rb-ra)*SCALE/2
                # The side rim retains LEFT's forward envelope. It must not
                # force the separate central FRONT shield onto that envelope.
                xf=float(CHEST_CURVE(z));xr=chest_back(0,z)
                blend=float(np.clip((xf-x)/max(xf-xr,.02),0,1))
                lateral=(1-blend)*yf+blend*yr+.002+.008*math.sin(math.pi*t)
                # The original FRONT shoulder notch is a visible overlap
                # constraint. Rear-shell width cannot migrate to the forward
                # flange and cover the blue shoulder's inward/downward end.
                forward=float(np.clip(x/.12,0,1))
                # The return curves inward within that envelope. Keeping the
                # whole lower clipped strip at a single Y/Z would collapse it
                # into a line rather than leave a real finite-width skin.
                limit=yf-.006*math.sin(math.pi*t)
                lateral=(1-forward)*lateral+forward*min(lateral,limit)
                vertices.append([x,sign*lateral,z])
        n=len(across);faces=[]
        for k in range(len(outer)-1):
            for i in range(n-1):faces.append([k*n+i,k*n+i+1,(k+1)*n+i+1,(k+1)*n+i])
        v=np.asarray(vertices)
        normal=sum((np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]]) for f in faces),start=np.zeros(3))
        if normal[1]*sign<0:faces=[list(reversed(f)) for f in faces]
        g.cover(side+"_ivory_hood_window_side_lip","torso",vertices,faces,IVORY,.007)
        g.parts[-1].update({"reference_left_outer_boundary_px":outer,
            "reference_left_inner_boundary_candidate_px":inner,
            "front_overlap_constraint":"Forward rim at X>=0.12m stays within the observed FRONT white boundary; rear width retained independently with a candidate transition at X=0..0.12m.",
            "left_height_continuation":"Lip constrained within the existing FRONT crown/shield height; LEFT crown/bottom pixels do not define an independent scale or a second projecting ivory nose.",
            "reconstruction_note":"Observed ivory crown/front/back rim rebuilt as a thin curved strip around an open shoulder window. Lateral depth, inner boundary beneath overlapping blue guards and skin are uncalibrated appearance candidates; no side wall or physical strength claim."})


def continuous_torso_shell(g,profiles):
    front=profiles["front"]["chest_ivory_outer"]
    back=[[x,y-612] for x,y in profiles["rear"]["rear_chest_ivory_outer"]]
    screen_outline=np.array([[x,y-612] for x,y in profiles["rear"]["rear_blue_service_hatch"]],float)
    screen_center=screen_outline.mean(axis=0)
    screen_opening=(screen_center+(screen_outline-screen_center)*[.82,.80]).tolist()
    screen_lo=min(v for u,v in screen_opening);screen_hi=max(v for u,v in screen_opening)
    cheek=profiles["front"]["left_blue_chest_cheek_visible"]
    samples=sorted(set([*np.linspace(87.12,max(p[1] for p in front),48),123.,128.,
        *[v for v,_,_ in profiles.get("front_white_boundary_vlr",[])],
        *[v for u,v in screen_opening]]))
    steps=len(samples);vertices=[];faces=[];colors=[]
    for py in samples:
        a,b=polygon_span(front,float(py));yf=max((b-a)*SCALE/2,.003)
        back_py=min(max(py,min(p[1] for p in back)+.1),max(p[1] for p in back)-.1)
        ra,rb=polygon_span(back,float(back_py));yr=max((rb-ra)*SCALE/2,.003)
        if py>245:yr*=max(.35,1-(py-245)/25)
        ys=max(yf+.022,yr+.020)
        if min(p[1] for p in cheek)<py<max(p[1] for p in cheek):
            ca,cb=polygon_span(cheek,float(py));ys=max(ys,(CX-ca)*SCALE)
        z=(GROUND-py)*SCALE;xf=chest_front(0,z);xr=chest_back(0,z);xm=(xf-.10+xr+.047)/2
        recess=np.interp(z,[1.85,2.0,2.35,2.47],[0.,1.,1.,0.])
        xs=(xf-.10)*(1-recess)+min(xf-.10,.30)*recess
        main_half=yf*.80
        if FRONT_SHIELD_CONFIG and py>=123:
            face=FRONT_SHIELD_CONFIG["observed_main_face_outline_uv"]
            # The shallow U-shaped visible turn at v123..128 is not a
            # fishtail cross section: blend the crown into the long face,
            # rather than collapse/re-expand its whole leading plane.
            face_py=float(np.clip(py,128.,259.99))
            ma,mb=polygon_span(face,face_py)
            target=min(yf*.90,max((mb-ma)*SCALE/2,.003))
            transition=float(np.clip((py-123)/5,0,1))
            main_half=(1-transition)*main_half+transition*target
        drop=float(FRONT_SHIELD_CONFIG.get("candidate_edge_drop_m",.045))
        edge_drop=.012+(drop-.012)*float(np.clip((py-123)/5,0,1))
        ring=[(xf,main_half),(xf,-main_half),(xf-edge_drop,-yf),(xs,-yf),
              (xm,-ys),(xr+.047,-yr-.022),(xr,-yr*.92),(xr,yr*.92),
              (xr+.047,yr+.022),(xm,ys),(xs,yf),(xf-edge_drop,yf)]
        vertices.extend([[x,y,z] for x,y in ring])
    n=12;faces.append(list(reversed(range(n))));colors.append(IVORY)
    for k in range(steps-1):
        z=vertices[k*n][2]
        for i in range(n):
            faces.append([k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i])
            is_side=i in (3,4,8,9)
            # Blue cheeks are separate contour-constrained wraps below. A
            # blue-painted full torso side made their FRONT bottom a shelf
            # and hid the source's dark recessed mechanical layers.
            color=DARK if is_side and z<2.55 else IVORY
            if i in (4,8) and 1.89<z<2.55:color=BLUE
            if i in (5,6,7) and z<1.842:color=DARK
            colors.append(color)
    faces.append(list(range((steps-1)*n,steps*n)));colors.append(DARK)
    armor=[faces[0]];screen_edge_vertices={}
    for k in range(steps-1):
        z=vertices[k*n][2]
        for i in (10,11,0,1,2,5,6,7):
            if i in (5,6,7) and z<1.846:continue
            if i==6:
                # Real module opening in the rear ivory skin. Retain the two
                # side strips and the full armor above/below the original hatch.
                edges=[]
                for row in (k,k+1):
                    if row not in screen_edge_vertices:
                        u0,u1=polygon_span(screen_opening,float(np.clip(samples[row],screen_lo,screen_hi)))
                        low=(u0-CX)*SCALE-.002;high=(u1-CX)*SCALE+.002
                        x,negative,zz=vertices[row*n+6];positive=vertices[row*n+7][1]
                        low=max(low,negative+.12*(positive-negative))
                        high=min(high,positive-.12*(positive-negative))
                        screen_edge_vertices[row]=(len(vertices),len(vertices)+1)
                        vertices.extend([[x,low,zz],[x,high,zz]])
                    edges.append(screen_edge_vertices[row])
                (a,b),(c,d)=edges
                armor.extend([[k*n+6,a,c,(k+1)*n+6],
                              [b,k*n+7,(k+1)*n+7,d]])
                if not(screen_lo-1e-7<=samples[k] and samples[k+1]<=screen_hi+1e-7):
                    armor.append([a,b,d,c])
                continue
            armor.append([k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i])
    g.cover("continuous_ivory_torso_armor_cover","torso",vertices,armor,IVORY,.007,faces)
    g.parts[-1].update({"edge_bevel_m":0,"surface_shading":"curved_hard_surface",
        "reconstruction_note":"Continuous crown/front shield and shorter rear armor skins with open shoulder sides and visible thin returns. Assembly cavity is empty, not a colored torso solid.",
        "reference_front_outline_px":front,"reference_rear_outline_normalized_px":back,
        "rear_control_module_opening_normalized_px":screen_opening,
        "rear_display_mounting_skin_open":True,
        "front_main_face_candidate":FRONT_SHIELD_CONFIG,
        "front_return_overlap_constraint":"Front returns stay within the visible white boundary; no additional 27mm lateral extension into the original blue shoulder notch."})
    for side,sign in (("left",1),("right",-1)):
        frame=[];frame_faces=[]
        for py in np.linspace(108,242,28):
            z=(GROUND-py)*SCALE;ra,rb=polygon_span(back,float(py));yr=(rb-ra)*SCALE/2
            xr=chest_back(0,z)
            frame.extend([[xr+.032,sign*(yr+.021),z],[xr+.100,sign*(yr+.010),z]])
        for k in range(27):frame_faces.append([2*k,2*k+1,2*(k+1)+1,2*(k+1)])
        if sign<0:frame_faces=[list(reversed(f)) for f in frame_faces]
        g.cover(side+"_blue_rear_shoulder_edge_cover","torso",frame,frame_faces,BLUE,.006)
        g.parts[-1]["reconstruction_note"]="Narrow rear blue edge armor beside the shorter ivory back cover; shoulder cavity stays open instead of a blue or black side wall. Hidden support remains unknown."


def service_hatch(g,profiles):
    """User-authorized rear control screen within the original blue hatch."""
    outline=[[x,y-612] for x,y in profiles["rear"]["rear_blue_service_hatch"]]
    center=np.mean(outline,axis=0)
    shadow=(center+1.035*(np.asarray(outline)-center)).tolist()
    # The blue bezel is a real annular cover, with an open module mounting
    # cavity. The outside contour, original four screws and upper tab remain.
    q=np.array([yz(u,v,True) for u,v in outline]);c=q.mean(axis=0)
    inner=c+(q-c)*[.82,.80];n=len(q)
    for name,outside,xf,xb,color,skin in (
        ("rear_service_door_shadow",np.array([yz(u,v,True) for u,v in shadow]),-.458,-.454,DARK,.0015),
        ("rear_blue_service_door",q,-.465,-.451,BLUE,.003)):
        vertices=[[x,y,z] for x,contour in ((xf,outside),(xf,inner),(xb,outside)) for y,z in contour]
        faces=[]
        for i in range(n):
            j=(i+1)%n;faces.extend([[i,j,n+j,n+i],[j,i,2*n+i,2*n+j]])
        sample=faces[0]
        if np.cross(np.array(vertices[sample[1]])-vertices[sample[0]],
                    np.array(vertices[sample[2]])-vertices[sample[0]])[0]>0:
            faces=[list(reversed(f)) for f in faces]
        g.cover(name,"torso",vertices,faces,color,skin,
            note="Original hatch's removable annular bezel/sealing edge with a genuine module mounting opening. No full plate across display package space. Mounting/gauge remain candidates.")
    g.parts[-1].update({"reference_rear_outline_normalized_px":outline,
        "user_authorized_function":"Rear central control screen: status, task selection and local control.",
        "screen_module_mounting_cavity_open":True})
    glass_outline=[[CX+y/SCALE,GROUND-z/SCALE] for y,z in inner]
    g.panel("rear_control_screen_module_envelope","torso",glass_outline,-.460,.026,DARK,0,rear=True,camber=0)
    g.parts[-1].update({"role":"display_module_envelope","edge_bevel_m":0,
        "module_dimensions_yz_m":np.ptp(inner,axis=0).tolist(),"module_depth_candidate_m":.026,
        "procurement_status":"yellow_custom_or_unselected","touch_and_controller_connected":False,
        "reconstruction_note":"Separate 26mm-deep display/control-electronics package envelope behind the retained blue bezel. A space candidate, not a selected device, assigned mass or released physical integration."})
    g.panel("rear_control_screen_glass","torso",glass_outline,-.4665,.0015,[.012,.095,.18,1],0,rear=True,camber=0)
    g.parts[-1].update({"role":"control_display_glass","edge_bevel_m":0,
        "surface_material":{"metallic":0.0,"roughness":.14},
        "display_content_status":"static_layout_candidate_no_live_telemetry",
        "reconstruction_note":"Inset dark-blue touch glass, physically separate from the blue armor bezel. Interface is a static native-mesh layout; no live control or measured telemetry claim."})
    yc,zc=c
    lit=[.38,.79,1.0,1]
    screen_mesh_text(g,"rear_control_screen_header","GORILLA",[-.4685,yc+.064,zc+.095],.0045,lit)
    for i,label in enumerate(("STATUS","TASK","LOCAL")):
        z=zc+.033-i*.069
        g.rounded_rect("rear_control_screen_touch_zone_"+label.lower(),"torso",[-.468,yc,z],
            .210,.045,.0007,.006,[.025,.16,.27,1],True)
        g.parts[-1].update({"role":"control_display_ui","edge_bevel_m":0,
            "touch_action_candidate":label.lower(),"control_connected":False})
        screen_mesh_text(g,"rear_control_screen_label_"+label.lower(),label,
            [-.4695,yc+.083,z+.009],.0033,lit)
        g.rounded_rect("rear_control_screen_zone_indicator_"+label.lower(),"torso",[-.4695,yc-.079,z],
            .016,.016,.0006,.004,lit,True)
        g.parts[-1].update({"role":"control_display_ui","edge_bevel_m":0,
            "indicator_is_static_layout":True})
    g.rounded_rect("rear_service_latch","torso",[-.469,0,2.320],.068,.026,.007,.007,DARK,True)
    g.rounded_rect("rear_door_upper_tab","torso",[chest_back(0,2.425)-.010,0,2.425],.048,.054,.015,.008,BLUE,True)
    for i,(px,py) in enumerate(((302,760),(347,760),(302,815),(347,815))):
        y,z=yz(px,py-612,True)
        g.bolt(f"rear_door_screw_{i}","torso",[-.470,y,z],axis=(-1,0,0),radius=.004)


def screen_mesh_text(g,name,text,origin,cell,color):
    """Small editable native glyph meshes; no image overlay or painted text."""
    font={
        "A":["010","101","111","101","101"],"C":["011","100","100","100","011"],
        "G":["011","100","101","101","011"],"I":["111","010","010","010","111"],
        "K":["101","110","100","110","101"],"L":["100","100","100","100","111"],
        "O":["010","101","101","101","010"],"R":["110","101","110","101","101"],
        "S":["011","100","010","001","110"],"T":["111","010","010","010","010"],
        "U":["101","101","101","101","111"],
    }
    x,y,z=origin;vertices=[];faces=[]
    box_faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
    for k,char in enumerate(text):
        for row,line in enumerate(font[char]):
            for col,on in enumerate(line):
                if on!="1":continue
                yy=y-(4*k+col)*cell;zz=z-row*cell;n=len(vertices)
                vertices.extend([[xx,vy,vz] for xx in (x,x+.0005)
                    for vy,vz in ((yy-.82*cell,zz),(yy,zz),(yy,zz+.82*cell),(yy-.82*cell,zz+.82*cell))])
                faces.extend([[n+i for i in f] for f in box_faces])
    g.part(name,"torso",vertices,faces,color)
    g.parts[-1].update({"role":"control_display_ui","surface_shading":"flat_weighted_normals",
        "display_text":text,"text_geometry":"closed native glyph cells",
        "display_content_status":"static_layout_candidate_no_live_telemetry"})


def side_return_cover(g,name,body,outline,sign,lateral,color,skin=.006):
    """Curved SIDE-facing cover with a real open back, not a deep extrusion."""
    uv=[np.asarray(p,float) for p in outline]
    faces=triangulate_outline(uv)
    for _ in range(2):
        midpoints={};new_faces=[]
        def midpoint(a,b):
            key=tuple(sorted((a,b)))
            if key not in midpoints:
                midpoints[key]=len(uv);uv.append((uv[a]+uv[b])/2)
            return midpoints[key]
        for a,b,c in faces:
            ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
            new_faces.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
        faces=new_faces
    vertices=[[(971-u)*SCALE,sign*lateral(u,v),(GROUND-v)*SCALE] for u,v in uv]
    normal=sum((np.cross(np.array(vertices[f[1]])-vertices[f[0]],
        np.array(vertices[f[2]])-vertices[f[0]]) for f in faces),start=np.zeros(3))
    if normal[1]*sign<0:faces=[list(reversed(f)) for f in faces]
    g.cover(name,body,vertices,faces,color,skin)
    g.parts[-1].update({"reference_left_outline_px":outline,
        "reconstruction_note":"Thin curved SIDE return matching visible artwork edges, with open mounting back. Hidden overlap/lateral depth and skin thickness are candidates; not a solid colored side wall."})


def chest_cheek(g,side,sign,profiles):
    # The old coarse outline included dark mechanism pixels and formed a
    # wide blue shelf. Keep the observed broad lower face separate from the
    # narrow inner wedge that continues beside the white shield.
    visible=[[277,162],[284,190],[291,219],[298,241],[309,250],
             [303,249],[291,239],[281,239],[270,237],[261,232],
             [253,224],[251,215],[258,211]]
    crease=[[284,190],[286,203],[288,216],[290,229],[291,239]]
    vent_side=profiles["left"]["side_vent_ivory_mount"]
    def forward(y,z):
        py=GROUND-z/SCALE
        u=CX-abs(y)/SCALE
        depth=float(np.interp(py,[162,184,205,222,240,251],
            [.315,.349,.370,.359,.334,.298]))
        turn=edge_u_at_v(crease,py)
        depth-=.0028*max(0,u-turn)
        # Front socket remains in front of its supporting blue face. This
        # visibility condition does not assert real assembly clearances.
        if 161.2<py<214:
            va,vb=polygon_span(profiles["front"]["left_vent_ivory_mount"],py)
            if va-1<u<vb+1:
                sa,sb=polygon_span(vent_side,float(np.clip(py,161.2,222.8)))
                depth=min(depth,(971-sa)*SCALE-.023)
        return depth
    def vent_clearance(py):
        opening=profiles["front"]["left_vent_black_opening"]
        if min(v for u,v in opening)<py<max(v for u,v in opening):
            a,b=polygon_span(profiles["front"]["left_vent_black_opening"],py)
            return b+2
        return -1e6
    patch_cover(g,side+"_blue_chest_cheek_wrap","torso",visible,sign,
        forward,BLUE,.006,feature_edge=crease,left_clip=vent_clearance)
    g.parts[-1].update({"reference_front_feature_edges_px":[crease,[[270,237],[281,239],[291,239]]],
        "visible_point_uncertainty_px":4,
        "intake_clearance_geometry":"Blue surface trimmed outside black opening +2px candidate margin; no blue plate behind the actual air throat.",
        "outline_status":"Visible broad-face/inner-turn hints with candidate continuation behind the radiator and white shield; not a calibrated full hidden outline.",
        "reconstruction_note":"Tapered broad blue cheek plus narrow inner wedge beside the shield, with a true open back; no fixed deep posterior wall or wide shelf."})
    side_outline=[[906,191],[932,191],[937,205],[943,223],[941,233],
                  [936,244],[924,250],[913,251],[906,240],[901,222],[899,205]]
    def side_lateral(u,py):
        q=float(np.clip(py,162.2,249.8))
        fa,fb=polygon_span(visible,q)
        sa,sb=polygon_span(side_outline,float(np.clip(py,191.2,250.8)))
        lateral=(CX-fa)*SCALE-.034*float(np.clip((u-sa)/max(sb-sa,1),0,1))
        # Return the supporting side armor around the outside of the actual
        # intake, rather than leave an edge-on blue plate inside the throat.
        # Its SIDE contour is retained; hidden Y depth is a declared choice.
        if py<214:
            opening=profiles["front"]["left_vent_black_opening"]
            v0,v1=min(v for u,v in opening),max(v for u,v in opening)
            a,b=polygon_span(opening,float(np.clip(py,v0+.05,v1-.05)))
            required=(CX-a)*SCALE+.012
            blend=float(np.clip((214-py)/4,0,1))
            lateral=(1-blend)*lateral+blend*max(lateral,required)
        return lateral
    side_return_cover(g,side+"_blue_chest_cheek_side_return","torso",side_outline,
        sign,side_lateral,BLUE)
    g.parts[-1].update({"observed_left_front_and_lower_boundary_uv":[[899,205],[901,222],[906,240],[913,251],[924,250],[936,244]],
        "intake_return_routing":"Upper hidden return wraps outside the actual black opening plus 12mm candidate clearance, with a transition below the mouth; no blue blade through the intake.",
        "hidden_left_upper_and_rear_boundary_status":"Candidate continuation under ivory radiator and white arm; dark mechanical layers remain separate."})


def hip_connector_cover(g,side,sign):
    front=[[272,244],[282,242],[290,242],[297,251],[302,265],
           [298,272],[289,273],[280,268],[273,259],[268,252]]
    side_outline=[[933,247],[941,245],[948,250],[950,256],[938,262],
                  [925,274],[917,273],[912,265],[918,255]]
    def forward(y,z):
        py=float(np.clip(GROUND-z/SCALE,245.15,273.8))
        a,b=polygon_span(side_outline,py)
        fa,fb=polygon_span(front,float(np.clip(GROUND-z/SCALE,242.2,272.8)))
        u=CX-abs(y)/SCALE
        return (971-a)*SCALE-.020*float(np.clip((u-fa)/max(fb-fa,1),0,1))
    patch_cover(g,side+"_ivory_hip_cuff",side+"_thigh",front,sign,forward,IVORY,.006)
    g.parts[-1].update({"reference_front_visible_points_uncertainty_px":4,
        "reconstruction_note":"Observed slanted FRONT white hip guard, turning back around a short dark axis layer. Thickness, hidden top continuation and X surface are candidates, not measured hardware."})
    def lateral(u,py):
        fa,fb=polygon_span(front,float(np.clip(py,242.2,272.8)))
        a,b=polygon_span(side_outline,float(np.clip(py,245.15,273.8)))
        return (CX-fa)*SCALE-.014*float(np.clip((u-a)/max(b-a,1),0,1))
    side_return_cover(g,side+"_ivory_hip_cuff_side_return",side+"_thigh",side_outline,sign,lateral,IVORY)


def torso_side_mechanism_layers(g,side,sign):
    """Compact distinct housings in the observed dark side strip.

    The artwork shows layers behind the intake and arm, not an empty bay or
    a filled black wall. Drum centers, unseen axial depth and identity remain
    appearance candidates; these are not actuator models or a load chain.
    """
    # One finite-skin housing wraps the connected side mechanism. The old
    # separated circular caps projected as floating dots in a true empty bay.
    outline=[[949,163],[966,162],[971,180],[967,203],[965,226],
             [960,245],[949,262],[937,262],[932,249],[938,228],[942,202],[943,179]]
    def lateral(u,v):
        return float(np.interp(v,[162,174,197,207,215,221,230,249,262],
            [.470,.478,.470,.445,.432,.399,.369,.292,.250]))-.006*abs(u-953)/18
    side_return_cover(g,side+"_dark_torso_side_housing","torso",outline,
        sign,lateral,DARK,skin=.006)
    g.parts[-1]["reconstruction_note"]="Independent finite-wall side housing over the actual spine/shoulder carrier, covering only the original dark mechanism strip. It leaves the exterior axilla and intake throat open; no filled dark torso wall or certified bearing housing."
    for i,(u,py,radius) in enumerate(((955,174,.048),(953,197,.048),
                                     (951,220,.047),(947,243,.041))):
        half=.035
        p=np.array([(971-u)*SCALE,sign*(lateral(u,py)-half+.008),(GROUND-py)*SCALE])
        a=p-[0,sign*half,0];b=p+[0,sign*half,0]
        g.link(side+f"_torso_side_layer_{i:02}","torso",a,b,
            [(0,radius*.82,radius*.82),(.08,radius,radius),
             (.24,radius,radius),(.31,radius*.93,radius*.93),
             (.87,radius*.93,radius*.93),(1,radius*.81,radius*.81)],DARK,True,40)
        g.parts[-1]["reconstruction_note"]="Distinct short dark housing in the artwork's exposed side mechanism strip. Center/depth/radius are appearance candidates; no SKU, joint axis, mass or load-bearing approval."
        p[1]+=sign*(half+.001)
        g.link(side+f"_torso_side_layer_lip_{i:02}","torso",p-[0,sign*.003,0],p+[0,sign*.003,0],
            [(0,radius*.82,radius*.82),(.20,radius*.88,radius*.88),
             (.80,radius*.88,radius*.88),(1,radius*.82,radius*.82)],METAL,True,40)


def rear_leg_cover(g,side,sign,profiles):
    """A separate returned rear guard on the middle leg carriage, not a flat tab."""
    outline=profiles["left"]["middle_leg_blue_rear_cap_visible"]
    outside=np.array([[(971-u)*SCALE,sign*(.624-.006*abs(v-454)/23),(GROUND-v)*SCALE]
        for u,v in outline])
    returned=outside.copy();returned[:,1]-=sign*.051;returned[:,0]+=.022
    vertices=np.concatenate([outside,returned]);n=len(outside)
    face=list(range(n))
    normal=sum((np.cross(outside[face[i]]-outside[0],outside[face[i+1]]-outside[0])
        for i in range(1,n-1)),start=np.zeros(3))
    if normal[1]*sign<0:face.reverse()
    # Three real returns, leaving the lower and inner mounting cavity open.
    faces=[face]
    for i in (0,1,5):
        j=(i+1)%n
        faces.append([j,i,i+n,j+n] if normal[1]*sign>=0 else [i,j,j+n,i+n])
    g.cover(side+"_blue_middle_shank_rear_cover",side+"_middle_shank",vertices,faces,BLUE,.006)
    g.parts[-1].update({"reference_left_outline_px":outline,
        "reconstruction_note":"Separate curved rear blue guard with finite outer/inner skins and real narrow returns onto the middle leg carriage. Lower mounting mouth remains open; no filled blue volume or structural approval."})


def lower_leg_guard(g,side,sign,profiles):
    """Front/side-constrained lower Z segment cover, with two open end mouths."""
    names={side+"_blue_distal_front_guard",side+"_ivory_distal_side_tab"}
    g.parts=[p for p in g.parts if p["name"] not in names]
    dual_view_shell(g,side+"_blue_distal_front_guard",side+"_distal_shank",
        profiles["front"]["left_lower_leg_blue_bridge"],
        profiles["left"]["lower_leg_blue_forward_bridge"],BLUE,sign,10)
    g.parts[-1]["reconstruction_note"]="Three-dimensional short lower blue Z-leg cover constrained by both original visible silhouettes; front and side breadth, inner skin and open upper/lower mouths replace the previous edge-on plate."


def separate_leg_rear_skins(g,profiles):
    """Independent rear covers tucked into the real C13 carrying assembly.

    No generic ring displacement.  Each rear guard has editable skin/returns,
    a specific original REAR profile, and open upper/lower mounting mouths.
    """
    for side,sign in (("left",1),("right",-1)):
        for kind,body,profile_id in (("middle",side+"_middle_shank","rear_left_middle_leg_blue_outer"),
                                    ("distal",side+"_distal_shank","rear_left_lower_leg_blue_bridge")):
            outline=profiles["rear"][profile_id]
            main=next(p for p in g.parts if p["name"]==side+("_blue_middle_shank_wrap" if kind=="middle" else "_blue_distal_front_guard"))
            main_v=np.asarray(main["vertices_world_m"])
            suffixes=("rear_upper_case","rear_bent_carrier") if kind=="middle" else ("rear_bent_case",)
            castings=[np.asarray(p["vertices_world_m"]) for p in g.parts
                if p["body"]==body and p["name"].startswith(side+"_")
                and (any(p["name"].endswith(suffix) for suffix in suffixes)
                    or p.get("c14_primary_structure_segment")==kind)]
            if not castings:raise ValueError("Rear skin needs actual carrying castings: "+side+kind)
            carriers=np.concatenate(castings)
            if kind=="middle":
                cap=next(p for p in g.parts if p["name"]==side+"_blue_middle_shank_rear_cover")
                cap_v=np.asarray(cap["vertices_world_m"])
                y_outer=float(np.max(sign*cap_v[:,1]))-.082
                y_inner=float(np.min(sign*main_v[:,1]))+.038
                x_floor=float(cap_v[:,0].min())+.004
            else:
                ivory=next(p for p in g.parts if p["name"]==side+"_ivory_ankle_"+("positive_y" if sign>0 else "negative_y")+"_sloping_brace")
                ivory_v=np.asarray(ivory["vertices_world_m"])
                y_outer=float(np.max(sign*ivory_v[:,1]))-.024
                y_inner=float(np.min(sign*main_v[:,1]))-.016
                x_floor=float(ivory_v[:,0].min())+.025
            lo=min(v for u,v in outline)+.20;hi=max(v for u,v in outline)-.20
            # Keep top/bottom at their artwork region, with middle rear skin
            # clipped to the already observed main armor end elevations.
            if kind=="middle":
                lo=max(lo,1215-float(main_v[:,2].max())/SCALE)
                hi=min(hi,1215-float(main_v[:,2].min())/SCALE)
            else:
                hi=min(hi,1215-(float(ivory_v[:,2].min())+.008)/SCALE)
            samples=sorted(set([*np.linspace(lo,hi,13),*[v for u,v in outline if lo<v<hi]]))
            vertices=[]
            for py in samples:
                u0,u1=polygon_span(outline,py)
                y0=max((CX-u1)*SCALE,y_inner);y1=min((CX-u0)*SCALE,y_outer)
                if y1-y0<.025:
                    center=(y0+y1)/2;y0=center-.0125;y1=center+.0125
                z=(1215-py)*SCALE
                band=carriers[abs(carriers[:,2]-z)<=.047]
                if not len(band):band=carriers[np.argsort(abs(carriers[:,2]-z))[:12]]
                x_back=max(x_floor,float(band[:,0].min())-.009)
                for t in (0,.5,1):
                    # Shoulders turn forward into the carrier; center lies
                    # outside the actual back face for REAR coverage.
                    vertices.append([x_back+.024*abs(2*t-1),sign*(y0+t*(y1-y0)),z])
            count=len(samples);faces=[]
            for k in range(count-1):
                for j in range(2):
                    face=[k*3+j,k*3+j+1,(k+1)*3+j+1,(k+1)*3+j]
                    faces.append(list(reversed(face)) if sign>0 else face)
            n=len(vertices)
            left=[k*3 for k in range(count)];right=[k*3+2 for k in range(count)]
            for indices in (left,right):
                start=len(vertices)
                vertices.extend((np.asarray(vertices[i])+[.022,0,0]).tolist() for i in indices)
                for k in range(count-1):
                    a,b=indices[k],indices[k+1];c,d=start+k,start+k+1
                    face=[b,a,c,d] if indices is left else [a,b,d,c]
                    faces.append(face if sign>0 else list(reversed(face)))
            g.cover(side+"_blue_"+kind+"_rear_guard_candidate",body,vertices,faces,BLUE,.006,
                note="Separate original-REAR-profile blue guard on the back of the actual carrying case. Open top/bottom and finite side returns; no SIDE-height blue wall, no dark-part recoloring, no physical approval.")
            g.parts[-1].update({"reference_rear_outline_px":outline,"appearance_skin_thickness_range_m":[.006,.006],
                "rear_guard_case_anchor_parts":[p["name"] for p in g.parts if p["body"]==body and (any(p["name"].endswith(suffix) for suffix in suffixes)
                    or p.get("c14_primary_structure_segment")==kind)],
                "top_bottom_mounting_mouths_open":True})


def refine_volumes(g,spec):
    landmarks=json.loads((ROBOT/"source/appearance_c_reference_landmarks.json").read_text())
    profiles={v:{p["id"]:p["global_uv_px"] for p in info["profiles"]} for v,info in landmarks["views"].items()}
    front_edges={p["id"]:p.get("feature_edges_global_uv_px",[]) for p in landmarks["views"]["front"]["profiles"]}
    shape_path=ROBOT/"source/appearance_c_front_shape_constraints.json"
    shoulder_shape=json.loads(shape_path.read_text())
    if shoulder_shape["source_sha256"]!=spec["appearance_authority"]["sha256"]:
        raise ValueError("FRONT shape constraints belong to a different artwork")
    boundary=shoulder_shape.get("front_white_shield_visible_boundary")
    if boundary:
        vlr=boundary["boundary_v_left_right_uv"]
        coarse=profiles["front"]["chest_ivory_outer"]
        # Retain the observed crown, and replace the coarse shoulder notch /
        # long shield edges with the explicitly reviewed visible white border.
        profiles["front"]["chest_ivory_outer"]=(coarse[:8]+
            [[r,v] for v,l,r in vlr]+boundary["lower_closure_candidate_uv"]+
            [[l,v] for v,l,r in reversed(vlr)]+[coarse[-1]])
        profiles["front_white_boundary_vlr"]=vlr
    remove=["ivory_continuous_front_carapace","ivory_long_shield_face","ivory_crown_top_lip","ivory_back_carapace","dark_torso_inner_layer",
            "saffron_front_pelvis","saffron_pelvis_front_inset","ivory_rear_sacral_cover","rear_saffron_crossbar"]
    for side in ("left","right"):
        remove += [side+suffix for suffix in ("_blue_shoulder_swept_top","_blue_shoulder_front_fold","_blue_rear_shoulder",
            "_blue_forearm_outer","_blue_forearm_long_plane","_blue_deltoid_outer","_blue_deltoid_front_plane",
            "_ivory_shoulder_cap","_ivory_upper_arm_link_cover","_ivory_upper_arm_inner_fold",
            "_blue_thigh_armor","_blue_thigh_front_facet","_blue_middle_shank","_blue_shank_front_plane",
            "_blue_chest_flank","_blue_lower_chest_flange","_gold_knee_guard","_gold_knee_center_face","_ivory_hip_cuff")]
    remove += ["rear_service_door_shadow","rear_blue_service_door","rear_service_latch","rear_door_upper_tab"]
    g.parts=[p for p in g.parts if p["name"] not in remove and "radiator_" not in p["name"] and "vent_fastener" not in p["name"] and not p["name"].startswith("rear_door_screw_")]
    continuous_torso_shell(g,profiles)
    hood_side_lip(g,profiles,shoulder_shape)
    service_hatch(g,profiles)
    curved_artwork_plate(g,"ivory_crown_inset","torso",profiles["front"]["crown_ivory_inset"],lambda y,z:chest_front(y,z)+.014,.009,[.95,.93,.87,1],camber=.013)
    curved_artwork_plate(g,"saffron_front_pelvis_cartridge","pelvis",profiles["front"]["pelvis_front_yellow_cartridge"],
        lambda y,z:.305+.014*(z-1.40),.075,GOLD,camber=.010)
    curved_artwork_plate(g,"ivory_rear_pelvis_cartridge","pelvis",[[x,y-612] for x,y in profiles["rear"]["rear_long_ivory_pelvis_cartridge"]],
        lambda y,z:-.217,.043,IVORY,rear=True,camber=.008)
    for side in ("left","right"):
        curved_artwork_plate(g,side+"_rear_yellow_pelvis_band","pelvis",[[x,y-612] for x,y in profiles["rear"]["rear_"+side+"_yellow_pelvis_band_visible"]],
            lambda y,z:-.195,.037,GOLD,rear=True,camber=.008)
    connector=[[u,v-612] for u,v in profiles["rear"]["rear_lower_ivory_connector"]]
    curved_artwork_plate(g,"ivory_rear_short_waist_connector","pelvis",connector,
        lambda y,z:-.327,.009,IVORY,rear=True,camber=.004)
    g.parts[-1]["reconstruction_note"]="Separate observed short REAR white trapezoid below the back armor and above the yellow V/long ivory cartridge. X/skin are candidates; FRONT coupler is a different visible cover."
    for part in g.parts:
        if part["name"]=="dark_torso_inner_layer":
            # Keep the visible carrier inside the blue/ivory envelope so it
            # cannot incorrectly occlude the art's blue inner cheek.
            for v in part["vertices_world_m"]:v[0]=.60*v[0]-.035;v[1]*=.90
        if part["name"]=="dark_pelvis_inner_layer":
            for v in part["vertices_world_m"]:v[1]*=.47
            part["reconstruction_note"]="Compact recessed central pelvis carrier candidate behind the separate yellow and ivory covers; no wide exposed dark box. Not a mass, structure or drive envelope."
    for side,s in (("left",1),("right",-1)):
        shoulder_sweep(g,side,s,profiles)
        chest_cheek(g,side,s,profiles)
        fitted_radiator(g,side,s,profiles)
        hip_connector_cover(g,side,s)
        torso_side_mechanism_layers(g,side,s)
        dual_view_shell(g,side+"_blue_forearm_wrap",side+"_forearm",profiles["front"]["left_forearm_blue_outer"],profiles["left"]["forearm_blue_outer"],BLUE,s,18,
            front_edges["left_forearm_blue_outer"][1:3],"forearm")
        dual_view_shell(g,side+"_blue_deltoid_wrap",side+"_upper_arm",profiles["front"]["left_upper_arm_blue_outer_guard"],profiles["left"]["upper_arm_blue_outer_guard"],BLUE,s,12,
            front_edges["left_upper_arm_blue_outer_guard"],"deltoid")
        shoulder_guard_assembly(g,side,s,profiles,shoulder_shape)
        dual_view_shell(g,side+"_ivory_lower_upper_arm",side+"_upper_arm",profiles["front"]["left_upper_arm_lower_ivory_guard"],
            [[967,197],[979,202],[1000,216],[1004,236],[995,254],[984,260],[970,237],[955,212]],IVORY,s,12,
            shell_sectors=list(range(12)))
        g.parts[-1]["reconstruction_note"]="Complete thin white sleeve around the bent mid-arm box member, with real inner/outer skins and open shoulder/elbow mouths. Original visible front/side contours retained; hidden rear continuation is a candidate."
        dual_view_shell(g,side+"_blue_thigh_wrap",side+"_thigh",profiles["front"]["left_thigh_blue_outer"],
            [[970,269],[949,283],[927,301],[916,318],[902,336],[897,350],[909,368],[929,382],[943,376],[965,351],[984,321],[987,299],[980,279]],BLUE,s,18,
            front_edges["left_thigh_blue_outer"],"thigh")
        dual_view_shell(g,side+"_blue_middle_shank_wrap",side+"_middle_shank",profiles["front"]["left_middle_leg_blue_outer"],profiles["left"]["middle_leg_blue_outer"],BLUE,s,15,
            front_edges["left_middle_leg_blue_outer"][1:2],"middle_shank")
        rear_leg_cover(g,side,s,profiles)
        lower_leg_guard(g,side,s,profiles)
        knee_outline=profiles["front"]["left_knee_yellow_insert"]
        if s<0:knee_outline=mirror_outline(knee_outline)
        side_guard=profiles["left"]["knee_yellow_insert"]
        def guard_depth(y,z,front=True):
            py=np.clip(GROUND-z/SCALE,349.15,408.85)
            a,b=polygon_span(side_guard,float(py))
            return (971-(a if front else b))*SCALE
        def guard_front(y,z):
            py=GROUND-z/SCALE
            ridge=(CX-edge_u_at_v(front_edges["left_knee_yellow_insert"][0],py))*SCALE
            d=abs(y)-ridge
            drop=min(.045,.034*max(0,d/.10)+.008*max(0,-d/.12))
            return max(guard_depth(y,z)-drop,guard_depth(y,z,False)+.013)
        fitted_guard(g,side+"_yellow_front_knee_insert",side+"_thigh",knee_outline,
            guard_front,lambda y,z:guard_depth(y,z,False),GOLD,
            outer_bevel=.003,inset_height=.002,inset_ratio=.95,open_cover=True)
        g.parts[-1].update({"reference_front_feature_edges_px":front_edges["left_knee_yellow_insert"],
            "reconstruction_note":"FRONT yellow knee color boundary and broad vertical fold restored; visible LEFT depth trend retained, side caps and hidden closure are uncalibrated."})
        knee_rear=[[x,y-612] for x,y in profiles["rear"]["rear_left_knee_yellow_insert"]]
        if s>0:knee_rear=mirror_outline(knee_rear)
        fitted_guard(g,side+"_yellow_rear_knee_insert",side+"_thigh",knee_rear,
            lambda y,z:-.10+.030*(z-1.10),lambda y,z:-.065+.030*(z-1.10),GOLD,rear=True,open_cover=True)
        # Preserve original gold markers on the actual new front surfaces.
        for part in g.parts:
            if not part["name"].startswith(side+"_"):continue
            if "forearm_gold_marker" in part["name"]:
                for v in part["vertices_world_m"]:v[0]-=.207
            if "deltoid_gold_marker" in part["name"]:
                for v in part["vertices_world_m"]:v[0]-=.185
            if "upper_arm_gold_marker" in part["name"]:
                for v in part["vertices_world_m"]:v[0]-=.170
            if "gold_knee" in part["name"]:
                for v in part["vertices_world_m"]:
                    v[0] += float(np.interp(v[2],[1.025,1.11,1.25,1.34],[.055,.105,.165,.125]))
            if "thigh_small_marker" in part["name"]:
                for v in part["vertices_world_m"]:v[0]-=.195
        # Blue U-yokes frame the small elbow barrel rather than leave a bare rod.
        outline=profiles["front"]["left_elbow_blue_yoke_visible"]
        g.panel(side+"_blue_elbow_yoke",side+"_upper_arm",outline if s==1 else mirror_outline(outline),
                -.100,.036,BLUE,.004,camber=.005)


def project_surface_details(g):
    """Attach reference seams/markers to the actual curved armor, along +X."""
    parts={p["name"]:p for p in g.parts}
    bindings={"forearm_gold_marker":"blue_forearm_wrap","forearm_upper_edge":"blue_forearm_wrap",
        "deltoid_gold_marker":"blue_deltoid_wrap","upper_arm_gold_marker":"ivory_lower_upper_arm",
        "thigh_small_marker":"blue_thigh_wrap","knee_small_marker":"yellow_front_knee_insert",
        "shank_small_marker":"blue_middle_shank_wrap"}
    rebuilt_edges=[]
    for part in list(g.parts):
        side=next((s for s in ("left","right") if part["name"].startswith(s+"_")),None)
        if not side:continue
        target=next((suffix for token,suffix in bindings.items() if token in part["name"]),None)
        if not target:continue
        surface=parts[side+"_"+target]
        v=np.asarray(surface["vertices_world_m"])
        triangles=np.asarray([[v[f[0]],v[f[i]],v[f[i+1]]] for f in surface["faces"] for i in range(1,len(f)-1)])
        if "forearm_upper_edge" in part["name"]:
            # The original edge lies on the silhouette. Moving individual tube
            # vertices to that silhouette collapses the tube's cross section.
            # Rebuild short closed segments around the projected centreline.
            original=np.asarray(part["vertices_world_m"])
            a,b=original[:8].mean(0),original[8:].mean(0)
            line=[];max_shift=0.
            for t in np.linspace(0,1,max(3,int(np.linalg.norm(b-a)/.012)+1)):
                p=(1-t)*a+t*b;hits=[];nearest=None
                for tri in triangles:
                    yz_point=p[1:];aa,bb,cc=tri[:,1:]
                    mat=np.column_stack((bb-aa,cc-aa))
                    if abs(np.linalg.det(mat))>1e-12:
                        uv=np.linalg.solve(mat,yz_point-aa)
                        w=np.array([1-uv.sum(),uv[0],uv[1]])
                        if w.min()>=-1e-7:hits.append(float(w@tri[:,0]))
                    for i,j in ((0,1),(1,2),(2,0)):
                        d=tri[j,1:]-tri[i,1:]
                        u=np.clip(np.dot(yz_point-tri[i,1:],d)/max(np.dot(d,d),1e-20),0,1)
                        q=(1-u)*tri[i]+u*tri[j];distance=np.linalg.norm(q[1:]-yz_point)
                        if nearest is None or distance<nearest[0]-1e-8 or (abs(distance-nearest[0])<=1e-8 and q[0]>nearest[1][0]):nearest=(distance,q)
                if hits:p[0]=max(hits)+.001
                else:
                    max_shift=max(max_shift,nearest[0]);p=nearest[1].copy();p[0]+=.001
                line.append(p)
            g.parts.remove(part)
            first=len(g.parts)
            g.tube(part["name"],part["body"],line,.0012,DARK,8)
            for edge in g.parts[first:]:
                edge.update({"attached_surface_part":surface["name"],
                    "surface_projection_unresolved_vertices":0,
                    "centreline_max_yz_attachment_shift_m":max_shift,
                    "reconstruction_note":"Thin opening seam rebuilt around the actual forearm surface; native closed cross section retained."})
                rebuilt_edges.append(edge)
            continue
        center_x=np.mean([p[0] for p in part["vertices_world_m"]])
        misses=0
        for p in part["vertices_world_m"]:
            yz_point=np.array(p[1:]);hits=[];nearest=None
            for tri in triangles:
                a,b,c=tri[:,1:]
                mat=np.column_stack((b-a,c-a));det=np.linalg.det(mat)
                if abs(det)>1e-12:
                    uv=np.linalg.solve(mat,yz_point-a)
                    weights=np.array([1-uv.sum(),uv[0],uv[1]])
                    if weights.min()>=-1e-7:hits.append(float(weights@tri[:,0]))
                for i,j in ((0,1),(1,2),(2,0)):
                    delta=tri[j,1:]-tri[i,1:]
                    t=np.clip(np.dot(yz_point-tri[i,1:],delta)/max(np.dot(delta,delta),1e-20),0,1)
                    q=(1-t)*tri[i]+t*tri[j];distance=np.linalg.norm(q[1:]-yz_point)
                    if nearest is None or distance<nearest[0]-1e-8 or (abs(distance-nearest[0])<=1e-8 and q[0]>nearest[1][0]):nearest=(distance,q)
            old_relative=p[0]-center_x
            if hits:p[0]=max(hits)+.002+old_relative
            elif nearest is not None and nearest[0]<.011:
                p[0]=float(nearest[1][0])+.002+old_relative
                p[1:]=nearest[1][1:].tolist()
            else:misses+=1
        part["attached_surface_part"]=surface["name"]
        part["edge_bevel_m"]=0
        part["surface_projection_unresolved_vertices"]=misses
        part["reconstruction_note"]="Original small marker/edge projected onto the actual armor surface; no floating decorative rods."


def build(spec):
    global FRONT_SHIELD_CONFIG
    FRONT_SHIELD_CONFIG=json.loads((ROBOT/"source/appearance_c_front_shape_constraints.json").read_text()).get("front_main_shield",{})
    g=Geometry(spec)
    # The narrow-tip main shield and thin crown are separate original features.
    g.panel("ivory_continuous_front_carapace","torso",
        [[254,101],[272,90],[302,86],[348,86],[380,91],[398,103],
         [387,138],[367,185],[340,258],[330,263],[315,262],[289,198],[272,153],[261,121]],
        chest_front,.039,IVORY,.007,camber=.012)
    g.panel("ivory_crown_top_lip","torso",
        [[257,101],[274,91],[303,87],[349,87],[378,92],[394,101],
         [378,111],[356,114],[296,114],[279,112]],
        lambda y,z:chest_front(y,z)+.014,.018,[.95,.93,.87,1],.004,camber=.008)
    g.panel("ivory_long_shield_face","torso",
        [[279,124],[294,118],[357,118],[373,125],[365,164],[353,199],
         [335,252],[326,259],[316,255],[299,206],[288,171]],
        lambda y,z:chest_front(y,z)+.020,.012,IVORY,.005,camber=.008)
    # Inset panel line around the crown, as shown on FRONT and TOP.
    g.seam("crown_top_panel_line","torso",[[274,99],[288,109],[361,109],[376,99]],
           lambda y,z:chest_front(y,z)+.034,.0012,color=[.46,.45,.41,1])
    for i,(px,py) in enumerate(((278,102),(296,111),(356,111),(375,102))):
        y,z=yz(px,py);g.bolt(f"crown_fastener_{i}","torso",[chest_front(y,z)+.037,y,z],radius=.004)
    # Back has a broad trapezoidal shell; rear pixel coordinates are normalized
    # to FRONT origin (the original REAR panel ground is 1215 rather than 603).
    rear_outline=[[244,109],[262,98],[298,92],[349,91],[381,100],[400,110],
                  [391,142],[383,194],[381,226],[369,253],[342,260],[294,260],
                  [273,251],[262,224],[257,194],[251,146]]
    g.panel("ivory_back_carapace","torso",rear_outline,chest_back,.039,IVORY,.007,rear=True,camber=.009)
    # Open dark carrier: hidden in front by the original ivory/blue armor.
    g.loft("dark_torso_inner_layer","torso",[
        ([.00,0,1.75],.13,.22),([.05,0,1.94],.23,.29),
        ([.03,0,2.15],.27,.37),([-.045,0,2.38],.25,.40),([-.10,0,2.54],.16,.35)],DARK,True,square=True)
    for side,s in (("left",1),("right",-1)):
        def out(p): return p if s==1 else mirror_outline(p)
        # Chest sides retain the staggered shoulders, vents and lower blue flanges.
        g.panel(side+"_blue_chest_flank","torso",out([
            [252,147],[275,145],[291,192],[307,250],[289,252],[273,244],
            [250,238],[244,221],[245,190]]),
            lambda y,z:.30+(.15 if z>2.08 else .02),.25,BLUE,.010,camber=.025)
        g.panel(side+"_blue_lower_chest_flange","torso",out([
            [253,212],[272,208],[290,243],[302,256],[277,251],[260,243],[252,228]]),
            lambda y,z:.35,.08,BLUE,.006,camber=.012)
        # Swept compact shoulders, in contrast to the rejected inflated blobs.
        g.panel(side+"_blue_shoulder_swept_top","torso",out([
            [212,113],[220,107],[251,101],[259,108],[269,127],[277,150],
            [259,154],[239,147],[225,132],[216,124]]),
            lambda y,z:.075+.10*(2.60-z),.38,BLUE,.012,camber=.017)
        g.panel(side+"_blue_shoulder_front_fold","torso",out([
            [218,121],[240,124],[266,146],[277,151],[261,157],[238,150],[225,137]]),
            .15,.046,[.012,.49,.79,1],.006,camber=.010)
        # Rear visible shoulder is slightly behind the crown.
        g.panel(side+"_blue_rear_shoulder","torso",out([
            [210,120],[218,113],[248,107],[266,129],[274,145],[252,150],[223,142]]),
            -.25,.055,BLUE,.009,rear=True,camber=.012)
        # Radiators have rounded inset frames, black wells and narrow louvers.
        y=s*(CX-260)*SCALE;z=(GROUND-185)*SCALE
        g.rounded_rect(side+"_radiator_ivory_socket","torso",[.477,y,z],.174,.333,.025,.034,IVORY)
        g.rounded_rect(side+"_radiator_gold_trim","torso",[.489,y,z],.137,.287,.012,.023,GOLD)
        g.rounded_rect(side+"_radiator_black_well","torso",[.493,y,z],.112,.266,.018,.016,BLACK)
        for i in range(13):
            zz=z-.120+i*.020
            g.box(side+f"_radiator_louver_{i:02}","torso",[.498,y,zz],[.007,.093,.0055],[.29,.29,.25,1],True)
            g.parts[-1]["edge_bevel_m"] = .001
        for zz in (z-.13,z+.13):
            for dy in (-.060,.060):
                g.bolt(side+f"_vent_fastener_{zz:.3f}_{dy:.3f}".replace("-","n").replace(".","p"),"torso",[.502,y+dy,zz],radius=.0038)
    # Slim vertical central indicator, flush with the long shield.
    zz=(GROUND-200)*SCALE;xx=chest_front(0,zz)+.042
    g.rounded_rect("central_indicator_recess","torso",[xx,0,zz],.069,.248,.010,.010,DARK)
    g.rounded_rect("central_indicator_gold_frame","torso",[xx+.002,0,zz],.054,.220,.006,.007,GOLD)
    g.rounded_rect("central_indicator_lit_strip","torso",[xx+.007,0,zz],.025,.185,.004,.004,[1,.83,.32,1])
    # Back service door follows REAR: rounded corners, inset dark seam, four screws.
    g.rounded_rect("rear_service_door_shadow","torso",[-.354,0,2.180],.310,.400,.010,.037,DARK,True)
    g.rounded_rect("rear_blue_service_door","torso",[-.359,0,2.180],.290,.380,.012,.027,BLUE,True)
    g.rounded_rect("rear_service_latch","torso",[-.374,0,2.320],.068,.026,.009,.007,DARK,True)
    g.rounded_rect("rear_door_upper_tab","torso",[-.336,0,2.425],.048,.054,.015,.008,BLUE,True)
    for i,(y,z) in enumerate(((-.113,2.027),(.113,2.027),(-.113,2.33),(.113,2.33))):
        g.bolt(f"rear_door_screw_{i}","torso",[-.377,y,z],axis=(-1,0,0),radius=.005)
    g.seam("rear_crown_panel_seam","torso",[[280,107],[296,131],[352,131],[370,107]],
           lambda y,z:chest_back(y,z)-.016,.0013,rear=True,color=[.46,.45,.41,1])
    # Short ivory coupler under the shield, then a compact saffron pelvis.
    g.panel("dark_central_waist_coupler","pelvis",[[308,263],[342,263],[338,275],[314,275]],.23,.10,DARK,.007,camber=.004)
    g.parts[-1].update({"role":"visible_mechanism",
        "reconstruction_note":"Dark compact FRONT waist coupling below the long ivory shield, distinct from the observed short white REAR connector. Appearance candidate, not a verified waist joint."})
    g.loft("dark_pelvis_inner_layer","pelvis",[([0,0,1.43],.105,.16),([0,0,1.62],.14,.18),([0,0,1.75],.12,.15)],DARK,True,square=True)
    g.panel("saffron_front_pelvis","pelvis",[[300,278],[308,275],[338,275],[348,282],
        [342,322],[336,344],[314,344],[305,322]],.302,.103,GOLD,.009,camber=.009)
    g.panel("saffron_pelvis_front_inset","pelvis",[[308,284],[335,284],[340,291],[333,333],[318,333]],.323,.007,[1,.69,.20,1],.004,camber=.003)
    g.rounded_rect("pelvis_front_black_latch","pelvis",[.339,0,1.410],.044,.061,.008,.008,DARK)
    g.panel("ivory_rear_sacral_cover","pelvis",[[307,294],[337,294],[335,340],[329,353],[316,353],[310,340]],-.217,.043,IVORY,.008,rear=True,camber=.01)
    g.panel("rear_saffron_crossbar","pelvis",[[274,278],[285,270],[312,276],[336,276],[360,270],[372,278],[369,286],[283,286]],-.195,.065,GOLD,.007,rear=True,camber=.008)
    for side,s in (("left",1),("right",-1)):
        def out(p):return p if s==1 else mirror_outline(p)
        sh=spec["points_world_m"][side+"_shoulder"]
        el=spec["points_world_m"][side+"_elbow"]
        # Upper shoulder porcelain cap and compact outer swept deltoid.
        g.panel(side+"_ivory_shoulder_cap",side+"_upper_arm",out([
            [202,130],[213,126],[221,136],[226,153],[225,170],[211,188],
            [198,178],[188,161],[190,145]]),.12,.22,IVORY,.009,camber=.022)
        g.panel(side+"_blue_deltoid_outer",side+"_upper_arm",out([
            [184,151],[195,153],[200,169],[197,194],[194,214],[172,217],
            [153,206],[160,183],[172,161]]),.15,.25,BLUE,.009,camber=.025)
        g.panel(side+"_blue_deltoid_front_plane",side+"_upper_arm",out([
            [185,155],[193,161],[195,184],[185,204],[167,208],[162,202],[170,183]]),
            .175,.021,[.013,.61,.92,1],.004,camber=.008)
        g.panel(side+"_ivory_upper_arm_link_cover",side+"_upper_arm",out([
            [204,184],[220,192],[229,210],[218,233],[204,250],[185,243],
            [182,230],[190,207]]),.165,.16,IVORY,.009,camber=.019)
        g.panel(side+"_ivory_upper_arm_inner_fold",side+"_upper_arm",out([
            [208,199],[219,211],[210,236],[203,244],[193,238],[197,218]]),
            .19,.015,[.96,.94,.87,1],.004,camber=.005)
        # Thick outward-biased blue forearm with slanted upper and lower openings.
        g.panel(side+"_blue_forearm_outer",side+"_forearm",out([
            [156,260],[181,269],[203,282],[208,307],[201,340],[190,359],
            [167,362],[146,370],[141,350],[138,309],[141,278]]),
            lambda y,z:.20+.022*math.sin((z-1.22)/.56*math.pi),.26,BLUE,.012,camber=.034)
        g.panel(side+"_blue_forearm_long_plane",side+"_forearm",out([
            [159,272],[176,276],[193,286],[196,307],[187,342],[177,355],[150,364],[147,343],[147,305]]),
            lambda y,z:.241+.012*math.sin((z-1.22)/.56*math.pi),.018,[.015,.61,.93,1],.006,camber=.008)
        # Upper lip is a separate bent edge, with an actual dark gap around the joint.
        g.seam(side+"_forearm_upper_edge",""+side+"_forearm",out([[151,263],[170,269],[188,278],[203,287]]),.211,.0022,color=DARK)
        for tag,pixels,xpos in (("deltoid",[[185,181],[190,177],[193,199],[189,202]],.190),
                               ("upper_arm",[[196,228],[200,228],[196,241],[192,240]],.216),
                               ("forearm",[[170,338],[175,337],[173,351],[169,352]],.267)):
            body=side+("_upper_arm" if tag!="forearm" else "_forearm")
            g.panel(side+"_"+tag+"_gold_marker",body,out(pixels),xpos,.008,GOLD,.002,camber=.002)
        # Ivory hip transition, blue thigh and the separate faceted yellow guard.
        g.panel(side+"_ivory_hip_cuff",side+"_thigh",out([
            [271,250],[287,249],[300,260],[296,269],[287,278],[272,271],[265,260]]),.090,.15,IVORY,.007,camber=.006)
        g.panel(side+"_blue_thigh_armor",side+"_thigh",out([
            [246,269],[268,270],[279,283],[290,309],[298,341],[297,364],
            [286,382],[272,393],[235,390],[221,377],[216,349],[220,315],[230,286]]),
            lambda y,z:.13+.070*math.sin((z-1.1)/.55*math.pi),.28,BLUE,.011,camber=.026)
        g.panel(side+"_blue_thigh_front_facet",side+"_thigh",out([
            [248,275],[264,277],[275,300],[282,332],[279,350],[250,348],[234,358],
            [228,340],[233,304]]),.222,.018,[.014,.61,.92,1],.007,camber=.005)
        g.panel(side+"_gold_knee_guard",side+"_thigh",out([
            [243,342],[273,348],[285,375],[280,392],[268,402],[243,399],[231,387],[231,368]]),
            .274,.082,GOLD,.008,camber=.012)
        g.panel(side+"_gold_knee_center_face",side+"_thigh",out([
            [247,349],[267,351],[278,376],[270,393],[250,390],[240,377]]),
            .293,.008,[1,.69,.20,1],.004,camber=.006)
        # Middle leg sweeps rearward in depth; deliberately asymmetrical armor.
        g.panel(side+"_blue_middle_shank",side+"_middle_shank",out([
            [218,429],[241,427],[266,431],[277,442],[275,464],[265,491],
            [244,504],[218,499],[207,484],[202,457],[205,441]]),
            lambda y,z:float(np.interp(z,[.52,.70,.88],[.065,.19,.275])),.19,BLUE,.010,camber=.020)
        g.panel(side+"_blue_shank_front_plane",side+"_middle_shank",out([
            [222,434],[243,435],[263,439],[259,466],[243,496],[222,493],[211,477],[211,454]]),
            lambda y,z:float(np.interp(z,[.52,.70,.88],[.093,.215,.305])),.015,[.02,.61,.92,1],.006,camber=.008)
        g.panel(side+"_blue_distal_front_guard",side+"_distal_shank",out([
            [213,513],[239,514],[246,531],[239,543],[207,541],[208,528]]),
            .055,.055,BLUE,.006,camber=.009)
        g.panel(side+"_ivory_distal_side_tab",side+"_distal_shank",out([
            [245,524],[252,528],[250,543],[240,548],[238,542]]),-.035,.022,IVORY,.004,camber=.004)
        for tag,pixels,xpos in (("thigh",[[261,281],[265,281],[263,291],[260,291]],.224),
                               ("knee",[[234,366],[239,363],[237,378],[233,379]],.290),
                               ("shank",[[208,447],[211,446],[210,458],[207,458]],.231)):
            body=side+("_thigh" if tag!="shank" else "_middle_shank")
            g.panel(side+"_"+tag+"_small_marker",body,out(pixels),xpos,.004,GOLD if tag!="knee" else METAL,.001,camber=.001)
    refine_volumes(g,spec)
    from gorilla_appearance_mechanics import add_mechanics
    first_mechanics=len(g.parts)
    add_mechanics(g,spec["points_world_m"],PALETTE)
    from gorilla_primary_structure import add_primary_structure
    add_primary_structure(g,spec["points_world_m"],PALETTE)
    from gorilla_composite_foot import replace_composite_feet
    replace_composite_feet(g,spec["points_world_m"],PALETTE)
    # These parts already have native bevel/lathe profiles. Additional blanket
    # bevels collapsed tiny ring/knuckle edges in round-three GLB topology.
    for part in g.parts[first_mechanics:]:part["edge_bevel_m"]=0
    for part in g.parts:
        if any(token in part["name"] for token in ("small_marker","dark_central_waist_coupler","ivory_distal_side_tab")):
            part["edge_bevel_m"]=0
    rear_landmarks=json.loads((ROBOT/"source/appearance_c_reference_landmarks.json").read_text())
    rear_profiles={v:{p["id"]:p["global_uv_px"] for p in info["profiles"]} for v,info in rear_landmarks["views"].items()}
    separate_leg_rear_skins(g,rear_profiles)
    project_surface_details(g)
    return g


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec",type=Path,default=ROBOT/"configs/appearance_c_spec.json")
    p.add_argument("--output",type=Path,default=ROBOT/"cad/source/appearance_c_scene.json")
    args=p.parse_args()
    spec=json.loads(args.spec.read_text())
    image=ROBOT/spec["appearance_authority"]["path"]
    if sha(image)!=spec["appearance_authority"]["sha256"]:raise ValueError("Sole artwork identity changed")
    g=build(spec)
    v=np.concatenate([np.array(p["vertices_world_m"]) for p in g.parts])
    scripts=[Path(__file__),Path(__file__).with_name("gorilla_appearance_mechanics.py"),Path(__file__).with_name("gorilla_primary_structure.py"),Path(__file__).with_name("gorilla_composite_foot.py"),ROOT/"src/sai_agent/structural_statics.py",ROBOT/"configs/structure_c14_spec.json",Path(__file__).with_name("build_gorilla_proportion_layout.py"),ROBOT/"source/appearance_c_reference_landmarks.json",ROBOT/"source/appearance_c_front_shape_constraints.json"]
    scene={
        "schema":"gorilla_appearance_scene_v2","robot_id":"gorilla_v0_1","checkpoint_id":"gorilla_appearance_c",
        "spec_path":str(args.spec.relative_to(ROOT)),"spec_sha256":sha(args.spec),
        "appearance_authority_path":str(image.relative_to(ROOT)),"image_sha256":sha(image),
        "units":"m","coordinate_frame":spec["coordinate_frame"],"rgba_encoding":"sRGB converted to linear by renderer",
        "parts":g.parts,"bounds_world_m":[v.min(axis=0).tolist(),v.max(axis=0).tolist()],"dimensions_xyz_m":np.ptp(v,axis=0).tolist(),
        "build_inputs":[{"path":str(x.relative_to(ROOT)),"sha256":sha(x)} for x in scripts],
        "physical_parameters_status":"not_assigned_appearance_reconstruction_only",
        "appearance_accepted":False,"physics_accepted":False,
        "uncertainties":["Artwork cameras, illumination and four-view poses are not calibrated.","Hidden depths and unseen mechanism surfaces are reconstructed candidates.","Display grouping uses historical body names; it is not a new physical joint contract.","Explicit bevel modifiers are applied identically before all rendering and export."],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(scene,indent=2)+"\n")
    print(json.dumps({"scene":str(args.output),"parts":len(g.parts),"dimensions_xyz_m":scene["dimensions_xyz_m"]}))


if __name__=="__main__":main()
