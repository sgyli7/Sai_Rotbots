"""Real native thin-wall Goose neck enclosures following reviewed concept 054.

These covers preserve the hardware/axis baseline. They are CAD candidates, never
an implicit modification of the immutable physics15 runtime. Units are mm.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
import sys
import time
from typing import Any
import numpy as np
from cadgen import build123d as b
from functools import lru_cache
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepAlgoAPI import BRepAlgoAPI_Check
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCP.BRep import BRep_Tool
from OCP.GeomAPI import GeomAPI_ProjectPointOnCurve
from OCP.gp import gp_Pnt
import math

ROOT = Path(__file__).resolve().parents[2]
VALIDATED_CHECKPOINT_ID = "neck_056_c07_continuous_head_skin"
WALL = 2.2
GAP = .8
# Each tuple is (world Z, X centre, X semiaxis, Y semiaxis). The stations are
# dimensioned against the actual installed frames and SKU cases, not the bitmap.
STATIONS = [
    (432.0, 29.45, 41.5, 54.5), (447.0, 28.0, 41.0, 55.5),
    (466.0, 18.5, 39.0, 56.0), (487.0, -6.0, 34.0, 59.0),
    (505.0, -22.0, 34.0, 58.5), (525.0, -39.5, 41.0, 59.0),
    (544.305, -43.55, 44.0, 63.0), (562.0, -38.0, 47.0, 63.0),
    (580.0, -17.0, 36.5, 60.0), (598.0, -3.0, 39.0, 60.5),
    (618.0, 16.0, 37.0, 51.0), (640.0, 28.45, 30.0, 42.0),
]
RETIRED_NAMES = [
    'lower_neck_front_integrated_clamshell', 'lower_neck_rear_integrated_clamshell',
    'upper_neck_front_integrated_clamshell', 'upper_neck_rear_integrated_clamshell',
    'neck_yaw_root_front_hood', 'neck_yaw_root_rear_hood',
    'head_pitch_joint_front_hood', 'head_pitch_joint_rear_hood',
]


def _one(shape: Any):
    if not hasattr(shape, 'wrapped'):
        shape = b.Compound(children=list(shape))
    solids = list(shape.solids())
    if len(solids) != 1 or not shape.is_valid or shape.volume <= 0:
        raise ValueError(f'Unsound cover: solids={len(solids)} volume={shape.volume}')
    return solids[0]


def _box(lo, hi):
    return b.Solid.make_box(*(np.asarray(hi) - np.asarray(lo)), b.Plane(origin=lo))


def _neck_loft(inset=0.0):
    wires=[]
    for z,x,rx,ry in STATIONS:
        p = b.Plane(origin=(x,-2.0,z))
        wires.append((p * b.Ellipse(rx-inset,ry-inset)).wires()[0])
    return b.Solid.make_loft(wires, ruled=False)


@lru_cache(maxsize=32)
def _native_input(root, name):
    base=Path(root)/'robots/goose_v0_2/cad/source/enclosure_refinement_056/neck_inputs'
    source=json.loads((base/'source_bound_inputs.json').read_text())
    records=list(source['parts'])
    additional=base/'additional_retained_interfaces.json'
    if additional.exists(): records+=json.loads(additional.read_text())
    bottom=base/'head_bottom_interface_inputs.json'
    if bottom.exists(): records+=json.loads(bottom.read_text())
    row=next(r for r in records if r['name']==name)
    path=base/(name+'.brep')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=row['native']['sha256']:
        raise ValueError(f'Changed retained hardware input: {name}')
    return b.import_brep(str(path))


@lru_cache(maxsize=1)
def _true_head_mouth(root):
    skull=_native_input(root,'head_integral_print_shell')
    face=next(f for f in skull.faces() if f.geom_type==b.GeomType.PLANE and abs(f.bounding_box().min.X-87.2)<1e-4 and f.bounding_box().size.X<1e-4)
    # Reassemble by geometric endpoints, independent of OCCT face-edge order.
    def chain(points):
        result=[]
        for start,end in zip(points,points[1:]):
            for edge in face.edges():
                a=np.array(list(edge.start_point()));c=np.array(list(edge.end_point()))
                if np.linalg.norm(a-start)<1e-3 and np.linalg.norm(c-end)<1e-3:
                    result.append(edge);break
                if np.linalg.norm(c-start)<1e-3 and np.linalg.norm(a-end)<1e-3:
                    result.append(edge.reversed());break
            else: raise ValueError('Retained native mouth topology changed')
        return result
    outer=chain(np.array([[87.2,-33.331844763,608.261466842],[87.2,-41.272072146,635.248794441],
                          [87.2,0,671.138584779],[87.2,41.272072146,635.248794441],[87.2,33.331844763,608.261466842]]))
    inner=chain(np.array([[87.2,-33.331844763,611.57933405],[87.2,-39.000612384,635.260743586],
                          [87.2,0,668.93374573],[87.2,39.000612384,635.260743586],[87.2,33.331844763,611.57933405]]))
    def close(edges,bottom):
        arc=b.Edge.make_three_point_arc(edges[-1].end_point(),(87.2,0,bottom),edges[0].start_point())
        return b.Wire(edges+[arc])
    return close(outer,592),close(inner,594.2),face


def _head_loft(inset=0.0,root=ROOT):
    outer,inner,_=_true_head_mouth(root)
    stations=[(-24,.08,.10,637),(-16,.65,.65,632),(0,1.1,1.05,631),
              (26,1.28,1.15,630.7),(57,1.2,1.12,630.8),(75.2,1.08,1.05,633.2)]
    if inset:
        stations=[(-21,.28,.30,635),*stations[1:]]
    wire=inner if inset else outer
    wires=[]
    for x,sy,sz,zc in stations:
        M=b.Matrix([[1,0,0,x-87.2],[0,sy,0,0],[0,0,sz,zc-sz*635],[0,0,0,1]])
        wires.append(wire.transform_geometry(M))
    return b.Solid.make_loft(wires,ruled=False)


def _cuff_profile(root, x, blend):
    outer,_,face=_true_head_mouth(root)
    # The protected lower rear jaw bay has no native U-edge. A 7mm deeper
    # smooth chin than the zero-position rigid prototype clears the real
    # stator corner during roll without increasing the top/sides of the head.
    edges=list(outer.edges())
    # Preserve the four actual source arch edges and only replace the closing chin.
    arch=[]
    for edge in edges:
        if edge.geom_type!=b.GeomType.CIRCLE: arch.append(edge)
    if len(arch)!=4: raise ValueError('Changed native cranial arch topology')
    chin=b.Edge.make_three_point_arc(arch[-1].end_point(),(87.2,0,592-7*blend),arch[0].start_point())
    profile=b.Wire(arch+[chin])
    sy=1.08-.08*blend;sz=1.05-.05*blend;zc=633.2+1.8*blend
    matrix=b.Matrix([[1,0,0,x-87.2],[0,sy,0,0],[0,0,sz,zc-sz*635],[0,0,0,1]])
    return profile.transform_geometry(matrix)


@lru_cache(maxsize=1)
def _lower_head_guard(root):
    # A real under-jaw dust guard closes the retained skull's rear-bottom U
    # access opening. It rotates with head_roll, outside the flexing12mm zone.
    # Nominal interference-free receiving contours are cut from actual retained
    # skull/motor/frame solids, not from a drawing or an invented filled mesh.
    outer=_cuff_profile(root,86.9,1)
    k=.971
    inner=outer.transform_geometry(b.Matrix([[1,0,0,0],[0,k,0,0],[0,0,k,(1-k)*635],[0,0,0,1]]))
    external=b.Solid.extrude(b.Face(outer),(16.1,0,0))
    internal=b.Solid.extrude(b.Face(inner),(16.1,0,0))
    tray=_one(external.cut(internal))
    tray=_one(tray.intersect(_box([86,-100,580],[104,100,611])))
    front=_one(external.intersect(_box([101.8,-100,580],[103.1,100,611])))
    shield=_one(tray.fuse(front))
    for name in ('head_integral_print_shell','beak_motor_catalog_case','thrust033_head_frame_needle_seats_7075'):
        shield=_one(shield.cut(_native_input(root,name)))
    return shield


def build_head_roll_cuff(context, q_rad=0.0):
    """Geometric prescribed torsion state, NOT an elastomer constitutive solve.

    Axial 12mm local cuff, rear bead fixed to head_pitch, front bead fixed to
    the unchanged native head_roll U-mouth. No rigid rotation claims strain.
    """
    root=Path(context['root']);axis=b.Axis((67.45,0,617.805),(1,0,0))
    outer_wires=[];inner_wires=[]
    # The final0.7mm bonding region is untwisted locally and follows the actual native mouth.
    for x,blend,twist in [(75.2,0,0),(80.85,.5,.5),(86.5,1,1),(87.2,1,1)]:
        profile=_cuff_profile(root,x,blend)
        # Uniform sectional shrink keeps the five native arch/chin edges in
        # correspondence. Direct planar offset creates28/29 tiny edges at
        # different sections and an ill-conditioned loft; it is not used.
        zc=633.2+1.8*blend;k=.971
        inner=profile.transform_geometry(b.Matrix([[1,0,0,0],[0,k,0,0],[0,0,k,(1-k)*zc],[0,0,0,1]]))
        outer=profile.rotate(axis,float(np.rad2deg(q_rad*twist)))
        inner=inner.rotate(axis,float(np.rad2deg(q_rad*twist)))
        outer_wires.append(outer);inner_wires.append(inner)
    shell=_one(b.Solid.make_loft(outer_wires).cut(b.Solid.make_loft(inner_wires)))
    return _one(shell.fuse(_lower_head_guard(root).rotate(axis,float(np.rad2deg(q_rad)))))


def _matched_loft(wires):
 assert all(len(w.edges())==5 for w in wires)
 op=BRepOffsetAPI_ThruSections(True,False,1e-6);op.CheckCompatibility(False);op.SetMaxDegree(3)
 for w in wires:op.AddWire(w.wrapped)
 op.Build();assert op.IsDone()
 return b.Solid(op.Shape())
def _ordered_wire(edges):
 op=BRepBuilderAPI_MakeWire()
 for e in edges:op.Add(e.wrapped)
 assert op.IsDone()
 return b.Wire(op.Wire())
def _phase_wire(w,start,next_point):
 edges=list(w.edges());result=[];cursor=np.asarray(start);next_point=np.asarray(next_point)
 # Fix the FIRST EDGE as well as the first vertex. A closed wire has two
 # legitimate walking directions at that vertex; choosing either flips phase.
 for i,e in enumerate(edges):
  a=np.asarray(list(e.start_point()));c=np.asarray(list(e.end_point()))
  if np.linalg.norm(a-cursor)<1e-3 and np.linalg.norm(c-next_point)<1e-3:
   result.append(e);cursor=c;edges.pop(i);break
  if np.linalg.norm(c-cursor)<1e-3 and np.linalg.norm(a-next_point)<1e-3:
   e=e.reversed();result.append(e);cursor=a;edges.pop(i);break
 else:raise ValueError('Native left-bottom to left-middle head edge not found')
 while edges:
  for i,e in enumerate(edges):
   if np.linalg.norm(np.asarray(list(e.start_point()))-cursor)<1e-3:
    result.append(e);cursor=np.asarray(list(e.end_point()));edges.pop(i);break
   if np.linalg.norm(np.asarray(list(e.end_point()))-cursor)<1e-3:
    e=e.reversed();result.append(e);cursor=np.asarray(list(e.end_point()));edges.pop(i);break
  else:raise ValueError('Native head profile cannot be phase locked')
 return _ordered_wire(result)
def _ellipse5(x,y,z,rx,ry,deg):
 a=math.radians(deg)
 plane=b.Plane(origin=(x,y,z),x_dir=(-math.cos(a),0,math.sin(a)),z_dir=(-math.sin(a),0,-math.cos(a)))
 angles=[-129.,-90.,0.,90.,129.,231.]
 return _ordered_wire([b.Edge.make_ellipse(rx,ry,plane,start_angle=p,end_angle=q) for p,q in zip(angles,angles[1:])])
def _native_section5(s,z):
 sec=b.section(s,section_by=b.Plane(origin=(0,0,z)));assert len(sec.edges())==1
 edge=sec.edges()[0]
 box=sec.bounding_box();cx=(box.min.X+box.max.X)/2;cy=(box.min.Y+box.max.Y)/2;rx=box.size.X/2;ry=box.size.Y/2
 curve=BRep_Tool.Curve_s(edge.wrapped,float(),float())
 def param(a):
  if abs(a-90)<1e-7:return None
  t=math.radians(a);p=gp_Pnt(cx-rx*math.cos(t),cy+ry*math.sin(t),z)
  project=GeomAPI_ProjectPointOnCurve(p,curve);p=project.NearestPoint();return float(edge.param_at_point((p.X(),p.Y(),p.Z())))
 angles=[-129.,-90.,0.,90.,129.,231.];us=[param(a) for a in angles];op=BRepBuilderAPI_MakeWire()
 for i in range(5):
  increasing=us[2]>us[1]
  a=us[i] if us[i] is not None else (0. if increasing else 1.);c=us[i+1] if us[i+1] is not None else (1. if increasing else 0.)
  piece=edge.trim(min(a,c),max(a,c))
  if (piece.start_point()-edge.position_at(a)).length>1e-5:piece=piece.reversed()
  assert (piece.start_point()-edge.position_at(a)).length<1e-5
  op.Add(piece.wrapped)
 assert op.IsDone();w=b.Wire(op.Wire())
 return w

def _head_wire(inset,x,sy,sz,zc,root=ROOT):
 outer,inner,_=_true_head_mouth(root)
 w=inner if inset else outer
 wire=w.transform_geometry(b.Matrix([[1,0,0,x-87.2],[0,sy,0,0],[0,0,sz,zc-sz*635],[0,0,0,1]]))
 start=[x,-33.331844763*sy,zc+sz*((611.57933405 if inset else 608.261466842)-635)]
 next_point=[x,(-39.000612384 if inset else -41.272072146)*sy,zc+sz*((635.260743586 if inset else 635.248794441)-635)]
 return _phase_wire(wire,start,next_point)

def _continuous_head_skin(root):
    """Native continuous turning skin, exact original N-section and head U-mouth.

    This is a neutral manufactured envelope, not a constitutive elastomer solve.
    The old head cup, head-entry boot and receiver lip are replaced by one skin;
    real forks, joint axes, hard guards and the original skull are unchanged.
    """
    outer_n=_neck_loft();inner_n=_neck_loft(1.2)
    def wires(inset):
        base=inner_n if inset else outer_n
        result=[_native_section5(base,z) for z in (590.,594.,598.)]
        for x,y,z,rx,ry,angle in [(6,-1.8,607,40,59,20),(20,-1,627.5,44,60,45),(43,-.3,635.0,42.5,56,75)]:
            result.append(_ellipse5(x,y,z,rx-inset,ry-inset,angle))
        result.extend([_head_wire(inset,57,1.2,1.12,630.8,root),_head_wire(inset,75.2,1.08,1.05,633.2,root)])
        return result
    def checked(shape):
        shape=_one(shape)
        if not BRepCheck_Analyzer(shape.wrapped,True,False,True).IsValid() or not BRepAlgoAPI_Check(shape.wrapped,True,True).IsValid():
            raise ValueError('Continuous turning skin native topology rejected')
        return shape
    external=checked(_matched_loft(wires(0.)))
    internal=checked(_matched_loft(wires(1.2)))
    turning=checked(external.cut(internal))
    clip=_box([-200,-100,430],[150,100,590])
    n_skin=checked(_one(outer_n.intersect(clip)).cut(_one(inner_n.intersect(clip))))
    joined=checked(turning.fuse(n_skin))
    mask=b.Solid.make_cylinder(82,180,b.Plane(origin=(28.45,-90,637.305),z_dir=(0,1,0)))
    return checked(joined.intersect(mask))

def build(context: dict) -> list[dict]:
    """Return native rigid guards, local flexible transitions and declarations."""
    root=Path(context['root']); out=Path(context['artifacts'])/'neck'
    out.mkdir(parents=True,exist_ok=True)
    pivots=context['pivots']
    for key,expected in [('neck_pitch',[29.45,0,440.305]),
                         ('neck_mid_pitch',[-43.55,0,544.305]),
                         ('head_pitch',[28.45,0,637.305])]:
        if not np.allclose(pivots[key],expected,atol=.01):
            raise ValueError(f'Unexpected actual joint datum for {key}: {pivots[key]}')
    for input_name in ('upper_neck_idler_fork_plate','upper_neck_output_fork_plate',
                       'head_pitch_to_roll_stator_bracket','head_integral_print_shell',
                       'lower_neck_idler_fork_plate','lower_neck_output_fork_plate',
                       'upper_neck_stationary_idler_spider','lower_neck_distal_rear_spacer_outer_1',
                       'lower_neck_distal_front_spacer_2','neck_mid_pitch_catalog_case',
                       'beak_motor_catalog_case','thrust033_head_frame_needle_seats_7075'):
        _native_input(root,input_name)
    neck_outer=_neck_loft(); neck_inner=_neck_loft(WALL)
    head_outer=_head_loft(root=root); head_inner=_head_loft(WALL,root=root)
    continuous=neck_outer.cut(neck_inner)
    split_z=550.0
    lower=_one(continuous.intersect(_box([-200,-100,430],[150,100,split_z-GAP/2])))
    upper=continuous.intersect(_box([-200,-100,split_z+GAP/2],[150,100,655]))
    if not hasattr(upper,'wrapped'): upper=b.Compound(children=list(upper))
    upper=_one(upper.cut(head_outer))
    head=_one(head_outer.cut(head_inner))
    continuous_head_skin=_continuous_head_skin(root)
    native_wiper=build_head_roll_cuff(context,0.0)
    # Minimum compliant regions follow clean analytic coaxial masks, rather
    # than sampled Boolean nicks. The rigid frame/actuator baseline is retained.
    mid=np.array(pivots['neck_mid_pitch'],float)
    h=np.array(pivots['head_pitch'],float)
    def cylinder(c,r,y0=-90,length=180):
        return b.Solid.make_cylinder(r,length,b.Plane(origin=(float(c[0]),y0,float(c[2])),z_dir=(0,1,0)))
    def sector(c,r,a0,a1):
        def point(deg):
            q=np.deg2rad(deg)
            return (float(c[0]+r*np.cos(q)),-90,float(c[2]+r*np.sin(q)))
        centre=(float(c[0]),-90,float(c[2]))
        arc=b.Edge.make_three_point_arc(point(a0),point((a0+a1)/2),point(a1))
        wire=b.Wire([b.Edge.make_line(centre,point(a0)),arc,b.Edge.make_line(point(a1),centre)])
        return b.Solid.extrude(b.Face(wire),(0,180,0))
    mid_mask=_one(cylinder(mid,46).fuse(sector(mid,88,-75,-15)))
    head_mask=cylinder(h,82)
    lower_cut=lower.cut(mid_mask)
    lower_solids=list(lower_cut.solids()) if hasattr(lower_cut,'wrapped') else [q for item in lower_cut for q in item.solids()]
    # Preserve the actual root-mounted rigid island. Any disconnected cosmetic
    # island is explicitly rematerialized in the continuous elastomer below,
    # never discarded or represented as a floating structural part.
    lower_rigid=_one(max((q for q in lower_solids if q.bounding_box().min.Z<435),key=lambda q:q.volume))
    upper_rigid=_one(upper.cut(head_mask))
    # 1.2-mm section-offset elastomer skins; not rigid bodies, and no claim
    # that a rigid rotation of their zero-pose meshes proves deformation.
    soft_wall=1.2
    thin=neck_outer.cut(_neck_loft(soft_wall))
    low_zone=thin.intersect(_box([-200,-100,430],[150,100,split_z+GAP/2]))
    if not hasattr(low_zone,'wrapped'): low_zone=b.Compound(children=list(low_zone))
    lower_boot=_one(low_zone.cut(lower_rigid))
    # Two shallow overlapping axis guards per side. All are rotationally
    # invariant about the real Y axes. Parent and child guards have 0.8mm gap.
    caps=[]
    for key,centre,parent_body,child_body,y_rows in [
        ('mid',mid,'neck_pitch','neck_mid_pitch',[(-55.8,'parent'),(-52.8,'child'),(46.6,'child'),(49.6,'parent')]),
        ('head',h,'neck_mid_pitch','head_pitch',[(-44.8,'parent'),(-41.8,'child'),(39.6,'child'),(42.6,'parent')])]:
        for i,(y,owner) in enumerate(y_rows):
            cap=b.Solid.make_cylinder(14.0,2.2,b.Plane(origin=(float(centre[0]),y,float(centre[2])),z_dir=(0,1,0)))
            cap_body=parent_body if owner=='parent' else child_body
            caps.append((f'{key}_internal_coaxial_guard_{i}_056',cap,cap_body))
            tool=b.Solid.make_cylinder(14.8,3.8,b.Plane(origin=(float(centre[0]),y-.8,float(centre[2])),z_dir=(0,1,0)))
            if key=='mid' and owner=='parent': upper_rigid=_one(upper_rigid.cut(tool))
            if key=='mid' and owner=='child': lower_rigid=_one(lower_rigid.cut(tool))
            if key=='head' and owner=='child': upper_rigid=_one(upper_rigid.cut(tool))
    lower,upper=lower_rigid,upper_rigid
    common=[
        'Original pitch/roll/yaw actuator locations and original integral skull/beak retained.',
        'Walls are section offsets: nominal PA12 2.2 mm and silicone 1.2 mm; local normal wall varies and is not a thickness qualification.',
        'No new decorative cuff. Neck hard/soft anchoring and internal assembly access require prototype detail qualification.',
        'C07 replaces the exposed PA12 head cup, entry boot and separate receiver lip with one continuous moulded silicone skin. The lower boundary uses the exact original N-section atZ590; the front uses the source-native U-profile atX75.2. Internal0.8mm coaxial guard gaps and all retained metal are unchanged. Flexible shape, attachment and material fatigue remain unqualified.',
        'Retained skull/forks/stator are hash-verified native source inputs; no frame, actuator or fastener geometry is modified.',
        'Cranial fixed rim ends X75.2; local12mm torsion cuff ends at actual retained native U-mouth X87.2. The underlying stator is unmodified.',
        'The head-roll cuff includes a1.2mm nominal lower U-tray X86.9..103 and1.2mm front baffle X101.8..103, receiving the actual original skull/motor/needle frame. No retained hardware is altered.',
        'Cuff body nominal1.2mm via0.971 sectional shrink (local normal thickness varies); its source-derived native U-shaped front edge bonds to a1.2mm land on the original2.2–3.3mm U-wall, with no added exterior split. Prescribed twist lofts are geometric states, not validated elastomer deformations.',
        'Rigid adjacent enclosures are sampled at original mid/head limits; whole-neck ROM, cable bending and flexible self-contact are NOT qualified.',
        'PA12 rigid guards/anchors and moulded silicone transition roles are separated. These non-load-bearing covers do not inherit structural/thermal qualification.',
        'Mass is geometry/density estimate only; immutable physics15 mass and inertia remain unchanged.',
    ]
    specs=[('lower_neck_rigid_anchor_056',lower,'PA12 root anchor; clean coaxial retreat instead of a flush collision rim','neck_pitch',2.2,1010,False),
           ('upper_neck_rigid_anchor_056',upper,'PA12 middle anchor; internal head articulation clearance','neck_mid_pitch',2.2,1010,False),
           ('mid_smooth_flexible_transition_056',lower_boot,'Moulded silicone elbow boot; two-shot or captive-bead connection, no cosmetic split','neck_pitch',soft_wall,1100,True),
           ('head_neck_continuous_flexible_skin_056',continuous_head_skin,'Continuous moulded silicone S-neck/cranial exterior; internal guards preserve real articulation','neck_mid_pitch',soft_wall,1100,True)]
    specs.append(('head_roll_flexible_mouth_cuff_056',native_wiper,'Local12mm silicone torsion cuff; fixed cranial bead and true native U-mouth rotating bead','head_pitch',1.2,1100,True))
    specs.extend((n,shape,'PA12 internal coaxial axis guard, paired parent/child lips',body,2.2,1010,False) for n,shape,body in caps)
    rows=[]
    for name,shape,role,body,wall,density,flex in specs:
        if not BRepCheck_Analyzer(shape.wrapped,True,False,True).IsValid():
            raise ValueError(f'Strict native geometry rejected: {name}')
        shape.label=name
        declarations=list(common)
        declarations.append('Flexible parts are neutral native solids only. No rigid-body rotation/disable-collision trick qualifies elastic deformation, wrinkling, pinch or fatigue.')
        rows.append({'name':name,'shape':shape,'role':role,'mount_body':body,
                     'nominal_wall_mm':wall,'assumptions':declarations,
                     'retire_display_names':RETIRED_NAMES,
                     'material_candidate':'moulded silicone nominal Shore A40, supplier selection NOT qualified' if flex else 'PA12, manufacturing/thermal unqualified',
                     'mass_density_assumption_kg_m3':density,
                     'estimated_mass_kg':float(shape.volume)*density*1e-9,
                     'deformable':flex,
                     'manufacturing_route_candidate':'two-piece matched mould casting; flexible boot installed before terminal guards' if flex else 'SLS PA12 prototype; moulded production part requires draft/detail review',
                     'attachment_status':'rear annular edge fixed at X75.2 to cranial cover; front1.2mm bonding land at X87.2 contacts the retained2.2–3.3mm native U-wall and follows head_roll; adhesive compression/wear/peel need prototype qualification' if name=='head_roll_flexible_mouth_cuff_056' else 'neutral matching boundaries defined; captive rim/snap details and primer/adhesion choice require prototype qualification',
                     'elastic_deformation_qualified':False if flex else None,
                     'flexible_anchors': ['neck_pitch','neck_mid_pitch'] if name=='mid_smooth_flexible_transition_056' else ['head_pitch','head_roll'] if name=='head_roll_flexible_mouth_cuff_056' else ['neck_mid_pitch','head_pitch'] if flex else None,
                     'engineering_qualified':False})
        if name=='head_neck_continuous_flexible_skin_056':
            rows[-1].update(
                replaces_candidate_parts=['head_rear_integrated_transition_056','head_smooth_flexible_transition_056','head_pitch_soft_receiver_lip_056'],
                attachment_status='continuous neutral skin with lower annular land matching the existing PA12 middle anchor and front land atX75.2 matching retained local torsion cuff; captive/adhesive detail and fatigue require prototype qualification',
                original_internal_coaxial_gap_mm=GAP,
                neutral_section_construction='exact source-N BSpline split into five phase-matched arcs, degree3 turning loft, exact native cranial U-profile; no rendered fill or hidden hardware')
    return rows


def check_mesh_clearance(context, rows, maximum_vertices_per_part=16):
    """Mesh-vertex broad-phase audit; misses crossing triangles, not exact Common."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    classifiers=[BRepClass3d_SolidClassifier(r['shape'].wrapped) for r in rows]
    boxes=[np.array([list(r['shape'].bounding_box().min),list(r['shape'].bounding_box().max)]) for r in rows]
    records=[]
    for src in context['native_geometry']:
        name=src['name']
        if name in RETIRED_NAMES or not any(w in name for w in ['neck','head_']): continue
        data=np.load(src['path']); v=np.unique(data['vertices']*1000,axis=0)
        if len(v)>maximum_vertices_per_part:
            v=v[np.linspace(0,len(v)-1,maximum_vertices_per_part,dtype=int)]
        results=[]
        for r,classifier,box in zip(rows,classifiers,boxes):
            mask=np.all((v>box[0]) & (v<box[1]),axis=1)
            points=v[mask]; inside=[]
            for p in points:
                classifier.Perform(gp_Pnt(*map(float,p)),1e-5)
                if classifier.State()==TopAbs_IN: inside.append(p.tolist())
            if len(points):
                results.append({'cover':r['name'],'tested_vertices':len(points),
                                'vertices_in_cover_material':len(inside),'witnesses_mm':inside[:5]})
        if results:
            records.append({'hardware':name,'vertex_subsample':len(v),'checks':results})
            print(json.dumps({'audit_part':name,'vertices':len(v),'in_material':sum(c['vertices_in_cover_material'] for c in results)}),flush=True)
            (Path(context['artifacts'])/'neck/mesh_vertex_clearance_partial_056.json').write_text(json.dumps({'completed_parts':records,'status':'INCOMPLETE_WHILE_RUNNING'},indent=2)+'\n')
    report={'method':'OCC solid classification of actual NPZ vertex subset; BROAD-PHASE, no triangle-intersection or motion qualification',
            'maximum_vertices_per_part':maximum_vertices_per_part,'parts':records,
            'intruding_part_count':sum(any(c['vertices_in_cover_material'] for c in r['checks']) for r in records)}
    (Path(context['artifacts'])/'neck/mesh_vertex_clearance_056.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def verify_rigid_interfaces(context, rows, native_records=None):
    """Reproduce adjacent rigid-cover sweeps; never qualify elastomer by omission."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    root=Path(context['root']); out=Path(context['artifacts'])/'neck'
    contract=json.loads((root/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json').read_text())
    limits={j['name']:j['range_rad'] for j in contract['joints']}
    by={r['name']:r for r in rows}; checks=[]; failures=[]
    for joint,parent,child,prefix,parent_anchor,child_anchor in [
        ('neck_mid_pitch','neck_pitch','neck_mid_pitch','mid_internal','lower_neck_rigid','upper_neck_rigid'),
        ('head_pitch','neck_mid_pitch','head_pitch','head_internal','upper_neck_rigid',None)]:
        lo,hi=limits[joint]
        angles=sorted(set([lo,.75*lo,.5*lo,.25*lo,-np.deg2rad(10),-np.deg2rad(5),0,np.deg2rad(5),np.deg2rad(10),.25*hi,.5*hi,.75*hi,hi]))
        fixed=[r for r in rows if not r['deformable'] and r['mount_body']==parent and (r['name'].startswith(prefix) or r['name'].startswith(parent_anchor))]
        moving=[r for r in rows if not r['deformable'] and r['mount_body']==child and (r['name'].startswith(prefix) or (child_anchor is not None and r['name'].startswith(child_anchor)))]
        axis=b.Axis(tuple(map(float,context['pivots'][joint])),(0,1,0))
        for angle in angles:
            for left in fixed:
                for right in moving:
                    a=left['shape']; c=right['shape'].rotate(axis,float(np.rad2deg(angle)))
                    ab=np.array([list(a.bounding_box().min),list(a.bounding_box().max)])
                    cb=np.array([list(c.bounding_box().min),list(c.bounding_box().max)])
                    separated=bool(np.any(ab[1]<cb[0]-1e-7) or np.any(cb[1]<ab[0]-1e-7))
                    volume=0.0; method='exact native AABB separated'
                    if not separated:
                        op=BRepAlgoAPI_Common(a.wrapped,c.wrapped);op.SetRunParallel(False);op.Build()
                        if not op.IsDone(): volume=None
                        else:
                            props=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),props);volume=float(props.Mass())
                        method='exact OCC Common'
                    check={'joint':joint,'q_rad':float(angle),'parts':[left['name'],right['name']],
                           'common_volume_mm3':volume,'method':method,'pass':volume is not None and abs(volume)<1e-3}
                    checks.append(check)
                    if not check['pass']: failures.append(check)
            print(json.dumps({'rigid_sweep_joint':joint,'q_rad':float(angle),'failures_so_far':len(failures)}),flush=True)
    result={'checkpoint':VALIDATED_CHECKPOINT_ID,
            'scope':'C07 adjacent PA12 anchors and8 internal rigid guards only, original joint limits. Former PA12 cranial cup is absent; continuous flexible skin is not qualified by this rigid sweep. No deformation/strain, cable, whole-robot or fatigue qualification.',
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'complete_angle_interval_continuous_proof':False,'q_limits_original_unchanged':True,
            'native_records':native_records,'checks':checks,'failures':failures,
            'all_sampled_rigid_pairs_clear':not failures}
    (out/'rigid_interface_motion_056.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def verify_head_roll_interface(context, rows):
    """Native rigid checks plus explicitly prescribed flexible roll states.

    This checks geometric enclosure and metal clearance. It does not claim
    that silicone will actually assume these shapes at an allowable stress.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    root=Path(context['root']);out=Path(context['artifacts'])/'neck'
    by={r['name']:r for r in rows};axis=b.Axis((67.45,0,617.805),(1,0,0))
    contract=json.loads((root/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json').read_text())
    limit=next(j['range_rad'] for j in contract['joints'] if j['name']=='head_roll')
    source_names=['head_integral_print_shell','head_pitch_to_roll_stator_bracket',
                  'upper_neck_idler_fork_plate','upper_neck_output_fork_plate',
                  'beak_motor_catalog_case','thrust033_head_frame_needle_seats_7075']
    sources={n:_native_input(root,n) for n in source_names};states=[]
    def common(left,right):
        a=np.array([list(left.bounding_box().min),list(left.bounding_box().max)])
        c=np.array([list(right.bounding_box().min),list(right.bounding_box().max)])
        if np.any(a[1]<c[0]-1e-7) or np.any(c[1]<a[0]-1e-7):
            return 0.0,'native AABB separation'
        op=BRepAlgoAPI_Common(left.wrapped,right.wrapped);op.SetRunParallel(False);op.Build()
        if not op.IsDone():return None,'OCC Common FAILED'
        props=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),props)
        return float(props.Mass()),'exact OCC Common'
    rigid=[r for r in rows if not r['deformable'] and r['mount_body']=='head_pitch']
    for q in [limit[0],0.0,limit[1]]:
        cuff=build_head_roll_cuff(context,float(q))
        skull=sources['head_integral_print_shell'].rotate(axis,float(np.rad2deg(q)))
        tag=f'{q:+.3f}'.replace('+','plus').replace('-','minus').replace('.','p')
        native=out/f'head_roll_cuff_prescribed_{tag}.brep';b.export_brep(cuff,str(native))
        record={'q_rad':float(q),'prescribed_geometry_only':True,
                'native':str(native),'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),
                'strict':bool(BRepCheck_Analyzer(cuff.wrapped,True,False,True).IsValid()),
                'BOP':bool(BRepAlgoAPI_Check(cuff.wrapped,True,True).IsValid()),
                'volume_mm3':float(cuff.volume),'single_solid':len(cuff.solids())==1,
                'rear_edge_fixed_plane_X_mm':75.2,'front_native_U_edge_plane_X_mm':87.2,
                'source_native_arch_edges_preserved':4,
                'prescribed_closed_circumference':'same four native arch curves and a continuous lower chin at every loft section; no omitted side sector',
                'pairs':[]}
        for name,hardware in sources.items():
            target=skull if name=='head_integral_print_shell' else hardware.rotate(axis,float(np.rad2deg(q))) if name in ('beak_motor_catalog_case','thrust033_head_frame_needle_seats_7075') else hardware
            volume,method=common(cuff,target)
            record['pairs'].append({'parts':['prescribed flexible cuff',name],
                'common_volume_mm3':volume,'method':method,'pass':volume is not None and abs(volume)<1e-3})
        for r in rigid:
            volume,method=common(r['shape'],skull)
            record['pairs'].append({'parts':[r['name'],'actual rotated native skull'],
                'common_volume_mm3':volume,'method':method,'pass':volume is not None and abs(volume)<1e-3})
        skin=by['head_neck_continuous_flexible_skin_056']['shape']
        for target_name,target in [('actual rotated native skull',skull),('prescribed local roll cuff',cuff)]:
            volume,method=common(skin,target)
            record['pairs'].append({'parts':['continuous neutral skin',target_name],
                'common_volume_mm3':volume,'method':method,'pass':volume is not None and abs(volume)<1e-3})
        record['continuous_skin_vs_roll_cuff_axial_partition']={
            'planes_X_mm':[75.2,75.2],
            'source_construction':'C07 continuous neutral flexible skin ends at75.2; prescribed roll cuff starts at75.2; material interiors lie on opposite sides. This is geometric partition, not elastomer motion validation.',
            'not_a_disabled_collision':True}
        b.export_step(b.Compound(children=[cuff,skull,*[r['shape'] for r in rigid]]),str(out/f'head_roll_interface_{tag}.step'))
        states.append(record)
        print(json.dumps({'head_roll_prescribed_state':q,'strict':record['strict'],
                          'nonzero_common_pairs':[p for p in record['pairs'] if not p['pass']]}),flush=True)
        (out/'head_roll_interface_partial.json').write_text(json.dumps(states,indent=2)+'\n')
    result={'checkpoint':VALIDATED_CHECKPOINT_ID,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'C07 native skull vs remaining rigid head guards and continuous neutral skin; prescribed local cuff vs actual skull/stator/forks and neutral skin, at original X-roll limits and zero. Fixed neutral skin is not a constitutive flexible simulation.',
            'not_qualified':['constitutive deformation','adhesive peel/retention','fatigue','pinch','thermal ageing','cable bending','whole-neck coupled motion'],
            'rigid_joint_limit_unchanged':True,'prescribed_geometry_not_elastic_simulation':True,
            'estimated_required_outer_chord_displacement_mm_at_R53p34':float(2*53.34*np.sin(max(abs(limit[0]),abs(limit[1]))/2)),
            'states':states,'all_prescribed_samples_clear':all(s['strict'] and s['BOP'] and s['single_solid'] and all(p['pass'] for p in s['pairs']) for s in states)}
    (out/'head_roll_interface_056.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def verify_affected_hardware(context, rows):
    """Recheck source-bound metal and C07 continuous skin/new-cover interfaces.

    Native minimum distance proves separation when positive. An exact native
    Common is required otherwise. This is not a whole-assembly motion check.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    root=Path(context['root']);out=Path(context['artifacts'])/'neck'
    cover=next(r['shape'] for r in rows if r['name']=='upper_neck_rigid_anchor_056')
    names=['upper_neck_idler_fork_plate','upper_neck_output_fork_plate',
           'lower_neck_idler_fork_plate','lower_neck_output_fork_plate',
           'upper_neck_stationary_idler_spider','lower_neck_distal_rear_spacer_outer_1',
           'lower_neck_distal_front_spacer_2','neck_mid_pitch_catalog_case']
    checks=[]
    for name in names:
        hardware=_native_input(root,name)
        distance=float(cover.distance_to(hardware));volume=0.0
        method='exact native positive minimum distance'
        if distance<1e-5:
            op=BRepAlgoAPI_Common(cover.wrapped,hardware.wrapped)
            op.SetRunParallel(False);op.Build()
            if not op.IsDone():volume=None
            else:
                props=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),props)
                volume=float(props.Mass())
            method='exact native Common'
        row={'cover':'upper_neck_rigid_anchor_056','hardware':name,
             'distance_mm':distance,'common_volume_mm3':volume,'method':method,
             'pass':volume is not None and abs(volume)<1e-3}
        checks.append(row);print(json.dumps(row),flush=True)
    skin=next(r['shape'] for r in rows if r['name']=='head_neck_continuous_flexible_skin_056')
    input_base=root/'robots/goose_v0_2/cad/source/enclosure_refinement_056/neck_inputs'
    native_names=[r['name'] for r in json.loads((input_base/'source_bound_inputs.json').read_text())['parts']]
    for manifest in ['additional_retained_interfaces.json','head_bottom_interface_inputs.json']:
        native_names.extend(r['name'] for r in json.loads((input_base/manifest).read_text()))
    targets=[(name,_native_input(root,name),'retained native input') for name in native_names]
    targets.extend((r['name'],r['shape'],'other C07 new cover') for r in rows if r['name']!='head_neck_continuous_flexible_skin_056')
    for name,target,kind in targets:
        distance=float(skin.distance_to(target));volume=0.0;method='exact native positive minimum distance'
        if distance<1e-5:
            op=BRepAlgoAPI_Common(skin.wrapped,target.wrapped);op.SetRunParallel(False);op.Build()
            if not op.IsDone():volume=None
            else:
                props=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),props);volume=float(props.Mass())
            method='exact native Common'
        row={'cover':'head_neck_continuous_flexible_skin_056','hardware':name,'target_kind':kind,
             'distance_mm':distance,'common_volume_mm3':volume,'method':method,
             'pass':volume is not None and abs(volume)<1e-3}
        checks.append(row);print(json.dumps(row),flush=True)
    result={'checkpoint':VALIDATED_CHECKPOINT_ID,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'8 legacy middle-anchor native interfaces plus C07 continuous skin vs12 source-bound native inputs and12 other new neck covers, zero pose. Whole retained-hardware batch is independently checked by integration; tiny positive clearance is not a manufacturing tolerance qualification.',
            'checks':checks,'pass':all(c['pass'] for c in checks)}
    (out/'real_hardware_fit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    t=time.monotonic()
    out=ROOT/'artifacts/goose_v0_2/enclosure_refinement_056'
    c=json.loads((ROOT/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json').read_text())
    context={'root':ROOT,'artifacts':out,
        'pivots':{j['name']:np.array(j['pivot_world_at_zero_m'])*1000 for j in c['joints']},
        'native_index':json.loads((ROOT/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json').read_text()),
        'native_geometry':json.loads((ROOT/'robots/goose_v0_2/cad/source/enclosure_refinement_056/retained_display_identity.json').read_text())['parts']}
    rows=build(context)
    if '--audit' in sys.argv:
        a=check_mesh_clearance(context,rows)
        print(json.dumps({'vertex_audit_intruding_part_count':a['intruding_part_count']}),flush=True)
    sys.path.insert(0,str(ROOT/'scripts/cad'))
    if '--native-only' not in sys.argv:
        from assemble_goose_enclosure_refinement_056 import mesh
    report={'checkpoint':VALIDATED_CHECKPOINT_ID,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'status':'NATIVE_SOURCE_CANDIDATE_FLEXIBLE_BEHAVIOR_UNQUALIFIED','physics15_unchanged':True,
            'parts':[],'retire_display_names':RETIRED_NAMES,
            'display_mesh_export_requested':'--native-only' not in sys.argv,
            'display_mesh_status':'shared056 tessellator preserves all native faces with witnessed local display tolerances/partitions; --native-only skips display export'}
    for r in rows:
        s=r['shape']; p=out/'neck'/(r['name']+'.brep'); b.export_brep(s,str(p))
        display=mesh(s,r['name'],out/'neck') if '--native-only' not in sys.argv else None
        d={k:v for k,v in r.items() if k!='shape'}
        d.update(native=str(p),path=display['path'] if display else None,volume_mm3=float(s.volume),native_valid=bool(s.is_valid),native_strict_valid=bool(BRepCheck_Analyzer(s.wrapped,True,False,True).IsValid()),native_BOP_valid=bool(BRepAlgoAPI_Check(s.wrapped,True,True).IsValid()),
                 solid_count=len(s.solids()),native_faces=display['native_faces'] if display else len(s.faces()),triangles=display['triangles'] if display else None,
                 tessellation_only_face_partitions=display['tessellation_only_face_partitions'] if display else None,
                 bounds_mm=[list(s.bounding_box().min),list(s.bounding_box().max)],native_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        report['parts'].append(d);print(json.dumps(d),flush=True)
    b.export_step(b.Compound(children=[r['shape'] for r in rows]),str(out/'neck/neck_candidate_056.step'))
    base=ROOT/'robots/goose_v0_2/cad/source/enclosure_refinement_056/neck_inputs'
    report['hardware_input_manifests']=[{'path':str((base/name).relative_to(ROOT)),
        'sha256':hashlib.sha256((base/name).read_bytes()).hexdigest()}
        for name in ('source_bound_inputs.json','additional_retained_interfaces.json','head_bottom_interface_inputs.json')]
    report['total_estimated_mass_kg']=sum(r['estimated_mass_kg'] for r in rows)
    report['elastomer_deformation_status']='NOT_EVALUATED: neutral BRep is not deformed-FEA or a physical fatigue/anti-pinch test'
    report['elapsed_s']=time.monotonic()-t
    (out/'neck/neck_candidate_056.json').write_text(json.dumps(report,indent=2)+'\n')
    if not all(p['native_strict_valid'] and p['native_BOP_valid'] and p['solid_count']==1 for p in report['parts']):
        raise ValueError('Native export quality rejected; see neck_candidate_056.json')
    if '--verify-affected-hardware' in sys.argv:
        if not verify_affected_hardware(context,rows)['pass']:
            raise ValueError('Actual retained hardware clearance rejected; see real_hardware_fit.json')
    if '--verify-rigid-interfaces' in sys.argv:
        if not verify_rigid_interfaces(context,rows,report['parts'])['all_sampled_rigid_pairs_clear']:
            raise ValueError('Adjacent rigid cover motion rejected; see rigid_interface_motion_056.json')
    if '--verify-head-roll' in sys.argv:
        if not verify_head_roll_interface(context,rows)['all_prescribed_samples_clear']:
            raise ValueError('Head-roll prescribed interface rejected; see head_roll_interface_056.json')

if __name__=='__main__': main()
