"""Actual public MJCF/mesh review views; no image-model geometry generation."""
import os
os.environ.setdefault('MUJOCO_GL','egl')
from pathlib import Path
import mujoco
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'artifacts/public-model-review'
out.mkdir(parents=True,exist_ok=True)
model=mujoco.MjModel.from_xml_path(str(ROOT/'models/full/visual.xml'))
model.vis.global_.offwidth=960
model.vis.global_.offheight=800
data=mujoco.MjData(model)
mujoco.mj_forward(model,data)
renderer=mujoco.Renderer(model,height=800,width=960)
for name,azimuth,elevation in [('front',40,-22),('rear',220,-22),('side',90,-10)]:
    camera=mujoco.MjvCamera()
    camera.lookat[:]=[.025,0,.23]
    camera.distance=.95
    camera.azimuth=azimuth;camera.elevation=elevation
    renderer.update_scene(data,camera=camera)
    Image.fromarray(renderer.render()).save(out/f'{name}.png')
renderer.close()
print(out)
