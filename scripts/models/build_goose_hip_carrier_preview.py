"""Actual new native hip/skin candidate, with coherently shifted distal geometry."""
from pathlib import Path
import argparse, copy, hashlib, json, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--wide',action='store_true'); args=parser.parse_args()
    skin_folder='hip_clearance_skins_wide' if args.wide else 'hip_clearance_skins'
    parameters_file='hip_clearance_wide_component_parameters.json' if args.wide else 'hip_clearance_component_parameters.json'
    paths=[R/'cad/source/pitch_foot_preview/scene.json', R/'cad/source/hip_roll_carriers/quad_scene.json',
           R/'cad/source'/skin_folder/'quad_scene.json', R/'evidence'/parameters_file]
    old,carriers,skins,parameters=[json.loads(p.read_text()) for p in paths]
    s=candidate(); folder=R/'cad/source'/('hip_carrier_wide_preview' if args.wide else 'hip_carrier_preview'); folder.mkdir(exist_ok=True)
    geometry=folder/'geometry'; geometry.mkdir(exist_ok=True)
    skin_names={p['name'] for p in skins['parts']}; parts=[]
    shift=np.array([.008,0.,0.])
    for original in old['parts']:
        if original['name'] in skin_names:
            continue
        p=copy.deepcopy(original)
        distal=False
        for side in ['right','left']:
            names=s.desc[side+'_hip_pitch']
            if p.get('body') in names or p['group'] in names or p['group']==side+'_foot' or p['name'].startswith((side+'_thigh_',side+'_shin_')):
                distal=True
        if distal:
            if 'geometry_npz' in p:
                file=R/p['geometry_npz']
                assert hashlib.sha256(file.read_bytes()).hexdigest()==p['source_sha256']
                with np.load(file,allow_pickle=False) as d:
                    vertices=d['vertices']+shift; faces=d['faces']
                new=geometry/(p['name']+'_quad.npz')
                np.savez_compressed(new,vertices=vertices,faces=faces)
                p['parent_geometry_sha256']=p['source_sha256']
                p['geometry_npz']=str(new.relative_to(R)); p['source_sha256']=hashlib.sha256(new.read_bytes()).hexdigest()
            else:
                p['vertices']=(np.array(p['vertices'])+shift).tolist()
            p['distal_axis_translation_m']=shift.tolist()
        parts.append(p)
    parts+=carriers['parts']+skins['parts']
    assert len({p['name'] for p in parts})==len(parts)
    report=dict(unit='m', status='HIP_CARRIER_AND_LOWER_ARCH_CANDIDATE_UNRELEASED', parts=parts,
        assembly_translation_m=[0.,0.,parameters['rigid_coordinate_lift_m']],
        nominal_conditional_mass_kg=parameters['nominal_conditional_mass_kg'],
        manufacturing_pass=False, final_appearance_pass=False, full_assembly_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        scope='Actual native roll-to-pitch mounts and lowerhip arches, with8mm translated hip-pitch descendants and foot contacts. Other cross-axis brackets, torso frame, mouth, electronics, cables and closures remain candidate geometry.')
    (folder/'scene.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
    print('candidate components',len(parts),'mass',report['nominal_conditional_mass_kg'])


if __name__=='__main__': main()
