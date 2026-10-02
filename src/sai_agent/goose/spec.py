"""SI design data and motor placement shared by CAD and physics exporters."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from sai_agent.paths import resource_root


def load_spec(path: Path | None = None) -> dict:
    path = path or resource_root() / 'robots/Goose_V0.1/configs/robot_spec.json'
    spec = json.loads(path.read_text())
    names = [j['name'] for j in spec['joints']]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate joint names')
    seen = {'torso'}
    buses = set()
    for joint in spec['joints']:
        if joint['parent'] not in seen:
            raise ValueError(f"Parent order: {joint['name']}")
        key = joint['bus'], joint['motor_id']
        if key in buses:
            raise ValueError(f'Duplicate motor address {key}')
        if not joint['range_rad'][0] <= joint['home_rad'] <= joint['range_rad'][1]:
            raise ValueError(f"Home outside limits: {joint['name']}")
        buses.add(key)
        seen.add(joint['name'])
    return spec


def motor_rotation(joint: dict) -> np.ndarray:
    """Vendor front faces +Y, top is +Z; joint datum is mid body depth.

    Vendor front-view u points -X in this local frame. Horn and static mount
    geometry remain in this frame before the desired shaft rotation.
    """
    axis = np.asarray(joint['axis'], dtype=float)
    axis /= np.linalg.norm(axis)
    source = np.array([0., 1., 0.])
    cross = np.cross(source, axis)
    sine = np.linalg.norm(cross)
    cosine = float(source @ axis)
    if sine < 1e-9:
        rotation = np.eye(3) if cosine > 0 else Rotation.from_rotvec([0, 0, np.pi]).as_matrix()
    else:
        rotation = Rotation.from_rotvec(cross / sine * np.arctan2(sine, cosine)).as_matrix()
    twist = np.pi / 2 if abs(axis[2]) > .9 else 0.
    if joint.get('mount_orientation') == 'inverted':
        twist += np.pi
    return Rotation.from_rotvec(axis * twist).as_matrix() @ rotation


def motor_envelope(joint: dict, spec: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    servo = spec['servos'][joint['servo']]
    width, height, depth = servo['body_whd_m']
    rotation = motor_rotation(joint)
    center = np.asarray(joint['position_m']) + rotation @ np.array([
        0., 0., servo['shaft_from_top_m'] - height / 2])
    return center, np.array([width, depth, height]), rotation


def quaternion_wxyz(rotation: np.ndarray) -> np.ndarray:
    x, y, z, w = Rotation.from_matrix(rotation).as_quat()
    return np.array([w, x, y, z])


def home_frames(spec: dict, root_position: np.ndarray | None = None) -> dict:
    frames = {'torso': (np.eye(3), np.asarray(root_position if root_position is not None
                                            else spec['root_home_position_m'], dtype=float))}
    for j in spec['joints']:
        r, p = frames[j['parent']]
        frames[j['name']] = (r @ Rotation.from_rotvec(np.asarray(j['axis'])*j['home_rad']).as_matrix(),
                             p + r @ np.asarray(j['position_m']))
    return frames
