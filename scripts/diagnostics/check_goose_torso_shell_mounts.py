"""Finite incremental shell-mount fit and fresh whole-body static screen.

All timeouts remain unknown. As-printed heat-insert and nominal thread
interference are measured explicitly, never generic collision exclusions.
"""
from pathlib import Path
import copy
import argparse
import hashlib
import itertools
import json
import sys

import numpy as np
import trimesh
from build123d import import_brep
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models'),str(ROOT/'scripts/diagnostics')]
from build_goose_cad import box,cylinder,transform
from build_goose_stage_two import candidate
from build_goose_integrated_hardware_candidate import opposed_clamp_result
from check_goose_grip_cassettes import bounded_common


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(shape):
    b=shape.bounding_box(optimal=False)
    return np.array(tuple(b.min)),np.array(tuple(b.max))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--zero-only',action='store_true');args=parser.parse_args()
    paths=[R/p for p in ['cad/exports/torso_shell_mounts/manifest.json','evidence/torso_shell_mount_parameters.json',
        'cad/source/camera_closure_fixture/assembly_scene.json','evidence/camera_head_closure_parameters.json',
        'evidence/integrated_hardware_parameters.json','evidence/body_bay_mechanical_parameters.json',
        'configs/mechanical_physics_contract.json','configs/body_bay_layout_candidate.json','configs/torso_shell_mounts.json']]
    kit,parameters,scene,old,static_source,default,contract,layout,cfg=[json.loads(p.read_text()) for p in paths]
    for value in [kit,parameters]:
        for relative,digest in value['source_hashes'].items():
            if sha(ROOT/relative)!=digest:raise ValueError(('Changed source',relative))
    own,delta,quad={}, {}, []
    shell_pairs={a['mounted_shell']:a for a in kit['interfaces']}
    owners={p['name']:p['body'] for p in old['items']}
    for p in kit['parts']:
        for rec in p['files'].values():
            if sha(R/rec['path'])!=rec['sha256']:raise ValueError('Changed output')
        shape=import_brep(R/p['files']['brep']['path'])
        if not shape.is_valid or len(shape.solids())!=1:raise ValueError('Invalid new native part')
        own[p['name']]=shape
        v,f=[np.load(R/p['files']['npz']['path'])[k] for k in ['vertices','faces']]
        if f.shape[1]!=4:raise ValueError('Non-quad source')
        mesh=trimesh.Trimesh(v,np.concatenate([f[:,[0,1,2]],f[:,[0,2,3]]]),process=False)
        error=abs(mesh.volume*1e9/p['volume_mm3']-1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or error>.005:raise ValueError('Quad closure mismatch')
        quad.append(dict(name=p['name'],faces=len(f),closed=True,all_quad=True,volume_relative_error=error))
        if p['name'] in shell_pairs:
            anchor=next(a for a in cfg['anchors'] if a['name']==shell_pairs[p['name']]['name'])
            old_shell=import_brep(R/anchor['source_shell'])
            interface=shell_pairs[p['name']];rot=np.array(interface['rotation_from_insert_z']);entry=np.array(interface['insert_entry_mm'])
            height=cfg['boss_inside_entry_depth_mm']-cfg['boss_outer_end_depth_mm']
            boss=transform(cylinder(cfg['boss_radius_mm'],height,[0,0,height/2]),rot,entry)
            pilot=transform(cylinder(cfg['insert_pilot_diameter_mm']/2,cfg['insert_pilot_depth_mm']+.02,[0,0,cfg['insert_pilot_depth_mm']/2-.01]),rot,entry)
            # Added(S union B minus H,S) = (B minus S) minus H. Avoid the
            # unstable full-shell Boolean difference of coincident NURBS faces.
            delta[p['name']]=(boss-old_shell)-pilot
            if not delta[p['name']].is_valid or len(delta[p['name']].solids())!=1:
                raise ValueError('Invalid local positive shell delta')
    threads={frozenset([t['screw'],t['tapped_part']]):t['expected_thread_overlap_mm3'] for t in kit['nominal_thread_contacts']}
    presses={frozenset([a['mounted_shell'],a['insert']]):a['intentional_as_printed_heat_insert_interference_mm3'] for a in kit['interfaces']}
    queries,failures,unknown,thread_records,press_records=[],[],[],[],[]
    retained_thread_checks={}
    def common(a,b,label):
        lo1,hi1=bounds(a);lo2,hi2=bounds(b)
        if np.any(np.minimum(hi1,hi2)-np.maximum(lo1,lo2)<=1e-6):return dict(volume_mm3=0.,method='conservative native bounds disjoint')
        result=bounded_common(a,b,3.)
        queries.append(dict(pair=label,timebox_seconds=3.,**result))
        if result.get('error')=='NATIVE_PAIR_TIMEBOX':
            result=bounded_common(a,b,30.)
            queries.append(dict(pair=label,timebox_seconds=30.,**result))
        return result
    for a,b in itertools.combinations(own,2):
        # Each shell's old portions remain in the target inventory below.
        # Positive native material deltas test newly created shell collisions.
        result=common(delta.get(a,own[a]),delta.get(b,own[b]),['own',a,b])
        expected=threads.get(frozenset([a,b]),presses.get(frozenset([a,b])))
        record=dict(a=a,b=b,**result)
        if 'error' in result:unknown.append(record)
        elif expected is not None:
            passed=abs(result['volume_mm3']-expected)<.05
            record.update(expected_mm3=expected,pass_nominal_contact=passed)
            (thread_records if frozenset([a,b]) in threads else press_records).append(record)
            if not passed:failures.append(record)
        elif result['volume_mm3']>.01:failures.append(record)
    # Preserve original shell surfaces as obstacles: a delta screen cannot
    # conceal a new bracket entering an unchanged part of its own old skin.
    targets,kinds={},{}
    native_placements={};native_sources={}
    for manifest_path in sorted((R/'cad/exports').glob('*/manifest.json')):
        value=json.loads(manifest_path.read_text())
        for part in value.get('parts',[]):
            files=part.get('files',{})
            if 'npz' in files and 'brep' in files:
                native_sources[files['npz']['path']]=(files['brep'],manifest_path)
            if 'npz' in files and part.get('world_from_local_mm'):
                key=files['npz']['path']
                if key in native_placements and native_placements[key][0]!=part['world_from_local_mm']:
                    raise ValueError(('Conflicting native placements',key))
                native_placements[key]=(part['world_from_local_mm'],manifest_path)
    for p in scene['parts']:
        name=p['name']
        if p.get('geometry_npz') and sha(R/p['geometry_npz'])!=p['source_sha256']:
            raise ValueError(('Changed frozen scene geometry',name))
        if name in kit['replaces_existing_parts'] and name not in [a['replaces_shell'] for a in cfg['anchors']]:continue
        path=R/p['geometry_npz'].replace('_quad.npz','.brep') if p.get('geometry_npz') else None
        if path and path.exists():
            record=native_sources.get(p['geometry_npz'])
            if record:
                brep,source=record
                if brep['path']!=str(path.relative_to(R)) or sha(path)!=brep['sha256']:
                    raise ValueError(('Changed declared native source',name))
                paths.append(source)
            else:raise ValueError(('Native source has no manifest lineage',name))
            shape=import_brep(path);kind='native_current_geometry'
            placement=native_placements.get(p['geometry_npz'])
            if placement:
                t,source=placement;shape=transform(shape,np.array(t['rotation']),np.array(t['translation']));paths.append(source)
            if p.get('candidate_translation_m'):
                shape=transform(shape,np.eye(3),np.array(p['candidate_translation_m'])*1000)
            if not shape.is_valid or not shape.solids():raise ValueError(('Invalid current native source',name))
            paths.append(path)
        else:
            if p.get('geometry_npz'):
                data=np.load(R/p['geometry_npz']);v=data['vertices'];paths.append(R/p['geometry_npz'])
            else:v=np.array(p['vertices'])
            lo,hi=v.min(0)*1000,v.max(0)*1000
            shape=box(hi-lo+.02,(hi+lo)/2)
            kind='complete_display_geometry_bounds_NOT_actual_bought_CAD'
        targets[name]=shape;kinds[name]=kind
        owners[name]=p.get('body',owners.get(name))
        if owners[name] is None:raise ValueError(('Missing physical owner',name))
    for name,allocation in layout['electronics_allowance_boxes_mm'].items():
        targets['allocation_'+name]=box(allocation['size'],allocation['centre'])
        owners['allocation_'+name]='torso';kinds['allocation_'+name]='retained_module_allowance_NOT_bought_or_connector_qualification'
    system=candidate();system.pivots={k:np.array(v) for k,v in parameters['pivots_world_at_zero_m'].items()}
    cases=[('zero',{})]+[(r['name'],r['joint_q_rad']) for r in static_source['static_results'] if r['mass_variant']==0 and r['drag_x_n']==0]
    cases += [(side+'_'+str((yaw,roll)),{side+'_hip_yaw':yaw,side+'_hip_roll':roll})
        for side in ['right','left'] for yaw,roll in itertools.product([-.6,.6],[-.5,.5])]
    cases += [('neck_yaw_'+str(yaw),{'neck_yaw':yaw}) for yaw in [-.6,.6]]
    if args.zero_only:cases=cases[:1]
    lift=np.array([0.,0.,parameters['rigid_coordinate_lift_m']])
    cache,reports={},[]
    for label,q in cases:
        fk,_=system.fk(q,root_p=system.pivots['torso']);hits,unresolved=[],[]
        for a,shape in own.items():
            for b,other in targets.items():
                owner=owners[b];key=(a,b,'fixed' if owner=='torso' else label)
                if key not in cache:
                    physical_owner=owner
                    if owner in {'beak_input_rotor','beak_coupler_link'}:
                        if abs(q.get('beak_hinge',0.))>1e-12:
                            raise ValueError('This finite screen uses the explicit closed-jaw19-body reduction')
                        physical_owner='head_roll'
                    pos,rot=fk[physical_owner]
                    moved=transform(other,rot,(pos-lift-rot@(system.pivots[physical_owner]-lift))*1000)
                    cache[key]=common(delta.get(a,shape),moved,[label,a,b])
                result=cache[key];expected=threads.get(frozenset([a,b]))
                row=dict(a=a,b=b,target_kind=kinds[b],**result)
                if 'error' in result:unresolved.append(row)
                elif expected is not None:
                    passed=abs(result['volume_mm3']-expected)<.05
                    retained_thread_checks[(a,b)]=dict(row,expected_mm3=expected,pass_nominal_contact=passed)
                    if not passed:hits.append(dict(row,expected_mm3=expected))
                elif result['volume_mm3']>.01:
                    if kinds[b]=='native_current_geometry':hits.append(row)
                    else:unresolved.append(dict(row,reason='Conservative allocation/display bound overlap needs actual geometry'))
        reports.append(dict(name=label,collisions=hits,unresolved=unresolved,pass_incremental_fit=not hits and not unresolved))
        print('SHELL FIT',label,len(hits),'hits',len(unresolved),'unknown',flush=True)
    system.items=copy.deepcopy(parameters['items']);system.contact_hulls={k:ConvexHull(np.array(v)) for k,v in default['contact_hulls'].items()}
    system.contact_center_y_m=default['contact_center_y_m'];system.tip=np.array(default['tip_world_at_zero_m'])
    payload=copy.deepcopy(next(p for p in default['items'] if p['name']=='specified_payload_50g'));system.items.append(payload)
    static={}
    for label,point,force in [('front20n',static_source['front_grip_reference_world_m'],20.),('middle50n',static_source['middle_grip_reference_world_m'],50.)]:
        system.grip=np.array(point);payload['center_m']=(system.grip+np.array(default['native_grip_reference']['payload_reference_offset_m'])).tolist();results=[]
        for variant in [-1,0,1]:
            model,_=system.model(variant)
            for row in static_source['static_results']:
                if row['mass_variant']!=variant:continue
                w,x,y,z=row['root_quaternion_wxyz'];support=['right'] if row['name']=='right_single_support' else ['left'] if row['name']=='left_single_support' else ['right','left']
                value=system.evaluate(row['name'],row['joint_q_rad'],np.array(row['root_position_m']),Rotation.from_quat([x,y,z,w]).as_matrix(),support,variant,row['drag_x_n'],model)
                if force!=50.:value=opposed_clamp_result(system,model,value,force)
                results.append(value)
        limits={p['name']:p['continuous_design_limit_nm'] for p in contract['joints']}
        joint_summary=[dict(joint=j,worst_nm=max(abs(r['joint_torque_nm'][j]) for r in results),limit_nm=limit,
            margin_nm=limit-max(abs(r['joint_torque_nm'][j]) for r in results)) for j,limit in limits.items()]
        static[label]=dict(cases=len(results),results=results,joint_summary=joint_summary,
            contact_feasible=sum(r['static_contact_feasible'] for r in results),all_static_torques_pass=all(j['margin_nm']>=0 for j in joint_summary))
    report=dict(schema='goose_torso_shell_mount_fit_v1',own_native_parts=len(own),quads=quad,
        own_pair_failures=failures,own_pair_unresolved=unknown,nominal_threads=thread_records,as_printed_heat_insert_interference=press_records,
        retained_frame_nominal_threads=list(retained_thread_checks.values()),
        finite_cases=reports,actual_native_queries=queries,target_inventory=[dict(name=k,kind=kinds[k],body=owners[k]) for k in targets],
        static_screens=static,incremental_geometry_pass=not failures and not unknown and all(r['pass_incremental_fit'] for r in reports),
        same_source_static_pass=all(s['all_static_torques_pass'] and s['contact_feasible']==s['cases'] for s in static.values()),
        manufacturing_release=False,full_assembly_pass=False,training_release=False,final_appearance_pass=False,
        limitations=['Positive native shell deltas plus retained original skin obstacles; not whole-old-assembly acceptance.',
            'Finite closed-jaw poses only; input rotor/coupler use the explicit closed-pose head transform, all geometry retained.',
            'Complete display/module bounds do not qualify actual connectors, electronics or purchased versions.',
            'Heat-insert interference is as-printed only; print/pullout, preload, strength, seams and doors remain gates.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__),ROOT/'scripts/cad/build_goose_cad.py',ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py',ROOT/'scripts/models/build_goose_stage_two.py',ROOT/'scripts/models/build_goose_integrated_hardware_candidate.py']})
    report['zero_only']=args.zero_only
    name='torso_shell_mount_zero_fit.json' if args.zero_only else 'torso_shell_mount_fit.json'
    (R/'evidence'/name).write_text(json.dumps(report,indent=2)+'\n')
    print('SHELL SUMMARY',report['incremental_geometry_pass'],'static',report['same_source_static_pass'],flush=True)
    if not report['incremental_geometry_pass'] or not report['same_source_static_pass']:raise SystemExit(1)


if __name__=='__main__':main()
