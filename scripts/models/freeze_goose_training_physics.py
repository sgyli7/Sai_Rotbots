"""Freeze actual whole05 plus explicitly named design allocations, not CAD completion."""
from __future__ import annotations
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'artifacts/goose_v0_2/physics_freeze_20261018_01'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,m):p.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
def source(p):return dict(repository_path=str(p.relative_to(ROOT)),sha256=digest(p),required_at_runtime=False)
def combine(rows):
 mass=sum(x['mass_kg']for x in rows);com=sum(x['mass_kg']*np.array(x['centre_zero_mm'])/1000 for x in rows)/mass;I=np.zeros((3,3))
 for r in rows:
  d=np.array(r['centre_zero_mm'])/1000-com;I+=np.array(r['inertia_at_com_zero_kg_m2'])+r['mass_kg']*(d@d*np.eye(3)-np.outer(d,d))
 I=(I+I.T)/2;e=np.linalg.eigvalsh(I)
 if e[0]<=0 or e[2]>e[0]+e[1]+1e-10:raise ValueError('Invalid aggregate inertia')
 return mass,com,I

def row_from_native(r):
 return dict(name=r['name'],body=r['body'],mass_kg=r['mass_kg'],centre_zero_mm=(np.array(r['center_of_mass_world_m'])*1000).tolist(),inertia_at_com_zero_kg_m2=r['inertia_at_com_world_kg_m2'],inertia_basis='Declared source-native completeMCI used as fixed engineering distribution; physical installation/manufacturing not claimed',group='simulation_engineering_allocation',native_mass_coverage=[],declared_source_native=r.get('native_source'),measured=False)

