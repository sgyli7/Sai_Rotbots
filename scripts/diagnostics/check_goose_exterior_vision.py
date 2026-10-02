"""Screen ground visibility against the appearance-only Goose exterior meshes.

The coordinates are visual-study hypotheses, not a camera mount or optical
calibration. This check cannot establish focus, image quality or autonomous
grasping performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import mujoco
import numpy as np


def first_hit(model, data, origin, target):
    start = np.asarray(origin, dtype=np.float64)
    direction = np.asarray(target, dtype=np.float64) - start
    direction /= np.linalg.norm(direction)
    geom_id = np.array([-1], dtype=np.int32)
    distance = mujoco.mj_ray(model, data, start, direction, None, True, -1, geom_id)
    name = (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(geom_id[0]))
            if geom_id[0] >= 0 else None)
    return {'first_geom': name, 'first_hit_distance_m': round(float(distance), 4)}


def rotation_y(degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def pitch_visibility(model, data, camera_origin):
    # Inverse-transform each world target into the neutral head frame. The
    # head/bill rays are exact for this rigid-body hypothesis; the torso and
    # neck are deliberately excluded, so this is not a clearance proof.
    pivot = np.array([0.086, 0.0, 0.744])
    origin = np.asarray(camera_origin)
    for geom_id in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or ''
        model.geom_group[geom_id] = (0 if name.startswith(('head', 'camera', 'beak')) else 1)
    head_only = np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8)
    rows = []
    for optical_pitch in [0, 35]:
        for target_x in [0.35, 0.40, 0.50, 0.75, 1.0]:
            valid = []
            target_world = np.array([target_x, 0.0, 0.0])
            for head_pitch in range(0, 101):
                target_head = pivot + rotation_y(-head_pitch) @ (target_world - pivot)
                ray = target_head - origin
                target_distance = float(np.linalg.norm(ray))
                ray /= target_distance
                in_camera = rotation_y(-optical_pitch) @ ray
                if in_camera[0] <= 0:
                    continue
                horizontal = math.degrees(math.atan2(in_camera[1], in_camera[0]))
                vertical = math.degrees(math.atan2(-in_camera[2], in_camera[0]))
                if abs(horizontal) > 47.5 or abs(vertical) > 35.0:
                    continue
                hit_id = np.array([-1], dtype=np.int32)
                hit_distance = mujoco.mj_ray(model, data, origin, ray,
                                             head_only, True, -1, hit_id)
                if hit_distance < 0 or hit_distance >= target_distance - 1e-4:
                    valid.append(head_pitch)
            if valid and valid != list(range(valid[0], valid[-1] + 1)):
                raise ValueError('Visible pitch samples are disjoint; do not summarize as one range')
            rows.append({
                'optical_pitch_inside_head_deg': optical_pitch,
                'target_world_m': target_world.tolist(),
                'visible_head_pitch_down_deg': [min(valid), max(valid)] if valid else None,
                'sample_step_deg': 1,
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-xml', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.appearance_xml))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    cameras = {
        'central_visual_lens': [0.236, 0.0, 0.737],
        'lateral_aperture_hypothesis': [0.225, 0.035, 0.737],
    }
    targets = [[x, y, 0.0] for x in [0.35, 0.40, 0.50, 0.75, 1.0, 1.5, 2.0]
               for y in [0.0, 0.10, 0.25]]
    rows = []
    for label, origin in cameras.items():
        for target in targets:
            rows.append({'camera': label, 'origin_m': origin, 'target_m': target,
                         **first_hit(model, data, origin, target)})
    pitch_rows = pitch_visibility(model, data, cameras['central_visual_lens'])
    result = {
        'status': 'appearance_only_visibility_screen',
        'appearance_xml_sha256': hashlib.sha256(args.appearance_xml.read_bytes()).hexdigest(),
        'candidate_camera_fov_deg': {'horizontal': 95, 'vertical': 70},
        'camera_fov_source': 'https://www.waveshare.com/product/modules/ov5693-5mp-usb-camera-a.htm',
        'assumptions': [
            'Optical centers are visual hypotheses outside the rendered lens or bezel, not mounted sensors.',
            'Neutral-pose rays target points on a flat floor; focus, exposure and calibration remain unverified.',
            'The lateral aperture is a diagnostic alternative only, not an approved extra camera.',
            'Pitch sweep rotates the head and beak rigidly around a visual yoke pivot; neck/torso collisions, motor limits and actual camera mounting are not checked.',
            'Optical pitch 0 and 35 degrees are mount hypotheses; 35 degrees comes from the superseded RC2 specification.',
        ],
        'neutral_pose_rays': rows,
        'head_pitch_visibility_screen': {
            'visual_yoke_pivot_m': [0.086, 0.0, 0.744],
            'head_pitch_down_search_deg': [0, 100],
            'rows': pitch_rows,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    summary = {}
    for label in cameras:
        chosen = [r for r in rows if r['camera'] == label and r['target_m'][1] == 0.0]
        summary[label] = [(r['target_m'][0], r['first_geom']) for r in chosen]
    summary['head_pitch_35deg_optical'] = [
        (r['target_world_m'][0], r['visible_head_pitch_down_deg'])
        for r in pitch_rows if r['optical_pitch_inside_head_deg'] == 35
    ]
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
