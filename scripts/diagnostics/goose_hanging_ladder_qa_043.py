"""Pure QA/observer for fixedhead hangingmass ladder. Never steps or commands a simulator."""
import math,time
import numpy as np
POLYGON=np.array([[179.3,-11.7],[215,-11.7],[239,-6.7],[257.7,-2.7],[257.7,2.7],[239,6.7],[215,11.7],[179.3,11.7]])
def selected_TPU_workface_domain(point_native_mm):
 p=np.asarray(point_native_mm)[:2];e=np.roll(POLYGON,-1,axis=0)-POLYGON;cross=e[:,0]*(p-POLYGON)[:,1]-e[:,1]*(p-POLYGON)[:,0];return bool(np.min(cross)>=-1e-7),float(np.min(cross/np.linalg.norm(e,axis=1)))
def observe_scaled(model,data,original_observation):
 """Add mass-scaled eligibility; preserve originalobserver/reasons/oldgeomDistance verbatim."""
 o=dict(original_observation);bid=model.body('calibrated_hanging_assembly').id;mass=float(model.body_subtreemass[bid]);gravity=np.asarray(model.opt.gravity);g=float(np.linalg.norm(gravity));up=-gravity/g;force=np.asarray(o['mouth_force_on_object_world_N']);mg=mass*g
 bg=model.geom('calibrated_304_ballast_geom').id;tg=model.geom('physical_support_surface').id;RB=data.geom_xmat[bg].reshape(3,3);RT=data.geom_xmat[tg].reshape(3,3);pB=data.geom_xpos[bg];pT=data.geom_xpos[tg];horizontal=bool(abs(RT[2,2]-1)<1e-10 and np.max(abs(RT[:2,2]))<1e-10);half=model.geom_size[bg];corners=np.array([[i,j,k]for i in [-1,1]for j in [-1,1]for k in [-1,1]])*half;local=(corners@RB.T+pB-pT)@RT;inside=bool(np.max(abs(local[:,0]))<=model.geom_size[tg,0]+1e-10 and np.max(abs(local[:,1]))<=model.geom_size[tg,1]+1e-10);gap=float(pB[2]-abs(RB[2])@half-pT[2]-model.geom_size[tg,2])
 domain=[]
 for p in o['material_points']:
  within,margin=selected_TPU_workface_domain(p['native_point_mm']);domain.append(dict(mouth=p['mouth'],normal_N=p['normal_N'],within_selected_TPU_XY=within,polygon_margin_mm=margin,native_point_mm=p['native_point_mm']))
 outside=sum(p['normal_N']for p in domain if not p['within_selected_TPU_XY']);force_threshold=mg*(190/196.2);grip=o['grip_normal_N'];eligible=bool(o['platform_N']<.05 and horizontal and inside and gap>.0005 and o['nonmouth_object_contact_normal_N']<.05 and force@up>force_threshold and min(grip.values())>5 and outside<=1.)
 o.update(actual_total_hanging_mass_kg=mass,actual_gravity_N=mg,mouth_support_threshold_N=force_threshold,mouth_force_opposing_gravity_N=float(force@up),gravity_load_N=mg,analytic_ballast_table_gap_m=gap,analytic_gap_applicable=horizontal and inside,original_hold_eligibility_20kg=o.get('hold_eligibility'),hold_eligibility=eligible,selected_TPU_domain_points=domain,selected_TPU_outside_force_N=outside,selected_TPU_domain_status='IN_DOMAIN'if outside<=1 else'OUT_OF_VALIDATED_WORKFACE_NO_BARETIP_WITNESS',no_new_material_or_physics_parameters=True)
 return o
class HoldLedger:
 def __init__(self):self.rows=[];self.since=None;self.longest=0.;self.start_nativeX=None
 def add(self,observation):
  t=float(observation['time']);x=float(observation['native_workpiece_center_mm'][0]);self.start_nativeX=x if self.start_nativeX is None else self.start_nativeX
  if self.rows and t<=self.rows[-1]['time_s']:raise ValueError('Fresh strictly increasingactualsubsteps required')
  if observation['hold_eligibility']:self.since=t if self.since is None else self.since
  else:self.since=None
  clock=0. if self.since is None else t-self.since;self.longest=max(self.longest,clock);self.rows.append(dict(time_s=t,nativeX_mm=x,eligible=observation['hold_eligibility']));window=[r for r in self.rows if r['time_s']>=t-1.];speed=None if len(window)<2 else(x-window[0]['nativeX_mm'])/(t-window[0]['time_s']);return dict(current_full_load_hold_s=clock,longest_full_load_hold_s=self.longest,retained5s=clock>=5.,total_outward_slide_mm=x-self.start_nativeX,last_up_to1s_outward_rate_mm_s=speed,last_rate_window_s=t-window[0]['time_s'],retention_is_not_stability_or_material_qualification=True,required_disclosure='A5s massretained result must separately disclose full outwardslide/contactpolygon/last1screep; sustaineddescent isnotstableceiling.')
