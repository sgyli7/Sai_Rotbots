"""Render review images from actual Goose MJCF/CAD assets, not concept art."""
from __future__ import annotations
import os
os.environ.setdefault('MUJOCO_GL','egl')
import argparse,hashlib,json
from pathlib import Path
import mujoco
import numpy as np
from PIL import Image
from sai_agent.paths import resource_root


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--ground-pose',action='store_true');a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    r=resource_root()/'robots/Goose_V0.1';p=r/'models/full/robot.xml';m=mujoco.MjModel.from_xml_path(str(p))
    m.vis.global_.offwidth=960;m.vis.global_.offheight=960
    d=mujoco.MjData(m);mujoco.mj_resetDataKeyframe(m,d,0)
    if a.ground_pose:
        q=json.loads((r/'evidence/ground_reach_check.json').read_text())
        if not q['pass'] or q['model_sha256']!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('Passing pose/model required')
        d.qpos[:]=q['qpos']
    mujoco.mj_forward(m,d)
    renderer=mujoco.Renderer(m,height=960,width=960)
    target=[.14,0,.37] if not a.ground_pose else [.16,0,.25]
    for name,az,elevation in [('three_quarter',45,-11),('front',0,-8),('side',90,-5),('rear',180,-8)]:
        cam=mujoco.MjvCamera();cam.lookat[:]=target;cam.distance=1.25 if not a.ground_pose else .95
        cam.azimuth=az;cam.elevation=elevation
        renderer.update_scene(d,camera=cam)
        Image.fromarray(renderer.render()).save(a.output/(name+'.png'))
    renderer.close()
    (a.output/'render_manifest.json').write_text(json.dumps({'source':'MJCF with generated CAD meshes',
        'concept_art':False,'model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'pose':'ground_kinematic' if a.ground_pose else 'home'},indent=2)+'\n')
    print(str(a.output))

if __name__=='__main__':main()
