"""Development-only baseline across real four-riser flights, without pose forcing."""
import json
import math
from pathlib import Path
import sys
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sai_agent.terrain import Staircase, scene_xml
from sai_agent.control import targets_numpy, torque_numpy, SIDES, FRONTS

out=ROOT/'artifacts/stair-baseline'
out.mkdir(parents=True,exist_ok=True)
rows=[]
for descending in [False,True]:
    for riser in [.02,.04,.06]:
        course=Staircase(riser=riser,descending=descending)
        xml=scene_xml((ROOT/'models/locomotion.xml').read_text(),course)
        model=mujoco.MjModel.from_xml_string(xml)
        data=mujoco.MjData(model)
        mujoco.mj_forward(model,data)
        wheels=[model.body(name).id for name in ['front_left_wheel','front_right_wheel','rear_left_wheel','rear_right_wheel']]
        trace=[]
        for k in range(1500):
            target=targets_numpy(np.zeros(16),[.10 if k>25 else 0,0],0)
            if k>25:
                phase=((k-25)*.02/3.2-np.array([0,.5,.75,.25]))%1
                h=np.where(phase<.25,.070*np.sin(math.pi*phase/.25)**2,0.)
                dx=np.where(phase<.25,-.03*np.cos(math.pi*phase/.25),.06*(.5-(phase-.25)/.75))
                down=.172812737-h
                beta=-FRONTS*np.arccos(np.clip((down**2+dx**2-.09**2-.11**2)/(2*.09*.11),-1,1))
                theta=np.arctan2(dx,down)-np.arctan2(.11*np.sin(beta),.09+.11*np.cos(beta))
                theta0=FRONTS*math.atan2(.05,.074833147)
                beta0=-FRONTS*(math.atan2(.05,.09797959)+math.atan2(.05,.074833147))
                target[1::4]=SIDES*(theta0-theta)
                target[2::4]=SIDES*(beta0-beta)
            for _ in range(10):
                data.ctrl[:]=torque_numpy(data.qpos,data.qvel,target)
                mujoco.mj_step(model,data)
            upright=1-2*(data.qpos[4]**2+data.qpos[5]**2)
            trace.append([data.time,*data.qpos[:3],upright,*data.xpos[wheels,0],*data.xpos[wheels,2]])
            if upright<.6 or not np.isfinite(data.qpos).all():break
        last_edge=course.start+(course.count-1)*course.tread
        passed=bool(min(data.xpos[wheels,0])>last_edge+.05 and upright>.9 and abs(data.qpos[1])<.3)
        row=dict(**course.as_dict(),passed=passed,simulated_seconds=data.time,
                 final_xyz=data.qpos[:3].tolist(),final_upright=upright,
                 minimum_wheel_x=float(min(data.xpos[wheels,0])),last_riser_x=last_edge)
        rows.append(row)
        name=f'{"down" if descending else "up"}-{round(riser*1000)}'
        np.savez_compressed(out/f'{name}.npz',trace=np.array(trace))
        (out/f'{name}.xml').write_text(xml)
        print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
