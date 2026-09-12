"""Four real risers plus a three-second stop on the final level, each direction."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import mujoco
import numpy as np
import onnxruntime as ort

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sai_agent.terrain import Staircase,scene_xml
from sai_agent.control import SCAN_XY,observation_numpy,targets_stairs_numpy,filter_action_numpy,STAND_HEIGHT
from sai_agent.runtime import JointAdapter

p=argparse.ArgumentParser()
p.add_argument('--policy',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
p.add_argument('--risers',type=float,nargs='+',default=[.02,.04,.06])
p.add_argument('--tread',type=float,default=.18)
p.add_argument('--initial-yaw',type=float,default=0.)
p.add_argument('--require-pass',action='store_true')
args=p.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
policy=ort.InferenceSession(str(args.policy),options,providers=['CPUExecutionProvider'])
rows=[]
started=time.monotonic()
for descending in [False,True]:
    for riser in args.risers:
        course=Staircase(riser=riser,descending=descending,tread=args.tread)
        xml=scene_xml((ROOT/'models/locomotion.xml').read_text(),course)
        model=mujoco.MjModel.from_xml_string(xml)
        data=mujoco.MjData(model)
        data.qpos[3:7]=[math.cos(args.initial_yaw/2),0,0,math.sin(args.initial_yaw/2)]
        mujoco.mj_forward(model,data)
        adapter=JointAdapter(model)
        wheels=[model.body(n+'_wheel').id for n in ['front_left','front_right','rear_left','rear_right']]
        last_edge=course.start+(course.count-1)*course.tread
        final_ground=float(course.height(last_edge+.1))
        trace=[];previous=np.zeros(16);cleared_at=None
        for k in range(1500):
            command=[.12 if k>=25 and cleared_at is None else 0.,0.]
            q,v=adapter.state(data)
            qw,qx,qy,qz=q[3:7]
            yaw=math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz))
            c,s=math.cos(yaw),math.sin(yaw)
            xy=SCAN_XY@np.array([[c,s],[-s,c]])+q[:2]
            scan=course.height(xy[:,0],xy[:,1])
            obs=observation_numpy(q,v,command,0.,previous,k*.02*2*math.pi/3.2,scan)
            action=filter_action_numpy(policy.run(None,{'obs':obs[None]})[0][0],command)
            target=targets_stairs_numpy(action,command,0.,k*.02/3.2,scan)
            for _ in range(10):
                adapter.apply(data,target)
                mujoco.mj_step(model,data)
            previous=action
            upright=1-2*(data.qpos[4]**2+data.qpos[5]**2)
            contact_wheels=set()
            penetration=0.
            for contact in data.contact:
                bodies=set(model.geom_bodyid[contact.geom].tolist())
                contact_wheels.update(bodies.intersection(wheels))
                penetration=max(penetration,float(-contact.dist))
            wheelx=data.xpos[wheels,0];wheelz=data.xpos[wheels,2]
            if cleared_at is None and min(wheelx)>last_edge+.05:cleared_at=data.time
            trace.append([data.time,*data.qpos[:3],yaw,upright,len(contact_wheels),penetration,
                          *wheelx,*wheelz])
            if upright<.6 or not np.isfinite(data.qpos).all():break
            if cleared_at is not None and data.time-cleared_at>=3:break
        a=np.array(trace)
        settled=a[a[:,0]>a[-1,0]-1.]
        checks={'all_wheels_cleared':bool(min(wheelx)>last_edge+.05),
                'three_second_stop':bool(cleared_at is not None and data.time-cleared_at>=3),
                'upright_on_final_level':bool(upright>.9),
                'remained_in_lane':bool(np.max(np.abs(a[:,2]))<.3),
                'height_on_final_level':bool(abs(data.qpos[2]-(final_ground+STAND_HEIGHT))<.02),
                'four_wheels_supported':bool(np.mean(settled[:,6]==4)>.7),
                'no_fall':bool(a[:,5].min()>.6)}
        name=f'{"down" if descending else "up"}-{round(riser*1000)}'
        np.savez_compressed(args.out/f'{name}.npz',trace=a)
        (args.out/f'{name}.xml').write_text(xml)
        row=dict(**course.as_dict(),initial_yaw=args.initial_yaw,passed=all(checks.values()),
                 checks=checks,simulated_seconds=data.time,cleared_at=cleared_at,
                 final_xyz=data.qpos[:3].tolist(),minimum_wheel_x=float(min(wheelx)),
                 min_upright=float(a[:,5].min()),max_penetration_m=float(a[:,7].max()))
        rows.append(row);print(json.dumps(row),flush=True)
result=dict(suite='continuous-stairs-v1',cases=rows,passed=all(r['passed'] for r in rows),
            policy_sha256=hashlib.sha256(args.policy.read_bytes()).hexdigest(),
            runtime_seconds=time.monotonic()-started,mujoco_version=mujoco.__version__,
            sensor='Exact simulation height map; hardware depth reconstruction is not implemented')
(args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if args.require_pass and not result['passed']:raise SystemExit('Stair acceptance failed')
