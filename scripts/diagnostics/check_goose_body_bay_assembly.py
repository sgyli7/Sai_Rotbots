"""Same-layout native frame, lower limbs and module-bay rejection screen.

This checks all available lower-body native solids, including old-old pairs.
Skin point inclusion is a rejection test, never a clearance certificate.
Missing head/ankle connections, wires and continuous sweep stay explicit.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, sys
import numpy as np
from build123d import import_step
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_stage_two import candidate
from build_goose_cad import box, cylinder, transform
from sai_agent.goose.morphology import apply_leg_layout
from sai_agent.native_cad import common_solid_volume_mm3 as overlap
from sai_agent.native_cad import boundary_surface_distance_mm


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group();mode.add_argument('--zero-only',action='store_true');mode.add_argument('--task-poses',action='store_true');args=parser.parse_args()
    layout_path=R/'configs/body_bay_layout_candidate.json';layout=json.loads(layout_path.read_text())
    s=candidate();before={n:p.copy() for n,p in s.pivots.items()};apply_leg_layout(s,layout)
    paths=[layout_path];native={};owners={};kinds={};points={};skin_native={}
    for folder in ['body_bay_frame','body_bay_roll_carriers','body_bay_pitch_forks','compliant_foot','body_bay_skins']:
        path=R/'cad/exports'/folder/'manifest.json';paths.append(path)
        manifest=json.loads(path.read_text())
        for part in manifest['parts']:
            for f in part['files'].values():
                assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256'],part['name']
            name=part['name'];shape=import_step(R/part['files']['step']['path'])
            assert shape.is_valid and len(shape.solids())==1,name
            shape=shape.solids()[0];t=part.get('world_from_local_mm')
            if t:shape=transform(shape,np.array(t['rotation']),np.array(t['translation']))
            if folder=='body_bay_skins':
                skin_native[name]=shape
                data=np.load(R/part['files']['npz']['path']);v=data['vertices']*1000;f=data['faces']
                points[name]=np.vstack([v,v[f].mean(axis=1)])
                continue
            body=part['body']
            if folder=='compliant_foot':shape=transform(shape,np.eye(3),(s.pivots[body]-before[body])*1000)
            native[name]=shape;owners[name]=body;kinds[name]='native_solid'
    # Case cylinders stop at the actual stator faces. Keep the documented
    # output socket recess for the intentionally seated pitch adapter pilot.
    roll_rotation=np.array([[0.,1.,0.],[1.,0.,0.],[0.,0.,-1.]])
    for side in ['right','left']:
        for suffix in ['hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch']:
            name=side+'_'+suffix
            if suffix=='hip_yaw':shape=cylinder(26.5,39.2,[0,0,-.5],'z');rotation=np.eye(3)
            else:
                shape=cylinder(27.5,53.5,[0,-1.5,0],'y')-cylinder(9,1.5,[0,25.5,0],'y')
                rotation=roll_rotation if suffix=='hip_roll' else np.eye(3) if side=='left' else np.diag([1.,-1.,-1.])
            name+='_stator_envelope';native[name]=transform(shape,rotation,s.pivots[side+'_'+suffix]*1000)
            owners[name]=s.parents[side+'_'+suffix];kinds[name]='catalog_stator_envelope'
    name='neck_yaw_stator_envelope';native[name]=cylinder(26.5,39.2,s.pivots['neck_yaw']*1000-[0,0,.5],'z')
    owners[name]='torso';kinds[name]='catalog_stator_envelope'
    for name,value in layout['electronics_allowance_boxes_mm'].items():
        native[name]=box(value['size'],value['centre']);owners[name]='torso';kinds[name]='module_allowance_box'
    cases=[('zero',{})]
    if args.task_poses:
        path=R/'evidence/body_bay_component_parameters.json';paths.append(path);ledger=json.loads(path.read_text())
        assert ledger['source_hashes']['robots/Goose_V0.1/configs/body_bay_layout_candidate.json']==hashlib.sha256(layout_path.read_bytes()).hexdigest()
        cases=[(r['name'],r['joint_q_rad']) for r in ledger['results'] if r['mass_variant']==0 and r['drag_x_n']==0]
        for side in ['right','left','both']:
            for yaw in [-np.pi/12,np.pi/12]:
                cases.append((side+'_yaw_15_'+str(yaw),{leg+'_hip_yaw':yaw for leg in (['right','left'] if side=='both' else [side])}))
    elif not args.zero_only:
        for side in ['right','left']:
            for yaw,roll in itertools.product([-.6,0,.6],[-.5,0,.5]):
                if yaw==roll==0:continue
                cases.append((side+'_'+str((yaw,roll)),{side+'_hip_yaw':yaw,side+'_hip_roll':roll}))
        for yaw,roll in itertools.product([-.6,.6],[-.5,.5]):
            for opposite in [False,True]:
                q={side+'_'+axis:value*(-1 if opposite and side=='right' else 1) for side in ['right','left'] for axis,value in [('hip_yaw',yaw),('hip_roll',roll)]}
                cases.append(('bilateral_'+str((yaw,roll,opposite)),q))
    reports=[];cache={};skin_cache={};names=list(native)
    for case,q in cases:
        poses,_=s.fk(q,root_p=s.pivots['torso']);installed={};bounds={};transforms={}
        for name,shape in native.items():
            body=owners[name];p,rot=poses[body];offset=(p-rot@s.pivots[body])*1000
            installed[name]=transform(shape,rot,offset);transforms[name]=(rot,offset)
            bb=installed[name].bounding_box();bounds[name]=(np.array(tuple(bb.min)),np.array(tuple(bb.max)))
        hits=[];exact=0;skin_hits=[]
        for a,b in itertools.combinations(names,2):
            lo=np.maximum(bounds[a][0],bounds[b][0]);hi=np.minimum(bounds[a][1],bounds[b][1])
            if np.any(hi-lo<=1e-6):continue
            key=(a,b)
            if owners[a]==owners[b] and key in cache:volume=cache[key]
            else:
                volume=overlap(installed[a],installed[b]);exact+=1
                if owners[a]==owners[b]:cache[key]=volume
            if volume>.01:hits.append(dict(a=a,b=b,intersection_mm3=volume,basis=[kinds[a],kinds[b]]))
        for name in names:
            # Reuse fixed-to-torso outcomes, but test every moving placement.
            if owners[name]=='torso' and name in skin_cache:
                skin_hits.extend(skin_cache[name]);continue
            own_hits=[];lo,hi=bounds[name]
            for skin,p in points.items():
                near=p[np.all((p>lo+.001)&(p<hi-.001),axis=1)]
                if not len(near):continue
                classifier=BRepClass3d_SolidClassifier(installed[name].wrapped)
                count=0;example=None
                for xyz in near:
                    classifier.Perform(gp_Pnt(*map(float,xyz)),1e-6)
                    if classifier.State()==TopAbs_IN:
                        count+=1
                        if example is None:example=xyz.tolist()
                if count:own_hits.append(dict(part=name,skin=skin,interior_skin_samples=count,example_world_mm=example))
            skin_hits.extend(own_hits)
            if owners[name]=='torso':skin_cache[name]=own_hits
        reports.append(dict(name=case,q_rad=q,exact_native_pair_calls=exact,collisions=hits,skin_rejection_hits=skin_hits,pass_rejection_screen=not(hits or skin_hits)))
        print(case,'solid_hits',len(hits),'skin_hits',len(skin_hits),flush=True)
    # Native surface distance to each module is a separate actual wall check.
    # Zero flags contact/overlap, never proof of usable connector clearance.
    module_gaps=[]
    for name in layout['electronics_allowance_boxes_mm']:
        distances=[]
        for skin,shape in skin_native.items():
            solid_distance=float(native[name].distance_to(shape))
            boundary_distance=boundary_surface_distance_mm(native[name],shape)
            distances.append(dict(skin=skin,solid_distance_mm=solid_distance,boundary_surface_distance_mm=boundary_distance,containment_classification_disagreement=solid_distance<.001 and boundary_distance>1))
        gap=min(r['boundary_surface_distance_mm'] for r in distances)
        module_gaps.append(dict(module=name,native_skin_surface_distance_mm=gap,at_least_1mm_surface_separation=gap>=1,details=distances))
    paths.extend([Path(__file__),ROOT/'src/sai_agent/native_cad.py',ROOT/'src/sai_agent/goose/morphology.py',R/'hardware/stage_three_actuator_mounts.json',ROOT/'scripts/models/build_goose_stage_two.py'])
    report=dict(schema='goose_body_bay_assembly_rejection_v1',sampled_poses=len(reports),passed_poses=sum(r['pass_rejection_screen'] for r in reports),native_lower_body_parts=sum(v=='native_solid' for v in kinds.values()),cases=reports,
        native_module_skin_distances=module_gaps,all_available_solids_no_interference=all(not r['collisions'] for r in reports),skin_rejection_screen_pass=all(not r['skin_rejection_hits'] for r in reports),
        whole_assembly_clearance_pass=False,manufacturing_pass=False,hardware_freeze=False,training_release=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        limitations=['All available lower-body solid pairs checked; missing ankle cross-axis and head/neck root mounts stay unclosed',
            'Skin samples inside exact parts prove a clash; no hits do not certify continuous native clearance',
            'Sampled yaw/roll extreme poses do not establish walking, turning gait or full pitch trajectories',
            'Module boxes retain installation allowances; actual connectors/cables/protection resistor are not released',
            'Solid containment can disagree with positive NURBS boundary distance; this discrepancy remains explicit and is not a whole-interior release',
            'OEM actuator output-bearing capacity and local stress are not certified by native solid validity'])
    output=R/'evidence'/('body_bay_zero_assembly_screen.json' if args.zero_only else 'body_bay_task_assembly_screen.json' if args.task_poses else 'body_bay_assembly_screen.json')
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['sampled_poses','passed_poses','native_lower_body_parts','all_available_solids_no_interference','skin_rejection_screen_pass','native_module_skin_distances']},indent=2),flush=True)
    return 0 if report['passed_poses']==len(reports) and all(r['at_least_1mm_surface_separation'] for r in module_gaps) else 1


if __name__=='__main__':raise SystemExit(main())
