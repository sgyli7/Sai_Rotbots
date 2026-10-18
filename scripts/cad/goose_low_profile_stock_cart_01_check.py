from pathlib import Path
import sys,json,hashlib,math
W=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(W/'scripts/cad'))
from goose_low_profile_stock_cart_01 import make_cart
from cadgen import read_step,build123d as bd
shape,rows,p=make_cart();exp=W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_01';E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01'
for row,ch in zip(rows,shape.children):
    rho=p['materials'][row['material']]['density_kg_m3'];row['full_inertia_about_COM_kg_m2']=[[v*rho*1e-15 for v in rr] for rr in ch.matrix_of_inertia];row['bounds_mm']={'min':list(ch.bounding_box().min),'max':list(ch.bounding_box().max)}
saved=read_step(exp/'goose_low_profile_stock_cart_01.step')
tote=bd.Pos(325,0,256.5)*bd.Box(600,400,150)
checks=[]
for ch in shape.children:
    ov=ch.intersect(tote);vol=ov.volume if ov is not None else 0.0
    checks.append({'part':ch.label,'overlap_volume_mm3':vol,'distance_mm':ch.distance_to(tote)})
old_path=W/'artifacts/goose_v0_2/low_profile_stock_cart_01/locked_r1/goose_low_profile_stock_cart_01.step'
old=read_step(old_path) if old_path.exists() else None;old_ov=old.intersect(tote) if old is not None else None
(E/'tote_clearance.json').write_text(json.dumps({'revision':p.get('revision'),'tote_envelope_mm':{'center':[325,0,256.5],'size':[600,400,150],'bottom_z':181.5},'scope':'Native positive-volume envelope test at intended centered load pose only. Deck support face touch allowed. No insertion sweep, loose-goods or dynamic retention qualification.','old_r1_STEP_SHA256':hashlib.sha256(old_path.read_bytes()).hexdigest() if old_path.exists() else None,'old_r1_tote_overlap_volume_mm3':sum(x.volume for x in old_ov) if isinstance(old_ov,list) else (old_ov.volume if old_ov is not None else 0.0),'new_positive_overlaps_above_0p001mm3':[r for r in checks if r['overlap_volume_mm3']>0.001],'new_mast_gusset_clearances':[r for r in checks if 'mast_base_gusset' in r['part']],'part_checks':checks},indent=2)+'\n')
m=sum(r['mass_kg'] for r in rows);com=[sum(r['mass_kg']*r['COM_mm'][i] for r in rows)/m for i in range(3)]
# Explicit unmodelled fastening/reserve, not density inflation or double counted M6s.
reserve=.35;reserve_com=[260,0,180];mt=m+reserve;ct=[(m*com[i]+reserve*reserve_com[i])/mt for i in range(3)]
payload=20.;cargo=[325,0,331.5];total=mt+payload;combined=[(mt*ct[i]+payload*cargo[i])/total for i in range(3)]
draw=[r for r in rows if any(w in r['name'] for w in ['drawbar_','roll_bearing','rotating_forward','bite_yoke','bite_core','bite_304','replaceable_bite'])];dm=sum(r['mass_kg'] for r in draw);dc=[sum(r['mass_kg']*r['COM_mm'][i] for r in draw)/dm for i in range(3)]
g=9.81;F=30.;t=p['frame_wall'];I=(20*30**3-(20-2*t)*(30-2*t)**3)/12;P=payload*g*2/2;span=490.;M=P*span/4;stress=M*15/I;defl=P*span**3/(48*69000*I)
I_mast=(32**4-28**4)/12;M_mast=F*330.;maststress=M_mast*16/I_mast
Fx_tip=total*g*(combined[0]-80)/480;Fy_tip=total*g*(190-abs(combined[1]))/480
support={'nominal_wheel_contact_centers_mm':[[x,y,0] for x in [80,570] for y in [-190,190]],'caster_all_headings_conservative_support_rectangle_mm':{'x':[80,570],'y':[-165,165]},'cargo_COM_allowed_mm':{'x':[225,425],'y':[-75,75],'z_max':400},'centered_payload_COM_assumed_mm':cargo,'loaded_COM_mm':combined,'nominal_loaded_tip_angle_side_deg':math.degrees(math.atan(190/combined[2])),'nominal_loaded_tip_angle_fore_aft_min_deg':math.degrees(math.atan(min(combined[0]-80,570-combined[0])/combined[2])),'cart_ideal_horizontal_pull_tip_thresholds_N':{'toward_goose_minusX':Fx_tip,'lateral':Fy_tip},'not_certification':'Rigid level four-point support only; swivel sweep, payload shift, slope and one-wheel obstacles separately require tests.'}
forces=[]
for rr in [.01,.02,.03]:
 for accel in [0,.2]:
  for slope in [0,.02]:forces.append({'rolling_coefficient_assumed':rr,'accel_m_s2':accel,'grade_assumed':slope,'estimated_required_F_N':rr*total*g+total*accel+total*g*slope,'excludes':'caster alignment, bearing seal losses, thresholds and floor joints'})
