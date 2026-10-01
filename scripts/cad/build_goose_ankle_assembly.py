"""Dimensioned ankle cross-axis carrier and two-sided foot saddle.

The case and output interfaces use the V3 manufacturer drawing. Native solids
are engineering candidates: this does not assign an unknown OEM bearing rating.
All coordinates are neutral world mm, without the common 3.7 mm contact lift.
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import trimesh
from build123d import import_step, export_step, export_brep, export_stl

ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_stage_two import candidate
from build_goose_cad import box, cylinder, holes, transform
from build_goose_pitch_forks import bar, radial
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties
from sai_agent.goose.morphology import apply_leg_layout


def main():
    layout=R/'configs/body_bay_layout_candidate.json'
    facts_file=R/'hardware/stage_three_actuator_mounts.json'
    facts=json.loads(facts_file.read_text())['catalog']
    s=candidate(); old={k:v.copy() for k,v in s.pivots.items()}
    apply_leg_layout(s,json.loads(layout.read_text()))
    source=R/'cad/source/body_bay_ankle_assembly'; out=R/'cad/exports/body_bay_ankle_assembly'
    source.mkdir(parents=True,exist_ok=True); out.mkdir(parents=True,exist_ok=True)
    records=[]; scene=[]; assemblies=[]; stacks=[]

    def emit(name, shape, owner, material='aluminium', notes=(), bearing=False):
        shape=shape.solids()[0] if len(shape.solids())==1 else shape
        if not shape.is_valid or len(shape.solids())!=1: raise ValueError((name,'native validity'))
        volume,com,I,_=native_properties(shape); rho=7850 if material=='steel' else 2700
        mass=volume*rho*1e-9
        if bearing: rho=.0053/volume*1e9; mass=.0053
        paths={'brep':source/(name+'.brep'),'step':out/(name+'.step'),'stl':out/(name+'.stl'),'npz':source/(name+'_quad.npz')}
        export_brep(shape,paths['brep']);export_step(shape,paths['step']);export_stl(shape,paths['stl'],tolerance=.08,angular_tolerance=.15)
        rt=import_step(paths['step']); rv,*_=native_properties(rt)
        mesh=trimesh.load(paths['stl'],force='mesh',process=True)
        tessellation=dict(tolerance_mm=.08,angular_tolerance_rad=.15)
        for tol,angle in [(.025,.08),(.01,.05)]:
            if mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0:break
            export_stl(shape,paths['stl'],tolerance=tol,angular_tolerance=angle)
            mesh=trimesh.load(paths['stl'],force='mesh',process=True)
            tessellation=dict(tolerance_mm=tol,angular_tolerance_rad=angle)
        if not rt.is_valid or len(rt.solids())!=1 or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0: raise ValueError((name,'exchange'))
        if abs(rv/volume-1)>1e-5 or abs(mesh.volume/volume-1)>.005:raise ValueError((name,'volume'))
        vertices,faces=quad_sampling(mesh);np.savez_compressed(paths['npz'],vertices=vertices,faces=faces)
        files={k:dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()}
        p=dict(name=name,body=owner,material=material,unit='mm',density_kg_m3=rho,volume_mm3=volume,mass_kg=mass,
            center_of_mass_world_m=(com/1000).tolist(),inertia_at_com_world_kg_m2=(I*rho*1e-15).tolist(),
            files=files,notes=list(notes),native_valid=True,stl_watertight=True,quad_faces=len(faces),tessellation=tessellation,manufacturing_released=False)
        if bearing:p.update(role='purchased_bearing_installation_envelope',mass_basis='SKF61800 catalog; annular envelope inertia')
        records.append(p);scene.append(dict(name=name,body=owner,group='native_ankle_assembly',material='titanium' if material=='steel' else 'ivory',
            role='dimensioned_ankle_candidate',geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))

    def screw(assembly,role,owner,anchor,thread,L,count,washer,stack,maximum,minimum=3.,notes=''):
        engagement=L-washer-stack
        if not minimum<=engagement<=maximum:raise ValueError((role,engagement,minimum,maximum))
        d=2.5 if thread=='M2.5' else 3.; hd=5 if d==2.5 else 6.;hh=3 if d==2.5 else 4.
        v=np.pi/4*(d*d*L+hd*hd*hh+((6 if d==2.5 else 7)**2-(d+.2)**2)*washer)
        stacks.append(dict(assembly=assembly,role=role,body=owner,anchor_part=anchor,thread=thread,length_mm=L,count=count,
            washer_stack_mm=washer,clamped_stack_mm=stack,engagement_mm=engagement,max_engagement_mm=maximum,
            mass_upper_estimate_kg=v*7850e-9*count,notes=notes,released=False))

    for side in ['right','left']:
        sign=-1 if side=='right' else 1
        P=s.pivots[side+'_ankle_pitch']*1000; Q=s.pivots[side+'_ankle_roll']*1000
        pitch=side+'_ankle_pitch'; roll=side+'_ankle_roll'; parent=s.parents[pitch]
        # Normalize pitch output to +Y before transforming to the actual side.
        rotation=np.eye(3) if sign>0 else np.diag([1.,-1.,-1.])
        front_y=46.; rear_y=-52.; adapter_t=17.; op=26.25
        # Two face discs and six turned posts give the same 17mm stack. Every
        # output screw clamps its own post; top-disc fork taps do not cross an
        # empty cavity. The discs and posts are separate real BOM components.
        angles=[30,90,150,210,270,330]
        for suffix,center_y,thickness in [('base_disc',op+1.5,3),('output_adapter',op+15,4)]:
            adapter=cylinder(20,thickness,[0,center_y,0],'y')-cylinder(4,10,[0,center_y,0],'y')
            if suffix=='base_disc':adapter+=cylinder(8.98,1.3,[0,op-.65,0],'y')-cylinder(4,5,[0,op-.65,0],'y')
            adapter=holes(adapter,radial(27,angles,center_y),3.2,10,'y')
            adapter=holes(adapter,radial(24,[60,180,300],center_y),4.05,10,'y')
            if suffix=='output_adapter':adapter=holes(adapter,radial(32,[0,120,240],center_y),2.5,10,'y')
            emit(side+'_ankle_pitch_'+suffix,transform(adapter,rotation,P),pitch,notes=['3mm base +10mm six turned posts +4mm threaded face =17mm stack.','Top face three M3 taps PCD32; motor screws clamp six independent OD7 ID3.2 posts.','Base18mm pilot and three guide-pin sockets preserve the actual output datum.'])
        for k,p in enumerate(radial(27,angles,op+8)):
            post=cylinder(3.5,10,p,'y')-cylinder(1.6,12,p,'y')
            emit(side+f'_ankle_pitch_output_post_{k}',transform(post,rotation,P),pitch,notes=['Turned6061 OD7 ID3.2 length10mm;parallel ends0.03mm;no paint on contact faces.'])
        name=side+'_ankle_pitch_output_adapter'
        screw(side,'pitch_output',pitch,name,'M3',22,6,1,17,4.5)
        # World profile follows the two actual pivots. The perpendicular front
        # ring has ID42; its opening remains clear of the rotating R20 adapter.
        arm_y=P[1]+sign*front_y; front_x=Q[0]+21.6
        A=P.copy();A[1]=0
        end=np.array([front_x+2,0,Q[2]+10]); B=np.array([P[0]+31,0,P[2]+34])
        arm=cylinder(20,5.5,[P[0],arm_y,P[2]],'y')+bar(A,end,16,5.5,arm_y)+bar(A,B,16,5.5,arm_y)
        arm+=box([14,5.5,14],[B[0],arm_y,B[2]])
        arm=holes(arm,[P+rotation@np.array([16*np.cos(t),front_y,16*np.sin(t)]) for t in np.deg2rad([0,120,240])],3.2,12,'y')
        arm=holes(arm,[P+rotation@np.array([13.5*np.cos(t),front_y,13.5*np.sin(t)]) for t in np.deg2rad([30,90,150,210,270,330])],5.8,12,'y')
        arm-=cylinder(7,12,[P[0],arm_y,P[2]],'y')
        bridge_points=[[B[0]+dx,arm_y,B[2]] for dx in [-4,4]]
        arm=holes(arm,bridge_points,3.2,12,'y')
        ring=cylinder(27.5,4,[front_x+2,Q[1],Q[2]],'x')
        ring+=box([4,abs(arm_y-Q[1]),14],[front_x+2,(arm_y+Q[1])/2,Q[2]+10])
        ring-=cylinder(21,12,[front_x+2,Q[1],Q[2]],'x')
        motor_pts=[[front_x+2,Q[1]+23.75*np.cos(t),Q[2]+23.75*np.sin(t)] for t in np.deg2rad([30,90,150,210,270,330])]
        ring=holes(ring,motor_pts,2.7,12,'x');arm+=ring
        name=side+'_ankle_cross_axis_carrier';emit(name,arm,pitch,notes=['One CNC6061-T6 cross-axis part: 5.5mm fork and 4mm stator front ring, no adhesive joint.','AK45-10 V3 case-front six M2.5 at PCD47.5. ID42 separates stationary ring from rotating output.','Ring outer radius27.5 leaves1mm nominal radial separation to the load plate plane at zero.','Machine transverse front holes after the plate profiles; no closed additive cavity.'])
        screw(side,'pitch_fork',pitch,name,'M3',10,3,1,5.5,17,3.5)
        screw(side,'roll_case_front',pitch,name,'M2.5',8,6,1,4,5)
        # Rear pitch support is displaced past the shin's rear plate.
        rear_world=P[1]-sign*52
        rear=cylinder(16,5.5,[P[0],rear_world,P[2]],'y')+bar(A,B,16,5.5,rear_world)
        rear+=box([14,5.5,14],[B[0],rear_world,B[2]])
        rear-=cylinder(9.5045,5,[P[0],rear_world-sign*.25,P[2]],'y')
        rear-=cylinder(6.5,12,[P[0],rear_world,P[2]],'y')
        retain=radial(25,[0,120,240],rear_y)
        rear=holes(rear,[P+rotation@v for v in retain],2.05,12,'y')
        rear=holes(rear,[[B[0]+dx,rear_world,B[2]] for dx in [-4,4]],3.2,12,'y')
        name=side+'_ankle_pitch_rear_fork';emit(name,rear,pitch,notes=['19H7 seat for SKF61800; 0.5mm shoulder, ID13 clears shaft shoulder.','Rear fork center -52mm normalized; 1mm beyond the shin rear plate.'])
        bridge_lo=min(arm_y,rear_world)+2.75;bridge_hi=max(arm_y,rear_world)-2.75; span=bridge_hi-bridge_lo
        bridge=box([14,span,14],[B[0],(bridge_lo+bridge_hi)/2,B[2]])
        bridge-=box([10,span-16,16],[B[0],(bridge_lo+bridge_hi)/2,B[2]])
        bridge=holes(bridge,[[B[0]+dx,y,B[2]] for dx in [-4,4] for y in [bridge_lo+4,bridge_hi-4]],2.5,8,'y')
        name=side+'_ankle_pitch_bridge';emit(name,bridge,pitch,notes=['CNC open-window bridge, two2mm rails,8mm tapped ends; four M3 blind8mm taps.'])
        screw(side,'pitch_bridge',pitch,name,'M3',12,4,.5,5.5,8)
        # This spider REPLACES the four distal middle spacers of the shin. A
        # single case bolt clamps the previous fork, spacer and this spider.
        rear_case=-28.25; spider_y=rear_case-2
        spider=cylinder(7,2,[0,spider_y,0],'y')
        rh=radial(47,[45,135,225,315],spider_y)
        for p in rh:spider+=cylinder(4,2,p,'y')
        for t in np.deg2rad([45,135,225,315]):spider+=bar(np.zeros(3),np.array([23.5*np.cos(t),0,23.5*np.sin(t)]),6,2,spider_y)
        spider=holes(spider,rh,3.2,6,'y')
        shaft_end=rear_y-3.15; shoulder=rear_y+2.25
        spider+=cylinder(6.25,spider_y-1-shoulder,[0,(spider_y-1+shoulder)/2,0],'y')
        spider+=cylinder(4.995,shoulder-shaft_end,[0,(shoulder+shaft_end)/2,0],'y')
        spider-=cylinder(1.25,8,[0,shaft_end+4,0],'y')
        name=side+'_ankle_pitch_stationary_spider';emit(name,transform(spider,rotation,P),parent,'steel',notes=['C45 steel spider and10g6 shaft; rear case4M3PCD47.','Replaces the four existing shin distal middle spacers; preserve one shared case screw stack.','Motor rear plug and PCB exposure require actual OEM surface inspection.'])
        bearing=cylinder(9.5,5,[0,rear_y-.25,0],'y')-cylinder(5,7,[0,rear_y-.25,0],'y')
        emit(side+'_ankle_pitch_bearing',transform(bearing,rotation,P),pitch,'steel',bearing=True)
        cover=cylinder(14,1,[0,rear_y-3.25,0],'y')-cylinder(8.5,3,[0,rear_y-3.25,0],'y')
        cover=holes(cover,radial(25,[0,120,240],rear_y-3.25),2.7,4,'y')
        name=side+'_ankle_pitch_bearing_cover';emit(name,transform(cover,rotation,P),pitch)
        screw(side,'pitch_outer_race_retainer',pitch,name,'M2.5',5,3,.5,1,5.5)
        washer=cylinder(6.25,.5,[0,shaft_end-.25,0],'y')-cylinder(1.6,3,[0,shaft_end-.25,0],'y')
        name=side+'_ankle_pitch_shaft_washer';emit(name,transform(washer,rotation,P),parent,'steel')
        screw(side,'pitch_shaft_retainer',parent,name,'M3',6,1,.5,.5,8)
        # Actual ankle-roll output adapter and front foot saddle.
        out_x=Q[0]+22.6
        adapter=cylinder(20,4,[out_x+2,Q[1],Q[2]],'x')-cylinder(4,10,[out_x+2,Q[1],Q[2]],'x')
        opoints=[[out_x+2,Q[1]+13.5*np.cos(t),Q[2]+13.5*np.sin(t)] for t in np.deg2rad([30,150,270])]
        lpoints=[[out_x+2,Q[1]+16*np.cos(t),Q[2]+16*np.sin(t)] for t in np.deg2rad([0,120,240])]
        adapter=holes(adapter,opoints,2.7,12,'x');adapter=holes(adapter,lpoints,2.5,12,'x')
        name=side+'_ankle_roll_output_adapter';emit(name,adapter,roll,notes=['Three OEM M2.5 output bores, PCD27; separate three M3 tapped fork holes at PCD32.','No unassigned pilot protrusion is added to the AK45-10 output.'])
        screw(side,'roll_output',roll,name,'M2.5',10,3,1,4,6)
        foot=import_step(R/f'cad/exports/compliant_foot/{side}_tapped_load_plate.step')
        foot=transform(foot,np.eye(3),(s.pivots[roll]-old[roll])*1000)
        plate_holes=[]
        for label,xc in [('front',out_x+6.75),('rear',Q[0]-29.0)]:
            shape=cylinder(20 if label=='front' else 16,5.5,[xc,Q[1],Q[2]],'x')
            shape+=box([5.5,48,Q[2]-11.5],[xc,Q[1],(Q[2]+11.5)/2])
            centers_x=[Q[0]+29,Q[0]+49] if label=='front' else [Q[0]-46,Q[0]-26]
            for dy in [-18,18]:shape+=box([30,10,4],[(centers_x[0]+centers_x[1])/2,Q[1]+dy,9.5])
            fholes=[[x,Q[1]+dy,9.5] for x in centers_x for dy in [-18,18]]
            plate_holes+=fholes;shape=holes(shape,fholes,3.2,14,'z')
            if label=='front':
                shape=holes(shape,[[xc,p[1],p[2]] for p in lpoints],3.2,12,'x')
                shape=holes(shape,[[xc,p[1],p[2]] for p in opoints],5.3,12,'x')
                shape-=cylinder(7,12,[xc,Q[1],Q[2]],'x')
            else:
                shape-=cylinder(9.5045,5,[xc-.25,Q[1],Q[2]],'x')
                shape-=cylinder(6.5,12,[xc,Q[1],Q[2]],'x')
                rp=[[xc,Q[1]+12.5*np.cos(t),Q[2]+12.5*np.sin(t)] for t in np.deg2rad([0,120,240])]
                shape=holes(shape,rp,2.05,12,'x')
            name=side+'_foot_'+label+'_saddle';emit(name,shape,roll,notes=['CNC6061-T6 foot saddle,5.5mm axial plate and4mm open side feet.','Load-plate screws M3x8+0.5mm washer give3.5mm engagement in4mm plate.','Rear seat SKF61800 19H7; no solid block across the motor floor.'])
            screw(side,label+'_foot_to_plate',roll,name,'M3',8,4,.5,4,4,3.5)
            if label=='front':screw(side,'roll_front_saddle',roll,name,'M3',10,3,1,5.5,4,3.5)
        foot=holes(foot,plate_holes,2.5,14,'z')
        emit(side+'_ankle_tapped_load_plate',foot,roll,notes=['Replaces the earlier four-hole load plate;8 additional M3 through taps match both foot saddles.','The original four sole mounting taps are preserved.'])
        # Roll stationary rear support is attached to the pitch-owned stator.
        rear_case_x=Q[0]-22.6; sx=rear_case_x-1
        spider=cylinder(7,2,[sx,Q[1],Q[2]],'x')
        rpts=[[sx,Q[1]+23.5*np.cos(t),Q[2]+23.5*np.sin(t)] for t in np.deg2rad([0,90,180,270])]
        for pt in rpts:
            spider+=cylinder(4,2,pt,'x')
            dy=np.array(pt)-[sx,Q[1],Q[2]];d=dy/np.linalg.norm(dy)
            rot=np.column_stack(([1.,0,0],d,np.cross([1.,0,0],d)))
            spider+=transform(box([2,np.linalg.norm(dy),6]),rot,(np.array(pt)+[sx,Q[1],Q[2]])/2)
        spider=holes(spider,rpts,2.7,6,'x')
        rx=Q[0]-29.0; shaft_end=rx-2.9; shoulder=rx+2.5
        spider+=cylinder(6.25,sx-1-shoulder,[(sx-1+shoulder)/2,Q[1],Q[2]],'x')
        spider+=cylinder(4.995,shoulder-shaft_end,[(shoulder+shaft_end)/2,Q[1],Q[2]],'x')
        spider-=cylinder(1.25,8,[shaft_end+4,Q[1],Q[2]],'x')
        name=side+'_ankle_roll_stationary_spider';emit(name,spider,pitch,'steel',notes=['C45 steel10g6 shaft,case rear4M2.5PCD47,2mm spider.','Independent rear radial support; rotating foot load plate does not attach to stator.'])
        screw(side,'roll_rear_case',pitch,name,'M2.5',6,4,.5,2,5)
        bearing=cylinder(9.5,5,[rx-.25,Q[1],Q[2]],'x')-cylinder(5,7,[rx-.25,Q[1],Q[2]],'x')
        emit(side+'_ankle_roll_bearing',bearing,roll,'steel',bearing=True)
        cover=cylinder(14,1,[rx-3.25,Q[1],Q[2]],'x')-cylinder(8.5,3,[rx-3.25,Q[1],Q[2]],'x')
        pts=[[rx-3.25,Q[1]+12.5*np.cos(t),Q[2]+12.5*np.sin(t)] for t in np.deg2rad([0,120,240])]
        cover=holes(cover,pts,2.7,5,'x');name=side+'_ankle_roll_bearing_cover';emit(name,cover,roll)
        screw(side,'roll_outer_race_retainer',roll,name,'M2.5',5,3,.5,1,5.5)
        washer=cylinder(6.25,.5,[shaft_end-.25,Q[1],Q[2]],'x')-cylinder(1.6,3,[shaft_end-.25,Q[1],Q[2]],'x')
        name=side+'_ankle_roll_shaft_washer';emit(name,washer,pitch,'steel')
        screw(side,'roll_shaft_retainer',pitch,name,'M3',6,1,.5,.5,8)
        assemblies.append(dict(side=side,pitch=pitch,roll=roll,pitch_pivot_mm=P.tolist(),roll_pivot_mm=Q.tolist(),
            pitch_front_plate_offset_mm=46,pitch_rear_plate_offset_mm=-52,bearing='SKF61800',
            load_path='shin stator -> pitch output adapter and rear radial idler -> cross-axis carrier -> roll stator; roll output adapter and rear radial idler -> two saddles ->8M3 plate taps -> load plate -> TPU sole',
            oem_output_bearing_rating_known=False,hardware_freeze=False))
        print(side,'ankle parts done',flush=True)
    replaced=[side+'_tapped_load_plate' for side in ['right','left']]+[side+f'_shin_distal_rear_spacer_middle_{k}' for side in ['right','left'] for k in range(4)]
    payload=dict(schema='goose_native_ankle_candidate_v1',parts=records,assemblies=assemblies,replaces_existing_native_parts=replaced,
        native_candidate_mass_kg=sum(p['mass_kg'] for p in records),fasteners=stacks,manufacturing_pass=False,full_assembly_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [layout,facts_file,Path(__file__)]})
    (out/'manifest.json').write_text(json.dumps(payload,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='NATIVE_ANKLE_CANDIDATE',parts=scene),separators=(',',':'))+'\n')
    print('native ankle kg',payload['native_candidate_mass_kg'],'fasteners kg',sum(p['mass_upper_estimate_kg'] for p in stacks),flush=True)

if __name__=='__main__':main()
