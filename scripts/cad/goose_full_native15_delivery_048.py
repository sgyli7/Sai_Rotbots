"""Native-only exact15 lower two-part replacement; no runtime or physics changes."""
from pathlib import Path
import json,hashlib,importlib.util
import numpy as np
W=Path(__file__).resolve().parents[2];E=W/'experiments/goose_v0_2/bill_lower_preload_patch_048/c01';hp=E/'module_handoff_final_001.json';h=json.load(open(hp));pp=W/'experiments/goose_v0_2/bill_lower_local_patch_043/c01/merge_plan_14.json';p=json.load(open(pp));sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest();ref=lambda q:dict(path=str(q),sha256=sha(q))
ret=h['retired_native_exact_names'];old={r['name']:r for r in p['new_parts']};assert len(ret)==2 and set(ret)<=old.keys();p['new_parts']=[r for r in p['new_parts']if r['name']not in ret]
for r in h['parts']:
 assert sha(r['path'])==r['sha256'];o=next(v for v in old.values()if v['source']['sha256']==r['old_sha256']);n=json.loads(json.dumps(o));m=r['new_source_mci'];I=np.array(m['I_com_kg_m2']);n.update(name='preload048_'+r['name'],source=ref(r['path']),mci=dict(mass_kg=m['mass_kg'],com_zero_mm=(np.array(m['COM_native_mm'])+np.array(r['translation_to_zero_mm'])).tolist(),inertia_com_kg_m2=[float(I[0,0]),float(I[1,1]),float(I[2,2]),float(I[0,1]),float(I[0,2]),float(I[1,2])]))
 p['new_parts'].append(n)
p.update(candidate_id='intact_full_head_15_preload048',parent_plan=ref(pp),incremental_handoff=ref(hp),incremental_retired_exact_names=ret);p['handoffs']['support_carrier']=ref(hp);npth=E/'merge_plan_15.json';npth.write_text(json.dumps(p,indent=2)+'\n');spec=importlib.util.spec_from_file_location('merge',W/'scripts/cad/goose_full_head_candidate_merge_026.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);base=mod.validate(p);out=W/'robots/goose_v0_2/cad/exports/full_native_head_integration_026/r12_preload048_review';mod.build(p,base,out);print(json.dumps(dict(output=str(out),plan=ref(npth),net_mass_delta_kg=h['net_source_mass_delta_kg'])))
