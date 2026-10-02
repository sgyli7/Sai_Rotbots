"""Editable segmented feet; unloaded fold geometry is not a new SI contract.

The original toe skins and independent high heel silhouette surround local
members. No sole skin or box beam bridges both rotating foot segments.
"""
from __future__ import annotations

import copy
import math
import numpy as np

from gorilla_primary_structure import hollow_member

AXIS = [0.0, 1.0, 0.0]


def _tag(part, side, group, pivot, *, parent=None, unlock=None, interface=None):
    part.update({
        "composite_foot_side": side,
        "composite_foot_group": group,
        "composite_foot_pivot_world_m": np.asarray(pivot, float).tolist(),
        "composite_foot_axis_world": AXIS.copy(),
        "physical_parent_body": parent or side+"_foot",
        "display_only_body": group in ("forefoot", "heel"),
        "composite_foot_candidate_status": "Geometry only; no SI joint, material, drive, lock or load capacity approval",
        "composite_foot_fold_scope": "Unloaded / raised foot only; forefoot -15deg and heel +10deg bounded probes",
        "composite_foot_interface_candidate": interface or "Unassigned; geometry is not proof of a weld, fitted bearing or fastener",
    })
    if unlock is not None:
        part["composite_foot_unlock_translation_world_m"] = list(unlock)
    return part


def _clip(poly, x, greater):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ai=a[0]>=x if greater else a[0]<=x
        bi=b[0]>=x if greater else b[0]<=x
        if ai: out.append(a)
        if ai != bi:
            t=(x-a[0])/(b[0]-a[0])
            out.append((np.asarray(a)+t*(np.asarray(b)-a)).tolist())
    return out


def _loft(g, name, body, rings, color):
    n=len(rings[0]); v=np.concatenate(rings); faces=[list(reversed(range(n)))]
    for k in range(len(rings)-1):
        for i in range(n):
            j=(i+1)%n
            faces.append([k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i])
    faces.append(list(range((len(rings)-1)*n,len(rings)*n)))
    g.part(name,body,v,faces,color,True,"Independent segment skin/pad candidate; contact material and fixing not specified")
    g.parts[-1].update({"edge_bevel_m":0,"role":"contact_surface_candidate"})
    return g.parts[-1]


def _box(g,name,body,center,size,color):
    g.box(name,body,center,size,color,True)
    g.parts[-1]["edge_bevel_m"]=0
    return g.parts[-1]


def _annulus(g,name,body,center,outer,inner,length,color,flat_z=None):
    """Finite material ring, optionally with an integral lower stop flat."""
    center=np.asarray(center,float); n=64; v=[]
    for rad in (outer,inner):
        for yy in (-length/2,length/2):
            for i in range(n):
                angle=2*math.pi*i/n; r=rad
                if rad==outer and flat_z is not None and not name.endswith('heel_rotor') and 280<=math.degrees(angle)<=310:
                    r=(flat_z-center[2])/math.sin(angle)
                if rad==outer and flat_z is not None and name.endswith("heel_rotor") and 230<=math.degrees(angle)<=260:
                    r=(flat_z-center[2])/math.sin(angle)
                v.append(center+[r*math.cos(angle),yy,r*math.sin(angle)])
    faces=[]; off=2*n
    for i in range(n):
        j=(i+1)%n
        faces.extend([[i,j,n+j,n+i],[off+n+i,off+n+j,off+j,off+i],
                      [j,i,off+i,off+j],[n+i,n+j,off+n+j,off+n+i]])
    g.part(name,body,v,faces,color,True,"Finite shaft/bushing/rotor envelope; fits, pin loading and retention are unverified")
    g.parts[-1]["edge_bevel_m"]=0
    return g.parts[-1]


def _slot_lug(g,name,body,center,color):
    """A real through-slot in a separate small candidate locking ear."""
    c=np.asarray(center,float);outer=[[-.018,-.014],[.018,-.014],[.018,.014],[-.018,.014]]
    inner=[[-.012,-.008],[.012,-.008],[.012,.008],[-.012,.008]]; v=[]
    for poly in (outer,inner):
        for yy in (-.007,.007):
            v.extend(c+[x,yy,z] for x,z in poly)
    faces=[]
    for i in range(4):
        j=(i+1)%4
        faces.extend([[i,j,4+j,4+i],[12+i,12+j,8+j,8+i],
                      [j,i,8+i,8+j],[4+i,4+j,12+j,12+i]])
    g.part(name,body,v,faces,color,True,"Separate integral/fixed ear candidate with an actual rectangular locking slot; attachment unverified")
    g.parts[-1].update({"edge_bevel_m":0,"slot_clearance_xyz_m":[.002,None,.002]})
    return g.parts[-1]


