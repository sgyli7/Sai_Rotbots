"""Overlay real ankle, neck and shell replacements on the same neutral scene."""
from pathlib import Path
import copy,hashlib,json
from sai_agent.goose.native_linkage import PART_OWNERS
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'


def main():
    paths=[R/'cad/source/body_bay_preview/scene.json',R/'evidence/body_bay_mechanical_parameters.json']
    old,ledger=[json.loads(p.read_text()) for p in paths]
    replacements_path=R/'configs/mechanical_native_replacements.json';paths.append(replacements_path)
    replacements=json.loads(replacements_path.read_text())['additional_replaces_by_folder']
    parts=copy.deepcopy(old['parts']);removed=[]
    for folder in ['body_bay_ankle_assembly','neck_root_assembly','neck_access_skins','hollow_shoe_covers','head_load_path','beak_native_linkage','head_linkage_clearance_skins','bill_backbones','jaw_retention','grip_cassettes','bill_mount_fasteners']:
        manifest=R/'cad/exports'/folder/'manifest.json';scene=R/'cad/source'/folder/'quad_scene.json';paths+=[manifest,scene]
        m,q=[json.loads(p.read_text()) for p in [manifest,scene]]
        names=set(m.get('replaces_existing_native_parts',m.get('replaces_existing_parts',[])))
        names.update(replacements.get(folder,[]))
        if folder=='body_bay_ankle_assembly':names|={side+'_ankle_crossmember' for side in ['right','left']}
        removed.extend(p['name'] for p in parts if p['name'] in names)
        parts=[p for p in parts if p['name'] not in names]+q['parts']
    assert len({p['name'] for p in parts})==len(parts)
    # Small retained stock servo pieces belong to the servo's output or case,
    # not to torso merely because their old display group is unmapped.
    for p in parts:
        n=p['name']
        if n in PART_OWNERS:
            p['body']=PART_OWNERS[n]
        elif n in {'head_roll_output_ring','head_roll_shaft_bolt'} or n.startswith('head_roll_horn_fixing_'):
            p['body']='head_roll'
        elif n=='head_roll_connector':p['body']='head_pitch'
        elif n=='neck_cable_0':
            p['body']='neck_yaw'
            p['role']='illustrative_stationary_root_cable_segment_actual_flex_route_unreleased'
    payload=dict(unit='m',status='MECHANICAL_CANDIDATE_HEAD_POWER_AND_CLOSURES_UNRELEASED',parts=parts,
        assembly_translation_m=[0,0,ledger['rigid_coordinate_lift_m']],nominal_conditional_mass_kg=ledger['nominal_conditional_mass_kg'],
        manufacturing_pass=False,final_appearance_pass=False,whole_assembly_clearance_pass=False,removed_parts=removed,
        retained_unreleased_architecture_parts=[n for n in old['retained_unreleased_architecture_parts'] if n not in removed],
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        scope='Same neutral body/leg/neck assembly,with native bill retention,replaceable grip carriers/pads and fixed-frame M3clamp stacks. Six old grip/bill corresponding parts replaced. Camera/skin connections,pad material and retention qualification,load/thermal qualification,power and wiring remain unreleased. Short-cover/short-span sole samples are not installed.')
    out=R/'cad/source/mechanical_preview';out.mkdir(exist_ok=True)
    (out/'scene.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')
    print('scene parts',len(parts),'mass kg',ledger['nominal_conditional_mass_kg'])

if __name__=='__main__':main()
