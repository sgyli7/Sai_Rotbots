"""Native, hollow, continuously rounded Goose 056 limb enclosures.

The original carriers, motors, bearings and contact soles remain the datum.
This module creates removable protective skins, never replacement load members.
Dimensions are world millimetres.  The skins are variable-section 3D lofts,
not constant-depth extrusions of the rejected 053 drawing.
"""
from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.interpolate import PchipInterpolator
from cadgen import build123d as b
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.Approx import Approx_IsoParametric, Approx_ChordLength
from OCP.GeomAbs import GeomAbs_C2
from OCP.TopoDS import TopoDS
from OCP.BRepAlgoAPI import BRepAlgoAPI_Check
from OCP.BRepCheck import BRepCheck_Analyzer

ROOT = Path(__file__).resolve().parents[2]
WALL = 1.8


def _compound(shape):
    if isinstance(shape, (list, tuple, b.ShapeList)):
        return b.Compound(children=list(shape))
    return shape


def _cut(shape, *tools):
    result = _compound(shape.cut(*tools))
    assert result and result.solids() and result.is_valid
    return result


def _capsule(a, c, ra, rc, waist, y):
    """Round-ended link section with tangent organic waist, in an XZ plane."""
    a, c = np.asarray(a, float), np.asarray(c, float)
    delta = c - a
    length = float(np.linalg.norm(delta))
    tangent = delta / length
    normal = np.array([-tangent[1], tangent[0]])

    def p(u, v):
        q = a + u * tangent + v * normal
        return (float(q[0]), float(y), float(q[1]))

    return b.Wire([
        b.Edge.make_three_point_arc(p(0, ra), p(-ra, 0), p(0, -ra)),
        b.Edge.make_bezier(p(0, -ra), p(.18*length, -ra), p(.37*length, -waist),
                           p(.63*length, -waist), p(.82*length, -rc), p(length, -rc)),
        b.Edge.make_three_point_arc(p(length, -rc), p(length+rc, 0), p(length, rc)),
        b.Edge.make_bezier(p(length, rc), p(.82*length, rc), p(.63*length, waist),
                           p(.37*length, waist), p(.18*length, ra), p(0, ra)),
    ])


def _link_volume(a, c, stations, inset=0):
    """Vary both width and waist across the side-to-side dome."""
    side = 1 if a[1] > 0 else -1
    wires = []
    for k, (y, ra, rc, waist) in enumerate(stations):
        yy = y
        if inset:
            if k == 0:
                yy += inset
            if k == len(stations)-1:
                yy -= inset
        wires.append(_capsule(a[[0, 2]], c[[0, 2]],
                              max(.2, ra-inset), max(.2, rc-inset),
                              max(.15, waist-inset), yy*side))
    return b.Solid.make_loft(wires, ruled=False)


def _quarter_circle_y(center,radius,y):
    """Exact circular wire with four non-periodic analytic arc parameters.

    The four arcs describe the same circle; they avoid a single periodic face
    acquiring ambiguous wire orientation after native hidden-interface cuts.
    """
    def p(t):return (center[0]+radius*math.cos(t),y,center[2]+radius*math.sin(t))
    return b.Wire([b.Edge.make_three_point_arc(p(k*math.pi/2),
            p((k+.5)*math.pi/2),p((k+1)*math.pi/2)) for k in range(4)])


def _axis_y_volume(center,stations,radial_extra=0):
    side=1 if center[1]>0 else -1
    return _controlled_loft([_quarter_circle_y(center,r+radial_extra,y*side)
                             for y,r in stations])


def _controlled_loft(profiles,param_type=Approx_IsoParametric,ruled=False):
    maker = BRepOffsetAPI_ThruSections(True, ruled, 1e-7)
    maker.CheckCompatibility(False)
    maker.SetMaxDegree(3)
    maker.SetParType(param_type)
    maker.SetContinuity(GeomAbs_C2)
    maker.SetSmoothing(False)
    for profile in profiles:
        if isinstance(profile, b.Vertex):
            maker.AddVertex(profile.wrapped)
        else:
            maker.AddWire(profile.wrapped)
    maker.Build()
    assert maker.IsDone()
    return b.Solid(TopoDS.Solid_s(maker.Shape()))


def _round_cross(x, yc, wy, rz, corner=6):
    """Rounded 3D cross section enclosing actual wide carrier corners."""
    plane=b.Plane(origin=(x,yc,0),x_dir=(0,1,0),z_dir=(1,0,0))
    return (plane*b.RectangleRounded(2*wy,2*rz,corner)).wires()[0]


def _longitudinal_link(length, yc, inset=0):
    # Profiles run down the actual link. There is no long flat face at the
    # outboard Y extreme, which caused the rejected raised longitudinal strip.
    distal_depth = 36 if length > 120 else 42
    waist = 23.3 if length > 120 else 22.3
    root_depth = 52 if length > 120 else 46
    mid_depth = 52 if length > 120 else 40
    sections = [(-34, root_depth-10, 27), (-20, root_depth-3, 39), (0, root_depth, 44),
                (25, root_depth-1, 28 if length > 120 else 31),
                (35,mid_depth,waist),(length/2,mid_depth,waist),
                (length-35,distal_depth+2,waist),
                (length-25, distal_depth+1, 28), (length, distal_depth, 42),
                (length+24, distal_depth-10, 31), (length+35, distal_depth-26, 16)]
    def centre(x):
        return float(np.interp(x,[0,length/2,length],
               [122.75,122.75,119.75] if length>120 else [114.5,129.5,127.875]))
    profiles = [b.Vertex(-45+inset, centre(-45), 0)]
    station_array=np.asarray(sections,float)
    interpolate=PchipInterpolator(station_array[:,0],station_array[:,1:],axis=0)
    for x in np.linspace(station_array[0,0],station_array[-1,0],61):
        wy,rz=interpolate(x)
        profiles.append(_round_cross(x,centre(x),wy-inset,
                       rz-(min(inset,1.2) if rz<24 else inset),max(2.,6-inset)))
    profiles.append(b.Vertex(length+44-inset, centre(length+44), 0))
    return _controlled_loft(profiles,ruled=True)


