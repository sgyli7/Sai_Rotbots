"""Reference-led R2 exterior rebuild. Quad authoring geometry, not a release CAD."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation
from build_goose_quad_exterior_study import QuadMesh, rounded_box, conform_to_round_box, quad_plate


def section_solid(rows, axis=0, power=4, count=12):
    """Closed quad loft with quad-grid end caps; rows=(axis, a, b, ha, hb)."""
    rows=np.asarray(rows,float)
    coords=np.linspace(-1,1,count+1)
    perimeter=[(i,0) for i in range(count)]+[(count,j) for j in range(count)]+[(i,count) for i in range(count,0,-1)]+[(0,j) for j in range(count,0,-1)]
    other=[i for i in range(3) if i!=axis]
    def point(row,i,j):
        u,v=coords[i],coords[j]
        a=u*np.sqrt(1-v*v/2); b=v*np.sqrt(1-u*u/2)
        rho=np.hypot(a,b)
        if rho>1e-12:
            den=(abs(a/rho)**power+abs(b/rho)**power)**(1/power)
            a/=den; b/=den
        p=np.zeros(3); p[axis]=row[0]
        p[other[0]]=row[1]+a*row[3]; p[other[1]]=row[2]+b*row[4]
        return p
    vertices=[]; rings=[]; faces=[]
    for row in rows:
        ring=[]
        for i,j in perimeter:
            ring.append(len(vertices)); vertices.append(point(row,i,j))
        rings.append(ring)
    for first,second in zip(rings,rings[1:]):
        for j in range(len(perimeter)):
            k=(j+1)%len(perimeter)
            faces.append((first[j],first[k],second[k],second[j]))
    for end in (0,len(rows)-1):
        grid=dict(zip(perimeter,rings[end]))
        for i in range(1,count):
            for j in range(1,count):
                grid[(i,j)]=len(vertices); vertices.append(point(rows[end],i,j))
        for i in range(count):
            for j in range(count):
                faces.append((grid[(i,j)],grid[(i+1,j)],grid[(i+1,j+1)],grid[(i,j+1)]))
    return QuadMesh(np.asarray(vertices),np.asarray(faces)).orient_outward()


def cylinder(center,radius,length,axis=1,bevel=1.5):
    c=np.asarray(center); other=[i for i in range(3) if i!=axis]
    h=length/2; bevel=min(bevel,h*.7,radius*.4)
    profile=[(-h,radius-bevel),(-h+bevel*.3,radius-bevel*.3),(-h+bevel,radius),
             (h-bevel,radius),(h-bevel*.3,radius-bevel*.3),(h,radius-bevel)]
    return section_solid([(c[axis]+z,c[other[0]],c[other[1]],r,r) for z,r in profile],axis,2,12)


def link(start,end,width,depth):
    start=np.asarray(start,float); end=np.asarray(end,float); d=end-start; length=np.linalg.norm(d)
    mesh=section_solid([(-length/2,0,0,width*.33,depth*.35),(-length/2+5,0,0,width*.48,depth*.48),
                        (-length*.32,0,0,width/2,depth/2),(length*.32,0,0,width*.46,depth*.48),
                        (length/2-4,0,0,width*.4,depth*.4),(length/2,0,0,width*.28,depth*.30)],2,4,8)
    rot,_=Rotation.align_vectors([d/length],[[0,0,1]])
    return mesh.transformed(rot.as_matrix(),tuple((start+end)/2))


def smooth_bill(rows):
    rows=np.asarray(rows,float)
    x=np.unique(np.concatenate([np.linspace(a,b,5) for a,b in zip(rows[:-1,0],rows[1:,0])]))
    interp=PchipInterpolator(rows[:,0],rows[:,1:],axis=0)(x)
    return section_solid(np.column_stack((x,interp)),0,3.5,12)


def build(opening=0):
    parts=[]
    def add(name,mat,mesh,group): parts.append(dict(name=name,material=mat,mesh=mesh,group=group))
    body_center=(-10,0,286); body_size=(286,198,184); body_radius=67
    add('torso','ivory',rounded_box(body_center,body_size,body_radius,24),'torso')
    add('undertray','graphite',section_solid([(190,-10,0,87,42),(196,-10,0,106,58),(204,-10,0,117,70),(212,-10,0,120,75)],2,3.5,16),'torso')
    add('top_button_base','graphite',cylinder((-83,0,377),11,3,2,.7),'torso')
    add('top_button','orange',cylinder((-83,0,380),9,4,2,1),'torso')
    for side in (-1,1):
        seam=conform_to_round_box(quad_plate((-47,0,286),(0,2,1),(177,103,1.6),(16,15),20),1,side,body_center,body_size,body_radius,1.0)
        door=conform_to_round_box(quad_plate((-47,0,286),(0,2,1),(174,100,2.0),(16,15),20),1,side,body_center,body_size,body_radius,2.4)
        add(f'door_reveal_{side}','seam',seam,'torso')
        add(f'wing_door_{side}','ivory',door,f'wing_door_{side}')
        for z in (277,):
            for x in (-103,-95,-87):
                vent=conform_to_round_box(quad_plate((x,0,z),(0,2,1),(2.4,12,1),(0.7,3),8),1,side,body_center,body_size,body_radius,3.8)
                add(f'door_vent_{side}_{x}','graphite',vent,f'wing_door_{side}')
        for x in (-112,18):
            dy=max(abs(x+10)-(143-67),0); dz=max(abs(303-286)-(92-67),0)
            y=32+np.sqrt(67**2-dy**2-dz**2)+3.8
            add(f'door_fastener_{side}_{x}','titanium',cylinder((x,side*y,303),2.8,1.2,1,.4),f'wing_door_{side}')
    # Neck: cylindrical axes and tapered covers with a visible rear cable.
    add('neck_saddle','graphite',rounded_box((45,0,375),(65,60,17),6,12),'neck_root')
    root=(43,0,403); elbow=(-28,0,512); yoke=(59,0,598)
    for name,p,r,l in [('neck_root',root,30,56),('neck_elbow',elbow,22,48),('head_yoke',yoke,22,46)]:
        add(name,'graphite',cylinder(p,r,l,1,2),name)
        for side in (-1,1):
            add(f'{name}_rim_{side}','titanium',cylinder((p[0],side*(l/2+1),p[2]),r*.74,2.3,1,.6),name)
            add(f'{name}_badge_{side}','orange',cylinder((p[0],side*(l/2+2.3),p[2]),r*.42,1.8,1,.6),name)
    add('lower_neck_spine','graphite',link((43,0,422),(-27,0,511),28,34),'neck_lower')
    add('lower_neck_motor_cover','graphite',link((39,0,425),(21,0,450),39,42),'neck_lower')
    add('lower_neck_fairing','ivory',link((24,0,451),(-22,0,509),37,39),'neck_lower')
    add('upper_neck_spine','graphite',link((-28,0,516),(58,0,598),24,29),'neck_upper')
    add('upper_neck_fairing','ivory',link((-18,0,529),(56,0,594),35,37),'neck_upper')
    cable=[(33,18,423),(4,18,447),(-47,18,497),(-43,18,524),(36,18,604)]
    for i,(a,b) in enumerate(zip(cable,cable[1:])):
        add(f'neck_cable_{i}','rubber',link(a,b,5,5),'neck_cable')
    # Small camera head, flush black mask, and pointed upper/floating lower R2 bill.
    hc=(111,0,588); hs=(110,92,94); hr=24
    add('head_shell','ivory',rounded_box(hc,hs,hr,24),'head')
    panel=section_solid([(158.5,0,589,31,30),(160,0,589,35,34),(168,0,589,35,34),(169,0,589,33,32)],0,5,16)
    add('camera_mask','graphite',panel,'head')
    add('camera_orange_ring','orange',cylinder((168,0,589),26,7,0,1.5),'head')
    add('camera_barrel','graphite',cylinder((173,0,589),21.5,7,0,1.4),'head')
    add('camera_glass','glass',cylinder((177.1,0,589),17.5,1.5,0,.4),'head')
    add('camera_inner_lens','lens',cylinder((178,0,589),10,1.2,0,.3),'head')
    for side in (-1,1):
        add(f'head_side_port_rim_{side}','titanium',cylinder((112,side*46.1,586),5.1,1.7,1,.5),'head')
        add(f'head_side_port_{side}','graphite',cylinder((112,side*47.2,586),3.3,1,1,.3),'head')
        add(f'beak_hinge_{side}','orange',cylinder((155,side*40,547),17,7,1,2),'head')
        add(f'beak_hinge_core_{side}','titanium',cylinder((155,side*44,547),10,2,1,.7),'head')
    upper=[(151,0,549,27,18),(165,0,550,29,19),(190,0,548,28,17),(222,0,544,23,13),
           (255,0,538,16,7),(280,0,534.5,10,3.5),(292,0,533,6,2),(296,0,532,3,1.5),(298,0,532,1.5,1)]
    lower=[(156,0,522,24,6),(172,0,522,26,6),(208,0,522.5,24,5.5),
           (246,0,523.5,17,4.5),(277,0,525,9,3),(291,0,526,4.5,2),(295,0,527,1.5,.8)]
    add('upper_beak','orange',smooth_bill(upper),'head')
    low=smooth_bill(lower)
    # R2 parallelogram preserves jaw orientation, with accompanying forward shift.
    q0=np.deg2rad(40); q=np.arcsin(np.sin(q0)-opening/25)
    dx=25*(np.cos(q)-np.cos(q0))
    low.vertices+=np.array((dx,0,1.4-opening))
    add('lower_beak','orange',low,'lower_beak')
    pad=smooth_bill([(174,0,528.3,20,.55),(208,0,528.3,20,.55),(244,0,528.3,14,.55),(279,0,528.3,5,.55)])
    pad.vertices+=np.array((dx,0,1.4-opening)); add('lower_grip_pad','rubber',pad,'lower_beak')
    add('nostril','graphite',rounded_box((204,0,562.4),(8,4,1.8),.8,8),'head')
    if opening:
        for side in (-1,1):
            for z in (533,547):
                a=(148,side*20,z); b=(148+25*np.cos(q),side*20,z+25*np.sin(q))
                add(f'r2_link_{side}_{z}','titanium',link(a,b,4,4),'lower_beak_link')
            b=(148+25*np.cos(q),side*20,533+25*np.sin(q))
            c=(b[0],side*20,b[2]+14)
            jaw=(156+dx,side*20,523.4-opening)
            add(f'r2_carrier_{side}','graphite',link(b,c,5,5),'lower_beak_link')
            add(f'r2_jaw_support_{side}','graphite',link(b,jaw,7,5),'lower_beak_link')
            for label,p in [('b',b),('c',c)]:
                add(f'r2_pin_{side}_{label}','titanium',cylinder(p,2.7,6,1,.4),'lower_beak_link')
    for side in (-1,1):
        y=side*87
        hip=(0,y,218); knee=(-64,y,126); ankle=(-9,y,45)
        add(f'hip_{side}','graphite',cylinder(hip,27,42,1,2),f'leg_{side}')
        add(f'thigh_spine_{side}','graphite',link(hip,knee,28,30),f'leg_{side}')
        add(f'thigh_fairing_{side}','ivory',link((hip[0]-2,y,hip[2]-5),(knee[0]+4,y,knee[2]+6),42,35),f'leg_{side}')
        add(f'shin_spine_{side}','graphite',link(knee,ankle,27,29),f'leg_{side}')
        add(f'shin_fairing_{side}','ivory',link((knee[0]+4,y,knee[2]-7),(ankle[0]-3,y,ankle[2]+7),38,35),f'leg_{side}')
        for name,p,r in [('hip',hip,27),('knee',knee,22),('ankle',ankle,20)]:
            if name!='hip': add(f'{name}_{side}','graphite',cylinder(p,r,40,1,1.6),f'leg_{side}')
            add(f'{name}_rim_{side}','titanium',cylinder((p[0],y+side*22,p[2]),r*.65,3,1,.6),f'leg_{side}')
            add(f'{name}_center_{side}','graphite',cylinder((p[0],y+side*24,p[2]),r*.33,1.7,1,.4),f'leg_{side}')
        for name,mat,rows in [
            ('sole','rubber',[(.5,86,43),(2,89,45),(9,89,45),(12,86,43)]),
            ('trim','orange',[(10.5,87,43.5),(14,86,43),(17,84,41)]),
            ('upper','ivory',[(16,83.5,40.5),(19,84,41),(27,79,38),(34,72,33),(35,68,30)]),
        ]:
            add(f'foot_{name}_{side}',mat,section_solid([(z,10,y,a,b) for z,a,b in rows],2,4,16),f'foot_{side}')
        add(f'ankle_boot_{side}','graphite',rounded_box((-13,y,35),(59,47,9),4,12),f'foot_{side}')
        add(f'foot_toe_flash_{side}','orange',quad_plate((67,y,30.6),(0,1,2),(30,40,1.5),(4,6),12),f'foot_{side}')
    return parts


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--opening',type=float,default=0)
    args=parser.parse_args(); out=args.output.resolve(); (out/'quad_source').mkdir(parents=True,exist_ok=True)
    parts=build(args.opening); scene=[]
    for part in parts:
        mesh=part.pop('mesh'); name=part['name']; path=out/'quad_source'/f'{name}.obj'; mesh.write_obj(path)
        part.update(vertices=(mesh.vertices*.001).tolist(),faces=mesh.faces.tolist(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        scene.append(part)
    data=dict(status='unapproved_exterior_rebuild',appearance_pass=False,manufacturing_pass=False,physics_pass=False,opening_mm=args.opening,parts=scene)
    (out/'scene.json').write_text(json.dumps(data),encoding='utf-8')
    print(json.dumps(dict(output=str(out),parts=len(parts),quad_faces=sum(len(x['faces']) for x in scene))))


if __name__=='__main__': main()
