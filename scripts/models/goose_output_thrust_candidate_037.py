"""Immutable11 plus independently reviewed037 real thrust parts. ZERO physics."""
from pathlib import Path
import json,hashlib,shutil,sys,importlib.util,xml.etree.ElementTree as ET
import numpy as np
W=Path(__file__).resolve().parents[2];SRC=W/'robots/goose_v0_2/models/physics_v0_2_20261021_11_candidate';OUT=W/'robots/goose_v0_2/models/physics_v0_2_20261021_12_candidate';H=W/'experiments/goose_v0_2/output_thrust_loadpath_037/c01/module_handoff.json';PLAN=W/'experiments/goose_v0_2/output_thrust_upgrade_033/c01/merge_plan_11_identity_r02.json';NP=W/'experiments/goose_v0_2/output_thrust_loadpath_037/c01/merge_plan_12.json';NO=W/'robots/goose_v0_2/cad/exports/full_native_head_integration_026/r09_thrust037_review'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def write(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def ten(v):
 a=np.asarray(v,float)
 if a.shape==(3,3):return a
 x,y,z,xy,xz,yz=a;return np.array([[x,xy,xz],[xy,y,yz],[xz,yz,z]])
def shift(m,c,I):c=np.asarray(c)*.001;return ten(I)+m*((c@c)*np.eye(3)-np.outer(c,c))
assert sha(H)=='fb53ad06cedf381757c8581402aad623ba0d2ca82913469658c915d47f6abbbe';h=json.loads(H.read_text());assert sha(PLAN)==h['parent_plan']['sha256'];plan=json.loads(PLAN.read_text());old={r['name']:r for r in plan['new_parts']};ret={r['name']for r in h['retired']};assert len(ret)==3 and ret<=old.keys()
for r in h['retired']:assert r==old[r['name']]
plan['new_parts']=[r for r in plan['new_parts']if r['name']not in ret]
for r in h['parts']:
 assert sha(W/r['source']['path'])==r['source']['sha256'];assert np.linalg.eigvalsh(ten(r['I_com_kg_m2'])).min()>0
 plan['new_parts'].append(dict(name='thrust037_'+r['name'],body=r['body'],source=r['source'],handoff_owner='support_carrier',material=r['material'],translation_to_zero_mm=r['translation_to_zero_mm'],rotation_xyz_deg=[0,0,0],catalogue_envelope_only=False,mci=r['mci']))
plan.update(candidate_id='intact_full_head_12_thrust037',parent_plan=ref(PLAN),incremental_retired_exact_names=sorted(ret),incremental_handoff=ref(H));plan['handoffs']['support_carrier']=ref(H);plan['unresolved']+=h['limitations']+['037 thread omitted metal upperbound corrected to .225g, not exact manufactured MCI','O40N conditional engineering screen, not measured dynamic capacity; no axialfloat or washer contact dynamics in runtime']
if NP.exists():assert json.loads(NP.read_text())==plan
else:write(NP,plan)
if '--native-only'in sys.argv:
 spec=importlib.util.spec_from_file_location('merger',W/'scripts/cad/goose_full_head_candidate_merge_026.py');mer=importlib.util.module_from_spec(spec);spec.loader.exec_module(mer);base=mer.validate(plan);mer.build(plan,base,NO);print(NO,sha(NO/'merged_native_manifest.json'));sys.exit(0)
assert (NO/'merged_native_manifest.json').is_file();assert not OUT.exists();import mujoco as mj
before={str(p.relative_to(SRC)):sha(p)for p in SRC.rglob('*')if p.is_file()and '__pycache__'not in p.parts};shutil.copytree(SRC,OUT,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(H,OUT/'source_inputs/thrust037_handoff.json');shutil.copy2(SRC/'manifest.json',OUT/'source_inputs/parent11_manifest.json')
pc=json.loads((OUT/'physical_contract.json').read_text());ledger=json.loads((OUT/'mass_ledger.json').read_text());items={x['name']:x for x in ledger['items']};assert ret<=items.keys();delta=sum(x['mass_kg']for x in h['parts'])-sum(items[n]['mass_kg']for n in ret);assert abs(delta-h['delta_mass_kg'])<1e-12
body='beak_hinge';row=next(x for x in pc['bodies']if x['name']==body);M=row['mass_kg'];C=np.asarray(row['centre_world_zero_m']);F=M*C;I0=shift(M,C*1000,row['inertia_at_com_world_zero_kg_m2'])
for name in ret:
 x=items[name];m=x['mass_kg'];c=x['centre_zero_mm'];M-=m;F-=m*np.asarray(c)*.001;I0-=shift(m,c,x['inertia_at_com_zero_kg_m2'])
for x in h['parts']:
 m=x['mass_kg'];c=x['mci']['com_zero_mm'];M+=m;F+=m*np.asarray(c)*.001;I0+=shift(m,c,x['I_com_kg_m2'])
C=F/M;IC=I0-M*((C@C)*np.eye(3)-np.outer(C,C));assert np.linalg.eigvalsh(IC).min()>0;anchor=np.array([146.45,0,608.305])*.001;row.update(mass_kg=M,centre_world_zero_m=C.tolist(),inertia_at_com_world_zero_kg_m2=IC.tolist(),inertia_at_com_body_kg_m2=IC.tolist(),com_local_m=(C-anchor).tolist())
ledger['items']=[x for x in ledger['items']if x['name']not in ret]
for x in h['parts']:ledger['items'].append(dict(name='thrust037_'+x['name'],body=body,mass_kg=x['mass_kg'],centre_zero_mm=x['mci']['com_zero_mm'],inertia_at_com_zero_kg_m2=x['I_com_kg_m2'],source=x['source'],engineering_approximation='Thread major-envelope/nominal density; not manufactured measured mass'))
row['source_mass_items']=[x['name']for x in ledger['items']if x['body']==body];row['item_count']=len(row['source_mass_items']);total=pc['nominal_robot_mass_kg']+delta;status='EXPERIMENTAL_THRUST037_ZERO_STEP_NOT_RUNTIME_ADMITTED';ledger.update(status=status,nominal_mass_kg=total,current_parent_mass_kg=total-delta,current_mass_delta_kg=delta,current_retired_items=sorted(ret),current_added_items=['thrust037_'+x['name']for x in h['parts']],thrust037_handoff=ref(H));write(OUT/'mass_ledger.json',ledger)
pc.update(release_id=OUT.name,status=status,nominal_robot_mass_kg=total,thrust037_handoff=ref(H),current_native_manifest=ref(NO/'merged_native_manifest.json'));pc['source_identity'].update(parent11_manifest=ref(SRC/'manifest.json'),current_native=ref(NO/'merged_native_manifest.json'),current_mass=ref(OUT/'mass_ledger.json'),incremental_mass_handoff=ref(H));write(OUT/'physical_contract.json',pc)
tree=ET.parse(OUT/'robot.xml');root=tree.getroot();root.set('model',OUT.name);node=root.find(".//body[@name='beak_hinge']/inertial");node.attrib.clear();node.set('mass',format(M,'.17g'));node.set('pos',' '.join(format(v,'.17g')for v in C-anchor));node.set('fullinertia',' '.join(format(v,'.17g')for v in[IC[0,0],IC[1,1],IC[2,2],IC[0,1],IC[0,2],IC[1,2]]))
for n in root.find('custom'):
 if n.get('name')=='physical_contract_sha256':n.set('data',sha(OUT/'physical_contract.json'))
 if n.get('name')=='status':n.set('data',status)
tree.write(OUT/'robot.xml',encoding='unicode');m=mj.MjModel.from_xml_path(str(OUT/'robot.xml'));parent=mj.MjModel.from_xml_path(str(SRC/'robot.xml'));mj.mj_saveModel(m,str(OUT/'actual_scene.mjb'));z=np.load(SRC/'initial_state.npz');d=mj.MjData(m);d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];mj.mj_forward(m,d);np.savez_compressed(OUT/'initial_state.npz',qpos=d.qpos,qvel=d.qvel)
arrays={n:bool(np.array_equal(getattr(m,n),getattr(parent,n)))for n in['jnt_axis','jnt_pos','jnt_range','dof_armature','dof_damping','dof_frictionloss','geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_condim','geom_solref','geom_solimp','actuator_gear','actuator_gainprm','actuator_biasprm','eq_data','eq_solref','eq_solimp']};assert all(arrays.values());assert abs(m.body_mass.sum()-total)<1e-10
changed=[mj.mj_id2name(m,mj.mjtObj.mjOBJ_BODY,i)for i in range(m.nbody)if not np.array_equal(m.body_mass[i],parent.body_mass[i])or not np.array_equal(m.body_ipos[i],parent.body_ipos[i])or not np.array_equal(m.body_inertia[i],parent.body_inertia[i])];assert changed==['beak_hinge']
write(OUT/'compiled_readback.json',dict(physics_steps=0,mass_kg=float(m.body_mass.sum()),delta_kg=delta,changed_MCI_bodies=changed,actual_body_MCI=dict(mass_kg=M,COM_zero_m=C.tolist(),I_com_kg_m2=IC.tolist()),unchanged_source_arrays=arrays,initial_ncon=int(d.ncon),runtime_axial_model='Ideal body/hinge bookkeeping; washer/axialfloat/loss dynamics unmodeled',limits=plan['unresolved']))
write(OUT/'thrust037_guard_condition.json',dict(handoff=ref(H),conditional_symmetric_O_N=40.,C_N=100.,minwasher_Sy_MPa=200,originalfactor6=True,actual_runtime_guard_not_changed=True,qualification='New explicit12runner/config and Rootauthorization needed; no hot swap11; no manufacturing or physicalcapacity pass'))
for n in['actuator_contract.json','runtime_interface.json']:
 x=json.loads((OUT/n).read_text());x['release_id']=OUT.name;x['thrust037_no_new_motor_cap']=True;write(OUT/n,x)
write(OUT/'hardware_change_receipt.json',dict(parent=ref(SRC/'manifest.json'),handoff=ref(H),retired=sorted(ret),added=['thrust037_'+x['name']for x in h['parts']],delta_mass_kg=delta,native=ref(NO/'merged_native_manifest.json'),original_outer_skin_pads_unchanged=True,thread_mass_uncertainty_upper_g=.225,physics_steps=0))
manifest=json.loads((SRC/'manifest.json').read_text());manifest.update(release_id=OUT.name,status=status);manifest['qualification_limits']+=plan['unresolved'];manifest['files']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='manifest.json'and '__pycache__'not in p.parts};write(OUT/'manifest.json',manifest);assert before=={str(p.relative_to(SRC)):sha(p)for p in SRC.rglob('*')if p.is_file()and '__pycache__'not in p.parts};print(json.dumps(dict(candidate=str(OUT),mass=total,delta=delta,manifest_sha256=sha(OUT/'manifest.json'),physics_steps=0)))