def _hollow_link(a, c, stations, wall=WALL):
    """Independently loft outer and inner sections, then place at real axes.

    Section offsets are directional; this is not a certified constant-normal
    wall or an OCCT normal-offset operation. Physical pivots stay unchanged.
    """
    delta = c-a
    length = float(np.linalg.norm(delta[[0, 2]]))
    dx, dz = delta[0]/length, delta[2]/length
    yc = 118.0 if length < 120 else 125.0
    outer = _longitudinal_link(length, yc)
    # Direct offset of this deeply waisted loft produced invalid self-
    # intersections despite a positive BRepCheck verdict. A controlled inner
    # section-defined cavity is explicit, reproducible and BOP-valid. Thickness
    # varies with section and must not be advertised as constant-normal wall.
    inner = _longitudinal_link(length, yc, inset=wall)
    skin = _cut(outer, inner)
    # A proper rotation about Y plus translation, retaining analytic circles.
    angle = -float(np.degrees(np.arctan2(dz, dx)))
    skin = skin.rotate(b.Axis.Y, angle).translate((a[0], 0, a[2]))
    outer = outer.rotate(b.Axis.Y, angle).translate((a[0], 0, a[2]))
    inner = inner.rotate(b.Axis.Y, angle).translate((a[0], 0, a[2]))
    if a[1] < 0:
        skin = skin.mirror(b.Plane.XZ)
        outer = outer.mirror(b.Plane.XZ)
        inner = inner.mirror(b.Plane.XZ)
    # Do not retain local .children after placing a multi-solid Part: older
    # build123d Boolean traversal can otherwise use the unmoved children.
    skin = b.Compound(children=[b.Solid(s.wrapped) for s in skin.solids()])
    outer = b.Solid(outer.solids()[0].wrapped)
    return outer, skin, b.Solid(inner.solids()[0].wrapped)


def _cylinder_y(center,radius,lo=0,hi=220):
    # Four analytic cylindrical faces retain unchanged radius/axis/extent.
    # Do not merge them back to one periodic surface during Boolean cleanup.
    side=1 if center[1]>0 else -1
    return b.Solid.extrude(b.Face(_quarter_circle_y(center,radius,side*lo)),
                           (0,side*(hi-lo),0))


def _incoming_link_clearance(a, c, half_width, ylo=60, yhi=195):
    delta = c[[0, 2]]-a[[0, 2]]
    tangent = delta/np.linalg.norm(delta)
    normal = np.array([-tangent[1], tangent[0]])
    lo, hi = a[[0, 2]]-20*tangent, c[[0, 2]]+10*tangent
    xz = [lo+normal*half_width, hi+normal*half_width,
          hi-normal*half_width, lo-normal*half_width]
    points = [(float(q[0]), ylo, float(q[1])) for q in xz]
    wire = b.Wire([b.Edge.make_line(points[i], points[(i+1)%4]) for i in range(4)])
    return b.Solid.extrude(b.Face(wire), (0, yhi-ylo, 0))


def _continuous_knee_mouth(center):
    """One analytic continuous incoming-arm mouth beyond the round cap.

    Local angular interval includes the real incoming-arm sweep over the
    unchanged left K[-1.8,+0.2] range. It is not a row of sampled drill cuts.
    The R44.5 outer cap remains untouched; this mouth is a motion interface.
    """
    a0,a1=np.radians([-65,105]);am=(a0+a1)/2
    def p(r,a):return (center[0]+r*np.cos(a),80,center[2]+r*np.sin(a))
    r0,r1=44.9,55.2
    wire=b.Wire([b.Edge.make_three_point_arc(p(r1,a0),p(r1,am),p(r1,a1)),
                 b.Edge.make_line(p(r1,a1),p(r0,a1)),
                 b.Edge.make_three_point_arc(p(r0,a1),p(r0,am),p(r0,a0)),
                 b.Edge.make_line(p(r0,a0),p(r1,a0))])
    return b.Solid.extrude(b.Face(wire),(0,100,0))


def _ankle_barrel(center, inset=0):
    radius, lo, hi = 39.2-inset, 70+inset, 180-inset
    solid = _cylinder_y(center, radius, lo, hi)
    circles = [e for e in solid.edges() if e.geom_type == b.GeomType.CIRCLE]
    return solid.fillet(10-inset, circles)


def _knee_barrel(center, inset=0):
    lo,hi=71.5+inset,178.8-inset
    solid = _cylinder_y(center,44.5-inset,lo,hi)
    low=[e for e in solid.edges() if e.geom_type==b.GeomType.CIRCLE
         and abs(abs(e.center().Y)-lo)<1e-5]
    solid=solid.fillet(3-inset,low)
    high=[e for e in solid.edges() if e.geom_type==b.GeomType.CIRCLE
          and abs(abs(e.center().Y)-hi)<1e-5]
    return solid.fillet(8-inset,high)


def _hip_barrel(center, inset=0):
    """Open R49 torso throat, ending in a rounded closed outboard cheek.

    The real primary carrier has ears past the spherical link end. Preserve
    the agreed R49/R47.2 circular interface and give those ears a true cavity.
    """
    hi=164-inset
    solid=_cylinder_y(center,49-inset,92.3 if inset else 92.5,hi)
    front=[e for e in solid.edges() if e.geom_type == b.GeomType.CIRCLE
           and abs(abs(e.center().Y)-hi)<1e-5]
    return solid.fillet(6-inset,front)


