"""Exact source-solid checks, including parts on the same/adjacent bodies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
from build123d import Location, import_brep
from OCP.gp import gp_Trsf

from sai_agent.paths import resource_root
from sai_agent.goose.spec import load_spec


def moved(shape,r,p):
    t=gp_Trsf();t.SetValues(*map(float,np.column_stack([r,p]).ravel()))
    return shape.moved(Location(t))


def overlaps(aa,bb):
    return np.all(aa[0]<bb[1]) and np.all(bb[0]<aa[1])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--samples',type=int,default=3)
    p.add_argument('--pose',choices=('home_to_grasp','standing'),default='home_to_grasp')
    p.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/part_clearance/result.json'))
    args=p.parse_args();robot=resource_root()/'robots/Goose_V0.1';cadpath=robot/'cad/exports/cad_manifest.json'
    cad=json.loads(cadpath.read_text());modelpath=robot/'models/full/robot.xml'
    m=mujoco.MjModel.from_xml_path(str(modelpath));d=mujoco.MjData(m)
    home=m.key_qpos[0].copy();ground=np.array(json.loads((robot/'evidence/ground_reach_check.json').read_text())['qpos'])
    parts=[(v,import_brep(robot/v['files']['brep']['path'])) for v in cad['parts']]
    hits=[];tested=0;broad=0
    standing=home.copy();standing[:7]=ground[:7]
    for name in [j['name'] for j in load_spec()['joints'] if j['control_group']=='locomotion']:
        address=m.joint(name).qposadr[0];standing[address]=ground[address]
    pose_values=[standing] if args.pose=='standing' else [home+(ground-home)*f for f in np.linspace(0,1,args.samples)]
    for sample,qpos in enumerate(pose_values):
        f=float(sample/(len(pose_values)-1)) if len(pose_values)>1 else 0.
        d.qpos[:]=qpos;mujoco.mj_forward(m,d);world=[]
        for part,shape in parts:
            b=m.body(part['body']).id;shape=moved(shape,d.xmat[b].reshape(3,3),d.xpos[b]*1000)
            bbox=shape.bounding_box();world.append((part,shape,(np.array(tuple(bbox.min)),np.array(tuple(bbox.max)))))
        for i,(first,a,aa) in enumerate(world):
            for second,b,bb in world[i+1:]:
                tested+=1
                if not overlaps(aa,bb):continue
                broad+=1;common=a&b;volume=float(common.volume) if common is not None and common.solids() else 0.
                if volume>1.:
                    hit={'sample':sample,'fraction':float(f),'parts':[first['name'],second['name']],
                         'bodies':[first['body'],second['body']],'intersection_mm3':volume}
                    hits.append(hit)
                    print(json.dumps(hit),flush=True)
        print(json.dumps({'sample':sample,'hits':len(hits),'exact_checks':broad}),flush=True)
    result={'scope':'exact part versus part at '+args.pose+' pose/path; all bodies, no collision-filter exemption',
            'samples':len(pose_values),'candidate_pairs':tested,'exact_boolean_checks':broad,'hits':hits,'pass':not hits,
            'cad_manifest_sha256':hashlib.sha256(cadpath.read_bytes()).hexdigest(),
            'model_sha256':hashlib.sha256(modelpath.read_bytes()).hexdigest(),
            'tolerance_mm3':1.,'unverified':['continuous full joint workspace','fastener heads/wire bends','printing tolerances','strength']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
