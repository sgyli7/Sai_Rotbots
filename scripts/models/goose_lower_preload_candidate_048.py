"""Immutable14 + frozen048 two actualparts, native merge and exact source-delta MCI. Zero physics."""
from pathlib import Path
import json,hashlib,shutil,sys,importlib.util,xml.etree.ElementTree as ET
import numpy as np
W=Path(__file__).resolve().parents[2];SRC=W/'robots/goose_v0_2/models/physics_v0_2_20261021_14_candidate';OUT=W/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate';H=W/'experiments/goose_v0_2/bill_lower_preload_patch_048/c01/module_handoff_final_001.json';PARENT=W/'experiments/goose_v0_2/bill_lower_local_patch_043/c01/merge_plan_14.json';NP=H.parent/'merge_plan_15.json';NO=W/'robots/goose_v0_2/cad/exports/full_native_head_integration_026/r12_preload048_review'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def ten(x):
 a=np.asarray(x,float)
 if a.shape==(3,3):return a
 xx,yy,zz,xy,xz,yz=a;return np.array([[xx,xy,xz],[xy,yy,yz],[xz,yz,zz]])
def six(I):return [float(I[0,0]),float(I[1,1]),float(I[2,2]),float(I[0,1]),float(I[0,2]),float(I[1,2])]
def moments(m,c,I):c=np.asarray(c,float)*.001;return m*c,ten(I)+m*((c@c)*np.eye(3)-np.outer(c,c))
def central(m,F,I):c=F/m;J=I-m*((c@c)*np.eye(3)-np.outer(c,c));assert np.linalg.eigvalsh(J).min()>0;return c,J
assert sha(H)=='9ac280c2e009b2d8dbe07d29cf03776570114ce157ca9a3bee04843554623b17'
h=json.load(open(H));assert sha(SRC/'manifest.json')=='992f1fd56774635443fa1d801e195eac92b2c6a870700e57792e3d8671befba9'
plan=json.load(open(NP));ret=set(h['retired_native_exact_names']);assert len(ret)==2
oldplan=json.load(open(PARENT));oldnative={x['name']:{'source':x['source']}for x in oldplan['new_parts']if x['name']in ret};assert len(oldnative)==2
rename={r['name']:'preload048_'+r['name']for r in h['parts']};trans=np.array([-13.55,0,32.305]);h['retired_runtime_ledger_aliases']={}
for r in h['parts']:
 r.update(r['new_source_mci']);assert sha(r['path'])==r['sha256'] and sha(r['old_path'])==r['old_sha256'];assert np.linalg.eigvalsh(ten(r['I_com_kg_m2'])).min()>0