def _cylinder_x(center, radius, lo, hi, rear_fillet=0):
    solid = b.Solid.make_cylinder(radius, hi-lo,
               b.Plane(origin=(lo, center[1], center[2]),
                       x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
    if rear_fillet:
        rear = [e for e in solid.edges() if e.geom_type == b.GeomType.CIRCLE
                and abs(e.center().X-lo) < 1e-5]
        solid = solid.fillet(rear_fillet, rear)
    return solid


def _xz_box(lo, hi):
    return b.Solid.make_box(hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2], b.Plane(origin=lo))


def _shoe_cross(x, y, base_width, centre_z, radius_y, radius_z,
                floor=7.8, shoulder=20):
    ratio = (shoulder-centre_z)/radius_z
    assert -1 < ratio < 0
    alpha = float(np.degrees(np.arcsin(ratio)))
    pl = b.Plane(origin=(x, y, centre_z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    arch = b.Edge.make_ellipse(radius_y, radius_z, pl, alpha, 180-alpha)
    right, left = arch.position_at(0), arch.position_at(1)
    rb, lb = (x, y+base_width, floor), (x, y-base_width, floor)
    re = b.Edge.make_bezier(rb, (x, y+base_width, floor+3),
                          (right.X, right.Y-1, right.Z-3), right)
    le = b.Edge.make_bezier(left, (left.X, left.Y+1, left.Z-3),
                          (x, y-base_width, floor+3), lb)
    return b.Wire([re, arch, le, b.Edge.make_line(lb, rb)])


def _coaxial_ar_shoe_volume(ar, inset=0):
    """Rear crown is an actual X-coaxial arc, joined to a rounded toe loft."""
    y, z = float(ar[1]), float(ar[2])
    floor = 7.8-(4 if inset > 0 else 0)
    r = 41.4-inset
    rear = _cylinder_x(ar, r, -20, 81.7)
    rear = _cut(rear, _xz_box((-100, -300, -100), (200, 300, floor)))
    side_at_shoulder = float(np.sqrt(r*r-(20-z)**2))
    bw = 36-inset
    points = [(-20, y-bw, floor), (-20, y+bw, floor),
              (-20, y+side_at_shoulder, 20), (-20, y-side_at_shoulder, 20)]
    band_face = b.Face(b.Wire([b.Edge.make_line(points[i], points[(i+1)%4]) for i in range(4)]))
    band = b.Solid.extrude(band_face, (101.7, 0, 0))
    rear = _compound(rear.fuse(band))
    def arch(x, width, top):
        w, h = width-inset, top-inset-floor
        left = [(x,y-w,floor),(x,y-w,floor+.8*h),(x,y-.6*w,floor+h),(x,y,floor+h)]
        right = [(x,y,floor+h),(x,y+.6*w,floor+h),(x,y+w,floor+.8*h),(x,y+w,floor)]
        return b.Wire([b.Edge.make_bezier(*left),b.Edge.make_bezier(*right),
                       b.Edge.make_line(right[-1],left[0])])
    heel = _controlled_loft([arch(-29.5+inset, 8, 22), arch(-26,25,59),
                             arch(-21,36,80),arch(-16,41.4,82.055)])
    toe = _controlled_loft([arch(77.5,41.4,82.055),arch(83,41.4,82.055),
                            arch(95,39,76),arch(105,37,64),arch(117,35,45),
                            arch(122,32,31),arch(125.8-inset,15,18)])
    volume = _compound(rear.fuse(heel, toe))
    # The cosmetic heel/toe loft must stay inside the real X-coaxial lap.
    # Retain the wider low basal seat for the actual plate and clips, below
    # Z20, rather than enlarging the entire crown around those small features.
    upper_rear_box = _xz_box((-60, y-100, 20), (81.7, y+100, 140))
    radial_limit = _cylinder_x(ar, r, -65, 82)
    return _cut(volume, _cut(upper_rear_box, radial_limit))


def _ar_bridge_window(ar):
    # The stationary AP bridge is allowed through the inside of the shoe.
    # The AP outer hood covers this 65-degree roof window, including the
    # full +/-0.5 rad AR range; it is not an exposed exterior opening.
    angle = np.radians(65)
    y, z = float(ar[1]), float(ar[2])
    points = [(-12.5, y, z), (-12.5, y+200*np.sin(angle), z+200*np.cos(angle)),
              (-12.5, y-200*np.sin(angle), z+200*np.cos(angle))]
    face = b.Face(b.Wire([b.Edge.make_line(points[i], points[(i+1)%3]) for i in range(3)]))
    return b.Solid.extrude(face, (93.5, 0, 0))


def _gaiter_cross(x, y, base, broad, floor, top):
    shoulder = top-25
    def p(v,z): return (x,y+v,z)
    left = b.Edge.make_bezier(p(-base,floor), p(-base,floor+35),
                               p(-broad,shoulder-25), p(-broad,shoulder))
    top_left = b.Edge.make_bezier(p(-broad,shoulder), p(-broad,top),
                                   p(-broad,top), p(0,top))
    top_right = b.Edge.make_bezier(p(0,top), p(broad,top),
                                    p(broad,top), p(broad,shoulder))
    right = b.Edge.make_bezier(p(broad,shoulder),p(broad,shoulder-25),
                                p(base,floor+35),p(base,floor))
    return b.Wire([left,top_left,top_right,right,
                   b.Edge.make_line(p(base,floor),p(-base,floor))])


def _gaiter_volume(ar, inset=0):
    y=float(ar[1])
    # Continuous boot surface with a broad rounded instep over the measured
    # actual AP case/frame, narrowing to the unchanged sole interface.
    stations=[(-31,5,5,18,87),(-29,18,39,7.8,117),
              (-23,37,44,7.8,123),(-10,39,47,7.8,126),
              (10,39,47,7.8,127),(38,39,46,7.8,118),
              (65,39,43,7.8,95),(78,39,42,7.8,85),
              (80.5,38,40,7.8,82),(83,36.8,37.8,7.8,77.4),
              (86,36.8,37.8,7.8,77.4)]
    samples=np.asarray(stations,float)
    section_values=PchipInterpolator(samples[:,0],samples[:,1:],axis=0)
    xs=np.linspace(samples[0,0],samples[-1,0],81)
    profiles=[]
    for i,x in enumerate(xs):
        base,broad,floor,top=section_values(x)
        if inset:
            floor = floor+inset if x < -29 else floor-4
            x += inset if i==0 else (0.3 if i==len(xs)-1 else 0)
        profiles.append(_gaiter_cross(x,y,base-inset,broad-inset,floor,top-inset))
    # Densely sampled monotone section curves with ruled native faces avoid
    # the global cubic loft folding its front retention spigot back on itself.
    # These are real CAD faces; transverse sections remain smoothly rounded.
    return b.Solid.make_loft(profiles,ruled=True)


def _rigid_toe_volume(ar,inset=0):
    y=float(ar[1]);floor=7.8-(4 if inset else 0)
    stations=np.asarray([(82.7,41.4,82.055),(95,39,76),(105,37,64),
                         (117,35,45),(122,32,31),(125.8,15,18)],float)
    interp=PchipInterpolator(stations[:,0],stations[:,1:],axis=0)
    xs=np.linspace(82.7,125.8,33);profiles=[]
    for i,x in enumerate(xs):
        width,top=interp(x);width-=inset;top-=inset;h=top-floor
        x=x-.3 if inset and i==0 else (x-inset if i==len(xs)-1 else x)
        left=[(x,y-width,floor),(x,y-width,floor+.8*h),
              (x,y-.6*width,floor+h),(x,y,floor+h)]
        right=[(x,y,floor+h),(x,y+.6*width,floor+h),
               (x,y+width,floor+.8*h),(x,y+width,floor)]
        profiles.append(b.Wire([b.Edge.make_bezier(*left),b.Edge.make_bezier(*right),
                                 b.Edge.make_line(right[-1],left[0])]))
    return b.Solid.make_loft(profiles,ruled=True)


def _complete_soft_shoe_volume(ar,inset=0):
    """Continuous rounded upper; true elliptic crown and a tucked curved heel.

    Cap radii follow the AP case/retainer and collector height zones.  The
    high transverse shoulder is removed rather than lowering the toe tip.
    Equal X sections are interpolated as one controlled cubic native loft;
    the result is a smooth surface, not a normal-smoothed ruled strip mesh.
    """
    y=float(ar[1])
    stations=np.asarray([(-36,.8,.8,82,86,2),(-35,8,22,50,104,20),
        (-33.5,18,38,26,115,22),(-31.5,26,43,12,119,22),
        (-29.5,34,44,7.8,121,22),(-27.5,35,44,7.8,122,22),(-23,37,44,7.8,121,22),
        (-10,39,47,7.8,124,26),(10,39,47,7.8,127,30),
        (25,39,46.5,7.8,120,26),(38,39,46,7.8,108,18),(45,39,45.2,7.8,107,17),
        (50,39,44.5,7.8,104,15),(65,39,43,7.8,84,18),
        (74,39,42.3,7.8,82,14),(78,39,42,7.8,80,14),
        (84,40.5,41.4,7.8,78.5,18),(95,39,39,7.8,76,26),
        (105,37,37,7.8,64,32),(117,35,35,7.8,45,32),
        (122,32,32,7.8,31,21),(125.8,15,15,7.8,18,9)],float)
    interpolate=PchipInterpolator(stations[:,0],stations[:,1:],axis=0)
    profiles=[]
    for i,x in enumerate(np.linspace(-36,125.8,113)):
        base,broad,floor,top,cap=interpolate(x)
        if inset:
            # C2 end contraction preserves positive longitudinal spacing.
            # Localising it at the end caps avoids unnecessary midfoot wall
            # growth and retains the measured rear-fork/CSK cavity envelope.
            blend=float(np.clip((x+29.5)/6.0,0,1))
            blend=blend*blend*(3-2*blend)
            floor+=inset*(1-blend)-4*blend
            def smooth5(q):
                q=float(np.clip(q,0,1))
                return q*q*q*(10+q*(-15+6*q))
            x+=inset*(1-smooth5((x+36)/13)-smooth5((x-105)/20.8))
        base=max(.15,base-inset);broad=max(.15,broad-inset);top-=inset
        cap=max(.15,min(cap-inset,.96*(top-floor)));equator=top-cap
        lower=max(.1,equator-floor)
        def p(v,z):return (x,y+v,z)
        plane=b.Plane(origin=(x,y,equator),x_dir=(0,-1,0),z_dir=(-1,0,0))
        profiles.append(b.Wire([
            b.Edge.make_bezier(p(-base,floor),p(-base,floor+.52*lower),
                              p(-broad,equator-.38*lower),p(-broad,equator)),
            b.Edge.make_ellipse(broad,cap,plane,0,90),
            b.Edge.make_ellipse(broad,cap,plane,90,180),
            b.Edge.make_bezier(p(broad,equator),p(broad,equator-.38*lower),
                              p(base,floor+.52*lower),p(base,floor)),
            b.Edge.make_line(p(base,floor),p(-base,floor))]))
    return _controlled_loft(profiles,ruled=False)


def _compliant_complete_shoe(ankle, ar, shin_outer, shin_cavity, shin):
    """Real single-material TPU shoe and upper joint tongue, zero-pose form.

    The retained sole, metal plate, saddles and clips carry the load. This soft
    enclosure spans AP/AR and the shin lip; material deformation is unqualified.
    Outer volumes are united before the shared cavity is removed so that no
    artificial midfoot membrane or external toe seam is introduced.
    """
    near=_cylinder_y(ankle,57,20,230)
    throat=_compound(shin_outer.intersect(near))
    throat_cavity=_compound(shin_cavity.intersect(
        _cylinder_y(ankle,59,20,230)))
    outer=_compound(_complete_soft_shoe_volume(ar).fuse(throat))
    inner=_compound(_complete_soft_shoe_volume(ar,1.2).fuse(throat_cavity))
    y=float(ar[1]);bottom=_xz_box((-70,y-120,-100),(160,y+120,7.81))
    return _cut(outer,inner,bottom,shin)


def _placed_link_volume(a,c,inset):
    d=c-a;length=float(np.linalg.norm(d[[0,2]]))
    angle=-float(np.degrees(np.arctan2(d[2],d[0])))
    return _longitudinal_link(length,125.,inset).rotate(b.Axis.Y,angle).translate((a[0],0,a[2]))


def _soft_knee_sleeve(hp,knee,ankle,thigh,shin,torso_clearance):
    """A real thin exterior sleeve behind the retained R44.5 cheek.

    The 1mm directional skin sits 0.3mm outside the prior parent envelope,
    keeping the motion mouth closed without filling it with a solid block.
    Its upper lip follows the unchanged thigh and needs physical retention.
    """
    outer=_compound(_placed_link_volume(knee,ankle,-1.3).fuse(
        _placed_link_volume(hp,knee,-1.3),_knee_barrel(knee,-1.3)))
    inner=_compound(_placed_link_volume(knee,ankle,-.3).fuse(
        _placed_link_volume(hp,knee,-.3),_knee_barrel(knee,-.3)))
    near=_cylinder_y(knee,58,20,230)
    sleeve=_compound(outer.intersect(near))
    sleeve=_cut(sleeve,inner,thigh,shin,torso_clearance)
    # A real 0.30mm hidden edge relief removes the measured re-entrant
    # body/boot trim cusp (0.073mm triangular face), rather than accepting
    # its native self-intersection or altering the retained body/load metal.
    relief=b.Solid.make_sphere(.30,b.Plane(origin=(knee[0]+28.019829893573926,
                                                  87.003,knee[2]+38.6652381714886)))
    return _cut(sleeve,relief)


def _remove_isolated_socket_trim(shape, *joints):
    """A socket removes its complete terminal trim, not a floating ring.

    Keep the main connected link skin only when every detached remnant lies
    wholly within the intended terminal joint neighbourhood. This operation
    is part of defining the socket lip, not an escape for arbitrary invalid
    topology or interference.
    """
    solids = sorted(shape.solids(), key=lambda s: s.volume, reverse=True)
    if len(solids) == 1:
        return solids[0]
    for orphan in solids[1:]:
        box = orphan.bounding_box()
        corners = np.array([[x, y, z] for x in [box.min.X, box.max.X]
                            for y in [box.min.Y, box.max.Y]
                            for z in [box.min.Z, box.max.Z]])
        assert min(np.max(np.linalg.norm((corners-np.asarray(joint))[:, [0, 2]], axis=1))
                   for joint in joints) < 75
        assert orphan.volume < .08*solids[0].volume
    return solids[0]


def _shoe_section(x, y0, z0, half_width, height, exponent=3.4):
    """A broad but continuously curved crown, ending at its sole interface."""
    angles = np.linspace(0, np.pi, 25)
    points = [(x, y0+half_width*np.sign(np.cos(q))*abs(np.cos(q))**(2/exponent),
               z0+height*np.sin(q)**(2/exponent)) for q in angles]
    arch = b.Edge.make_spline(points)
    return b.Wire([arch, b.Edge.make_line(points[-1], points[0])])


def _shoe_volume(y, inset=0):
    # The taller heel/instep encloses the real retained AR case and steel
    # collector. The toe descends continuously; there is no applied toe patch.
    stations = [(7.8, 48.3, 78.0, 36.0), (18, 48.0, 77.8, 37.5),
                (37, 47.0, 73.0, 37), (55, 43.0, 62.5, 35.5),
                (70, 36.0, 50.0, 32.5), (81, 27.0, 34.0, 26),
                (88, 19.0, 16.0, 15)]
    profiles = [(b.Plane(origin=(x, y, z-(4 if k == 0 and inset else inset)))*
                 b.Ellipse(rx-inset, ry-inset)).wires()[0]
                for k, (z, x, rx, ry) in enumerate(stations)]
    profiles.append(b.Vertex(17, y, 91-inset))
    return _controlled_loft(profiles)


def _build_native_skins(context):
    pivots = context['pivots']
    wall = float(context.get('nominal_wall_mm', WALL))
    result = []
    # The real hip throat uses the approved R49 moving/R49.7 torso interface.
    # Legacy station tables below are unused by the section-defined loft.
    thigh_stations = [(65.5, 14, 10, 7), (69.8, 35.5, 29, 21),
                      (72.0, 39.5, 36, 25), (85, 39.5, 40.5, 27),
                      (105, 39.5, 43, 28), (113, 39.5, 44, 28),
                      (131, 44.5, 45, 29), (152, 44, 45, 29),
                      (166, 38, 39, 26), (174, 23, 24, 18),
                      (178, 2, 2, 1)]
    shin_stations = [(68.5, 9, 8, 6), (73, 38, 29, 22),
                     (78, 41, 35, 26), (92, 42.5, 38, 27),
                     (115, 43, 39.2, 28), (137, 44.5, 40, 29),
                     (159, 44, 39.2, 28), (174, 37, 33, 25),
                     (181, 20, 19, 16), (185, 2, 2, 1)]
    ankle_stations = [(78, 5), (82, 30), (86, 38), (94, 39.2),
                      (151, 39.2), (162, 36), (168, 24), (172, 5)]

    def add(name, shape, role, body, assumptions, retire=(),
            material='PA12_design_budget', density=1010., part_wall=None):
        shape = _compound(shape)
        assert shape.is_valid and len(shape.solids()) == 1 and shape.volume > 0, name
        if not BRepAlgoAPI_Check(shape.wrapped).IsValid():
            b.export_brep(shape,str(Path(context['artifacts'])/('invalid_'+name+'.brep')))
            raise AssertionError(name+' strict BOP invalid')
        shape.label = name
        result.append(dict(name=name, shape=shape, role=role, mount_body=body,
                           nominal_wall_mm=wall if part_wall is None else part_wall,
                           assumptions=assumptions,
                           density_kg_m3=density, material=material,
                           retire_previous_cosmetic=list(retire)))
        if material.startswith('TPU'):
            result[-1].update(deformable=True,
                attachment_bodies=([body.replace('knee_pitch','hip_pitch'),body]
                  if 'knee_sleeve' in name else
                  [body.replace('ankle_roll','knee_pitch'),body.replace('ankle_roll','ankle_pitch'),body]),
                hidden_edge_retention='Candidate concealed compression/underlap edge; dimensions and fastener preload not released',
                mass_body_assignment='Bookkeeping approximation for a future physics candidate; not frozen15 MCI',
                deformation_qualified=False,fatigue_qualified=False)

    for side in ['left']:
        print('BUILD_LIMB', side, flush=True)
        hp, knee, ankle = [np.asarray(pivots[side+'_'+j], float)
                            for j in ['hip_pitch', 'knee_pitch', 'ankle_pitch']]
        thigh_outer, thigh, thigh_cavity = _hollow_link(hp, knee, thigh_stations, wall)
        # The child's real coaxial dome fills this purposeful socket; it is
        # not an exposed decorative through-hole in the assembled exterior.
        knee_socket = _cylinder_y(knee, 45.2, 30, 220)
        thigh = _cut(thigh, knee_socket, _cylinder_y(hp, 29.0, 30, 104))
        # Only the redundant inboard skin inside the torso is removed. The
        # exact approved closed outer body is the trim datum; no load member
        # and no exterior chassis wall is cut to make this skin fit.
        body_envelope_path = ROOT/'robots/goose_v0_2/cad/source/enclosure_refinement_056/closed_belly_outer_input.brep'
        assert body_envelope_path.exists(), str(body_envelope_path)
        assert hashlib.sha256(body_envelope_path.read_bytes()).hexdigest() == '0b9b7266cd7b2633bdb777370b77ef7f871be0c88baac2358a7cbcab8fca76a1'
        envelope = b.import_brep(str(body_envelope_path))
        # A rigid small translation supplies clearance on the obscured
        # inboard side without claiming a constant-normal body offset.
        torso_clearance = _compound(envelope.fuse(envelope.translate((0, .7, 0))))
        thigh = _cut(thigh, torso_clearance)
        hip_skirt_outer = _hip_barrel(hp)
        hip_skirt_inner = _hip_barrel(hp,wall)
        hip_lead_in = _axis_y_volume(hp,[(91.8,49.25),(97.6,49.25),(100.2,47.2)])
        hip_skirt = _cut(hip_skirt_outer, hip_skirt_inner, thigh_cavity,hip_lead_in)
        thigh = _cut(_compound(thigh.fuse(hip_skirt)),hip_skirt_inner)
        thigh = _remove_isolated_socket_trim(thigh, hp, knee)
        add(side+'_thigh_continuous_protective_skin_056', thigh,
            'Full inboard/outboard/rear protective skin around unchanged thigh carrier; coaxial knee socket',
            side+'_hip_pitch',
            ['All original load-bearing primary and inner covers remain.',
             f'Cavity uses independent inner sections targeting {wall:g} mm skin; actual wall is variable and unqualified.',
             'Narrow carrier waist uses a local 1.2mm directional thickness target; minimum normal wall and manufacture remain unqualified.',
             'Inboard hip motor throat is a functional interface; final service attachment and travel sweep remain.'])

        shin_outer, shin, shin_cavity = _hollow_link(knee, ankle, shin_stations, wall)
        # A real round knee cheek encloses the retained incoming carrier at
        # both sides. The link waist follows the measured 21.55mm hardware
        # half-envelope; it no longer keeps an unnecessary 29mm bulge.
        shin = _cut(_compound(shin.fuse(_knee_barrel(knee))),
                    _knee_barrel(knee, wall),shin_cavity)
        ankle_socket = _ankle_barrel(ankle, -.7)
        shin = _cut(shin, ankle_socket)
        incoming = _incoming_link_clearance(hp, knee, 31.8, 72, 180)
        incoming = _cut(incoming, _cylinder_y(knee, 35.5, 30, 205))
        shin = _cut(shin, incoming)
        shin = _cut(shin, torso_clearance)
        shin = _cut(shin, _continuous_knee_mouth(knee))
        shin = _remove_isolated_socket_trim(shin, knee, ankle)
        add(side+'_shin_continuous_protective_skin_056', shin,
            'Fully wrapped rounded shin with covered inboard hardware and one ankle articulation socket',
            side+'_knee_pitch',
            ['Original steel/aluminium shin load structure and real fasteners remain inside.',
             'Knee and ankle openings are occupied by separately moving coaxial covers.',
             'One continuous analytic knee mouth covers the unchanged incoming-arm sweep outside the retained R44.5 round cap.',
             'Waist has local 1.2mm directional target; this is not a measured minimum wall qualification.',
             'Final assembly closure is to be placed on the inboard service side.'])

        if context.get('limbs_only'):
            continue

        ar = np.asarray(pivots[side+'_ankle_roll'], float)
        if context.get('ankle_construction', 'compliant_gaiter_candidate') == 'compliant_gaiter_candidate':
            knee_sleeve=_soft_knee_sleeve(hp,knee,ankle,thigh,shin,torso_clearance)
            add(side+'_continuous_flexible_knee_sleeve_056',knee_sleeve,
                'Thin continuous TPU knee interface sleeve; real covering behind the unchanged R44.5 PA12 cheek',
                side+'_knee_pitch',
                ['Real independent soft CAD part closing the prior knee motion mouth; the unchanged R44.5 PA12 cheek remains underneath the thin layer.',
                 'A 0.30mm hidden torso-trim edge relief is real source geometry, not a post-render repair.',
                 '1.0mm directional skin with 0.3mm standoff from the prior envelope; mounting and minimum normal wall are unqualified.',
                 'Spans hip-pitch to knee-pitch skins; assembled form only, no rigid sweep is claimed for TPU.',
                 'Hidden compression/retention, flexural fatigue and pinching require physical design validation.',
                 'Original metal knee limit interference is not resolved by this cover.'],
                material='TPU95A_design_budget',density=1200.,part_wall=1.0)
            shoe=_compliant_complete_shoe(ankle,ar,shin_outer,shin_cavity,shin)
            add(side+'_one_piece_shoe_upper_056',shoe,
                'One continuous TPU shoe, heel and ankle throat with no separate front toe crown or midfoot seam',
                side+'_ankle_roll',
                ['Original sole, load plate, saddles, clips and fasteners remain actual load-bearing hardware.',
                 'TPU95A 1200kg/m3 and 1.2mm main skin are design estimates; upper shin tongue locally follows 1.8mm source cavity.',
                 'Upper lip nests at the shin edge and spans AP/AR; flexible mounting, deformation, fatigue and pinching remain unqualified.',
                 'Outer volumes share one cavity; no hollow-volume internal membrane is retained.',
                 'Zero-pose native fit is not a flexible-life or full-motion qualification.'],
                [side+'_visible_AP_inboard_coaxial_service_shell_clearance_009_c09',
                 side+'_visible_AP_outboard_coaxial_service_shell_clearance_009_c09',
                 side+'_integrated_AR_shoe_crown_continuous_009_c03'],
                material='TPU95A_design_budget',density=1200.,part_wall=1.2)
            continue
        ankle_outer = _ankle_barrel(ankle)
        ankle_inner = _ankle_barrel(ankle, wall)
        # Stationary AP hood overlaps the moving shoe at the ACTUAL X-axis
        # of AR, not at the pitch Y-axis.  41.4 -> 42.1 is the working gap.
        skirt_outer = _cylinder_x(ar, 43.9, -12.5, 81.0, rear_fillet=2)
        skirt_outer = _cut(skirt_outer, _xz_box((-100, -300, -100), (200, 300, 36)))
        skirt_inner = _cylinder_x(ar, 43.9-wall, -20.0, 86.0)
        hood_outer = _compound(ankle_outer.fuse(skirt_outer))
        hood_inner = _compound(ankle_inner.fuse(skirt_inner))
        ankle_skin = _cut(hood_outer, hood_inner)
        # The incoming shin passes through the central rim; both outer
        # coaxial end faces stay closed, avoiding the rejected crescent and
        # unused inboard centre hole.
        incoming_ap = _incoming_link_clearance(knee, ankle, 28, 73, 177)
        incoming_ap = _cut(incoming_ap, _cylinder_y(ankle, 31.5, 30, 205))
        ankle_skin = _cut(ankle_skin, incoming_ap)
        ankle_skin = _remove_isolated_socket_trim(ankle_skin, ankle)
        add(side+'_ankle_coaxial_rounded_guard_056', ankle_skin,
            'Closed AP cheek and continuous heel hood with hidden X-coaxial AR overlap',
            side+'_ankle_pitch',
            ['AP metal load body and steel collector remain; X-coaxial skirt covers the AR shoe roof window.',
             'AR shoe radius41.4 and AP hood inner radius42.1 give0.7mm nominal working clearance.',
             'Outer cheek faces closed; central incoming-arm rim is an actual movement interface.',
             'Full AP/AR assembly sweep remains to verify against actual retained hardware.'],
            [side+'_visible_AP_inboard_coaxial_service_shell_clearance_009_c09',
             side+'_visible_AP_outboard_coaxial_service_shell_clearance_009_c09'])

        y = float(hp[1])
        shoe_outer = _coaxial_ar_shoe_volume(ar)
        shoe_inner = _coaxial_ar_shoe_volume(ar, wall)
        bottom_opening = b.Solid.make_box(220, 140, 17.81,
                              b.Plane(origin=(-50, y-70, -10)))
        shoe = _cut(shoe_outer, shoe_inner, bottom_opening, _ar_bridge_window(ar))
        add(side+'_one_piece_shoe_upper_056', shoe,
            'One-piece AR shoe with rounded toe and sole skirt, concealed coaxial rear roof interface',
            side+'_ankle_roll',
            ['Original sole and bottom contact geometry are not modified.',
             'Crown starts at Z7.80 mm above the original Z7.075 mm sole seat.',
             'One-piece toe and basal skirt; rear roof window is fully covered by AP X-coaxial hood.',
             'No decorative toe overlay or separate heel trim; real AR overlap at output X81.0/81.7mm.',
             'Clip reuse, sole engagement and AR movement clearance require final fit work.'],
            [side+'_integrated_AR_shoe_crown_continuous_009_c03'])
    # The input contract is exactly bilateral. Mirror the completed native
    # assembly rather than independently refitting the same loft backwards.
    # OCCT's backwards loft approximation otherwise introduces needless small
    # left/right volume differences.
    for joint in ['hip_pitch', 'knee_pitch', 'ankle_pitch', 'ankle_roll']:
        assert np.allclose(np.asarray(pivots['right_'+joint]),
                           np.asarray(pivots['left_'+joint])*[1, -1, 1], atol=1e-8)
    for part in list(result):
        mirrored = dict(part)
        mirrored['name'] = part['name'].replace('left_', 'right_', 1)
        mirrored['shape'] = part['shape'].mirror(b.Plane.XZ)
        mirrored['shape'].label = mirrored['name']
        mirrored['mount_body'] = part['mount_body'].replace('left_', 'right_', 1)
        if 'attachment_bodies' in part:
            mirrored['attachment_bodies']=[x.replace('left_','right_',1) for x in part['attachment_bodies']]
        mirrored['retire_previous_cosmetic'] = [x.replace('left_', 'right_', 1)
                                                for x in part['retire_previous_cosmetic']]
        result.append(mirrored)
    return result


def build(context):
    """Reproducible native skins with non-periodic round-surface parameters.

    SkipClean preserves the four analytic parameter domains instead of
    recombining their trimmed wires into the original ambiguous periodic face.
    It changes representation only; all dimensions and retained hardware stay.
    """
    with b.SkipClean():
        parts=_build_native_skins(context)
    for part in parts:
        shape=part['shape']
        assert BRepCheck_Analyzer(shape.wrapped,True,False,True).IsValid(), part['name']+' exact BRep'
        assert BRepAlgoAPI_Check(shape.wrapped,True,True).IsValid(),part['name']+' BOP'
    return parts


def main():
    started = time.monotonic()
    out = ROOT/'artifacts/goose_v0_2/enclosure_refinement_056/limbs'
    out.mkdir(parents=True, exist_ok=True)
    contract = json.loads((ROOT/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json').read_text())
    geometry = json.loads((ROOT/'robots/goose_v0_2/cad/source/enclosure_refinement_056/retained_display_identity.json').read_text())['parts']
    context = dict(root=ROOT, pivots={j['name']:np.array(j['pivot_world_at_zero_m'])*1000 for j in contract['joints']},
                   artifacts=out, native_index={}, native_geometry=geometry)
    parts = build(context)
    sys.path.insert(0, str(ROOT/'scripts/cad'))
    from remesh_goose_design_covers_052 import triangulate
    report = []
    cached_meshes = {}
    for part in parts:
        native_file = out/(part['name']+'.brep')
        before = hashlib.sha256(native_file.read_bytes()).hexdigest() if native_file.exists() else None
        b.export_brep(part['shape'], str(native_file))
        after = hashlib.sha256(native_file.read_bytes()).hexdigest()
        if before == after and (out/(part['name']+'.npz')).exists():
            cached_meshes[part['name']] = True
    for part in parts:
        shape = part['shape']
        mesh_file = out/(part['name']+'.npz')
        mirrored_left = out/(part['name'].replace('right_', 'left_', 1)+'.npz')
        if part['name'] in cached_meshes:
            with np.load(mesh_file) as data:
                v, n, f = data['vertices']*1000, data['normals'], data['faces']
            nf = len(shape.faces())
        elif part['name'].startswith('right_') and mirrored_left.exists():
            with np.load(mirrored_left) as data:
                v, n, f = data['vertices'].copy(), data['normals'].copy(), data['faces'][:, [0, 2, 1]].copy()
            v[:, 1] *= -1
            n[:, 1] *= -1
            np.savez(mesh_file, vertices=v, normals=n, faces=f)
            v *= 1000
            nf = len(shape.faces())
        else:
            v, n, f, nf = triangulate(shape)
            np.savez(mesh_file, vertices=(v/1000).astype(np.float32), normals=n.astype(np.float32), faces=f)
        entry = {k:val for k,val in part.items() if k != 'shape'}
        entry.update(native_volume_mm3=float(shape.volume),
                     estimated_design_mass_kg=float(shape.volume)*part['density_kg_m3']*1e-9,
                     native_valid=shape.is_valid, solid_count=len(shape.solids()), native_faces=nf,
                     bounds_mm=[list(shape.bounding_box().min), list(shape.bounding_box().max)],
                     path=str(out/(part['name']+'.npz')), native=str(out/(part['name']+'.brep')),
                     original_material='uncoloured_protective_skin', triangles=len(f), vertices=len(v))
        report.append(entry)
        print(json.dumps({'part':part['name'], 'volume_mm3':shape.volume, 'triangles':len(f)}), flush=True)
        (out/'limb_parts.json').write_text(json.dumps(report, indent=2)+'\n')
    b.export_step(b.Compound(children=[r['shape'] for r in parts]), str(out/'limb_enclosures_056.step'))
    (out/'build_receipt.json').write_text(json.dumps(dict(status='NATIVE_PROTECTIVE_SKIN_CANDIDATE_NOT_PHYSICS_RELEASE',
                   elapsed_s=time.monotonic()-started, count=len(parts), source=str(Path(__file__)),
                   original_load_path_preserved=True, original_sole_preserved=True,
                   full_motion_qualified=False, hardware_mass_released=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
