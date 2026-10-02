"""Render six actual recorded states of the detached manipulation trial."""
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    evidence = ROBOT/'evidence/supported_manipulation_cycle_contract_constant_pitch.json'
    report = json.loads(evidence.read_text())
    out = ROOT/'artifacts/Goose_V0.1/supported_manipulation_cycle_contract_constant_pitch'
    xml, trajectory = out/'task.xml', out/'sampled_qpos.npz'
    assert sha(xml) == report['task_xml_sha256']
    assert sha(trajectory) == report['sampled_qpos_sha256']
    for rel, expected in report['source_hashes'].items():
        assert sha(ROOT/rel) == expected, rel
    model = mujoco.MjModel.from_xml_path(str(xml))
    model.vis.global_.offwidth = model.vis.global_.offheight = 500
    model.vis.headlight.ambient[:] = [.4, .4, .4]
    for name, color in [('ground', [.82, .83, .83, 1.]),
                        ('floor_50g_object', [.18, .30, .38, 1.])]:
        geom = model.geom(name).id
        model.geom_group[geom] = 2
        model.geom_rgba[geom] = color
    data = mujoco.MjData(model)
    options = mujoco.MjvOption()
    options.geomgroup[:] = [0, 1, 1, 0, 0, 0]
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [.075, 0., .30]
    camera.distance = .92
    camera.azimuth = 110.
    camera.elevation = -12.
    frames = np.load(trajectory)
    sheet = Image.new('RGB', (1500, 1120), 'white')
    draw = ImageDraw.Draw(sheet)
    requested = [(0.1, 'START'), (7.5, 'FLOOR APPROACH'), (10., 'ACTUAL PAD HOLD'),
                 (11.7, 'PLACE'), (12.4, 'RELEASE'), (19.8, 'RETURN TO STAND')]
    identity = []
    with mujoco.Renderer(model, height=500, width=500) as renderer:
        for i, (seconds, title) in enumerate(requested):
            frame = int(np.argmin(abs(frames['time_s']-seconds)))
            time_s = float(frames['time_s'][frame])
            data.qpos[:] = frames['qpos'][frame]
            mujoco.mj_forward(model, data)
            renderer.update_scene(data, camera=camera, scene_option=options)
            x, y = i % 3*500, i//3*560
            sheet.paste(Image.fromarray(renderer.render()), (x, y+30))
            row = min(report['records'], key=lambda r:abs(r['time_s']-time_s))
            draw.text((x+12, y+10), f'{title} | actual t={time_s:.2f}s', fill='black')
            draw.text((x+12, y+538), f'Object bottom: {row["object_min_z_m"]*1000:.1f} mm', fill='black')
            identity.append(dict(title=title, time_s=time_s,
                qpos_sha256=hashlib.sha256(frames['qpos'][frame].tobytes()).hexdigest()))
    output = ROBOT/'images/supported_manipulation_cycle.png'
    sheet.save(output)
    manifest = dict(schema='goose_actual_manipulation_render_v1',
        output=str(output.relative_to(ROOT)), output_sha256=sha(output), frames=identity,
        recorded_qpos_edited=False, body_poses_edited=False, actual_physics_trial=True,
        manufacturing_appearance_pass=False, strict_control_gate_pass=False,
        ground_and_object_display_colors_changed_only=True,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [evidence, xml, trajectory, Path(__file__)]})
    (ROBOT/'evidence/supported_manipulation_render.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(output, flush=True)


if __name__ == '__main__':
    main()
