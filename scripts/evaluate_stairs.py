"""Four real risers plus a three-second stop on the final level, each direction."""
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
import onnxruntime as ort

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sai_agent.terrain import Staircase,scene_xml
from sai_agent.control import SCAN_XY,observation_numpy,targets_stairs_numpy,filter_action_numpy,STAND_HEIGHT,HeadingHold
from sai_agent.runtime import JointAdapter

p=argparse.ArgumentParser()
p.add_argument('--policy',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
p.add_argument('--risers',type=float,nargs='+',default=[.02,.04,.06])
p.add_argument('--tread',type=float,default=.18)
p.add_argument('--initial-yaw',type=float,default=0.)
p.add_argument('--require-pass',action='store_true')
p.add_argument('--full-robot',action='store_true')
p.add_argument('--lift-height',type=float,default=.055)
p.add_argument('--heading-control',action='store_true')
p.add_argument('--speed',type=float,default=.12)
p.add_argument('--leg-scale',type=float,default=.18)
p.add_argument('--stride',type=float,default=.05)
p.add_argument('--max-seconds',type=float,default=30.,help='Declared per-flight time limit; default acceptance remains 30 s')
p.add_argument('--direction',choices=['both','up','down'],default='both')
p.add_argument('--crouch',type=float,default=0.,help='Requested normalized crouch, slewed at the deployment rate')
p.add_argument('--lane-control',action='store_true',help='Diagnostic known-route steering on the staircase center line')
p.add_argument('--yaw-correction-limit',type=float,default=.4,help='Outer heading correction bound in rad/s; motor torque limits remain fixed')
args=p.parse_args()
if args.max_seconds<=3: p.error('--max-seconds must exceed the required 3 s final stop')
if not 0<=args.crouch<=1: p.error('--crouch must be in [0, 1]')
if args.lane_control and not args.heading_control: p.error('--lane-control requires --heading-control')
args.out.mkdir(parents=True,exist_ok=True)
options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
policy=ort.InferenceSession(str(args.policy),options,providers=['CPUExecutionProvider'])
rows=[]
started=time.monotonic()
source=(ROOT/'models/locomotion.xml').read_text()
if args.full_robot:
    root=ET.parse(ROOT/'models/full/robot.xml').getroot();world=root.find('worldbody')
    for body in list(world.findall('body')):
        if body.get('name')=='item':world.remove(body)
    for geom in list(world.findall('geom')):
        if geom.get('name','').startswith('course_'):world.remove(geom)
    for mesh in root.findall('.//asset/mesh'):
        mesh.set('file',str(ROOT/'models/full'/mesh.get('file')))
    k=root.find('keyframe')
    if k is not None:root.remove(k)
    source=ET.tostring(root,encoding='unicode')
for descending in ([False,True] if args.direction=='both' else [args.direction=='down']):
    for riser in args.risers:
        course=Staircase(riser=riser,descending=descending,tread=args.tread)
        xml=scene_xml(source,course)
        model=mujoco.MjModel.from_xml_string(xml)
        data=mujoco.MjData(model)
        data.qpos[3:7]=[math.cos(args.initial_yaw/2),0,0,math.sin(args.initial_yaw/2)]
        mujoco.mj_forward(model,data)
        adapter=JointAdapter(model)
        wheels=[model.body(n+'_wheel').id for n in ['front_left','front_right','rear_left','rear_right']]
        last_edge=course.start+(course.count-1)*course.tread
        final_ground=float(course.height(last_edge+.1))
        trace=[];previous=np.zeros(16);cleared_at=None;heading_hold=HeadingHold(args.yaw_correction_limit);crouch=0.
        for k in range(math.floor(args.max_seconds/.02)):
            command=[args.speed if k>=25 and cleared_at is None else 0.,0.]
            q,v=adapter.state(data)
            qw,qx,qy,qz=q[3:7]
            yaw=math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz))
            c,s=math.cos(yaw),math.sin(yaw)
            xy=SCAN_XY@np.array([[c,s],[-s,c]])+q[:2]
            scan=course.height(xy[:,0],xy[:,1])
            crouch+=float(np.clip(args.crouch-crouch,-.04,.04))
            obs=observation_numpy(q,v,command,crouch,previous,k*.02*2*math.pi/3.2,scan)
            action=filter_action_numpy(policy.run(None,{'obs':obs[None]})[0][0],command)
            target=targets_stairs_numpy(action,command,crouch,k*.02/3.2,scan,args.lift_height,args.leg_scale,args.stride)
            if args.lane_control and command[0]>.015:
                # Known straight route y=0, using simulated odometry. Supply a
                # bounded heading reference; HeadingHold changes wheel speeds only.
                heading_hold.desired=float(np.clip(math.atan2(-q[1],.5),-.4,.4))
            if args.heading_control:target=heading_hold.apply(target,command,yaw,v[5])
            for _ in range(round(.02/model.opt.timestep)):
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
            if cleared_at is None and min(wheelx)>last_edge+.08:cleared_at=data.time
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
                'height_on_final_level':bool(abs(data.qpos[2]-(final_ground+STAND_HEIGHT-.035*crouch))<.02),
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
            full_robot=args.full_robot,actuators=model.nu,
            lift_height=args.lift_height,heading_control=args.heading_control,
            commanded_speed=args.speed,
            leg_scale=args.leg_scale,
            stride=args.stride,
            max_simulated_seconds=args.max_seconds,
            direction=args.direction,crouch=args.crouch,
            lane_control=args.lane_control,
            yaw_correction_limit=args.yaw_correction_limit,
            policy_sha256=hashlib.sha256(args.policy.read_bytes()).hexdigest(),
            runtime_seconds=time.monotonic()-started,mujoco_version=mujoco.__version__,
            sensor='Exact simulation height map; hardware depth reconstruction is not implemented')
(args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if args.require_pass and not result['passed']:raise SystemExit('Stair acceptance failed')
