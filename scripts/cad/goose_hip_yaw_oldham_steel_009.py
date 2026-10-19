"""Unchanged real Oldham geometry, wrought 17-4PH H900 material candidate.

Produces only an independent source/MCI packet. No assembly, drive cap,
collision, or controller file is changed. FE qualification is a separate input.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np
import build123d as bd
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

W=Path(__file__).resolve().parents[2]
BASE=W/'artifacts/goose_v0_2/tangpa_mango_ankle_integration_34/whole_stage_01/mango_primary_form_reset_01/whole_body_architecture_05'
OLD=BASE/'upper_short_yaw_delivery_47_actual_drive_08'

def ident(p):
    return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def run(fe):
    R=W/'robots/goose_v0_2'
    C=R/'cad/source/hip_yaw_oldham_steel_009/c01'
    E=R/'evidence/hip_yaw_oldham_steel_009/c01'
    X=R/'cad/exports/hip_yaw_oldham_steel_009/c01'
    for p in [C,E,X]:p.mkdir(parents=True,exist_ok=True)
    idx=R/'cad/source/drag_hardware_integration_009_06/assembly_index.json'
    ledger=json.loads(idx.read_text());parts=[];deltas=[]
    for side,ii in [('left',901),('right',939)]:
        old=ledger['parts'][ii]
        p=C/f'{side}_yaw_drive_oldham_17_4ph_h900_009_c01.brep'
        original=OLD/f'{side}_yaw_drive_oldham_FCD400_cross_slider.brep'
        source=original if original.exists() else p
        assert source.exists(), 'Need retained exact native source, never synthesize a substitute'
        if source != p:shutil.copyfile(source,p)
        s=bd.import_brep(p)
        assert len(s.solids())==1 and BRepCheck_Analyzer(s.wrapped).IsValid()
        g=GProp_GProps();err=BRepGProp.VolumeProperties_s(s.wrapped,g,1e-9,True,False)
        v=float(g.Mass());com=np.array(g.CentreOfMass().Coord())/1000
        I=np.array([[g.MatrixOfInertia().Value(a+1,b+1)for b in range(3)]for a in range(3)])*7800e-15
        m=v*7800e-9
        assert abs(v-old['native_volume_mm3'])<1e-6
        assert np.max(abs(com-np.array(old['center_of_mass_world_m'])))<1e-10
        assert np.max(abs(I-np.array(old['inertia_at_com_world_kg_m2'])*7800/7100))<1e-13
        step=X/f'{side}_yaw_drive_oldham_17_4ph_h900_009_c01.step'
        bd.export_step(s,step);rr=bd.import_step(step)
        assert len(rr.solids())==1 and abs(rr.volume-v)<1e-5
        r={'name':p.stem,'body':old['body'],'retired_name':old['name'],
          'retired_native_index06':ii,'retired_item':old,'source':ident(p),
          'unchanged_original_source':ident(source),'source_bytes_exactly_equal':p.read_bytes()==source.read_bytes(),
          'source_to_target_world_zero_4x4':np.eye(4).tolist(),
          'native_volume_mm3':v,'center_of_mass_world_m':com.tolist(),
          'inertia_at_com_world_kg_m2':I.tolist(),'mass_kg':m,
          'material':'wrought_UNS_S17400_17_4PH_H900_certified_condition_required',
          'density_kg_m3':7800.,'signed_positive_solids':1,'native_BRepCheck_valid':True,
          'native_unchanged_SI_result_inherited_from_retired06':old['native_quality'],
          'integration_error':err,'step':ident(step),'step_readback':{'solids':1,'volume_mm3':rr.volume,'BRepCheck_valid':BRepCheck_Analyzer(rr.wrapped).IsValid()},
          'actual_part_weighed_or_heat_treated':False}
        parts.append(r)
        om=old['mass_kg'];oc=np.array(old['center_of_mass_world_m']);oi=np.array(old['inertia_at_com_world_kg_m2'])
        raw=lambda mass,c,inertia:inertia+mass*((c@c)*np.eye(3)-np.outer(c,c))
        deltas.append({'owner':r['body'],'retired_name':old['name'],'new_name':r['name'],
          'delta_mass_kg':m-om,'delta_first_moment_world_kg_m':(m*com-om*oc).tolist(),
          'delta_inertia_about_world_origin_kg_m2':(raw(m,com,I)-raw(om,oc,oi)).tolist()})
    packet={'candidate_id':'hip_yaw_oldham_steel_009_c01','source':ident(Path(__file__)),
      'status':'OWNER_FINITE_STATIC_AB_PROTOTYPE_CHAIN1P8_NOT_RUNTIME_APPLIED',
      'parent_native_06_index':ident(idx),'replacement_parts':parts,'body_raw_moment_deltas':deltas,
      'nominal_pair_mass_increase_kg':sum(r['mass_kg']-r['retired_item']['mass_kg']for r in parts),
      'geometry_axes_neutral_ratio_collision_or_provider_changed':False,'physics_steps':0,
      'material_choice':'Wrought17-4PH ConditionH900; no cast/AM equivalent, no unaged ConditionA substitution.',
      'cost_boundary':{'net_finished_material_mass_g_per_part':parts[0]['mass_kg']*1000,
        'example_round_blank_size_mm':[20,5],
        'example_two_round_blanks_mass_g':2*np.pi*10**2*5*7800e-6,
        'new_custom_types':1,'quantity':2,
        'cost_rationale':'No extra adapter/space/fastener; only tiny custom slider material changes. Small-lot machining, root finishing and certified heat treatment likely dominate raw stock.',
        'actual_material_machining_heat_treatment_quote_received':False,
        'lowest_market_price_claimed':False},
      'procurement_requirements':{'standards':'UNS S17400 / ASTM A564 bar or AMS5643, material and heat treatment certificate; procurement minimum yield1170MPa must be explicitly accepted by supplier, not inferred from a typical-property value.',
        'required_yield_MPa':1170,'required_hardness_HRC':[40,47],
        'commercial_product_form_source':'https://www.carpentertechnology.com/hubfs/7407324/Material%20Saftey%20Data%20Sheets/Custom%20630%20%2817-4%20PH%29.pdf',
        'stock_leadtime_and_actual_price_verified':False,'material_order_placed':False},
      'process_requirements':{'heat_treatment':'Certified solution-treated wrought stock; H900482±5°C for60±5min then air cool, with batch coupon/certification. Prefer certified pre-aged bar followed by finish machining, or rough machine ConditionA then age and finish-grind mating faces.',
        'H900_shrinkage_strain_from_ConditionA':[.0004,.0006],
        '18mm_diameter_nominal_contraction_mm':[.0072,.0108],
        '3mm_tongue_width_nominal_contraction_mm':[.0012,.0018],
        'geometry_is_final_finished_H900_size':True,
        'sliding_side_clearance_each_mm':.02,'axial_face_clearance_mm':.1,'groove_bottom_clearance_mm':.2,
        'final_tolerance_requirement':'Re-measure both20µm side clearances, rootR.1,1mmweb andflatness after heat treatment; proposed tongue width±.005mm and parallelism/flatness≤.01mm require process qualification. No new geometry tolerance is silently added to frozen source.',
        'surface_finish_proposal_not_measured':'Finish-grind/lap sliding flanks Ra≤.8µm, deburr without reducingR.1 roots. Not an achieved surface measurement.'},
      'wear_and_life_boundary':{'counterfaces':'Existing C45_QT lower output flange and upper hub/shaft retained; separate SKF bearings still carry belt load.',
        'lubrication':'Existing grease/wear requirement retained. Grease compatibility and replenishment intervals need bench qualification; no dry-running or unlubricated endurance claim.',
        'risks':['Harder H900 slider may transfer wear to softer C45 grooves; inspect backlash/scuffing and grease debris.','H900 peak-strength material has lower impact toughness and poorer chloride-SCC margin than higher-temperature-aged states; no crash/cleaning-chemical/fatigue certification.','Reversed torque, misalignment, impact and unilateral sliding contact are not covered by the bilateral linear FE screen.'],
        'runtime_friction_change_measured':False},
      'integration_boundary':'Only retire the two exact Oldham occurrences after source identity matches formal07; add raw MCI deltas without overwriting07 whole-body masses. No direct runtime cap approval. Owner must separately adopt motor+slider packet and remaining transmission assumptions.',
      'manufacturing_fatigue_wear_released':False,'2Nm_actual_admission_by_this_script':False,
      'owner_selected_chain_continuous_torque_Nm':1.8,
      'owner_decision_boundary':'Owner accepts only finite static hardwareA/B prototype at1.8Nm continuous chain cap; not2Nm, no lifetime/manufacturing qualification. Existing runtime07 remains unchanged.'}
    if fe:
        data=json.loads(fe.read_text());packet['two_mesh_screen']=ident(fe)
        packet['static_screen_status']=data['status']
        packet['guarded_static_result']=data.get('mesh_allowance_screen')
        fine=data['cases'][-1]
        peak=fine['von_mises_MPa']['max']*.9
        packet['1p8Nm_linear_elastic_screen_NOT_new_FE']={
          'from_actual_2Nm_solution_linear_scale':.9,'stress_MPa':peak,
          'displacement_mm':fine['max_displacement_mm']*.9,
          'mesh_guard':1.2,'guarded_stress_MPa':peak*1.2,
          'required_yield_MPa':1170.,'allowable_at_SF2_MPa':585.,
          'guarded_yield_SF':1170/(peak*1.2),
          'guard_is_not_strict_convergence_or_contact_error_bound':True}
    motor=R/'evidence/hip_yaw_ak45_upgrade_009/c01/integration_handoff.json'
    motorpacket=json.loads(motor.read_text())
    proposal=[]
    for entry in motorpacket['proposed_actuator_changes_NOT_applied']:
        r=dict(entry)
        r['motor_selected_continuous_cap_Nm']=r.pop('proposed_continuous_cap_Nm')
        r['owner_chain_continuous_cap_Nm']=1.8
        r['final_selected_continuous_cap_Nm']=1.8
        r['selected_peak_design_limit_Nm']=1.8
        r['public_torque_peak_limit_Nm']=1.8
        r['peak_enabled']=False
        r['all_actual_execution_modes_chain_hard_cap_Nm']=1.8
        r['limit_semantics']='Motor manufacturer24V rated2.5Nm and existing80% design motor cap2.0Nm remain separate; Owner chain cap1.8Nm applied as min, not as invented72% manufacturer curve.'
        r['continuous_torque_envelope']='min(1.8Nm chain cap,2.0Nm selected motor cap, AK45 manufacturer24V chord curve with engineering22.2/24 speed scaling); source selected speed limit11.623892818282236rad/s; no peak, no48V credit.'
        proposal.append(r)
    packet['combined_motor_and_slider_proposal']={
      'motor_input_packet':ident(motor),'motor_original_2Nm_block_status_preserved_as_history':True,
      'replacement_parts':motorpacket['replacement_parts']+parts,
      'retired_occurrences':motorpacket['retired_occurrences']+[
        {'name':r['retired_name'],'body':r['body'],'ledger_item':r['retired_item']}for r in parts],
      'body_raw_moment_deltas':motorpacket['body_raw_moment_deltas_relative06_ONLY_motor_items']+deltas,
      'nominal_mass_delta_kg':.144+sum(r['mass_kg']-r['retired_item']['mass_kg']for r in parts),
      'proposed_actuator_changes_NOT_applied':proposal,
      'implementation_owner':'F integrates new08 only after Owner approval; no hot overwrite07.',
      'replacement_occurrence_count':6,'new_custom_material_types':1,
      'old_source_collision_and_contact_changes':False}
    p=E/'integration_handoff.json';p.write_text(json.dumps(packet,indent=2)+'\n')
    print(json.dumps({'packet':ident(p),'pair_mass_increase_kg':packet['nominal_pair_mass_increase_kg'],'parts':[(r['name'],r['mass_kg'])for r in parts]}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fe',type=Path);run(p.parse_args().fe)
