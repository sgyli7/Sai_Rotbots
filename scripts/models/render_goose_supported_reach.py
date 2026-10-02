"""Render recorded free-root states; never alter their pose for presentation."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trajectory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.trajectory.read_text())
    path = ROBOT / 'models/stage_two/robot.xml'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record['model_sha256']
    model = mujoco.MjModel.from_xml_path(str(path))
    model.vis.global_.offwidth = model.vis.global_.offheight = 600
    # Groups1/2 contain visual meshes and visible motor cases; group3 is
    # collision-only. Keep motor cases visible even though they also collide.
    for i in range(model.ngeom):
        if model.geom(i).name == 'floor':
            model.geom_group[i] = 2
            model.geom_rgba[i] = [.82, .83, .83, 1]
    model.vis.headlight.ambient[:] = [.4, .4, .4]
    data = mujoco.MjData(model)
    options = mujoco.MjvOption()
    options.geomgroup[:] = [0, 1, 1, 0, 0, 0]
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [.04, 0, .29]
    camera.distance = 1.02
    camera.azimuth = 110
    camera.elevation = -8
    sheet = Image.new('RGB', (1800, 680), 'white')
    draw = ImageDraw.Draw(sheet)
    with mujoco.Renderer(model, height=600, width=600) as renderer:
        for column, (seconds, title) in enumerate(((0, 'START'), (13.5, 'LOW APPROACH'), (27.9, 'RETURN TO STAND'))):
            frame = min(record['frames'], key=lambda f: abs(f['time_s'] - seconds))
            data.qpos[:] = frame['qpos']
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=camera, scene_option=options)
            sheet.paste(Image.fromarray(renderer.render()), (column * 600, 40))
            draw.text((column * 600 + 18, 14), f"{title}  t={frame['time_s']:.2f}s", fill='black')
            draw.text((column * 600 + 18, 650), f"Grip height: {frame['grip_m'][2] * 1000:.1f} mm | actual simulated state", fill='black')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    print(args.output)


if __name__ == '__main__':
    main()
