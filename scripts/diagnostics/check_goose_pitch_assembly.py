"""Re-read actual native fork parts and check installed static/swept overlap.

No whole-robot release is inferred. Contacts at mating faces are allowed;
positive-volume interference between different parts is not.
"""
from pathlib import Path
import sys, json, hashlib,itertools
import numpy as np
from scipy.spatial.transform import Rotation
from build123d import import_step

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/models'),str(ROOT/'scripts/cad')]
from build_goose_stage_two import candidate
from build_goose_cad import transform


def overlap(a,b):
    aa=a.bounding_box();bb=b.bounding_box()
    if not np.all(np.minimum(tuple(aa.max),tuple(bb.max))-np.maximum(tuple(aa.min),tuple(bb.min))>1e-6):return 0.
    q=a&b
    return sum(x.volume for x in q.solids()) if q is not None else 0.


def main():
    path=R/'cad/exports/pitch_fork_assembly/manifest.json';m=json.loads(path.read_text());s=candidate()
    originals={};records={};integrity=[]
    for p in m['parts']:
        for meta in p['files'].values():
            f=R/meta['path'];assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256'],f
        t=p['world_from_local_mm'];shape=import_step(R/p['files']['step']['path'])
        if not shape.is_valid or len(shape.solids())!=1:raise ValueError(p['name'])
        originals[p['name']]=transform(shape,np.array(t['rotation']),np.array(t['translation']))
        records[p['name']]=p
    for source,sha in m['source_hashes'].items():assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==sha,source
    cases=[('zero',{})]
    # Separate physical link angle from parent/child common transform.
    for n in ['neck_mid_pitch','right_knee_pitch','left_knee_pitch']:
        for angle in [-.2,.5,1.0,1.4]:
            if n.startswith('right'):angle=-angle
            cases.append((n+'_'+str(angle),{n:angle}))
    reports=[]
    for name,q in cases:
        poses,_=s.fk(q,root_p=s.pivots['torso'])
        shapes={}
        for part,shape in originals.items():
            b=records[part]['body'];pos,rot=poses[b]
            shapes[part]=transform(shape,rot,(pos-rot@s.pivots[b])*1000)
        collisions=[];tested=0
        for a,b in itertools.combinations(shapes,2):
            # Geometries on opposite limbs cannot approach in these local tests.
            if a.startswith('left_') and b.startswith('right_') or a.startswith('right_') and b.startswith('left_'):continue
            v=overlap(shapes[a],shapes[b]);tested+=1
            if v>.01:collisions.append(dict(a=a,b=b,intersection_mm3=v))
        reports.append(dict(name=name,q_rad=q,tested_pairs=tested,collisions=collisions,pass_no_interference=not collisions))
        print(name,'collisions',len(collisions),flush=True)
    # Check native tap/clearance holes by probes at real STEP interface coords.
    hole_tests=[]
    from build_goose_cad import cylinder
    for p in m['parts']:
        for f in p.get('features',[]):
            for center in f['centers_mm']:
                shape=import_step(R/p['files']['step']['path']);probe=cylinder(f['diameter_mm']*.499,20,center,'y')
                v=overlap(shape,probe);hole_tests.append(dict(part=p['name'],center_mm=center,overlap_mm3=v,pass_clear=v<.01))
    report=dict(schema='goose_native_pitch_assembly_gate_v1',manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        parts=len(records),case_count=len(reports),cases=reports,tap_drill_probes=hole_tests,
        partial_interference_pass=all(x['pass_no_interference'] for x in reports) and all(x['pass_clear'] for x in hole_tests),
        full_assembly_pass=False,manufacturing_pass=False,
        scope='six native parallel-axis links only; no vendor motor solids, cross-axis brackets, cables, torso, head shell, feet or fastener solids',
        limitations=['Sampled joint poses, not a continuous proof','Positive-volume threshold0.01mm3 screens CAD tolerance crumbs, not a machining tolerance guarantee','Bearing installation envelope does not encode balls/races/actual preload'])
    (R/'evidence/manufacturing_pitch_assembly.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['parts','case_count','partial_interference_pass','full_assembly_pass']},indent=2))
    return 0 if report['partial_interference_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
