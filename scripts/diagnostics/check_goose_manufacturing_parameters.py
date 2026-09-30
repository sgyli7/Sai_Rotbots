"""Recompute whole-robot parameters and statics with actual manufacturing increments.

Only components explicitly replaced here consume old allowances. The remainder
stays visible, so an unfinished frame/electrical design is never massless.
Old training models/contracts are immutable. This emits a conditional SI ledger.
"""
from pathlib import Path
import sys,json,hashlib,copy
import numpy as np
from scipy.spatial import ConvexHull
from scipy.linalg import eigvalsh

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/models'),str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from compare_goose_native_skin_parameters import aggregate


def main():
    files=[R/'configs/stage_two_contract.json',R/'cad/exports/manufacturing_skins/manifest.json',
        R/'cad/exports/pitch_fork_assembly/manifest.json',R/'cad/exports/compliant_foot/manifest.json',
        R/'configs/manufacturing_head_layout.json',R/'hardware/native_pitch_fastener_stacks.json']
    old,skins,forks,feet,head,fasteners=[json.loads(p.read_text()) for p in files]
    s=candidate();original_items=copy.deepcopy(s.items);removed=[]
    old_skin_names={p['name'] for p in skins['parts'] if not p['name'].startswith('goose_head_shell_')}|{'goose_head_shell'}
    fork_names={i['name'] for i in s.items if i['name'] in s.parts and '_fork_' in i['name']}
    foot_names={side+'_'+suffix for side in ['left','right'] for suffix in ['foot_sole','foot_load_plate']}
    lower_joints={a['lower_joint'] for a in forks['assemblies']}
    removable=old_skin_names|fork_names|foot_names|{n+'_mount_reserve' for n in lower_joints}
    removed=[i for i in s.items if i['name'] in removable];s.items=[i for i in s.items if i['name'] not in removable]
    allocated_names={a['upper_joint'] for a in forks['assemblies']}|lower_joints
    consumed=[]
    for i in s.items:
        if i['name']=='camera_module':i['center_m']=(np.array(i['center_m'])+head['optical_module_translation_from_stage_two_m']).tolist()
        if i['name'] in {n+'_structure_allocation' for n in allocated_names} and i['mass_kg']>=.019:
            consumed.append(dict(name=i['name'],consumed_kg=.01,retained_kg=i['mass_kg']-.01))
            ratio=(i['mass_kg']-.01)/i['mass_kg'];i['mass_kg']-=.01
            i['inertia_at_com_kg_m2']=(np.array(i['inertia_at_com_kg_m2'])*ratio).tolist()
            i['basis']='retained10g hardware/lead allowance after native attachment replacement; not selected fastener/harness mass'
    for p in skins['parts']:
        s.items.append(dict(name=p['name'],body='head_roll' if p['name'].startswith('goose_head_shell_') else 'torso',
            mass_kg=p['full_density_mass_kg'],center_m=p['center_of_mass_world_m'],inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],
            relative_uncertainty=.1,basis='actual native skin volume at1270kg/m3; mounting/paint not released'))
    for m in [forks,feet]:
        for p in m['parts']:
            s.items.append(dict(name=p['name'],body=p['body'],mass_kg=p['mass_kg'],center_m=p['center_of_mass_world_m'],
                inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],relative_uncertainty=.1,
                basis='native CAD volume/material density, or explicitly labeled SKF bearing catalog mass; remaining allowances retained'))
    # Conservative selected-stack envelope is added in full. Existing lead,
    # bracket and small-hardware allocations remain: some overlap is intentional
    # until the whole machine is complete, instead of hiding a mass shortfall.
    for row in fasteners['rows']:
        mass=row['mass_upper_estimate_kg']
        s.items.append(dict(name=row['assembly']+'_'+row['role']+'_fastener_mass_bound',body=row['body'],
            mass_kg=mass,center_m=row['center_world_m'],inertia_at_com_kg_m2=(np.eye(3)*mass*.03**2/3).tolist(),
            relative_uncertainty=.1,basis='conservative full-cylinder screw/head/washer envelope at steel7850kg/m3; anchored to actual CAD part COM,30mm isotropic inertia approximation; not catalog weighing'))
    raise_m=feet['robot_rigid_parts_must_be_raised_mm']/1000
    for i in s.items:i['center_m']=(np.array(i['center_m'])+[0,0,raise_m]).tolist()
    for name in s.pivots:s.pivots[name]=s.pivots[name]+[0,0,raise_m]
    s.grip+=np.array([0,0,raise_m]);s.tip+=np.array([0,0,raise_m])
    for f in feet['feet']:
        corners=[]
        for x,y in f['pad_centers_world_xy_mm']:
            for dx in [-2.5,2.5]:
                for dy in [-12.,12.]:corners.append([(x+dx)/1000,(y+dy)/1000])
        s.contact_hulls[f['side']]=ConvexHull(corners)
    parameters=[]
    for b in old['bodies']:
        new=aggregate([i for i in s.items if i['body']==b['name']],s.pivots[b['name']])
        mr=new['mass_kg']/b['mass_kg']-1; dc=np.linalg.norm(np.array(new['com_local_m'])-b['com_local_m'])
        ir=eigvalsh(np.array(new['inertia_at_com_body_kg_m2']),np.array(b['inertia_at_com_body_kg_m2']))
        lo,hi=b['inertia_multiplier_range']
        parameters.append(dict(name=b['name'],**new,mass_change_kg=new['mass_kg']-b['mass_kg'],com_change_m=float(dc),
            generalized_inertia_ratio=ir.tolist(),within_parent_parameter_bounds=bool(abs(mr)<=b['mass_relative_design_uncertainty'] and dc<=b['com_randomization_m'] and np.all(ir>=lo) and np.all(ir<=hi))))
    # The static solver historically uses torso as world-origin frame.
    # World-referenced original item/pivot coordinates remain lifted consistently.
    s.pivots['torso']=np.zeros(3)
    cases=[]
    for drop in [0,40,60,80]:
        q,r,rot=s.pose(drop);cases.append((f'crouch_{drop}',q,r,rot,['right','left']))
    q,r,rot=s.pose(60,neck=True);cases.append(('low_reach',q,r,rot,['right','left']))
    for side in ['right','left']:
        q,r,rot=s.pose();q,r,rot=s.bank(side,q,r);cases.append((side+'_single_support',q,r,rot,[side]))
    mass=sum(i['mass_kg'] for i in s.items)
    s.items.append(dict(name='specified_payload_50g',body='head_roll',mass_kg=.05,center_m=s.grip.tolist(),relative_uncertainty=0))
    results=[]
    for scale in [-1,0,1]:
        model,_=s.model(scale)
        for name,q,root,rot,sides in cases:
            for drag in [-2,0,2]:
                value=s.evaluate(name,q,root,rot,sides,scale,drag,model)
                value['joint_limit_violations']=[j['name'] for j in old['joints'] if not j['range_rad'][0]<=q[j['name']]<=j['range_rad'][1]]
                results.append(value)
    summaries=[]
    for j in old['joints']:
        worst=max(results,key=lambda r:abs(r['joint_torque_nm'][j['name']]))
        torque=abs(worst['joint_torque_nm'][j['name']]);limit=j['continuous_design_limit_nm']
        summaries.append(dict(joint=j['name'],worst_static_nm=torque,old_continuous_limit_nm=limit,margin_nm=limit-torque,
            case=worst['name'],mass_variant=worst['mass_variant'],drag_n=worst['drag_x_n'],within_old_limit=torque<=limit))
    report=dict(schema='goose_native_component_parameters_v1',hardware_freeze=False,new_training_release=False,old_model_modified=False,
        nominal_conditional_mass_kg=mass,parent_mass_kg=old['nominal_robot_mass_kg'],change_kg=mass-old['nominal_robot_mass_kg'],
        mass_basis='conditional native/catalog sum with conservative fastener bounds and retained unclosed hardware allocations; not a finalized nominal hardware mass',
        fastener_mass_upper_estimate_kg=fasteners['mass_upper_estimate_kg'],retained_allowance_overlap_possible=True,
        removed_old_estimates_kg=sum(x['mass_kg'] for x in removed),removed_item_names=[x['name'] for x in removed],
        consumed_allocations=consumed,remaining_allowance_items=[x for x in s.items if 'reserve' in x['name'] or 'allocation' in x['name']],
        rigid_coordinate_lift_m=raise_m,bodies=parameters,items=s.items,contact_hulls={side:s.contact_hulls[side].points[s.contact_hulls[side].vertices].tolist() for side in ['right','left']},
        joint_summary=summaries,static_cases=len(results),static_contact_feasible=sum(x['static_contact_feasible'] for x in results),
        all_static_within_old_continuous_limits=all(x['within_old_limit'] for x in summaries),
        within_old_parameter_bounds=all(b['within_parent_parameter_bounds'] for b in parameters),results=results,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]},
        limitations=['Manufacturing increment only: cross-axis frame, head/shaft, wiring, cooling and power remain incomplete',
            'Flat-contact wrench feasibility is a necessary check; it does not impose measured pad spring pressure or prove rough-terrain gait',
            'Native density and catalog masses are estimates, not weighing; machining tolerances/bolts/coatings have remaining allocations',
            'Changing contact outline, inertia or installation needs a new full model/contract before training; never replace stage-two files',
            'No 18-axis real-hardware, thermal, grasp/drag or walking acceptance is inferred'])
    (R/'evidence/manufacturing_component_parameters.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['nominal_conditional_mass_kg','change_kg','static_cases','static_contact_feasible','all_static_within_old_continuous_limits','within_old_parameter_bounds']},indent=2))
    print(json.dumps([x for x in summaries if not x['within_old_limit']],indent=2))


if __name__=='__main__':main()
