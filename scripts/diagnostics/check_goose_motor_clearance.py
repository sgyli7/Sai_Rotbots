"""OBB intersection check independent of engine parent-collision filtering."""
from __future__ import annotations

import json
from pathlib import Path

import mujoco
import numpy as np

from sai_agent.goose.spec import load_spec, motor_envelope
from sai_agent.paths import resource_root


def overlap(a,b,clearance=0.):
    pa,sa,ra=a;pb,sb,rb=b
    axes=[*ra.T,*rb.T]
    axes += [np.cross(x,y) for x in ra.T for y in rb.T]
    depths=[]
    for axis in axes:
        length=np.linalg.norm(axis)
        if length<1e-9:continue
        n=axis/length
        extent_a=np.sum(abs(ra.T@n)*(sa/2+clearance/2))
        extent_b=np.sum(abs(rb.T@n)*(sb/2+clearance/2))
        depth=extent_a+extent_b-abs(n@(pb-pa))
        if depth<=0:return False,0.
        depths.append(depth)
    return True,min(depths)


def main():
    robot=resource_root()/'robots/Goose_V0.1';spec=load_spec()
    model=mujoco.MjModel.from_xml_path(str(robot/'models/full/robot.xml'));data=mujoco.MjData(model)
    home=model.key_qpos[0].copy();ground=np.array(json.loads((robot/'evidence/ground_reach_check.json').read_text())['qpos'])
    violations=[];checks=0
    for fraction in np.linspace(0,1,51):
        data.qpos[:]=home+(ground-home)*fraction;mujoco.mj_forward(model,data)
        boxes=[]
        for j in spec['joints']:
            p,size,r=motor_envelope(j,spec);body=model.body(j['parent']).id
            parent_r=data.xmat[body].reshape(3,3)
            boxes.append((data.xpos[body]+parent_r@p,size,parent_r@r))
        for i in range(len(boxes)):
            for k in range(i+1,len(boxes)):
                checks+=1;intersects,depth=overlap(boxes[i],boxes[k],.0005)
                if intersects:
                    violations.append({'fraction':float(fraction),'motors':[spec['joints'][i]['name'],spec['joints'][k]['name']], 'minimum_sat_overlap_m':float(depth)})
    result={'scope':'vendor body envelopes, includes adjacent bodies, 51 home-to-ground interpolation poses; no frame/cable/PCB acceptance',
            'inflation_clearance_m':.0005,'checks':checks,'violations':violations,'pass':not violations}
    (robot/'evidence/motor_clearance_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
