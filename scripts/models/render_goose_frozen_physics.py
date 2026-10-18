"""Quick actual MuJoCo contacts and per-body COM, no retouching."""
from pathlib import Path
import argparse,json,importlib.util
import mujoco,numpy as np
from PIL import Image,ImageDraw


def main(a):
 p=a.package.resolve();spec=importlib.util.spec_from_file_location('preview_runtime',p/'runtime_adapter.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);env=module.FrozenPhysics(p);env.reset();m,d=env.model,env.data;m.vis.global_.offwidth=800;m.vis.global_.offheight=800
 m.vis.headlight.ambient[:]=[.35,.35,.35];m.vis.headlight.diffuse[:]=[.65,.65,.65];m.vis.headlight.specular[:]=[0,0,0]
 renderer=mujoco.Renderer(m,height=800,width=800,max_geom=5000);board=Image.new('RGB',(2400,850),(245,245,245));draw=ImageDraw.Draw(board);camera=mujoco.MjvCamera();camera.lookat[:]=[0,0,.33];camera.distance=1.15;camera.elevation=-12
 for i,(label,azimuth)in enumerate([('front',0.),('right',-90.),('oblique',-45.)]):
  camera.azimuth=azimuth;renderer.update_scene(d,camera)
  for g in renderer.scene.geoms[:renderer.scene.ngeom]:g.specular=0;g.shininess=0;g.reflectance=0
  board.paste(Image.fromarray(renderer.render()),(800*i,35));draw.text((800*i+18,10),label+' | actual collision hulls',fill=(0,0,0))
 draw.text((20,825),'Compiled runtime geometry. Exact per-body COM is in physical_contract.json; this image is not a manufacturing or TangPa appearance claim.',fill=(0,0,0));a.output.parent.mkdir(parents=True,exist_ok=True);board.save(a.output);renderer.close();print(a.output,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
