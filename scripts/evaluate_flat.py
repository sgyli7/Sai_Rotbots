"""Fixed CPU MuJoCo command suite: no training rewards in acceptance criteria."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sai_agent.control import observation_numpy, targets_numpy, torque_numpy, filter_action_numpy, CONTROL_DT
from sai_agent.runtime import JointAdapter

p=argparse.ArgumentParser()
p.add_argument('--policy', type=Path, help='Omit for the zero-residual analytical baseline')
p.add_argument('--out', type=Path, required=True)
p.add_argument('--require-pass', action='store_true')
p.add_argument('--full-robot', action='store_true',help='Keep all arm/cargo joints and original contact meshes')
p.add_argument('--robot',choices=['Sai_Agent_001','Sai_Agent_002'],default='Sai_Agent_001')
args=p.parse_args()
from sai_agent.paths import model_root
MODELS=model_root(args.robot)
args.out.mkdir(parents=True, exist_ok=True)
if args.policy:
    import onnxruntime as ort
    options=ort.SessionOptions(); options.intra_op_num_threads=2; options.inter_op_num_threads=1
    policy=ort.InferenceSession(str(args.policy), options, providers=['CPUExecutionProvider'])
else:
    policy=None
cases = [('stop',0,0,False), ('W',.16,0,False), ('S',-.16,0,False),
         ('A',0,.45,False), ('D',0,-.45,False), ('WA',.14,.3,False),
         ('shift',0,0,True), ('W_shift',.14,0,True)]
model_path=MODELS/'locomotion.xml'
if args.full_robot:
    model_path=MODELS/'full/locomotion-articulated.xml'
    root=ET.parse(MODELS/'full/robot.xml').getroot()
    world=root.find('worldbody')
    for body in list(world.findall('body')):
        if body.get('name')=='item':world.remove(body)
    for g in list(world.findall('geom')):
        if g.get('name','').startswith('course_'):world.remove(g)
    keyframe=root.find('keyframe')
    if keyframe is not None:root.remove(keyframe)
    ET.ElementTree(root).write(model_path,encoding='unicode')
model=mujoco.MjModel.from_xml_path(str(model_path))
adapter=JointAdapter(model)
substeps=round(CONTROL_DT/model.opt.timestep)
rows=[]
start=time.monotonic()
for name, vx, yaw, use_shift in cases:
    data=mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    prev=np.zeros(16); crouch=0.; trace=[]
    for k in range(600):
        t=k*CONTROL_DT
        command=np.array([vx if t>=1 else 0., yaw if t>=1 else 0.])
        requested_crouch=float(use_shift and 3<=t<8)
        crouch+=np.clip(requested_crouch-crouch, -.04, .04)
        q,v=adapter.state(data)
        obs=observation_numpy(q, v, command, crouch, prev,
                              k*CONTROL_DT*2*math.pi/2.4, np.zeros(24))
        action=policy.run(None,{'obs':obs[None]})[0][0] if policy else np.zeros(16)
        action=filter_action_numpy(action,command)
        target=targets_numpy(action, command, crouch)
        for _ in range(substeps):
            adapter.apply(data,target)
            mujoco.mj_step(model,data)
        prev=action
        qw,qx,qy,qz=data.qpos[3:7]
        heading=math.atan2(2*(qw*qz+qx*qy), 1-2*(qy*qy+qz*qz))
        q,v=adapter.state(data)
        local_v=observation_numpy(q,v,command,crouch,prev,0,np.zeros(24))[3:6]
        trace.append([t,*data.qpos[:3],heading,local_v[0],data.qvel[5],
                      1-2*(qx*qx+qy*qy),crouch,*action,local_v[1]])
        if not np.isfinite(data.qpos).all() or trace[-1][7]<.6:
            break
    a=np.array(trace)
    np.savez_compressed(args.out/f'{name}.npz',trace=a,
                       columns=np.array(['time','x','y','z','yaw','body_vx','body_wz','upright','crouch']+
                                        [f'action_{i}' for i in range(16)]+['body_vy']))
    steady=a[:,0]>=2
    recovered=a[:,0]>=9
    normal=(a[:,0]>=1)&(a[:,0]<3)
    low=(a[:,0]>=5)&(a[:,0]<8)
    heading=np.unwrap(a[:,4])
    metrics=dict(case=name, duration=float(a[-1,0]+CONTROL_DT),
        displacement_xy_m=(a[-1,1:3]-a[0,1:3]).tolist(),
        yaw_change_rad=float(heading[-1]-heading[0]),
        velocity_mae=float(np.abs(a[steady,5]-vx).mean()) if steady.any() else 100.,
        yaw_mae=float(np.abs(a[steady,6]-yaw).mean()) if steady.any() else 100.,
        lateral_mae=float(np.abs(a[steady,-1]).mean()) if steady.any() else 100.,
        min_upright=float(a[:,7].min()),
        crouch_drop_m=float(a[normal,3].mean()-a[low,3].mean()) if low.any() else 0.,
        recovered_height_difference_m=float(abs(a[normal,3].mean()-a[recovered,3].mean())) if recovered.any() else 100.)
    checks={'completed_12s':len(a)==600,'upright':metrics['min_upright']>.9,
            'velocity_tracking':metrics['velocity_mae']<.06,
            'yaw_tracking':metrics['yaw_mae']<.22,
            'lateral_tracking':metrics['lateral_mae']<.04}
    if name in ('stop','shift'):
        checks['stationary_drift']=np.linalg.norm(metrics['displacement_xy_m'])<.12
    if use_shift:
        checks.update(crouch_drop=.023<metrics['crouch_drop_m']<.055,
                      stand_recovery=metrics['recovered_height_difference_m']<.012)
    if name in ('W','S'):
        checks['travel_direction']=np.sign(vx)*metrics['displacement_xy_m'][0]>.7
    if name in ('A','D'):
        checks['turn_direction']=np.sign(yaw)*metrics['yaw_change_rad']>1.5
        checks['turn_center_drift']=np.linalg.norm(metrics['displacement_xy_m'])<.4
    checks={key: bool(value) for key,value in checks.items()}
    metrics.update(checks=checks,passed=all(checks.values()))
    rows.append(metrics)
    print(json.dumps(metrics),flush=True)
result={'suite':'flat-command-v2','simulator':'CPU MuJoCo','mujoco_version':mujoco.__version__,
        'policy_sha256':hashlib.sha256(args.policy.read_bytes()).hexdigest() if args.policy else None,
        'model_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
        'full_robot':args.full_robot,'actuators':model.nu,'joints':model.njnt,
        'zero_input_control':'explicit wheel braking and analytical height posture; no pose forcing',
        'seconds':time.monotonic()-start,'cases':rows,'passed':all(r['passed'] for r in rows)}
(args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if args.require_pass and not result['passed']:
    raise SystemExit('Flat command acceptance failed; see result.json')