def _member(g,name,body,path,width,depth,wall,palette,side,group,pivot, width_hint=(0,1,0)):
    hollow_member(g,name,body,path,width,depth,wall,palette,width_hint=width_hint)
    p=_tag(g.parts[-1],side,group,pivot)
    p["structure_view_visible"]=True
    p["structural_member"].update({"physical_parent_body":side+"_foot",
        "composite_segment":group,"body_load_path_world_m":[list(map(float,q)) for q in path],
        "connection_boundary":"Terminates at segment fork/stop candidate. Never propagate a rigid-beam load path across the articulating axle.",
        "load_role":"articulated_segment_candidate_load_split_unverified"})
    return p


def _front_ankle_cover(g,side,ankle,palette,pivot):
    """Short front guard outside the unchanged upper socket and toe sweep."""
    body=side+"_foot";v=[]
    for x,z,w in ((.034,.252,.092),(.045,.274,.105),(.052,.299,.105),(.047,.311,.096)):
        for t in (-1,-.72,0,.72,1):
            v.append([x,ankle[1]+(1 if side=='left' else -1)*.041+t*w,z+.010*(1-t*t)])
    f=[[k*5+j,k*5+j+1,(k+1)*5+j+1,(k+1)*5+j] for k in range(3) for j in range(4)]
    normal=np.cross(np.array(v[1])-v[0],np.array(v[6])-v[0])
    if normal[0]<0:f=[q[::-1] for q in f]
    g.cover(side+"_composite_ankle_front_guard",body,v,f,palette['ivory'],.006,
        note="Short returned white ankle guard outside the original main socket; open mounting back and toe-motion clearance. Candidate shape/gauge.")
    _tag(g.parts[-1],side,'arch',pivot)


