"""Generate original parametric Goose RC2 components (millimetres in CAD).

Vendor geometry is a dimension/mass envelope, never a copied vendor STEP.
Manufacturing acceptance is separate from export validity and is reported as
false until attachment stacks and the swept assembly have been reviewed.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from build123d import (Box, CenterOf, Compound, Cylinder, Ellipse, Location, Pos, Rot,
                      Sphere, export_brep, export_step, export_stl, loft)
from OCP.gp import gp_Trsf

from sai_agent.goose.spec import home_frames, load_spec, motor_rotation
from sai_agent.paths import resource_root


def transform(shape, rotation=np.eye(3), position=np.zeros(3)):
    matrix=np.eye(4);matrix[:3,:3]=rotation;matrix[:3,3]=position
    trsf=gp_Trsf();trsf.SetValues(*[float(x) for x in matrix[:3,:].ravel()])
    return shape.moved(Location(trsf))


def box(size, pos=(0,0,0)):
    return Pos(*map(float,pos))*Box(*map(float,size))


def cylinder(radius, length, pos=(0,0,0), axis='z'):
    orientation=Rot(90,0,0) if axis=='y' else Rot(0,90,0) if axis=='x' else Rot(0,0,0)
    return Pos(*map(float,pos))*orientation*Cylinder(float(radius),float(length))


def holes(shape, points, diameter, length, axis):
    for p in points:shape=shape-cylinder(diameter/2,length,p,axis)
    return shape


def egg(dims):
    # Avoid coincident transformed sphere faces in repeated shell/boss booleans.
    # Fifteen native ellipse sections make a smooth editable closed loft.
    return loft([Pos(0,0,dims[2]*math.sin(t))*Ellipse(dims[0]*math.cos(t),dims[1]*math.cos(t))
                 for t in np.linspace(-math.pi/2+.02,math.pi/2-.02,15)])


def plate_on_y(width, height, depth, center_z, y, pcd, n, diameter, boss):
    # Flat profile is easy to print. Large lower corners can be softened later.
    shape=box((width,depth,height),(0,y,center_z))
    shape=shape+cylinder(width/2,depth,(0,y,0),'y')
    points=[(pcd/2*math.cos(a),y,pcd/2*math.sin(a))
            for a in np.arange(n)*2*math.pi/n]
    return holes(shape,points,diameter,depth+2,'y')-cylinder(boss/2,depth+2,(0,y,0),'y')


def static_cradle(kind, servo):
    width,height,depth=np.asarray(servo['body_whd_m'])*1000
    top=servo['shaft_from_top_m']*1000;bottom=top-height
    gap=.3;wall=3.0
    left=box((wall,depth+4,height+4),(-(width+wall)/2-gap,0,(top+bottom)/2))
    right=box((wall,depth+4,height+4),((width+wall)/2+gap,0,(top+bottom)/2))
    base=box((width+20,depth+8,4),(0,0,bottom-2))
    # Keep the centre of the base open for the rear/bottom cable egress.
    base=base-box((12 if kind in ('xm430','xm540') else width-10,depth-8,8),(0,0,bottom-2))
    shape=left+right+base
    if kind in ('xm430','xm540'):
        rows=(4,28) if kind=='xm430' else (6,38)
        depths=(11,23) if kind=='xm430' else (14,30)
        points=[(0,depth/2-d,-v) for d in depths for v in rows]
        shape=holes(shape,points,2.9,width+2*wall+2,'x')
    else:
        # Through pilot sockets mirror the case-corner ear mounting scheme;
        # the supplied M2 TAP screws enter the vendor plastic, not these ears.
        for y in (-depth/2-1,depth/2+1):
            ears=box((width+6,2,height+4),(0,y,(top+bottom)/2))
            ears=ears-box((width-7,8,height-8),(0,y,(top+bottom)/2))
            ears=holes(ears,[(x,y,z) for x in (-8,8) for z in (7.5,-22.5)],2.4,8,'y')
            shape=shape+ears
    mount=[(x,y,bottom-2) for x in ((-10,10) if kind in ('xm430','xm540') else (-(width/2+5),width/2+5))
           for y in (-(depth/2-3),depth/2-3)]
    shape=holes(shape,mount,3.4,8,'z')
    return shape,{'base_z_mm':bottom-4,'mount_points_mm':mount,
                  'side_screw_max_insertion_mm':3 if kind=='xm430' else 4 if kind=='xm540' else None}


def main():
    root=resource_root();robot=root/'robots/Goose_V0.1';spec=load_spec()
    source=robot/'cad/source';out=robot/'cad/exports'
    source.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    frames=home_frames(spec,root_position=np.zeros(3));parts=[];shapes=[]
    prior_manifest=out/'cad_manifest.json'
    previous={p['name']:p for p in json.loads(prior_manifest.read_text())['parts']} if prior_manifest.exists() else {}
    density={'petg':1.27e-6,'tpu':1.20e-6,'aluminium':2.70e-6}

    def emit(name,shape,body,material='petg',color='white',r=None,p=None,notes=None):
        if r is not None:shape=transform(shape,r,p if p is not None else np.zeros(3))
        if not shape.is_valid or not shape.solids():raise RuntimeError(f'Invalid CAD: {name}')
        if len(shape.solids())!=1:raise RuntimeError(f'Disconnected printable part {name}: {[(round(s.volume,3),tuple(s.center())) for s in shape.solids()]}')
        if shape.volume<=0:raise RuntimeError(f'Non-positive CAD volume: {name}')
        brep=source/(name+'.brep');step=out/(name+'.step');stl=out/(name+'.stl')
        export_brep(shape,brep)
        old=previous.get(name,{})
        unchanged=old.get('files',{}).get('brep',{}).get('sha256')==hashlib.sha256(brep.read_bytes()).hexdigest()
        if not unchanged or not step.exists() or not stl.exists():
            export_step(shape,step);export_stl(shape,stl,tolerance=.15,angular_tolerance=.2)
        center=np.array(tuple(shape.center(CenterOf.MASS)))
        inertia=np.array(shape.matrix_of_inertia)*density[material]*1e-6
        volume=float(shape.volume);mass=volume*density[material]
        br,bp=frames.get(body,frames['torso'])
        shapes.append(transform(shape,br,bp*1000))
        record={'name':name,'body':body,'material':material,'color':color,
                'volume_mm3':volume,'mass_kg':mass,'density_kg_per_m3':density[material]*1e9,
                'center_of_mass_body_m':(center/1000).tolist(),
                'inertia_about_com_body_kg_m2':inertia.tolist(),
                'solid_count':len(shape.solids()),'cad_valid':bool(shape.is_valid),
                'bounds_body_mm':{'min':list(shape.bounding_box().min),'max':list(shape.bounding_box().max)},
                'print_orientation':'choose flat structural face; shells use supported seam face',
                'manufacturing_status':'prototype_attachment_and_swept_clearance_review_pending',
                'notes':notes or [],'files':{}}
        for file in (brep,step,stl):record['files'][file.suffix[1:]]={'path':str(file.relative_to(robot)),
                                                                  'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        parts.append(record)
        print(f'CAD {name}: {mass*1000:.1f} g',flush=True)
        return shape

    dims=np.array(spec['body_dimensions_m'])*500
    outer=egg(dims)
    boss_clipper=egg(dims-.8)
    shell=outer-egg(dims-2.4)
    door_hardware=[]
    # Ports remain geometric, understated ovals produced by the body curvature.
    for side in (-1,1):
        # Port and hinge y positions follow the current body width.
        side_y=dims[1]-5.5
        cutter=box((112,64,58),(-8,side*side_y,0))
        door=shell & cutter
        # Separate door from body by a printable .6 mm seam on all port edges.
        door=door & box((110.8,66,56.8),(-8,side*side_y,0))
        shell=shell-cutter
        label='left' if side>0 else 'right'
        # Two flexible, replaceable TPU straps attach to internal M3 insert
        # bosses. Bosses touch the curved shell without drawing a wing outline.
        for index,x in enumerate((-35,20)):
            hinge_y=dims[1]-13
            boss=box((10,20,9),(x,side*hinge_y,24)) & boss_clipper
            boss=holes(boss,[(x,side*hinge_y,24)],4.5,28,'y')
            door=door+boss
            fixed=box((10,20,8),(x,side*hinge_y,34)) & boss_clipper
            fixed=holes(fixed,[(x,side*hinge_y,34)],4.5,28,'y')
            shell=shell+fixed
            # Thick screw pads joined by a 1 mm web that bends at the seam.
            strap_y=dims[1]-2.8
            strap=box((14,1,22),(x,side*strap_y,29))
            strap=strap+box((14,3,7),(x,side*strap_y,24))+box((14,3,7),(x,side*strap_y,34))
            strap=holes(strap,[(x,side*strap_y,z) for z in (24,34)],3.4,6,'y')
            door_hardware.append((f'{label}_door_hinge_strap_{index}',strap))
        # Front-edge magnet faces across the .6 mm door seam; this keeps the
        # lower rim independent of the leg/service opening.
        magnety=side*(dims[1]-13)
        fixed=box((12,20,12),(54,magnety,0)) & boss_clipper
        fixed=fixed-cylinder(3.1,2.2,(49.1,magnety,0),'x')
        moving=box((12,20,12),(41.4,magnety,0)) & boss_clipper
        moving=moving-cylinder(3.1,2.2,(46.3,magnety,0),'x')
        door=door+moving;shell=shell+fixed
        emit(label+'_service_door',door,'torso',notes=[
            'Manual door, two replaceable TPU hinges, M3 inserts and one 6x2 magnet pair.',
            'Adhesive retains magnets; close by hand. No actuator.'])
    # Root yaw shaft opening and leg exits are derived from the motor envelope.
    shell=shell-cylinder(50,120,(55,0,76),'z')
    # Static root case is offset behind the shaft; cut its actual local box.
    neckroot=next(j for j in spec['joints'] if j['name']=='neck_yaw')
    rootservo=spec['servos'][neckroot['servo']];w,h,d=np.array(rootservo['body_whd_m'])*1000
    shell=shell-transform(box((w+1,d+1,h+1),(0,0,rootservo['shaft_from_top_m']*1000-h/2)),motor_rotation(neckroot),np.array(neckroot['position_m'])*1000)
    for y in (-46,46):shell=shell-box((128,70,90),(20,y,-85))
    for x in (-72,72):
        for y in (-59,59):
            boss=box((14,24,12),(x,y,-12)) & boss_clipper
            boss=holes(boss,[(x,55*np.sign(y),-12)],4.5,16,'z')
            shell=shell+boss
    # Continuous split; alignment/boss features added after attachment review.
    seam_points=[(0,0,dims[2]-3),(0,0,-dims[2]+3)]+[(0,y,69) for y in (-48,48)]+[(0,y,-38) for y in (-85,85)]
    for point in seam_points:shell=shell+(box((14,10,10),point) & boss_clipper)
    shell=holes(shell,seam_points,3.4,20,'x')
    emit('body_shell_front',shell & box((119.8,220,190),(60.1,0,0)),'torso',notes=['Six internal M3 seam bolts; insert/nut seats accessed through side doors.'])
    emit('body_shell_rear',shell & box((119.8,220,190),(-60.1,0,0)),'torso')
    for name,strap in door_hardware:emit(name,strap,'torso',material='tpu',color='white')
    base=box((160,140,4),(0,0,-20)) & egg(dims-4)
    # Root cradles bolt to vertical bulkheads; their case mounting datum is
    # orthogonal to the floor plate. Both bulkheads are one connected print.
    base=base+box((4,145,40),(-41.25,0,-36))
    base=base+box((4,49,42),(13.75,0,67.5))+box((4,40,70),(13.75,0,15))
    for j in spec['joints']:
        if j['parent']!='torso':continue
        r=motor_rotation(j);servo=spec['servos'][j['servo']]
        w,h,d=np.array(servo['body_whd_m'])*1000
        keep=transform(box((w+1,d+1,h+1),(0,0,servo['shaft_from_top_m']*1000-h/2)),r,np.array(j['position_m'])*1000)
        base=base-keep
        if j['name'].endswith('hip_yaw'):
            # Floor opening for yaw motor cradle and the rotating fork.
            base=base-box((80,68,12),(0,j['position_m'][1]*1000,-20))
        _,mount=static_cradle(j['servo'],servo)
        for q in mount['mount_points_mm']:
            q=np.asarray(q);q[2]-=2
            point=r@q+np.array(j['position_m'])*1000
            axis='x' if abs(r[0,2])>.9 else 'y' if abs(r[1,2])>.9 else 'z'
            base=holes(base,[point],3.4,12,axis)
    for x in (-64,-32,0,32,64):
        for y in (-62,-30,0,30,62):base=base-cylinder(1.7,8,(x,y,-20),'z')
    base=holes(base,[(x,y,-20) for x in (-72,72) for y in (-55,55)],3.4,8,'z')
    emit('torso_base_plate',base,'torso',color='black',notes=['Root motor cradles: M3 bulkhead bolts. Shell: four M3 vertical insert bolts at x=+/-72,y=+/-55. Electronics use adjustable grid.'])

    for j in spec['joints']:
        servo=spec['servos'][j['servo']];r=motor_rotation(j);p=np.array(j['position_m'])*1000
        cradle,mount=static_cradle(j['servo'],servo)
        if j['name'].endswith('hip_roll'):
            bottom=servo['shaft_from_top_m']*1000-servo['body_whd_m'][1]*1000
            cradle=cradle-box((28,5,6),(0,-20,bottom-2))
            # The parent's split yaw rails pass beside this case support.
            # Two shallow side notches preserve the central mounting web.
            cradle=transform(cradle,r,p)
            for side in (-1,1):
                cradle=cradle-box((10,14,12),(-20,side*22,-102))
        if j['name']=='head_roll':
            # Clear the parent fork's narrow rear upright while retaining the
            # other three faces of the case cradle.
            cradle=transform(cradle,r,p)-box((6,4,6),(50,-20,-142.5))
        if j['name']=='beak_drive':
            for y in (-12,12):
                lug=box((18,4,8),(6,y,18))+cylinder(6,4,(0,y,18),'y')
                lug=lug+box((3,4,11),(12,y,15))
                lug=holes(lug,[(0,y,18)],5.2,8,'y')
                cradle=cradle+lug
        emit(j['name']+'_static_cradle',cradle,j['parent'],
             r=None if j['name']=='head_roll' or j['name'].endswith('hip_roll') else r,
             p=None if j['name']=='head_roll' or j['name'].endswith('hip_roll') else p,
             notes=[mount,'Attach through documented static case holes; output horn screws are separate.'])
        if j['name']=='beak_drive':continue
        depth=servo['body_whd_m'][2]*1000
        front=depth/2+servo['front_horn_plane_m']*1000
        rear=depth/2+abs(servo['rear_idler_plane_m']*1000+depth)
        spacer=7 if j['servo'] in ('xm430','xm540') else 4 if j['name']=='head_roll' else 0
        if j['name'].endswith('hip_pitch'):
            end=31.75;width=28.0
        elif j['name'].endswith('knee_pitch'):
            end=46.75;width=28.0
        elif j['name'].endswith('ankle_pitch'):
            end=27.;width=28.0  # Bridge bottom touches foot floor at -29 mm.
        elif j['name']=='neck_pitch':end=60.;width=34.0
        elif j['name']=='neck_mid_pitch':end=44.;width=34.0
        elif j['name']=='head_pitch':end=-60.;width=28.0
        elif j['name']=='head_roll':end=-44.;width=22.0
        elif j['name'].endswith('hip_roll'):end=-60.;width=28.0
        elif j['name']=='neck_yaw':end=28.;width=28.0
        else:end=18.;width=28.0 if j['servo']!='xc330' else 22.0
        # Independent flat plates and a bolted bridge; retain native component
        # geometry instead of merging a multi-material assembly into one STL.
        for face,y in [('front',front+spacer+2),('rear',-rear-spacer-2)]:
            profile=plate_on_y(width,abs(end)+(4 if j['name'].endswith('ankle_pitch') else 6),4,end/2,y,
                               servo['horn_pcd_m']*1000,servo['horn_hole_count'],
                               servo['horn_clearance_m']*1000,9 if j['servo']=='xm430' else 11 if j['servo']=='xm540' else 6)
            profile=holes(profile,[(-width/4,y,end),(width/4,y,end)],3.4,8,'y')
            emit(j['name']+'_output_'+face,profile,j['name'],r=r,
                 notes=['PCD matches vendor horn/idler. Rear idler hardware required.',
                        f'Annular compression spacer {spacer} mm; screw stack must respect vendor insertion limit.'])
        bridgewidth=width
        bridge=box((bridgewidth,front+rear+2*spacer,4 if j['name'].endswith('ankle_pitch') else 8),(0,(front-rear)/2,end))
        for y in (front+spacer+2,-rear-spacer-2):
            bridge=holes(bridge,[(-width/4,y,end),(width/4,y,end)],3.4,12,'y')
        if j['name'] in ('neck_pitch','neck_mid_pitch'):
            bridge=bridge-box((12.3,12.3,12),(0,0,end))
            bridge=holes(bridge,[(0,0,end)],3.4,width+2,'x')
            mx,my=(12.,19.55) if j['name']=='neck_pitch' else (9.,14.)
            bridge=holes(bridge,[(x,y,end) for x in (-mx,mx) for y in (-my,my)],3.4,12,'z')
        if j['name'].endswith(('hip_pitch','knee_pitch')):
            bridge=holes(bridge,[(x,y,end) for x in (-10,10) for y in (-14,14)],3.4,12,'z')
        bridge=transform(bridge,r)
        if j['name'].endswith('hip_yaw'):
            # Split lateral webs avoid the rear horn/idler and both faces of
            # the child roll motor while joining broad bolted end flanges.
            cross=box((46,54,4),(1,0,-24))-cylinder(11.0,6,(0,0,-24),'z')
            bridge=bridge+cross
            for side in (-1,1):bridge=bridge+box((6,8,82.25),(-20,side*22,-65.125))
            bridge=bridge+box((46,54,4),(0,0,-106.25))
            bridge=holes(bridge,[(x,y,-106.25) for x in (-14,14) for y in (-10,10)],3.4,8,'z')
        elif j['name'].endswith('hip_roll'):
            sy=1 if j['name'].startswith('left') else -1
            bridge=bridge+box((60,44,8),(28,-sy*15,-67.5))
            # The rear knee frame swings through this outboard corner.
            bridge=bridge-box((20,26,12),(51,sy*2,-67.5))
            bridge=bridge+box((8,8,114.5),(56,-sy*30,-10.25))+box((8,58,8),(56,-sy*5,47))
            bridge=bridge+box((48.5,42,4),(56,sy*20,41.25))
            bridge=holes(bridge,[(x,y,41.25) for x in (46,66) for y in (sy*20-14,sy*20+14)],3.4,8,'z')
        elif j['name']=='neck_yaw':
            bridge=bridge+box((4,49.1,32.75),(34,0,-16.375))+box((58.75,52,4),(61.375,0,-30.75))
            bridge=holes(bridge,[(x,y,-30.75) for x in (54,74) for y in (-19,19)],3.4,8,'z')
        elif j['name']=='head_pitch':
            bridge=bridge+box((58,31,4),(25,0,-60))+box((4,4,86.5),(50,-20,-101.75))
            bridge=bridge+box((8,12,4),(50,-16,-60))
            bridge=bridge+box((31,40,4),(50,0,-146.5))
            bridge=holes(bridge,[(x,y,-146.5) for x in (41.5,58.5) for y in (-15,15)],3.4,8,'z')
        elif j['name']=='head_roll':
            bridge=holes(bridge,[(x,y,-44) for x in (-7,7) for y in (-10,10)],3.4,12,'z')
        elif j['name'].endswith('ankle_pitch'):
            bridge=holes(bridge,[(x,y,-27) for x in (-7,7) for y in (-21,21)],3.4,8,'z')
        emit(j['name']+'_output_bridge',bridge,j['name'],
             notes=['M3 through bolts/nuts join flat side plates. Integrated child-cradle flange uses matching M3 holes; no glued structural joint.'])
        if spacer:
            for face,y in [('front',front+spacer/2),('rear',-rear-spacer/2)]:
                outer,inner,pcd,n=(8,4,6,4) if j['servo']=='xc330' else (12.75,5.5,11,8) if j['servo']=='xm540' else (9.75,4.5,8,8)
                ring=cylinder(outer,spacer,(0,y,0),'y')-cylinder(inner,spacer+2,(0,y,0),'y')
                ring=holes(ring,[(pcd*math.cos(a),y,pcd*math.sin(a)) for a in np.arange(n)*2*math.pi/n],2.4,spacer+2,'y')
                emit(j['name']+'_horn_spacer_'+face,ring,j['name'],r=r)
        if j['name'].endswith('ankle_pitch'):
            # Inverted motor is accommodated by a cavity; load goes through the
            # 4 mm sole and external fork, not a motor shell pressed into PETG.
            foot=box((120,70,28),(15,0,-18))-box((110,60,26),(15,0,-16))-box((74,48,30),(0,0,-11))
            foot=holes(foot,[(x,y,-30) for x in (-7,7) for y in (-21,21)],3.4,8,'z')
            emit(j['name'].replace('ankle_pitch','foot_shell'),foot,j['name'],color='orange')
            emit(j['name'].replace('ankle_pitch','foot_tread'),box((120,70,2),(15,0,-33)),j['name'],material='tpu',color='black')

    # The short first neck span uses one printed adapter with a wire duct.
    # The longer second span uses commodity square tube with bolted end clamps.
    z0,z1=64.,86.25
    adapter=box((20,20,z1-z0),(0,0,(z0+z1)/2))
    adapter=adapter+box((34,49.1,6),(0,0,z0+3))+box((53.5,52,6),(0,0,z1-3))
    adapter=adapter-box((12.3,12.3,z1-z0+2),(0,0,(z0+z1)/2))
    adapter=holes(adapter,[(x,y,z0+3) for x in (-12,12) for y in (-19.55,19.55)],3.4,8,'z')
    adapter=holes(adapter,[(x,y,z1-3) for x in (-10,10) for y in (-19,19)],3.4,8,'z')
    emit('neck_pitch_bridge_adapter',adapter,'neck_pitch',notes=['M3 through bolts at lower fork and upper motor cradle; centre duct for the bus harness.'])
    mid_length=spec['neck_link_lengths_m'][1]*1000
    upper_bottom=mid_length-63.25; upper_pins=(mid_length-59.25,mid_length-51.25)
    tube=box((12,12,mid_length-86),(0,0,(44+mid_length-42)/2))-box((9,9,mid_length-84),(0,0,(44+mid_length-42)/2))
    tube=holes(tube,[(0,0,z) for z in (60,68,*upper_pins)],3.4,16,'x')
    emit('neck_mid_pitch_tube',tube,'neck_mid_pitch',material='aluminium',notes=[f'12x12x1.5 square tube, cut {mid_length-86:g} mm; 3.4 mm pin holes at 16/24/{upper_pins[0]-44:g}/{upper_pins[1]-44:g} mm from lower cut.'])
    for name,bottom,width,depth,mount_x,mount_y in [
            ('neck_mid_lower_clamp',48.,28.,38.,9.,14.),
            ('neck_mid_upper_clamp',upper_bottom,48.5,42.,10.,14.)]:
        isupper='upper' in name;face=bottom+24 if isupper else bottom
        clamp=box((20,20,24),(0,0,bottom+12))+box((width,depth,6),(0,0,face-3 if isupper else face+3))
        clamp=clamp-box((12.3,12.3,28),(0,0,bottom+12))
        clamp=holes(clamp,[(x,y,face) for x in (-mount_x,mount_x) for y in (-mount_y,mount_y)],3.4,14,'z')
        clamp=holes(clamp,[(0,0,z) for z in (upper_pins if isupper else (60,68))],3.4,24,'x')
        emit(name,clamp,'neck_mid_pitch',notes=['M3 cross pins through tube and clamp; nuts on the outside.'])

    # Head cover deliberately omits feathers/eyes. Actual camera aperture and
    # mouth recess follow the reserved component space, not concept artwork.
    helmet=Pos(12,0,35)*Sphere(1).scale((52,36,60))-Pos(12,0,35)*Sphere(1).scale((49.8,33.8,57.8))
    camera=spec['camera'];cr=Rotation.from_euler('y',camera['board_pitch_down_rad']).as_matrix();cp=np.array(camera['board_center_head_m'])*1000
    hood=box((24,24,44),(8,0,0))-box((22,20,40),(8,0,0))
    hood=hood-cylinder(9.3,30,(20,0,0),'x')
    hood=transform(hood,cr,cp)
    helmet=helmet+hood
    helmet=helmet-box((82,50,65),(34,0,15))
    helmet=helmet-cylinder(38,70,(-15,0,0),'x')
    helmet=helmet-box((160,120,80),(0,0,-40))
    for y in (-16.5,16.5):helmet=helmet-box((70,7.5,65),(56,y,55))
    helmet=helmet-box((24,32,46),(44,0,36))
    # The floating jaw must clear the cover through its full parallelogram arc.
    helmet=helmet-box((37,31,82),(61,0,65))
    # Fixed pivot lugs get clearance at the lower rear camera hood corners.
    for y in (-12,12):helmet=helmet-cylinder(6.3,4.6,(44,y,62),'y')
    head_clip_outer=Pos(12,0,35)*Sphere(1).scale((52,36,60))
    for x,mount_y in ((30,24),(50,16)):
        for sy in (-1,1):
            boss=box((12,10,10),(x,sy*(mount_y+7),24)) & head_clip_outer
            boss=boss-cylinder(1.6,4,(x,sy*(mount_y+4),24),'y')
            helmet=helmet+boss
    # Three PCB edge clamps: two top corners and one lower centre. A narrow
    # portrait board clears the paired crank planes; no unverified PCB holes.
    for y,z in ((10.5,17),(-10.5,17),(0,21)):
        pad=box((5,5,7),(-2.5,y,z))
        pad=holes(pad,[(-2.5,y,z)],2.4,8,'x')
        helmet=helmet+transform(pad,cr,cp)
    # Rear pad of the lower centre reaches the connected hood bottom rim.
    helmet=helmet+transform(box((5,18,3),(-2.5,0,21)),cr,cp)
    for y,z in ((10.5,17),(-10.5,17),(0,21)):
        helmet=helmet-transform(box((2.6,5.6,7.6),(2,y,z)),cr,cp)
    # Static head-pitch fork crosses the rear skin during the side-head roll.
    # These service reliefs follow its home, half-roll and ground-grasp arcs.
    helmet=helmet-box((17,36,12),(-34,0,55))
    helmet=helmet-box((30,17,18),(-9,31,47))
    helmet=helmet-box((21,76,10),(1,0,21))
    # Fixed beak motor cradle sits partly inside the otherwise solid skin.
    helmet=helmet-box((16,30,12),(34,0,62))
    # Open the real lens optical path through the front shell. The existing
    # recessed hood retains the camera; the outer skin must not occlude it.
    helmet=helmet-transform(cylinder(10.5,55,(38,0,0),'x'),cr,cp)
    # The bore can sever tiny remnants of the temporary PCB-pad stock. They
    # are not connected printable material and do not belong in the cover.
    helmet=max(helmet.solids(),key=lambda solid:solid.volume)
    emit('head_cover',helmet,'head_roll',notes=['Lens aperture follows the pitched camera axis; verify undistorted FOV and hand-eye calibration with real hardware.'])

    # Beak R2 closed-pose geometry belongs to fixed head, drive/follower and
    # floating lower jaw. A full parallelogram is represented in the MJCF.
    a=np.array(spec['joints'][-1]['position_m'])*1000
    l=spec['beak']['crank_length_m']*1000;h=spec['beak']['anchor_spacing_m']*1000
    closed=spec['beak']['closed_rad'];padz=spec['beak']['pad_mount_z_relative_jaw_m']*1000
    # Head carrier: bottom plate bolts beneath roll fork. Outside struts clear
    # both case envelopes. Top tray holds the normal-orientation beak cradle.
    carrier=box((44,37,4),(4,0,-50))
    for y in (-17,17):carrier=carrier+box((4,4,63.5),(26,y,-16.25))
    carrier=carrier+box((40,38,4),(44,0,13.5))
    carrier=holes(carrier,[(x,y,-50) for x in (-7,7) for y in (-10,10)],3.4,8,'z')
    carrier=holes(carrier,[(x,y,13.5) for x in (29,59) for y in (-8.5,8.5)],3.4,8,'z')
    # Front uprights stay beyond the entire fixed roll case in the shaft
    # direction, preserving clearance through +/-90 degree side-head grasp.
    for y in (-24,24):
        carrier=carrier+box((60,10,4),(54,np.sign(y)*20,13.5))+box((4,4,32),(82,y,29.5))
    carrier=carrier+box((4,52,4),(82,0,44))
    carrier=holes(carrier,[(82,y,44) for y in (-10,10)],3.4,8,'z')
    for x,mount_y in ((30,24),(50,16)):
        for sy in (-1,1):
            if mount_y==24:
                carrier=carrier+box((12,4,12.5),(x,sy*24,21.75))
            else:
                carrier=carrier+box((12,2.5,4.5),(x,sy*16.75,17.75))+box((12,4,8),(x,sy*16,24))
            carrier=holes(carrier,[(x,sy*mount_y,24)],2.4,8,'y')
    emit('head_structural_carrier',carrier,'head_roll',color='white',notes=['Roll fork bottom M3; beak cradle M3 tray; upper bill two M3; cover four internal M2 bolts; portrait camera retained by cover hood edge clamps.'])
    for i,(y,z) in enumerate(((10.5,17),(-10.5,17),(0,21))):
        clip=box((2,5,7),(2,y,z));clip=holes(clip,[(2,y,z)],2.4,6,'x')
        emit(f'camera_edge_clip_{i}',clip,'head_roll',color='black',r=cr,p=cp,notes=['M2 through bolt/nut; retain PCB edges with 0.5 mm TPU shims; no guessed mounting hole.'])
    top=l*math.sin(closed)+padz+1
    upper=box((30,28,7),a+np.array([51,0,top+5.5]))
    upper=upper-cylinder(8,40,a+np.array([15,0,top+5]),'y')
    upper=upper+box((12,28,2),(87,0,41))
    upper=holes(upper,[(82,y,38) for y in (-10,10)],3.4,12,'z')
    emit('upper_beak',upper,'head_roll',color='orange',notes=['Prototype bill; rounded/tapered silhouette refinement deferred.'])
    rhead,phead=frames['head_roll']
    frames['upper_crank']=(rhead@Rotation.from_rotvec([0,-closed,0]).as_matrix(),phead+rhead@(a+np.array([0,0,h]))/1000)
    for name,body in [('lower_drive_crank','beak_drive'),('upper_follower_crank','upper_crank')]:
        for side in (-1,1):
            y=side*16.5
            crank=box((l,4,6),(l/2,y,0))+cylinder(8,4,(0,y,0),'y')+cylinder(5,4,(l,y,0),'y')
            crank=holes(crank,[(l,y,0)],3.2,8,'y')
            if name=='lower_drive_crank':
                crank=holes(crank,[(6*math.cos(a),y,6*math.sin(a)) for a in np.arange(4)*math.pi/2],2.4,8,'y')
                crank=crank-cylinder(4,8,(0,y,0),'y')
            else:crank=holes(crank,[(0,y,0)],3.2,8,'y')
            emit(name+('_front' if side<0 else '_rear'),crank,body,color='orange',
                 notes=['Lower front: four M2 to built-in horn. Lower rear: FPX330 idler and four M2.',
                        'Upper A-C pivot: 3 mm shoulder shaft/bushings. Jaw B-C pivots: 3 mm shoulder shafts.'])
    jaw=box((54,28,4),(27,0,padz-8))
    jaw=jaw+box((8,28,h-padz+15.5),(0,0,(h+padz-6.5)/2))
    # Trim the back face against the fixed motor tray and the lower heel at
    # closed pose; leave the pin bosses and most of the 8 mm web intact.
    jaw=jaw-box((1.3,30,70),(-3.85,0,-8))
    jaw=jaw-box((7,30,2),(-.5,0,-40.5))
    jaw=holes(jaw,[(0,0,0),(0,0,h)],5.2,34,'y')
    jaw=holes(jaw,[(x,y,padz-8) for x in (25,40) for y in (-12,12)],2.4,8,'z')
    # Keep this part in jaw-local coordinates; assembly transform below uses
    # its actual closed world frame, not the head frame from active joints.
    jawbody='lower_jaw'
    frames[jawbody]=(rhead,phead+rhead@(a+np.array([l*math.cos(closed),0,l*math.sin(closed)]))/1000)
    emit('lower_jaw',jaw,jawbody,color='orange')
    emit('upper_grip_pad',box((30,22,2),a+np.array([51,0,top+1])),'head_roll',material='tpu',color='black')
    frames['lower_pad']=(rhead,frames[jawbody][1]+rhead@np.array([.025,0,padz/1000]))
    # A printable TPU cartridge gives passive translation/tilt through folded
    # flexures; physics represents it with lumped compliance, not exact FEM.
    cartridge=box((35,28,1.2),(32.5,0,padz-5.4))
    for x,direction in ((23.,-1),(42.,1)):
        cartridge=cartridge+box((4,18,1.2),(x,0,padz-4.2))
        cartridge=cartridge+box((1.2,18,3.4),(x+direction*1.4,0,padz-3.1))
        cartridge=cartridge+box((4,18,1.2),(x,0,padz-2))
    cartridge=cartridge+box((35,22,1),(32.5,0,padz-1.5))+box((35,22,2),(32.5,0,padz))
    cartridge=holes(cartridge,[(x,y,padz-5.4) for x in (25,40) for y in (-12,12)],2.4,2,'z')
    emit('lower_compliant_grip_cartridge',cartridge,jawbody,material='tpu',color='black',notes=[
        'Four flush M2 flat-head screws retain the base. 1.2 mm folded flexures and replaceable TPU grip.',
        '1.5 mm/4 degree lumped simulator compliance is a calibration target, not a measured TPU property.'])

    assembly=Compound(shapes);export_step(assembly,out/'goose_rc2_assembly.step')
    result={'schema_version':1,'robot_id':spec['robot_id'],'revision':spec['engineering_revision'],
            'cad_units':'mm','physics_units':'SI','generator':'scripts/cad/build_goose_cad.py',
            'spec_sha256':hashlib.sha256((robot/'configs/robot_spec.json').read_bytes()).hexdigest(),
            'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'parts':parts,'printed_mass_kg':sum(p['mass_kg'] for p in parts if p['material']!='aluminium'),
            'aluminium_mass_kg':sum(p['mass_kg'] for p in parts if p['material']=='aluminium'),
            'all_solids_valid':all(p['cad_valid'] for p in parts),'full_manufacturing_acceptance':False,
            'open_checks':['child cradle attachment to fork','shell fasteners and manual door hinge/latch',
                           'beak handed crank pair and compliant pad carrier','full swept assembly clearance',
                           'wire/service envelopes','printed anisotropic strength and thermal testing'],
            'source_vendor_geometry':'dimensions only; no vendor CAD redistributed'}
    (out/'cad_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (source/'parameters.json').write_text(json.dumps({'spec_sha256':result['spec_sha256'],
        'length_unit':'mm','petg_wall_mm':2.4,'structural_plate_mm':4,'fit_gap_mm':.3,
        'normal_bore_clearance_mm':.4,'door_seam_mm':.6},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='parts'},indent=2))


if __name__=='__main__':main()
