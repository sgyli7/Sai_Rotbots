"""Native linkage sweep against the head candidate and existing head skins.

Threads are represented by nominal bolt major and tap-drill envelopes. Their
explicit intended overlap is reported, not called geometric clearance. This
screen never certifies thread strength, pin bending or complete bill load paths.
"""
from pathlib import Path
import hashlib,itertools,json,sys
import numpy as np
from build123d import import_step
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import transform
from sai_agent.native_cad import common_solid_volume_mm3 as overlap


def main():
    paths=[R/'cad/exports/beak_native_linkage/manifest.json',R/'cad/exports/head_load_path/manifest.json',R/'cad/exports/head_linkage_clearance_skins/manifest.json']
    link,head,skins=[json.loads(p.read_text()) for p in paths]
    parts={};new={p['name'] for p in link['parts']};groups={}
    for m in [link,head,skins]:
        for p in m['parts']:
            if m is skins and not p['name'].startswith('goose_head_shell_'):continue
            for f in p['files'].values():assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256']
            parts[p['name']]=import_step(R/p['files']['step']['path']).solids()[0];groups[p['name']]=p.get('body','head_roll')
    M=np.array(link['motor_axis_world_mm']);J=np.array(link['jaw_axis_world_mm']);phase=link['closed_phase_rad'];radius=link['crank_radius_mm'];D=radius*np.array([np.cos(phase),0,np.sin(phase)])
    cases=[];cache={}
    threads={frozenset(['beak_native_input_flange','beak_input_button_screw']),frozenset(['beak_native_output_arm','beak_output_button_screw'])}
    input_names={'beak_native_input_flange','beak_input_steel_sleeve','beak_input_washer','beak_input_button_screw'}
    output_names={'beak_native_output_arm','beak_native_d_shaft','beak_output_steel_sleeve','beak_output_washer','beak_output_button_screw'}
    translated={'beak_native_coupler','beak_input_bush_candidate','beak_output_bush_candidate'}
    for q in np.linspace(0,.55,23):
        rot=Rotation.from_rotvec([0,q,0]).as_matrix();delta=rot@D-D;shapes={};bounds={}
        for name,shape in parts.items():
            if name in input_names:shapes[name]=transform(shape,rot,M-rot@M)
            elif name in output_names:shapes[name]=transform(shape,rot,J-rot@J)
            elif name in translated:shapes[name]=transform(shape,np.eye(3),delta)
            else:shapes[name]=shape
            bb=shapes[name].bounding_box();bounds[name]=(np.array(tuple(bb.min)),np.array(tuple(bb.max)))
        hits=[];mating=[]
        for a,b in itertools.combinations(shapes,2):
            if a not in new and b not in new:continue
            if np.any(np.minimum(bounds[a][1],bounds[b][1])-np.maximum(bounds[a][0],bounds[b][0])<=1e-6):continue
            # No approximate distance filter; each remaining candidate uses
            # exact native solid common volume.
            v=overlap(shapes[a],shapes[b])
            if v<=.01:continue
            row=dict(a=a,b=b,intersection_mm3=v)
            if frozenset([a,b]) in threads:
                row['purpose']='nominal M4major versus3.3mm tap-drill;intended threaded engagement,not a clearance pass'
                row['expected_overlap_mm3']=float(np.pi*(2**2-1.65**2)*4.5)
                row['volume_matches_nominal_4_5mm_thread']=abs(v-row['expected_overlap_mm3'])<.05
                mating.append(row)
            else:hits.append(row)
        passed=not hits and len(mating)==2 and all(r['volume_matches_nominal_4_5mm_thread'] for r in mating)
        cases.append(dict(q_rad=float(q),collisions=hits,intended_thread_envelopes=mating,sampled_geometry_pass=passed))
        print('BEAK NATIVE',round(q,3),'hits',len(hits),'thread envelopes',len(mating),'pass',passed,flush=True)
    scene_path=R/'cad/source/mechanical_preview/scene.json';scene=json.loads(scene_path.read_text());scene_parts={p['name']:p for p in scene['parts']}
    source_scenes=[R/'cad/source'/folder/'quad_scene.json' for folder in ['beak_native_linkage','head_load_path','head_linkage_clearance_skins']]
    native_parts=[p for source in source_scenes for p in json.loads(source.read_text())['parts']]
    installed=all(p['name'] in scene_parts and p['source_sha256']==scene_parts[p['name']]['source_sha256'] for p in native_parts)
    paths.extend(source_scenes)
    paths.append(scene_path)
    report=dict(schema='goose_beak_native_linkage_fit_v1',candidate_parts=len(new),checked_parts=len(parts),cases=cases,
        passed_samples=sum(c['sampled_geometry_pass'] for c in cases),sample_count=len(cases),integrated=installed,whole_head_release=False,manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        limitations=['Native moving linkage only;existing upper/lower bill bones and shaft axial retainers are not closed.',
                     'Nominal screw versus tap-drill overlap is intentional and quantified;this is not thread pullout/preload proof.',
                     'Candidate bush flange/tolerances, pin/sleeve grade and stationary grasp thermal duty remain unverified.',
                     '23samples do not prove continuous clearance or physical grasp/drag success.'])
    (R/'evidence/beak_native_linkage_fit.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['passed_samples']==len(cases) else 1

if __name__=='__main__':raise SystemExit(main())
