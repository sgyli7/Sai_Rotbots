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

BODY=np.array([[-184,335,4,3],[-171,332,25,10],[-148,323,47,22],
 [-119,304,70,45],[-84,287,91,67],[-30,281,100,81],
 [22,286,96,91],[66,296,80,87],[102,305,53,69],
 [126,310,29,45],[139,314,4,5]],float)
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
            rear=-148+20*abs(v)**3; front=78-22*abs(v)**3
            x=np.interp(i,[0,10,48,64],[-184,rear,front,139])
            t=np.clip((i-10)/38,0,1)
            half=.11+.57*np.sin(t*np.pi/2)**.7
            center=.25-.10*t
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
            arr[k,1]+=side*2.6*np.sin(np.pi*u)*np.sin(np.pi*v)
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
    add('body_nose_plug','ivory',cylinder((139.2,0,314),4.1,1.2,0,.3),'shell','end_plug_candidate')
    add('body_tail_plug','ivory',cylinder((-184.2,0,335),3.5,1.2,0,.3),'shell','end_plug_candidate')
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

    collar=[]; collar_faces=[]; n=64
    rings=[(352,61,52),(362,53,47),(374,43,38),(385,35,32),(391,32,29),
           (391,29,26),(385,31.5,29),(374,39.5,35),(362,49.5,44),(352,57.5,49)]
    for z,rx,ry in rings:
        for t in np.arange(n)*2*np.pi/n: collar.append((43+rx*np.cos(t),ry*np.sin(t),z))
    for k in range(len(rings)):
        for j in range(n): collar_faces.append((k*n+j,k*n+(j+1)%n,((k+1)%len(rings))*n+(j+1)%n,((k+1)%len(rings))*n+j))
    add('sculpted_neck_shoulder','ivory',QuadMesh(np.array(collar),np.array(collar_faces)).orient_outward(),'shell','hollow_shell_candidate')

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

    # Round crown, tapered forehead and side eyes make the head read as a goose.
    rows=[(53,0,586,3,5),(65,0,589,24,27),(85,0,594,38,34),
          (109,0,593,41,34),(130,0,587,37,32),(150,0,579,31,26),
          (168,0,573,25,19),(177,0,571,22,16)]
    x=np.linspace(53,177,57); vals=PchipInterpolator(np.array(rows)[:,0],np.array(rows)[:,1:],axis=0)(x)
    add('goose_head_shell','ivory',section_solid(np.column_stack((x,vals)),0,2.8,16),'head','shell_outer_surface_candidate')
    # An inset forward optical window replaces the protruding camera goggle.
    add('camera_bezel','graphite',cylinder((177.7,0,576),9.5,1.6,0,.5),'head')
    add('camera_glass','glass',cylinder((178.7,0,576),7.7,.8,0,.25),'head')
    add('camera_inner_lens','lens',cylinder((179.2,0,576),4.5,.5,0,.15),'head')
    for side,label in [(-1,'right'),(1,'left')]:
        # Eyes are decorative inserts. The forward lens remains the camera.
        hp=PchipInterpolator(np.array(rows)[:,0],np.array(rows)[:,1:],axis=0)
        _,cz,ry,rz=hp(123); _,czd,ryd,rzd=hp.derivative()(123)
        zz=605-cz; power=2.8; yy=ry*(1-(abs(zz)/rz)**power)**(1/power)
        normal=np.array([-power*(yy/ry)**power*ryd/ry+power*(abs(zz)/rz)**(power-1)*np.sign(zz)*(-czd/rz-zz*rzd/rz**2), side*power*(yy/ry)**(power-1)/ry, power*(abs(zz)/rz)**(power-1)*np.sign(zz)/rz])
        normal/=np.linalg.norm(normal); rot,_=Rotation.align_vectors([normal],[[0,1,0]])
        eye_base=np.array([123,side*yy,605])
        eye=cylinder((0,0,0),5.8,1.8,1,.7)
        eye.vertices*=np.array([1.24,1,.70])
        add('eye_'+label,'glass',eye.transformed(rot.as_matrix(),tuple(eye_base+normal*1.15)),'head')
    for part in previous_build(opening):
        if part['group'] in ('lower_beak','lower_beak_link') or part['name'] in ('upper_beak','nostril') or part['name'].startswith('beak_hinge'):
            name=part['name'].replace('-1','right').replace('_1','_left')
            mesh=part['mesh']; mesh.vertices[:,0]=151+(mesh.vertices[:,0]-151)*.86
            if part['name'].startswith('beak_hinge'):
                centre=(mesh.vertices.max(axis=0)+mesh.vertices.min(axis=0))/2
                mesh.vertices=centre+(mesh.vertices-centre)*.68
                mesh.vertices[:,1]-=np.sign(centre[1])*8
            add(name,part['material'],mesh,part['group'])
    servo('beak_drive','xc330',(139,0,557),up=(1,0,0))

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
    parts,motors=build(args.opening,args.doors_open)
    for part in parts:
        mesh=part.pop('mesh'); path=out/'quad_source'/(part['name']+'.obj'); mesh.write_obj(path)
        part.update(vertices=(mesh.vertices*.001).tolist(),faces=mesh.faces.tolist(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    payload=dict(status='sculpted_exterior_candidate',appearance_pass=False,physics_pass=False,manufacturing_pass=False,opening_mm=args.opening,doors_exploded=args.doors_open,parts=parts)
    (out/'scene.json').write_text(json.dumps(payload))
    (out/'hardware_basis.json').write_text(json.dumps(dict(status='candidate packaging, not released mechanics',actuators=motors,source_spec_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'robots/Goose_V0.1/configs/robot_spec.json').read_bytes()).hexdigest(),shell_notes='Torso halves and separate covers are hollow quad solids, analytic normal offset 2.4 mm before slight cover fit shrink; no manufacturing wall-thickness acceptance; no mounting/hinge/print release.'),indent=2)+'\n')
    print(json.dumps(dict(parts=len(parts),quads=sum(len(p['faces']) for p in parts),actuators=len(motors),output=str(out))))


if __name__=='__main__': main()
