"""Show installed native link and sole increments without claiming full release."""
from pathlib import Path
import json, hashlib

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'robots/Goose_V0.1'

def main():
    paths=[R/'cad/source/manufacturing_preview/scene.json',
           R/'cad/source/pitch_fork_assembly/quad_scene.json',
           R/'cad/source/compliant_foot/quad_scene.json',
           R/'cad/exports/compliant_foot/manifest.json']
    old,forks,feet,foot_manifest=[json.loads(p.read_text()) for p in paths]
    assemblies=['lower_neck','upper_neck','left_thigh','right_thigh','left_shin','right_shin']
    replaced={a+'_fork_'+end for a in assemblies for end in ['front','rear','bridge']}
    replaced|={side+'_foot_'+suffix for side in ['left','right'] for suffix in ['sole','load_plate']}
    found={p['name'] for p in old['parts'] if p['name'] in replaced}
    if found!=replaced: raise ValueError(('Missing old components',replaced-found))
    parts=[p for p in old['parts'] if p['name'] not in replaced]+forks['parts']+feet['parts']
    if len({p['name'] for p in parts})!=len(parts):raise ValueError('Duplicate component')
    payload=dict(unit='m',status='NATIVE_LINK_AND_SOLE_INCREMENT_FULL_ASSEMBLY_UNRELEASED',
        manufacturing_pass=False,final_appearance_pass=False,parts=parts,
        assembly_translation_m=[0,0,foot_manifest['robot_rigid_parts_must_be_raised_mm']/1000],
        removed_candidate_parts=sorted(replaced),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        scope='Same native 156 link components and four sole/load plates. Motor cylinders, cross-axis architecture, jaw, covers, fasteners and cables remain incomplete candidates. All components are lifted coherently for the actual compliant sole contact datum.')
    out=R/'cad/source/pitch_foot_preview';out.mkdir(exist_ok=True)
    (out/'scene.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')
    print(len(parts),'parts; final/manufacturing release false')

if __name__=='__main__':main()
