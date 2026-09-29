"""Independent finite double-support reach validation; never an object-grasp pass."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import mujoco
from sai_agent.goose.stage_one import StageOneEnv
from sai_agent.goose.low_reach import SupportedReach
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'

def evaluate(stage='stage_two',seeds=(901,902,903,904),steps=1400,save_trajectory=None):
    model=R/'models'/stage/'robot.xml';contract=R/'configs'/f'{stage}_contract.json'
    c=json.loads(contract.read_text());cases=[]
    poses=json.loads((R/'evidence'/f'{stage}_system_gate.json').read_text())['pose_geometry']
    crouch=next(p['joint_q_rad'] for p in poses if p['name']=='crouch_60')
    qc=np.array([crouch[n] for n in c['joint_order']])
    for seed in [None,*seeds]:
        e=StageOneEnv(model,contract,1,seed=seed or 900,randomize=seed is not None,commands=False,auto_reset=False);e.max_episode_length=steps+1
        m,d=e.models[0],e.data[0];controller=SupportedReach(c,qc);hold=[];records=[];trajectory=[];bad=[];self_hits=[];torques=[];residuals=[];root_errors=[];contact_steps=0
        for k in range(steps):
            target,info=controller.reference(k*.02,d.qpos[e.qidx],d.qpos[3:7])
            _,_,_,rows=e.step((target/e.scale)[None,:]);row=rows[0]
            root_est=controller.root_from_supported_feet(d.qpos[e.qidx],d.qpos[3:7]);root_errors.append(np.linalg.norm(root_est-d.qpos[:3]))
            actual=d.xpos[m.body('head_roll').id]+d.xmat[m.body('head_roll').id].reshape(3,3)@controller.grip_local
            if info['phase']=='hold':hold.append(actual.tolist())
            residuals.append(info['ik_weighted_residual_m']);records.append(row);torques.append(e.last_tau[0].copy());contact_steps+=all(row['feet_touch'])
            if save_trajectory is not None and seed is None and k%5==0:trajectory.append(dict(time_s=float(d.time),qpos=d.qpos.tolist(),grip_m=actual.tolist(),phase=info['phase']))
            for contact in d.contact:
                pair={int(contact.geom1),int(contact.geom2)}
                if e.floor_id in pair and not pair.intersection(e.foot_ids):bad.append(dict(step=k,pair=[m.geom(int(contact.geom1)).name,m.geom(int(contact.geom2)).name],dist_m=float(contact.dist)))
                elif e.floor_id not in pair and contact.dist<-.0005:self_hits.append(dict(step=k,pair=[m.geom(int(contact.geom1)).name,m.geom(int(contact.geom2)).name],dist_m=float(contact.dist)))
            if row['failure'] or bad or self_hits:break
        hold=np.array(hold);tau=np.array(torques)
        success=bool(len(records)==steps and not bad and not self_hits and len(hold)>100 and abs(hold[-100:,2].mean()-.045)<.010 and abs(hold[-100:,0].mean()-.28)<.015 and min(row['upright'] for row in records)>.95)
        cases.append(dict(seed=seed,randomized=seed is not None,passed=success,steps=len(records),nonfoot_ground_contacts=bad[:5],self_collision_hits=self_hits[:5],hold_grip_mean_m=hold[-100:].mean(0).tolist() if len(hold) else None,hold_grip_min_z_m=float(hold[:,2].min()) if len(hold) else None,minimum_upright=min(row['upright'] for row in records),both_feet_contact_fraction=contact_steps/len(records),max_ik_weighted_residual_m=max(residuals),root_estimate_error_max_m=max(root_errors),joint_rms_torque_nm=np.sqrt(np.mean(tau*tau,axis=0)).tolist(),joint_max_torque_nm=np.max(abs(tau),axis=0).tolist(),final_root_height_m=float(d.qpos[2]),final_root_upright=records[-1]['upright'],final_joint_error_max_rad=float(np.max(abs(d.qpos[e.qidx])))))
        if trajectory:save_trajectory.write_text(json.dumps(dict(model_sha256=c['model_sha256'],frames=trajectory),separators=(',',':'))+'\n')
        print(json.dumps({k:cases[-1][k] for k in ('seed','passed','steps','hold_grip_mean_m','nonfoot_ground_contacts','self_collision_hits')}),flush=True)
    return dict(status='BOUNDED_DOUBLE_SUPPORT_APPROACH_CHECK',model_sha256=c['model_sha256'],contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'src/sai_agent/goose/low_reach.py',ROOT/'src/sai_agent/goose/stage_one.py']},cases=cases,all_passed=all(x['passed'] for x in cases),object_pickup_passed=False,walking_passed=False,limits=['Closed mouth only; no object contact or lift','Level floor, no-slip double support; only encoder/IMU in control; contact state is validation-only','Four sampled randomizations do not establish the entire uncertainty envelope','Grip target45mm above floor does not demonstrate picking up thin fabric or flat objects'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',default='stage_two');p.add_argument('--output',type=Path,required=True);p.add_argument('--trajectory',type=Path);a=p.parse_args()
    if a.trajectory:a.trajectory.parent.mkdir(parents=True,exist_ok=True)
    result=evaluate(a.stage,save_trajectory=a.trajectory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