sources={'hydro_6061':'https://www.hydro.com/globalassets/01-products--services/extruded-profiles/americas/ena-resources/alloy-data-sheets/hydro_2019_data_sheet_6061.pdf','castor_resistance_context':'https://www.blickle.com/guide/info-box-wheel-series','note':'No vendor rolling percentage or off-the-shelf wheel capacity is assigned to the custom envelope. rr values are explicit scenario assumptions to be measured.'}
out={'design_id':'low_profile_stock_cart_01','status':'CAD_GEOMETRY_AND_ANALYTICAL_SCREEN_ONLY','parts':rows,'CAD_part_count':len(rows),'native_solid_count':len(shape.solids()),'all_individual_valid_positive':all(r['positive_volume'] and r['valid_native'] for r in rows),'CAD_mass_kg':m,'CAD_COM_mm':com,'unmodelled_reserve_kg':reserve,'reserve_reason':'Basket quick pins, frame joint angle brackets/corner hardware, remaining locking nuts, spring ends and anti-drop fasteners not yet fully detailed. Existing modelled wheel/mast M6s not counted twice.','estimated_empty_mass_kg':mt,'estimated_empty_mass_range_kg':[mt*.9,mt*1.15],'estimated_empty_COM_mm':ct,'payload_kg':payload,'gross_mass_kg':total,'over_goose_weight_ratio_gross':total/16.97020392883353,'drawbar_hand_end_moving_mass_kg':dm,'drawbar_COM_mm':dc,'unbalanced_vertical_bite_force_N':dm*g*abs(dc[0]+95)/255,'pitch_balance_spring_target_Nm':dm*g*abs(dc[0]+95)*.001,'support_screen':support,'analytical_structure':{'rail_section_mm':[20,30,2],'rail_I_mm4':I,'2g_20kg_load_split_two_rails_one_center_load_each_stress_MPa':stress,'same_deflection_mm':defl,'assumed_screen_allowable_MPa':70,'mast_F30N_330mm_arm_stress_MPa':maststress,'wheel_module_min_design_rating_N_each':total*g*2/3,'limit':'Beam nominal screening only. Joint groups, gusset/base plate, three-wheel events and caster/fork bolts not FEA or certified. Deck requires 600x400 tote/supporting box base; concentrated feet need local spreading plate.','cargo_tote_fit_mm':[610,410]},'force_scenarios':forces,'saved_step':{'bytes':(exp/'goose_low_profile_stock_cart_01.step').stat().st_size,'SHA256':hashlib.sha256((exp/'goose_low_profile_stock_cart_01.step').read_bytes()).hexdigest(),'solid_count':len(saved.solids()),'is_valid':saved.is_valid,'bounds_mm':{'min':list(saved.bounding_box().min),'max':list(saved.bounding_box().max)},'volume_delta_mm3':saved.volume-shape.volume},'sources':sources,'physics_integrations':0,'GPU':0,'training_updates':0}
(E/'geometry_mass_screen.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['CAD_part_count','native_solid_count','all_individual_valid_positive','CAD_mass_kg','estimated_empty_mass_kg','gross_mass_kg','drawbar_hand_end_moving_mass_kg','unbalanced_vertical_bite_force_N','pitch_balance_spring_target_Nm','analytical_structure','saved_step']},indent=2))