def main(a):
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 bp=R/'integration_release/whole_core_review_05_mass/conditional_mass_ledger.json';sp=R/'integration_release/whole05_complete_counterbalance_readback_01/whole05_full_SI_contract.json';ep=R/'thermal_manufacturing/simulation_mass_contract_0519_01/E_simulation_mass_contract.json';axis=ROOT/'robots/goose_v0_2/configs/v01_frozen_reference_contract.json';fp=ROOT/'robots/goose_v0_2/hardware/actuator_facts.json';wh=R/'integration_release/whole_core_review_05/integration.json'
 ledger=read(bp);physical=read(sp);E=read(ep);old=read(axis);facts=read(fp);items=copy.deepcopy(ledger['items']);before=sum(x['mass_kg']for x in items);ops=[]
 for op in E['operations_for_F_to_apply_once']:
  nr=op['new']
  if op['operation']=='replace_existing_cap04_with_access_cap':
   ix=next(i for i,x in enumerate(items)if x['name']=='rear_service_cap');prev=items[ix];assert abs(prev['mass_kg']-op['old']['mass_kg'])<1e-10;items[ix]=row_from_native(nr);ops.append(dict(operation='replace',old=prev,new=items[ix]))
  elif op['operation']=='add_separate_protection_cup':
   nr=copy.deepcopy(nr);nr['name']='engineering_allocation/'+nr['name'];r=row_from_native(nr);assert r['name']not in {x['name']for x in items};items.append(r);ops.append(dict(operation='add',new=r))
  elif op['operation']=='add_once_internal_NC_whole14g':
   r=dict(name='engineering_allocation/internal_recessed_nc_whole_unit',body=nr['body'],mass_kg=nr['mass_kg'],centre_zero_mm=nr['com_world_zero_mm'],inertia_at_com_zero_kg_m2=nr['uniform_or_actual_inertia_com_world_kg_m2'],inertia_basis=nr['basis'],group='simulation_engineering_allocation',native_mass_coverage=[],measured=False);assert r['name']not in {x['name']for x in items};items.append(r);ops.append(dict(operation='add',new=r))
  else:raise ValueError('Unknown E operation')
 for r in E['remaining_original_E25_engineering_allocations']:
  rr=row_from_native(dict(r,name='engineering_allocation/'+r['name']));rr.update(inertia_basis=r['basis'],allocation_box_mm=r['allocation_box_mm']);assert rr['name']not in{x['name']for x in items};items.append(rr);ops.append(dict(operation='add_unconsumed_budget',new=rr))
 total=sum(x['mass_kg']for x in items);assert abs(total-before-E['accounting']['E_only_net_delta_vs_whole05_kg'])<1e-10
 # These inputs all belong to fixed torso. Every other body is copied bytewise
 # as numerical data from the actual23body source, preserving jaw/input splits.
 torso=next(b for b in physical['bodies']if b['name']=='torso');mass,com,I=combine([x for x in items if x['body']=='torso']);torso.update(mass_kg=mass,centre_world_zero_m=com.tolist(),com_local_m=(com-np.array(torso['origin_world_zero_m'])).tolist(),inertia_at_com_body_kg_m2=I.tolist(),inertia_at_com_world_zero_kg_m2=I.tolist(),source_mass_items=[x['name']for x in items if x['body']=='torso']);physical['nominal_robot_mass_kg']=total
 for j in physical['passive_linkage_joints']:
  if j['name']=='beak_coupler_link':j.update(physical_angular_stop=False,range_rad_is_nominal_linkage_branch_not_separate_hard_stop=True)
 loss_source=R/'structural_topology/CRBT_real_head_roll_drive_loss_budget_01/head_roll_once_only_loss_and_fit_budget.json'
 next(j for j in physical['joints']if j['name']=='head_roll')['frictionloss_nm']=.036
 physical.update(schema='goose_v0_2_frozen_design_physics_v1',release_id='physics_v0_2_20261018_01',status='FIXED_DESIGN_MCI_AND_AXES_RUNTIME_CONTACT_VALIDATION_SEPARATE',contract_revision=2,head_roll_CRBT_once_only_frictionloss_nm=.03,physics_dt_s=.005,torque_dt_s=.005,policy_dt_s=.02,physics_steps_per_tick=4,torque_updates_per_tick=4,policy_calls_per_tick=1,action_size=18,root_origin_at_zero_m=[0,0,0],observation_size=65,observation_layout=old['observation_layout'],action_semantics='18 normalized positiontargets; clamp[-1,1], rangeclamp, slew byselectedspeed; 200Hz PD effort on actualmotor/input coordinate; continuous caps, torque-speed and350W positive mechanical power; no gravityfeedforward/reward/task in referenceadapter',beak_transmission=copy.deepcopy(old['beak_transmission']),sources=[source(p)for p in[bp,sp,ep,axis,fp,wh,loss_source]],engineering_allocation_delta_kg=total-before,mass_and_inertia_measured=False,hardware_manufacturing_released=False,training_task_policy_or_rewards_included=False,hardware_followup_rule='No change to saved rigidmass/COM/fullI/axes/outercontacts/actuatorcontract. Future hardwarechanges require a separately versioned physics package; never overwrite this release.')
 for nm,ref in [('drive_axis_world_m','beak_input_rotor'),('jaw_axis_world_m','beak_hinge')]:
  physical['beak_transmission'][nm]=next(j for j in physical['joints']+physical['passive_linkage_joints']if j['name']==ref)['pivot_world_at_zero_m']
 axes=[]
 for j in physical['joints']:
  key=j['actuator'];curvekey='ak45_36_v3'if'parallel_crank'in key else 'xc330_preserved_design'if key=='xc330_m288_t'else key;f=facts['curves'][curvekey];servo=curvekey=='xc330_preserved_design';gear=288.35 if servo else 36 if curvekey=='ak45_36_v3'else 10
  row=dict(name=j['name'],model='XC330-M288-T'if servo else f['model'],actuated_joint=j.get('actuation_joint',j['name']),selected_continuous_design_limit_nm=j['continuous_design_limit_nm'],selected_peak_design_limit_nm=j['torque_peak_limit_nm'],selected_speed_limit_rad_s=j['speed_limit_rad_s'],kp_nm_rad=j['kp_nm_rad'],kd_nm_s_rad=j['kd_nm_s_rad'],manufacturer_rated_torque_nm=f['rated_torque_nm'],manufacturer_peak_or_stall_nm=.93 if servo else f['peak_torque_nm'],reference_voltage_v=5. if servo else 24.,simulation_voltage_window_v=[5,5]if servo else[20,25.2],selected_torque_speed_curve_rad_s_nm=f['speed_rad_s_torque_nm'],gear_ratio=gear,xml_actuator_gear=1.,reflected_gear_inertia_already_in_joint_armature=True,damping_nm_s_rad=j['damping_nm_s_rad'],logical_joint_frictionloss_nm=j['frictionloss_nm'],actual_drive_joint_frictionloss_nm=next((x.get('frictionloss_nm',0)for x in physical['passive_linkage_joints']if x['name']==j.get('actuation_joint')),j['frictionloss_nm']),armature_at_logical_joint_kg_m2=j['armature_kg_m2'],electrical_encoder_sign=j.get('actual_motor_electrical_angle_sign',1.),source_url='https://emanual.robotis.com/docs/en/dxl/x/xc330-m288/'if servo else f['url'],source_basis='ManufacturerM28823g/288.35/5V; selected .14/.18Nm and3rad/s deliberatelyretained design derating, not measured continuous manufacturer rating'if servo else f['basis'],runtime_default_enforcement='Continuous effort force/ctrl clamps inXML; 200Hz adapter additionally torque-speed/slew andaggregatepower. Peak disabled; no hidden duration or thermalmodel.')
  axes.append(row)
 drive=dict(schema='goose_v0_2_fixed_drive_contract_v1',release_id=physical['release_id'],default_mode='continuous_only',axes=axes,positive_mechanical_power_limit_w=float(old['positive_mechanical_power_limit_w']),peak_output_enabled=False,peak_duration_s=None,thermal_model_implemented=False,negative_power_regeneration_model_implemented=False,reference_adapter='src/sai_agent/goose/frozen_physics_runtime.py',timing=dict(physics_dt_s=.005,drive_dt_s=.005,policy_dt_s=.02),power_supply=dict(main='6S battery designbus20..25.2V, reference curves24V; no performancecredit above24V',nominal_bus_v=22.2,torque_speed_curve_reference_v=24,head_roll='Regulated5V branch for XC330-M288; old factstable24V inheritedfield is explicitly rejected',mechanical_positive_budget_w=350.,electrical_power_or_current_hard_cap_implemented=False,efficiency_and_voltage_sag='Not measured/simulated;350W is mechanical designbudget, not electrical wattmeter/currentguarantee',high_voltage_derating='For bus below24V adapter speed-axis of curves scaleslinearly byV/24; no additionaltorquecredit',brake='Negative mechanical power is not freeenergy claim; regenerative voltage/brake/thermal hardware pending'),manufacturer_sources_checked_UTC='2026-10-18',caveats=['No long-duration manufacturer thermal rating inferred from peak or stall','Damping/backdrive/friction are selected design assumptions; not benchidentified','Continuous caps are immutable default; optional transient peak needs a new explicit validated driveprofile','Rate andpowerenforcement is adapter responsibility if another engine directly loads theMJCF'])
 ledger.update(schema='goose_frozen_design_physical_mass_ledger_v1',status='FROZEN_SIMULATION_MASS_DISTRIBUTION_NOT_INSTALLED_HARDWARE',items=items,nominal_mass_kg=total,original_whole05_mass_kg=before,engineering_operations=ops,engineering_mass_patch=source(ep),all_additions_are_explicit_design_allocations_not_manufacturing_claims=True)
 save(out/'mass_ledger.json',ledger);save(out/'physical_contract.json',physical);save(out/'actuator_contract.json',drive);save(out/'engineering_mass_patch.json',E);save(out/'actuator_source_facts.json',facts)
 save(out/'source_snapshot.json',dict(release_id=physical['release_id'],whole05=source(wh),source_tuple=source(R/'integration_release/whole05_selected_source_packet_04/ordered_geometry_metadata.json'),source_SI=source(sp),E=source(ep),correct_six_foot_source=source(R/'form_mechanics/foot_physics_priority_checkpoint_01/foot_physics_priority_checkpoint.json'),head10_actual_not_head17=True,source_paths_are_provenance_not_runtime_dependencies=True))
 save(out/'freeze_summary.json',dict(total_mass_kg=total,body_count=len(physical['bodies']),public_axes=18,internal_coordinates=4,E_delta_kg=total-before,physical_contract_sha256=digest(out/'physical_contract.json'),actuator_contract_sha256=digest(out/'actuator_contract.json'),mass_ledger_sha256=digest(out/'mass_ledger.json')));print((out/'freeze_summary.json').read_text())

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args())
