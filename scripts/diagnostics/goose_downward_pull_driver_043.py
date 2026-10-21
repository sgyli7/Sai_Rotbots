"""Source-bound finite041 driver. Default prepares only; --execute requires exactRootauth.
No object state writes after initial recipe; originaladapter limiter once per5ms.
"""
import os
for x in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[x]='1'
import argparse,hashlib,importlib.util,json,time,resource
from pathlib import Path
import numpy as np,mujoco as mj
W=Path('/home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots')
HANDOFF=W/'experiments/goose_v0_2/downward_pull_fixture_041_near_hangers/source_bound_handoff_001.json'
PLAN={'schema':'finite_actual_feedback_phases_041_001','limits':{'sim_s':12.,'wall_s':900.,'CPU':1,'threads':1,'memory_GiB':8,'GPU':0},'settle':{'minimum_s':.15,'timeout_s':.75,'table_N_range':[176.2,216.2],'gap_abs_max_m':.001,'payload_speed_max_m_s':.02},'close':{'timeout_s':3.5,'reference_speed_rad_s':.2,'speed_pause_rad_s':.7,'lower_contact_pause_N':2.,'bilateral_N':5.,'bilateral_continuous_s':.1},'preload':{'target_input_Nm':3.,'torque_slew_Nm_s':5.,'timeout_s':1.,'target_hold_s':.1},'withdraw':{'reference_m':-.04,'speed_m_s':.02,'timeout_s':2.75,'offtable_N_max':.05,'gap_min_m':.0005},'hold':{'continuous_s':5.,'total_timeout_s':5.75,'small_slip_allowed':True},'drop':{'relative_down_displacement_m':.03,'unsupported_continuous_s':.15,'mouth_support_Z_N_min':20.},'all_phases':'First source/structure/loop/ROM/speed/2.025mm/hidden/nonmouth guard ends; no retry. Drop defined only after platformwithdrawal; no instant softmicro-slip failure.'}
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
 selected_target=float(args.target_input_Nm);plan=json.loads(json.dumps(PLAN));plan['preload']['target_input_Nm']=selected_target
 handoff=args.handoff;h=json.load(open(handoff));refs(h)
 assert h['qa_source']['sha256']=='8d63e8c37d67eca47c98a5feb4371028fc231b078cb574275bc192a77ead76ae';qa=load(h['qa_source']['path'],'qa043');mass=float(h['payload']['assembly_mass_kg']);assert 5<=mass<=20
 plan['fixture_total_mass_kg']=mass;plan['settle']['table_N_range']=[mass*9.81-20,mass*9.81+20];holdledger=qa.HoldLedger()
 model=mj.MjModel.from_binary_path(h['mjb']['path']);d=mj.MjData(model);z=np.load(h['initial']['path']);d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl'];mj.mj_forward(model,d)
 mod=load(h['source']['path'],'fixture041');adapter=load(h['adapter']['path'],'adapter12');drv=adapter.FrozenPhysics(Path(h['adapter']['path']).parent)
 cfg=json.load(open(h['fixture_guard']['path']));table=json.load(open(h['retained_table']['path']));obs=qa.observe_scaled(model,d,correct_box_gap(model,d,mod.observe_fixture(model,d,cfg,table)))
 assert model.nu==2 and model.neq==1 and model.opt.timestep==.0005 and not obs['reasons'];assert model.actuator(0).name=='beak_hinge_motor'
 ji=model.joint('beak_input_rotor');qi=int(ji.qposadr[0]);vi=int(ji.dofadr[0]);pj=int(model.joint('platform_slide').qposadr[0]);pid=model.body('calibrated_hanging_assembly').id
 assert abs(sum(model.body_mass[i]for i in range(model.nbody)if model.body_rootid[i]==pid)-mass)<1e-9
 plan_sha=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest();required={'root_authorized':True,'runner_sha256':sha(__file__),'handoff_sha256':sha(handoff),'scene_sha256':h['scene']['sha256'],'mjb_sha256':h['mjb']['sha256'],'initial_sha256':h['initial']['sha256'],'plan_sha256':plan_sha,'selected_input_target_Nm':selected_target,'fixture_mass_kg':mass,'qa_source_sha256':h['qa_source']['sha256']}
 if args.execute:
  assert args.authorization;auth=json.load(open(args.authorization));assert all(auth.get(k)==v for k,v in required.items()),'ExactRootsource/plan authorizationrequired';os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
 args.out.mkdir(parents=True);dump(args.out/'command_plan.json',plan);dump(args.out/'required_authorization_fields.json',required);(args.out/'runner_snapshot.py').write_bytes(Path(__file__).read_bytes());(args.out/'source_bound_handoff.json').write_bytes(handoff.read_bytes())
 for k in ['scene','mjb','initial']:(args.out/Path(h[k]['path']).name).write_bytes(Path(h[k]['path']).read_bytes())
 dump(args.out/'zero_step_receipt.json',{'physics_steps':0,'required_authorization':required,'zero_observation':obs,'clock':{'physics_s':.0005,'drive_s':.005,'reference_s':.02},'adapter_once_axis5_to_bench0':True,'all3mechanismjoint_ROM_check':True,'no_hot_initialization':True,'fixture_not_wholeGoose':True})
 if not args.execute:print(json.dumps({'status':'ZERO_STEP_READY','out':str(args.out),'runner_sha256':sha(__file__),'plan_sha256':plan_sha,'selected_input_target_Nm':selected_target,'fixture_mass_kg':mass,'qa_source_sha256':h['qa_source']['sha256']}));return
 (args.out/'root_authorization.json').write_bytes(args.authorization.read_bytes());started=time.monotonic();phase='settle';phase_start=0.;events=[];rows=[];last_request=0.;target=float(d.qpos[qi]);platform_ref=0.;bilat=0.;offclock=0.;holdclock=0.;unsupported=0.;failure=None;entry_com=d.subtree_com[pid].copy();fullinputclock=0.;ledger=(args.out/'contacts_substeps.jsonl').open('w');tick=0
 def enter(new):
  nonlocal phase,phase_start
  events.append({'time':float(d.time),'from':phase,'to':new,'observation':obs});phase=new;phase_start=float(d.time)
 try:
  while d.time<12-1e-10:
   if time.monotonic()-started>900:failure={'reason':'wall900'};break
   t=float(d.time);age=t-phase_start;normal=obs['grip_normal_N'];both=min(normal.values())>5
   if tick%4==0:
    if phase=='settle':
     speed=np.linalg.norm(d.qvel[int(model.joint('test_object_free6d').dofadr[0]):int(model.joint('test_object_free6d').dofadr[0])+3])
     if age>=.15 and plan['settle']['table_N_range'][0]<=obs['platform_N']<=plan['settle']['table_N_range'][1] and abs(obs['platform_ballast_signed_gap_m'])<.001 and speed<.02:enter('close')
     elif age>.75:failure={'reason':'platform_settle_timeout'};break
    elif phase=='close':
     if bilat>=.1:enter('preload')
     elif age>3.5 or target>=-1e-8:failure={'reason':'no_bilateral_capture_within_finite_ROM_time'};break
     elif abs(obs['input_speed_rad_s'])<=.7:target=min(0.,target+.004)
    elif phase=='preload':
     if fullinputclock>=.1:enter('withdraw')
     elif age>1.:failure={'reason':'preload_actual_selected_target_not_reached'};break
    elif phase=='withdraw':
     platform_ref=max(-.04,platform_ref-.0004)
     if offclock>=.02:enter('hold')
     elif age>2.75:failure={'reason':'platform_not_actually_released'};break
    elif phase=='hold':
     if holdclock>=5:enter('complete');break
     if age>5.75:failure={'reason':'continuous_full_load_hold_not_completed'};break
   if phase in ['settle','close']:
    requested=drv.kp[5]*(target-d.qpos[qi])-drv.kd[5]*d.qvel[vi]
   else:requested=last_request+np.clip(selected_target-last_request,-.025,.025)
   request18=np.zeros(18);vel18=np.zeros(18);request18[5]=requested;vel18[5]=d.qvel[vi];limited=drv.limit_torque(request18,vel18);tau=float(limited[5]);last_request=tau;d.ctrl[0]=tau;d.ctrl[1]=platform_ref
   for sub in range(10):
    mj.mj_step(model,d);mj.mj_forward(model,d);obs=qa.observe_scaled(model,d,correct_box_gap(model,d,mod.observe_fixture(model,d,cfg,table)))
    obs['hold_ledger']=holdledger.add(obs)
    if obs['selected_TPU_outside_force_N']>1.:obs['reasons'].append('selected_TPU_workface_domain_exited_NOT_CAPACITY_LIMIT')
    for n in ['beak_hinge','beak_input_rotor','beak_coupler_link']:
     j=model.joint(n);x=float(d.qpos[int(j.qposadr[0])]);lo,hi=model.jnt_range[j.id]
     if not lo-1e-8<=x<=hi+1e-8:obs['reasons'].append('source_ROM_'+n)
    both=min(obs['grip_normal_N'].values())>5;bilat=bilat+.0005 if both else 0.;offclock=offclock+.0005 if obs['hold_eligibility']else 0.;holdclock=holdclock+.0005 if phase=='hold'and obs['hold_eligibility']else 0.;fullinputclock=fullinputclock+.0005 if abs(obs['input_tau_Nm']-selected_target)<.01 else 0.
    unsupported=unsupported+.0005 if phase in ['withdraw','hold']and obs['platform_N']<.05 and obs['mouth_force_on_object_world_N'][2]<20 else 0.
    row={'time':float(d.time),'phase':phase,'qpos':d.qpos.copy(),'qvel':d.qvel.copy(),'qacc':d.qacc.copy(),'ctrl':d.ctrl.copy(),'actuator_force':d.actuator_force.copy(),'requested_input':requested,'limited_input':tau,'platform_ref':platform_ref,'hold_clock':holdclock,'observation':obs};ledger.write(json.dumps(row,default=lambda x:x.tolist()if isinstance(x,np.ndarray)else str(x))+'\n')
    rows.append({k:v for k,v in row.items()if k!='observation'})
    if obs['reasons']:failure={'reason':'original_guard','reasons':obs['reasons'],'time':float(d.time)};break
    if unsupported>.15 or (phase in ['withdraw','hold']and obs['platform_N']<.05 and entry_com[2]-d.subtree_com[pid,2]>.03):failure={'reason':'declared_drop_or_unsupported_loss','time':float(d.time)};break
   tick+=1
   if tick%4==0:print(json.dumps({'time':float(d.time),'phase':phase,'tau':obs['input_tau_Nm'],'N':obs['grip_normal_N'],'table_N':obs['platform_N'],'gap':obs['platform_ballast_signed_gap_m'],'hold_clock':holdclock,'reasons':obs['reasons']}),flush=True)
   if failure:break
  if phase!='complete' and failure is None:failure={'reason':'finite_sim12_budget_before_complete'}
 except Exception as error:
  failure={'reason':'software_exception_not_hardware_failure','error':repr(error),'time':float(d.time)}
 finally:
  ledger.close();np.savez_compressed(args.out/'trajectory_substeps.npz',**{k:np.array([r[k]for r in rows])for k in rows[0]}if rows else {});np.savez_compressed(args.out/'final_actual_state.npz',time=float(d.time),qpos=d.qpos,qvel=d.qvel,qacc=d.qacc,ctrl=d.ctrl,actuator_force=d.actuator_force);dump(args.out/'events.json',events);dump(args.out/'result.json',{'phase':phase,'actual_end_s':float(d.time),'failure':failure,'hold_continuous_s':holdclock,'selected_input_target_Nm':selected_target,'actual_fixture_mass_kg':mass,'mass_retained_not_necessarily_stable':True,'actual_observation':obs,'physics_steps':len(rows),'wall_s':time.monotonic()-started,'no_retry':True,'no_wholeGoose_or_transport_qualification':True});print(json.dumps({'finished':True,'phase':phase,'time':float(d.time),'failure':failure,'hold_s':holdclock}),flush=True)
if __name__=='__main__':main()
