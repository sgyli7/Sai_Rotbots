"""Bounded M3 stack interference against the actual candidate head assembly."""
from pathlib import Path
import hashlib
import itertools
import json
import sys
import time

import numpy as np
from build123d import import_brep, import_step
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import transform
from check_goose_grip_cassettes import bounded_common
from sai_agent.goose.native_linkage import INPUT_PARTS, COUPLER_PARTS
from sai_agent.native_csg import contained_in_one_void


def main():
    started=time.monotonic()
    folders=['head_load_path','beak_native_linkage','bill_backbones','jaw_retention',
             'grip_cassettes','bill_mount_fasteners']
    paths=[R/'cad/exports'/folder/'manifest.json' for folder in folders]
    manifests=[json.loads(p.read_text()) for p in paths]
    replacement_file=R/'configs/mechanical_native_replacements.json'
    additional=json.loads(replacement_file.read_text())['additional_replaces_by_folder']
    shapes,groups={},{}
    for folder,manifest in zip(folders,manifests):
        for name in manifest.get('replaces_existing_parts',[])+additional.get(folder,[]):
            shapes.pop(name,None);groups.pop(name,None)
        for part in manifest['parts']:
            file=R/part['files']['step']['path']
            if hashlib.sha256(file.read_bytes()).hexdigest()!=part['files']['step']['sha256']:
                raise ValueError(('STEP identity',part['name']))
            name=part['name'];shapes[name]=import_step(file).solids()[0]
            groups[name]=('input' if name in INPUT_PARTS else 'coupler' if name in COUPLER_PARTS
                          else 'jaw' if part['body']=='beak_hinge' else 'fixed')
    kit=manifests[-1];new={p['name'] for p in kit['parts']}
    voids={}
    grip=manifests[-2]
    for path,expected in grip['source_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError(('Stale shell native CUT construction',path))
    for name,relation in grip['native_csg_relations'].items():
        voids[name]=[]
        for record in relation['subtractive_solids']:
            file=R/record['path']
            if record['unit']!='mm' or hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:
                raise ValueError(('Native shell cut operand identity',name,record))
            shape=import_brep(file)
            if not shape.is_valid or len(shape.solids())!=1:raise ValueError(('Native cut validity',name))
            voids[name].append(shape.solids()[0])
    pairs=[(a,b) for a,b in itertools.combinations(shapes,2) if a in new or b in new]
    threads={frozenset((p['screw'],p['nut'])):p for p in kit['nominal_thread_contacts']}
    link=manifests[1];m=np.array(link['motor_axis_world_mm']);j=np.array(link['jaw_axis_world_mm'])
    d=link['crank_radius_mm']*np.array([np.cos(link['closed_phase_rad']),0,np.sin(link['closed_phase_rad'])])
    cache,errors,cases,queries,certificates={}, {}, [], [], []
    for q in np.linspace(0,.55,23):
        rot=Rotation.from_rotvec([0,q,0]).as_matrix();posed={};bounds={}
        for name,shape in shapes.items():
            group=groups[name]
            posed[name]=(shape if group=='fixed' else transform(shape,rot,j-rot@j)
                         if group=='jaw' else transform(shape,rot,m-rot@m)
                         if group=='input' else transform(shape,np.eye(3),rot@d-d))
            bb=posed[name].bounding_box(optimal=False)
            bounds[name]=np.array(tuple(bb.min)),np.array(tuple(bb.max))
        hits,contacts,unresolved=[],[],[];tested=0
        posed_voids={name:items if groups[name]=='fixed' else [transform(s,rot,j-rot@j) for s in items]
                     for name,items in voids.items() if name in shapes}
        for a,b in pairs:
            key=frozenset((a,b));invariant=groups[a]==groups[b]
            if time.monotonic()-started>120:
                unresolved.append(dict(a=a,b=b,error='FULL_CHECK_TIMEBOX'))
                break
            if invariant and key in errors:
                unresolved.append(dict(a=a,b=b,**errors[key],invariant_cached=True));continue
            if invariant and key in cache:v=cache[key]
            elif np.any(np.minimum(bounds[a][1],bounds[b][1])-np.maximum(bounds[a][0],bounds[b][0])<=1e-6):v=0.
            else:
                proof=None
                for target,part in [(a,b),(b,a)]:
                    found=contained_in_one_void(posed[part],posed_voids.get(target,[]))
                    if found is not None:
                        proof=dict(target=target,part=part,**found);break
                if proof is not None:
                    certificates.append(dict(q_rad=float(q),a=a,b=b,method='recorded_native_subtraction_containment',**proof))
                    v=proof['outside_volume_mm3']
                else:
                    result=bounded_common(posed[a],posed[b],3.)
                    queries.append(dict(q_rad=float(q),a=a,b=b,**result))
                    if 'error' in result:
                        if invariant:errors[key]=result
                        unresolved.append(dict(a=a,b=b,**result));continue
                    v=result['volume_mm3']
            if invariant:cache[key]=v
            tested+=1
            if key in threads:
                expected=threads[key]['expected_thread_overlap_mm3']
                contacts.append(dict(a=a,b=b,intersection_mm3=v,expected_nominal_thread_overlap_mm3=expected,
                                     nominal_thread_contact_pass=abs(v-expected)<.02))
            elif v>.01:hits.append(dict(a=a,b=b,intersection_mm3=v))
        passed=not hits and not unresolved and tested==len(pairs) and len(contacts)==4 and all(c['nominal_thread_contact_pass'] for c in contacts)
        cases.append(dict(q_rad=float(q),collisions=hits,unresolved_pairs=unresolved,
                          tested_pairs=tested,nominal_thread_contacts=contacts,sampled_geometry_pass=passed))
        print('BILL FRAME M3 FIT',round(q,3),'hits',len(hits),'unresolved',len(unresolved),flush=True)
        if time.monotonic()-started>120:break
    report=dict(schema='goose_bill_frame_m3_native_fit_v1',increment_parts=len(new),
                checked_native_parts=len(shapes),pair_count=len(pairs),sample_count=len(cases),
                passed_samples=sum(c['sampled_geometry_pass'] for c in cases),cases=cases,
                native_queries=queries,native_csg_certificates=certificates,elapsed_wall_seconds=time.monotonic()-started,
                installed=False,manufacturing_release=False,preload_release=False,
                full_tool_access_pass=False,structural_strength_pass=False,
                source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in paths+[replacement_file,Path(__file__),ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py',ROOT/'src/sai_agent/native_csg.py']},
                limitations=['Four actual nominal clamp stacks versus listed head solids at23jaw angles,not continuous or whole robot.',
                             'Nominal screw/nut thread contacts are measured separately;all unrelated overlaps and unresolved pairs reject.',
                             'No supplied threaded CAD,preload,grade,locking,local root/bearing stress or complete tool-path qualification.',
                             'Independent candidate;no installed scene,ledger,collision,runtime or colour version changed.'])
    (R/'evidence/bill_mount_fasteners_native_fit.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if len(cases)==23 and report['passed_samples']==23 else 1


if __name__=='__main__':
    raise SystemExit(main())
