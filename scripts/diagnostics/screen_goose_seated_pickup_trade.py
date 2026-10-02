"""Screen compact Goose sit/grasp morphology without claiming an assembly.

This compares a raised hip, a wider pair of feet and the R2 lower-jaw floor
sweep on the same visual candidate. It deliberately keeps joint packaging,
dynamic control, soft pads and object contact outside its pass criteria.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

import numpy as np
import trimesh

from check_goose_exterior_reach import (pitch_matrix, pivots_from_manifest,
                                         solve_pose, solve_seated_legs,
                                         tip_datum_from_mesh)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lower_jaw_floor_sweep(appearance_dir: Path, pivots: dict, tip: np.ndarray,
                          sit_mm: float, tip_x_mm: float, tip_z_mm: float,
                          torso_deg: float, head_global_deg: float,
                          minimum_clearance_mm: float = 2.0) -> dict:
    manifest = json.loads((appearance_dir / 'manifest.json').read_text())
    mechanism = manifest['beak_ideal_r2_motion']
    if manifest['beak_pose'] != 'closed_visual_only':
        raise ValueError('The jaw sweep requires the closed lower-jaw mesh')
    length = float(mechanism['crank_length_mm'])
    q_closed = math.radians(float(mechanism['closed_crank_angle_deg']))
    if length <= 0 or length * (1 + math.sin(q_closed)) < 30:
        raise ValueError('The R2 crank cannot reach the requested 30 mm opening')
    lower, upper, head = solve_pose(
        np.array([tip_x_mm, 0.0, tip_z_mm + sit_mm]),
        torso_deg, head_global_deg, tip, pivots)
    hip, root, elbow, yoke = (pivots[name] for name in
                               ('hip', 'root', 'elbow', 'yoke'))
    root_world = hip + pitch_matrix(torso_deg) @ (root - hip)
    elbow_world = root_world + pitch_matrix(torso_deg + lower) @ (elbow - root)
    yoke_world = (elbow_world + pitch_matrix(torso_deg + lower + upper)
                  @ (yoke - elbow) - np.array([0.0, 0.0, sit_mm]))
    vertices = trimesh.load_mesh(appearance_dir / 'beak_lower.stl').vertices
    gaps = []
    for nominal_gap_mm in range(31):
        q = math.asin(math.sin(q_closed) - nominal_gap_mm / length)
        shift = np.array([length * (math.cos(q) - math.cos(q_closed)),
                          0.0, -float(nominal_gap_mm)])
        world = (pitch_matrix(head_global_deg)
                 @ (vertices + shift - yoke).T).T + yoke_world
        gaps.append({'nominal_pad_opening_mm': nominal_gap_mm,
                     'orange_lower_shell_floor_clearance_mm':
                         round(float(world[:, 2].min()), 3)})
    contiguous_safe = -1
    for row in gaps:
        if row['orange_lower_shell_floor_clearance_mm'] < minimum_clearance_mm:
            break
        contiguous_safe = row['nominal_pad_opening_mm']
    return {
        'sit_drop_mm': sit_mm,
        'tip_visual_target_xz_mm': [tip_x_mm, tip_z_mm],
        'torso_pitch_down_deg': torso_deg,
        'head_global_pitch_down_deg': head_global_deg,
        'relative_pitch_deg': {'lower_neck': round(lower, 3),
                               'upper_neck': round(upper, 3),
                               'head': round(head, 3)},
        'required_orange_shell_floor_clearance_mm': minimum_clearance_mm,
        'largest_contiguous_nominal_opening_with_clearance_mm': contiguous_safe,
        'selected_opening_clearance_mm': {
            str(row['nominal_pad_opening_mm']):
                row['orange_lower_shell_floor_clearance_mm']
            for row in gaps if row['nominal_pad_opening_mm'] in (0, 5, 10, 15, 20, 25, 30)
        },
        'samples': gaps,
    }


def seated_hip_rows(appearance_dir: Path, pivots: dict,
                    hip_rise_mm: tuple[float, ...], sit_drops_mm: tuple[float, ...],
                    torso_deg: float) -> list[dict]:
    knee_mesh = trimesh.load_mesh(appearance_dir / 'knee_1.stl')
    knee_shell_below_axis_mm = float(pivots['knee'][2] - knee_mesh.bounds[0, 2])
    hip_mesh = trimesh.load_mesh(appearance_dir / 'hip_1.stl')
    wing_seam = trimesh.load_mesh(appearance_dir / 'wing_door_seam_1.stl')
    hip_to_wing_vertical_gap = float(wing_seam.bounds[0, 2]
                                       - hip_mesh.bounds[1, 2])
    body_vertices = trimesh.load_mesh(appearance_dir / 'body.stl').vertices
    rows = []
    for rise in hip_rise_mm:
        layout = deepcopy(pivots)
        layout['hip'] = pivots['hip'].copy()
        layout['hip'][2] += rise
        thigh_length = float(np.linalg.norm(layout['knee'] - layout['hip']))
        cases = []
        for drop in sit_drops_mm:
            try:
                angles, knee_xz = solve_seated_legs(layout, drop, torso_deg)
            except ValueError as exc:
                cases.append({'sit_drop_mm': drop, 'planar_leg_ik_reached': False,
                              'reason': str(exc)})
                continue
            body_world = ((pitch_matrix(torso_deg)
                           @ (body_vertices - layout['hip']).T).T
                          + layout['hip'] - np.array([0.0, 0.0, drop]))
            knee_low = float(knee_xz[1] - knee_shell_below_axis_mm)
            cases.append({
                'sit_drop_mm': drop,
                'planar_leg_ik_reached': True,
                'hip_knee_ankle_relative_pitch_deg': np.round(angles, 2).tolist(),
                'sampled_knee_cover_floor_clearance_mm': round(knee_low, 2),
                'sampled_body_floor_clearance_mm':
                    round(float(body_world[:, 2].min()), 2),
                'five_mm_knee_and_ten_mm_body_floor_gate':
                    bool(knee_low >= 5 and body_world[:, 2].min() >= 10),
            })
        rows.append({
            'hip_axis_rise_mm': rise,
            'trial_thigh_axis_length_mm': round(thigh_length, 2),
            'nominal_hip_hub_to_wing_seam_vertical_gap_mm':
                round(hip_to_wing_vertical_gap - rise, 2),
            'seated_cases': cases,
        })
    return rows


def stance_rows(appearance_dir: Path, spread_mm: tuple[float, ...]) -> list[dict]:
    foot = trimesh.load_mesh(appearance_dir / 'foot_sole_1.stl').vertices
    floor_z = float(foot[:, 2].min())
    patch = foot[foot[:, 2] <= floor_z + 1]
    inner = float(patch[:, 1].min())
    outer = float(patch[:, 1].max())
    return [{
        'feet_each_side_outward_mm': shift,
        'two_foot_outer_lateral_support_half_width_mm': round(outer + shift, 2),
        'necessary_com_shift_to_one_foot_inner_edge_mm': round(inner + shift, 2),
    } for shift in spread_mm]


def hip_lateral_rows(appearance_dir: Path, pivots: dict,
                     outward_mm: tuple[float, ...], sit_drops_mm: tuple[float, ...]) -> list[dict]:
    """Separate hip relocation from foot spreading in the existing 3-D shells."""
    hip = trimesh.load_mesh(appearance_dir / 'hip_1.stl').bounds
    ankle = trimesh.load_mesh(appearance_dir / 'ankle_1.stl').bounds
    door = trimesh.load_mesh(appearance_dir / 'wing_service_door_1.stl').bounds
    hip_y = float((hip[0, 1] + hip[1, 1]) / 2)
    ankle_y = float((ankle[0, 1] + ankle[1, 1]) / 2)
    return [{
        'hips_each_side_outward_mm': shift,
        'feet_shift_mm': 0,
        'two_foot_support_width_change_mm': 0,
        'symmetric_hip_motor_pair_lateral_com_shift_mm': 0,
        'hub_outboard_of_existing_wing_door_mm': round(float(hip[1, 1] + shift - door[1, 1]), 2),
        'hip_to_fixed_ankle_lateral_offset_mm': round(hip_y + shift - ankle_y, 2),
        'straight_hip_ankle_line_angles_deg': [
            {'sit_drop_mm': drop,
             'lateral_angle_deg': round(math.degrees(math.atan2(
                 abs(hip_y + shift - ankle_y),
                 math.hypot(float(pivots['hip'][0] - pivots['ankle'][0]),
                            float(pivots['hip'][2] - drop - pivots['ankle'][2])))), 2)}
            for drop in sit_drops_mm
        ],
    } for shift in outward_mm]


def longer_leg_rows(appearance_dir: Path, pivots: dict,
                    extension_mm: tuple[float, ...],
                    sit_drops_mm: tuple[float, ...]) -> list[dict]:
    """Keep the torso and ankles fixed while extending both ideal leg links."""
    hip = pivots['hip'][[0, 2]]
    knee = pivots['knee'][[0, 2]]
    ankle = pivots['ankle'][[0, 2]]
    thigh = float(np.linalg.norm(knee - hip))
    shin = float(np.linalg.norm(ankle - knee))
    knee_mesh = trimesh.load_mesh(appearance_dir / 'knee_1.stl')
    cover_below_axis = float(pivots['knee'][2] - knee_mesh.bounds[0, 2])
    rows = []
    for extension in extension_mm:
        cases = []
        for drop in sit_drops_mm:
            trial_hip = hip - np.array([0.0, drop])
            span = ankle - trial_hip
            distance = float(np.linalg.norm(span))
            upper, lower = thigh + extension, shin + extension
            if not abs(upper - lower) <= distance <= upper + lower:
                cases.append({'sit_drop_mm': drop, 'planar_leg_ik_reached': False})
                continue
            along = (upper**2 - lower**2 + distance**2) / (2 * distance)
            normal = np.array([-span[1], span[0]]) / distance
            midpoint = trial_hip + along * span / distance
            offset = math.sqrt(max(0.0, upper**2 - along**2)) * normal
            trial_knee = min((midpoint + offset, midpoint - offset),
                             key=lambda point: point[0])
            cases.append({
                'sit_drop_mm': drop,
                'planar_leg_ik_reached': True,
                'posterior_knee_xz_mm': np.round(trial_knee, 2).tolist(),
                'original_knee_cover_floor_clearance_proxy_mm':
                    round(float(trial_knee[1] - cover_below_axis), 2),
            })
        rows.append({'each_link_extension_mm': extension,
                     'trial_thigh_axis_length_mm': round(thigh + extension, 2),
                     'trial_shin_axis_length_mm': round(shin + extension, 2),
                     'body_and_ankle_standing_height_held_fixed': True,
                     'seated_cases': cases})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--mass-evidence', type=Path,
                        help='Optional same-manifest conditional mass screen for hip-motor-only COM sensitivity.')
    args = parser.parse_args()
    appearance = args.appearance_dir
    manifest_path = appearance / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if not manifest.get('compact_body_study'):
        parser.error('This comparison requires a compact-body exterior study')
    pivots = pivots_from_manifest(appearance)
    tip = tip_datum_from_mesh(appearance)
    result = {
        'status': 'visual_morphology_trade_only_not_joint_or_grasp_release',
        'appearance_manifest_sha256': digest(manifest_path),
        'source_script_sha256': digest(Path(__file__)),
        'baseline_hip_axis_xyz_mm': pivots['hip'].tolist(),
        'hip_rise_screen': seated_hip_rows(appearance, pivots,
                                          (0, 5, 10, 15, 25), (90, 120, 130, 140), 20),
        'feet_spread_screen': stance_rows(appearance, (0, 6, 12)),
        'hips_outward_feet_fixed_screen': hip_lateral_rows(
            appearance, pivots, (0, 3, 6, 12), (0, 90, 130)),
        'longer_links_fixed_body_and_feet_screen': longer_leg_rows(
            appearance, pivots, (0, 5, 10, 15), (0, 90, 120, 130, 140)),
        'jaw_floor_screen': [
            lower_jaw_floor_sweep(appearance, pivots, tip, *case)
            for case in (((90, 280, 15, 20, 60),
                          (90, 240, 15, 20, 70),
                          (140, 340, 15, 20, 40),
                          (110, 320, 25, 20, 50))
                         if manifest.get('r2_head_wrap_study') else
                         ((90, 280, 15, 20, 60),
                          (90, 240, 15, 20, 70),
                          (140, 340, 15, 20, 40)))
        ],
        'limitations': [
            'Hip rise moves only an analytical pivot and existing hip hub envelope; no new thigh, motor bracket, wiring, joint axis or wing hinge is designed.',
            'The seated leg IK is planar and the knee ground gate checks only the current visual cover; full leg self-collision and mechanical stops are absent.',
            'Moving the hip sideways alone does not enlarge the foot support polygon; spreading both feet enlarges two-foot support but increases single-foot COM transfer.',
            'The hip-to-ankle lateral line angle is only a gross 3-D datum, not a solved hip-roll trajectory or motor torque requirement.',
            'Longer-link rows keep body and ankle height fixed; the original knee-cover radius is only a floor proxy and longer fairings, motors, joint limits and mass have not been built.',
            'The R2 jaw sweep uses only the orange closed lower-shell mesh with ideal linkage motion; soft pads, compliance, objects and ground contact force are absent.',
            'No model here demonstrates grasping, rising with an object, gait, continuous torque, thermal load or full-scale manufacturing.',
        ],
    }
    if args.mass_evidence:
        mass = json.loads(args.mass_evidence.read_text())
        if mass['source_manifest_sha256'] != result['appearance_manifest_sha256']:
            raise ValueError('Mass screen belongs to a different appearance manifest')
        total_kg = mass['cases_by_assumed_uniform_wall_mm']['1.6']['standing']['mass_kg']
        six_hip_motor_mass_kg = 6 * 0.082
        result['conditional_hip_motor_only_com_height_change'] = {
            'source_mass_evidence_sha256': digest(args.mass_evidence),
            'assumed_total_mass_kg': total_kg,
            'six_hip_motor_mass_kg': six_hip_motor_mass_kg,
            'rows': [
                {'hip_motor_rise_mm': rise,
                 'com_height_change_mm': round(six_hip_motor_mass_kg * rise / total_kg, 3)}
                for rise in (5, 10, 15, 25)
            ],
            'limitation': 'Only six assumed hip motors move; housing, longer links, brackets and body redistribution are excluded.',
        }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'hip_wing_gaps_mm': {str(row['hip_axis_rise_mm']):
                             row['nominal_hip_hub_to_wing_seam_vertical_gap_mm']
                             for row in result['hip_rise_screen']},
        'jaw_safe_opening_mm': [row['largest_contiguous_nominal_opening_with_clearance_mm']
                                for row in result['jaw_floor_screen']],
    }))


if __name__ == '__main__':
    main()
