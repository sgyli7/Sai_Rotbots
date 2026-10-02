"""Own perforated motor interfaces from official drawing facts, millimetres.

These are interface prototypes, not an assembled or released motor bracket.
The remaining fork, rear idler, frame and connector gates are explicit.
Vendor geometry is inspected externally and is not redistributed here.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
import trimesh
from build123d import export_brep,export_step,export_stl,import_step
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder,holes
from goose_nurbs_skin import native_properties
ROBOT=ROOT/'robots/Goose_V0.1'

def quad_sampling(mesh):
    """Shared-edge split of native tessellation into closed planar quad cells.

    This is a CAD-derived render mesh, not an artist's subdivision control cage.
    NURBS/analytic BREP remains the editable engineering source.
    """
    points=mesh.vertices.tolist();midpoints={};faces=[]
    for a,b,c in mesh.faces:
        indices=[]
        for i,j in [(a,b),(b,c),(c,a)]:
            key=tuple(sorted((int(i),int(j))))
            if key not in midpoints:
                midpoints[key]=len(points);points.append(((mesh.vertices[i]+mesh.vertices[j])/2).tolist())
            indices.append(midpoints[key])
        center=len(points);points.append(mesh.vertices[[a,b,c]].mean(axis=0).tolist())
        ab,bc,ca=indices
        faces.extend([(a,ab,center,ca),(b,bc,center,ab),(c,ca,center,bc)])
    return np.asarray(points)/1000,np.asarray(faces,dtype=np.int64)

def main():
    facts_path=ROBOT/'hardware/stage_three_actuator_mounts.json'
    facts=json.loads(facts_path.read_text())['catalog']
    source=ROBOT/'cad/source/actuator_interfaces';dest=ROBOT/'cad/exports/actuator_interfaces'
    source.mkdir(parents=True,exist_ok=True);dest.mkdir(parents=True,exist_ok=True)
    records=[];scene=[]
    for kind,d in facts.items():
        direction=d['vendor_output_direction_y'];origin=d['bbox_center_y']
        output=direction*(d['output_mount_face_vendor_y']-origin)
        static=direction*(d['case_front_mount_face_vendor_y']-origin)
        for role in ['output_adapter','stationary_front_ring']:
            mount=d['output_mount'] if role=='output_adapter' else d['case_front_mount']
            thickness=4. if kind=='ak45_36_v3' and role=='output_adapter' else 3.
            y=(output if role=='output_adapter' else static)+thickness/2
            radius=20. if role=='output_adapter' else 30.
            # The stationary ring clears the full rotating adapter, rather
            # than joining the two parts and accidentally locking the axis.
            bore=4. if kind=='ak45_36_v3' and role=='output_adapter' else (7.6 if role=='output_adapter' else 21.)
            shape=cylinder(radius,thickness,(0,y,0),'y')-cylinder(bore,thickness+4,(0,y,0),'y')
            clearance=3.2 if mount['thread']=='M3' else 2.7
            angles=direction*np.deg2rad(mount['vendor_angles_xz_deg'])
            centers=[(mount['pcd']/2*np.cos(a),y,mount['pcd']/2*np.sin(a)) for a in angles]
            shape=holes(shape,centers,clearance,thickness+4,'y')
            features=[dict(type='motor_clearance',diameter_mm=clearance,centers_mm=np.asarray(centers).tolist(),thread_in_motor=mount['thread'],max_motor_insertion_mm=mount['max_insertion'])]
            if kind=='ak45_36_v3' and role=='output_adapter':
                # Actual drawing is a socket. A 17.96mm locating pilot enters
                # 1.30mm, leaving both radial clearance and axial bottom gap.
                pilot_y=output-.65
                pilot=cylinder(8.98,1.3,(0,pilot_y,0),'y')-cylinder(bore,5,(0,pilot_y,0),'y')
                shape=shape+pilot
                pins=d['guide_pins'];pa=direction*np.deg2rad(pins['vendor_angles_xz_deg'])
                pc=[(pins['pcd']/2*np.cos(a),y,pins['pcd']/2*np.sin(a)) for a in pa]
                shape=holes(shape,pc,4.05,thickness+5,'y')
                features.append(dict(type='guide_clearance',diameter_mm=4.05,centers_mm=np.asarray(pc).tolist()))
            # Separate outer link holes: these do not intersect the motor
            # pattern. Threaded mating plate and bolt stack are not inferred.
            if role=='output_adapter':
                link_angles=np.deg2rad([0,120,240])
                link_centers=[(17*np.cos(a),y,17*np.sin(a)) for a in link_angles]
                shape=holes(shape,link_centers,3.2,thickness+3,'y')
                features.append(dict(type='link_clearance',diameter_mm=3.2,centers_mm=np.asarray(link_centers).tolist(),mating_status='fork face and retention design pending'))
            if not shape.is_valid or len(shape.solids())!=1:raise RuntimeError((kind,role,'invalid native solid'))
            name=kind+'_'+role;brep=source/(name+'.brep');step=dest/(name+'.step');stl=dest/(name+'.stl')
            export_brep(shape,brep);export_step(shape,step);export_stl(shape,stl,tolerance=.08,angular_tolerance=.18)
            rt=import_step(step);volume,com,I,error=native_properties(shape);rv,*_=native_properties(rt)
            tm=trimesh.load(stl,force='mesh',process=True)
            if not tm.is_watertight or not tm.is_winding_consistent or tm.volume<=0 or abs(rv-volume)>volume*1e-7:raise RuntimeError((name,'exchange failed'))
            vertices,quads=quad_sampling(tm);npz=source/(name+'_quad.npz');np.savez_compressed(npz,vertices=vertices,faces=quads)
            scene.append(dict(name=name,group='motor_interfaces',material='titanium',role='actual_perforated_interface_uninstalled',geometry_npz=str(npz.relative_to(ROBOT)),source_sha256=hashlib.sha256(npz.read_bytes()).hexdigest()))
            # A selected standard bolt plus 0.5mm washer fits the documented
            # maximum insertion. Actual preload and grade still need release.
            bolt_length=8. if kind=='ak45_36_v3' and role=='output_adapter' else (6. if mount['max_insertion']>=3 else 5.)
            penetration=bolt_length-thickness-.5
            if not 2<=penetration<=mount['max_insertion']-.25:raise RuntimeError((name,'bad screw depth'))
            thread_d=3. if mount['thread']=='M3' else 2.5
            torque=24. if kind=='ak45_36_v3' else (7. if kind=='ak45_10_v3' else 4.1)
            # Equal tangential sharing is only an optimistic elastic screen;
            # it is not a friction/preload or fatigue certification.
            force_per_bolt=torque/(len(centers)*mount['pcd']/2000)
            net_section=radius-mount['pcd']/2-clearance/2
            record=dict(name=name,actuator=kind,role=role,unit='mm',material='aluminium_6061_t6_candidate',density_kg_m3=2700.,volume_mm3=volume,mass_kg=volume*2.7e-6,center_of_mass_local_m=(com/1000).tolist(),inertia_at_com_local_kg_m2=(I*2700e-15).tolist(),native_valid=True,step_roundtrip_valid=True,stl_watertight=True,quad_faces=len(quads),source_quad_kind='shared-edge planar subdivision of native tessellation; not a subdivision modelling cage',interface_face_local_y_mm=output if role=='output_adapter' else static,thickness_mm=thickness,features=features,selected_bolt=dict(thread=mount['thread'],length_mm=bolt_length,washer_thickness_mm=.5,motor_penetration_mm=penetration,insertion_limit_mm=mount['max_insertion'],strength_grade='not released'),screen=dict(applied_catalog_peak_torque_nm=torque,equal_share_tangential_force_n=force_per_bolt,outer_motor_hole_edge_ligament_mm=net_section,outer_link_hole_edge_ligament_mm=1.4 if role=='output_adapter' else None,method='simple equal-share peak-torque screen; excludes preload, unequal sharing, fatigue and off-axis load'),manufacturing_released=False,remaining_gates=['assembled fork/frame mating and back-side idler','thread preload/grade and load-path validation','vendor connector and installation sweep'],files={})
            for file in [brep,step,stl,npz]:record['files'][file.suffix[1:]]=dict(path=str(file.relative_to(ROBOT)),sha256=hashlib.sha256(file.read_bytes()).hexdigest())
            records.append(record);print(name,'mass_g',round(record['mass_kg']*1000,2),flush=True)
    manifest=dict(schema='goose_actuator_interface_prototypes_v1',status='PERFORATED_NATIVE_INTERFACES_NOT_ASSEMBLY_RELEASE',manufacturing_pass=False,unit='mm',local_frame='+Y points out of output end; origin is vendor case bounding-box center; supplied -Y-output files rotate 180deg about X before normalization',facts_sha256=hashlib.sha256(facts_path.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parts=records)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (source/'quad_scene.json').write_text(json.dumps(dict(unit='m',status=manifest['status'],parts=scene),separators=(',',':'))+'\n')
if __name__=='__main__':main()
