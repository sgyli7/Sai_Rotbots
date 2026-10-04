"""Validate the 11-leaf M0 engineering entry, never claim learned task success."""
from pathlib import Path
import argparse, hashlib, json, subprocess, time
import numpy as np
import mujoco
from scipy.spatial import ConvexHull
from sai_agent.goose.task_proxy_runtime import TaskProxyRuntime
from sai_agent.goose.task_goal import TaskGoal
from sai_agent.goose.stage_one_gravity import NominalNeckGravity, quat_matrix
from sai_agent.goose.convex_support import compiled_support, compiled_body_vertices

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/Goose_V0.1'
SCENARIOS={'neutral':1500,'joint_motion':500,'jaw_full_range':500}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def action_at(s,t):
 a=np.zeros(18);v=np.sin(t*.02*2*np.pi*.25)
 if s=='joint_motion':a[0]=.1*v;a[5]=.1*(1-v)/2;a[6]=.04*v;a[12]=-.04*v
 if s=='jaw_full_range':a[5]=(np.sin(t*.02*2*np.pi*.125)+1)/2
 return a

def post_depth(m,d,foot_ids):
 values=[]
 for g in foot_ids:
  v=compiled_body_vertices(m,g);b=m.geom_bodyid[g]
  values.append(max(0.,-float((v@d.xmat[b].reshape(3,3).T+d.xpos[b])[:,2].min())))
 return max(values)

def source_trace(model,contract,scenario,ticks):
 r=TaskProxyRuntime(model.resolve(),contract.resolve());rows=[]
 for i in range(ticks):
  t=time.perf_counter();obs,info=r.step(action_at(scenario,i));ms=(time.perf_counter()-t)*1000
  rows.append(dict(tick=i+1,q=r.data.qpos[r.qidx].tolist(),qd=r.data.qvel[r.vidx].tolist(),root_position_m=r.data.qpos[:3].tolist(),upright=info['upright'],failure=info['failure'],post_integration_sole_depth_m=post_depth(r.model,r.data,r.foot_geoms),physics_integrations=info['physics_integrations'],controller_updates=info['controller_updates'],step_ms=ms))
 return rows