def _build_side(g,side,s,points,palette):
    ankle=np.asarray(points[side+"_ankle"],float);foot=np.asarray(points[side+"_foot"],float)
    pivot=np.array([ankle[0]-.031,ankle[1],.124])
    arch=side+"_foot"; fore=side+"_forefoot_display"; heel=side+"_heel_display"
    g.bodies.update((fore,heel))
    old={p['name']:p for p in g.parts if p['body']==arch}
    retain=[n for n in old if (n.startswith(side+'_ankle_') and any(k in n for k in
        ('wide_inner_bridge','bridge_shoulder','support_cheek','recessed_face','thin_rim'))) or n==side+'_z_ankle_primary_socket']
    g.parts=[p for p in g.parts if p['body']!=arch or p['name'] in retain]
    for p in g.parts:
        if p['name'] in retain:_tag(p,side,'arch',pivot,interface='Unchanged original upper-ankle visible group/socket. Original mechanical verification status retained.')
    for name in ('ivory_artwork_sloping_toe','ivory_lower_toe_front_rim','ivory_inner_low_rail','ivory_outer_low_rail','graphite_clipped_front_bumper'):
        p=copy.deepcopy(old[side+'_'+name]);p['body']=fore
        _tag(p,side,'forefoot',pivot,interface='Separate thin armor/protective rim mounted to forefoot local ribs; mounts remain candidates')
        p['composite_native_shell_preserved']=True;g.parts.append(p)
    # Segment-owned front pads, cut at the observed rear toe edge; no arch skin.
    oldpad=old[side+'_black_ground_sole']; vv=np.asarray(oldpad['vertices_world_m']);base=vv[np.isclose(vv[:,2],0)].tolist()
    clipped=_clip(base,.025,True)
    for label,zs,col in (('forepad',[0,.009,.027,.033],palette['black']),('forepad_upper_edge',[.034,.042],palette['dark'])):
        rings=[np.array([[q[0],q[1],z] for q in clipped]) for z in zs]
        _tag(_loft(g,side+'_composite_'+label,fore,rings,col),side,'forefoot',pivot,
             interface='Independent fore contact patch; sole material/fastening and collision definition unverified')
    # Original independent high heel: top slopes backwards, hollow under/front.
    y=ankle[1]
    bottom=np.array([[-.421,-.153],[-.380,-.213],[-.146,-.211],[-.105,-.178],
                     [-.104,.176],[-.147,.211],[-.380,.212],[-.421,.151]])
    bottom[:,1]*=s
    padpoly=bottom.copy();padpoly[:,1]+=y;padpoly[:,0]=np.minimum(padpoly[:,0],-.100)
    _tag(_loft(g,side+'_composite_heel_pad',heel,[np.c_[padpoly,np.full(8,z)] for z in (0,.010,.028,.033)],palette['black']),side,'heel',pivot)
    shellbottom=bottom.copy();shellbottom[:,0]+= .005
    middle=shellbottom.copy();middle[:,0]+= .008
    top=shellbottom.copy();top[:,0]=np.where(top[:,0]>-.20,top[:,0]-.048,top[:,0]+.023);top[:,1]*=.78
    # These X values are world values; only lateral origin is added.
    heel_rings=[np.c_[q[:,0],q[:,1]+y,np.full(8,z)]
        for z,q in ((.034,shellbottom),(.070,middle),(.1695,top))]
    heel_vertices=np.concatenate(heel_rings)
    # The front and its two corner skins are an actual assembly mouth around
    # the fixed small arch shaft/seats. Main side skins/rear/top remain.
    sheet=[]
    for k in range(2):
        for i in (0,1,5,6,7):
            j=(i+1)%8; sheet.append([k*8+i,k*8+j,(k+1)*8+j,(k+1)*8+i])
    sheet.append(list(range(16,24)))
    if s<0:sheet=[f[::-1] for f in sheet]
    g.cover(side+'_composite_high_heel_shell',heel,heel_vertices,sheet,palette['dark'],.006,
        note='Actual returned 6mm heel skin with open underside/front corners around the fixed arch axis. Side/rear/top outer profiles retained; candidate gauge only.')
    _tag(g.parts[-1],side,'heel',pivot,interface='Open-front/under heel cover around independent local frame; finite 6mm candidate skin, not a structural block')
    # A separate thin removable rear inset, belonging entirely to the heel.
    p=copy.deepcopy(old[side+'_heel_recessed_rear_face']);p['body']=heel
    _tag(p,side,'heel',pivot);g.parts.append(p)
    _front_ankle_cover(g,side,ankle,palette,pivot)
    # Fixed raised arch. It ends above the ground gap and is not a full sole.
    _member(g,side+'_composite_arch_stem',arch,[ankle,[ankle[0],ankle[1],.181]],.115,.088,.006,palette,side,'arch',pivot)
    _member(g,side+'_composite_arch_crossbeam',arch,[[ankle[0]+.004,y-.184,.190],[ankle[0]+.004,y+.184,.190]],.070,.040,.005,palette,side,'arch',pivot,width_hint=(1,0,0))
    # Independent short local boxes wholly on their own side of the gap.
    _member(g,side+'_composite_fore_local_box',fore,[[.065,foot[1]+s*.020,.064],[.345,foot[1]+s*.020,.064]],.245,.048,.006,palette,side,'forefoot',pivot)
    _member(g,side+'_composite_heel_local_box',heel,[[-.335,y,.066],[-.194,y,.066]],.245,.044,.005,palette,side,'heel',pivot)
    # The pin remains fixed; separated concentric bearing/rotor layers have real
    # bores and axial margins. These are editable spaces, not selected bearings.
    pin=_annulus(g,side+'_composite_arch_pin',arch,pivot,.0215,.008,.390,palette['metal'])
    _tag(pin,side,'arch',pivot,interface='Hollow candidate pin; actual pin retention, fits and fatigue unverified')
    for direction,label in ((-1,'negative_y'),(1,'positive_y')):
        ys=y+direction*.180
        boss=pivot+[0,direction*.180,0]
        _tag(_annulus(g,side+'_composite_'+label+'_arch_boss',arch,boss,.037,.023,.014,palette['dark']),side,'arch',pivot)
        _member(g,side+'_composite_'+label+'_arch_support',arch,
            [[ankle[0]+.004,ys,.190],[pivot[0],ys,.166]],.024,.026,.004,palette,side,'arch',pivot)
        # Lower stops sit above the visible ground gap. Their short brackets
        # connect to stationary side seats, never to both moving local boxes.
        for group,offset,zflat,outer in (('forefoot',.110,.071,.043),('heel',.148,.073,.039)):
            b=fore if group=='forefoot' else heel
            cy=y+direction*offset; center=pivot+[0,direction*offset,0]
            rotor=_annulus(g,side+'_composite_'+label+'_'+('fore_rotor' if group=='forefoot' else 'heel_rotor'),b,center,outer,.0315,.026,palette['dark'],flat_z=zflat)
            _tag(rotor,side,group,pivot,interface='Separate rotor/fork layer; lower flat mates only the corresponding stationary stop')
            _tag(_annulus(g,side+'_composite_'+label+'_'+group+'_bushing',b,center,.030,.0225,.026,palette['metal']),side,group,pivot,
                 interface='Nominal pin journal radial margin 1mm; rotor margin 1.5mm; these are layout gaps, not manufacturing fits')
            if group=='forefoot':
                targety=foot[1]+direction*.112
                path=[pivot+[.044,direction*offset,0],[.043,targety,.078],[.105,targety,.064]]
                lugcenter=np.array([pivot[0]+.049,cy,.088]); stopx=pivot[0]+.030
            else:
                targety=y+direction*.105
                path=[pivot+[-.040,direction*offset,0],[-.222,targety,.090],[-.257,targety,.066]]
                lugcenter=np.array([pivot[0]+.033,cy,.080]); stopx=pivot[0]-.025
            for k,(a,bb) in enumerate(zip(path,path[1:])):
                _member(g,side+'_composite_'+label+'_'+group+'_fork_'+str(k),b,[a,bb],.034,.032,.004,palette,side,group,pivot)
            _tag(_slot_lug(g,side+'_composite_'+label+'_'+group+'_lock_ear',b,lugcenter,palette['dark']),side,group,pivot,
                 interface='Candidate slotted ear attachment to local rotor/fork; integral casting or join remains unverified')
            stop=_box(g,side+'_composite_'+label+'_'+group+'_neutral_stop',arch,[stopx,cy,zflat-.010],[.044,.026,.020],palette['dark'])
            _tag(stop,side,'arch',pivot,interface=group+' lower stop flat: neutral face contact only; use locked state for body-load analysis')
            stop['composite_stop_target_group']=group;stop['composite_stop_top_z_m']=zflat
            _member(g,side+'_composite_'+label+'_'+group+'_stop_bracket',arch,
                [[stopx,ys,zflat-(.029 if group=='forefoot' else .019)],[stopx,cy,zflat-(.029 if group=='forefoot' else .019)]],.028,.020 if group=='forefoot' else .016,.003,palette,side,'arch',pivot,width_hint=(1,0,0))
            # Fore locks withdraw towards arch center; heel locks withdraw out.
            extract=(-direction if group=='forefoot' else direction)*.032
            tonguecenter=lugcenter+[0,math.copysign(.0315 if group=='forefoot' else .0235,extract),0]
            tongue=_box(g,side+'_composite_'+label+'_'+group+'_lock_tongue',arch,tonguecenter,[.020,.079 if group=='forefoot' else .063,.012],palette['metal'])
            _tag(tongue,side,'lock',pivot,unlock=[0,extract,0],interface='Independent retractable tongue inside real 24x16mm slot; neutral 2mm edge clearance, actuation/holding unverified')
            tongue['composite_lock_target_group']=group
            guidecenter=lugcenter+[0,math.copysign(.062 if group=='forefoot' else .027,extract),0]
            guide=_slot_lug(g,side+'_composite_'+label+'_'+group+'_lock_guide',arch,guidecenter,palette['dark'])
            _tag(guide,side,'arch',pivot,interface='Stationary slotted tongue guide; mount to arch side support remains unverified')
    for p in g.parts:
        if p.get('composite_foot_side')==side:
            p['composite_foot_assembly_reference']='AA3 separated toe / raised small dark arch seat / independent high dark heel'
            p['composite_foot_original_axis_status']='Preferred visible lower seat region, not an axis proven by the illustration'


def replace_composite_feet(g, points, palette):
    """Replace old rigid-foot display assembly after add_primary_structure.

    Register display groups without changing the physical spec. The parent
    builder decides export/diagnostic grouping and a future SI contract.
    """
    for side,s in (('left',1),('right',-1)):
        _build_side(g,side,s,points,palette)
    return g
