"""Immutable10 + explicit frozen033 identity-r02. Native/model ZERO steps only."""
from pathlib import Path
import json,hashlib,copy,shutil,importlib.util,xml.etree.ElementTree as ET
import numpy as np,sys
W=Path(__file__).resolve().parents[2];SRC=W/'robots/goose_v0_2/models/physics_v0_2_20261021_10_candidate';OUT=W/'robots/goose_v0_2/models/physics_v0_2_20261021_11_candidate';H=W/'experiments/goose_v0_2/output_thrust_upgrade_033/c01/integration_handoff_identity_r02.json';PLAN=W/'experiments/goose_v0_2/full_native_head_integration_026/merge_plan_r07_fork_c02.json';NP=W/'experiments/goose_v0_2/output_thrust_upgrade_033/c01/merge_plan_11_identity_r02.json';NO=W/'robots/goose_v0_2/cad/exports/full_native_head_integration_026/r08_thrust033_identity_r02_review'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def write(p,j):p.write_text(json.dumps(j,indent=2)+'\n')
def ten(v):
 a=np.asarray(v,float)
 if a.shape==(3,3):return a
 x,y,z,xy,xz,yz=a;return np.array([[x,xy,xz],[xy,y,yz],[xz,yz,z]])
def inertia0(m,c,I):c=np.array(c)*.001;return ten(I)+m*((c@c)*np.eye(3)-np.outer(c,c))
resume='--resume-zero-staging' in sys.argv
if OUT.exists():
 assert resume and not(OUT/'thrust033_guard_condition.json').exists()
 assert json.loads((OUT/'manifest.json').read_text())['release_id']==SRC.name
else:assert not resume
assert sha(H)=='b69cadb8178a6b26aaa5e4d3772483778cd27f5c3b9597b3bc9b4a1ff7677b39'
h=json.loads(H.read_text());plan=json.loads(PLAN.read_text());old={p['name']:p for p in plan['new_parts']};ret=set(h['retired_exact_names']);assert len(ret)==6 and ret<=set(old)
plan['new_parts']=[p for p in plan['new_parts']if p['name']not in ret]
for p in h['parts']:
 f=W/p['native']['path'];assert sha(f)==p['native']['sha256'];I=ten(p['I_com_kg_m2']);assert np.linalg.eigvalsh(I).min()>0
 plan['new_parts'].append(dict(name=p['new_name'],body=p['body'],source=p['native'],handoff_owner='support_carrier',material=p.get('material','Original rear catalog bearing'),translation_to_zero_mm=[-13.55,0,32.305],rotation_xyz_deg=[0,0,0],catalogue_envelope_only='nk12' in p['name'],mci=dict(mass_kg=p['mass_kg'],com_zero_mm=(np.array(p['COM_native_mm'])+[-13.55,0,32.305]).tolist(),inertia_com_kg_m2=[I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]],inertia_status=p.get('inertia_status','Frozen source native tensor'))))
plan.update(candidate_id='intact_full_head_11_thrust033_identity_r02',parent_plan=ref(PLAN),incremental_retired_exact_names=sorted(ret),incremental_handoff=ref(H));plan['handoffs']['support_carrier']=ref(H);plan['unresolved']+=h['install_limits']+['Translated OCP Boolean had non-SE3-invariant false positives; bounded native-source q0/.1513 old/new frame comparison 0. No manufacturing or general clearance qualification.']
if NP.exists():assert json.loads(NP.read_text())==plan
else:write(NP,plan)
spec=importlib.util.spec_from_file_location('merge',W/'scripts/cad/goose_full_head_candidate_merge_026.py');mer=importlib.util.module_from_spec(spec);spec.loader.exec_module(mer);baseline=mer.validate(plan)
if not NO.exists():mer.build(plan,baseline,NO)
else:assert json.loads((NO/'merged_native_manifest.json').read_text())['candidate_id']==plan['candidate_id']
if '--native-only' in sys.argv:
 print(json.dumps(dict(native=str(NO),plan_sha=sha(NP),physics_steps=0)));sys.exit(0)
