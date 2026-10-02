"""Goose sculpted revision: chest, shoulders, rising tail and a tapered goose head.

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
from scipy.spatial.transform import Rotation
from build_goose_r2_reference_rebuild import (build as previous_build, section_solid,
    cylinder, link, smooth_bill, rounded_box, QuadMesh)

BODY=np.array([[-156,316,4,4],[-145,312,27,17],[-124,300,56,35],
 [-93,287,81,58],[-45,280,96,76],[10,284,97,87],
 [54,293,85,91],[91,304,64,72],[119,312,35,46],[134,316,4,5]],float)
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
            rear=-130+20*abs(v)**3; front=76-22*abs(v)**3
            x=np.interp(i,[0,10,48,64],[-156,rear,front,134])
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
            if 40<=i<50 and j>=43: continue # true neck opening through both shell halves
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
    add('body_nose_plug','ivory',cylinder((134.2,0,316),4.1,1.2,0,.3),'shell','end_plug_candidate')
    add('body_tail_plug','ivory',cylinder((-156.2,0,316),4.1,1.2,0,.3),'shell','end_plug_candidate')
    add('belly_frame','graphite',section_solid([(207,-10,0,54,27),(213,-10,0,74,42),(224,-10,0,92,57)],2,3,12),'chassis')
    add('button_socket','graphite',cylinder((-79,0,357),10,4,2,.8),'shell')
    add('top_button','orange',cylinder((-79,0,360),8.2,3.6,2,.8),'shell')

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
    servo('head_pitch','xm430',(61,0,599),up=(.73,0,.68))
    fork('upper_neck_fork',(-30,0,512),(61,0,599),53,16)
    servo('head_roll','xc330',(99,0,588),(1,0,0),(0,0,1))
    cable=[(31,31,379),(29,31,413),(-47,31,489),(-47,31,520),(43,29,601),(75,20,596)]
    for i,(a,b) in enumerate(zip(cable,cable[1:])): add(f'neck_cable_{i}','rubber',link(a,b,4,4),'neck_cable')

    # One compact head volume: brow, flush optical window, cheek and bill root.
    rows=[(70,0,598,4,5),(79,0,599,25,26),(96,0,600,36,33),
          (119,0,600,39,33),(142,0,596,38,32),(162,0,590,34,29),
          (173,0,588,29,26),(177,0,588,26,25)]
    x=np.linspace(70,177,57); hp=PchipInterpolator(np.array(rows)[:,0],np.array(rows)[:,1:],axis=0)
    vals=hp(x); head=section_solid(np.column_stack((x,vals)),0,2.8,16)
    # Lower the cheeks around the rear linkage while keeping the camera bay clear.
    def smooth(v):
        v=np.clip(v,0,1); return v*v*(3-2*v)
    v=head.vertices
    v[:,2]-=9*smooth((v[:,0]-125)/25)*(1-smooth((v[:,0]-171)/7))*smooth((abs(v[:,1])-15)/10)*smooth((582-v[:,2])/20)
    add('goose_head_shell','ivory',head,'head','shell_outer_surface_candidate')
    visor=section_solid([(177.2,0,594,19,9.5),(178,0,594,21,11),(179.1,0,594,20,10)],0,3.2,12)
    add('flush_camera_window','graphite',visor,'head')
    add('camera_glass','glass',cylinder((179.4,0,594),7.6,.7,0,.25),'head')
    add('camera_inner_lens','lens',cylinder((179.9,0,594),4.8,.5,0,.15),'head')
    add('camera_board_proxy','graphite',rounded_box((160.3,0,594),(1.6,18,40),.5,8),'head_internal','camera_dimension_proxy')
    add('camera_lens_proxy','graphite',cylinder((170.155,0,594),9,19.69,0,.5),'head_internal','camera_dimension_proxy')
    # No decorative side eyes: the single dark optical band is the expression.
    upper=[(157,0,566,25,12),(176,0,566,29,12),(198,0,564,28,10),
           (221,0,561,23,7),(240,0,558.4,16,4.2),(254,0,556.9,9,2.7),
           (261,0,556,4,1.8),(263,0,556,1.8,1.1)]
    lower=[(160,0,546.5,23,5.5),(180,0,547,26,5),(208,0,547.5,24,4.5),
           (236,0,548.5,16,3.5),(253,0,550,8,2),(259,0,551,3.5,1.2),(261,0,551.4,1.5,.7)]
    add('fixed_upper_bill','orange',smooth_bill(upper),'head')
    q0=np.deg2rad(40); q=np.arcsin(np.sin(q0)-opening/25)
    dx=25*(np.cos(q)-np.cos(q0)); offset=np.array([dx,0,-opening])
    jaw=smooth_bill(lower);jaw.vertices+=offset
    add('parallel_lower_bill','orange',jaw,'lower_beak')
    upper_pad=smooth_bill([(179,0,553.6,21,.6),(208,0,553.6,21,.6),(238,0,553.6,13,.6),(244,0,553.6,9,.6)])
    lower_pad=smooth_bill([(179,0,552.35,21,.65),(208,0,552.35,21,.65),(238,0,552.35,13,.65),(244,0,552.35,9,.65)])
    add('upper_grip_pad','rubber',upper_pad,'head');lower_pad.vertices+=offset
    add('lower_grip_pad','rubber',lower_pad,'lower_beak')
    # Direct drive of the upper 25 mm crank at the actual XC330 output axis.
    servo('beak_drive','xc330',(147,0,562),up=(1,0,0))
    for side,label in [(-1,'right'),(1,'left')]:
        for z in (548,562):
            a=np.array([147,side*19,z]);b=a+np.array([25*np.cos(q),0,25*np.sin(q)])
            add(f'concealed_crank_{label}_{z}','titanium',link(a,b,4.2,3.0),'beak_linkage')
            for pivot,p in [('fixed',a),('moving',b)]:
                add(f'beak_pin_{label}_{z}_{pivot}','graphite',cylinder(p,2.2,4,1,.35),'beak_linkage')
        upper_b=np.array([147+25*np.cos(q),side*19,562+25*np.sin(q)])
        heel=np.array([166.15+dx,side*19,550-opening])
        add('jaw_heel_'+label,'graphite',link(upper_b,heel,6,3.5),'lower_beak')
    return_beak=dict(crank_length_mm=25,fixed_pivot_separation_mm=14,closed_angle_deg=40,
                     opening_mm=opening,lower_jaw_shift_x_mm=float(dx),jaw_parallel=True)

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
        for name,mat,rows in [
            ('sole','rubber',[(.5,86,44),(2,89,46),(9,89,46),(12,87,44)]),
            ('trim','orange',[(10.5,87,44),(14,85,43),(16.5,83,41)]),
            ('upper','ivory',[(15,82,40),(20,83,41),(29,77,37),(35,67,32),(37,55,26)])]:
            add(label+'_foot_'+name,mat,section_solid([(z,10,y,a,b) for z,a,b in rows],2,3.1,16),label+'_foot')
        # Service hood only covers the actual forward roll-servo reservation.
        add(label+'_ankle_service_hood','ivory',rounded_box((52,y-side*12,43),(42,58,28),10,16),label+'_foot','service_hood_outer_candidate')
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
    payload=dict(status='integrated_exterior_candidate',appearance_pass=False,physics_pass=False,manufacturing_pass=False,opening_mm=args.opening,doors_exploded=args.doors_open,parts=parts)
    (out/'scene.json').write_text(json.dumps(payload))
    (out/'hardware_basis.json').write_text(json.dumps(dict(status='candidate packaging, not released mechanics',actuators=motors,source_spec_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'robots/Goose_V0.1/configs/robot_spec.json').read_bytes()).hexdigest(),shell_notes='Torso halves and separate covers are hollow quad solids, analytic normal offset 2.4 mm before slight cover fit shrink; no manufacturing wall-thickness acceptance; no mounting/hinge/print release.'),indent=2)+'\n')
    print(json.dumps(dict(parts=len(parts),quads=sum(len(p['faces']) for p in parts),actuators=len(motors),output=str(out))))


if __name__=='__main__': main()
