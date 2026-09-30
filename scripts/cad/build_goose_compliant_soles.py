"""Native replaceable TPU leaf soles and matching tapped aluminium load plates.

Geometric spring constants are screening hypotheses, not measured TPU contact.
Each foot has six independent10mm-span leaves with1.5mm bottom-out clearance.
This changes the contact surface and requires a new physics version.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import trimesh
from build123d import import_step,Face,Solid,Vector,Pos,export_step,export_brep,export_stl

ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,holes
from build_goose_actuator_interfaces import quad_sampling
from goose_nurbs_skin import native_properties


def leaf(x,y):
    # Local top of supporting walls is z=0. The1mm carrier is above it.
    shape=box((2,24,4.2),(x-6,y,-2.1))+box((2,24,4.2),(x+6,y,-2.1))
    shape+=box((10,24,2.4),(x,y,-3.0))
    shape+=box((5,24,1.5),(x,y,-4.95))
    return shape


def main():
    source=R/'cad/source/compliant_foot'; out=R/'cad/exports/compliant_foot'
    source.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    parts=[];scene=[];feet=[]
    for side,sign in [('right',-1),('left',1)]:
        original=R/f'cad/exports/foot_support_candidate/{side}_foot_load_plate.step'
        plate=import_step(original)
        bottom=[f for f in plate.faces() if abs(f.center().Z-3.5)<1e-6 and abs(f.normal_at().Z)>.99]
        if len(bottom)!=1: raise ValueError((side,'ambiguous bottom face'))
        face=Face(bottom[0].outer_wire())
        carrier=Solid.extrude(face,Vector(0,0,1)).moved(Pos(0,0,-1))
        centers=[(x,sign*89+dy) for x in [-55.,25.,98.] for dy in [-18.,18.]]
        sole=carrier
        for x,y in centers: sole+=leaf(x,y).moved(Pos(0,0,2.5))
        fasteners=[(x,sign*89+dy,3.) for x in [-50.,90.] for dy in [-30.,30.]]
        sole=holes(sole,fasteners,3.2,12,'z')
        # TAP geometry: holes2.5mm, M3 through4mm. Native plate receives exact
        # same mounting positions; four independent screws clamp the carrier.
        plate=holes(plate,fasteners,2.5,12,'z')
        for suffix,shape,rho,material in [('flexible_sole',sole,1240.,'rubber'),('tapped_load_plate',plate,2700.,'titanium')]:
            name=side+'_'+suffix
            if not shape.is_valid or len(shape.solids())!=1:raise ValueError((name,'native validity'))
            brep=source/(name+'.brep');step=out/(name+'.step');stl=out/(name+'.stl')
            export_brep(shape,brep);export_step(shape,step);export_stl(shape,stl,tolerance=.08,angular_tolerance=.15)
            tm=trimesh.load(stl,process=True,force='mesh');v,c,I,_=native_properties(shape)
            rt=import_step(step);rv,*_=native_properties(rt)
            if not tm.is_watertight or not tm.is_winding_consistent or tm.volume<=0 or abs(rv-v)>v*1e-5:raise ValueError((name,'roundtrip'))
            vertices,quads=quad_sampling(tm);npz=source/(name+'_quad.npz');np.savez_compressed(npz,vertices=vertices,faces=quads)
            record=dict(name=name,body=side+'_ankle_roll',material=material,density_kg_m3=rho,
                volume_mm3=v,mass_kg=v*rho*1e-9,center_of_mass_world_m=(c/1000).tolist(),
                inertia_at_com_world_kg_m2=(I*rho*1e-15).tolist(),native_valid=True,stl_watertight=True,
                quad_faces=len(quads),unit='mm',manufacturing_released=False,files={})
            for file in [brep,step,stl,npz]:record['files'][file.suffix[1:]]=dict(path=str(file.relative_to(R)),sha256=hashlib.sha256(file.read_bytes()).hexdigest())
            parts.append(record);scene.append(dict(name=name,body=record['body'],group=side+'_foot',material=material,
                role='native_compliant_contact_candidate',geometry_npz=str(npz.relative_to(R)),source_sha256=hashlib.sha256(npz.read_bytes()).hexdigest()))
        # Geometric compression range stops before a screw head can meet ground.
        feet.append(dict(side=side,pad_centers_world_xy_mm=[list(c) for c in centers],
            contact_rectangles_size_mm=[5.,24.],undeformed_contact_plane_world_z_mm=-3.2,
            load_plate_bottom_mm=3.5,carrier_thickness_mm=1.,leaf_span_mm=10.,leaf_width_mm=24.,leaf_thickness_mm=2.4,
            available_compression_mm=1.5,fastener_positions_mm=[list(p) for p in fasteners],
            mounting=dict(thread_in_plate='M3',screw='ISO7380-1 M3x6 grade8.8',quantity=4,
                underside_spacer_mm=1.,washer_mm=.5,tpu_carrier_mm=1.,nominal_aluminium_engagement_mm=3.5),
            print_orientation='carrier flat on bed, contact pads upward; open10mm bridges, no enclosed support',
            material='Bambu TPU90A, external spool; dried per maker; dense leaf and carrier, no unmeasured infill spring shortcut'))
        print(side,'compliant sole and native tapped plate complete',flush=True)
    report=dict(schema='goose_compliant_foot_v1',manufacturing_pass=False,contact_release=False,
        old_model_modified=False,requires_new_contact_version=True,robot_rigid_parts_must_be_raised_mm=3.7,
        # Leaf elementary beam uses tensile E as a first approximation; printed
        # bending, geometric stiffening and hysteresis remain coupon inputs.
        material_data=dict(density_kg_m3=1240.,youngs_modulus_z_mpa=4.4,youngs_modulus_z_uncertainty_mpa=.6,
            source='https://store.bblcdn.eu/s8/default/8140c9d50a6049a3b634fa1387518d8d/Bambu_TPU_90A_Technical_Data_Sheet_582bf8f6-1f0a-474c-aeda-9e72af3689dc.pdf',
            scope='manufacturer typical tensile specimen; not a measured spring or friction coefficient'),
        parts=parts,feet=feet,source_hashes={str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        remaining_gates=['spring force/deflection coupon and repeated load hysteresis','actual ankle interface and all shoe outer covers','new version inertia/contact model and terrain validation','measured dry/wet traction and wear'])
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status='COMPLIANT_FOOT_NOT_FULL_ASSEMBLY_RELEASE',parts=scene),separators=(',',':'))+'\n')


if __name__=='__main__':main()