import mujoco as mj
parent_files={str(p.relative_to(SRC)):sha(p)for p in SRC.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
shutil.copytree(SRC,OUT,ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=resume);shutil.copy2(H,OUT/'source_inputs/thrust033_identity_r02.json');shutil.copy2(SRC/'manifest.json',OUT/'source_inputs/parent10_manifest.json')
pc=json.loads((OUT/'physical_contract.json').read_text());ledger=json.loads((OUT/'mass_ledger.json').read_text());items={p['name']:p for p in ledger['items']};assert ret<=set(items)
xml=ET.parse(OUT/'robot.xml');root=xml.getroot();root.set('model',OUT.name);changed={};anchors={'head_roll':np.array([67.45,0,617.805]),'beak_hinge':np.array([146.45,0,608.305])}
for body in anchors:
 row=next(r for r in pc['bodies']if r['name']==body);mass=row['mass_kg'];com=np.array(row['centre_world_zero_m'])*1000;I=ten(row['inertia_at_com_world_zero_kg_m2']);M=mass;F=mass*com*.001;I0=inertia0(mass,com,I)
 for p in h['parts']:
  if p['body']!=body:continue
  o=items[p['retired_final_part']['name']];m=o['mass_kg'];c=o['centre_zero_mm'];ii=o['inertia_at_com_zero_kg_m2'];M-=m;F-=m*np.array(c)*.001;I0-=inertia0(m,c,ii)
  m=p['mass_kg'];c=np.array(p['COM_native_mm'])+[-13.55,0,32.305];ii=ten(p['I_com_kg_m2']);M+=m;F+=m*c*.001;I0+=inertia0(m,c,ii)
 C=F/M;IC=I0-M*((C@C)*np.eye(3)-np.outer(C,C));assert np.linalg.eigvalsh(IC).min()>0
 row.update(mass_kg=float(M),centre_world_zero_m=C.tolist(),inertia_at_com_world_zero_kg_m2=IC.tolist(),inertia_at_com_body_kg_m2=IC.tolist(),com_local_m=(C-anchors[body]*.001).tolist());changed[body]=dict(mass_kg=float(M),com_zero_mm=(C*1000).tolist(),fullI_kg_m2=IC.tolist())
 node=root.find(f".//body[@name='{body}']/inertial");node.attrib.clear();node.set('mass',format(M,'.17g'));node.set('pos',' '.join(format(v,'.17g')for v in C-anchors[body]*.001));node.set('fullinertia',' '.join(format(v,'.17g')for v in [IC[0,0],IC[1,1],IC[2,2],IC[0,1],IC[0,2],IC[1,2]]))
ledger['items']=[p for p in ledger['items']if p['name']not in ret]
for p in h['parts']:ledger['items'].append(dict(name=p['new_name'],body=p['body'],mass_kg=p['mass_kg'],centre_zero_mm=(np.array(p['COM_native_mm'])+[-13.55,0,32.305]).tolist(),inertia_at_com_zero_kg_m2=ten(p['I_com_kg_m2']).tolist(),source=p['native'],engineering_approximation='nk12' in p['name']))
delta=sum(p['mass_kg'] for p in h['parts'])-sum(items[n]['mass_kg']for n in ret);total=pc['nominal_robot_mass_kg']+delta
pc.update(release_id=OUT.name,status='EXPERIMENTAL_THRUST033_ZERO_STEP_NOT_RUNTIME_ADMITTED',nominal_robot_mass_kg=total,thrust033_handoff=ref(H),current_native_manifest=ref(NO/'merged_native_manifest.json'))
pc['source_identity']['parent10_manifest']=ref(SRC/'manifest.json');pc['source_identity']['current_native']=ref(NO/'merged_native_manifest.json')
ledger.update(status=pc['status'],nominal_mass_kg=total,current_parent_mass_kg=total-delta,current_mass_delta_kg=delta,current_retired_items=sorted(ret),current_added_items=[p['new_name']for p in h['parts']],thrust033_handoff=ref(H),limits=h['install_limits'])
for row in pc['bodies']:
 if row['name']in changed:row['source_mass_items']=[p['name']for p in ledger['items']if p['body']==row['name']];row['item_count']=len(row['source_mass_items'])
write(OUT/'mass_ledger.json',ledger);pc['source_identity']['current_mass']=ref(OUT/'mass_ledger.json');pc['source_identity']['incremental_mass_handoff']=ref(H);write(OUT/'physical_contract.json',pc)
for n in root.find('custom'):
 if n.get('name')=='physical_contract_sha256':n.set('data',sha(OUT/'physical_contract.json'))
 if n.get('name')=='status':n.set('data',pc['status'])
xml.write(OUT/'robot.xml',encoding='unicode');m=mj.MjModel.from_xml_path(str(OUT/'robot.xml'));oldm=mj.MjModel.from_xml_path(str(SRC/'robot.xml'));mj.mj_saveModel(m,str(OUT/'actual_scene.mjb'));d=mj.MjData(m);z=np.load(SRC/'initial_state.npz');d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];mj.mj_forward(m,d);np.savez_compressed(OUT/'initial_state.npz',qpos=d.qpos,qvel=d.qvel)
arrays={n:bool(np.array_equal(getattr(m,n),getattr(oldm,n)))for n in ['jnt_axis','jnt_pos','jnt_range','dof_armature','dof_damping','dof_frictionloss','geom_type','geom_size','geom_pos','geom_quat','geom_friction','geom_condim','geom_solref','geom_solimp','actuator_gear','actuator_gainprm','actuator_biasprm','eq_data','eq_solref','eq_solimp']};assert all(arrays.values())
assert abs(m.body_mass.sum()-total)<1e-10
olddata=mj.MjData(oldm);olddata.qpos[:]=z['qpos'];olddata.qvel[:]=z['qvel'];mj.mj_forward(oldm,olddata)
assert d.ncon==olddata.ncon and all(abs(a.dist-b.dist)<1e-12 and a.geom1==b.geom1 and a.geom2==b.geom2 for a,b in zip(d.contact,olddata.contact))
for name in ['beak_input_rotor','beak_coupler_link']:assert np.array_equal(m.body_inertia[m.body(name).id],oldm.body_inertia[oldm.body(name).id])
write(OUT/'compiled_readback.json',dict(schema='thrust033_zero_step_v1',physics_steps=0,parent=ref(SRC/'manifest.json'),mass_kg=float(m.body_mass.sum()),delta_kg=delta,changed_body_MCI=changed,unchanged_arrays=arrays,initial_ncon=int(d.ncon),clock={'physics_dt':m.opt.timestep,'drive_dt':.005,'reference_dt':.02},internal_axial_model='No new axial DoF/actual washer contact in runtime; rigid body MCI only. Capacity upgrade is engineering static-screen condition, not dynamic validation.',limits=h['install_limits']))
write(OUT/'thrust033_guard_condition.json',dict(handoff=ref(H),new_symmetric_O_axial_condition_N=h['symmetric_conditional_allow_N'],C_condition_N=100.,active_runner_guard_not_changed=True,old_candidate10_guard_preserved=True,qualification='Do not hot apply new guard; Owner must authorize explicit candidate11 runner/config',manufacturing_qualified=False))
for n in ['actuator_contract.json','runtime_interface.json']:
 j=json.loads((OUT/n).read_text());j['release_id']=OUT.name;j['thrust033_candidate_no_new_drive_cap']=True;write(OUT/n,j)
write(OUT/'hardware_change_receipt.json',dict(parent=ref(SRC/'manifest.json'),handoff=ref(H),retired=sorted(ret),added=[p['new_name']for p in h['parts']],delta_kg=delta,native=ref(NO/'merged_native_manifest.json'),outer_original_unchanged=True,physics_steps=0))
manifest=json.loads((SRC/'manifest.json').read_text());manifest.update(release_id=OUT.name,status=pc['status']);manifest['qualification_limits']+=h['install_limits'];manifest['files']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='manifest.json'and '__pycache__'not in p.parts};write(OUT/'manifest.json',manifest)
assert parent_files=={str(p.relative_to(SRC)):sha(p)for p in SRC.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
print(json.dumps(dict(candidate=str(OUT),native=str(NO),mass=total,delta=delta,manifest_sha=sha(OUT/'manifest.json'),physics_steps=0)))
