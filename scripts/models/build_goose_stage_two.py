"""Bounded stage-two candidate: rated beak drive with a 1:1 parallel-crank link.

Keeps stage one immutable. Small transmission masses are reduced to their closed
pose; a separate sweep quantifies the error. These are architecture solids, not
released machining drawings or a measured continuous-grasp specification.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/models'));sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_stage_one import candidate as stage_one,make_contract,build,mesh,cylinder_inertia,box_inertia,R,CATALOG
from build_goose_r2_reference_rebuild import cylinder,section_solid
OUT=R/'models/stage_two';CONFIG=R/'configs/stage_two_contract.json'
MOTOR=np.array([.129,0,.601]);JAW=np.array([.160,0,.576]);RADIUS=.012;PHASE=np.deg2rad(225);LINK_Y=.034
REMOVED={'beak_pinion_envelope','beak_output_gear_envelope','pinion_bearing_reserve'}

def rod(a,b,width,thickness):
 # Flat rectangular bar along X in its local plane, with closed quad end caps.
 a,b=np.array(a),np.array(b);delta=b-a;length=np.linalg.norm(delta)
 q=section_solid([(-length/2,0,0,width/2,thickness/2),(length/2,0,0,width/2,thickness/2)],axis=0,power=8,count=8)
 direction=delta/length;normal=np.array([0,1,0]);second=np.cross(normal,direction)
 # Local axes X=bar, Y=in-plane normal, Z=axial thickness.
 return q.transformed(np.column_stack([direction,second,normal]),(a+b)/2)

def transmission_parts(q=0.):
 direction=RADIUS*np.array([np.cos(PHASE-q),0,np.sin(PHASE-q)])
 a=MOTOR.copy();b=JAW.copy();a[1]=.02975;b[1]=.029
 pa=a+direction;pb=b+direction;pa[1]=pb[1]=LINK_Y
 parts=[]
 def add(name,shape,material,body,kind):
  parts.append(dict(name=name,material=material,group='head_internal' if body=='head_roll' else 'lower_beak',body=body,role=kind,vertices=(shape.vertices/1000).tolist(),faces=shape.faces.tolist()))
 add('beak_rated_motor_case',cylinder(MOTOR*1000,27.5,56.5,1,.4),'graphite','head_roll','manufacturer_cylindrical_envelope')
 add('beak_input_crank',cylinder(a*1000,18,2.5,1,.25),'titanium','head_roll','unperforated_adapter_blank')
 tip=b+direction
 add('beak_output_crank',rod(b*1000,tip*1000,14,4),'titanium','beak_hinge','output_arm_blank_shaft_and_pin_holes_pending')
 add('beak_output_hub',cylinder(b*1000,7,4,1,.25),'titanium','beak_hinge','8mm_bore_clamp_hub_blank')
 add('beak_coupler',rod(pa*1000,pb*1000,12,4.5),'titanium','head_roll','coupler_blank_holes_and_bush_seats_pending')
 for label,p in [('input',pa),('output',pb)]:
  add('beak_'+label+'_pin',cylinder(p*1000,2.5,8.5,1,.15),'titanium','head_roll' if label=='input' else 'beak_hinge','5mm_shoulder_pin_envelope')
 return parts

def candidate():
 s=stage_one();old_owner=s.owner
 s.selected['neck_mid_pitch']='ak45_36_v3';s.actuators['neck_mid_pitch']=CATALOG['ak45_36_v3']
 s.owner=lambda n: 'beak_hinge' if n in ('beak_supported_output_shaft','beak_output_crank','beak_output_hub','beak_output_pin') else ('head_roll' if n.startswith('beak_') and n not in s.parts else old_owner(n))
 s.parts={n:p for n,p in s.parts.items() if n not in REMOVED and p['group']!='beak_drive'}
 # Replace anonymous bearings with a dimensioned 698 pair. Closed support
 # envelopes are conservative; the 8mm bore is detailed in the hardware spec.
 for n,y in [('jaw_bearing_reserve_right',-.0265),('jaw_bearing_reserve_left',.0235)]:
  p=s.parts[n];q=cylinder([160,y*1000,576],9.5,6,1,.2);p['vertices']=(q.vertices/1000).tolist();p['faces']=q.faces.tolist()
 new=transmission_parts()
 for p in new:s.parts[p['name']]=p
 s.items=[i for i in s.items if i['name'] not in REMOVED]
 for i in s.items:
  if i['name']=='neck_mid_pitch':
   i.update(mass_kg=.349,relative_uncertainty=.03,basis='AK45-36 V3.0 upgrade: previous middle-neck continuous design margin failed in stage-two mass envelope')
   i['inertia_at_com_kg_m2']=cylinder_inertia(.349,.0275,.0565,s.axes['neck_mid_pitch']).tolist()
  elif i['name']=='beak_drive':
   i.update(mass_kg=.349,center_m=MOTOR.tolist(),relative_uncertainty=.03,basis='AK45-36 V3.0 manufacturer349g; cylinder inertia at proposed center; 1:1 crank transmission')
   i['inertia_at_com_kg_m2']=cylinder_inertia(.349,.0275,.0565,[0,1,0]).tolist()
  elif i['name']=='beak_drive_mount_reserve':
   i.update(mass_kg=.025,center_m=MOTOR.tolist(),relative_uncertainty=.3,basis='mount/strain-relief allowance; existing head frame also retained')
   i['inertia_at_com_kg_m2']=box_inertia(.025,[.055,.06,.01]).tolist()
  elif i['name']=='logic_buck':
   i['basis']='Pololu D24V90F5 5V logic candidate; 4.8g board inside25g thermal/wiring allocation; enclosed thermal acceptance pending'
  elif i['name']=='servo_buck':
   i['basis']='Pololu D24V22F5 5V XC330 branch candidate; 2.3g board; retained40g allocation includes protection/thermal headroom; no12V branch'
  elif i['name']=='beak_supported_output_shaft':i['body']='beak_hinge'
  elif i['name'].startswith('jaw_bearing_reserve_'):
   mm=mesh(s.parts[i['name']]);i.update(mass_kg=.0072,center_m=mm.center_mass.tolist(),relative_uncertainty=.1,basis='JTEKT698 catalog7.2g; 8x19x6mm; C0r910N; retaining housing in head frame allowance')
   i['inertia_at_com_kg_m2']=(mm.moment_inertia*.0072/mm.mass).tolist()
 # Blank volume deliberately overestimates removed holes. Pins are steel; bars Al.
 for p in new:
  if p['name']=='beak_rated_motor_case':continue
  mm=mesh(p);mass=float(mm.volume*(7850 if p['name'].endswith('_pin') else 2700))
  s.items.append(dict(name=p['name'],body=p['body'],mass_kg=mass,center_m=mm.center_mass.tolist(),relative_uncertainty=.15,basis='solid blank mass, 2700kg/m3 Al or7850 steel; moving-mass reduction is separately bounded',inertia_at_com_kg_m2=(mm.moment_inertia*mass/mm.mass).tolist()))
 # Exact bush/washer/screw SKUs are partly pending, so retain an explicit reserve.
 s.items.append(dict(name='beak_bush_fastener_allowance',body='head_roll',mass_kg=.010,center_m=[.147,.029,.588],relative_uncertainty=.3,basis='2 iglidur GFM0506-05 bushes and shoulder fasteners/retainers allocation',inertia_at_com_kg_m2=box_inertia(.010,[.045,.014,.034]).tolist()))
 s.extra_collision_geometries=[dict(body='head_roll',name='beak_rated_motor_collision',kind='cylinder',fromto=' '.join(str(x) for x in np.r_[MOTOR-[0,.02825,0]-s.pivots['head_roll'],MOTOR+[0,.02825,0]-s.pivots['head_roll']]),size='.0275',rgba='.1 .12 .13 1',contype='2',conaffinity='3',group='3')]
 return s

def contract(s):
 c=make_contract(s);c['schema']='goose_stage_two_si_v2';c['parent_contract_sha256']=hashlib.sha256((R/'configs/stage_one_contract.json').read_bytes()).hexdigest()
 j=c['joints'][5];j.update(actuator='ak45_36_v3_parallel_crank_1_to_1',continuous_design_limit_nm=4.4,torque_peak_limit_nm=4.5,speed_limit_rad_s=1.,armature_kg_m2=CATALOG['ak45_36_v3']['rotor_gcm2']*1e-7*36**2,frictionloss_nm=.08)
 c['beak_transmission']=dict(type='uncrossed_equal_parallel_cranks',drive_axis_world_m=MOTOR.tolist(),jaw_axis_world_m=JAW.tolist(),crank_radius_m=RADIUS,closed_crank_angle_in_xz_rad=PHASE,coupler_pin_spacing_m=float(np.linalg.norm((JAW-MOTOR)[[0,2]])),ideal_angle_ratio=1.,efficiency_design_assumption=.85,output_design_continuous_nm=4.4,output_peak_limit_nm=4.5,thermal_status='manufacturer rated8Nm at40rpm; stationary enclosed-head thermal hold still requires bench test',lumped_mass_status='small input crank/coupler masses frozen at closed pose; sweep bounds in stage_two_mechanism_gate.json',head_shell_required_local_wall_m=.002,connector_clearance_status='main case and mechanism screened; actual mating plug and bend radius still pending')
 c['status']='STAGE_TWO_CONDITIONAL_ARCHITECTURE_NOT_HARDWARE_FREEZE'
 c['electrical_scope']={'motor_bus_nominal_v':24.,'battery_direct_connection_released':False,'ak48_driver_operating_window_v':None,'logic_5v_candidate':'Pololu D24V90F5','head_roll_5v_candidate':'Pololu D24V22F5','can_axis_count':17,'ttl_axis_count':1,'control_power_limit_is_not_electrical_input_limit':True}
 c['source_hashes']['scripts/models/build_goose_stage_two.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 return c

def main():
 s=candidate();c=contract(s);build(s,c,OUT,CONFIG)
 from export_goose_stage_one import export
 export(s,c,'stage_two')
 print(json.dumps(dict(stage_two_mass_kg=c['nominal_robot_mass_kg'],mass_change_kg=c['nominal_robot_mass_kg']-json.loads((R/'configs/stage_one_contract.json').read_text())['nominal_robot_mass_kg']),indent=2))
if __name__=='__main__':main()
