"""Actual public MJCF/mesh review views; no image-model geometry generation."""
import os
os.environ.setdefault('MUJOCO_GL','egl')
from pathlib import Path
import argparse
import sys
import mujoco
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sai_agent.paths import model_root
p=argparse.ArgumentParser()
p.add_argument('--robot',default='Sai_Agent_001',choices=['Sai_Agent_001','Sai_Agent_002'])
p.add_argument('--out',type=Path)
args=p.parse_args()
out=args.out or ROOT/'artifacts'/f'{args.robot}-model-review'
out.mkdir(parents=True,exist_ok=True)
model=mujoco.MjModel.from_xml_path(str(model_root(args.robot)/'full/visual.xml'))
model.vis.global_.offwidth=960
model.vis.global_.offheight=800
data=mujoco.MjData(model)
mujoco.mj_forward(model,data)
for i in range(model.ngeom):
    name=model.geom(i).name or ""
    if name.startswith("course_") or name=="item_box":model.geom_rgba[i,3]=0
renderer=mujoco.Renderer(model,height=800,width=960)
for name,azimuth,elevation in [('front',220,-22),('rear',40,-22),('side',90,-10),('cargo-top',160,-65)]:
    camera=mujoco.MjvCamera()
    camera.lookat[:]=[.025,0,.23]
    camera.distance=.95
    camera.azimuth=azimuth;camera.elevation=elevation
    renderer.update_scene(data,camera=camera)
    Image.fromarray(renderer.render()).save(out/f'{name}.png')
renderer.close()
print(out)
