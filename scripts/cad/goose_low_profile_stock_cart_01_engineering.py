"""Recompute stated analytical design screens from current CAD mass ledger."""
from pathlib import Path
import json,math,itertools,hashlib
W=Path(__file__).resolve().parents[2];E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01'
p=json.loads((E/'geometry_mass_screen.json').read_text());previous=json.loads((W/'robots/goose_v0_2/cad/source/low_profile_stock_cart_01/analytical_screen_assumptions.json').read_text())
M=p['gross_mass_kg'];m=p['estimated_empty_mass_kg'];ec=p['estimated_empty_COM_mm'];cargo=20.;g=9.81
before=previous['before_estimated_empty_mass_kg'];mat=[]
for old in previous['material_weight_change']:
    k=old['material'];after=sum(r['mass_kg'] for r in p['parts'] if r['material']==k);mat.append({'material':k,'before_CAD_mass_kg':old['before_CAD_mass_kg'],'after_CAD_mass_kg':after,'delta_kg':after-old['before_CAD_mass_kg']})
I=(20*30**3-17*27**3)/12;P=M*g;beamM=P*490/4;wheelN=M*g*2/3
corners=[]
for x,y in itertools.product([225,425],[-75,75]):
    c=[(m*ec[i]+cargo*[x,y,400][i])/M for i in range(3)];Wn=M*g
    corners.append({'cargo_COM_mm':[x,y,400],'gross_COM_mm':c,'gravity_front_rear_axle_groups_N':[Wn*(570-c[0])/490,Wn*(c[0]-80)/490],'gravity_left_right_groups_N':[Wn*(165-c[1])/330,Wn*(c[1]+165)/330],'pull_minusX_tip_threshold_N':Wn*(c[0]-80)/480,'lateral_tip_threshold_N':Wn*(165-abs(c[1]))/480,'static_grade_tip_tangent_fore_aft':min(c[0]-80,570-c[0])/c[2]})
out={**previous,'design_id':'low_profile_stock_cart_01','revision':'r2_tote_gusset_clearance','after_estimated_empty_mass_kg':m,'reduction_kg':before-m,'reduction_percent':100*(before-m)/before,'material_weight_change':mat,'geometry_mass_ledger_SHA256':hashlib.sha256((E/'geometry_mass_screen.json').read_bytes()).hexdigest(),'beam_screen':{'load_assumption':'2g gross cart+cargo entirely split between two rails, one central load each. No empty-wheel mass subtraction.','rail_outer_width_height_wall_mm':[20,30,1.5],'span_mm':490,'I_mm4':I,'per_rail_center_load_N':P,'nominal_bending_MPa':beamM*15/I,'deflection_mm':P*490**3/(48*69000*I),'comparison_allowable_assumed_MPa':70,'limit':'No net-hole, local buckling, joint/slip or fatigue qualification.'},'wheel_and_handle_screen':{'2g_gross_divided_by_three_min_wheel_load_N':wheelN,'axle_d10_46mm_simply_supported_sigma_MPa':32*(wheelN*46/4)/(math.pi*10**3),'spreader3mm_68mm_strip_25mm_overhang_sigma_MPa':6*(wheelN/2)*25/(68*3**2),'bite_d8_170mm_span_30N_centerload_sigma_MPa':32*(30*170/4)/(math.pi*8**3),'limits':'Nominal analytical stress only, not caster/bearing/brake rating or impact endurance.'},'cargo_extreme_static_screen':corners,'force_scenarios':[{'c_rr_assumption':rr,'gross_mass_kg':M,'flat_constant_speed_N':rr*M*g,'flat_start_accel_0p2_N_without_caster_start':rr*M*g+M*.2,'2pct_grade_plus_accel_0p2_N_without_caster_start':rr*M*g+M*.2+M*g*.02} for rr in [.01,.02,.03]],'physics_integrations':0,'training':0}
(E/'structure_load_screen.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'empty_mass_kg':m,'gross_mass_kg':M,'beam_MPa':out['beam_screen']['nominal_bending_MPa'],'min_corner_forward_tip_N':min(c['pull_minusX_tip_threshold_N'] for c in corners),'reduction_percent':out['reduction_percent']},indent=2))
