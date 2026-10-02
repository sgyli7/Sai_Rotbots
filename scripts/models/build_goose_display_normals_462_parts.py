"""Generate approximate display normals from the existing body design profile.

Only shading inputs and their colour configuration are written. Native CAD,
quad coordinates/topology, STL, collision and mass files remain untouched.
This cannot certify manufacturing surface quality or absence of CAD defects.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robot-root', type=Path, default=Path('robots/Goose_V0.1'))
    parser.add_argument('--scene', type=Path)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    root = args.robot_root.resolve()
    scene_path = args.scene or root / 'cad/source/torso_shell_mount_fixture/assembly_scene.json'
    config_path = args.config or root / 'configs/microduck_color_blocking_462_parts.json'
    scene = json.loads(scene_path.read_text())
    config = json.loads(config_path.read_text())
    profile_path = root / 'configs/body_bay_layout_candidate.json'
    rows = np.asarray(json.loads(profile_path.read_text())['body_profile_x_cz_ry_rz_mm'])
    profile = PchipInterpolator(rows[:, 0], rows[:, 1:], axis=0)
    derivative = profile.derivative()
    folder = root / 'source/microduck_color_blocking_462_parts'
    folder.mkdir(parents=True, exist_ok=True)
    config['display_normal_fields'] = {}
    for part in scene['parts']:
        if part['name'] not in ('torso_mounted_shell_left_fore', 'torso_mounted_shell_right_fore'):
            continue
        geometry = root / part['geometry_npz']
        if hashlib.sha256(geometry.read_bytes()).hexdigest() != part['source_sha256']:
            raise ValueError('Display normals require the exact current quad source')
        vertices = np.load(geometry)['vertices'] * 1000
        cz, ry, rz = profile(vertices[:, 0]).T
        czd, ryd, rzd = derivative(vertices[:, 0]).T
        co, si = (np.abs(vertices[:, 1]) - .12) / ry, (vertices[:, 2] - cz) / rz
        magnitude = np.hypot(co, si)
        co, si = co / magnitude, si / magnitude
        side = 1 if part['name'].endswith('left_fore') else -1
        normals = np.column_stack((-co * co * ryd / ry - si * czd / rz - si * si * rzd / rz,
                                   side * co / ry, si / rz))
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        if not np.isfinite(normals).all():
            raise ValueError('Invalid profile-derived display normals')
        # These shells include internal attachment bosses. Zero is a sentinel:
        # the renderer retains native split normals when profile alignment is
        # absent. Never project those bosses onto a smooth body envelope.
        normals[(magnitude < .95) | (magnitude > 1.005)] = 0
        path = folder / f"{part['name']}_display_normals.npz"
        np.savez_compressed(path, canonical_normals=normals)
        config['display_normal_fields'][part['name']] = {
            'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'geometry_sha256': part['source_sha256'],
            'profile_path': str(profile_path.relative_to(root)),
            'profile_sha256': hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            'basis': 'Approximate existing body-profile derivative, limited to radial envelope0.95..1.005. Attachment/cut vertices outside that envelope use native split normals. Inner-face sign and cut-rim normals retained; display only, not CAD surface proof.',
        }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    print('DISPLAY_NORMAL_FIELDS_COMPLETE', len(config['display_normal_fields']))


if __name__ == '__main__':
    main()
