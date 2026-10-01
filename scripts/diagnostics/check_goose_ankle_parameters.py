"""Replace ankle allowances by real candidate geometry in the whole SI ledger."""
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
    paths=[R/'evidence/body_bay_component_parameters.json',R/'cad/exports/body_bay_ankle_assembly/manifest.json',R/'configs/stage_two_contract.json']
    old,native,contract=[json.loads(p.read_text()) for p in paths]
    remove=set(native['replaces_existing_native_parts'])
    remove|={side+suffix for side in ['right','left'] for suffix in ['_ankle_crossmember','_ankle_roll_mount_reserve','_ankle_pitch_structure_allocation','_ankle_roll_structure_allocation']}
    s=candidate();s.pivots={k:np.array(v) for k,v in old['pivots_world_at_zero_m'].items()}
    s.items=[copy.deepcopy(i) for i in old['items'] if i['name'] not in remove and i['name']!='specified_payload_50g']
    lift=old['rigid_coordinate_lift_m'];by_native={p['name']:p for p in native['parts']}
    for p in native['parts']:
        s.items.append(dict(name=p['name'],body=p['body'],mass_kg=p['mass_kg'],center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),
            inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],relative_uncertainty=.1,basis='native ankle candidate density estimate; bearing uses catalog mass'))
    for p in native['fasteners']:
        m=p['mass_upper_estimate_kg'];anchor=by_native[p['anchor_part']]
        s.items.append(dict(name=p['assembly']+'_ankle_'+p['role']+'_fastener_bound',body=p['body'],mass_kg=m,
            center_m=(np.array(anchor['center_of_mass_world_m'])+[0,0,lift]).tolist(),inertia_at_com_kg_m2=(np.eye(3)*m*.03**2/3).tolist(),
            relative_uncertainty=.1,basis='conservative full steel screw/head/washer upper mass; anchor COM approximation'))
    assert len({i['name'] for i in s.items})==len(s.items)
    mass=sum(i['mass_kg'] for i in s.items)
    bodies=[dict(name=b['name'],**aggregate_rigid_components([i for i in s.items if i['body']==b['name']],s.pivots[b['name']])) for b in contract['bodies']]
    s.grip=np.array(old['grip_world_at_zero_m']);s.tip=np.array(old['tip_world_at_zero_m'])
    s.contact_hulls={k:ConvexHull(np.array(v)) for k,v in old['contact_hulls'].items()};s.contact_center_y_m=old['contact_center_y_m']
    s.items.append(copy.deepcopy(next(i for i in old['items'] if i['name']=='specified_payload_50g')))
    cases=[]
    for drop in [0,40,60,80]:
        q,p,rot=s.pose(drop);cases.append(('crouch_'+str(drop),q,p,rot,['right','left']))
    q,p,rot=s.pose(60,neck=True);cases.append(('low_reach',q,p,rot,['right','left']))
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
    report=copy.deepcopy(old);report.update(schema='goose_body_bay_ankle_si_candidate_v1',nominal_conditional_mass_kg=mass,items=s.items,bodies=bodies,
        removed_ankle_items=[i for i in old['items'] if i['name'] in remove],ankle_fasteners=native['fasteners'],results=results,joint_summary=summary,
        static_cases=len(results),static_contact_feasible=sum(r['static_contact_feasible'] and not r['joint_limit_violations'] for r in results),
        all_static_torques_pass=all(r['pass_torque'] for r in summary),source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        hardware_freeze=False,new_training_release=False,manufacturing_pass=False)
    report['limitations']+=['Full ankle native geometry replaces prior crossmember and mount/structure reserves. Remaining whole-robot issues still apply.']
    (R/'evidence/body_bay_ankle_parameters.json').write_text(json.dumps(report,indent=2)+'\n')
    print('mass kg',mass,'contact',report['static_contact_feasible'],'/',len(results),'torque',report['all_static_torques_pass'])
    print(json.dumps([r for r in summary if not r['pass_torque']],indent=2))
    return 0 if report['static_contact_feasible']==len(results) and report['all_static_torques_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
