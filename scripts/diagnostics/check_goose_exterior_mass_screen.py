"""Estimate mass, center of mass and hip gravity load for the R2 exterior.

This is a conditional thin-shell mass study; real print masses and hardware
mounts must replace its assumptions before a dynamics model is released.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from check_goose_exterior_reach import (ANKLE, BODY_CENTER, ELBOW, HIP, KNEE, ROOT, YOKE,
                                         group_for, pitch_matrix, solve_pose,
                                         tip_datum_from_mesh, pivots_from_manifest)


PETG_DENSITY_KG_M3 = 1250.0
XM430_KG = 0.082
XM540_KG = 0.165
XC330_KG = 0.023
XL330_KG = 0.018
TORQUE_SCREEN_NM = 0.82
MOTOR_COVER_NAMES = {'hip', 'knee', 'ankle', 'neck_root', 'neck_elbow',
                     'head_yoke', 'beak_hinge'}


def surface_centroid(mesh):
    return np.average(mesh.triangles_center, axis=0, weights=mesh.area_faces)


def printed_parts(directory, wall_mm):
    items = []
    for path in sorted(directory.glob('*.stl')):
        name = path.stem
        if any(name == prefix or name.startswith(prefix + '_') for prefix in MOTOR_COVER_NAMES):
            continue
        mesh = trimesh.load_mesh(path)
        mass = min(mesh.area * 1e-6 * wall_mm * 1e-3 * PETG_DENSITY_KG_M3,
                   abs(mesh.volume) * 1e-9 * PETG_DENSITY_KG_M3)
        if mass <= 0:
            raise ValueError(f'Invalid print mass estimate: {path}')
        items.append((name, group_for(name) or 'legs', mass, surface_centroid(mesh)))
    return items


def motor_and_component_items(root, pivots=None, manifest=None):
    pivots = pivots or {'hip': HIP, 'root': ROOT, 'elbow': ELBOW,
                        'yoke': YOKE, 'body_center': BODY_CENTER,
                        'knee': KNEE, 'ankle': ANKLE}
    body_center = pivots['body_center']
    head_shift = pivots['yoke'][2] - YOKE[2]
    items = []
    for side in (-1, 1):
        y = side * 88.0
        for index in range(3):
            items.append((f'leg_hip_{side}_{index}', 'legs', XM430_KG,
                          pivots['hip'] + np.array([0.0, y, 0.0])))
        items.append((f'leg_knee_{side}', 'legs', XM430_KG,
                      pivots['knee'] + np.array([0.0, y, 0.0])))
        items.append((f'leg_ankle_{side}', 'legs', XM430_KG,
                      pivots['ankle'] + np.array([0.0, y, 0.0])))
    beak_mass = XC330_KG
    beak_axis = np.array([191.0, 0, 680.0 + head_shift])
    if manifest and manifest.get('r2_internal_belt_study'):
        package = manifest['beak_drive_package_hypothesis']
        if package['motor'] != 'XL330-M288-T':
            raise ValueError('Unrecognized internal-belt beak motor')
        beak_mass = XL330_KG
        beak_axis = np.array(package['motor_input_axis_visual_mm'], dtype=float)
    items += [
        ('neck_yaw_motor', 'torso', XM430_KG, pivots['root'].copy()),
        ('neck_root_pitch_motor', 'torso', XM540_KG, pivots['root'].copy()),
        ('neck_elbow_pitch_motor', 'lower', XM540_KG, pivots['elbow'].copy()),
        ('head_pitch_motor', 'upper', XM430_KG, pivots['yoke'].copy()),
        ('head_roll_motor', 'head', XC330_KG,
         np.array([140.0, 0, 730.0 + head_shift])),
        ('beak_motor', 'head', beak_mass, beak_axis),
        ('torso_frame_reserve', 'torso', 0.085, body_center.copy()),
    ]
    component_path = root / 'robots/Goose_V0.1/hardware/component_envelopes.json'
    components = json.loads(component_path.read_text())['components']
    for c in components:
        local = np.array(c['center_m']) * 1000
        items.append((c['name'], 'torso', c['mass_reserve_kg'], body_center + local))
    return items


def placed(items, pivots=None, torso_deg=0.0, lower_deg=0.0,
           upper_deg=0.0, head_deg=0.0):
    pivots = pivots or {'hip': HIP, 'root': ROOT, 'elbow': ELBOW, 'yoke': YOKE}
    hip, root, elbow, yoke = (pivots[name] for name in ('hip', 'root', 'elbow', 'yoke'))
    rot = pitch_matrix
    root_world = hip + rot(torso_deg) @ (root - hip)
    elbow_world = root_world + rot(torso_deg + lower_deg) @ (elbow - root)
    yoke_world = elbow_world + rot(torso_deg + lower_deg + upper_deg) @ (yoke - elbow)
    transforms = {'torso': (hip, hip, torso_deg),
                  'lower': (root, root_world, torso_deg + lower_deg),
                  'upper': (elbow, elbow_world, torso_deg + lower_deg + upper_deg),
                  'head': (yoke, yoke_world, torso_deg + lower_deg + upper_deg + head_deg)}
    placed_items = []
    for name, group, mass, center in items:
        if group == 'legs':
            world = center
        else:
            local_pivot, world_pivot, angle = transforms[group]
            world = world_pivot + rot(angle) @ (center - local_pivot)
        placed_items.append((name, group, mass, world))
    return placed_items


def summary(items, support, hip=HIP):
    total = sum(mass for _, _, mass, _ in items)
    com = sum(mass * center for _, _, mass, center in items) / total
    upper = [(name, group, mass, center) for name, group, mass, center in items if group != 'legs']
    upper_mass = sum(x[2] for x in upper)
    signed_hip_gravity_moment = sum(mass * 9.81 * (center[0] - hip[0]) / 1000
                                    for _, _, mass, center in upper)
    x_range = support['double_support_necessary_x_com_interval_mm']
    return {
        'mass_kg': round(total, 3),
        'upper_body_mass_kg': round(upper_mass, 3),
        'projected_com_mm': np.round(com, 2).tolist(),
        'double_support_x_margin_to_nearest_end_mm': round(min(com[0] - x_range[0],
                                                               x_range[1] - com[0]), 2),
        'signed_upper_body_gravity_moment_about_hip_Nm': round(signed_hip_gravity_moment, 3),
        'equal_share_per_hip_Nm': round(abs(signed_hip_gravity_moment) / 2, 3),
        'per_hip_XM430_screening_limit_Nm': TORQUE_SCREEN_NM,
        'per_hip_screening_pass': bool(abs(signed_hip_gravity_moment) / 2 <= TORQUE_SCREEN_NM),
        'single_foot_lateral_shift_needed_mm': support['single_foot_requires_lateral_com_shift_from_centerline_at_least_mm'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--support-evidence', type=Path, required=True)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--standing-only', action='store_true',
                        help='Do not apply the legacy visual ground-reach pose to a newer exterior.')
    args = parser.parse_args()
    support = json.loads(args.support_evidence.read_text())
    if support['status'] != 'support_geometry_only_no_static_or_walking_certification':
        raise ValueError('Unexpected support evidence status')
    manifest = json.loads((args.appearance_dir / 'manifest.json').read_text())
    pivots = pivots_from_manifest(args.appearance_dir)
    if not args.standing_only:
        target = np.array([300.0, 0.0, 20.0])
        torso_deg, global_head_deg = 40.0, 80.0
        lower, upper, head = solve_pose(target, torso_deg, global_head_deg,
                                        tip_datum_from_mesh(args.appearance_dir), pivots)
        reach_pose = {'torso': torso_deg, 'neck_lower_relative': round(lower, 3),
                      'neck_upper_relative': round(upper, 3),
                      'head_relative': round(head, 3)}
    else:
        reach_pose = None
    cases = {}
    for wall_mm in (1.2, 1.6, 2.0, 2.4):
        printed = printed_parts(args.appearance_dir, wall_mm)
        items = printed + motor_and_component_items(args.project_root, pivots, manifest)
        neutral = summary(placed(items, pivots), support, pivots['hip'])
        case = {'standing': neutral,
                'printed_proxy_mass_kg': round(sum(x[2] for x in printed), 3)}
        if reach_pose is not None:
            case['ground_reach_visual_pose'] = summary(
                placed(items, pivots, torso_deg, lower, upper, head),
                support, pivots['hip'])
        cases[str(wall_mm)] = case
    result = {
        'status': 'conditional_mass_and_gravity_screen_not_dynamic_validation',
        'source_manifest_sha256': hashlib.sha256((args.appearance_dir / 'manifest.json').read_bytes()).hexdigest(),
        'support_evidence_sha256': hashlib.sha256(args.support_evidence.read_bytes()).hexdigest(),
        'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'visual_pivots_mm': {name: np.round(value, 3).tolist()
                             for name, value in pivots.items()},
        'ground_reach_pose_deg': reach_pose,
        'beak_motor_basis': ('XL330-M288-T 18 g at the visual internal-belt input axis'
                             if manifest.get('r2_internal_belt_study') else
                             'legacy XC330 23 g beak motor trial placement'),
        'mass_basis': 'Vendor motor mass assumptions; electronics reserves from component_envelopes.json; visual print surfaces × uniform wall × 1250 kg/m3, capped at solid volume; 85g torso frame reserve.',
        'cases_by_assumed_uniform_wall_mm': cases,
        'limitations': [
            'Visual STL surfaces overlap, and no real print wall/infill/fastener/structural mass has been measured.',
            'Motor and electronics SKUs/placements are inherited as a trial, not mechanically installed in this exterior.',
            'The trial includes five leg motors per side; a possible sixth ankle axis per side and its brackets are absent from this mass estimate.',
            'Equal left/right hip moment sharing is only a screening assumption and 0.82 Nm is a vendor estimate, not continuous thermal certification.',
            'Static projected COM and hip moment omit acceleration, contact force distribution, friction, drag, and all gait control.',
            'The ground-reach pose is visual kinematics and has no verified collision-free actuator envelope.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({wall: case for wall, case in cases.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
