"""Rebuild one explicit SI ledger from the actual body-bay native candidates.

Retain unresolved hardware allocations and historical model files. This is
a conditional parameter set, not manufacture, gait or training acceptance.
"""
from pathlib import Path
import copy,hashlib,json,math,sys
import numpy as np
from scipy.spatial import ConvexHull
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/models'),str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from sai_agent.goose.morphology import apply_leg_layout
from sai_agent.goose.mass_properties import aggregate_rigid_components


def main():
    paths=[R/'configs/body_bay_layout_candidate.json',R/'evidence/manufacturing_component_parameters.json',
        R/'cad/exports/pitch_fork_assembly/manifest.json',R/'hardware/native_pitch_fastener_stacks.json',
        R/'hardware/hip_roll_carrier_fasteners.json',R/'configs/stage_two_contract.json']
    layout,old,old_forks,pitch_screws,roll_screws,contract=[json.loads(p.read_text()) for p in paths]
    native=[]
    for folder in ['body_bay_skins','body_bay_frame','body_bay_roll_carriers','body_bay_pitch_forks']:
        path=R/'cad/exports'/folder/'manifest.json';paths.append(path);value=json.loads(path.read_text())
        assert value['source_hashes']['robots/Goose_V0.1/configs/body_bay_layout_candidate.json']==hashlib.sha256(paths[0].read_bytes()).hexdigest(),folder
        native+=value['parts']
    s=candidate();lift=old['rigid_coordinate_lift_m'];old_pivots={n:p.copy()+[0,0,lift] for n,p in s.pivots.items()}
    apply_leg_layout(s,layout)
    for n in s.pivots:
        if n!='torso':s.pivots[n]+= [0,0,lift]
    # The static solver uses a world-origin torso root, while CAD candidate()
    # retains its architecture datum at Z=.29m. Use one explicit convention.
    s.pivots['torso']=np.zeros(3)
    s.grip +=[0,0,lift];s.tip +=[0,0,lift]
    leg_assemblies={side+'_'+segment for side in ['right','left'] for segment in ['thigh','shin']}
    removed_names={p['name'] for p in old_forks['parts'] if any(p['name'].startswith(a+'_') for a in leg_assemblies)}
    removed_names|={p['name'] for p in native if p['body']=='torso' and p['name'].startswith(('torso_shell_','wing_access_cover_'))}
    removed_names|={'belly_frame','neck_yaw_mount_reserve'}
    removed_names|={side+'_'+axis+'_mount_reserve' for side in ['right','left'] for axis in ['hip_yaw','hip_roll','hip_pitch']}
    leg_screws=[r for r in pitch_screws['rows'] if r['assembly'] in leg_assemblies]
    removed_names|={r['assembly']+'_'+r['role']+'_fastener_mass_bound' for r in leg_screws}
    removed=[i for i in old['items'] if i['name'] in removed_names]
    s.items=[copy.deepcopy(i) for i in old['items'] if i['name'] not in removed_names and i['name']!='specified_payload_50g']
    consumed=[];by_native={p['name']:p for p in native}
    for i in s.items:
        name=i['name'];body=i['body'];anchor=name if name in s.pivots else name.removesuffix('_mount_reserve') if name.endswith('_mount_reserve') else body
        if anchor in s.pivots and anchor!='torso':i['center_m']=(np.array(i['center_m'])+s.pivots[anchor]-old_pivots[anchor]).tolist()
        if name in layout['electronics_allowance_boxes_mm']:
            value=layout['electronics_allowance_boxes_mm'][name];i['center_m']=(np.array(value['centre'])/1000+[0,0,lift]).tolist()
            # Packaging boxes orient the provisional inertial estimate. Actual
            # mounted PCB/component COM still needs measured/vendor detail.
            dims=np.array(value['size'])/1000;m=i['mass_kg']
            i['inertia_at_com_kg_m2']=np.diag(m*(np.sum(dims*dims)-dims*dims)/12).tolist()
            i['basis']+='; same-version installation allocation and box inertia'
        if name in [side+'_'+axis+'_structure_allocation' for side in ['right','left'] for axis in ['hip_yaw','hip_roll']]:
            amount=.01;ratio=(i['mass_kg']-amount)/i['mass_kg'];i['mass_kg']-=amount
            i['inertia_at_com_kg_m2']=(np.array(i['inertia_at_com_kg_m2'])*ratio).tolist()
            consumed.append(dict(name=name,consumed_kg=amount,retained_kg=i['mass_kg']))
    # Body shoulder changes need a coherent button datum. Its mount/hole is
    # still a candidate; this translation does not certify its installation.
    profile=PchipInterpolator(np.array(layout['body_profile_x_cz_ry_rz_mm'])[:,0],np.array(layout['body_profile_x_cz_ry_rz_mm'])[:,1:],axis=0)
    value=profile(-86);button_shift=(value[0]+value[2]-381)/1000
    display_translations={name:[0,0,float(button_shift)] for name in ['button_socket','top_button']}
    for i in s.items:
        if i['name'] in display_translations:i['center_m']=(np.array(i['center_m'])+display_translations[i['name']]).tolist()
    for p in native:
        s.items.append(dict(name=p['name'],body=p['body'],mass_kg=p['mass_kg'],center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),
            inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],relative_uncertainty=.1,basis='same-version native CAD density estimate; unreleased manufacturing candidate'))
    fasteners=[]
    def add_screws(name,body,anchor,thread,length,count,washer,notes):
        d=2.5 if thread=='M2.5' else 3;hd,hh=(5,3) if d==2.5 else (6,4)
        volume=math.pi/4*(d*d*length+hd*hd*hh+((6 if d==2.5 else 7)**2-(d+.2)**2)*washer)
        if 'nut' in notes:volume+=math.pi/4*(6**2-3.2**2)*2.4
        m=volume*7850e-9*count;p=by_native[anchor]
        fasteners.append(dict(name=name,body=body,thread=thread,length_mm=length,count=count,mass_upper_estimate_kg=m,anchor=anchor,notes=notes,released=False))
        s.items.append(dict(name=name,body=body,mass_kg=m,center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),
            inertia_at_com_kg_m2=(np.eye(3)*m*.03**2/3).tolist(),relative_uncertainty=.1,basis='full steel screw/head/washer/nut upper envelope; COM at anchor;30mm isotropic inertia approximation'))
    for row in leg_screws:
        p=by_native[row['anchor_part']];m=row['mass_upper_estimate_kg']
        s.items.append(dict(name=row['assembly']+'_'+row['role']+'_fastener_mass_bound',body=row['body'],mass_kg=m,
            center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),inertia_at_com_kg_m2=(np.eye(3)*m*.03**2/3).tolist(),relative_uncertainty=.1,basis='unchanged same-thickness fork screw stack; relocated actual native anchor; conservative steel mass bound'))
    for row in roll_screws['rows']:
        anchor=row['anchor_part'];m=row['mass_upper_estimate_kg'];p=by_native[anchor]
        s.items.append(dict(name=row['assembly']+'_'+row['role']+'_fastener_bound',body=row['body'],mass_kg=m,center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),
            inertia_at_com_kg_m2=(np.eye(3)*m*.03**2/3).tolist(),relative_uncertainty=.1,basis='same-thickness roll carrier screw stack; current native anchor; conservative steel mass bound'))
    for side in ['right','left']:
        yaw=side+'_hip_yaw';prefix=side+'_'
        add_screws(prefix+'yaw_output_screws',yaw,prefix+'hip_yaw_output_adapter','M2.5',8,3,1.5,'4mm adapter;2.5mm insertion<=3mm')
        add_screws(prefix+'yaw_u_top_screws',yaw,prefix+'hip_yaw_output_adapter','M3',10,3,1,'5.5mm top;3.5mm insertion into4mm adapter')
        add_screws(prefix+'roll_front_screws',yaw,prefix+'hip_yaw_to_roll_u_carrier','M3',8,6,1,'4mm stator ring;3mm insertion<=4mm')
        add_screws(prefix+'yaw_rear_screws','torso','torso_open_chassis_plate','M2.5',8,4,.5,'3mm rear plate;4.5mm insertion<=5mm')
        for k in [0,1]:add_screws(prefix+'battery_post_screw_'+str(k),'torso',prefix+'battery_frame_post_'+str(k),'M3',25,1,1,'3mmplate+14.1mmpost+2.5mmrail+1mmwashers+2.4mmnut;2mm nominal protrusion; actual hardware sweep pending')
    add_screws('neck_yaw_rear_screws','torso','neck_yaw_rear_frame_plate','M2.5',8,4,.5,'3mm rear plate;4.5mm insertion<=5mm')
    for k in range(4):add_screws('neck_frame_through_screw_'+str(k),'torso','neck_frame_spacer_'+str(k),'M3',16,1,1,'3mmplate+4mmspacer+3mmplate+1mmwashers+2.4mmnut;2.6mm nominal protrusion')
    # Do not zero unknown closures/harness/brake hardware merely because the
    # provisional main-protection allocation is too vague to release.
    for name,m,size,centre in [('torso_shell_mount_allocation',.03,[.13,.10,.02],[-.04,0,.32]),('brake_hardware_extra_allocation',.12,[.10,.02,.03],[.075,0,.25])]:
        dims=np.array(size);s.items.append(dict(name=name,body='torso',mass_kg=m,center_m=(np.array(centre)+[0,0,lift]).tolist(),inertia_at_com_kg_m2=np.diag(m*(sum(dims*dims)-dims*dims)/12).tolist(),relative_uncertainty=.5,basis='unclosed hardware reserve, not selected/rated resistor or shell mounting geometry'))
    mass=sum(i['mass_kg'] for i in s.items);assert len({i['name'] for i in s.items})==len(s.items)
    s.items.append(dict(name='specified_payload_50g',body='head_roll',mass_kg=.05,center_m=s.grip.tolist(),inertia_at_com_kg_m2=(np.eye(3)*1e-6).tolist(),relative_uncertainty=0,basis='specified held-object lump, no actual contact/grip proof'))
    for side in ['right','left']:
        shift=s.pivots[side+'_ankle_roll']-old_pivots[side+'_ankle_roll'];s.contact_hulls[side]=ConvexHull(np.array(old['contact_hulls'][side])+shift[:2])
    s.contact_center_y_m={side:float(s.pivots[side+'_ankle_roll'][1]) for side in ['right','left']}
    bodies=[dict(name=b['name'],**aggregate_rigid_components([i for i in s.items if i['body']==b['name'] and i['name']!='specified_payload_50g'],s.pivots[b['name']])) for b in contract['bodies']]
    cases=[]
    for drop in [0,40,60,80]:
        q,p,rot=s.pose(drop);cases.append(('crouch_'+str(drop),q,p,rot,['right','left']))
    q,p,rot=s.pose(60,neck=True);cases.append(('low_reach',q,p,rot,['right','left']))
    for side in ['right','left']:
        q,p,rot=s.pose();q,p,rot=s.bank(side,q,p);cases.append((side+'_single_support',q,p,rot,[side]))
    results=[]
    for scale in [-1,0,1]:
        model,_=s.model(scale)
        for name,q,p,rot,support in cases:
            for drag in [-2,0,2]:
                value=s.evaluate(name,q,p,rot,support,scale,drag,model)
                value['joint_limit_violations']=[j['name'] for j in contract['joints'] if not j['range_rad'][0]<=q[j['name']]<=j['range_rad'][1]]
                results.append(value)
    summary=[]
    for j in contract['joints']:
        worst=max(results,key=lambda x:abs(x['joint_torque_nm'][j['name']]))
        torque=abs(worst['joint_torque_nm'][j['name']]);limit=j['continuous_design_limit_nm']
        summary.append(dict(joint=j['name'],worst_static_nm=torque,continuous_limit_nm=limit,margin_nm=limit-torque,case=worst['name'],mass_variant=worst['mass_variant'],drag_n=worst['drag_x_n'],pass_torque=torque<=limit))
    report=dict(schema='goose_body_bay_si_candidate_v1',nominal_conditional_mass_kg=mass,rigid_coordinate_lift_m=lift,pivots_world_at_zero_m={n:p.tolist() for n,p in s.pivots.items()},
        grip_world_at_zero_m=s.grip.tolist(),tip_world_at_zero_m=s.tip.tolist(),bodies=bodies,items=s.items,
        contact_hulls={side:s.contact_hulls[side].points[s.contact_hulls[side].vertices].tolist() for side in ['right','left']},contact_center_y_m=s.contact_center_y_m,
        torso_display_part_translations_m=display_translations,removed_items=removed,consumed_allocations=consumed,new_frame_fasteners=fasteners,
        native_rebuilt_parts=len(native),native_rebuilt_mass_kg=sum(p['mass_kg'] for p in native),retained_allowance_items=[i for i in s.items if 'reserve' in i['name'] or 'allocation' in i['name']],
        static_cases=len(results),static_contact_feasible=sum(r['static_contact_feasible'] and not r['joint_limit_violations'] for r in results),all_static_torques_pass=all(r['pass_torque'] for r in summary),joint_summary=summary,results=results,
        hardware_freeze=False,manufacturing_pass=False,new_training_release=False,old_models_modified=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__),ROOT/'src/sai_agent/goose/mass_properties.py',ROOT/'src/sai_agent/goose/morphology.py',ROOT/'scripts/diagnostics/screen_goose_system_loads.py']},
        limitations=['Actual native body/frame/new leg forks replace explicit old components; remaining hardware reserves stay nonzero',
            'Main protection is not rated/packaged;120g additional brake hardware is an allocation, not a chosen part',
            'OEM yaw bearing ratings absent, global assembly task/extreme collisions and fastener/wiring sweeps remain gates',
            '63static cases are necessary equilibrium checks, not walking/turning/grasp/drag or thermal acceptance',
            'Native CAD inertia is actual candidate geometry; catalogue motor/PCB inertia and fastener COM remain approximations',
            'No new trainable full model or final appearance release; stage-two policy compatibility is not assumed'])
    (R/'evidence/body_bay_component_parameters.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['nominal_conditional_mass_kg','native_rebuilt_parts','static_cases','static_contact_feasible','all_static_torques_pass']},indent=2),flush=True)
    print(json.dumps([r for r in summary if not r['pass_torque']],indent=2),flush=True)
    return 0 if report['static_contact_feasible']==len(results) and report['all_static_torques_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
