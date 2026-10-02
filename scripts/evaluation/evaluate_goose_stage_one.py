"""Independent holdout rollouts and slow whole-body pose transitions.

Reports actual velocity and failures; a finite PPO checkpoint is never counted
as a walking pass merely because it stayed standing.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import mujoco
from sai_agent.goose.stage_one import StageOneEnv
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def main():
 p=argparse.ArgumentParser();p.add_argument('--policy',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--steps',type=int,default=600);a=p.parse_args()
 model=R/'models/stage_one/robot.xml';contract=R/'configs/stage_one_contract.json';c=json.loads(contract.read_text());results=[]
 if a.policy:
  import onnxruntime as ort
  policy=ort.InferenceSession(str(a.policy),providers=['CPUExecutionProvider'])
  meta=json.loads((a.policy.parent/'metadata.json').read_text())
  if meta['model_sha256']!=c['model_sha256'] or meta['contract_sha256']!=hashlib.sha256(contract.read_bytes()).hexdigest():raise ValueError('Policy was trained with different model/contract')
 for mode in ('nominal_stand','randomized_stand','randomized_forward'):
  e=StageOneEnv(model,contract,16,93017,randomize=mode!='nominal_stand',commands=False)
  if mode=='randomized_forward':e.commands[:,0]=.12
  start=np.array([d.qpos[:3].copy() for d in e.data]);fail=0;records=[]
  for step in range(a.steps):
   action=policy.run(None,{'observation':e.observations()})[0] if a.policy else np.zeros((16,18))
   obs,rew,done,rows=e.step(action);fail+=sum(r['failure'] for r in rows);records.extend(rows)
   if mode=='randomized_forward':e.commands[:,0]=.12
  speeds=np.array([r['velocity_body_m_s'] for r in records]);torque=np.array([r['torque_nm'] for r in records])
  results.append(dict(mode=mode,episodes=16,seconds_per_env=a.steps*.02,failures=fail,mean_velocity_x_m_s=float(speeds[:,0].mean()),mean_abs_command_error_m_s=float(np.mean(abs(speeds[:,0]-(.12 if mode=='randomized_forward' else 0)))),mean_upright=float(np.mean([r['upright'] for r in records])),minimum_height_m=min(r['height_m'] for r in records),rms_torque_nm=np.sqrt(np.mean(torque*torque,axis=0)).tolist(),max_torque_nm=np.max(abs(torque),axis=0).tolist(),mean_saturation=float(np.mean([r['torque_saturation_fraction'] for r in records])),single_support_fraction=float(np.mean([sum(r['feet_touch'])==1 for r in records])) ))
 transitions=[];gates=json.loads((R/'evidence/stage_one_system_gate.json').read_text())
 for name in ('crouch_40','crouch_60','crouch_80','low_reach'):
  q=next(p['joint_q_rad'] for p in gates['pose_geometry'] if p['name']==name);desired=np.array([q[n] for n in c['joint_order']]);e=StageOneEnv(model,contract,1,randomize=False,commands=False,auto_reset=False);e.max_episode_length=10000;records=[];collision_names=set();failure=False
  for step in range(600):
   u=np.clip(step/300,0,1);u=u*u*(3-2*u);action=(u*desired/e.scale)[None,:];obs,rew,done,rows=e.step(action);records.extend(rows)
   d=e.data[0];m=e.models[0]
   for ct in d.contact:
    if ct.dist<-.001 and e.floor_id not in (ct.geom1,ct.geom2):collision_names.add((m.geom(int(ct.geom1)).name,m.geom(int(ct.geom2)).name))
   if rows[0]['failure']:failure=True;break
  d=e.data[0];bid=e.models[0].body('head_roll').id;grip=d.xpos[bid]+d.xmat[bid].reshape(3,3)@(np.array([.24,0,.553])-np.array(c['joints'][4]['pivot_world_at_zero_m']))
  transitions.append(dict(pose=name,failure=failure,steps=len(records),nonadjacent_collision_pairs=sorted(collision_names),final_grip_m=grip.tolist(),final_body_height_m=float(d.xpos[e.torso,2]),joint_tracking_error_max_rad=float(abs(d.qpos[e.qidx]-desired).max()),minimum_upright=min(r['upright'] for r in records),failure_last_record=records[-1] if failure else None,minimum_height_m=min(r['height_m'] for r in records),rms_torque_nm=np.sqrt(np.mean(np.array([r['torque_nm'] for r in records])**2,axis=0)).tolist(),status='PASS_SLOW_NOMINAL_TRANSITION' if not failure and not collision_names and abs(d.qpos[e.qidx]-desired).max()<.15 else 'FAIL'))
 report=dict(status='INDEPENDENT_HOLDOUT_RESULTS',model_sha256=c['model_sha256'],contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),policy_sha256=hashlib.sha256(a.policy.read_bytes()).hexdigest() if a.policy else None,actor='PPO ONNX' if a.policy else 'zero action PD baseline',seed=93017,rollouts=results,slow_pose_transitions=transitions,walking_acceptance=False,sim2real_acceptance=False)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