assert (NO/'merged_native_manifest.json').exists() and not OUT.exists();import mujoco as mj
before={str(p.relative_to(SRC)):sha(p)for p in SRC.rglob('*')if p.is_file()and'__pycache__'not in p.parts};shutil.copytree(SRC,OUT,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(H,OUT/'source_inputs/preload048_handoff.json');shutil.copy2(SRC/'manifest.json',OUT/'source_inputs/parent14_manifest.json');pc=json.load(open(OUT/'physical_contract.json'));ledger=json.load(open(OUT/'mass_ledger.json'));items={x['name']:x for x in ledger['items']};aliases=h['retired_runtime_ledger_aliases'];ledgerret={aliases.get(n,n)for n in ret};assert ledgerret<=items.keys();delta=sum(r['mass_kg']-r['old_source_mci']['mass_kg']for r in h['parts']);assert abs(delta-h['net_source_mass_delta_kg'])<1e-8;newitems=[];deltas=[]
for r in h['parts']:
 oldname=next(n for n in ret if oldnative[n]['source']['sha256']==r['old_sha256']);item=items[aliases.get(oldname,oldname)];M=item['mass_kg'];F,I=moments(M,item['centre_zero_mm'],item['inertia_at_com_zero_kg_m2']);old=r['old_source_mci'];fo,io=moments(old['mass_kg'],np.array(old['COM_native_mm'])+trans,old['I_com_kg_m2']);fn,inew=moments(r['mass_kg'],np.array(r['COM_native_mm'])+trans,r['I_com_kg_m2']);dm=r['mass_kg']-old['mass_kg'];M+=dm;F+=fn-fo;I+=inew-io;C,J=central(M,F,I);newitems.append({'name':rename[r['name']],'body':r['body'],'mass_kg':M,'centre_zero_mm':(C*1000).tolist(),'inertia_at_com_zero_kg_m2':J.tolist(),'source':{'path':r['path'],'sha256':r['sha256']},'new_geometry_raw_mci':{'mass_kg':r['mass_kg'],'centre_zero_mm':(np.array(r['COM_native_mm'])+trans).tolist(),'I_com_kg_m2':r['I_com_kg_m2']},'retained_parent_ledger_offset_policy':'Exact source new-old mass/first/second delta, preserve inherited14 ledger/source discrepancy'});deltas.append({'body':r['body'],'dm':dm,'dF':fn-fo,'dI':inew-io})
anchors={'head_roll':np.array([67.45,0,617.805])*.001,'beak_hinge':np.array([146.45,0,608.305])*.001};changed=[]
for body in ['beak_hinge']:
 row=next(x for x in pc['bodies']if x['name']==body);M=row['mass_kg'];F,I=moments(M,np.array(row['centre_world_zero_m'])*1000,row['inertia_at_com_world_zero_kg_m2']);
 for d in deltas:
  if d['body']==body:M+=d['dm'];F+=d['dF'];I+=d['dI']
 C,J=central(M,F,I);row.update(mass_kg=M,centre_world_zero_m=C.tolist(),inertia_at_com_world_zero_kg_m2=J.tolist(),inertia_at_com_body_kg_m2=J.tolist(),com_local_m=(C-anchors[body]).tolist());changed.append(body)
ledger['items']=[x for x in ledger['items']if x['name']not in ledgerret]+newitems;total=pc['nominal_robot_mass_kg']+delta;status='EXPERIMENTAL_PRELOAD048_ZERO_STEP_NOT_PHYSICS_ADMITTED';ledger.update(status=status,nominal_mass_kg=total,current_parent_mass_kg=total-delta,current_mass_delta_kg=delta,current_retired_items=sorted(ledgerret),current_added_items=[x['name']for x in newitems],preload048_handoff=ref(H));write(OUT/'mass_ledger.json',ledger)
for row in pc['bodies']:
 if row['name']in changed:row['source_mass_items']=[x['name']for x in ledger['items']if x['body']==row['name']];row['item_count']=len(row['source_mass_items'])
pc.update(release_id=OUT.name,status=status,nominal_robot_mass_kg=total,preload048_handoff=ref(H),current_native_manifest=ref(NO/'merged_native_manifest.json'));pc['source_identity'].update(parent14_manifest=ref(SRC/'manifest.json'),current_native=ref(NO/'merged_native_manifest.json'),current_mass=ref(OUT/'mass_ledger.json'),incremental_mass_handoff=ref(H));write(OUT/'physical_contract.json',pc)
tree=ET.parse(OUT/'robot.xml');root=tree.getroot();root.set('model',OUT.name)
for body in changed:
 row=next(x for x in pc['bodies']if x['name']==body);node=root.find(".//body[@name='"+body+"']/inertial");node.attrib.clear();node.set('mass',format(row['mass_kg'],'.17g'));node.set('pos',' '.join(format(v,'.17g')for v in row['com_local_m']));node.set('fullinertia',' '.join(format(v,'.17g')for v in six(ten(row['inertia_at_com_body_kg_m2']))))
for n in root.find('custom'):
 if n.get('name')=='physical_contract_sha256':n.set('data',sha(OUT/'physical_contract.json'))
 if n.get('name')=='status':n.set('data',status)
tree.write(OUT/'robot.xml',encoding='unicode');m=mj.MjModel.from_xml_path(str(OUT/'robot.xml'));parent=mj.MjModel.from_xml_path(str(SRC/'robot.xml'));mj.mj_saveModel(m,str(OUT/'actual_scene.mjb'));z=np.load(SRC/'initial_state.npz');d=mj.MjData(m);d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];mj.mj_forward(m,d);np.savez_compressed(OUT/'initial_state.npz',qpos=d.qpos,qvel=d.qvel)
names=['jnt_axis','jnt_pos','jnt_range','dof_armature','dof_damping','dof_frictionloss','geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_condim','geom_solref','geom_solimp','actuator_gear','actuator_gainprm','actuator_biasprm','eq_data','eq_solref','eq_solimp'];arrays={n:bool(np.array_equal(getattr(m,n),getattr(parent,n)))for n in names};assert all(arrays.values());actualchanged=[m.body(i).name for i in range(m.nbody)if any(not np.array_equal(getattr(m,n)[i],getattr(parent,n)[i])for n in ['body_mass','body_ipos','body_inertia','body_iquat'])];assert set(actualchanged)==set(changed);assert abs(m.body_mass.sum()-total)<1e-10
write(OUT/'compiled_readback.json',{'physics_steps':0,'mass_kg':float(m.body_mass.sum()),'delta_kg':delta,'author_cut_delta_kg':h['net_source_mass_delta_kg'],'complete_sourceMCI_minus_authorcut_delta_kg':delta-h['net_source_mass_delta_kg'],'changed_MCI_bodies':actualchanged,'unchanged_source_arrays':arrays,'initial_ncon':d.ncon,'source_delta_policy':'Only2 source new-old moments applied to retained14 ledger','geometry_mass_deltas':[{k:v.tolist()if isinstance(v,np.ndarray)else v for k,v in x.items()}for x in deltas],'runtime_collision_unchanged':True,'unresolved':h['limits']})
write(OUT/'hardware_change_receipt.json',{'parent':ref(SRC/'manifest.json'),'handoff':ref(H),'retired_native':sorted(ret),'retired_ledger':sorted(ledgerret),'added':[x['name']for x in newitems],'delta_mass_kg':delta,'native':ref(NO/'merged_native_manifest.json'),'source_control_caps_geometry_unchanged_except_MCI':True,'outer_bbox_same_internal_pocket_only':True,'selectedTPUsha_retained':['755c9712f22dd17faa0ef3a6a474c5c26c5f62a18762e28dab87dbf42c3809d0','349a389c16101cd953b3050e0c67cba6c3fcb07c8c3652f162d543e382815130']})
for n in ['actuator_contract.json','runtime_interface.json']:
 x=json.load(open(OUT/n));x['release_id']=OUT.name;x['local043_no_new_motor_cap']=True;write(OUT/n,x)
manifest=json.load(open(SRC/'manifest.json'));manifest.update(release_id=OUT.name,status=status);manifest['qualification_limits']+=h['limits'];manifest['files']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='manifest.json'and'__pycache__'not in p.parts};write(OUT/'manifest.json',manifest);assert before=={str(p.relative_to(SRC)):sha(p)for p in SRC.rglob('*')if p.is_file()and'__pycache__'not in p.parts};print(json.dumps({'candidate':str(OUT),'mass_kg':total,'delta_kg':delta,'manifest_sha256':sha(OUT/'manifest.json'),'physics_steps':0}))
