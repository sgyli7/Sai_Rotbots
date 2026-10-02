"""Native candidate head fit; all new-pair intersections remain explicit."""
from pathlib import Path
import hashlib,itertools,json,sys
import numpy as np
from build123d import import_step
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_stage_two import candidate
from build_goose_cad import cylinder,transform
from sai_agent.native_cad import common_solid_volume_mm3 as overlap


def main():
    paths=[R/'cad/exports/head_load_path/manifest.json',R/'cad/exports/head_linkage_clearance_skins/manifest.json',
        R/'cad/exports/body_bay_pitch_forks/manifest.json',R/'evidence/body_bay_mechanical_parameters.json']
    head,skin,forks,ledger=[json.loads(p.read_text()) for p in paths]
    shapes={};owners={};new={p['name'] for p in head['parts']}
    for m in [head,skin,forks]:
        for p in m['parts']:
            if m is skin and not p['name'].startswith('goose_head_shell_'):continue
            if m is forks and not p['name'].startswith('upper_neck_'):continue
            for f in p['files'].values():assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256']
            shape=import_step(R/p['files']['step']['path']).solids()[0]
            t=p.get('world_from_local_mm')
            if t:shape=transform(shape,np.array(t['rotation']),t['translation'])
            shapes[p['name']]=shape;owners[p['name']]=p.get('body','head_roll')
    shapes['head_pitch_stator']=cylinder(26.5,44.2,[42,-.5,605],'y');owners['head_pitch_stator']='neck_mid_pitch'
    s=candidate();s.pivots={k:np.array(v)-([0,0,ledger['rigid_coordinate_lift_m']] if k!='torso' else 0) for k,v in ledger['pivots_world_at_zero_m'].items()}
    cases=[('zero',{})]+[(r['name'],r['joint_q_rad']) for r in ledger['results'] if r['mass_variant']==0 and r['drag_x_n']==0]
    cases+=[('head_roll_'+str(v),{'head_roll':v}) for v in [-.6,-.35,.35,.6]]
    records=[];cache={}
    for name,q in cases:
        poses,_=s.fk(q,root_p=s.pivots['torso']);moved={};bounds={}
        for n,shape in shapes.items():
            p,rot=poses[owners[n]];moved[n]=transform(shape,rot,(p-rot@s.pivots[owners[n]])*1000)
            bb=moved[n].bounding_box();bounds[n]=(np.array(tuple(bb.min)),np.array(tuple(bb.max)))
        hits=[]
        for a,b in itertools.combinations(shapes,2):
            if a not in new and b not in new:continue
            if np.any(np.minimum(bounds[a][1],bounds[b][1])-np.maximum(bounds[a][0],bounds[b][0])<=1e-6):continue
            key=(a,b)
            if owners[a]==owners[b] and key in cache:v=cache[key]
            else:
                v=overlap(moved[a],moved[b])
                if owners[a]==owners[b]:cache[key]=v
            if v>.01:hits.append(dict(a=a,b=b,intersection_mm3=v,owners=[owners[a],owners[b]]))
        records.append(dict(name=name,q_rad=q,collisions=hits,pass_rejection_screen=not hits));print('HEAD',name,'hits',len(hits),flush=True)
    out=dict(schema='goose_head_load_path_fit_v1',candidate_parts=len(new),checked_parts=len(shapes),cases=records,
        passed_poses=sum(r['pass_rejection_screen'] for r in records),pose_count=len(records),integrated=True,
        manufacturing_pass=False,whole_head_release=False,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        limitations=['Actual mating plugs, screw heads and upper/lower bill structural connections are not modeled.',
            'Native head frame and linkage are integrated in the mechanical candidate; this head-only screen does not cover the torso or release the bill load path.',
            'Sampled fit cannot release screw strength, bearing moment, thermal duty or complete mechanisms.'])
    (R/'evidence/head_load_path_fit.json').write_text(json.dumps(out,indent=2)+'\n')
    return 0 if out['passed_poses']==out['pose_count'] else 1

if __name__=='__main__':raise SystemExit(main())
