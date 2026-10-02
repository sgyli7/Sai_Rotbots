"""Pose the B/R2 exterior study for a visual ground-reach screen.

This uses the appearance meshes and provisional pivots. It checks a sampled
shell gap, not joint packaging, actuator range, stability, or a grasp task.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault('MUJOCO_GL', 'egl')

import mujoco
import numpy as np
from PIL import Image
from scipy.optimize import least_squares
import trimesh


HIP = np.array([-10.0, 0.0, 286.0])
ROOT = np.array([59.0, 0.0, 477.0])
ELBOW = np.array([0.0, 0.0, 632.0])
YOKE = np.array([86.0, 0.0, 744.0])
BODY_CENTER = np.array([-10.0, 0.0, 350.0])
KNEE = np.array([-65.0, 0.0, 157.0])
ANKLE = np.array([0.0, 0.0, 51.0])
BODY_FILLET_RADIUS = 92.0
BODY_HALF_SIZE = np.array([175.0, 102.5, 115.0])


def pivots_from_manifest(appearance_dir):
    """Use the actual appearance profile rather than stale tall-study axes."""
    manifest = json.loads((Path(appearance_dir) / 'manifest.json').read_text())
    profile = manifest.get('vertical_profile_mm')
    pivots = {'hip': HIP.copy(), 'knee': KNEE.copy(), 'ankle': ANKLE.copy(),
              'root': ROOT.copy(),
              'elbow': ELBOW.copy(), 'yoke': YOKE.copy(),
              'body_center': BODY_CENTER.copy()}
    if profile:
        for name in ('hip', 'knee', 'ankle'):
            pivots[name][2] = (pivots[name][2] * profile['leg_z_scale']
                               + profile.get('leg_z_offset', 0.0))
        for name in ('root', 'elbow'):
            pivots[name][2] = (pivots[name][2] * profile['neck_z_scale']
                               + profile['neck_z_offset'])
        pivots['yoke'][2] += profile['head_z_shift']
        pivots['body_center'][2] += profile['body_z_shift']
    for name in ('root', 'elbow', 'yoke'):
        pivots[name][2] -= manifest.get('neck_assembly_drop_mm', 0.0)
    pivots['yoke'][0] -= manifest.get('head_assembly_back_mm', 0.0)
    pivots['yoke'] += np.asarray(manifest.get('rest_yoke_delta_mm', [0.0, 0.0, 0.0]),
                                 dtype=float)
    pivots['knee'][0] += manifest.get('knee_forward_shift_mm', 0.0)
    return pivots


def pitch_matrix(degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def tip_datum_from_mesh(appearance_dir):
    """Locate the visible upper-bill tip for the specific appearance candidate."""
    vertices = trimesh.load_mesh(Path(appearance_dir) / 'beak_upper.stl').vertices
    foremost_x = float(vertices[:, 0].max())
    tip_band = vertices[vertices[:, 0] >= foremost_x - 2.0]
    return np.array([foremost_x, 0.0, float(tip_band[:, 2].mean())])


def solve_pose(target, torso_deg, head_global_deg, tip_datum, pivots=None):
    pivots = pivots or {'hip': HIP, 'root': ROOT, 'elbow': ELBOW, 'yoke': YOKE}
    hip, root, elbow, yoke = (pivots[name] for name in ('hip', 'root', 'elbow', 'yoke'))
    root_world = hip + pitch_matrix(torso_deg) @ (root - hip)

    def residual(pair):
        lower, upper = pair
        tip = (root_world + pitch_matrix(torso_deg + lower) @ (elbow - root)
               + pitch_matrix(torso_deg + lower + upper) @ (yoke - elbow)
               + pitch_matrix(head_global_deg) @ (tip_datum - yoke))
        return (tip - target)[[0, 2]]

    solution = least_squares(residual, [45.0, 40.0],
                             bounds=([-30.0, -140.0], [70.0, 140.0]))
    lower, upper = solution.x
    head_relative = head_global_deg - torso_deg - lower - upper
    if np.linalg.norm(solution.fun) > 0.1:
        raise ValueError('Target is not reached by this provisional pose search')
    if abs(head_relative) > 160:
        raise ValueError('The provisional head-relative pitch exceeds the screen limit')
    return float(lower), float(upper), float(head_relative)


def group_for(name):
    if name == 'body' or name.startswith(('body_', 'wing_', 'neck_root')):
        return 'torso'
    if name.startswith(('neck_lower', 'neck_elbow')):
        return 'lower'
    if name.startswith('neck_upper'):
        return 'upper'
    if name == 'head' or name.startswith(('head_', 'camera_', 'beak_')):
        return 'head'
    return None


def vector_string(values):
    return ' '.join(f'{value:.9f}' for value in values)


def solve_seated_legs(pivots, sit_drop_mm, torso_deg):
    """Posterior-knee planar IK with the original ankles fixed on the floor."""
    hip, knee, ankle = (pivots[name][[0, 2]] for name in ('hip', 'knee', 'ankle'))
    target_hip = hip - np.array([0.0, sit_drop_mm])
    thigh_length = float(np.linalg.norm(knee - hip))
    shin_length = float(np.linalg.norm(ankle - knee))
    delta = ankle - target_hip
    reach = float(np.linalg.norm(delta))
    if not abs(thigh_length - shin_length) <= reach <= thigh_length + shin_length:
        raise ValueError('Sit height is beyond the planar leg reach')
    direction = math.atan2(delta[1], delta[0])
    spread = math.acos(np.clip((reach**2 + thigh_length**2 - shin_length**2)
                               / (2 * reach * thigh_length), -1.0, 1.0))
    candidates = []
    for sign in (-1, 1):
        thigh_angle = direction + sign * spread
        target_knee = target_hip + thigh_length * np.array([math.cos(thigh_angle),
                                                             math.sin(thigh_angle)])
        shin_angle = math.atan2(*(ankle - target_knee)[::-1])
        original_thigh_angle = math.atan2(*(knee - hip)[::-1])
        original_shin_angle = math.atan2(*(ankle - knee)[::-1])
        hip_pitch = math.degrees(original_thigh_angle - thigh_angle) - torso_deg
        knee_pitch = math.degrees(original_shin_angle - shin_angle) - torso_deg - hip_pitch
        ankle_pitch = -torso_deg - hip_pitch - knee_pitch
        candidates.append((target_knee, (hip_pitch, knee_pitch, ankle_pitch)))
    posterior_knee, angles = min(candidates, key=lambda item: item[0][0])
    return angles, posterior_knee


def make_posed_xml(source, destination, torso_deg, lower_deg, upper_deg, head_deg,
                   pivots, sit_drop_mm=0.0, seated_leg_angles=None):
    tree = ET.parse(source)
    root = tree.getroot()
    for asset in root.findall('./asset/mesh'):
        asset.set('file', str((source.parent / asset.get('file')).resolve()))
    world = root.find('worldbody')
    hip, root_p, elbow, yoke = (pivots[name] for name in ('hip', 'root', 'elbow', 'yoke'))
    torso = ET.SubElement(world, 'body', name='pose_torso',
                          pos=vector_string((hip - np.array([0.0, 0.0, sit_drop_mm])) / 1000),
                          euler=vector_string([0, math.radians(torso_deg), 0]))
    lower = ET.SubElement(torso, 'body', name='pose_neck_lower',
                          pos=vector_string((root_p - hip) / 1000),
                          euler=vector_string([0, math.radians(lower_deg), 0]))
    upper = ET.SubElement(lower, 'body', name='pose_neck_upper',
                          pos=vector_string((elbow - root_p) / 1000),
                          euler=vector_string([0, math.radians(upper_deg), 0]))
    head = ET.SubElement(upper, 'body', name='pose_head',
                         pos=vector_string((yoke - elbow) / 1000),
                         euler=vector_string([0, math.radians(head_deg), 0]))
    groups = {'torso': (torso, hip), 'lower': (lower, root_p),
              'upper': (upper, elbow), 'head': (head, yoke)}
    leg_groups = {}
    if seated_leg_angles is not None:
        hip_pitch, knee_pitch, ankle_pitch = seated_leg_angles
        for side in (-1, 1):
            hip_side = pivots['hip'] + np.array([0.0, side * 88.0, 0.0])
            knee_side = pivots['knee'] + np.array([0.0, side * 88.0, 0.0])
            ankle_side = pivots['ankle'] + np.array([0.0, side * 88.0, 0.0])
            thigh = ET.SubElement(torso, 'body', name=f'pose_thigh_{side}',
                                  pos=vector_string((hip_side - hip) / 1000),
                                  euler=vector_string([0, math.radians(hip_pitch), 0]))
            shin = ET.SubElement(thigh, 'body', name=f'pose_shin_{side}',
                                 pos=vector_string((knee_side - hip_side) / 1000),
                                 euler=vector_string([0, math.radians(knee_pitch), 0]))
            foot = ET.SubElement(shin, 'body', name=f'pose_foot_{side}',
                                 pos=vector_string((ankle_side - knee_side) / 1000),
                                 euler=vector_string([0, math.radians(ankle_pitch), 0]))
            leg_groups[side] = {'thigh': (thigh, hip_side),
                                'shin': (shin, knee_side), 'foot': (foot, ankle_side)}
    for geom in list(world.findall('geom')):
        name = geom.get('name') or ''
        group = group_for(name)
        if group:
            parent, pivot = groups[group]
            world.remove(geom)
            geom.set('pos', vector_string(-pivot / 1000))
            parent.append(geom)
        elif seated_leg_angles is not None and name.startswith(('hip_', 'thigh_', 'knee_',
                                                                'shin_', 'ankle_', 'foot_')):
            side = int(name.rsplit('_', 1)[-1])
            if name.startswith('hip_'):
                parent, pivot = torso, hip
            else:
                part = ('thigh' if name.startswith(('thigh_', 'knee_')) else
                        'shin' if name.startswith(('shin_', 'ankle_')) else 'foot')
                parent, pivot = leg_groups[side][part]
            world.remove(geom)
            geom.set('pos', vector_string(-pivot / 1000))
            parent.append(geom)
    tree.write(destination, encoding='unicode')


def body_signed_distance(points, body_center, half_size, radius):
    delta = np.abs(points - body_center) - (half_size - radius)
    return (np.linalg.norm(np.maximum(delta, 0), axis=1)
            + np.minimum(np.max(delta, axis=1), 0) - radius)


def ellipsoid_signed_distance_approx(points, center, radii):
    """Conservative visual-shell proximity estimate for the rear crown trial."""
    delta = points - center
    k0 = np.linalg.norm(delta / radii, axis=1)
    k1 = np.linalg.norm(delta / (radii * radii), axis=1)
    return np.where(k1 > 1e-9, k0 * (k0 - 1) / np.maximum(k1, 1e-9),
                    -float(np.min(radii)))


def mesh_vertices(source, name):
    return trimesh.load_mesh(source.parent / f'{name}.stl').vertices


def sampled_geometry(source, torso_deg, lower_deg, upper_deg, head_deg, pivots):
    manifest = json.loads((source.parent / 'manifest.json').read_text())
    if manifest.get('lofted_body_study') or manifest.get('conformal_body_door_study'):
        raise ValueError('This lofted visual body has no calibrated shell-distance model')
    scale = np.array(manifest.get('body_scale_xyz', [1.0, 1.0, 1.0]))
    body_half_size = BODY_HALF_SIZE * scale
    body_radius = BODY_FILLET_RADIUS * float(scale.min())
    crown = manifest.get('rear_body_crown_shape_visual_mm')

    def shell_distance(points):
        distance = body_signed_distance(points, pivots['body_center'],
                                        body_half_size, body_radius)
        if crown:
            distance = np.minimum(distance, ellipsoid_signed_distance_approx(
                points, np.asarray(crown['center'], dtype=float),
                np.asarray(crown['radii'], dtype=float)))
        return distance

    hip, root, elbow, yoke = (pivots[name] for name in ('hip', 'root', 'elbow', 'yoke'))
    first = root + pitch_matrix(lower_deg) @ (elbow - root)
    second = first + pitch_matrix(lower_deg + upper_deg) @ (yoke - elbow)
    lower = mesh_vertices(source, 'neck_lower')
    lower_in_torso = (pitch_matrix(lower_deg) @ (lower - root).T).T + root
    upper = mesh_vertices(source, 'neck_upper')
    upper_in_torso = ((pitch_matrix(lower_deg + upper_deg) @ (upper - elbow).T).T
                      + first)
    head = mesh_vertices(source, 'head')
    head_in_torso = ((pitch_matrix(lower_deg + upper_deg + head_deg)
                      @ (head - yoke).T).T + second)
    body = mesh_vertices(source, 'body')
    body_world = (pitch_matrix(torso_deg) @ (body - hip).T).T + hip
    yoke_world = hip + pitch_matrix(torso_deg) @ (second - hip)
    bill_min_z = {}
    for name in ['beak_upper', 'beak_lower']:
        bill = mesh_vertices(source, name)
        bill_world = (pitch_matrix(torso_deg + lower_deg + upper_deg + head_deg)
                      @ (bill - yoke).T).T + yoke_world
        bill_min_z[name] = round(float(bill_world[:, 2].min()), 2)
    return {
        'lower_fairing_to_body_sampled_min_mm': round(float(shell_distance(lower_in_torso).min()), 2),
        'upper_fairing_to_body_sampled_min_mm': round(float(shell_distance(upper_in_torso).min()), 2),
        'head_shell_to_body_sampled_min_mm': round(float(shell_distance(head_in_torso).min()), 2),
        'body_min_height_world_mm': round(float(body_world[:, 2].min()), 2),
        'beak_min_height_world_mm': bill_min_z,
    }


def render_pose(xml, output):
    model = mujoco.MjModel.from_xml_path(str(xml))
    model.vis.global_.offwidth = 1000
    model.vis.global_.offheight = 1000
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, width=1000, height=1000)
    for label, azimuth in [('side', 90), ('three_quarter', 125)]:
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [.12, 0, .32]
        camera.distance = 1.20
        camera.azimuth = azimuth
        camera.elevation = -7
        camera.orthographic = True
        renderer.update_scene(data, camera=camera)
        Image.fromarray(renderer.render()).save(output / f'{label}.png')
    renderer.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-xml', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--sit-drop-mm', type=float, default=0.0)
    parser.add_argument('--torso-deg', type=float, default=40.0)
    parser.add_argument('--head-global-deg', type=float, default=80.0)
    parser.add_argument('--target-tip-z-mm', type=float, default=20.0)
    parser.add_argument('--target-tip-x-mm', type=float, default=300.0)
    parser.add_argument('--sweep-steps', type=int, default=0,
                        help='Sample a straight joint-space stand-to-target path; 0 skips the path screen.')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if not 0 <= args.sit_drop_mm <= 140:
        raise ValueError('Sit drop is outside the preliminary leg geometry study')
    if not 0 <= args.target_tip_z_mm <= 100:
        raise ValueError('Target tip height is outside the preliminary reach study')
    if args.sweep_steps and args.sweep_steps < 2:
        raise ValueError('A joint-space sweep requires at least two samples')
    target = np.array([args.target_tip_x_mm, 0.0,
                       args.target_tip_z_mm + args.sit_drop_mm])
    torso_deg, global_head_deg = args.torso_deg, args.head_global_deg
    pivots = pivots_from_manifest(args.appearance_xml.parent)
    tip_datum = tip_datum_from_mesh(args.appearance_xml.parent)
    lower_deg, upper_deg, head_deg = solve_pose(target, torso_deg, global_head_deg,
                                                tip_datum, pivots)
    seated_leg_angles = None
    seated_knee = None
    if args.sit_drop_mm:
        seated_leg_angles, seated_knee = solve_seated_legs(pivots, args.sit_drop_mm,
                                                            torso_deg)
    posed_xml = args.output / 'posed_appearance.xml'
    make_posed_xml(args.appearance_xml, posed_xml, torso_deg, lower_deg,
                   upper_deg, head_deg, pivots, args.sit_drop_mm, seated_leg_angles)
    render_pose(posed_xml, args.output)
    sample = sampled_geometry(args.appearance_xml, torso_deg, lower_deg,
                              upper_deg, head_deg, pivots)
    sample['body_min_height_world_mm'] = round(sample['body_min_height_world_mm']
                                               - args.sit_drop_mm, 2)
    sample['beak_min_height_world_mm'] = {name: round(value - args.sit_drop_mm, 2)
                                           for name, value in sample['beak_min_height_world_mm'].items()}
    sweep = None
    if args.sweep_steps:
        samples = []
        for fraction in np.linspace(0.0, 1.0, args.sweep_steps):
            geometry = sampled_geometry(args.appearance_xml, torso_deg * fraction,
                                        lower_deg * fraction, upper_deg * fraction,
                                        head_deg * fraction, pivots)
            geometry['body_min_height_world_mm'] = round(
                geometry['body_min_height_world_mm'] - args.sit_drop_mm * fraction, 2)
            geometry['beak_min_height_world_mm'] = {
                name: round(value - args.sit_drop_mm * fraction, 2)
                for name, value in geometry['beak_min_height_world_mm'].items()}
            samples.append({'fraction': round(float(fraction), 4), **geometry})
        checks = {
            'lower_fairing_to_body_sampled_min_mm': 5.0,
            'upper_fairing_to_body_sampled_min_mm': 5.0,
            'head_shell_to_body_sampled_min_mm': 5.0,
            'body_min_height_world_mm': 10.0,
        }
        minima = {key: min(row[key] for row in samples) for key in checks}
        minima['beak_min_height_world_mm'] = {
            name: min(row['beak_min_height_world_mm'][name] for row in samples)
            for name in ('beak_upper', 'beak_lower')}
        sweep = {
            'method': 'Linear interpolation of torso, neck, and head joint angles with linear torso descent; no feedback or leg collision.',
            'sample_count': args.sweep_steps,
            'sampled_minima': minima,
            'necessary_clearance_pass': (
                all(minima[key] >= limit for key, limit in checks.items())
                and bool(min(minima['beak_min_height_world_mm'].values()) >= 2.0)),
            'samples': samples,
        }
    result = {
        'status': 'appearance_only_seated_ground_reach_candidate_unverified' if args.sit_drop_mm else 'appearance_only_ground_reach_candidate_unverified',
        'source_appearance_xml_sha256': hashlib.sha256(args.appearance_xml.read_bytes()).hexdigest(),
        'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'target_bill_tip_visual_datum_mm': [args.target_tip_x_mm, 0.0,
                                             args.target_tip_z_mm],
        'sit_drop_mm': args.sit_drop_mm,
        'seated_leg_pitch_deg': (dict(zip(('hip', 'knee', 'ankle'),
                                       np.round(seated_leg_angles, 3)))
                                 if seated_leg_angles is not None else None),
        'seated_knee_xz_mm': (np.round(seated_knee, 3).tolist()
                             if seated_knee is not None else None),
        'source_bill_tip_visual_datum_mm': np.round(tip_datum, 3).tolist(),
        'visual_pivots_mm': {name: np.round(pivots[key], 3).tolist()
                             for name, key in [('hip', 'hip'), ('neck_root', 'root'),
                                               ('neck_elbow', 'elbow'), ('head_yoke', 'yoke')]},
        'pose_pitch_down_deg': {'torso': torso_deg, 'neck_lower_relative': round(lower_deg, 3),
                                'neck_upper_relative': round(upper_deg, 3),
                                'head_relative': round(head_deg, 3),
                                'head_global': global_head_deg},
        'sampled_geometry': sample,
        'sampled_stand_to_target_sweep': sweep,
        'limitations': [
            'No actuator range, mass, torque, continuous heat, foot stability or gait verification.',
            'Sampled shell distance uses mesh vertices and rounded-box/optional ellipsoid body approximations, not continuous collision or tolerances.',
            'Joint-space sweep, when present, samples one straight path; it omits leg links, cable routing and controlled motion.',
            ('Legs use planar posterior-knee IK with flat feet; hip roll/yaw and lateral balance remain unverified.'
             if args.sit_drop_mm else
             'Legs are held in the neutral visual pose while the torso pitches around the hip pivot.'),
            'No camera FOV, object contact, cable sweep, fasteners, print splits or actual motor installation.',
            'The user-selected pointed exterior still has not passed appearance review.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pose_pitch_down_deg': result['pose_pitch_down_deg'],
                      'sampled_geometry': sample}, ensure_ascii=False))


if __name__ == '__main__':
    main()
