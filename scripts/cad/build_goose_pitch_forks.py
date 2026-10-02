"""Dimensioned paired pitch forks and independent rear support, mm native CAD.

This increment closes explicit attachment geometry for six parallel-axis links.
It does not release the cross-axis joints, torso, head, wires or whole robot.
CAD holes marked TAP are tap-drill geometry; threads are manufacturing notes.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from build123d import export_brep, export_step, export_stl, import_step

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/models'), str(ROOT/'scripts/cad')]
from build_goose_stage_two import candidate
from build_goose_cad import cylinder, box, holes, transform
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties
from sai_agent.goose.morphology import apply_leg_layout


def radial(pcd, angles, y, offset=np.zeros(3)):
    return [offset + [pcd/2*np.cos(a), y, pcd/2*np.sin(a)] for a in np.deg2rad(angles)]


def bar(a, b, width, thickness, y):
    a, b = np.array(a), np.array(b)
    delta = b-a
    direction = delta/np.linalg.norm(delta)
    rot = np.column_stack((direction, [0,1,0], np.cross(direction,[0,1,0])))
    center = (a+b)/2; center[1] = y
    return transform(box((np.linalg.norm(delta),thickness,width)), rot, center)


def fork_profile(a, b, y, rear=False):
    shape = bar(a,b,24,5.5,y)
    direction=(b-a)/np.linalg.norm(b-a);middle=(a+b)/2
    shape += bar(middle-direction*9,middle+direction*9,18,5.5,y)
    shape += cylinder(20 if not rear else 16,5.5,a+[0,y,0],'y')
    shape += cylinder(27.5,5.5,b+[0,y,0],'y')
    return shape


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--layout', type=Path); args = parser.parse_args()
    s = candidate()
    if args.layout: apply_leg_layout(s, json.loads(args.layout.read_text()))
    facts_file = ROBOT/'hardware/stage_three_actuator_mounts.json'
    facts = json.loads(facts_file.read_text())['catalog']
    folder = 'body_bay_pitch_forks' if args.layout else 'pitch_fork_assembly'
    source = ROBOT/'cad/source'/folder
    exports = ROBOT/'cad/exports'/folder
    source.mkdir(parents=True,exist_ok=True); exports.mkdir(parents=True,exist_ok=True)
    records=[]; scene=[]; assemblies=[]

    def emit(name, shape, owner, rotation, origin, material='aluminium', notes=None, features=None):
        if not shape.is_valid or len(shape.solids())!=1: raise ValueError((name,'native solid invalid'))
        brep=source/(name+'.brep'); step=exports/(name+'.step'); stl=exports/(name+'.stl')
        export_brep(shape,brep); export_step(shape,step); export_stl(shape,stl,tolerance=.1,angular_tolerance=.2)
        volume,com,I,_=native_properties(shape)
        rt=import_step(step); rv,*_=native_properties(rt)
        tm=trimesh.load(stl,force='mesh',process=True)
        if not tm.is_watertight or not tm.is_winding_consistent or tm.volume<=0: raise ValueError((name,'STL topology'))
        # STEP rewrites analytic intersection tolerances; 10ppm is below the
        # machining volume uncertainty. Record it, rather than asserting exact bytes.
        if abs(rv-volume)>volume*1e-5 or abs(tm.volume-volume)>volume*.005: raise ValueError((name,'roundtrip volume',rv,volume,tm.volume))
        vertices,quads=quad_sampling(tm)
        vertices=vertices@rotation.T+origin/1000
        npz=source/(name+'_quad.npz'); np.savez_compressed(npz,vertices=vertices,faces=quads)
        rho=7850 if material=='steel' else 2700
        record=dict(name=name,body=owner,material=material,unit='mm',density_kg_m3=rho,
            volume_mm3=volume,mass_kg=volume*rho*1e-9,
            center_of_mass_world_m=((rotation@com+origin)/1000).tolist(),
            inertia_at_com_world_kg_m2=(rotation@(I*rho*1e-15)@rotation.T).tolist(),
            world_from_local_mm=dict(rotation=rotation.tolist(),translation=origin.tolist()),
            notes=notes or [],features=features or [],manufacturing_released=False,
            native_valid=True,stl_watertight=True,quad_faces=len(quads),
            step_volume_relative_error=abs(rv-volume)/volume,stl_volume_relative_error=abs(tm.volume-volume)/volume,files={})
        for p in [brep,step,stl,npz]: record['files'][p.suffix[1:]]=dict(path=str(p.relative_to(ROBOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        records.append(record)
        scene.append(dict(name=name,body=owner,group='native_pitch_assembly',material='titanium' if material=='steel' else 'ivory',
            role='dimensioned_attachment_unreleased_full_assembly',geometry_npz=str(npz.relative_to(ROBOT)),source_sha256=hashlib.sha256(npz.read_bytes()).hexdigest()))
        return shape

    pairs=[] if args.layout else [('lower_neck','neck_pitch','neck_mid_pitch'),('upper_neck','neck_mid_pitch','head_pitch')]
    for side in ['right','left']:
        pairs += [(side+'_thigh',side+'_hip_pitch',side+'_knee_pitch'),(side+'_shin',side+'_knee_pitch',side+'_ankle_pitch')]
    for label,upper,lower in pairs:
        # Preserve physical axes and pivots; normalize +Y toward output side.
        rotation=np.eye(3) if s.axes[upper][1]>0 else np.diag([1.,-1.,-1.])
        origin=s.pivots[upper]*1000
        b=rotation.T@((s.pivots[lower]-s.pivots[upper])*1000); a=np.zeros(3)
        uf=facts[s.selected[upper]]; lf=facts[s.selected[lower]]
        def coord(d,key): return d['vendor_output_direction_y']*(d[key]-d['bbox_center_y'])
        output=coord(uf,'output_mount_face_vendor_y')
        casefront=coord(lf,'case_front_mount_face_vendor_y')
        caserear=coord(lf,'case_rear_mount_face_vendor_y')
        urear=coord(uf,'case_rear_mount_face_vendor_y')
        level=1 if label=='upper_neck' or label.endswith('_shin') else 0
        adapter_t=4+6.5*level
        front_inner=output+adapter_t; front_y=front_inner+2.75
        rear_y=-39.-6.5*level; rear_inner=rear_y+2.75
        top_motor=radial(27,uf['output_mount']['vendor_angles_xz_deg'],output+adapter_t/2)
        top_links=radial(32,[0,120,240],output+adapter_t/2)
        guide=radial(24,[60,180,300],output+adapter_t/2)
        adapter=cylinder(20,adapter_t,[0,output+adapter_t/2,0],'y')-cylinder(4,adapter_t+4,[0,output+adapter_t/2,0],'y')
        adapter+=cylinder(8.98,1.3,[0,output-.65,0],'y')-cylinder(4,5,[0,output-.65,0],'y')
        adapter=holes(adapter,top_motor,3.2,adapter_t+5,'y')
        adapter=holes(adapter,guide,4.05,adapter_t+5,'y')
        adapter=holes(adapter,top_links,2.5,adapter_t+5,'y')
        emit(label+'_output_adapter',adapter,upper,rotation,origin,
            notes=['Three M3 TAP through holes at PCD32; deburr, minimum effective thread3.5mm.',
                   'Motor M3x8 +0.5mm washer at level0; M3x16 +1.5mm washers at level1; max4.5mm insertion.',
                   'Fork M3x10 +1mm washer:3.5mm thread engagement; do not substitute longer screws.'],
            features=[dict(type='tap_drill',thread='M3',diameter_mm=2.5,centers_mm=[p.tolist() for p in top_links])])
        front=fork_profile(a,b,front_y)
        front=holes(front,radial(32,[0,120,240],front_y),3.2,12,'y')
        front=holes(front,radial(27,uf['output_mount']['vendor_angles_xz_deg'],front_y),5.8,12,'y')
        front-=cylinder(7,12,[0,front_y,0],'y')
        front-=cylinder(21,12,b+[0,front_y,0],'y')
        lm=lf['case_front_mount']; clearance=3.2 if lm['thread']=='M3' else 2.7
        lower_holes=radial(lm['pcd'],lf['vendor_output_direction_y']*np.array(lm['vendor_angles_xz_deg']),front_y,b)
        front=holes(front,lower_holes,clearance,12,'y')
        spacer_t=front_inner-casefront
        for k,p in enumerate(lower_holes):
            ring=cylinder(4,spacer_t,[p[0],casefront+spacer_t/2,p[2]],'y')-cylinder(clearance/2,spacer_t+2,[p[0],casefront+spacer_t/2,p[2]],'y')
            emit(label+f'_distal_front_spacer_{k}',ring,upper,rotation,origin,
                notes=['Turned case stand-off replaces heavy full annular block; parallel ends0.03mm.', 'Never connect this static case spacer to the rotating output.'])
        rear=fork_profile(a,b,rear_y,rear=True)
        # 19H7 seat: nominal mesh19.009. Outer shoulder at inner face leaves0.5mm.
        rear-=cylinder(9.5045,5.0,[0,rear_y-.25,0],'y')
        rear-=cylinder(6.5,10,[0,rear_y,0],'y')
        retainer_points=radial(25,[0,120,240],rear_y)
        rear=holes(rear,retainer_points,2.05,12,'y')
        rear-=cylinder(18,12,b+[0,rear_y,0],'y')
        rm=lf['case_rear_mount']; rear_clear=3.2 if rm['thread']=='M3' else 2.7
        rear_holes=radial(rm['pcd'],lf['vendor_output_direction_y']*np.array(rm['vendor_angles_xz_deg']),rear_y,b)
        rear=holes(rear,rear_holes,rear_clear,12,'y')
        next_fork=lower in {x[1] for x in pairs}
        for k,p in enumerate(rear_holes):
            h=caserear-rear_inner
            # Reserve the same actual2mm steel spider at the next motor. One
            # shared case bolt passes through the stack; no overlapping posts.
            regions=[('outer',rear_inner,caserear-3),('inner',caserear-1,caserear)]
            if not next_fork: regions.append(('middle',caserear-3,caserear-1))
            for region,start,end in regions:
                spacer=cylinder(4,end-start,[p[0],(start+end)/2,p[2]],'y')-cylinder(rear_clear/2,end-start+2,[p[0],(start+end)/2,p[2]],'y')
                emit(label+f'_distal_rear_spacer_{region}_{k}',spacer,upper,rotation,origin,
                    notes=['Turned aluminium spacer; two end faces parallel within0.03mm.', 'If next fork exists, its stationary steel spider fills the2mm middle stack. Shared case screw, not two screws.'])
        # The fixed rear spider carries a stationary shaft. Moving plate has
        # bearing outer ring; no static-case screw passes through the moving plate.
        rear_face=urear-1.
        spider=cylinder(8,2,[0,rear_face-1,0],'y')
        rear_mount=uf['case_rear_mount']
        rh=radial(rear_mount['pcd'],uf['vendor_output_direction_y']*np.array(rear_mount['vendor_angles_xz_deg']),rear_face-1)
        for p in rh:
            spider+=bar(np.zeros(3),np.array([p[0],0,p[2]]),8,2,rear_face-1)
            spider+=cylinder(5,2,p,'y')
        spider=holes(spider,rh,3.2,5,'y')
        shaft_end=rear_y-2.75-.4
        spider+=cylinder(4.996,abs(shaft_end-(rear_face-2)),[0,(shaft_end+rear_face-2)/2,0],'y')
        inner_bearing_face=rear_y+2.25
        spider+=cylinder(6.25,(rear_face-2)-inner_bearing_face,[0,((rear_face-2)+inner_bearing_face)/2,0],'y')
        # M3 blind tapped retainer hole is physically bored from outer end.
        spider-=cylinder(1.25,8,[0,shaft_end+4,0],'y')
        emit(label+'_stationary_idler_spider',spider,s.parents[upper],rotation,origin,material='steel',
            notes=['C45 steel, shaft10g6, bearing inner ring slip fit; outer retaining washer contacts INNER RING only.',
                   'Four M3x8 grade10.9 +0.5mm washer +1mm standoff:4.5mm insertion, max5.',
                   'End M3 TAP depth8; use M3x6 +0.5mm washer. Shaft shoulder/washer must clear bearing seals.',
                   'Rear driver/cable cooling and mating plug remain whole-assembly gates.'])
        if level==0:
            for k,p in enumerate(rh):
                spacer=cylinder(4,1,[p[0],urear-.5,p[2]],'y')-cylinder(1.6,3,[p[0],urear-.5,p[2]],'y')
                emit(label+f'_proximal_rear_spacer_{k}',spacer,s.parents[upper],rotation,origin,
                    notes=['1mm stand-off maintains driver rear-face clearance; M3x8 stack includes this spacer.'])
        bearing=cylinder(9.5,5,[0,rear_y-.25,0],'y')-cylinder(5,7,[0,rear_y-.25,0],'y')
        emit(label+'_idler_bearing_installation',bearing,upper,rotation,origin,material='steel',
            notes=['Purchased SKF61800,10x19x5; installation envelope, NOT a manufactured plain steel sleeve.',
                   'Use catalog mass and dynamic behavior, not this envelope density.'])
        records[-1].update(mass_kg=.0053,mass_basis='SKF61800 catalog; annular installation envelope inertia approximation',
            inertia_at_com_world_kg_m2=(np.array(records[-1]['inertia_at_com_world_kg_m2'])*.0053/records[-1]['mass_kg']).tolist(),
            role='purchased_bearing_installation_envelope')
        outer_cover_y=rear_y-3.25
        cover=cylinder(14,1,[0,outer_cover_y,0],'y')-cylinder(8.5,3,[0,outer_cover_y,0],'y')
        cover=holes(cover,radial(25,[0,120,240],outer_cover_y),2.7,4,'y')
        emit(label+'_bearing_outer_retainer',cover,upper,rotation,origin,
            notes=['Three M2.5x5 +0.5mm washer into fork M2.5 TAP3.5mm.', 'ID17 contacts outer race only; purchased bearing race abutment diagram must be matched.'])
        washer_y=shaft_end-.25
        washer=cylinder(6.25,.5,[0,washer_y,0],'y')-cylinder(1.6,3,[0,washer_y,0],'y')
        emit(label+'_shaft_end_washer',washer,s.parents[upper],rotation,origin,material='steel',
            notes=['0.5mm steel washer OD12.5 ID3.2. M3x6 into stationary shaft.', '0.4mm axial float at inner race is intentional, not uncontrolled press preload.'])
        middle=(a+b)/2; direction=b/np.linalg.norm(b)
        bridge_y=(front_inner+rear_inner)/2; bridge_h=front_inner-rear_inner
        bridge=bar(middle-direction*7,middle+direction*7,18,bridge_h,bridge_y)
        # CNC through-window leaves two2mm rails and8mm solid tapped ends;
        # unlike a sealed hollow block, this is machinable from an open side.
        bridge-=bar(middle-direction*5,middle+direction*5,20,bridge_h-16,bridge_y)
        bolt_points=[middle+direction*k+[0,0,0] for k in [-4.,4.]]
        for p in bolt_points:
            front=holes(front,[p+[0,front_y,0]],3.2,12,'y')
            rear=holes(rear,[p+[0,rear_y,0]],3.2,12,'y')
            # blind taps from each end: depth8, with open middle untouched.
            bridge=holes(bridge,[p+[0,front_inner-4,0],p+[0,rear_inner+4,0]],2.5,8,'y')
        emit(label+'_bridge',bridge,upper,rotation,origin,notes=['Four M3x12 with0.5mm washers;6mm engagement in M3 blind taps8mm.'])
        emit(label+'_output_fork_plate',front,upper,rotation,origin,notes=['CNC6061-T6,5.5mm, white paint outside fits; no paint on joint interfaces.'])
        emit(label+'_idler_fork_plate',rear,upper,rotation,origin,notes=['CNC6061-T6,5.5mm. SKF61800 outer seat19H7; inner shoulder0.5mm.', 'Three M2.5 TAP holes secure the separate outer-race cover.'])
        assemblies.append(dict(name=label,upper_joint=upper,lower_joint=lower,owner=upper,
            near_plate_center_local_y_mm=front_y,far_plate_center_local_y_mm=rear_y,
            plate_center_spacing_mm=front_y-rear_y,front_spacer_mm=spacer_t,rear_spacer_mm=caserear-rear_inner,
            axial_level=level,neighbor_fork_separation_mm=1.,output_adapter_thickness_mm=adapter_t,
            plate_stem_width_mm=24.,plate_stem_thickness_mm=5.5,conservative_net_beam_width_mm=20.8,
            bearing=dict(sku='SKF61800',dimensions_mm=[10,19,5],dynamic_load_n=1720,static_load_n=830,catalog_mass_kg=.0053),
            static_rear_support_owner=s.parents[upper],moving_bearing_outer_owner=upper,
            output_fork_thread=dict(pcd_mm=32,thread='M3',count=3,effective_engagement_mm=3.5),
            load_path='motor output -> tapped adapter -> near fork -> bridge -> far fork; opposite-side radial support through bearing onto stationary rear spider; distal motor case belongs to this moving link',
            release=False,remaining=['purchased bearing abutment limits','distal fastener stacks','motor cable installation','assembled sweep and stress concentrations']))
        print(label,'native parts done',flush=True)
    manifest=dict(schema='goose_native_pitch_assembly_v1',scope='four new-layout leg links only' if args.layout else 'six parallel-axis links only',
        manufacturing_pass=False,assembly_pass=False,source_hashes={str(facts_file.relative_to(ROOT)):hashlib.sha256(facts_file.read_bytes()).hexdigest(),str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        parts=records,assemblies=assemblies)
    if args.layout:
        manifest['source_hashes'][str(args.layout.resolve().relative_to(ROOT))] = hashlib.sha256(args.layout.read_bytes()).hexdigest()
        manifest['source_hashes']['src/sai_agent/goose/morphology.py'] = hashlib.sha256((ROOT/'src/sai_agent/goose/morphology.py').read_bytes()).hexdigest()
    (exports/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='NATIVE_PARALLEL_PITCH_ATTACHMENTS_NOT_FULL_ASSEMBLY',parts=scene),separators=(',',':'))+'\n')


if __name__=='__main__': main()
