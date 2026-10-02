"""Exact solid intersection against vendor case boxes along the grasp path.

Includes adjacent rigid bodies, which physics engines often exclude. This
does not infer cable clearance or anisotropic strength from a solid boolean.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
from build123d import Box, Location, Pos, import_brep
from OCP.gp import gp_Trsf

from sai_agent.goose.spec import load_spec,motor_envelope
from sai_agent.paths import resource_root


def moved(shape,r,p):
    matrix=np.column_stack([r,p]);t=gp_Trsf();t.SetValues(*map(float,matrix.ravel()))
    return shape.moved(Location(t))


def overlap(a,b):
    aa=a.bounding_box();bb=b.bounding_box()
    amin,amax,bmin,bmax=map(lambda v:list(v),(aa.min,aa.max,bb.min,bb.max))
    return all(amin[i]<bmax[i] and bmin[i]<amax[i] for i in range(3))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--samples',type=int,default=9)
    parser.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/cad_clearance/result.json'))
    args=parser.parse_args();robot=resource_root()/'robots/Goose_V0.1';spec=load_spec()
    cadpath=robot/'cad/exports/cad_manifest.json';cad=json.loads(cadpath.read_text())
    modelpath=robot/'models/full/robot.xml';m=mujoco.MjModel.from_xml_path(str(modelpath));d=mujoco.MjData(m)
    ground=np.array(json.loads((robot/'evidence/ground_reach_check.json').read_text())['qpos'])
    home=m.key_qpos[0].copy();parts=[(p,import_brep(robot/p['files']['brep']['path'])) for p in cad['parts']]
    motors=[]
    for j in spec['joints']:
        center,size,r=motor_envelope(j,spec)
        motors.append((j,moved(Box(*(size*1000)),r,center*1000)))
    hits=[];tested=0;broadphase=0
    for sample,fraction in enumerate(np.linspace(0,1,args.samples)):
        d.qpos[:]=home*(1-fraction)+ground*fraction;mujoco.mj_forward(m,d)
        world_parts=[];world_motors=[]
        for part,shape in parts:
            b=m.body(part['body']).id;world_parts.append((part,moved(shape,d.xmat[b].reshape(3,3),d.xpos[b]*1000)))
        for j,shape in motors:
            b=m.body(j['parent']).id;world_motors.append((j,moved(shape,d.xmat[b].reshape(3,3),d.xpos[b]*1000)))
        for part,shape in world_parts:
            for joint,motor in world_motors:
                tested+=1
                if not overlap(shape,motor):continue
                broadphase+=1;common=shape & motor;volume=float(common.volume) if common.solids() else 0.
                if volume>1.:hits.append({'sample':sample,'path_fraction':float(fraction),'part':part['name'],
                                         'motor':joint['name'],'intersection_mm3':volume})
        print(json.dumps({'sample':sample,'hits_so_far':len(hits),'boolean_checks':broadphase}),flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result={'scope':'exact CAD part versus case envelopes along linear home-to-side-ground-grasp joint path',
            'samples':args.samples,'candidate_pairs':tested,'exact_boolean_checks':broadphase,
            'max_accepted_intersection_mm3':1,'hits':hits,'pass':not hits,
            'cad_manifest_sha256':hashlib.sha256(cadpath.read_bytes()).hexdigest(),
            'model_sha256':hashlib.sha256(modelpath.read_bytes()).hexdigest(),
            'unverified':['all other joint combinations','part-versus-part','wire bends/connectors','strength']}
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'hits':len(hits)}))
    return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
