"""Native roll-to-pitch carriers, with an explicit new-axis candidate.

Old stage-two assets are immutable. The +8mm X candidate moves hip pitch and
its descendants together; native geometry, mass and the next SI ledger must
follow that change. These carriers do not release the entire leg or robot.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
import trimesh
from build123d import import_step,export_step,export_brep,export_stl

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_cad import transform,cylinder,box,holes
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties
from build_goose_stage_two import candidate
from sai_agent.goose.morphology import apply_leg_layout

SHIFT_MM=8.

def line_plate(a,b,width,thickness):
    a=np.array(a);b=np.array(b);direction=(b-a)/np.linalg.norm(b-a)
    # Profile lies in YZ, thickness along X.
    matrix=np.column_stack(([1.,0,0],direction,np.cross([1.,0,0],direction)))
    return transform(box([thickness,np.linalg.norm(b-a),width]),matrix,(a+b)/2)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--layout',type=Path);args=parser.parse_args()
    s=candidate();facts_path=R/'hardware/stage_three_actuator_mounts.json';facts=json.loads(facts_path.read_text())['catalog']
    if args.layout: apply_leg_layout(s,json.loads(args.layout.read_text()))
    old_adapter_path=R/'cad/exports/pitch_fork_assembly/lower_neck_output_adapter.step'
    folder='body_bay_roll_carriers' if args.layout else 'hip_roll_carriers'
    source=R/'cad/source'/folder;dest=R/'cad/exports'/folder
    source.mkdir(exist_ok=True);dest.mkdir(exist_ok=True);parts=[];scene=[];assemblies=[]
    def emit(name,shape,body,notes,features=None):
        if not shape.is_valid or len(shape.solids())!=1:raise ValueError((name,'native invalid/disconnected'))
        # Detach imported STEP assembly metadata from the moved geometry.
        # Keep the exact native solid; round-trip mass properties below must agree.
        shape=shape.solids()[0]
        volume,com,I,_=native_properties(shape)
        paths={'brep':source/(name+'.brep'),'step':dest/(name+'.step'),'stl':dest/(name+'.stl'),'npz':source/(name+'_quad.npz')}
        export_brep(shape,paths['brep']);export_step(shape,paths['step']);export_stl(shape,paths['stl'],tolerance=.08,angular_tolerance=.18)
        rt=import_step(paths['step']);rv,*_=native_properties(rt)
        mesh=trimesh.load(paths['stl'],force='mesh',process=True)
        if not rt.is_valid or len(rt.solids())!=1 or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:raise ValueError((name,'exchange invalid'))
        if abs(rv/volume-1)>1e-5 or abs(mesh.volume/volume-1)>.005:raise ValueError((name,'exchange volume'))
        vertices,faces=quad_sampling(mesh);np.savez_compressed(paths['npz'],vertices=vertices,faces=faces)
        files={k:dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()}
        parts.append(dict(name=name,body=body,material='aluminium_6061_t6_candidate',unit='mm',density_kg_m3=2700,
            volume_mm3=volume,mass_kg=volume*2700e-9,center_of_mass_world_m=(com/1000).tolist(),inertia_at_com_world_kg_m2=(I*2700e-15).tolist(),
            notes=notes,features=features or [],files=files,native_valid=True,manufacturing_released=False,quad_faces=len(faces)))
        scene.append(dict(name=name,body=body,group='hip_roll_carriers',material='ivory',role='native_cross_axis_carrier_candidate',geometry_npz=files['npz']['path'],source_sha256=files['npz']['sha256']))
    for side in ['right','left']:
        sign=-1 if side=='right' else 1
        parent=s.pivots[side+'_hip_roll']*1000;child=s.pivots[side+'_hip_pitch']*1000+([0,0,0] if args.layout else [SHIFT_MM,0,0])
        # Parent output +X; local +Y is output, normalized local +X is world Y.
        roll_rotation=np.array([[0,1,0],[1,0,0],[0,0,-1]],dtype=float)
        adapter=transform(import_step(old_adapter_path),roll_rotation,parent)
        emit(side+'_hip_roll_output_adapter',adapter,side+'_hip_roll',[
            'Six M3x8 +0.5mm washers into catalog output holes;3.5mm insertion<=4.5mm.',
            'Three existing M3 TAP at PCD32; carrier uses M3x10 +1mm washer,3.5mm engagement.',
            'Native prototype geometry reused in the declared +X orientation, not a copied vendor motor.'])
        front=parent[0]+26.25+4.;x=front+2.75
        case_y=child[1]+sign*25.25;inner=case_y;outer=case_y+sign*4.
        block_y=case_y-sign*3.
        end=np.array([x,block_y,child[2]])
        a=np.array([x,parent[1],parent[2]])
        arm=cylinder(20,5.5,a,'x')+line_plate(a,end,24,5.5)
        link=[parent+roll_rotation@np.array([16*np.cos(t),33.,16*np.sin(t)]) for t in np.deg2rad([0,120,240])]
        arm=holes(arm,link,3.2,14,'x')
        motor_access=[parent+roll_rotation@np.array([13.5*np.cos(t),33.,13.5*np.sin(t)]) for t in np.deg2rad([30,90,150,210,270,330])]
        arm=holes(arm,motor_access,5.8,14,'x')
        arm-=cylinder(7,14,a,'x')
        arm_bolts=[np.array([x,block_y,child[2]+dz]) for dz in [-4,4]]
        arm=holes(arm,arm_bolts,3.2,14,'x')
        # Squared end pad gives the two block screws full edge ligaments.
        pad=box([5.5,6.,32.],[x,block_y,child[2]])
        pad=holes(pad,arm_bolts,3.2,14,'x');arm+=pad
        # Trim the profile at the case-plate inner mating face. A square-ended
        # diagonal arm otherwise overlaps the perpendicular plate by~1.4mm.
        arm-=box([100,100,120],[x,case_y+sign*50.,child[2]])
        emit(side+'_hip_roll_carrier_arm',arm,side+'_hip_roll',[
            'CNC6061-T6 5.5mm flat plate; M3x10 +1mm washers into output adapter.',
            'Two M3x12 +0.5mm washers to block;6mm engagement in8mm blind tap.',
            'Six5.8mm tool/head access bores keep output screws independently accessible.'],
            [dict(type='clearance',axis='x',diameter_mm=3.2,centers_mm=[p.tolist() for p in link+arm_bolts])])
        block_center=np.array([front-6.,block_y,child[2]])
        block=box([12.,6.,32.],block_center)
        xb=[np.array([front-4.,block_y,child[2]+dz]) for dz in [-4,4]]
        block=holes(block,xb,2.5,8,'x')
        yb=[np.array([front-6.,block_y,child[2]+dz]) for dz in [-12,12]]
        block=holes(block,yb,2.5,8,'y')
        emit(side+'_hip_roll_corner_block',block,side+'_hip_roll',[
            'CNC6061-T6,12x6x32mm; twoM3 TAP blind8mm from arm side; twoM3 TAP through6mm from case plate side.',
            'Orthogonal hole rows are separated8mm in Z; no crossed thread bores.',
            'Case plate M3x10 +0.5mm washer:5.5mm insertion; no longer substitute.'],
            [dict(type='tap_drill',axis='x',diameter_mm=2.5,centers_mm=[p.tolist() for p in xb]),dict(type='tap_drill',axis='y',diameter_mm=2.5,centers_mm=[p.tolist() for p in yb])])
        y=(inner+outer)/2
        plate=cylinder(30,4,[child[0],y,child[2]],'y')-cylinder(21,10,[child[0],y,child[2]],'y')
        bridge_min=front-12.;bridge_max=child[0]-25.
        plate+=box([bridge_max-bridge_min,4,32],[(bridge_min+bridge_max)/2,y,child[2]])
        angles=np.deg2rad(facts['ak45_36_v3']['case_front_mount']['vendor_angles_xz_deg'])*sign
        motor_holes=[np.array([child[0]+24*np.cos(t),y,child[2]+24*np.sin(t)]) for t in angles]
        plate=holes(plate,motor_holes,3.2,12,'y')
        plate_bolts=[np.array([front-6.,y,child[2]+dz]) for dz in [-12,12]]
        plate=holes(plate,plate_bolts,3.2,12,'y')
        emit(side+'_hip_pitch_static_front_carrier',plate,side+'_hip_roll',[
            'CNC6061-T6 4mm; sixM3x8 +1mm washer into stator front:3mm insertion<=4mm.',
            'ID42 clears output adapter radius20 with1mm radial gap; outer mounting ring stays separate from moving fork.',
            'TwoM3x10 +0.5mm washer to corner block;5.5mm engagement in6mm through tap.',
            'Child pitch case/front face retained; actual connector/wiring sweep and local strength remain gates.'],
            [dict(type='clearance',axis='y',diameter_mm=3.2,centers_mm=[p.tolist() for p in motor_holes+plate_bolts])])
        assemblies.append(dict(side=side,parent_joint=side+'_hip_roll',child_joint=side+'_hip_pitch',parent_output_world_axis=[1,0,0],
            old_child_pivot_world_mm=(s.pivots[side+'_hip_pitch']*1000).tolist(),new_child_pivot_world_mm=child.tolist(),
            descendants_translation_world_mm=[SHIFT_MM,0,0],same_axis_order=True,manufacturing_pass=False,
            load_path='parent output -> tapped adapter ->5.5mm carrier arm -> orthogonally tapped corner block ->4mm stator front carrier -> six child-case M3 holes; next moving fork stays on child output'))
        if args.layout:
            assemblies[-1].pop('old_child_pivot_world_mm')
            assemblies[-1].pop('descendants_translation_world_mm')
            assemblies[-1]['declared_layout_pivots']=True
        print(side,'carrier native parts done',flush=True)
    payload=dict(schema='goose_hip_roll_carrier_candidate_v1',scope='two roll-to-pitch carriers only; explicit +8mm distal leg X shift',
        new_training_release=False,full_assembly_pass=False,manufacturing_pass=False,parts=parts,assemblies=assemblies,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [facts_path,old_adapter_path,Path(__file__)]})
    if args.layout:
        payload['scope']='two roll-to-pitch carriers at explicit new body-bay pivots; no legacy8mm translation should be applied'
        payload['source_hashes'][str(args.layout.resolve().relative_to(ROOT))]=hashlib.sha256(args.layout.read_bytes()).hexdigest()
    (dest/'manifest.json').write_text(json.dumps(payload,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='HIP_CARRIER_AXIS_SHIFT_CANDIDATE_UNRELEASED',parts=scene),separators=(',',':'))+'\n')
    print('native carrier mass kg',sum(p['mass_kg'] for p in parts))

if __name__=='__main__':main()