class FiniteLadderQA:
 """Pure next-test proposal. Root authorizes; F alone executes. Hardstop never auto retries."""
 def __init__(self):self.grid=np.arange(5,50.01,2.5).tolist();self.records=[];self.started=time.monotonic();self.max_trials=8;self.max_wall_s=3600
 def record(self,mass_kg,torque_Nm,outcome,receipt_sha256):
  if outcome not in ['PASS5S','CAPACITY_FAIL','DOMAIN_STOP','PHYSICAL_GUARD','SOFTWARE_STOP']:raise ValueError('Explicit outcome required')
  if not receipt_sha256:raise ValueError('Actual sealedreceipt identity required')
  self.records.append(dict(mass_kg=mass_kg,torque_Nm=torque_Nm,outcome=outcome,receipt_sha256=receipt_sha256))
 def next_proposal(self):
  if len(self.records)>=8 or time.monotonic()-self.started>=3600:return dict(action='STOP_BUDGET',no_more_physics=True)
  if any(r['outcome']in ['DOMAIN_STOP','PHYSICAL_GUARD','SOFTWARE_STOP']for r in self.records):return dict(action='STOP_ROOT_REVIEW',reason='Guard/domain/software receipts are not hardwarecapacitybounds; noauto retry')
  cap=[r for r in self.records if r['torque_Nm']==4.4]
  if not self.records:return dict(action='PROPOSE_ONLY',mass_kg=20.,torque_Nm=3.,reason='Requiredsamecondition13regression countsoneof8')
  if not cap:return dict(action='PROPOSE_ONLY',mass_kg=20.,torque_Nm=4.4,reason='Firstsourcecaptest;3Nmregressiondoesnotbound4.4capacity')
  passed=[r['mass_kg']for r in cap if r['outcome']=='PASS5S'];failed=[r['mass_kg']for r in cap if r['outcome']=='CAPACITY_FAIL'];low=max(passed,default=None);high=min(failed,default=None)
  li=-1 if low is None else self.grid.index(low);hi=len(self.grid)if high is None else self.grid.index(high)
  locate_count=len(set(r['mass_kg']for r in cap))-1
  if hi-li>1 and locate_count<4 and len(self.records)<6:
   idx=(li+hi)//2;return dict(action='PROPOSE_ONLY',mass_kg=self.grid[idx],torque_Nm=4.4,reason='Oneadaptive2.5kggridboundary; no linear5kgbudgetoverrun')
  if low is None:return dict(action='STOP_NO_TESTED_PASS',observed_min_failure_kg=high)
  attempts=[r for r in cap if r['mass_kg']==low]
  if any(r['outcome']!='PASS5S'for r in attempts):return dict(action='STOP_NONREPEATABLE',maximum_observed_pass_kg=low)
  if len(attempts)<3:return dict(action='PROPOSE_ONLY',mass_kg=low,torque_Nm=4.4,reason='Boundaryrepeat'+str(len(attempts)+1)+'of3; no newbound fromsame trial')
  return dict(action='STOP_COMPLETE',repeatable_tested_lower_bound_kg=low,minimum_actual_capacity_fail_kg=high,observed_bracket_width_kg=None if high is None else high-low,upper50_failed_claim_permitted=50. in failed,range_censored=high is None)

def original_fixture_mass_variant(xml_root,total_mass_kg):
 """Return a deepcopy of frozen20kg scene with only real304 ballast thickness/MCI,
 table placement and externaltable gravitybias changed. Existingfixture limited<=20kg.
 This is not a robotdensity/gain/cap/contact edit and never compiles or executes.
 """
 import copy
 root=copy.deepcopy(xml_root)
 if not 5<=total_mass_kg<=20:raise ValueError('Original304fixture only5..20kg; strongerfixture requires separateRootadoption')
 obj=root.find(".//body[@name='calibrated_hanging_assembly']");ballast=root.find(".//body[@name='calibrated_304_ballast']");table=root.find(".//body[@name='physical_lowering_platform']")
 if obj is None or ballast is None or table is None:raise ValueError('Exactnamed originalfixture required')
 vals=lambda a:np.array([float(x)for x in a.split()]);fmt=lambda a:' '.join(format(float(v),'.17g')for v in a)
 bodies=[obj]+list(obj.findall('.//body'));oldtotal=sum(float(b.find('inertial').get('mass'))for b in bodies if b.find('inertial')is not None);bi=ballast.find('inertial');bg=ballast.find('geom');oldmass=float(bi.get('mass'));constant=oldtotal-oldmass;mass=total_mass_kg-constant
 if mass<=0:raise ValueError('Requestedtotal belowrealfixturemass')
 half=vals(bg.get('size'));bp=vals(ballast.get('pos'));oldtop=bp[2]+half[2];oldbottom=bp[2]-half[2];height=mass/(8000*(2*half[0])*(2*half[1]));half[2]=height/2;bp[2]=oldtop-height/2;bg.set('size',fmt(half));ballast.set('pos',fmt(bp));bi.set('mass',str(mass));dims=half*2;bi.set('diaginertia',fmt([mass*(dims[(i+1)%3]**2+dims[(i+2)%3]**2)/12 for i in range(3)]));tp=vals(table.get('pos'));tp[2]+=(oldtop-height)-oldbottom;table.set('pos',fmt(tp));act=root.find(".//general[@name='external_platform_actuator']");bias=vals(act.get('biasprm'));g=9.81;bias[0]=(total_mass_kg+8)*g;act.set('biasprm',fmt(bias))
 return root,dict(declared_total_mass_kg=total_mass_kg,constant_actual_fixture_mass_kg=constant,ballast_mass_kg=mass,ballast_dimensions_m=dims.tolist(),ballast_top_unchanged_m=oldtop,externaltable_gravitybias_N=bias[0],platform_cap_N=600,source_robot_and_contacts_unchanged=True,actual_mass_andMCI_must_be_compiled_readback=True,no_density_fudge=True,no_physics=True)
