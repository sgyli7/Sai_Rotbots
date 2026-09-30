"""Replace old skin estimates with native masses, without changing the model.

This is a bounded change-impact ledger. Remaining mounts/frame/power are still
allocations; a budget comparison cannot certify the complete manufactured robot.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.linalg import eigvalsh
ROOT=Path(__file__).resolve().parents[2];ROBOT=ROOT/'robots/Goose_V0.1'

def aggregate(items,pivot):
    mass=sum(i['mass_kg'] for i in items);center=sum(i['mass_kg']*np.array(i['center_m']) for i in items)/mass;inertia=np.zeros((3,3))
    for i in items:
        offset=np.array(i['center_m'])-center
        inertia+=np.array(i['inertia_at_com_kg_m2'])+i['mass_kg']*((offset@offset)*np.eye(3)-np.outer(offset,offset))
    if np.linalg.eigvalsh(inertia).min()<=0:raise ValueError('Invalid body inertia')
    return dict(mass_kg=mass,com_local_m=(center-pivot).tolist(),inertia_at_com_body_kg_m2=inertia.tolist())

def main():
    contract_file=ROBOT/'configs/stage_two_contract.json';skins_file=ROBOT/'cad/exports/manufacturing_skins/manifest.json';layout_file=ROBOT/'configs/manufacturing_head_layout.json'
    contract=json.loads(contract_file.read_text());skins=json.loads(skins_file.read_text());layout=json.loads(layout_file.read_text())
    items=json.loads(json.dumps(contract['items']));old_names={p['name'] for p in skins['parts'] if not p['name'].startswith('goose_head_shell_')}|{'goose_head_shell'}
    removed=[i for i in items if i['name'] in old_names];items=[i for i in items if i['name'] not in old_names]
    replacements=[]
    for p in skins['parts']:
        i=dict(name=p['name'],body='head_roll' if p['name'].startswith('goose_head_shell_') else 'torso',mass_kg=p['full_density_mass_kg'],center_m=p['center_of_mass_world_m'],inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],basis='native CAD at assumed1270kg/m3 PETG; no infill discount; attachment geometry pending')
        items.append(i);replacements.append(i)
    for i in items:
        if i['name']=='camera_module':i['center_m']=(np.array(i['center_m'])+layout['optical_module_translation_from_stage_two_m']).tolist()
    pivots={j['name']:np.array(j['pivot_world_at_zero_m']) for j in contract['joints']};pivots['torso']=np.array(contract['root_origin_at_zero_m']);rows=[]
    for old in contract['bodies']:
        name=old['name'];new=aggregate([i for i in items if i['body']==name],pivots[name])
        mass_change=new['mass_kg']/old['mass_kg']-1;com_change=np.linalg.norm(np.array(new['com_local_m'])-old['com_local_m'])
        inertia_ratio=eigvalsh(np.array(new['inertia_at_com_body_kg_m2']),np.array(old['inertia_at_com_body_kg_m2']))
        low,high=old['inertia_multiplier_range'];within=abs(mass_change)<=old['mass_relative_design_uncertainty']+1e-12 and com_change<=old['com_randomization_m']+1e-12 and np.all(inertia_ratio>=low-1e-12) and np.all(inertia_ratio<=high+1e-12)
        rows.append(dict(name=name,native_skin_increment_parameters=new,mass_change_kg=new['mass_kg']-old['mass_kg'],com_change_m=float(com_change),generalized_inertia_ratio=inertia_ratio.tolist(),within_parent_mass_com_inertia_bounds=bool(within)))
    old_mass=contract['nominal_robot_mass_kg'];mass=sum(i['mass_kg'] for i in items)
    report=dict(status='NATIVE_SKIN_ONLY_CHANGE_IMPACT_NOT_NEW_FROZEN_MODEL',hardware_freeze=False,model_was_modified=False,parent_mass_kg=old_mass,skin_increment_nominal_mass_kg=mass,nominal_mass_change_kg=mass-old_mass,removed_skin_estimates_kg=sum(i['mass_kg'] for i in removed),native_skin_mass_kg=sum(i['mass_kg'] for i in replacements),component_change_within_parent_parameter_bounds=all(r['within_parent_mass_com_inertia_bounds'] for r in rows),bodies=rows,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [contract_file,skins_file,layout_file,Path(__file__)]},limits=['Only eight skin parts and coherent camera offset are substituted. New interfaces, frame, fasteners, cooling and power are not frozen.','Matching old numerical randomization bounds is not manufacturing acceptance or a proof of trained-policy transfer.','Camera body extrinsics must be revised coherently in any eventual new model; the stage-two contract and model remain immutable.'])
    (ROBOT/'evidence/manufacturing_skin_parameter_delta.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['skin_increment_nominal_mass_kg','nominal_mass_change_kg','component_change_within_parent_parameter_bounds','hardware_freeze']},indent=2))
if __name__=='__main__':main()
