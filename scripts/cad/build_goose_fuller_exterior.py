"""Goose fuller body, expressive camera eye and swept web-foot candidate.

The quad shells and motor proxies are editable. Nominal motor case dimensions
are sourced; custom links, fastening and actuator selection are NOT released.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from scipy.spatial.transform import Rotation
from build_goose_r2_reference_rebuild import (build as previous_build, section_solid,
    cylinder, link, smooth_bill, rounded_box, QuadMesh)

BODY=np.array([[-170,312,4,5],[-162,306,32,24],[-142,297,65,49],
 [-106,286,98,76],[-49,286,115,94],[11,289,116,101],
 [59,295,103,97],[100,305,77,79],[131,312,41,50],[148,316,4,5]],float)
PROFILE=PchipInterpolator(BODY[:,0],BODY[:,1:],axis=0)


def closed_skin(outer,inner,faces):
    """Thicken an arbitrary quad surface, including its window boundaries."""
    used=sorted(set(np.asarray(faces).ravel())); remap={v:i for i,v in enumerate(used)}
    a=np.asarray(outer)[used]; b=np.asarray(inner)[used]; n=len(a)
    fs=[tuple(remap[k] for k in f) for f in faces]
    all_faces=fs+[tuple(v+n for v in reversed(f)) for f in fs]
    edges=Counter(tuple(sorted((f[i],f[(i+1)%4]))) for f in fs for i in range(4))
    for (u,v),count in edges.items():
        if count==1: all_faces.append((u,v,v+n,u+n))
    return QuadMesh(np.vstack((a,b)),np.asarray(all_faces)).orient_outward()


def body_halves(side):
    outer=[]; inner=[]; shell_faces=[]; aft_faces=[]; fore_faces=[]; door_faces=[]; nx=64; nv=48
    for i in range(nx+1):
        for j in range(nv+1):
            v=np.clip((j-25)/11,-1,1)
            rear=-142+22*abs(v)**3; front=83-24*abs(v)**3
            x=np.interp(i,[0,10,48,64],[-170,rear,front,148])
            t=np.clip((i-10)/38,0,1)
            half=.11+.45*np.sin(t*np.pi/2)**.7
            center=.14-.07*t
            angle=np.interp(j,[0,14,36,48],[-np.pi/2,center-half,center+half,np.pi/2])
            cz,ry,rz=PROFILE(x)
            outer.append((x,side*(ry*np.cos(angle)+.12),cz+rz*np.sin(angle)))
            czd,ryd,rzd=PROFILE.derivative()(x)
            co,si=np.cos(angle),np.sin(angle)
            normal=np.array([-co*co*ryd/ry-si*czd/rz-si*si*rzd/rz,side*co/ry,si/rz])
            normal/=np.linalg.norm(normal)
            inner.append(np.asarray(outer[-1])-2.4*normal)
    for i in range(nx):
        for j in range(nv):
            f=(i*(nv+1)+j,(i+1)*(nv+1)+j,(i+1)*(nv+1)+j+1,i*(nv+1)+j+1)
            if 39<=i<49 and j>=42: continue # true neck opening through both shell halves
            if 27<=i<45 and j<8: continue # paired lower hip service apertures
            if 10<=i<48 and 14<=j<36: door_faces.append(f)
            else: (aft_faces if i<30 else fore_faces).append(f)
    aft=closed_skin(outer,inner,aft_faces)
    fore=closed_skin(outer,inner,fore_faces)
    aft.vertices[:,0]-=.08; fore.vertices[:,0]+=.08
    # Separate conforming manual wing cover, slightly smaller than the aperture.
    oo=np.asarray(outer).copy(); ii=np.asarray(inner).copy()
    # Give the access cover a shallow sculpted shoulder, not a flat outlined lid.
    for arr in (oo,ii):
        for k in range(len(arr)):
            i,j=divmod(k,nv+1)
            u=np.clip((i-10)/38,0,1); v=np.clip((j-14)/22,0,1)
            arr[k,1]+=side*1.2*np.sin(np.pi*u)*np.sin(np.pi*v)
        arr[:,0]=-32+(arr[:,0]+32)*.988
        arr[:,2]=293+(arr[:,2]-293)*.974
        arr[:,1]+=side*.25
    door=closed_skin(oo,ii,door_faces)
    return aft,fore,door


def ring(center,outer,inner,depth,axis=1,n=48):
    c=np.asarray(center); other=[k for k in range(3) if k!=axis]; vertices=[]
    for axial,r in [(-depth/2,outer),(depth/2,outer),(depth/2,inner),(-depth/2,inner)]:
        for t in np.arange(n)*2*np.pi/n:
            p=c.copy().astype(float); p[axis]+=axial; p[other[0]]+=r*np.cos(t); p[other[1]]+=r*np.sin(t); vertices.append(p)
    faces=[(layer*n+j,layer*n+(j+1)%n,((layer+1)%4)*n+(j+1)%n,((layer+1)%4)*n+j) for layer in range(4) for j in range(n)]
    return QuadMesh(np.array(vertices),np.array(faces)).orient_outward()


def build(opening=0,doors_open=False):
    parts=[]; motors=[]
    def add(name,mat,mesh,group,role='custom_visual_candidate'):
        parts.append(dict(name=name,material=mat,mesh=mesh,group=group,role=role))
    for side,label in [(-1,'right'),(1,'left')]:
        aft,fore,door=body_halves(side)
        add('torso_shell_'+label+'_aft','ivory',aft,'shell','hollow_shell_candidate')
        add('torso_shell_'+label+'_fore','ivory',fore,'shell','hollow_shell_candidate')
        if doors_open:
            # Review exploded access view, not an assertion about hinge sweep.
            door.vertices[:,1]+=side*95
        add('wing_access_cover_'+label,'ivory',door,'wing_'+label,'removable_cover_candidate')
    add('body_nose_plug','ivory',cylinder((148.2,0,316),4.1,1.2,0,.3),'shell','end_plug_candidate')
    add('body_tail_plug','ivory',cylinder((-170.2,0,312),4.1,1.2,0,.3),'shell','end_plug_candidate')
    add('belly_frame','graphite',section_solid([(207,-10,0,54,27),(213,-10,0,74,42),(224,-10,0,92,57)],2,3,12),'chassis')
    add('button_socket','graphite',cylinder((-86,0,378),10,4,2,.8),'shell')
    add('top_button','orange',cylinder((-86,0,381),8.2,3.6,2,.8),'shell')

    root=Path(__file__).resolve().parents[2]
    spec=json.loads((root/'robots/Goose_V0.1/configs/robot_spec.json').read_text())['servos']
    def servo(name,kind,shaft,axis=(0,1,0),up=(0,0,1)):
        s=spec[kind]; w,h,d=np.asarray(s['body_whd_m'])*1000
        if kind=='xc330': d=26 # Official current body envelope, not old RC2 23 mm reservation.
        top=s['shaft_from_top_m']*1000; center_z=top-h/2
        ey=np.asarray(axis,float); ey/=np.linalg.norm(ey)
        ez=np.asarray(up,float); ez-=np.dot(ez,ey)*ey; ez/=np.linalg.norm(ez)
        ex=np.cross(ey,ez); rot=np.column_stack((ex,ey,ez)); p=np.asarray(shaft,float)
        def put(suffix,mat,mesh,role='catalog_dimension_proxy'):
            add(name+'_'+suffix,mat,mesh.transformed(rot,tuple(p)),name,role)
        put('case','graphite',rounded_box((0,0,center_z),(w,d,h),2,10))
        put('front_case','titanium',rounded_box((0,d/2-.6,center_z),(w-1.4,1.6,h-1.4),.65,8))
        radius=13 if kind=='xm540' else 10.5 if kind=='xm430' else 8
        put('horn','titanium',cylinder((0,d/2+1.8,0),radius,3.6,1,.65))
        put('idler','titanium',cylinder((0,-d/2-1.8,0),radius*.85,3.6,1,.65))
        put('output_ring','orange',ring((0,d/2+4,0),radius+2,radius+.4,1.6), 'painted_custom_guard')
        put('shaft_bolt','graphite',cylinder((0,d/2+4.2,0),3.2,1.5,1,.4))
        pcd=s['horn_pcd_m']*1000
        for i,t in enumerate(np.arange(s['horn_hole_count'])*2*np.pi/s['horn_hole_count']):
            put(f'horn_fixing_{i}','graphite',section_solid([(d/2+3.4,pcd/2*np.cos(t),pcd/2*np.sin(t),1.05,1.05),(d/2+4.2,pcd/2*np.cos(t),pcd/2*np.sin(t),1.05,1.05)],1,2,4))
        put('connector','rubber',rounded_box((0,-d/2-1,top-h+8),(11,3,6),1,6))
        motors.append(dict(joint=name,model=s['model'],case_whd_mm=[w,h,d],shaft_world_mm=list(shaft),axis_world=list(axis),up_world=list(ez),source=s['source'],geometry='reconstructed nominal dimension proxy; not vendor CAD',selection_status='candidate, not procurement freeze'))
        return d

    def fork(name,a,b,span=56,width=16):
        # Custom paired plates expose the stock motor between front/rear supports.
        for side,label in [(-1,'rear'),(1,'front')]:
            aa=np.array(a,float); bb=np.array(b,float); aa[1]+=side*span/2; bb[1]+=side*span/2
            add(name+'_'+label,'ivory',link(aa,bb,width,3.5),name)
        end=np.array(b,float)
        add(name+'_bridge','titanium',rounded_box(tuple(end),(16,span+3,7),2,8),name)

    # Five-axis neck/head chain from the present modular-servo architecture.
    servo('neck_yaw','xm430',(43,0,342),(0,0,1),(1,0,0))
    add('neck_yaw_mount','graphite',cylinder((43,0,381),27,8,2,2),'neck_mount')
    servo('neck_pitch','xm540',(43,0,408))
    servo('neck_mid_pitch','xm540',(-30,0,512),up=(-.57,0,.82))
    fork('lower_neck_fork',(43,0,408),(-30,0,512),58,19)
    servo('head_pitch','xm430',(42,0,605),up=(.73,0,.68))
    fork('upper_neck_fork',(-30,0,512),(42,0,605),53,16)
    servo('head_roll','xc330',(76,0,587),(1,0,0),(0,0,1))
    fork('head_roll_bridge',(42,0,605),(76,0,587),42,13)
    cable=[(31,31,379),(29,31,413),(-47,31,489),(-47,31,520),(43,29,601),(75,20,596)]
    for i,(a,b) in enumerate(zip(cable,cable[1:])): add(f'neck_cable_{i}','rubber',link(a,b,4,4),'neck_cable')

    # One compact head volume: brow, flush optical window, cheek and bill root.
    rows=[(64,0,603,4,5),(77,0,603,28,29),(96,0,603,40,36),
          (119,0,602,44,35),(142,0,598,44,36),(162,0,595,41,33),
          (173,0,601,35,36),(177,0,600,31,34)]
    x=np.linspace(64,177,57); hp=PchipInterpolator(np.array(rows)[:,0],np.array(rows)[:,1:],axis=0)
    vals=hp(x); head=section_solid(np.column_stack((x,vals)),0,2.8,16)
    # Lower the cheeks around the rear linkage while keeping the camera bay clear.
    def smooth(v):
        v=np.clip(v,0,1); return v*v*(3-2*v)
    v=head.vertices
    v[:,2]-=9*smooth((v[:,0]-125)/25)*(1-smooth((v[:,0]-171)/7))*smooth((abs(v[:,1])-15)/10)*smooth((582-v[:,2])/20)
    # Cover the bearing envelope with continuous cheeks, not exposed crescent edges.
    v[:,1]+=np.sign(v[:,1])*7*smooth((v[:,0]-136)/12)*(1-smooth((v[:,0]-171)/6))*smooth((591-v[:,2])/10)*smooth((abs(v[:,1])-15)/12)
    add('goose_head_shell','ivory',head,'head','shell_outer_surface_candidate')
    visor=section_solid([(177.2,0,606,24,20),(178.3,0,606,27,23),(180.1,0,606,26,22)],0,3.2,12)
    add('flush_camera_window','graphite',visor,'head')
    add('camera_glass','glass',cylinder((181.0,0,606),14.4,1.4,0,.6),'head')
    add('camera_inner_lens','lens',cylinder((182,0,606),9.8,.7,0,.25),'head')
    add('camera_eye_bezel','orange',ring((180.5,0,606),16.7,14.9,1.2,axis=0),'head','decorative_optical_surround')
    add('camera_board_proxy','graphite',rounded_box((160.3,0,606),(1.6,18,40),.5,8),'head_internal','camera_dimension_proxy')
    add('camera_lens_proxy','graphite',cylinder((170.155,0,606),9,19.69,0,.5),'head_internal','camera_dimension_proxy')
    # No decorative side eyes: the single dark optical band is the expression.
    upper=[(157,0,566,25,12),(176,0,566,29,12),(198,0,564,28,10),
           (221,0,561,23,7),(240,0,558.4,16,4.2),(254,0,556.9,9,2.7),
           (261,0,556,4,1.8),(263,0,556,1.8,1.1)]
    lower=[(160,0,546.5,23,5.5),(180,0,547,26,5),(208,0,547.5,24,4.5),
           (236,0,548.5,16,3.5),(253,0,550,8,2),(259,0,551,3.5,1.2),(261,0,551.4,1.5,.7)]
    add('fixed_upper_bill','orange',smooth_bill(upper),'head')
    # Natural hinged lower bill; the upper bill stays fixed to the skull.
    pivot=np.array([160.,0.,576.])
    tip=np.array([261.,0.,551.4])-pivot
    angle=brentq(lambda q: tip[0]*np.sin(q)+tip[2]*(1-np.cos(q))-opening,0,np.pi/3) if opening else 0.
    rotation=Rotation.from_rotvec([0,angle,0]).as_matrix()
    def hinge(mesh):
        mesh.vertices=(mesh.vertices-pivot)@rotation.T+pivot
        return mesh
    jaw=hinge(smooth_bill(lower));add('hinged_lower_bill','orange',jaw,'lower_beak')
    upper_pad=smooth_bill([(179,0,553.6,21,.6),(208,0,553.6,21,.6),(238,0,553.6,13,.6),(244,0,553.6,9,.6)])
    lower_pad=smooth_bill([(179,0,552.35,21,.65),(208,0,552.35,21,.65),(238,0,552.35,13,.65),(244,0,552.35,9,.65)])
    add('upper_grip_pad','rubber',upper_pad,'head')
    add('lower_grip_pad','rubber',hinge(lower_pad),'lower_beak')
    # Stronger candidate drive. Transmission envelopes are reservations, not cut gears.
    motor=np.array([140.,0.,576.+np.sqrt(24**2-20**2)])
    servo('beak_drive','xm540',tuple(motor),up=(1,0,0))
    add('beak_pinion_envelope','titanium',cylinder((motor[0],30,motor[2]),7,8,1,.5),'beak_transmission','metal_gear_envelope_not_tooth_cad')
    add('beak_output_gear_envelope','titanium',cylinder((160,30,576),19,8,1,.7),'beak_transmission','metal_gear_envelope_not_tooth_cad')
    add('beak_supported_output_shaft','titanium',cylinder((160,0,576),4,76,1,.4),'beak_transmission','shaft_envelope_candidate')
    for side,label in [(-1,'right'),(1,'left')]:
        add('jaw_bearing_reserve_'+label,'graphite',ring((160,side*36,576),8,4,5),'beak_transmission','bearing_reservation_not_selected_sku')
        heel=link((160,side*22,576),(168,side*22,549),7,3.5)
        add('internal_jaw_heel_'+label,'graphite',hinge(heel),'lower_beak')
    # The pinion requires a separately supported shaft to protect the motor bearing.
    add('pinion_bearing_reserve','graphite',ring((motor[0],38,motor[2]),8,4,5),'beak_transmission','bearing_reservation_not_released_support')

    # Six-axis-per-leg packaging candidate: actual case sizes, visible fork links.
    for side,label in [(-1,'right'),(1,'left')]:
        y=side*89
        servo(label+'_hip_yaw','xm430',(0,side*59,278),(0,0,1),(1,0,0))
        servo(label+'_hip_roll','xm430',(-51,side*78,240),(1,0,0),(0,side,0))
        hip=(7,y,227); knee=(-58,y,132); ankle=(-7,y,62)
        servo(label+'_hip_pitch','xm540',hip,(0,side,0),up=(.56,0,.83))
        servo(label+'_knee_pitch','xm540',knee,(0,side,0),up=(-.59,0,.81))
        servo(label+'_ankle_pitch','xm430',ankle,(0,side,0))
        servo(label+'_ankle_roll','xm430',(53,y,36),(1,0,0),(0,side,0))
        fork(label+'_thigh_fork',hip,knee,58,20)
        fork(label+'_shin_fork',knee,ankle,57,18)
        add(label+'_ankle_crossmember','titanium',rounded_box((22,y,50),(71,39,5),2,10),label+'_foot')
        # Continuous support sole; sweep only outward toward the front.
        # The old heel and longitudinal contact reach are preserved.
        def web_outline(mesh):
            vv=mesh.vertices
            u=np.clip((vv[:,0]+30)/110,0,1); u=u*u*(3-2*u)
            vv[:,1]=y+(vv[:,1]-y)*(1+.24*u)
            vv[:,0]+=np.maximum(vv[:,0]-20,0)*.32
            return mesh
        for name,mat,rows in [
            ('sole','rubber',[(.5,86,44),(2,89,46),(9,89,46),(12,87,44)]),
            ('trim','orange',[(10.5,87,44),(14,85,43),(16.5,83,41)])]:
            mesh=section_solid([(z,10,y,a,b) for z,a,b in rows],2,3.1,16)
            add(label+'_foot_'+name,mat,web_outline(mesh),label+'_foot')
        # A single rising instep contains the roll-servo envelope, instead of a top lump.
        rows=[(-76,y,19,3,2.5),(-67,y,23,25,7),(-40,y,28,37,12),
              (-7,y,31,42,15),(25,y,36,47,20),(53,y,37,49,21),
              (75,y,36,50,20),(95,y,26,46,10),(112,y,19,25,3),(118,y,18,3,2)]
        pp=PchipInterpolator(np.array(rows)[:,0],np.array(rows)[:,1:],axis=0)
        for suffix,mat,lo,hi in [('aft','ivory',-76,19.9),('fore','orange',20.1,118)]:
            xx=np.linspace(lo,hi,41)
            upper=section_solid(np.column_stack((xx,pp(xx))),0,3.1,16)
            add(label+'_foot_upper_'+suffix,mat,upper,label+'_foot','shell_outer_surface_candidate')
    # Nominal electronics / service envelopes from recorded hardware facts.
    # Heights and service margins are explicit layout assumptions where no SKU height is frozen.
    layout=[
        ('battery_service',(-73,0,292),(96,56,38),'graphite','CNHL 1501303BK 78x39x21.5 mm plus provisional swelling/lead/retention space'),
        ('compute_stack',(-60,0,335),(80,48,32),'graphite','Radxa ZERO 3W 65x30 mm and USB hub; stack/thermal/connector height is a reservation'),
        ('left_power_hub',(15,60,309),(58,66,25),'titanium','U2D2 Power Hub PCB 48x57 mm; 25 mm assembly height assumed'),
        ('right_power_hub',(15,-60,309),(58,66,25),'titanium','U2D2 Power Hub PCB 48x57 mm; 25 mm assembly height assumed'),
        ('logic_buck',(-63,55,322),(49,29,22),'graphite','Pololu D24V90F5 40.6x20.3x7.6 mm plus provisional wiring/thermal space'),
        ('servo_buck',(-63,-55,322),(49,29,22),'graphite','Pololu D24V90F5 40.6x20.3x7.6 mm plus provisional wiring/thermal space'),
        ('main_protection',(83,0,301),(44,48,38),'graphite','Relay/fuse/power switching category reservation; no frozen assembly SKU'),
        ('interfaces_audio',(8,0,305),(44,52,32),'graphite','U2D2/IMU/audio category reservation; exact packing and cable bends unresolved')]
    for name,pos,size,mat,basis in layout:
        add(name,mat,rounded_box(pos,size,2,8),'torso_electronics','provisional_electronics_service_envelope')
        parts[-1]['envelope_basis']=basis
    return parts,motors


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--opening',type=float,default=0); parser.add_argument('--doors-open',action='store_true')
    args=parser.parse_args(); out=args.output.resolve(); (out/'quad_source').mkdir(parents=True,exist_ok=True)
    if not 0 <= args.opening <= 30: raise ValueError('Review opening must be between 0 and 30 mm')
    parts,motors=build(args.opening,args.doors_open)
    for part in parts:
        mesh=part.pop('mesh'); path=out/'quad_source'/(part['name']+'.obj'); mesh.write_obj(path)
        part.update(vertices=(mesh.vertices*.001).tolist(),faces=mesh.faces.tolist(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    payload=dict(status='fuller_webfoot_exterior_candidate',appearance_pass=False,physics_pass=False,manufacturing_pass=False,opening_mm=args.opening,doors_exploded=args.doors_open,parts=parts)
    (out/'scene.json').write_text(json.dumps(payload))
    (out/'hardware_basis.json').write_text(json.dumps(dict(status='candidate packaging, not released mechanics',actuators=motors,source_spec_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'robots/Goose_V0.1/configs/robot_spec.json').read_bytes()).hexdigest(),shell_notes='Torso halves and separate covers are hollow quad solids, analytic normal offset 2.4 mm before slight cover fit shrink; no manufacturing wall-thickness acceptance; no mounting/hinge/print release.'),indent=2)+'\n')
    print(json.dumps(dict(parts=len(parts),quads=sum(len(p['faces']) for p in parts),actuators=len(motors),output=str(out))))


if __name__=='__main__': main()
