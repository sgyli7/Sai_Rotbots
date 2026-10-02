"""Check integral native shell, finite head poses, service path and new statics.

Preserve unknowns and failures. This does not release the rest of the robot.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

import numpy as np
import trimesh
from build123d import import_brep, import_step
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models'),str(ROOT/'scripts/diagnostics')]
from build_goose_cad import box,transform
from build_goose_stage_two import candidate
from build_goose_integrated_hardware_candidate import opposed_clamp_result
from check_goose_grip_cassettes import bounded_common


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(shape):
    bb=shape.bounding_box(optimal=False)
    return np.array(tuple(bb.min)),np.array(tuple(bb.max))


def main():
    paths=[R/p for p in ['cad/exports/one_piece_head_service/manifest.json',
        'evidence/one_piece_head_service_parameters.json','cad/source/torso_shell_mount_fixture/assembly_scene.json',
        'evidence/integrated_hardware_parameters.json','evidence/body_bay_mechanical_parameters.json',
        'configs/mechanical_physics_contract.json','evidence/camera_catalog_layout.json']]
    kit,params,scene,poses_source,default,contract,catalog=[json.loads(p.read_text()) for p in paths]
    for value in [kit,params]:
        for rel,digest in value['source_hashes'].items():
            if sha(ROOT/rel)!=digest:raise ValueError(('Changed input',rel))
    part=kit['parts'][0]
    for file in part['files'].values():
        if sha(R/file['path'])!=file['sha256']:raise ValueError('Changed output')
    shell=import_brep(R/part['files']['brep']['path'])
    if not shell.is_valid or len(shell.solids())!=1:raise ValueError('Not one native shell')
    q=np.load(R/part['files']['npz']['path']);v,f=q['vertices'],q['faces']
    if f.shape[1]!=4:raise ValueError('Non-quad source')
    mesh=trimesh.Trimesh(v,np.concatenate([f[:,[0,1,2]],f[:,[0,2,3]]]),process=False)
    volume_error=abs(mesh.volume*1e9/part['volume_mm3']-1)
    if not mesh.is_watertight or not mesh.is_winding_consistent or volume_error>.005:
        raise ValueError('Quad source closure/volume failed')
    targets,owners={},{}
    for p in scene['parts']:
        if p['name'] in kit['replaces_existing_parts'] or p.get('role')=='vendor_dimension_display_reference_not_printable':continue
        if p.get('body') not in ['head_roll','head_pitch','beak_hinge','beak_input_rotor','beak_coupler_link']:continue
        file=R/p['geometry_npz']
        if sha(file)!=p['source_sha256']:raise ValueError('Changed predecessor quad')
        native=file.with_name(file.name.replace('_quad.npz','.brep'))
        if not native.exists():raise ValueError(('Missing native head target',p['name']))
        shape=import_brep(native)
        if not shape.is_valid or not shape.solids():raise ValueError('Invalid head target')
        targets[p['name']]=shape;owners[p['name']]=p['body'];paths.extend([file,native])
    supplier_path=ROOT/'artifacts/Goose_V0.1/camera_vendor_docs/b0471.step'
    if sha(supplier_path)!=catalog['vendor_files']['step']['sha256']:raise ValueError('Changed OEM input')
    supplier=import_step(supplier_path);paths.append(supplier_path)
    pose=catalog['selected'];vendor_r=np.array(pose['vendor_to_native_rotation']);vendor_t=np.array(pose['vendor_to_native_translation_mm'])
    vendor_inventory=[]; vendor_atoms={}; vendor_enclosures={}; vendor_open_bounds={}
    for child in supplier.children:
        valid=bool(child.is_valid and child.solids())
        if valid:
            shape=transform(child,vendor_r,vendor_t)
        else:
            lo,hi=bounds(child);shape=transform(box(hi-lo+1.4,(hi+lo)/2),vendor_r,vendor_t)
        name='supplier_'+child.label;targets[name]=shape;owners[name]='head_roll'
        atoms=[]
        if valid:
            for solid in child.solids():
                lo,hi=bounds(solid)
                atoms.append((transform(solid,vendor_r,vendor_t),transform(box(hi-lo+.02,(hi+lo)/2),vendor_r,vendor_t)))
        else:
            records=[]
            for index,original in enumerate(child.shells()):
                lo,hi=bounds(original)
                records.append(dict(index=index,lo=lo,hi=hi,center=(lo+hi)/2,faces=len(original.faces())))
            if sum(r['faces'] for r in records)!=len(child.faces()):
                raise ValueError('Original non-solid group shell inventory omits source faces')
            vendor_open_bounds[name]=records
            atoms.append((shape,shape))
        vendor_atoms[name]=atoms
        lo,hi=bounds(child)
        vendor_enclosures[name]=transform(box(hi-lo+.02,(hi+lo)/2),vendor_r,vendor_t) if valid else shape
        vendor_inventory.append(dict(name=name,source_valid=valid,source_solids=len(child.solids()),
            original_shells=len(child.shells()),original_faces=len(child.faces()),all_original_faces_retained=True,
            basis='All original valid OEM solids' if valid else 'Complete original shell hierarchy; each source bounds expanded0.7mm'))
    queries=[]
    def raw_common(a,b,label):
        lo1,hi1=bounds(a);lo2,hi2=bounds(b)
        if np.any(np.minimum(hi1,hi2)-np.maximum(lo1,lo2)<=1e-6):return dict(volume_mm3=0.,method='complete native bounds disjoint')
        result=bounded_common(a,b,3.);queries.append(dict(pair=label,timebox_seconds=3.,**result))
        if result.get('error')=='NATIVE_PAIR_TIMEBOX':
            result=bounded_common(a,b,20.);queries.append(dict(pair=label,timebox_seconds=20.,**result))
        return result
    def supplier_common(a,name,displacement,label):
        if name in vendor_open_bounds:
            import time
            started=time.monotonic(); results=[]; covered=[]; unresolved=[]; contacts=[]
            def visit(records,depth):
                lo=np.min([r['lo'] for r in records],axis=0);hi=np.max([r['hi'] for r in records],axis=0)
                envelope=transform(box(hi-lo+1.4,(hi+lo)/2),vendor_r,vendor_t+displacement)
                result=raw_common(a,envelope,[*label,name,'complete_original_shell_group_bounds',depth,len(records)])
                row=dict(indices=[r['index'] for r in records],source_faces=sum(r['faces'] for r in records),depth=depth,**result)
                results.append(row)
                if 'error' not in result and result['volume_mm3']<=1e-8:
                    covered.extend(row['indices']);return
                if len(records)==1:
                    (unresolved if 'error' in result else contacts).append(row);return
                if time.monotonic()-started>300:
                    unresolved.append(dict(indices=row['indices'],error='COMPLETE_ORIGINAL_GROUP_PROOF_TIMEBOX'));return
                axis=int(np.argmax(np.ptp([r['center'] for r in records],axis=0)))
                records=sorted(records,key=lambda r:r['center'][axis]);mid=len(records)//2
                visit(records[:mid],depth+1);visit(records[mid:],depth+1)
            visit(vendor_open_bounds[name],0)
            result=dict(method='Every original non-solid source shell enclosed; source-axis bounds expanded0.7mm, recursively refined without omitting any original faces',
                source_faces_retained=sum(r['faces'] for r in vendor_open_bounds[name]),source_shells_retained=len(vendor_open_bounds[name]),
                covered_clear_shells=len(set(covered)),leaf_contacts=contacts,unresolved_bounds=unresolved,group_bounds_results=results,
                physical_purchased_camera_qualified=False)
            if unresolved:result['error']='ORIGINAL_OPEN_OEM_SOURCE_BOUNDS_UNRESOLVED'
            else:result['volume_mm3']=sum(max(0.,r['volume_mm3']) for r in contacts)
            return result
        whole=raw_common(a,transform(vendor_enclosures[name],np.eye(3),displacement),[*label,name,'complete_group_bounds'])
        if 'error' not in whole and whole['volume_mm3']<=1e-8:
            return dict(volume_mm3=0.,method='Complete original OEM group bounds expanded0.01mm; conservative zero proof',original_solids_retained=len(vendor_atoms[name]),group_enclosure_result=whole)
        results=[]
        for index,(solid,enclosing) in enumerate(vendor_atoms[name]):
            envelope=transform(enclosing,np.eye(3),displacement)
            coarse=raw_common(a,envelope,[*label,name,'complete_solid_bounds',index])
            if 'error' not in coarse and coarse['volume_mm3']<=1e-8:
                result=dict(volume_mm3=0.,method='complete original native solid bounds expanded0.01mm; conservative zero proof')
            else:
                result=raw_common(a,transform(solid,np.eye(3),displacement),[*label,name,'original_solid',index])
            results.append(dict(index=index,enclosing_result=coarse,**result))
        if any('error' in x for x in results):
            return dict(error='ORIGINAL_OEM_SOLID_PROOF_UNRESOLVED',solid_results=results)
        return dict(volume_mm3=sum(max(0.,x['volume_mm3']) for x in results),
            method='All original OEM solids retained; conservative sum intersection bound',solids_checked=len(results),solid_results=results)
    def common(a,b,label):
        if label[-1] in vendor_atoms:
            # First head case is zero; subsequent same-owner rigid cases use
            # its invariant cache. Service camera poses are explicit below.
            np.testing.assert_allclose(bounds(b),bounds(targets[label[-1]]),atol=1e-5)
            return supplier_common(a,label[-1],np.zeros(3),label[:-1])
        return raw_common(a,b,label)
    system=candidate();system.pivots={k:np.array(v) for k,v in params['pivots_world_at_zero_m'].items()}
    lift=np.array([0.,0.,params['rigid_coordinate_lift_m']])
    cases=[('zero',{})]+[(r['name'],r['joint_q_rad']) for r in poses_source['static_results'] if r['mass_variant']==0 and r['drag_x_n']==0]
    cases += [('head_roll_'+str(q),{'head_roll':q}) for q in [-.6,.6]]
    reports,cache=[],{}
    for label,q in cases:
        fk,_=system.fk(q,root_p=system.pivots['torso'])
        def place(shape,owner):
            if owner in {'beak_input_rotor','beak_coupler_link'}:
                if abs(q.get('beak_hinge',0.))>1e-12:raise ValueError('Closed-jaw reduction only')
                owner='head_roll'
            pos,rot=fk[owner]
            return transform(shape,rot,(pos-lift-rot@(system.pivots[owner]-lift))*1000)
        moved=place(shell,'head_roll');hits,unknown=[],[]
        for name,other in targets.items():
            key=(name,'fixed' if owners[name] in {'head_roll','beak_input_rotor','beak_coupler_link'} else label)
            if key not in cache:cache[key]=common(moved,place(other,owners[name]),[label,'head_integral_print_shell',name])
            result=cache[key]
            if 'error' in result:unknown.append(dict(target=name,**result))
            elif result['volume_mm3']>.01:hits.append(dict(target=name,**result))
        reports.append(dict(name=label,joint_q_rad=q,collisions=hits,unresolved=unknown,pass_fit=not hits and not unknown))
        print('INTEGRAL FIT',label,len(hits),'hits',len(unknown),'unknown',[(h['target'],h['volume_mm3']) for h in hits],flush=True)
    # Complete core installation sequence remains a separate gate. The
    # interrupted predecessor's failed straight-removal route is not inherited
    # as a passed route for this revised one-piece source.
    install=[];camera_service=[]
    core_names=['head_frame_camera_fastened_carrier','beak_motor_catalog_case','head_roll_horn_adapter','jaw_front_bearing','jaw_rear_bearing']
    for dx in np.arange(0.,160.001,5.):
        moved=transform(shell,np.eye(3),[dx,0.,0.]);hits,unknown=[],[]
        for name in core_names:
            result=raw_common(moved,targets[name],['service_front_translation',float(dx),name])
            if 'error' in result:unknown.append(dict(target=name,**result))
            elif result['volume_mm3']>.01:hits.append(dict(target=name,**result))
        install.append(dict(shell_front_translation_mm=float(dx),collisions=hits,unresolved=unknown,pass_fit=not hits and not unknown))
        print('ONE PIECE CORE SERVICE',float(dx),len(hits),'hits',len(unknown),'unknown',flush=True)
    system.items=copy.deepcopy(params['items']);system.contact_hulls={k:ConvexHull(np.array(v)) for k,v in default['contact_hulls'].items()}
    system.contact_center_y_m=default['contact_center_y_m'];system.tip=np.array(default['tip_world_at_zero_m'])
    payload=copy.deepcopy(next(p for p in default['items'] if p['name']=='specified_payload_50g'));system.items.append(payload)
    static={}
    for station,point,force in [('front20n',poses_source['front_grip_reference_world_m'],20.),('middle50n',poses_source['middle_grip_reference_world_m'],50.)]:
        system.grip=np.array(point);payload['center_m']=(system.grip+np.array(default['native_grip_reference']['payload_reference_offset_m'])).tolist();results=[]
        for variant in [-1,0,1]:
            model,_=system.model(variant)
            for row in poses_source['static_results']:
                if row['mass_variant']!=variant:continue
                w,x,y,z=row['root_quaternion_wxyz'];support=['right'] if row['name']=='right_single_support' else ['left'] if row['name']=='left_single_support' else ['right','left']
                result=system.evaluate(row['name'],row['joint_q_rad'],np.array(row['root_position_m']),Rotation.from_quat([x,y,z,w]).as_matrix(),support,variant,row['drag_x_n'],model)
                if force!=50.:result=opposed_clamp_result(system,model,result,force)
                results.append(result)
        summary=[]
        for joint in contract['joints']:
            value=max(abs(r['joint_torque_nm'][joint['name']]) for r in results);limit=joint['continuous_design_limit_nm']
            summary.append(dict(joint=joint['name'],worst_nm=value,limit_nm=limit,margin_nm=limit-value,pass_torque=value<=limit))
        static[station]=dict(cases=len(results),results=results,joint_summary=summary,contact_feasible=sum(r['static_contact_feasible'] for r in results),all_static_torques_pass=all(r['pass_torque'] for r in summary))
    fit_pass=all(p['pass_fit'] for p in reports);path_pass=all(p['pass_fit'] for p in install);camera_path_pass=False
    static_pass=all(v['contact_feasible']==63 and v['all_static_torques_pass'] for v in static.values())
    paths += [Path(__file__),ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py',ROOT/'scripts/models/build_goose_stage_two.py',ROOT/'scripts/models/build_goose_integrated_hardware_candidate.py']
    result=dict(schema='goose_one_piece_head_service_fit_v1',native_single_solid=True,source_quads=len(f),quad_closed=True,
        quad_vs_native_volume_relative_error=volume_error,target_inventory=list(targets),complete_original_oem_groups=vendor_inventory,
        finite_head_cases=reports,incremental_head_fit_pass=fit_pass,finite_service_cases=install,
        finite_service_path_pass=path_pass,finite_camera_service_pass=camera_path_pass,finite_camera_service_cases=camera_service,service_retained_core_parts=core_names,
        service_detached_parts_scope='One-piece print with rear and110x70mm underside openings, detachable camera face. Complete component-by-component insertion/tool path remains unqualified; Finite33 straight retained-core translations checked; optics, cables and tools remain separate gates.',
        continuous_installation_path_pass=False,static_screens=static,same_source_static_pass=static_pass,
        retained_native_pair_proofs=[dict(target=key[0],relative_pose_key=key[1],**value) for key,value in cache.items()],actual_native_queries=queries,full_assembly_pass=False,manufacturing_release=False,training_release=False,final_appearance_pass=False,
        limitations=['Finite10closed-head poses only; other body contacts, opening jaw and continuous sweep remain gates.',
            'Component insertion/removal, continuous swept volume, tool and cable paths remain unqualified for this corrected source.',
            'The OEM non-solid group remains conservatively expanded; purchased revision and plugs remain unqualified.',
            'Torque limits are design screening assumptions, not verified drive/thermal output ratings.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in dict.fromkeys(paths)})
    (R/'evidence/one_piece_head_service_fit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('INTEGRAL SUMMARY',fit_pass,'finite shell service',path_pass,'finite camera service',camera_path_pass,'static',static_pass,flush=True)
    return 0 if fit_pass and path_pass and static_pass else 1


if __name__=='__main__':
    raise SystemExit(main())
