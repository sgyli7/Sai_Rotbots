"""Actual body-bay CAD increments, with explicit retained unreleased pieces."""
from pathlib import Path
import copy,hashlib,json,sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate
from sai_agent.goose.morphology import apply_leg_layout


def main():
    paths=[R/'cad/source/manufacturing_preview/scene.json',R/'configs/body_bay_layout_candidate.json',R/'evidence/body_bay_component_parameters.json']
    old,layout,ledger=[json.loads(p.read_text()) for p in paths]
    s=candidate();original_pivots={n:p.copy() for n,p in s.pivots.items()};original_items={i['name']:i for i in s.items};apply_leg_layout(s,layout)
    folder=R/'cad/source/body_bay_preview';folder.mkdir(exist_ok=True);geometry=folder/'geometry';geometry.mkdir(exist_ok=True)
    scenes={}
    for name in ['body_bay_skins','body_bay_frame','body_bay_roll_carriers','body_bay_pitch_forks','pitch_fork_assembly','compliant_foot']:
        path=R/'cad/source'/name/'quad_scene.json';paths.append(path);scenes[name]=json.loads(path.read_text())
    assemblies=['lower_neck','upper_neck']+[side+'_'+segment for side in ['right','left'] for segment in ['thigh','shin']]
    replaced={a+'_fork_'+end for a in assemblies for end in ['front','rear','bridge']}
    replaced|={side+'_foot_'+suffix for side in ['right','left'] for suffix in ['sole','load_plate']}
    replaced|={p['name'] for p in scenes['body_bay_skins']['parts']}|{'belly_frame'}
    parts=[];retained=[]
    def move(part,shift):
        if np.linalg.norm(shift)<1e-12:return
        if 'geometry_npz' in part:
            path=R/part['geometry_npz'];assert hashlib.sha256(path.read_bytes()).hexdigest()==part['source_sha256']
            with np.load(path,allow_pickle=False) as data:vertices=data['vertices']+shift;faces=data['faces']
            path=geometry/(part['name']+'_quad.npz');np.savez_compressed(path,vertices=vertices,faces=faces)
            part['geometry_npz']=str(path.relative_to(R));part['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            part['vertices']=(np.array(part['vertices'])+shift).tolist()
            part['source_sha256']=hashlib.sha256(json.dumps(part['vertices'],separators=(',',':')).encode()).hexdigest()
        part['candidate_translation_m']=shift.tolist()
    for original in old['parts']:
        if original['name'] in replaced:continue
        part=copy.deepcopy(original);name=part['name'];shift=np.zeros(3)
        if name.endswith('_catalog_case') and part['group'] in s.pivots:
            anchor=part['group'];shift=s.pivots[anchor]-original_pivots[anchor];part['body']=s.parents[anchor]
        elif name in layout['electronics_allowance_boxes_mm']:
            shift=np.array(layout['electronics_allowance_boxes_mm'][name]['centre'])/1000-np.array(original_items[name]['center_m'])
        elif name in ledger['torso_display_part_translations_m']:
            shift=np.array(ledger['torso_display_part_translations_m'][name])
        else:
            body=part.get('body') or (s.owner(name) if name in s.parts else 'torso')
            if body in s.pivots and body!='torso':shift=s.pivots[body]-original_pivots[body]
        move(part,shift);parts.append(part)
        if part.get('role')!='native_nurbs_skin_attachment_pending':retained.append(name)
    for name in ['body_bay_skins','body_bay_frame','body_bay_roll_carriers','body_bay_pitch_forks']:
        parts+=copy.deepcopy(scenes[name]['parts'])
    parts+=[copy.deepcopy(p) for p in scenes['pitch_fork_assembly']['parts'] if p['name'].startswith(('lower_neck_','upper_neck_'))]
    for original in scenes['compliant_foot']['parts']:
        part=copy.deepcopy(original);body=part['body'];move(part,s.pivots[body]-original_pivots[body]);parts.append(part)
    assert len({p['name'] for p in parts})==len(parts)
    payload=dict(unit='m',status='BODY_BAY_NATIVE_CANDIDATE_PARTIAL_ASSEMBLY_UNRELEASED',parts=parts,
        assembly_translation_m=[0,0,ledger['rigid_coordinate_lift_m']],nominal_conditional_mass_kg=ledger['nominal_conditional_mass_kg'],
        manufacturing_pass=False,final_appearance_pass=False,whole_assembly_clearance_pass=False,
        retained_unreleased_architecture_parts=retained,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        scope='Actual native module-bay skins,16frame parts,8rollcarriers,104newleg and52retainedneck fork parts,4compliantfoot parts; remaining head/ankle/button/electronics closures are explicit architecture candidates. All geometry follows the same neutral pivots and3.7mm physical foot datum lift. Segmented neck/leg covers are not installed.')
    (folder/'scene.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')
    print('components',len(parts),'conditional_mass',payload['nominal_conditional_mass_kg'])


if __name__=='__main__':main()
