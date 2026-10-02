"""Same-version ledger with native ankles, neck cradle and revised neck passage."""
from pathlib import Path
import copy,hashlib,json,sys
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate
from sai_agent.goose.mass_properties import aggregate_rigid_components


def main():
    paths=[R/'evidence/body_bay_component_parameters.json',R/'cad/exports/body_bay_ankle_assembly/manifest.json',R/'configs/stage_two_contract.json',R/'cad/exports/neck_root_assembly/manifest.json',R/'cad/exports/neck_access_skins/manifest.json',R/'cad/exports/hollow_shoe_covers/manifest.json',R/'cad/exports/head_load_path/manifest.json',R/'cad/exports/beak_native_linkage/manifest.json',R/'cad/exports/head_linkage_clearance_skins/manifest.json']
    old,native,contract,neck,skins,shoes,head,link,cheeks=[json.loads(p.read_text()) for p in paths]
    task_path=R/'configs/mechanical_task_poses.json';paths.append(task_path)
    task=json.loads(task_path.read_text())['low_reach']
    for part in cheeks['parts']:
        part.update(body='head_roll',mass_kg=part['full_density_mass_kg'],mass_basis='native PETG density estimate; local cheek/underside clearance')
    native['parts']+=neck['parts']+skins['parts']+shoes['parts']+head['parts']+link['parts']+cheeks['parts']
    native['fasteners']+=[dict(p,assembly='neck_root') for p in neck['fasteners']]
    native['replaces_existing_native_parts']+=neck['replaces_existing_parts']+skins['replaces_existing_parts']+shoes['replaces_existing_parts']+head['replaces_existing_parts']+link['replaces_existing_parts']+cheeks['replaces_existing_parts']
    replacements_path=R/'configs/mechanical_native_replacements.json'
    fit_path=R/'evidence/jaw_retention_native_fit.json'
    mesh_path=R/'evidence/jaw_retention_quad_gate.json'
    replacements=json.loads(replacements_path.read_text())['additional_replaces_by_folder']
    fit=json.loads(fit_path.read_text());mesh=json.loads(mesh_path.read_text())
    if fit['sample_count']!=23 or fit['passed_samples']!=23 or not mesh['mesh_identity_and_geometry_pass']:
        raise ValueError('bill/retention integration requires the same-source23-sample fit and quad gates')
    for gate in [fit,mesh]:
        for relative,expected in gate['source_hashes'].items():
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                raise ValueError('stale bill/retention gate: '+relative)
    paths.extend([replacements_path,fit_path,mesh_path])
    for filename in ['grip_cassette_native_fit.json','grip_cassette_quad_gate.json',
                     'bill_mount_fasteners_native_fit.json','bill_mount_fasteners_quad_gate.json']:
        path=R/'evidence'/filename;gate=json.loads(path.read_text());paths.append(path)
        if 'passed_samples' in gate and gate['passed_samples']!=gate['sample_count']:
            raise ValueError('incomplete native grip/frame fit: '+filename)
        if 'passed_samples' in gate and gate['sample_count']!=23:
            raise ValueError('native grip/frame fit must cover23jaw poses: '+filename)
        if 'mesh_identity_and_geometry_pass' in gate and not gate['mesh_identity_and_geometry_pass']:
            raise ValueError('native grip/frame quad gate failed: '+filename)
        if filename=='grip_cassette_native_fit.json' and (gate['scope']!='full' or not gate['complete_sample_matrix'] or gate['excluded_native_skins']):
            raise ValueError('grip installation requires the complete shell-inclusive pair matrix')
        for relative,expected in gate['source_hashes'].items():
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                raise ValueError('stale grip/frame gate: '+relative)
    by_part={p['name']:p for p in native['parts']}
    for folder in ['bill_backbones','jaw_retention','grip_cassettes','bill_mount_fasteners']:
        manifest_path=R/'cad/exports'/folder/'manifest.json';paths.append(manifest_path)
        increment=json.loads(manifest_path.read_text())
        removed=increment['replaces_existing_parts']+replacements.get(folder,[])
        native['replaces_existing_native_parts'].extend(removed)
        for name in removed:by_part.pop(name,None)
        for part in increment['parts']:
            if part['name'] in by_part:raise ValueError('duplicate native replacement: '+part['name'])
            by_part[part['name']]=part
    native['parts']=list(by_part.values())
    remove=set(native['replaces_existing_native_parts'])|{'head_roll'}
    remove|={side+suffix for side in ['right','left'] for suffix in ['_ankle_crossmember','_ankle_roll_mount_reserve','_ankle_pitch_structure_allocation','_ankle_roll_structure_allocation']}
    s=candidate();s.pivots={k:np.array(v) for k,v in old['pivots_world_at_zero_m'].items()}
    s.items=[copy.deepcopy(i) for i in old['items'] if i['name'] not in remove and i['name']!='specified_payload_50g']
    lift=old['rigid_coordinate_lift_m'];by_native={p['name']:p for p in native['parts']}
    for p in native['parts']:
        s.items.append(dict(name=p['name'],body=p['body'],mass_kg=p['mass_kg'],center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),
            inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],relative_uncertainty=.1,basis=p.get('mass_basis','native density estimate')+'; same-version native mechanical candidate; installation-envelope inertia remains approximate'))
    for p in native['fasteners']:
        m=p['mass_upper_estimate_kg'];anchor=by_native[p['anchor_part']]
        s.items.append(dict(name=p['assembly']+'_ankle_'+p['role']+'_fastener_bound',body=p['body'],mass_kg=m,
            center_m=(np.array(anchor['center_of_mass_world_m'])+[0,0,lift]).tolist(),inertia_at_com_kg_m2=(np.eye(3)*m*.03**2/3).tolist(),
            relative_uncertainty=.1,basis='conservative full steel screw/head/washer upper mass; anchor COM approximation'))
    assert len({i['name'] for i in s.items})==len(s.items)
    mass=sum(i['mass_kg'] for i in s.items)
    bodies=[dict(name=b['name'],**aggregate_rigid_components([i for i in s.items if i['body']==b['name']],s.pivots[b['name']])) for b in contract['bodies']]
    grip_path=R/'configs/mechanical_grip_reference.json';paths.append(grip_path)
    grip_reference=json.loads(grip_path.read_text())
    s.grip=np.array(grip_reference['reference_native_world_m'])+[0,0,lift]
    s.tip=np.array(old['tip_world_at_zero_m'])
    s.contact_hulls={k:ConvexHull(np.array(v)) for k,v in old['contact_hulls'].items()};s.contact_center_y_m=old['contact_center_y_m']
    payload=copy.deepcopy(next(i for i in old['items'] if i['name']=='specified_payload_50g'))
    payload['center_m']=(s.grip+grip_reference['payload_reference_offset_m']).tolist()
    payload['basis']='specified held-object static lump at the native-cassette reference;no actual contact/grip proof'
    s.items.append(payload)
    cases=[]
    for drop in [0,40,60,80]:
        q,p,rot=s.pose(drop);cases.append(('crouch_'+str(drop),q,p,rot,['right','left']))
    # Retract the lower neck within its hood opening, then extend the upper
    # chain downward. The old60mm/neck IK posture intersected the native hood.
    # The new60mm crouch reaches about27mm above the plane atX173mm. The
    #75mm trial put the bill tip below ground despite a positive grip site.
    # Full motion path and actual beak/ground contacts are checked separately.
    q,p,rot=s.pose(task['crouch_drop_mm'])
    q.update({n:task[n+'_rad'] for n in ['neck_pitch','neck_mid_pitch','head_pitch']})
    cases.append(('low_reach',q,p,rot,['right','left']))
    for side in ['right','left']:
        q,p,rot=s.pose();q,p,rot=s.bank(side,q,p);cases.append((side+'_single_support',q,p,rot,[side]))
    results=[]
    for variant in [-1,0,1]:
        model,_=s.model(variant)
        for name,q,p,rot,supports in cases:
            for drag in [-2,0,2]:
                result=s.evaluate(name,q,p,rot,supports,variant,drag,model)
                result['joint_limit_violations']=[j['name'] for j in contract['joints'] if not j['range_rad'][0]<=q[j['name']]<=j['range_rad'][1]]
                results.append(result)
    summary=[]
    for j in contract['joints']:
        worst=max(results,key=lambda r:abs(r['joint_torque_nm'][j['name']]))
        t=abs(worst['joint_torque_nm'][j['name']]);limit=j['continuous_design_limit_nm']
        summary.append(dict(joint=j['name'],worst_static_nm=t,continuous_limit_nm=limit,margin_nm=limit-t,case=worst['name'],mass_variant=worst['mass_variant'],drag_n=worst['drag_x_n'],pass_torque=t<=limit))
    report=copy.deepcopy(old);report.update(schema='goose_body_bay_mechanical_si_candidate_v1',nominal_conditional_mass_kg=mass,items=s.items,bodies=bodies,
        removed_ankle_items=[i for i in old['items'] if i['name'] in remove],ankle_fasteners=native['fasteners'],results=results,joint_summary=summary,
        static_cases=len(results),static_contact_feasible=sum(r['static_contact_feasible'] and not r['joint_limit_violations'] for r in results),
        all_static_torques_pass=all(r['pass_torque'] for r in summary),source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        hardware_freeze=False,new_training_release=False,manufacturing_pass=False)
    report['limitations']+=['Full ankle native geometry replaces prior crossmember and mount/structure reserves. Remaining whole-robot issues still apply.']
    old_native_names=set()
    for folder in ['body_bay_frame','body_bay_roll_carriers','body_bay_pitch_forks','body_bay_skins']:
        old_native_names|={p['name'] for p in json.loads((R/'cad/exports'/folder/'manifest.json').read_text())['parts']}
    current_native_names=(old_native_names-remove)|{p['name'] for p in native['parts']}
    report['native_rebuilt_parts']=len(current_native_names)
    report['native_rebuilt_mass_kg']=sum(i['mass_kg'] for i in s.items if i['name'] in current_native_names)
    report['retained_allowance_items']=[copy.deepcopy(i) for i in s.items if any(t in i['name'] for t in ['reserve','allocation','allowance'])]
    report['current_removed_items']=[copy.deepcopy(i) for i in old['items'] if i['name'] in remove]
    report['native_beak_transmission']={k:link[k] for k in ['motor_axis_world_mm','jaw_axis_world_mm','crank_radius_mm','closed_phase_rad','coupler_spacing_mm']}
    report['head_scope']='Native head support/linkage, hollow bills, fixed/steel keyed backbones and axial-retention installation candidates included. Prior printed jaw-heel proxies replaced. Existing80g head_internal_frame_reserve retained for unclosed pad/camera/skin fastening and wiring; no implicit mass saving claimed. Geometric sampling is not strength/manufacturing qualification.'
    report['static_linkage_mass_reduction']='Input rotor and coupler are aggregated at their closed pose for this static screen; runtime model explicitly splits the moving bodies. Beak-opening COM/torque differences require their independent bound.'
    report['grip_world_at_zero_m']=s.grip.tolist()
    report['native_grip_reference']=grip_reference
    report['head_scope']='Native head support/linkage,bill backbones/retention,replaceable carriers/pads and four actual fixed-frame M3clamp stacks are included.80g head internal reserve retained for camera/skin fastening,wiring and unclosed details. Nominal sampled fit is not material,preload,strength or manufacturing qualification.'
    (R/'evidence/body_bay_mechanical_parameters.json').write_text(json.dumps(report,indent=2)+'\n')
    print('mass kg',mass,'contact',report['static_contact_feasible'],'/',len(results),'torque',report['all_static_torques_pass'])
    print(json.dumps([r for r in summary if not r['pass_torque']],indent=2))
    return 0 if report['static_contact_feasible']==len(results) and report['all_static_torques_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
