"""Bounded planted-foot turn feasibility; no learned gait or hardware release."""
from pathlib import Path
import json,sys,hashlib,copy
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate

def main():
    paths=[R/'configs/stage_two_contract.json',R/'evidence/manufacturing_component_parameters.json']
    contract,data=[json.loads(p.read_text()) for p in paths];s=candidate()
    lift=data['rigid_coordinate_lift_m']
    for n in s.pivots:s.pivots[n]+=[0,0,lift]
    s.pivots['torso']=np.zeros(3);s.items=copy.deepcopy(data['items']);s.grip+=[0,0,lift];s.tip+=[0,0,lift]
    for side in ['right','left']:s.contact_hulls[side]=ConvexHull(data['contact_hulls'][side])
    limits={j['name']:j['range_rad'] for j in contract['joints']};model,_=s.model(0)
    cases=[]
    for side in ['left','right']:
        q,root,rot=s.pose();q,root,rot=s.bank(side,q,root)
        poses,_=s.fk(q,root,rot);target_p,target_r=poses[side+'_ankle_roll']
        names=[side+'_'+n for n in ['hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch','ankle_roll']]
        for degrees in [-30,-15,15,30]:
            desired=Rotation.from_euler('z',degrees,degrees=True).as_matrix()@rot
            def residual(x):
                state=dict(q);state.update(zip(names,x));p,r=s.fk(state,root,desired)[0][side+'_ankle_roll']
                return np.r_[(p-target_p)*10,Rotation.from_matrix(target_r.T@r).as_rotvec()]
            x0=np.array([q[n] for n in names]);x0[0]=np.clip(x0[0]-np.deg2rad(degrees),*limits[names[0]])
            solved=least_squares(residual,x0,bounds=([limits[n][0] for n in names],[limits[n][1] for n in names]),max_nfev=250,ftol=1e-11,xtol=1e-11,gtol=1e-11)
            state=dict(q);state.update(zip(names,solved.x));p,r=s.fk(state,root,desired)[0][side+'_ankle_roll']
            pos=np.linalg.norm(p-target_p);angle=np.linalg.norm(Rotation.from_matrix(target_r.T@r).as_rotvec())
            check=s.evaluate('turn_'+side+'_'+str(degrees),state,root,desired,[side],0,0,model)
            violations=[n for n,v in check['joint_torque_nm'].items() if abs(v)>next(j['continuous_design_limit_nm'] for j in contract['joints'] if j['name']==n)]
            cases.append(dict(side=side,torso_yaw_change_deg=degrees,stance_q_rad={n:state[n] for n in names},position_error_m=float(pos),orientation_error_rad=float(angle),kinematic_pass=bool(pos<1e-5 and angle<1e-4),static_contact_feasible=check['static_contact_feasible'],continuous_torque_violations=violations,static=check))
    result=dict(schema='goose_turning_kinematic_screen_v1',leg_axes={j['name']:j['axis_parent'] for j in contract['joints'] if 'hip_' in j['name'] or 'ankle_' in j['name'] or 'knee_' in j['name']},cases=cases,
        planted_foot_kinematic_pass=all(p['kinematic_pass'] for p in cases),static_screen_pass=all(p['static_contact_feasible'] and not p['continuous_torque_violations'] for p in cases),
        turning_gait_pass=False,hardware_turning_pass=False,manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        limitations=['Static end poses with an unactuated prescribed torso rotation, not a trajectory controller or walking test',
            'Other foot is not lifted here and is excluded from contacts: swing-foot clearance/trajectory and full collision still required',
            'Native cross-axis mounts, cable sweep, actual yaw speed/torque and repeated90/180degree step turns are unreleased',
            'Hip yaw range is joint range, not an upper bound or measured radius/rate of whole-body turning'])
    (R/'evidence/manufacturing_turning_screen.json').write_text(json.dumps(result,indent=2)+'\n')
    print({k:result[k] for k in ['planted_foot_kinematic_pass','static_screen_pass','turning_gait_pass']})
    print([{k:p[k] for k in ['side','torso_yaw_change_deg','position_error_m','orientation_error_rad','static_contact_feasible','continuous_torque_violations']} for p in cases])
    return 0 if result['planted_foot_kinematic_pass'] and result['static_screen_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