def metrics(t):
 return dict(ticks=len(t),minimum_upright=min(v['upright'] for v in t),maximum_post_integration_sole_depth_m=max(v['post_integration_sole_depth_m'] for v in t),maximum_joint_speed_rad_s=float(np.max(np.abs([v['qd'] for v in t]))),step_p95_ms=float(np.percentile([v['step_ms'] for v in t],95)))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--native-probe',type=Path,required=True);ap.add_argument('--out',type=Path,default=ROOT/'artifacts/Goose_V0.1/task_proxy_11_v1');args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 model=ROBOT/'models/task_proxy_11_v1/robot.xml';contract=ROBOT/'configs/task_proxy_11_v1_contract.json';plant=ROBOT/'models/task_proxy_11_v1/native_plant.json';c=json.loads(contract.read_text())
 r=TaskProxyRuntime(model.resolve(),contract.resolve());m=r.model
 assert m.ngeom-1==11 and m.nbody-1==21 and m.nu==18 and m.njnt==21
 complexity=dict(robot_collision_leaves=11,convex_mesh_leaves=11,sole_box_leaves=0,robot_bodies=21,active_axes=18,passive_hinges=2,compiled_support_vertices=sum(len(compiled_support(m,i)) for i in range(m.nmesh)),maximum_mesh_support_vertices=max(len(compiled_support(m,i)) for i in range(m.nmesh)))
 sig=json.loads((ROBOT/'source/task_proxy_11_v1/physical_signature.json').read_text())
 physical={k:bool(np.array_equal(getattr(m,k),v)) for k,v in sig['fields'].items()}
 assert all(physical.values())
 # Source-derived upper contact plane must not be bridged by the merged head hull.
 g=m.geom('head_upper_bill_envelope').id;b=m.geom_bodyid[g];v=compiled_body_vertices(m,g)@r.data.xmat[b].reshape(3,3).T+r.data.xpos[b]-[0,0,.002];eq=ConvexHull(v).equations
 plane=c['functional_grip_refinement']['contact_plane_world_zero_z_m'];face_errors=[]
 polygon=np.array(c['functional_grip_refinement']['exact_source_contact_polygon_world_m'])
 center=polygon[:,:2].mean(axis=0)
 samples=np.r_[polygon[:,:2]*.999+center*.001,((polygon[:,:2]+np.roll(polygon[:,:2],1,axis=0))/2)*.999+center*.001,center[None,:]]
 for x,y in samples:
  valid=eq[:,2]<-1e-10;z=max(-(eq[valid,0]*x+eq[valid,1]*y+eq[valid,3])/eq[valid,2]);face_errors.append(abs(float(z-plane)))
 assert max(face_errors)<2e-7
 # Finite coupled poses, with explicit neighbour-role exclusions; not continuous CAD sweeps.
 domain=json.loads((ROBOT/'evidence/task_action_domain_v1.json').read_text());poses={};d=mujoco.MjData(m)
 for label,states in list(domain['paths'].items())+[(s['label'],[s]) for s in domain['known_rejected_combinations']]:
  rejected=0
  for state in states:
   mujoco.mj_resetData(m,d);d.qpos[:3]=state['root_translation_m'];d.qpos[3:7]=state['root_quaternion_wxyz']
   for n,q in state['joint_q_rad'].items():d.qpos[m.joint(n).qposadr[0]]=q
   for j in c['passive_linkage_joints']:d.qpos[m.joint(j['name']).qposadr[0]]=j['mimic_multiplier']*d.qpos[m.joint(j['mimic_joint']).qposadr[0]]+j['mimic_offset_rad']
   mujoco.mj_forward(m,d)
   hits=[x for x in d.contact if all(m.geom_bodyid[g] for g in x.geom) and x.dist < -1e-5]
   rejected+=bool(hits)
  expected=label not in domain['paths'];assert bool(rejected)==expected
  poses[label]=dict(states=len(states),rejected_states=rejected,integration_steps=0)
 summary={};gravity=NominalNeckGravity(c);goal=TaskGoal('probe_item',(.2,.1,.02),(1,0,0,0),(.4,-.1,.02));controller_error=0.;observation_error=0.
 for scenario,ticks in SCENARIOS.items():
  source=source_trace(model,contract,scenario,ticks);native_path=args.out/(scenario+'_rapier.json')
  subprocess.run([str(args.native_probe.resolve()),str(plant),str(contract),str(native_path),scenario,str(ticks)],check=True)
  target=json.loads(native_path.read_text());trace=target['trace'];assert len(trace)==ticks and target['native_collider_count']==target['source_geometry_count']==11
  assert target['native_solver_iterations']==1 and abs(target['native_dt_s']-.02)<1e-9
  assert target['physical_integrations']==ticks and target['actual_native_shape_leaves']==11
  cooked_errors=[];exported={v['name']:v for v in json.loads(plant.read_text())['colliders']}
  for shape in target['native_shape_readback']:
   actual=np.array(shape['points_source_local_m']);expected=np.array(exported[shape['name']]['vertices_local_m']);a=ConvexHull(actual).equations;e=ConvexHull(expected).equations
   cooked_errors.extend([max(0.,float((expected@a[:,:3].T+a[:,3]).max())),max(0.,float((actual@e[:,:3].T+e[:,3]).max()))])
  assert max(cooked_errors)<1e-6
  tm_cooked=dict(actual_native_shape_leaves=target['actual_native_shape_leaves'],actual_native_support_points=target['actual_native_support_points'],maximum_directed_support_plane_error_m=max(cooked_errors))
  assert max(x['full_inertia_relative_error'] for x in target['body_measurements'])<5e-6
  assert max(x['com_error_m'] for x in target['body_measurements'])<1e-6
  assert max(x['mass_error_kg'] for x in target['body_measurements'])<1e-6
  sm,tm=metrics(source),metrics(trace);pin=max(v['jaw_pin_error_m'] for v in trace)
  for side,rows,mt in [('source',source,sm),('target',trace,tm)]:
   assert mt['minimum_upright']>.99 and mt['maximum_post_integration_sole_depth_m']<.0015 and mt['step_p95_ms']<20
   assert all(v['controller_updates']==v['tick'] and v.get('physics_integrations',v.get('integrations'))==v['tick'] for v in rows)
   assert not any(v.get('failure',False) for v in rows)
   q=np.array([v['q'] for v in rows]);bounds=np.array([j['range_rad'] for j in c['joints']]);assert np.all(q>=bounds[:,0]-1e-5) and np.all(q<=bounds[:,1]+1e-5)
  assert pin<.00075
  qerr=float(np.max(np.abs(np.array([v['q'] for v in source])-np.array([v['q'] for v in trace]))));rooterr=float(np.max(np.linalg.norm(np.array([v['root_position_m'] for v in source])-np.array([v['root_position_m'] for v in trace]),axis=1)))
  # Cross-engine comparison tolerance is for this bounded holding/motion probe.
  assert qerr<.075 and rooterr<.015
  for i,row in enumerate(trace):
   # FF is recorded pre-integration; use previous feedback, not this Tick's post-state.
   prev=trace[i-1] if i else dict(q=[0.]*18,root_rotation_wxyz=[1.,0,0,0]);ff=gravity(np.array(prev['q'])[:6],prev['root_rotation_wxyz']);controller_error=max(controller_error,float(np.max(abs(ff-row['gravity_feedforward_nm']))))
   expected=goal.actor_extension(np.array(row['root_position_m']),row['root_rotation_wxyz'],quat_matrix(row['root_rotation_wxyz']),0)
   observation_error=max(observation_error,float(np.max(abs(expected-np.array(row['pickup_observation'])[65:]))))
   assert len(row['observation'])==65 and len(row['pickup_observation'])==82
  summary[scenario]=dict(source=sm,target=tm,native_geometry=tm_cooked,maximum_jaw_pin_error_m=pin,maximum_paired_joint_position_difference_rad=qerr,maximum_paired_root_position_difference_m=rooterr,target_report_sha256=sha(native_path))
 assert controller_error<1e-5 and observation_error<1e-6
 report=dict(schema='goose_task_proxy_m0_acceptance_v1',candidate_id=c['candidate'],model_sha256=sha(model),contract_sha256=sha(contract),plant_sha256=sha(plant),complexity=complexity,physical_identity=physical,finite_pose_checks=poses,upper_grip_face_maximum_plane_error_m=max(face_errors),scenarios=summary,nominal_gravity_cross_language_maximum_error_nm=controller_error,pickup_extension_cross_language_maximum_error=observation_error,engineering_entry_pass=True,full_task_success_claim=False,scope='Cold start, 30s holding, 10s small joint motion, 10s full jaw travel, finite FK, native SI readback, clocks and observation extension; no learned task, uneven terrain, physical material, drag or complete hardware qualification',environment=dict(mujoco=mujoco.__version__,rapier='0.35.3 with isolated explicit contact fork',native_binary_sha256=sha(args.native_probe),source_physical_integrations=sum(SCENARIOS.values()),target_physical_integrations=sum(SCENARIOS.values()),optimizer_updates=0),thresholds=dict(upright_minimum=.99,post_sole_depth_maximum_m=.0015,jaw_pin_error_maximum_m=.00075,paired_joint_error_maximum_rad=.075,paired_root_error_maximum_m=.015,step_p95_maximum_ms=20,full_inertia_relative_error_maximum=5e-6))
 (args.out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
