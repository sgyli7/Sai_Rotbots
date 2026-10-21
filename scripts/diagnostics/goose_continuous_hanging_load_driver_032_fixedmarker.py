"""Source-bound finite041 driver. Default prepares only; --execute requires exactRootauth.
No object state writes after initial recipe; originaladapter limiter once per5ms.
"""
import os
for x in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[x]='1'
import argparse,hashlib,importlib.util,json,time,resource
from pathlib import Path
import numpy as np,mujoco as mj
from goose_virtual_hanging_load_047 import VirtualPayload,BoundedHoldLedger
from goose_continuous_load_schedule_031 import ContinuousLoadRamp
RAMP_HELPER=Path(__file__).with_name('goose_continuous_load_schedule_031.py')
RAMP_SHA='defa9bd2ef7f2d9dbabe5d1d9a6b2921b9f0f59a5a0acdf87805014d99e42859'
HELPER=Path(__file__).with_name('goose_virtual_hanging_load_047.py')
HELPER_SHA='2f57502035472426b2d8c498c7f3054f06f285d7a2c7f948d7d22f0d12f8bf07'
W=Path('/home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots')
HANDOFF=W/'experiments/goose_v0_2/downward_pull_fixture_041_near_hangers/source_bound_handoff_001.json'
PLAN={'schema':'finite_actual_feedback_phases_041_001','limits':{'sim_s':40.,'wall_s':600.,'CPU':1,'threads':1,'memory_GiB':8,'GPU':0},'settle':{'minimum_s':.15,'timeout_s':.75,'table_N_range':[176.2,216.2],'gap_abs_max_m':.001,'payload_speed_max_m_s':.02},'close':{'timeout_s':5.0,'reference_speed_rad_s':.2,'speed_pause_rad_s':.7,'lower_contact_pause_N':2.,'bilateral_N':5.,'bilateral_continuous_s':.1},'preload':{'target_input_Nm':3.,'torque_slew_Nm_s':5.,'timeout_s':1.,'target_hold_s':.1},'withdraw':{'reference_m':-.04,'speed_m_s':.02,'timeout_s':2.75,'offtable_N_max':.05,'gap_min_m':.0005},'hold':{'continuous_s':5.,'total_timeout_s':5.75,'small_slip_allowed':True},'drop':{'relative_down_displacement_m':.03,'unsupported_continuous_s':.15,'mouth_support_Z_N_min':20.},'all_phases':'First source/structure/loop/ROM/speed/2.025mm/hidden/nonmouth guard ends; no retry. Drop defined only after platformwithdrawal; no instant softmicro-slip failure.'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,default=lambda a:a.tolist()if isinstance(a,np.ndarray)else str(a))+'\n')
def load(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def refs(x):
 if isinstance(x,dict):
  if 'path'in x and 'sha256'in x:assert sha(x['path'])==x['sha256'],x['path']
  for v in x.values():refs(v)
 elif isinstance(x,list):
  for v in x:refs(v)
def correct_box_gap(model,data,observation):
 """Pure observer correction: horizontal table and contained box footprint only.
 Keeps original mj_geomDistance as independent witness; no physical writes.
 """
 o=dict(observation);it=model.geom('physical_support_surface').id;ib=model.geom('calibrated_304_ballast_geom').id
 if model.geom_type[it]!=mj.mjtGeom.mjGEOM_BOX or model.geom_type[ib]!=mj.mjtGeom.mjGEOM_BOX:raise ValueError('Analyticgap requires actualbox pair')
 Rt=data.geom_xmat[it].reshape(3,3);Rb=data.geom_xmat[ib].reshape(3,3)
 if np.max(abs(Rt[2]-[0,0,1]))>1e-10:raise ValueError('Analyticgap requires horizontalactualtable')
 relative_center=Rt.T@(data.geom_xpos[ib]-data.geom_xpos[it]);extent=abs(Rt.T@Rb)@model.geom_size[ib];inside=bool(np.all(abs(relative_center[:2])+extent[:2]<=model.geom_size[it,:2]+1e-10))
 bottom=float(data.geom_xpos[ib,2]-abs(Rb[2])@model.geom_size[ib]);top=float(data.geom_xpos[it,2]+abs(Rt[2])@model.geom_size[it]);gap=bottom-top
 o.update(original_mj_geomDistance_m=o['platform_ballast_signed_gap_m'],analytic_box_bottom_Z_m=bottom,analytic_table_top_Z_m=top,analytic_vertical_gap_m=gap,analytic_box_footprint_contained=inside,gap_observer_revision='horizontal_box_support_plane_exact_001')
 if not inside:o['reasons']=list(o['reasons'])+['fixture_ballast_projection_left_support_table_observer_domain']
 o['platform_ballast_signed_gap_m']=gap
 o['hold_eligibility']=bool(inside and o['platform_N']<.05 and gap>.0005 and o['nonmouth_object_contact_normal_N']<.05 and o['mouth_force_on_object_world_N'][2]>190)
 return o
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--handoff',type=Path,default=HANDOFF);a.add_argument('--target-input-Nm',type=float,choices=[3.0,4.4],default=3.0);a.add_argument('--execute',action='store_true');a.add_argument('--authorization',type=Path);args=a.parse_args();assert not args.out.exists()
 selected_target=float(args.target_input_Nm);plan=json.loads(json.dumps(PLAN));plan['preload']['target_input_Nm']=.50139024;plan['preload']['timeout_s']=3.;plan['preload']['actual_speed_max_rad_s']=.02;plan['drop']['marker']='cart_bite_bar geomcenter, not mass-dependent subtreeCOM';plan['withdraw']['first_hold_actual_q_max_m']=-.0395;plan['withdraw']['continue_reference_slew_in_hold']=True;plan['load_torque_rule']={'base_Nm':.50139024,'per_added_kg_Nm':.20,'cap_Nm':4.4,'recovery_boosts':False}
 handoff=args.handoff;h=json.load(open(handoff));refs(h)
 assert h['qa_source']['sha256']=='8d63e8c37d67eca47c98a5feb4371028fc231b078cb574275bc192a77ead76ae';qa=load(h['qa_source']['path'],'qa043');mass=float(h['payload']['assembly_mass_kg']);assert mass==20
 plan['fixture_total_mass_kg']=mass;plan['settle']['table_N_range']=[mass*9.81-20,mass*9.81+20];holdledger=None
 model=mj.MjModel.from_binary_path(h['mjb']['path']);d=mj.MjData(model);z=np.load(h['initial']['path']);d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl'];mj.mj_forward(model,d)
 assert sha(HELPER)==HELPER_SHA and sha(RAMP_HELPER)==RAMP_SHA;vp=VirtualPayload(model);mass=vp.fixed+.05;initial_mass_update=vp.set_total_mass(d,mass);model.actuator_biasprm[1,0]=(8+mass)*9.81;mj.mj_forward(model,d);holdledger=BoundedHoldLedger();plan['platform_fixed_initial_gravity_bias_N']=(8+mass)*9.81;plan['fixture_initial_mass_kg']=mass;plan['settle']['table_N_range']=[max(0.,mass*9.81-.2),mass*9.81+.2];plan['continuous_load']={'maximum_total_kg':20.,'increment_kg':1.,'smooth_ramp_s':.5,'only_top_qualified_hold_s':5.,'no_intermediate_dwell_pause_or_boost':True,'helper_sha256':HELPER_SHA,'continuous_schedule_sha256':RAMP_SHA};
 mod=load(h['source']['path'],'fixture041');adapter=load(h['adapter']['path'],'adapter12');drv=adapter.FrozenPhysics(Path(h['adapter']['path']).parent)
 cfg=json.load(open(h['fixture_guard']['path']));table=json.load(open(h['retained_table']['path']));obs=qa.observe_scaled(model,d,correct_box_gap(model,d,mod.observe_fixture(model,d,cfg,table)))
 assert model.nu==2 and model.neq==1 and model.opt.timestep==.0005 and not obs['reasons'];assert model.actuator(0).name=='beak_hinge_motor'
 ji=model.joint('beak_input_rotor');qi=int(ji.qposadr[0]);vi=int(ji.dofadr[0]);pj=int(model.joint('platform_slide').qposadr[0]);pid=model.body('calibrated_hanging_assembly').id
 assert abs(sum(model.body_mass[i]for i in range(model.nbody)if model.body_rootid[i]==pid)-mass)<1e-9
 plan_sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest();required={'root_authorized':True,'runner_sha256':sha(__file__),'handoff_sha256':sha(handoff),'scene_sha256':h['scene']['sha256'],'mjb_sha256':h['mjb']['sha256'],'initial_sha256':h['initial']['sha256'],'plan_sha256':plan_sha,'selected_input_target_Nm':selected_target,'fixture_mass_kg':mass,'load_helper_sha256':HELPER_SHA,'continuous_schedule_sha256':RAMP_SHA,'qa_source_sha256':h['qa_source']['sha256']}
 if args.execute:
  assert args.authorization;auth=json.load(open(args.authorization));assert all(auth.get(k)==v for k,v in required.items()),'ExactRootsource/plan authorizationrequired';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
 args.out.mkdir(parents=True);mj.mj_saveModel(model,str(args.out/'modified_initial_scene.mjb'));dump(args.out/'command_plan.json',plan);dump(args.out/'required_authorization_fields.json',required);(args.out/'runner_snapshot.py').write_bytes(Path(__file__).read_bytes());(args.out/'source_bound_handoff.json').write_bytes(handoff.read_bytes())
 for k in ['scene','mjb','initial']:(args.out/Path(h[k]['path']).name).write_bytes(Path(h[k]['path']).read_bytes())
 dump(args.out/'zero_step_receipt.json',{'physics_steps':0,'required_authorization':required,'zero_observation':obs,'clock':{'physics_s':.0005,'drive_s':.005,'reference_s':.02},'adapter_once_axis5_to_bench0':True,'all3mechanismjoint_ROM_check':True,'no_hot_initialization':True,'fixture_not_wholeGoose':True})
 if not args.execute:print(json.dumps({'status':'ZERO_STEP_READY','out':str(args.out),'runner_sha256':sha(__file__),'plan_sha256':plan_sha,'selected_input_target_Nm':selected_target,'fixture_mass_kg':mass,'load_helper_sha256':HELPER_SHA,'continuous_schedule_sha256':RAMP_SHA,'qa_source_sha256':h['qa_source']['sha256']}));return
 (args.out/'root_authorization.json').write_bytes(args.authorization.read_bytes());started=time.monotonic();phase='settle';phase_start=0.;events=[];rows=[];last_request=0.;target=float(d.qpos[qi]);platform_ref=0.;bilat=0.;offclock=0.;holdclock=0.;unsupported=0.;failure=None;entry_rod_center=d.geom_xpos[model.geom('cart_bite_bar').id].copy();fullinputclock=0.;ledger=(args.out/'contacts_substeps.jsonl').open('w');tick=0;loads=[];schedule=None;decision=None;last_load_update=None;recent_rate=0.;initial_mass=mass;low_stable_clock=0.;recovery_boost=0.;boost_count=0;last_boost_time=None;command_torque_goal=.50139024
 def enter(new):
  nonlocal phase,phase_start,schedule
  events.append({'time':float(d.time),'from':phase,'to':new,'observation':obs});phase=new;phase_start=float(d.time)
  if new=='hold':schedule=ContinuousLoadRamp(mass,d.time)
 try:
  while d.time<40.-1e-10:
   if time.monotonic()-started>600:failure={'reason':'wall600'};break
   t=float(d.time);age=t-phase_start;normal=obs['grip_normal_N'];both=min(normal.values())>5
   if tick%4==0:
    if phase in['withdraw','hold']:platform_ref=max(plan['withdraw']['reference_m'],platform_ref-.0004)
    if phase=='settle':
     speed=np.linalg.norm(d.qvel[int(model.joint('test_object_free6d').dofadr[0]):int(model.joint('test_object_free6d').dofadr[0])+3])
     if age>=.15 and plan['settle']['table_N_range'][0]<=obs['platform_N']<=plan['settle']['table_N_range'][1] and abs(obs['platform_ballast_signed_gap_m'])<.001 and speed<.02:enter('close')
     elif age>.75:failure={'reason':'platform_settle_timeout'};break
    elif phase=='close':
     if bilat>=.1:enter('preload')
     elif age>5.0 or target>=-1e-8:failure={'reason':'no_bilateral_capture_within_finite_ROM_time'};break
     elif abs(obs['input_speed_rad_s'])<=.7:target=min(0.,target+.004)
    elif phase=='preload':
     if low_stable_clock>=.1:enter('withdraw')
     elif age>3.:failure={'reason':'low_preload_not_actually_settled_NO_MASS_LIMIT'};break
    elif phase=='withdraw':
     if offclock>=.02:enter('hold')
     elif age>2.75:failure={'reason':'platform_not_actually_released'};break
    elif phase=='hold':pass
   if phase=='hold':
    decision=schedule.update(d.time,obs['hold_eligibility']);goal=max(mass,decision['total_mass_goal_kg'])
    if abs(goal-mass)>1e-12:last_load_update=vp.set_total_mass(d,goal);loads.append(last_load_update);mass=goal
    if decision['stop']:enter('complete');break
   if phase in ['settle','close']:
    requested=drv.kp[5]*(target-d.qpos[qi])-drv.kd[5]*d.qvel[vi]
   else:
    command_torque_goal=min(4.4,.50139024+.20*(mass-initial_mass))
    requested=last_request+np.clip(command_torque_goal-last_request,-.025,.025)
   request18=np.zeros(18);vel18=np.zeros(18);request18[5]=requested;vel18[5]=d.qvel[vi];limited=drv.limit_torque(request18,vel18);tau=float(limited[5]);last_request=tau;d.ctrl[0]=tau;d.ctrl[1]=platform_ref
   for sub in range(10):
    mj.mj_step(model,d);mj.mj_forward(model,d);obs=qa.observe_scaled(model,d,correct_box_gap(model,d,mod.observe_fixture(model,d,cfg,table)))
    obs['fixed_rod_center_world_m']=d.geom_xpos[model.geom('cart_bite_bar').id].tolist();obs['fixed_rod_initial_center_world_m']=entry_rod_center.tolist();obs['fixed_rod_down_displacement_m']=float(entry_rod_center[2]-d.geom_xpos[model.geom('cart_bite_bar').id,2]);obs['subtree_COM_is_MCI_diagnostic_not_geometric_drop']=True;obs['hold_eligibility_before_fullywithdrawn_gate']=obs['hold_eligibility'];obs['platform_actual_q_m']=float(d.qpos[pj]);obs['platform_reference_m']=platform_ref;obs['fullywithdrawn_gate']=bool(d.qpos[pj]<=-.0395 and obs['platform_N']<.05 and obs['platform_ballast_signed_gap_m']>.0005);obs['hold_eligibility']=bool(obs['hold_eligibility']and obs['fullywithdrawn_gate']);obs['hold_ledger']=holdledger.add(obs);recent_rate=(obs['hold_ledger']['last_up_to1s_outward_rate_mm_s']or 0.)*.001;obs['virtual_load_schedule']=None if schedule is None else decision;obs['parameter_mass_update_last']=last_load_update;obs['testobject_virtual_mass_changes_not_robot']=True
    if obs['selected_TPU_outside_force_N']>1.:obs['reasons'].append('selected_TPU_workface_domain_exited_NOT_CAPACITY_LIMIT')
    for n in ['beak_hinge','beak_input_rotor','beak_coupler_link']:
     j=model.joint(n);x=float(d.qpos[int(j.qposadr[0])]);lo,hi=model.jnt_range[j.id]
     if not lo-1e-8<=x<=hi+1e-8:obs['reasons'].append('source_ROM_'+n)
    both=min(obs['grip_normal_N'].values())>5;low_stable_clock=low_stable_clock+.0005 if phase=='preload'and both and abs(obs['input_speed_rad_s'])<=.02 and abs(obs['input_tau_Nm']-.50139024)<.01 else 0.;bilat=bilat+.0005 if both else 0.;offclock=offclock+.0005 if obs['hold_eligibility']else 0.;holdclock=holdclock+.0005 if phase=='hold'and obs['hold_eligibility']else 0.;fullinputclock=fullinputclock+.0005 if abs(obs['input_tau_Nm']-selected_target)<.01 else 0.
    unsupported=unsupported+.0005 if phase in ['withdraw','hold']and obs['platform_N']<.05 and obs['mouth_force_on_object_world_N'][2]<mass*9.81*.1 else 0.
    row={'time':float(d.time),'phase':phase,'qpos':d.qpos.copy(),'qvel':d.qvel.copy(),'qacc':d.qacc.copy(),'ctrl':d.ctrl.copy(),'actuator_force':d.actuator_force.copy(),'requested_input':requested,'limited_input':tau,'platform_ref':platform_ref,'hold_clock':holdclock,'command_torque_goal_Nm':command_torque_goal,'recovery_boost_Nm':recovery_boost,'recovery_boost_count':boost_count,'actual_test_total_mass_kg':mass,'observation':obs};ledger.write(json.dumps(row,default=lambda x:x.tolist()if isinstance(x,np.ndarray)else str(x))+'\n')
    rows.append({k:v for k,v in row.items()if k!='observation'})
    if obs['reasons']:failure={'reason':'original_guard','reasons':obs['reasons'],'time':float(d.time)};break
    if unsupported>.15 or (phase in ['withdraw','hold']and obs['platform_N']<.05 and entry_rod_center[2]-d.geom_xpos[model.geom('cart_bite_bar').id,2]>.03):failure={'reason':'declared_drop_or_unsupported_loss','time':float(d.time)};break
   tick+=1
   if tick%20==0:print(json.dumps({'time':float(d.time),'phase':phase,'tau':obs['input_tau_Nm'],'N':obs['grip_normal_N'],'table_N':obs['platform_N'],'gap':obs['platform_ballast_signed_gap_m'],'hold_clock':holdclock,'reasons':obs['reasons']}),flush=True)
   if failure:break
  if phase!='complete' and failure is None:failure={'reason':'finite_sim40_budget_before_complete'}
 except Exception as error:
  failure={'reason':'software_exception_not_hardware_failure','error':repr(error),'time':float(d.time)}
 finally:
  ledger.close();np.savez_compressed(args.out/'trajectory_substeps.npz',**{k:np.array([r[k]for r in rows])for k in rows[0]}if rows else {});np.savez_compressed(args.out/'final_actual_state.npz',time=float(d.time),qpos=d.qpos,qvel=d.qvel,qacc=d.qacc,ctrl=d.ctrl,actuator_force=d.actuator_force);dump(args.out/'events.json',events);dump(args.out/'virtual_mass_energy_updates.json',loads);mj.mj_saveModel(model,str(args.out/'final_mass_scene.mjb'));dump(args.out/'load_schedule_final.json',None if schedule is None else decision);dump(args.out/'result.json',{'phase':phase,'actual_end_s':float(d.time),'failure':failure,'hold_continuous_s':holdclock,'selected_input_target_Nm':selected_target,'actual_fixture_mass_kg':mass,'mass_retained_not_necessarily_stable':True,'actual_observation':obs,'physics_steps':len(rows),'wall_s':time.monotonic()-started,'no_retry':True,'no_wholeGoose_or_transport_qualification':True,'ramp_entered':schedule is not None,'actual_mass_peak_kg':mass,'top_qualified_hold_s':0. if decision is None else decision.get('qualified_top_hold_s',0.),'intermediate_hold_is_not_top_weight_qualification':True,'load_helper_sha256':HELPER_SHA,'initial_mass_update':initial_mass_update,'initial_low_preload_Nm':.50139024,'recovery_boost_Nm':recovery_boost,'recovery_boost_count':boost_count});print(json.dumps({'finished':True,'phase':phase,'time':float(d.time),'failure':failure,'hold_s':holdclock}),flush=True)
if __name__=='__main__':main()
