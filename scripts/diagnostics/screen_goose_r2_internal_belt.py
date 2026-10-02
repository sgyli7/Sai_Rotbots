"""Necessary CAD envelope checks for the compact R2 internal-belt candidate.

The visual meshes are not a printable assembly. This script tests a conservative
motor body and sampled belt envelope against an inset exterior, then checks the
moving orange bill and side carrier solids at nine ideal jaw positions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from build123d import Box

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_exterior_study import (  # noqa: E402
    bill, disk, fairing_between, moved, rounded_box,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlap(a, b) -> float:
    return round(float((a & b).volume), 5)


def outside(a, enclosure) -> float:
    return round(float((a - enclosure).volume), 5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.appearance_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if not manifest.get('r2_internal_belt_study') or manifest['beak_pose'] != 'closed_visual_only':
        parser.error('Expected a closed R2 internal-belt appearance study')
    if (manifest['head_scale'], manifest['head_assembly_back_mm']) != (1.0, 25.0):
        parser.error('This screen is tied to the compact wrapped-head visual candidate')
    if (manifest.get('integrated_camera_face_study')
            or manifest.get('recessed_camera_bezel_study')
            or manifest.get('sculpted_head_study')
            or manifest.get('helmet_head_study')
            or manifest.get('tapered_helmet_head_study')):
        parser.error('The recessed camera face requires a separate package screen')
    continuous_cheek = bool(manifest.get('continuous_head_cheek_study'))
    swept_head = bool(manifest.get('reference_head_clearance_study'))
    whole_proportions = bool(manifest.get('reference_whole_proportions_study'))
    rest_delta = np.asarray(manifest.get('rest_yoke_delta_mm', [0.0, 0.0, 0.0]),
                            dtype=float)
    visual_dx = -125 - manifest['head_assembly_back_mm'] + rest_delta[0]
    visual_dz = (150 + manifest['vertical_profile_mm']['head_z_shift']
                 - manifest['neck_assembly_drop_mm'] + rest_delta[2])

    hypothesis = manifest['beak_drive_package_hypothesis']
    a = np.asarray(hypothesis['fixed_output_A_visual_mm'], dtype=float)
    motor_axis = np.asarray(hypothesis['motor_input_axis_visual_mm'], dtype=float)
    wall = 2.7  # design screen, not a finalized PETG print wall
    wrapped = bool(manifest.get('r2_head_wrap_study'))
    pocket_length = float(manifest.get('r2_front_pocket_length_mm') or 60)
    head_center = (np.array([270 + visual_dx, 0,
                             (559 if whole_proportions else 563) + visual_dz], dtype=float)
                   if wrapped else
                   np.array([265 + visual_dx, 0, 580 + visual_dz], dtype=float))
    head_size = ((130, 92, 104) if whole_proportions else (130, 92, 116)
                 if wrapped else (120, 92, 102))
    head_inner = rounded_box(tuple(value - 2 * wall for value in head_size),
                             (35 if whole_proportions else 40 if wrapped else 32) - wall,
                             head_center)
    if wrapped and not swept_head:
        # Conservatively expand the exterior's lower-front jaw pocket inward
        # by the assumed wall thickness before assessing usable head volume.
        head_inner -= rounded_box((pocket_length + 2 * wall, 70 + 2 * wall, 95 + 2 * wall),
                                  8 + wall, (345 + visual_dx, 0, 512.5 + visual_dz))
        if not continuous_cheek:
            for side in (-1, 1):
                head_inner -= rounded_box((24 + 2 * wall, 16 + 2 * wall, 50 + 2 * wall),
                                          4 + wall, (322 + visual_dx, side * 33,
                                                     535 + visual_dz))
    motor_body = moved(Box(20, 26, 34), motor_axis + (0, 0, -7.5))
    motor_fit = outside(motor_body, head_inner)
    yoke = disk(23, 50, (211 + visual_dx, 0, 594 + visual_dz))
    camera_panel = (rounded_box((16, 65, 50), 6,
                                (326 + visual_dx, 0, 585 + visual_dz))
                    if whole_proportions else
                    rounded_box((16, 69, 60), 6,
                                (334 + visual_dx, 0, 590 + visual_dz))
                    if wrapped else
                    rounded_box((14, 69, 67), 6,
                                (334 + visual_dx, 0, 587 + visual_dz)))

    hinge_inner = None if wrapped else disk(20 - wall, 54 - 2 * wall, a)
    belt_enclosure = head_inner if wrapped else head_inner + hinge_inner
    belt_lateral_center = float(hypothesis['gross_belt_lateral_center_visual_mm'])
    # 16/32 teeth at 2 mm pitch give 2:1. Gross outer radii intentionally
    # exceed the pitch radii; another 0.5 mm is reserved for an early screen.
    belt_samples = []
    for t in np.linspace(0, 1, 33):
        center = (1 - t) * motor_axis + t * a
        center[1] = belt_lateral_center
        envelope = disk(6.5 + 5.0 * t + 0.5, 6, center)
        belt_samples.append({'fraction': round(float(t), 5),
                             'outside_inset_exterior_mm3': outside(envelope, belt_enclosure)})
    c = float(np.linalg.norm(a - motor_axis))
    r_small, r_big = 16 / math.pi, 32 / math.pi  # pitch radii, 2 mm pitch
    delta = r_big - r_small
    pitch_length = (2 * math.sqrt(c * c - delta * delta)
                    + math.pi * (r_small + r_big)
                    + 2 * delta * math.asin(delta / c))

    if swept_head:
        # The v95 head is a separate thin shell with locally carved linkage
        # keepouts. Its uncut inset core is a conservative drive-volume check;
        # the older rectangular-pocket and outboard-link tests do not describe
        # this new geometry and must not be counted as a complete package pass.
        link_centers = hypothesis['paired_four_bar_lateral_centers_visual_mm']
        motor_to_link_lateral_gap = min(abs(y) for y in link_centers) - 2 - 13
        belt_to_link_lateral_gap = min(abs(y) for y in link_centers) - 2 - (abs(belt_lateral_center) + 3)
        checks = {
            'motor_inside_nominal_head_core': motor_fit < .01,
            'motor_clear_of_neck_yoke': overlap(motor_body, yoke) < .01,
            'motor_clear_of_camera_panel': overlap(motor_body, camera_panel) < .01,
            'belt_samples_inside_nominal_head_core': max(
                sample['outside_inset_exterior_mm3'] for sample in belt_samples) < .01,
            'nominal_lateral_motor_to_link_gap_positive': motor_to_link_lateral_gap > 0,
            'nominal_lateral_belt_to_link_gap_positive': belt_to_link_lateral_gap > 0,
        }
        result = {
            'status': ('v95_nominal_drive_core_screen_pass_only' if all(checks.values())
                       else 'v95_nominal_drive_core_screen_failed'),
            'appearance_review_pass': False,
            'manufacturing_release_pass': False,
            'appearance_manifest_sha256': sha256(manifest_path),
            'source_script_sha256': sha256(Path(__file__)),
            'source_builder_sha256': manifest['source_sha256'],
            'vendor_source': 'https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/',
            'motor_body_whd_vendor_mm': [20, 34, 26],
            'motor_axis_visual_mm': motor_axis.tolist(),
            'gross_belt_lateral_center_mm': belt_lateral_center,
            'paired_four_bar_lateral_centers_mm': link_centers,
            'checks': checks,
            'motor_outside_nominal_inset_head_core_mm3': motor_fit,
            'motor_to_yoke_overlap_mm3': overlap(motor_body, yoke),
            'motor_to_camera_panel_overlap_mm3': overlap(motor_body, camera_panel),
            'minimum_nominal_motor_to_link_lateral_gap_mm': motor_to_link_lateral_gap,
            'minimum_nominal_belt_to_link_lateral_gap_mm': belt_to_link_lateral_gap,
            'gross_belt_pitch_length_at_nominal_centres_mm': round(pitch_length, 4),
            'belt_sample_count': len(belt_samples),
            'maximum_sampled_belt_outside_nominal_inset_head_core_mm3': max(
                sample['outside_inset_exterior_mm3'] for sample in belt_samples),
            'belt_samples': belt_samples,
            'limitations': [
                'The visual motor orientation, shaft location and 16T/32T pulley sizes are layout hypotheses, not vendor CAD installation.',
                'A straight centerline with 33 circular belt sections omits tooth geometry, tensioner, belt dynamics and true continuous swept volume.',
                'The lateral gaps use nominal motor and 4 mm link widths; shafts, bearings, brackets, wiring and assembly tolerance remain unallocated.',
                'The v95 visual head shell and moving-link cuts are checked separately; this core test is not a complete assembly or strength validation.',
            ],
        }
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'checks': checks,
                          'maximum_sampled_belt_outside_nominal_inset_head_core_mm3':
                              result['maximum_sampled_belt_outside_nominal_inset_head_core_mm3']}))
        return

    # Reconstruct the actual orange lofts and the new root connectors in the
    # same pre-head coordinates as the builder, avoiding mesh approximation.
    stretch = manifest['beak_length_factor']

    def sections(rows):
        return [(316 + (x - 316) * stretch, z, w, h) for x, z, w, h in rows]

    upper = bill(sections([(320, 538, 23, 18), (342, 539, 23, 19),
                           (380, 537.5, 19, 17.5), (414, 530.5, 12, 10.5),
                           (433, 525.75, 7, 6.25), (440, 521.25, 2.5, 2.75)]), flat=True)
    lower_rows = [(322, 509, 21, 10), (348, 509, 22, 10),
                  (382, 511, 17, 8), (417, 513, 11, 6),
                  (435, 515, 6, 3.5), (439, 516, 2, 2)]
    if manifest.get('slim_lower_bill_study'):
        lower_rows = [(x, z + min(2, h - .7), w, h - min(2, h - .7))
                      for x, z, w, h in lower_rows]
    lower = bill(sections(lower_rows), flat=True)
    head_pre = (rounded_box((130, 92, 104), 35, (270, 0, 559))
                - rounded_box((pocket_length, 70, 95), 8, (345, 0, 512.5))
                - rounded_box((18, 67, 52), 7, (327, 0, 585))
                if whole_proportions else
                rounded_box((130, 92, 116), 40, (270, 0, 563))
                - rounded_box((pocket_length, 70, 95), 8, (345, 0, 512.5)) if wrapped else
                rounded_box((120, 92, 102), 32, (265, 0, 580)))
    if wrapped and not continuous_cheek:
        for side in (-1, 1):
            head_pre -= rounded_box((24, 16, 50), 4, (322, side * 33, 535))
    camera_panel_pre = (rounded_box((16, 65, 50), 6, (326, 0, 585))
                        if whole_proportions else
                        rounded_box((16, 69, 60), 6, (334, 0, 590))
                        if wrapped else
                        rounded_box((14, 69, 67), 6, (334, 0, 587)))
    previous_wrapped_camera_panel = (rounded_box((14, 69, 67), 6,
                                                 (334, 0, 587))
                                     if wrapped else None)
    camera_ring_pre = (disk(24, 9, (337, 0, 585), 'x') if whole_proportions
                       else disk(27, 9, (346, 0, 587), 'x'))
    fixed_hinge = None if wrapped else disk(20, 54, (298, 0, 524))
    sweep = []
    q0 = math.radians(40)
    for gap in np.linspace(0, 30, 9):
        q = math.asin(math.sin(q0) - gap / 25)
        dx = 25 * (math.cos(q) - math.cos(q0))
        moving_lower = moved(lower, (dx, 0, -gap))
        sample = {'nominal_opening_mm': round(float(gap), 5),
                  'upper_lower_overlap_mm3': overlap(upper, moving_lower),
                  'head_lower_overlap_mm3': overlap(head_pre, moving_lower),
                  'fixed_hinge_lower_overlap_mm3': (
                      overlap(fixed_hinge, moving_lower) if fixed_hinge is not None else None),
                  'side_carriers': []}
        for side in (-1, 1):
            y = side * 30
            b = (298 + 25 * math.cos(q), y, 524 + 25 * math.sin(q))
            root = (322 + dx, side * 22 if wrapped else y, 509 - gap)
            carrier, _ = fairing_between(b, root, 8 if wrapped else 7,
                                          5 if wrapped else 4)
            bridge = rounded_box((8, 15, 7), 3, (322 + dx, side * 24, 509 - gap))
            sample['side_carriers'].append({
                'side': side,
                'carrier_fixed_hinge_overlap_mm3': (
                    overlap(carrier, fixed_hinge) if fixed_hinge is not None else None),
                'carrier_head_overlap_mm3': overlap(carrier, head_pre),
                'carrier_upper_overlap_mm3': overlap(carrier, upper),
                'bridge_fixed_hinge_overlap_mm3': (
                    overlap(bridge, fixed_hinge) if fixed_hinge is not None else None),
                'bridge_head_overlap_mm3': overlap(bridge, head_pre),
                'bridge_upper_overlap_mm3': overlap(bridge, upper),
                'bridge_lower_joint_overlap_mm3': overlap(bridge, moving_lower),
                'bridge_carrier_joint_overlap_mm3': overlap(bridge, carrier),
            })
        sweep.append(sample)

    camera_upper_overlap = overlap(camera_panel_pre, upper)
    camera_upper_clearance = round(camera_panel_pre.distance_to(upper), 5)
    camera_ring_joint_overlap = overlap(camera_panel_pre, camera_ring_pre)
    fixed_head_upper_overlap = overlap(head_pre, upper)
    gross_pass = (motor_fit < .01
                  and overlap(motor_body, yoke) < .01
                  and overlap(motor_body, camera_panel) < .01
                  and (not wrapped or (camera_upper_overlap < .01
                                       and camera_upper_clearance > 1
                                       and camera_ring_joint_overlap > 1
                                       and fixed_head_upper_overlap < .01))
                  and max(s['outside_inset_exterior_mm3'] for s in belt_samples) < .01
                  and all(s['upper_lower_overlap_mm3'] < .01
                          and s['head_lower_overlap_mm3'] < .01
                          and (wrapped or s['fixed_hinge_lower_overlap_mm3'] < .01)
                          and all(v['carrier_head_overlap_mm3'] < .01
                                  and v['bridge_head_overlap_mm3'] < .01
                                  and v['carrier_upper_overlap_mm3'] < .01
                                  and v['bridge_upper_overlap_mm3'] < .01
                                  and (wrapped or
                                       (v['carrier_fixed_hinge_overlap_mm3'] < .01
                                        and v['bridge_fixed_hinge_overlap_mm3'] < .01))
                                  and v['bridge_lower_joint_overlap_mm3'] > 1
                                  and v['bridge_carrier_joint_overlap_mm3'] > 1
                                  for v in s['side_carriers']) for s in sweep))
    result = {
        'status': 'gross_package_screen_pass_only' if gross_pass else 'gross_package_screen_failed',
        'appearance_review_pass': False,
        'manufacturing_release_pass': False,
        'appearance_manifest_sha256': sha256(manifest_path),
        'source_script_sha256': sha256(Path(__file__)),
        'vendor_source': 'https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/',
        'motor_body_whd_vendor_mm': [20, 34, 26],
        'motor_shaft_from_one_end_layout_assumption_mm': 9.5,
        'motor_axis_visual_mm': motor_axis.tolist(),
        'motor_box_visual_min_mm': [motor_axis[0] - 10, -13, motor_axis[2] - 24.5],
        'motor_box_visual_max_mm': [motor_axis[0] + 10, 13, motor_axis[2] + 9.5],
        'motor_outside_2p7mm_inset_head_mm3': motor_fit,
        'motor_yoke_overlap_mm3': overlap(motor_body, yoke),
        'motor_camera_panel_overlap_mm3': overlap(motor_body, camera_panel),
        'drive_A_visual_mm': a.tolist(),
        'wrapped_head_visual_study': wrapped,
        'continuous_head_cheek_study': continuous_cheek,
        'reference_whole_proportions_study': whole_proportions,
        'fixed_head_upper_bill_overlap_mm3': fixed_head_upper_overlap,
        'camera_panel_upper_bill_overlap_mm3': camera_upper_overlap,
        'camera_panel_upper_bill_clearance_mm': camera_upper_clearance,
        'previous_wrapped_camera_panel_upper_bill_overlap_mm3': (
            overlap(previous_wrapped_camera_panel, upper)
            if previous_wrapped_camera_panel is not None else None),
        'camera_panel_ring_joint_overlap_mm3': camera_ring_joint_overlap,
        'motor_to_A_center_distance_mm': round(c, 4),
        'belt_hypothesis': {
            'profile': 'GT2 candidate, sourcing and actual pulley OD unverified',
            'input_output_teeth': [16, 32],
            'drive_ratio': 2,
            'pitch_length_at_nominal_centres_mm': round(pitch_length, 4),
            'gross_radius_motor_output_mm': [6.5, 11.5],
            'extra_radial_allowance_mm': .5,
            'gross_width_mm': 6,
            'belt_lateral_center_mm': belt_lateral_center,
            'belt_lateral_center_source': 'appearance_manifest.beak_drive_package_hypothesis.gross_belt_lateral_center_visual_mm',
            'max_sampled_outside_inset_exterior_mm3': max(
                s['outside_inset_exterior_mm3'] for s in belt_samples),
            'samples': belt_samples,
        },
        'r2_ideal_nine_pose_brep': sweep,
        'limitations': [
            'This tests gross solids and 33 sampled belt stations, not a continuous belt sweep or real tooth geometry.',
            'Head and bill are still solid appearance parts; hollow frames, bearings, shaft, motor horn, tensioner, fasteners, split lines and cable bend are absent.',
            'Any measured head/fixed-upper-bill overlap must be removed by a real shell split; moving carrier overlaps demand internal cavities, slots and full swept-volume checks.',
            'The vendor motor body size is official, but the 9.5 mm output location and orientation are layout assumptions pending the vendor CAD.',
            'The 2.7 mm skin is a geometric study; material, print direction, tolerance, stiffness and impact loads are unverified.',
            'The two long lower-root carriers are only visual solids and have not been checked for strength or acceptable appearance.',
            'No real pad gap, friction, 50 g object capture, dragging or continuous motor torque has been tested in this candidate.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'motor_outside_2p7mm_inset_head_mm3',
                                            'motor_yoke_overlap_mm3',
                                            'motor_camera_panel_overlap_mm3')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
