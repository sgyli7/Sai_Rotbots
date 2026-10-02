"""Native ankle installation and bounded pose rejection screen.

Check all pairs involving a new ankle solid against the existing lower-body
assembly and catalog stators. Intended mating faces may touch, not overlap.
"""
from pathlib import Path
import hashlib, itertools, json, sys
import numpy as np
from build123d import import_step
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_stage_two import candidate
from build_goose_cad import cylinder, transform
from sai_agent.goose.morphology import apply_leg_layout
from sai_agent.native_cad import common_solid_volume_mm3 as overlap


def main():
    layout=R/'configs/body_bay_layout_candidate.json';s=candidate();old={k:v.copy() for k,v in s.pivots.items()}
    apply_leg_layout(s,json.loads(layout.read_text()))
    ankle_path=R/'cad/exports/body_bay_ankle_assembly/manifest.json';ankle=json.loads(ankle_path.read_text())
    replaced=set(ankle['replaces_existing_native_parts']);new={p['name'] for p in ankle['parts']}
    shoes=json.loads((R/'cad/exports/hollow_shoe_covers/manifest.json').read_text());new|={p['name'] for p in shoes['parts']}
    shapes={};owners={};paths=[layout,ankle_path];kinds={}
    for folder in ['body_bay_frame','body_bay_roll_carriers','body_bay_pitch_forks','compliant_foot','body_bay_ankle_assembly','hollow_shoe_covers']:
        path=R/'cad/exports'/folder/'manifest.json';paths.append(path)
        for p in json.loads(path.read_text())['parts']:
            if p['name'] in replaced:continue
            for f in p['files'].values():assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256']
            shape=import_step(R/p['files']['step']['path']).solids()[0]
            t=p.get('world_from_local_mm')
            if t:shape=transform(shape,np.array(t['rotation']),t['translation'])
            if folder=='compliant_foot':shape=transform(shape,np.eye(3),(s.pivots[p['body']]-old[p['body']])*1000)
            shapes[p['name']]=shape;owners[p['name']]=p['body'];kinds[p['name']]='native_solid'
    roll_rotation=np.array([[0.,1.,0.],[1.,0.,0.],[0.,0.,-1.]])
    for side in ['right','left']:
        for suffix in ['hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch','ankle_roll']:
            joint=side+'_'+suffix
            if suffix=='hip_yaw':shape=cylinder(26.5,39.2,[0,0,-.5],'z');rot=np.eye(3)
            elif suffix=='ankle_roll':shape=cylinder(26.5,44.2,[Q:=float(s.pivots[joint][0]*1000-.5),s.pivots[joint][1]*1000,s.pivots[joint][2]*1000],'x');rot=None
            else:
                shape=cylinder(27.5,53.5,[0,-1.5,0],'y')-cylinder(9,1.5,[0,25.5,0],'y')
                rot=roll_rotation if suffix=='hip_roll' else np.eye(3) if side=='left' else np.diag([1.,-1.,-1.])
            if rot is not None:shape=transform(shape,rot,s.pivots[joint]*1000)
            name=joint+'_stator_envelope';shapes[name]=shape;owners[name]=s.parents[joint];kinds[name]='catalog_stator_envelope'
    ledger_path=R/'evidence/body_bay_component_parameters.json';paths.append(ledger_path);ledger=json.loads(ledger_path.read_text())
    cases=[(r['name'],r['joint_q_rad']) for r in ledger['results'] if r['mass_variant']==0 and r['drag_x_n']==0]
    cases+=[('zero',{})]
    for side in ['right','left']:
        for pitch,roll in itertools.product([-.35,0,.35],[-.35,0,.35]):
            if pitch==roll==0:continue
            cases.append((side+'_ankle_'+str((pitch,roll)),{side+'_ankle_pitch':pitch,side+'_ankle_roll':roll}))
    names=list(shapes);cache={};reports=[]
    for name,q in cases:
        poses,_=s.fk(q,root_p=s.pivots['torso']);installed={};bounds={}
        for n,shape in shapes.items():
            p,rot=poses[owners[n]];installed[n]=transform(shape,rot,(p-rot@s.pivots[owners[n]])*1000)
            bb=installed[n].bounding_box();bounds[n]=(np.array(tuple(bb.min)),np.array(tuple(bb.max)))
        hits=[];count=0
        for a,b in itertools.combinations(names,2):
            if a not in new and b not in new:continue
            lo=np.maximum(bounds[a][0],bounds[b][0]);hi=np.minimum(bounds[a][1],bounds[b][1])
            if np.any(hi-lo<=1e-6):continue
            key=(a,b)
            if owners[a]==owners[b] and key in cache:v=cache[key]
            else:
                v=overlap(installed[a],installed[b]);count+=1
                if owners[a]==owners[b]:cache[key]=v
            if v>.01:hits.append(dict(a=a,b=b,intersection_mm3=v,owners=[owners[a],owners[b]]))
        reports.append(dict(name=name,q_rad=q,collisions=hits,exact_native_pair_calls=count,pass_rejection_screen=not hits))
        print(name,'hits',len(hits),flush=True)
    report=dict(schema='goose_native_ankle_shoe_screen_v1',parts=len(new),checked_assembly_parts=len(shapes),poses=len(reports),passed_poses=sum(r['pass_rejection_screen'] for r in reports),
        cases=reports,replaced_parts=sorted(replaced),full_assembly_pass=False,manufacturing_pass=False,
        limitations=['Pairs involving new ankle native solids only; preceding full lower-body rejection evidence remains separate.',
            'Catalog motor stator cylinders omit real connectors; screw/head/washer/wire sweep is not represented.',
            'Bounded sampled poses do not establish continuous range, strength, dynamic gait or OEM bearing capacity.',
            'Native open-bottom shoe covers are checked; attachment fasteners and minimum wall thickness remain separate gates.'],
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]})
    (R/'evidence/mechanical_ankle_shoe_screen.json').write_text(json.dumps(report,indent=2)+'\n')
    print('passed',report['passed_poses'],'/',report['poses'],flush=True)
    return 0 if report['passed_poses']==report['poses'] else 1

if __name__=='__main__':raise SystemExit(main())
