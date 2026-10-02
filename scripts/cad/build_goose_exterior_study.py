"""Build an appearance-only Goose study against the archived B/R2 reference.

This is deliberately separate from the RC2 mechanism and cannot be used as a
print-ready or dynamic robot. Coordinates are provisional millimetres.
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
from scipy.spatial.transform import Rotation
from build123d import (Box, Compound, Cylinder, Ellipse, Matrix, Plane, Pos, Rot, Sphere,
                       RectangleRounded, export_step, export_stl, extrude, fillet, loft, offset)
from OCP.gp import gp_Trsf
from build123d import Location

from sai_agent.paths import resource_root


COLORS = {
    'white': '0.90 0.89 0.85 1',
    'orange': '0.94 0.38 0.04 1',
    'black': '0.055 0.065 0.07 1',
    'dark': '0.16 0.17 0.18 1',
    'lens': '0.01 0.025 0.04 1',
    'glass': '0.025 0.055 0.075 1',
    'metal': '0.40 0.44 0.46 1',
}


# Align the leg mounts with the middle of the body and carry the soles forward.
# This is a visual/support-footprint correction, not a verified walking layout.
DEFAULT_LEG_FORWARD_SHIFT_MM = 85
R2_CRANK_LENGTH_MM = 25.0
R2_ANCHOR_SPACING_MM = 14.0
R2_CLOSED_RAD = math.radians(40.0)
R2_NET_OPENING_MM = 30.0
R2_GEAR_MODULE_MM = 0.8
R2_INPUT_GEAR_TEETH = 18
R2_OUTPUT_GEAR_TEETH = 36
R2_GEAR_CENTER_MM = R2_GEAR_MODULE_MM * (R2_INPUT_GEAR_TEETH + R2_OUTPUT_GEAR_TEETH) / 2
REAR_BODY_CROWN_CENTER_MM = (-75.0, 0.0, 312.0)
REAR_BODY_CROWN_RADII_MM = (102.0, 83.0, 88.0)


def moved(shape, center, rotation=None):
    matrix = np.eye(4)
    matrix[:3, 3] = center
    if rotation is not None:
        matrix[:3, :3] = rotation
    trsf = gp_Trsf()
    trsf.SetValues(*[float(v) for v in matrix[:3, :].ravel()])
    return shape.moved(Location(trsf))


def scaled_z(shape, scale, offset):
    """Apply an appearance-only vertical affine map to a finished solid."""
    return shape.transform_geometry(Matrix([
        [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, scale, offset], [0, 0, 0, 1],
    ]))


def scaled_about(shape, scale, center):
    """Scale an appearance solid about a fixed torso datum, in millimetres."""
    sx, sy, sz = scale
    x, y, z = center
    return shape.transform_geometry(Matrix([
        [sx, 0, 0, x * (1 - sx)],
        [0, sy, 0, y * (1 - sy)],
        [0, 0, sz, z * (1 - sz)],
        [0, 0, 0, 1],
    ]))


def rounded_box(size, radius, center):
    shape = Box(*size)
    return moved(fillet(shape.edges(), radius), center)


def ellipsoid(radii, center):
    return moved(Sphere(1).scale(radii), center)


def lofted_goose_body():
    """Continuous rear-fuller shell, still a solid appearance study."""
    sections = [
        (-185, 32, 58, 270),
        (-155, 177, 180, 265),
        (-110, 205, 255, 276),
        (-10, 205, 230, 270),
        (90, 188, 205, 270),
        (150, 112, 120, 270),
        (165, 32, 58, 270),
    ]
    profiles = []
    for x, width, height, z in sections:
        plane = Plane(origin=(x, 0, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        profiles.append(plane * RectangleRounded(
            width, height, min(width, height) * .42))
    return loft(profiles)


def reference_fuller_goose_body():
    """Visual torso with a full front chest and a continuous side surface."""
    sections = [
        (-185, 24, 48, 270),
        (-155, 175, 180, 267),
        (-110, 205, 230, 270),
        (-10, 205, 230, 270),
        (90, 202, 220, 270),
        (150, 122, 145, 270),
        (165, 24, 48, 270),
    ]
    profiles = []
    for x, width, height, z in sections:
        plane = Plane(origin=(x, 0, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        profiles.append(plane * RectangleRounded(
            width, height, min(width, height) * .42))
    return loft(profiles)


def reference_torso_hull():
    """Full, flatter torso with rounded ends and a broad side hatch field."""
    blank = Box(350, 205, 230)
    longitudinal = [edge for edge in blank.edges()
                    if abs(edge.tangent_at(.5).X) > .99]
    hull = fillet(longitudinal, 65)
    end_edges = [edge for edge in hull.edges()
                 if abs(edge.center().X) > 174.9]
    return moved(fillet(end_edges, 40), (-10, 0, 270))


def sculpted_goose_head():
    """Continuous helmet-like exterior around the R2 drive and camera face."""
    sections = [
        (197, 30, 45, 570),
        (212, 70, 94, 567),
        (235, 91, 112, 565),
        (275, 94, 116, 563),
        (310, 92, 110, 567),
        (334, 86, 96, 575),
        (344, 86, 96, 575),
    ]
    profiles = []
    for x, width, height, z in sections:
        plane = Plane(origin=(x, 0, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        profiles.append(plane * RectangleRounded(
            width, height, min(width, height) * .42))
    return loft(profiles)


def helmet_goose_head():
    """Rounded helmet with a real frontal face for the inset camera panel."""
    blank = Box(130, 92, 116)
    longitudinal = [edge for edge in blank.edges()
                    if abs(edge.tangent_at(.5).X) > .99]
    shell = fillet(longitudinal, 28)
    front = [edge for edge in shell.edges() if edge.center().X > 64.9]
    shell = fillet(front, 8)
    back = [edge for edge in shell.edges() if edge.center().X < -64.9]
    return moved(fillet(back, 25), (270, 0, 563))


def tapered_helmet_goose_head():
    """Round rear helmet flowing into a camera-sized nose, without a front slab."""
    sections = [
        (197, 30, 45, 570),
        (212, 68, 88, 567),
        (235, 90, 110, 563),
        (275, 94, 112, 563),
        (305, 90, 104, 567),
        (330, 84, 90, 577),
        (342, 80, 78, 583),
    ]
    profiles = []
    for x, width, height, z in sections:
        plane = Plane(origin=(x, 0, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        profiles.append(plane * RectangleRounded(
            width, height, min(width, height) * .25))
    return loft(profiles)


def conformal_wing_panels(body, side):
    """Split visual hatch patches from the torso's own curved side surface."""
    outer = side_panel(190, 99, 14, 26, (-35, side * 100, 295))
    inner = side_panel(186, 95, 14, 24, (-35, side * 100, 295))
    seam = body & (outer - inner)
    door = body & inner
    vents = []
    for x in (-97, -89, -81):
        cutter = side_panel(2.8, 14, 14, 1, (x, side * 100, 282))
        vents.append(door & cutter)
        door = door - cutter
    proud = (0, side * .7, 0)
    return outer, seam, moved(door, proud), [moved(vent, proud) for vent in vents]


def side_panel(width, height, thickness, radius, center):
    face = Plane.XZ * RectangleRounded(width, height, radius)
    return moved(extrude(face, amount=thickness, both=True), center)


def shoe_layer(length, width, thickness, corner, center):
    # The reference shoe is a low, blunt rounded rectangle, not a tapered bill.
    footprint = Plane.XY * RectangleRounded(length, width, corner)
    blank = extrude(footprint, amount=thickness / 2, both=True)
    return moved(fillet(blank.edges(), min(thickness * .28, 3)), center)


def disk(radius, thickness, center, axis='y'):
    r = Rot(90, 0, 0) if axis == 'y' else Rot(0, 90, 0) if axis == 'x' else Rot(0, 0, 0)
    return moved(r * Cylinder(radius, thickness), center)


def fairing_between(start, end, width, depth, color='white'):
    vector = np.subtract(end, start)
    length = float(np.linalg.norm(vector))
    stock = Box(width, depth, length)
    shape = fillet(stock.edges(), min(width, depth) * .26)
    rotation, _ = Rotation.align_vectors([vector / length], [[0, 0, 1]])
    return moved(shape, (np.asarray(start) + end) / 2, rotation.as_matrix()), color


def bill(sections, flat=False):
    profiles = []
    for x, z, half_width, half_height in sections:
        # Profile normal follows forward X; width is lateral Y.
        from build123d import Plane
        plane = Plane(origin=(x, 0, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        if flat:
            corner = min(half_width, half_height) * .58
            profiles.append(plane * RectangleRounded(2 * half_width, 2 * half_height, corner))
        else:
            profiles.append(plane * Ellipse(half_width, half_height))
    return loft(profiles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--beak-open', action='store_true',
                        help='Appearance pose only: place the lower bill at the R2 30 mm four-bar target opening.')
    parser.add_argument('--foot-shift-mm', type=float, default=0,
                        help='Shift the shoe fore/aft while leaving the ankle fixed.')
    parser.add_argument('--heel-extension-mm', type=float, default=0,
                        help='Extend the shoe behind the ankle while holding its toe fixed.')
    parser.add_argument('--foot-toe-shortening-mm', type=float, default=0,
                        help='Pull the toe edge back while retaining the heel support extension.')
    parser.add_argument('--leg-forward-shift-mm', type=float,
                        default=DEFAULT_LEG_FORWARD_SHIFT_MM,
                        help='Move the hip, leg and shoe together relative to the early B/R2 study.')
    parser.add_argument('--knee-forward-shift-mm', type=float, default=0.0,
                        help='Move the knee and adjoining fairings forward without moving hip or ankle.')
    parser.add_argument('--beak-length-factor', type=float, default=1.0,
                        help='Stretch the pointed bill forward from its hinge for a visual-only R2 comparison.')
    parser.add_argument('--head-scale', type=float, default=1.0,
                        help='Scale the white head shell about its centre for a visual-only proportion comparison.')
    parser.add_argument('--head-assembly-back-mm', type=float, default=0.0,
                        help='Bring the head, pointed bill, and upper-neck endpoint back for a B/R2 silhouette comparison.')
    parser.add_argument('--neck-rest-fold-deg', type=float, default=0.0,
                        help='Fold only the upper neck rearward in the neutral visual pose; keep the head and bill level.')
    parser.add_argument('--vertical-compression', type=float, default=0.0,
                        help='Interpolate 0..1 from the B-like tall study toward the compact R2 body ratio.')
    parser.add_argument('--r2-proportions', action='store_true',
                        help='Use the R2 body/neck ratio while retaining more leg length than the compact study.')
    parser.add_argument('--r2-low-ankle-study', action='store_true',
                        help='Reproduce the rejected R2 comparison whose pitch motor enters the sole.')
    parser.add_argument('--compact-body-study', action='store_true',
                        help='Appearance-only 310x190x200 mm torso study for a lower sit-and-grasp pose.')
    parser.add_argument('--compact-body-height-mm', type=float, default=200.0,
                        help='Appearance-only torso height within the compact-body study; packaging is unverified.')
    parser.add_argument('--compact-body-length-mm', type=float, default=310.0,
                        help='Appearance-only torso fore-aft length within the compact-body study.')
    parser.add_argument('--low-profile-shell-study', action='store_true',
                        help='Reduce the raised wing-hatch lip and stacked shoe height against the B/R2 reference.')
    parser.add_argument('--r2-geared-cheek-study', action='store_true',
                        help='Study a raised R2 fixed axis and a cheek envelope for an offset 2:1 XL330 drive.')
    parser.add_argument('--r2-internal-belt-study', action='store_true',
                        help='Study an XL330 inside the white head with a concealed 2:1 belt to a raised R2 jaw axis.')
    parser.add_argument('--r2-head-wrap-study', action='store_true',
                        help='Appearance trial: wrap the hidden R2 output inside a longer lower head shell and keep one small orange root badge.')
    parser.add_argument('--slim-lower-bill-study', action='store_true',
                        help='Thin the R2 lower-bill underside while retaining its upper grip datum for ground-clearance comparison.')
    parser.add_argument('--integrated-camera-face-study', action='store_true',
                        help='Recess the black camera face into the white head silhouette and bring its lens stack back.')
    parser.add_argument('--recessed-camera-bezel-study', action='store_true',
                        help='Seat the full black camera bezel 5 mm deeper in the head while keeping the lens stack joined.')
    parser.add_argument('--lower-beak-root-cap-study', action='store_true',
                        help='Move the small orange identity cap down toward the visible R2 bill root.')
    parser.add_argument('--sculpted-head-study', action='store_true',
                        help='Trial a continuous head hull that seats the full camera bezel around the pointed R2 bill.')
    parser.add_argument('--helmet-head-study', action='store_true',
                        help='Trial a rounded helmet with a defined inset frontal camera face.')
    parser.add_argument('--tapered-helmet-head-study', action='store_true',
                        help='Trial a round rear helmet tapering to a camera-sized nose face.')
    parser.add_argument('--continuous-head-cheek-study', action='store_true',
                        help="Keep the wrapped head's white side cheeks continuous over the visual R2 linkage.")
    parser.add_argument('--rear-body-crown-study', action='store_true',
                        help="Add fullness behind the neck while preserving the compact body's front reach keepout.")
    parser.add_argument('--lofted-body-study', action='store_true',
                        help='Use a continuous rear-fuller torso loft instead of the rounded-box visual shell.')
    parser.add_argument('--conformal-body-door-study', action='store_true',
                        help='Trial a fuller continuous torso with manual wing patches cut from its curved sides.')
    parser.add_argument('--conformal-wing-door-study', action='store_true',
                        help='Cut the manual wing patches from the existing rounded torso without changing its outline.')
    parser.add_argument('--reference-torso-door-study', action='store_true',
                        help='Trial a flatter full torso and conformal minimalist manual doors as one shape.')
    parser.add_argument('--reference-whole-proportions-study', action='store_true',
                        help='Compare a lower head and longer visible neck as one B/R2 silhouette change.')
    parser.add_argument('--reference-head-clearance-study', action='store_true',
                        help='Trial a thin continuous head skin cut by the R2 bill sweep, replacing the large front rectangular visual pocket.')
    args = parser.parse_args()
    if not -50 <= args.foot_shift_mm <= 50 or not 0 <= args.heel_extension_mm <= 80:
        raise ValueError('Foot study parameters exceed the preliminary comparison range')
    if not 0 <= args.foot_toe_shortening_mm <= 45:
        raise ValueError('Toe shortening exceeds the preliminary appearance comparison range')
    if not 0 <= args.leg_forward_shift_mm <= 110:
        raise ValueError('Leg layout study parameter exceeds the preliminary range')
    if not 0 <= args.knee_forward_shift_mm <= 45:
        raise ValueError('Knee shift exceeds the preliminary morphology comparison range')
    if not 1.0 <= args.beak_length_factor <= 1.8:
        raise ValueError('Beak visual stretch exceeds the preliminary comparison range')
    if not 1.0 <= args.head_scale <= 1.25:
        raise ValueError('Head visual scale exceeds the preliminary comparison range')
    if not 0 <= args.head_assembly_back_mm <= 45:
        raise ValueError('Head assembly shift exceeds the preliminary comparison range')
    if not 0 <= args.neck_rest_fold_deg <= 20:
        raise ValueError('Upper-neck rest fold exceeds the preliminary visual comparison range')
    if not 170 <= args.compact_body_height_mm <= 200:
        raise ValueError('Compact torso height exceeds the preliminary comparison range')
    if not 270 <= args.compact_body_length_mm <= 310:
        raise ValueError('Compact torso length exceeds the preliminary comparison range')
    if not 0 <= args.vertical_compression <= 1:
        raise ValueError('Vertical compression must be between 0 and 1')
    if sum((bool(args.vertical_compression), args.r2_proportions,
            args.r2_low_ankle_study)) > 1:
        raise ValueError('Choose one vertical proportion study')
    if args.compact_body_study and not args.r2_proportions:
        raise ValueError('The compact body study uses the high-ankle R2 proportions')
    if not args.compact_body_study and args.compact_body_height_mm != 200:
        raise ValueError('Compact torso height requires --compact-body-study')
    if not args.compact_body_study and args.compact_body_length_mm != 310:
        raise ValueError('Compact torso length requires --compact-body-study')
    if args.r2_geared_cheek_study and not (args.r2_proportions and args.compact_body_study):
        raise ValueError('The geared cheek study uses the compact R2 proportions')
    if args.r2_internal_belt_study and not (args.r2_proportions and args.compact_body_study):
        raise ValueError('The internal belt study uses the compact R2 proportions')
    if args.r2_internal_belt_study and args.r2_geared_cheek_study:
        raise ValueError('Choose one R2 drive package study')
    if args.r2_head_wrap_study and not args.r2_internal_belt_study:
        raise ValueError('The wrapped head study requires the internal R2 belt candidate')
    if args.slim_lower_bill_study and not args.r2_head_wrap_study:
        raise ValueError('The slim lower-bill study requires the wrapped R2 head')
    if args.recessed_camera_bezel_study and (
            not args.r2_head_wrap_study or args.integrated_camera_face_study):
        raise ValueError('The recessed bezel trial requires the wrapped R2 head without the earlier face trial')
    if args.lower_beak_root_cap_study and not args.r2_head_wrap_study:
        raise ValueError('The lower bill-root cap trial requires the wrapped R2 head')
    if args.sculpted_head_study and (
            not args.r2_head_wrap_study or args.integrated_camera_face_study
            or args.recessed_camera_bezel_study or args.head_scale != 1.0):
        raise ValueError('The sculpted head trial requires the unscaled wrapped R2 head and its own camera seat')
    if args.helmet_head_study and (
            not args.r2_head_wrap_study or args.sculpted_head_study
            or args.tapered_helmet_head_study or args.integrated_camera_face_study
            or args.recessed_camera_bezel_study or args.head_scale != 1.0):
        raise ValueError('The helmet trial requires the unscaled wrapped R2 head and its own camera seat')
    if args.tapered_helmet_head_study and (
            not args.r2_head_wrap_study or args.sculpted_head_study
            or args.integrated_camera_face_study or args.recessed_camera_bezel_study
            or args.head_scale != 1.0):
        raise ValueError('The tapered helmet trial requires the unscaled wrapped R2 head and its own camera seat')
    if args.continuous_head_cheek_study and (
            not args.r2_head_wrap_study or args.sculpted_head_study):
        raise ValueError('The continuous cheek trial uses the original wrapped R2 head')
    if args.rear_body_crown_study and not (
            args.r2_proportions and args.compact_body_study
            and args.compact_body_height_mm == 180
            and args.compact_body_length_mm == 280):
        raise ValueError('The rear crown trial is tied to the compact v73 body core')
    if args.lofted_body_study and not (
            args.r2_proportions and args.compact_body_study
            and args.compact_body_height_mm == 180
            and args.compact_body_length_mm == 280
            and not args.rear_body_crown_study):
        raise ValueError('The lofted body trial is tied to the compact v73 body core')
    if args.conformal_body_door_study and not (
            args.r2_proportions and args.compact_body_study
            and args.compact_body_height_mm == 180
            and args.compact_body_length_mm == 280
            and not args.rear_body_crown_study and not args.lofted_body_study):
        raise ValueError('The conformal hatch trial is tied to the compact v73 body core')
    if args.conformal_wing_door_study and not (
            args.r2_proportions and args.compact_body_study
            and args.compact_body_height_mm == 180
            and args.compact_body_length_mm == 280
            and not args.rear_body_crown_study and not args.lofted_body_study
            and not args.conformal_body_door_study):
        raise ValueError('The conformal wing trial uses the rounded compact v73 body')
    if args.reference_torso_door_study and not (
            args.r2_proportions and args.compact_body_study
            and args.compact_body_height_mm == 180
            and args.compact_body_length_mm == 280
            and not args.rear_body_crown_study and not args.lofted_body_study
            and not args.conformal_body_door_study and not args.conformal_wing_door_study):
        raise ValueError('The reference torso trial uses the compact v73 core')
    if args.reference_whole_proportions_study and not (
            args.r2_proportions and args.compact_body_study
            and args.compact_body_height_mm == 180
            and args.compact_body_length_mm == 280
            and args.head_scale == 1.0 and args.head_assembly_back_mm == 25.0
            and args.r2_head_wrap_study and not args.sculpted_head_study
            and not args.helmet_head_study and not args.tapered_helmet_head_study
            and not args.integrated_camera_face_study
            and not args.recessed_camera_bezel_study):
        raise ValueError('The whole-proportion trial requires the original compact R2 silhouette')
    if args.reference_head_clearance_study and not args.reference_whole_proportions_study:
        raise ValueError('The bill-swept head trial requires the v92 whole proportions')
    args.output.mkdir(parents=True, exist_ok=False)
    root = resource_root()
    references = [
        root / 'robots/Goose_V0.1/design/concepts/history/walker_b_selected_reference.png',
        root / 'robots/Goose_V0.1/design/concepts/history/walker_r1/goose_v0.1_walker_concept.png',
        root / 'robots/Goose_V0.1/design/concepts/beak_r2_review_board.png',
        root / 'robots/Goose_V0.1/design/concepts/r2_pointed_beak_closed_reference.jpg',
        root / 'robots/Goose_V0.1/design/concepts/r2_pointed_beak_parallel_open_reference.jpg',
    ]
    parts = []
    r2_profile = {'body_z_shift': -60.0, 'neck_z_scale': .645,
                  'neck_z_offset': 105.075, 'head_z_shift': -159.0}
    if args.reference_whole_proportions_study:
        neck_scale = .8
        neck_offset = 105.075 + (.645 - neck_scale) * 477
        r2_profile.update(neck_z_scale=neck_scale,
                          neck_z_offset=neck_offset,
                          head_z_shift=744 * neck_scale + neck_offset - 744)
    vertical_profile = (
        {'leg_z_scale': (229.0 - 51.0) / (286.0 - 51.0),
         'leg_z_offset': 51.0 * (1.0 - (229.0 - 51.0) / (286.0 - 51.0)),
         **r2_profile}
        if args.r2_proportions else
        {'leg_z_scale': .8, 'leg_z_offset': 0.0, **r2_profile}
        if args.r2_low_ankle_study else
        {'leg_z_scale': 1 - .32 * args.vertical_compression,
         'leg_z_offset': 0.0,
         'body_z_shift': -90 * args.vertical_compression,
         'neck_z_scale': 1 - .34 * args.vertical_compression,
         'neck_z_offset': 68.1 * args.vertical_compression,
         'head_z_shift': -185 * args.vertical_compression}
    )
    neck_assembly_drop_mm = ((200.0 - args.compact_body_height_mm) / 2
                             if args.compact_body_study else 0.0)
    rest_elbow = np.array([0.0, 0.0, 632.0 * vertical_profile['neck_z_scale']
                           + vertical_profile['neck_z_offset'] - neck_assembly_drop_mm])
    rest_yoke = np.array([86.0 - args.head_assembly_back_mm, 0.0,
                          744.0 + vertical_profile['head_z_shift'] - neck_assembly_drop_mm])
    rest_fold_rotation = Rotation.from_euler('y', -args.neck_rest_fold_deg,
                                              degrees=True).as_matrix()
    rest_yoke_delta = (rest_elbow + rest_fold_rotation @ (rest_yoke - rest_elbow)
                       - rest_yoke)

    def add(name, shape, color):
        # Keep one shared head/bill shift so the side silhouette stays
        # coherent in the closed and open poses.
        if name == 'head' or name.startswith(('head_', 'camera_', 'beak_')):
            shape = moved(shape, (-125 - args.head_assembly_back_mm, 0, 150))
        elif name.startswith('hip_'):
            shape = moved(shape, (-60 + args.leg_forward_shift_mm, 0, 80))
        elif name.startswith(('thigh_', 'knee_', 'shin_', 'ankle_', 'foot_')):
            shape = moved(shape, (-60 + args.leg_forward_shift_mm, 0, 0))
        elif name.startswith(('body', 'wing_', 'neck_root')):
            shape = moved(shape, (0, 0, 80))
        if args.r2_proportions or args.r2_low_ankle_study or args.vertical_compression:
            if name.startswith(('hip_', 'thigh_', 'knee_', 'shin_', 'ankle_')):
                shape = scaled_z(shape, vertical_profile['leg_z_scale'],
                                 vertical_profile['leg_z_offset'])
            elif name.startswith(('body', 'wing_')):
                shape = moved(shape, (0, 0, vertical_profile['body_z_shift']))
            elif name.startswith('neck_'):
                shape = scaled_z(shape, vertical_profile['neck_z_scale'],
                                 vertical_profile['neck_z_offset'])
            elif name == 'head' or name.startswith(('head_', 'camera_', 'beak_')):
                shape = moved(shape, (0, 0, vertical_profile['head_z_shift']))
        if args.compact_body_study and (name == 'body' or name.startswith(('body_', 'wing_'))):
            shape = scaled_about(shape, (args.compact_body_length_mm / 350, 190 / 205,
                                         args.compact_body_height_mm / 230),
                                 (-10, 0, 290))
        if args.rear_body_crown_study and name == 'body':
            shape = shape + ellipsoid(REAR_BODY_CROWN_RADII_MM,
                                      REAR_BODY_CROWN_CENTER_MM)
        elif args.rear_body_crown_study and name == 'body_top_button':
            shape = moved(shape, (0, 0, 18))
        if neck_assembly_drop_mm and (name.startswith('neck_') or name == 'head'
                                      or name.startswith(('head_', 'camera_', 'beak_'))):
            shape = moved(shape, (0, 0, -neck_assembly_drop_mm))
        if args.neck_rest_fold_deg:
            if name.startswith('neck_upper'):
                shape = moved(shape, rest_elbow - rest_fold_rotation @ rest_elbow,
                              rest_fold_rotation)
            elif name == 'head' or name.startswith(('head_', 'camera_', 'beak_')):
                shape = moved(shape, rest_yoke_delta)
        if not shape.is_valid or shape.volume <= 0:
            raise ValueError(f'invalid exterior study shape: {name}')
        path = args.output / (name + '.stl')
        export_stl(shape, path,
                   tolerance=.12 if args.r2_head_wrap_study else .3,
                   angular_tolerance=.07 if args.r2_head_wrap_study else .18)
        parts.append((name, shape, color, path))

    # The B design has a broad continuous body, a small camera head and a long,
    # tapered orange bill. These solids describe silhouette only.
    body_shape = (reference_torso_hull() if args.reference_torso_door_study else
                  reference_fuller_goose_body() if args.conformal_body_door_study else
                  lofted_goose_body() if args.lofted_body_study else
                  rounded_box((350, 205, 230), 92, (-10, 0, 270)))
    wing_panels = {}
    if (args.conformal_body_door_study or args.conformal_wing_door_study
            or args.reference_torso_door_study):
        for side in (-1, 1):
            outer, seam, door, vents = conformal_wing_panels(body_shape, side)
            wing_panels[side] = (seam, door, vents)
            body_shape = body_shape - outer
    add('body', body_shape, 'white')
    add('body_underside', ellipsoid((145, 86, 27), (-10, 0, 155)), 'black')
    add('body_top_button', disk(10, 5, (-79, 0, 390), 'z'), 'orange')
    for side in (-1, 1):
        if (args.conformal_body_door_study or args.conformal_wing_door_study
                or args.reference_torso_door_study):
            seam, door, vents = wing_panels[side]
            add(f'wing_door_seam_{side}', seam, 'metal')
            add(f'wing_service_door_{side}', door, 'white')
            for x, vent in zip((-97, -89, -81), vents):
                add(f'wing_vent_{side}_{-x}', vent, 'black')
        else:
            seam_thickness = 1 if args.low_profile_shell_study else 2
            door_thickness = 2 if args.low_profile_shell_study else 4
            door_y = 103.5 if args.low_profile_shell_study else 105
            vent_y = 105 if args.low_profile_shell_study else 108
            add(f'wing_door_seam_{side}', side_panel(190, 99, seam_thickness,
                                                     26, (-35, side * 103.5, 295)), 'metal')
            add(f'wing_service_door_{side}', side_panel(186, 95, door_thickness,
                                                        24, (-35, side * door_y, 295)), 'white')
            for x in (-97, -89, -81):
                add(f'wing_vent_{side}_{-x}', side_panel(2.8, 14, 1.2, 1,
                                                         (x, side * vent_y, 282)), 'black')
        add(f'hip_{side}', disk(29, 42, (-35, side * 87, 205)), 'black')
        add(f'hip_rim_{side}', disk(21, 43, (-35, side * 87, 205)), 'metal')
        add(f'hip_accent_{side}', disk(12, 44, (-35, side * 87, 205)), 'orange')
    add('neck_root_saddle', rounded_box((70, 62, 22), 8, (59, 0, 373)), 'black')
    add('neck_root', disk(35, 54, (59, 0, 397)), 'black')
    add('neck_root_rim', disk(24, 55, (59, 0, 397)), 'metal')
    add('neck_root_accent', disk(13, 56, (59, 0, 397)), 'orange')
    for name, start, end in [
        ('neck_lower_spine', (52, 0, 493), (-22, 0, 625)),
        ('neck_upper_spine', (-17, 0, 638),
         (86 - args.head_assembly_back_mm, 0, 744)),
    ]:
        shape, _ = fairing_between(start, end, 23, 30)
        add(name, shape, 'black')
    for name, start, end, width, depth in [
        ('neck_lower', (74, 0, 493), (0, 0, 625), 47, 52),
        ('neck_upper', (5, 0, 638),
         (81 - args.head_assembly_back_mm, 0, 744), 43, 44),
    ]:
        shape, color = fairing_between(start, end, width, depth)
        add(name, shape, color)
    add('neck_elbow', disk(27, 54, (0, 0, 632)), 'black')
    add('neck_elbow_rim', disk(19, 55, (0, 0, 632)), 'metal')
    add('neck_elbow_accent', disk(11, 56, (0, 0, 632)), 'orange')
    add('head_yoke', disk(23, 50, (211, 0, 594)), 'black')
    r2_front_pocket_length_mm = 66 if args.continuous_head_cheek_study else 60
    head_outer = (sculpted_goose_head() if args.sculpted_head_study else
                   tapered_helmet_goose_head() if args.tapered_helmet_head_study else
                   helmet_goose_head() if args.helmet_head_study else
                   rounded_box((130, 92, 104), 35, (270, 0, 559))
                   if args.reference_whole_proportions_study else
                   rounded_box((130, 92, 116), 40, (270, 0, 563)))
    if args.reference_head_clearance_study:
        # Keep a continuous outside skin; carve the moving bill separately
        # after its actual solids and translation path have been built.
        head_shape = head_outer - rounded_box(
            (124.6, 86.6, 98.6), 32.3, (270, 0, 559))
    elif args.r2_head_wrap_study:
        head_shape = head_outer - rounded_box(
            (r2_front_pocket_length_mm, 70, 95), 8, (345, 0, 512.5))
    else:
        head_shape = rounded_box(
            tuple(value * args.head_scale for value in (120, 92, 102)),
            32 * args.head_scale, (265, 0, 580))
    if (args.r2_head_wrap_study and not args.continuous_head_cheek_study
            and not args.reference_head_clearance_study):
        for side in (-1, 1):
            head_shape -= rounded_box((24, 16, 50), 4, (322, side * 33, 535))
    camera_panel_size = ((16, 65, 50) if args.reference_whole_proportions_study else
                         (16, 69, 60) if args.r2_head_wrap_study else
                         (14, 69, 67))
    camera_panel_center = ((338 if args.tapered_helmet_head_study else
                            331 if args.helmet_head_study else
                            339 if args.sculpted_head_study else
                            326 if args.reference_whole_proportions_study else
                            329 if args.recessed_camera_bezel_study else 334,
                            0, 585 if args.reference_whole_proportions_study else 590)
                           if args.r2_head_wrap_study else
                           (334, 0, 587))
    camera_panel_shape = rounded_box(camera_panel_size, 6, camera_panel_center)
    if args.reference_whole_proportions_study:
        head_shape -= rounded_box((18, 67, 52), 7, (327, 0, 585))
    elif args.tapered_helmet_head_study:
        head_shape -= rounded_box((18, 71, 62), 7, (338, 0, 590))
    elif args.helmet_head_study:
        head_shape -= rounded_box((18, 71, 62), 7, (332, 0, 590))
    elif args.sculpted_head_study or args.recessed_camera_bezel_study:
        head_shape -= camera_panel_shape
    elif args.integrated_camera_face_study:
        camera_mask = rounded_box((18, 69, 60), 6, (331, 0, 590))
        camera_panel_shape = head_shape & camera_mask
        head_shape -= camera_mask
    if not args.reference_head_clearance_study:
        add('head', head_shape, 'white')
    # Keep the black camera face clear of the fixed upper bill while joining
    # the orange lens ring to the face in this visual package study.
    add('camera_panel', camera_panel_shape, 'black')
    camera_stack_dx = (-9.0 if args.reference_whole_proportions_study else
                       -1.0 if args.tapered_helmet_head_study else
                       -4.0 if args.helmet_head_study else
                       3.0 if args.sculpted_head_study else
                       -5.0 if args.recessed_camera_bezel_study else
                       -6.5 if args.integrated_camera_face_study else 0.0)
    camera_stack_z = 585 if args.reference_whole_proportions_study else 587
    lens_scale = 24 / 27 if args.reference_whole_proportions_study else 1.0
    add('camera_ring', disk(27 * lens_scale, 9,
                            (346 + camera_stack_dx, 0, camera_stack_z), 'x'), 'orange')
    add('camera_lens', disk(20 * lens_scale, 10,
                            (352 + camera_stack_dx, 0, camera_stack_z), 'x'), 'lens')
    add('camera_inner_glass', disk(15 * lens_scale, 1.5,
                                   (358 + camera_stack_dx, 0, camera_stack_z), 'x'), 'glass')
    add('camera_aperture', disk(8 * lens_scale, 1,
                                (359 + camera_stack_dx, 0, camera_stack_z), 'x'), 'lens')
    add('camera_glint', disk(2.5 * lens_scale, .6,
                             (360 + camera_stack_dx, -5, camera_stack_z + 6), 'x'), 'white')
    hinge_center = ((298, 0, 524) if args.r2_internal_belt_study else (316, 0, 538))
    if not args.r2_head_wrap_study:
        add('beak_hinge', disk(20, 54, hinge_center), 'orange')
    if not args.r2_internal_belt_study:
        add('beak_mechanism_cover', rounded_box((28, 34, 15), 5, (300, 0, 530)), 'black')
    if args.r2_geared_cheek_study:
        # Gross exterior keepout only. The black cheek must eventually be
        # hollow with bearing seats and slots for both moving crank pairs.
        add('beak_geared_cheek_keepout', rounded_box((56, 80, 54), 10,
                                                     (292, 0, 522)), 'dark')
    for side in (-1, 1):
        add(f'head_side_port_{side}', disk(5, 2, (270, side * 47 * args.head_scale, 578)), 'dark')
        if args.r2_internal_belt_study and not args.r2_head_wrap_study:
            # A thin outboard cheek hides the four-bar at rest while leaving
            # the moving linkage inside it and the pointed bill unobstructed.
            add(f'beak_service_cheek_{side}',
                side_panel(50, 50, 2, 20, (303, side * 35, 531)),
                'white' if args.r2_head_wrap_study else 'orange')
        if args.r2_head_wrap_study:
            # This cap covers the fixed upper-bill root visually; its position
            # is not an output-axis or bearing design datum.
            badge_z = 526 if args.lower_beak_root_cap_study else 542
            badge_radius = 16 if args.lower_beak_root_cap_study else 11
            add(f'beak_root_badge_{side}', disk(badge_radius, 2,
                (316, side * 44, badge_z)), 'orange')
            add(f'beak_root_badge_core_{side}', disk(
                10 if args.lower_beak_root_cap_study else 7, 2,
                (316, side * 46, badge_z)), 'metal')
        else:
            add(f'beak_hinge_cap_{side}', disk(11, 2,
                (hinge_center[0], side * (38 if args.r2_internal_belt_study else 28),
                 hinge_center[2])), 'metal')
    def beak_sections(sections):
        hinge_x = 316.0
        return [(hinge_x + (x - hinge_x) * args.beak_length_factor,
                 z, half_width, half_height)
                for x, z, half_width, half_height in sections]

    # Preserve the pointed upper silhouette while lifting its inner surface
    # away from the moving lower shell. The earlier visual loft intersected
    # the closed lower shell near the tip by more than 8 cm^3.
    upper = bill(beak_sections([(320, 538, 23, 18), (342, 539, 23, 19),
                  (380, 537.5, 19, 17.5), (414, 530.5, 12, 10.5),
                  (433, 525.75, 7, 6.25), (440, 521.25, 2.5, 2.75)]), flat=True)
    add('beak_upper', upper, 'orange')
    beak_q = (math.asin(math.sin(R2_CLOSED_RAD)
                       - R2_NET_OPENING_MM / R2_CRANK_LENGTH_MM)
              if args.beak_open else R2_CLOSED_RAD)
    bill_dx = R2_CRANK_LENGTH_MM * (math.cos(beak_q) - math.cos(R2_CLOSED_RAD))
    bill_dz = R2_CRANK_LENGTH_MM * (math.sin(beak_q) - math.sin(R2_CLOSED_RAD))
    lower_rows = [(322, 509, 21, 10), (348, 509, 22, 10),
                  (382, 511, 17, 8), (417, 513, 11, 6),
                  (435, 515, 6, 3.5), (439, 516, 2, 2)]
    if args.slim_lower_bill_study:
        # Hold the pad-facing upper surface while lifting the underside.
        lower_rows = [(x, z + min(2, h - .7), w, h - min(2, h - .7))
                      for x, z, w, h in lower_rows]
    lower = bill(beak_sections(lower_rows), flat=True)
    beak_shell_sweep = []
    for trial_q in np.linspace(R2_CLOSED_RAD, math.asin(
            math.sin(R2_CLOSED_RAD) - R2_NET_OPENING_MM / R2_CRANK_LENGTH_MM), 9):
        trial_dx = R2_CRANK_LENGTH_MM * (math.cos(trial_q) - math.cos(R2_CLOSED_RAD))
        trial_dz = R2_CRANK_LENGTH_MM * (math.sin(trial_q) - math.sin(R2_CLOSED_RAD))
        intersection_mm3 = float((upper & moved(lower, (trial_dx, 0, trial_dz))).volume)
        beak_shell_sweep.append({
            'crank_angle_deg': round(math.degrees(trial_q), 4),
            'nominal_pad_opening_mm': round(-trial_dz, 4),
            'orange_shell_intersection_mm3': round(intersection_mm3, 5),
        })
        if intersection_mm3 > 0.01:
            raise ValueError('Upper and lower R2 appearance shells intersect during the opening sweep')
    add('beak_lower', moved(lower, (bill_dx, 0, bill_dz)), 'orange')
    add('beak_grip', moved(bill(beak_sections([(340, 519, 17, 1.5),
        (382, 519, 14, 1.5), (427, 520, 5, 1)]), flat=True),
        (bill_dx, 0, bill_dz)), 'black')
    add('beak_nostril', ellipsoid((4.2, 2.4, 1.4),
        (316 + (370 - 316) * args.beak_length_factor, 0, 557)), 'black')
    # The closed reference hides its linkage inside the cheek. The open pose
    # shows only the compact four-bar, without an exposed dangling fixture.
    # These are still appearance solids, not a validated R2 assembly.
    mechanism_solids = []
    if args.beak_open or args.r2_internal_belt_study:
        for side in (-1, 1):
            y = side * (20 if args.reference_head_clearance_study else
                        30 if args.r2_internal_belt_study else 18)
            fixed_a = ((298, y, 524) if args.r2_internal_belt_study else
                       (302.85, y, 524 if args.r2_geared_cheek_study else 493))
            fixed_d = (fixed_a[0], y, fixed_a[2] + R2_ANCHOR_SPACING_MM)
            moving_b = (fixed_a[0] + R2_CRANK_LENGTH_MM * math.cos(beak_q),
                        y, fixed_a[2] + R2_CRANK_LENGTH_MM * math.sin(beak_q))
            moving_c = (moving_b[0], y, moving_b[2] + R2_ANCHOR_SPACING_MM)
            for suffix, start, end in [('lower', fixed_a, moving_b), ('upper', fixed_d, moving_c)]:
                shape, _ = fairing_between(start, end, 4, 4)
                mechanism_solids.append((f'beak_link_{suffix}_{side}', shape))
                add(f'beak_link_{suffix}_{side}', shape, 'dark')
            carrier, _ = fairing_between(moving_b, moving_c, 5, 5)
            mechanism_solids.append((f'beak_moving_carrier_{side}', carrier))
            add(f'beak_moving_carrier_{side}', carrier, 'dark')
            if args.r2_internal_belt_study:
                # The raised output shaft needs a side-mounted rigid drop from
                # moving pivot B to the thin lower-bill root. Keep the drop
                # outside the fixed cheek, then bridge inward at the root.
                jaw_root = (322 + bill_dx, side * 18, 509 + bill_dz)
                jaw_root_side = (jaw_root[0], side * 18 if args.reference_head_clearance_study
                                 else side * 22 if args.r2_head_wrap_study else y,
                                 jaw_root[2])
                jaw_drop, _ = fairing_between(moving_b, jaw_root_side,
                                              8 if args.r2_head_wrap_study else 7,
                                              5 if args.r2_head_wrap_study else 4)
                mechanism_solids.append((f'beak_lower_root_carrier_{side}', jaw_drop))
                add(f'beak_lower_root_carrier_{side}', jaw_drop,
                    'dark' if args.r2_head_wrap_study else 'orange')
                root_bridge = rounded_box((8, 15, 7), 3,
                                          (jaw_root[0],
                                           side * (18 if args.reference_head_clearance_study else 24),
                                           jaw_root[2]))
                mechanism_solids.append((f'beak_lower_root_bridge_{side}', root_bridge))
                add(f'beak_lower_root_bridge_{side}', root_bridge, 'orange')
            for suffix, point in [('a', fixed_a), ('d', fixed_d), ('b', moving_b), ('c', moving_c)]:
                add(f'beak_pivot_{suffix}_{side}', disk(2.5, 5, point), 'metal')

    head_mechanism_overlap_mm3 = None
    head_mechanism_sweep_samples = None
    head_shell_solids_count = None
    if args.reference_head_clearance_study:
        # A 1 mm visual gap around the rigid upper and sampled moving lower
        # bill is a first interference check, not a tool- or print-ready fit.
        head_shape -= offset(upper, amount=1)
        lower_keepout = offset(lower, amount=1)
        for trial_q in np.linspace(R2_CLOSED_RAD, math.asin(
                math.sin(R2_CLOSED_RAD) - R2_NET_OPENING_MM / R2_CRANK_LENGTH_MM), 17):
            trial_dx = R2_CRANK_LENGTH_MM * (math.cos(trial_q) - math.cos(R2_CLOSED_RAD))
            trial_dz = R2_CRANK_LENGTH_MM * (math.sin(trial_q) - math.sin(R2_CLOSED_RAD))
            head_shape -= moved(lower_keepout, (trial_dx, 0, trial_dz))
        # The paired crank links live inboard of the orange bill root. Cut
        # their sampled motion through the nominal 2.7 mm visual shell too;
        # a later mechanical design still needs bearings, stops and fasteners.
        head_mechanism_sweep_samples = 9
        for trial_q in np.linspace(R2_CLOSED_RAD, math.asin(
                math.sin(R2_CLOSED_RAD) - R2_NET_OPENING_MM / R2_CRANK_LENGTH_MM),
                head_mechanism_sweep_samples):
            trial_dx = R2_CRANK_LENGTH_MM * (math.cos(trial_q) - math.cos(R2_CLOSED_RAD))
            trial_dz = R2_CRANK_LENGTH_MM * (math.sin(trial_q) - math.sin(R2_CLOSED_RAD))
            for side in (-1, 1):
                y = side * 20
                fixed_a = (298, y, 524)
                fixed_d = (298, y, 524 + R2_ANCHOR_SPACING_MM)
                moving_b = (298 + R2_CRANK_LENGTH_MM * math.cos(trial_q),
                            y, 524 + R2_CRANK_LENGTH_MM * math.sin(trial_q))
                moving_c = (moving_b[0], y, moving_b[2] + R2_ANCHOR_SPACING_MM)
                jaw_root_side = (322 + trial_dx, side * 18, 509 + trial_dz)
                for start, end, width, depth in (
                        (fixed_a, moving_b, 4, 4),
                        (fixed_d, moving_c, 4, 4),
                        (moving_b, moving_c, 5, 5),
                        (moving_b, jaw_root_side, 8, 5)):
                    axis = np.asarray(end) - start
                    direction = axis / np.linalg.norm(axis)
                    clearance_start = np.asarray(start) - .8 * direction
                    clearance_end = np.asarray(end) + .8 * direction
                    moving_keepout, _ = fairing_between(
                        clearance_start, clearance_end, width + 1.6, depth + 1.6)
                    head_shape -= moving_keepout
        head_mechanism_overlap_mm3 = {
            name: round(float((head_shape & shape).volume), 5)
            for name, shape in mechanism_solids
        }
        head_shell_solids_count = len(head_shape.solids())
        add('head', head_shape, 'white')

    # Visible mechanisms remain compact under broad white fairings. Wide, low
    # rounded feet retain the reference's orange/white/black color separation.
    for side in (-1, 1):
        y = side * 88
        hip = (-35, y, 287)
        knee = (-90 + args.knee_forward_shift_mm, y, 157)
        ankle = (-25, y, 51)
        shape, _ = fairing_between((hip[0] - 19, y, hip[2]),
                                   (knee[0] - 19, y, knee[2]), 23, 27)
        add(f'thigh_back_{side}', shape, 'black')
        shape, _ = fairing_between(hip, knee, 48, 42)
        add(f'thigh_{side}', shape, 'white')
        add(f'knee_{side}', disk(23, 42, knee), 'black')
        add(f'knee_rim_{side}', disk(16, 43, knee), 'metal')
        add(f'knee_accent_{side}', disk(9, 44, knee), 'orange')
        shape, _ = fairing_between((knee[0] - 18, y, knee[2]),
                                   (ankle[0] - 18, y, ankle[2]), 22, 26)
        add(f'shin_back_{side}', shape, 'black')
        shape, _ = fairing_between(knee, ankle, 43, 42)
        add(f'shin_{side}', shape, 'white')
        add(f'ankle_{side}', disk(21, 42, ankle), 'black')
        add(f'ankle_rim_{side}', disk(12, 43, ankle), 'metal')
        add(f'ankle_accent_{side}', disk(6, 44, ankle), 'orange')
        shoe_layers = ([
            ('sole', 179, 92, 11, 27, 6, 'black'),
            ('orange', 174, 87, 8, 26, 15.5, 'orange'),
            ('white', 164, 79, 14, 23, 26.5, 'white'),
        ] if args.low_profile_shell_study else [
            ('sole', 179, 92, 13, 27, 7, 'black'),
            ('orange', 174, 87, 10, 26, 18, 'orange'),
            ('white', 164, 79, 16, 23, 31, 'white'),
        ])
        for suffix, length, width, thickness, corner, center_z, color in shoe_layers:
            add(f'foot_{suffix}_{side}', shoe_layer(length + args.heel_extension_mm
                - args.foot_toe_shortening_mm,
                width, thickness, corner,
                (50 + args.foot_shift_mm - args.heel_extension_mm / 2
                 - args.foot_toe_shortening_mm / 2, y, center_z)), color)
        add(f'foot_orange_instep_{side}', moved(bill([
            (-10, 42 if args.low_profile_shell_study else 48, 2, 1),
            (5, 43 if args.low_profile_shell_study else 49, 18, 2),
            (38, 44 if args.low_profile_shell_study else 50, 23, 2),
            (65, 44 if args.low_profile_shell_study else 50, 14, 1.5),
            (71, 43 if args.low_profile_shell_study else 49, 1, 1),
        ]), (-45 + args.foot_shift_mm, y, 0)), 'orange')
        add(f'foot_orange_toe_{side}', shoe_layer(60, 50, 2, 11,
            (96 + args.foot_shift_mm - args.foot_toe_shortening_mm, y,
             35 if args.low_profile_shell_study else 40)), 'orange')
        add(f'foot_toe_tread_{side}', shoe_layer(5, 38, 1.4, 1.5,
            (103 + args.foot_shift_mm - args.foot_toe_shortening_mm, y,
             36.8 if args.low_profile_shell_study else 41.8)), 'black')

    bounds = [shape.bounding_box() for _, shape, _, _ in parts]
    bbox_min = np.min([[b.min.X, b.min.Y, b.min.Z] for b in bounds], axis=0)
    bbox_max = np.max([[b.max.X, b.max.Y, b.max.Z] for b in bounds], axis=0)
    part_boxes = {name: shape.bounding_box() for name, shape, _, _ in parts}
    export_step(Compound(children=[shape for _, shape, _, _ in parts]), args.output / 'appearance_assembly.step')
    model = ET.Element('mujoco', model='goose_exterior_study')
    ET.SubElement(model, 'compiler', angle='radian')
    visual = ET.SubElement(model, 'visual')
    ET.SubElement(visual, 'headlight', ambient='.23 .23 .23', diffuse='.65 .65 .65',
                  specular='.30 .30 .30')
    asset = ET.SubElement(model, 'asset')
    ET.SubElement(asset, 'texture', type='skybox', builtin='gradient',
                  rgb1='.94 .94 .93', rgb2='.78 .79 .79', width='512', height='3072')
    for color, rgba in COLORS.items():
        ET.SubElement(asset, 'material', name='mat_' + color, rgba=rgba,
                      specular='.65' if color in ('white', 'orange', 'lens') else '.35',
                      shininess='.65', reflectance='.04')
    for name, _, _, path in parts:
        ET.SubElement(asset, 'mesh', name=name, file=path.name, scale='.001 .001 .001')
    world = ET.SubElement(model, 'worldbody')
    ET.SubElement(world, 'light', pos='-1 -1 2', dir='.4 .4 -1', diffuse='.9 .9 .9')
    ET.SubElement(world, 'light', pos='1 1 2', dir='-.4 -.4 -1', diffuse='.5 .5 .5')
    ET.SubElement(world, 'geom', name='floor', type='plane', size='2 2 .1', rgba='.77 .77 .75 1')
    for name, _, color, _ in parts:
        ET.SubElement(world, 'geom', name=name, type='mesh', mesh=name,
                      material='mat_' + color, contype='0', conaffinity='0')
    xml = args.output / 'appearance.xml'
    ET.ElementTree(model).write(xml, encoding='unicode')
    m = mujoco.MjModel.from_xml_path(str(xml))
    m.vis.global_.offwidth = 1000
    m.vis.global_.offheight = 1000
    data = mujoco.MjData(m)
    mujoco.mj_forward(m, data)
    renderer = mujoco.Renderer(m, height=1000, width=1000)
    for view, azimuth, elevation in [('side', 90, -7), ('three_quarter', 125, -7),
                                     ('front', 180, -7), ('rear', 0, -7), ('top', 180, -86)]:
        camera = mujoco.MjvCamera()
        camera.lookat[:] = (bbox_min + bbox_max) / 2000
        camera.distance = max(bbox_max - bbox_min) / 1000 * 1.56
        camera.azimuth = azimuth
        camera.elevation = elevation
        camera.orthographic = True
        renderer.update_scene(data, camera=camera)
        Image.fromarray(renderer.render()).save(args.output / (view + '.png'))
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [
        (part_boxes['head'].min.X + part_boxes['beak_upper'].max.X) / 2000,
        0,
        (part_boxes['head'].max.Z + part_boxes['beak_lower'].min.Z) / 2000,
    ]
    camera.distance = .46
    camera.azimuth = 125
    camera.elevation = -7
    renderer.update_scene(data, camera=camera)
    Image.fromarray(renderer.render()).save(args.output / 'beak_detail.png')
    renderer.close()
    head_visual_dx = -125 - args.head_assembly_back_mm + rest_yoke_delta[0]
    head_visual_dz = (150 + vertical_profile['head_z_shift']
                      - neck_assembly_drop_mm + rest_yoke_delta[2])
    manifest = {
        'status': 'failed_appearance_study_not_manufacturing_or_physics',
        'appearance_review_pass': False,
        'appearance_revision': 'r2_pointed_beak_parametric_visual_study',
        'leg_forward_shift_mm': args.leg_forward_shift_mm,
        'knee_forward_shift_mm': args.knee_forward_shift_mm,
        'foot_shift_mm': args.foot_shift_mm,
        'heel_extension_mm': args.heel_extension_mm,
        'foot_toe_shortening_mm': args.foot_toe_shortening_mm,
        'beak_length_factor': args.beak_length_factor,
        'head_scale': args.head_scale,
        'head_assembly_back_mm': args.head_assembly_back_mm,
        'neck_rest_fold_deg': args.neck_rest_fold_deg,
        'rest_yoke_delta_mm': np.round(rest_yoke_delta, 6).tolist(),
        'vertical_compression': args.vertical_compression,
        'r2_proportions': args.r2_proportions,
        'r2_low_ankle_study': args.r2_low_ankle_study,
        'compact_body_study': args.compact_body_study,
        'compact_body_height_mm': args.compact_body_height_mm,
        'compact_body_length_mm': args.compact_body_length_mm,
        'low_profile_shell_study': args.low_profile_shell_study,
        'r2_geared_cheek_study': args.r2_geared_cheek_study,
        'r2_internal_belt_study': args.r2_internal_belt_study,
        'r2_head_wrap_study': args.r2_head_wrap_study,
        'r2_front_pocket_length_mm': (r2_front_pocket_length_mm
                                      if args.r2_head_wrap_study else None),
        'slim_lower_bill_study': args.slim_lower_bill_study,
        'integrated_camera_face_study': args.integrated_camera_face_study,
        'recessed_camera_bezel_study': args.recessed_camera_bezel_study,
        'lower_beak_root_cap_study': args.lower_beak_root_cap_study,
        'sculpted_head_study': args.sculpted_head_study,
        'helmet_head_study': args.helmet_head_study,
        'tapered_helmet_head_study': args.tapered_helmet_head_study,
        'continuous_head_cheek_study': args.continuous_head_cheek_study,
        'rear_body_crown_study': args.rear_body_crown_study,
        'lofted_body_study': args.lofted_body_study,
        'conformal_body_door_study': args.conformal_body_door_study,
        'conformal_wing_door_study': args.conformal_wing_door_study,
        'reference_torso_door_study': args.reference_torso_door_study,
        'reference_whole_proportions_study': args.reference_whole_proportions_study,
        'reference_head_clearance_study': args.reference_head_clearance_study,
        'reference_head_mechanism_overlap_mm3': head_mechanism_overlap_mm3,
        'reference_head_mechanism_sweep_samples': head_mechanism_sweep_samples,
        'reference_head_shell_solids_count': head_shell_solids_count,
        'rear_body_crown_shape_visual_mm': ({
            'center': REAR_BODY_CROWN_CENTER_MM,
            'radii': REAR_BODY_CROWN_RADII_MM,
        } if args.rear_body_crown_study else None),
        'neck_assembly_drop_mm': neck_assembly_drop_mm,
        'body_scale_xyz': ([args.compact_body_length_mm / 350, 190 / 205,
                            args.compact_body_height_mm / 230]
                           if args.compact_body_study else [1, 1, 1]),
        'vertical_profile_mm': (vertical_profile
                                if args.r2_proportions or args.r2_low_ankle_study
                                or args.vertical_compression else None),
        'beak_pose': 'parallel_open_visual_only' if args.beak_open else 'closed_visual_only',
        'beak_ideal_r2_motion': {
            'crank_length_mm': R2_CRANK_LENGTH_MM,
            'fixed_anchor_spacing_mm': R2_ANCHOR_SPACING_MM,
            'closed_crank_angle_deg': math.degrees(R2_CLOSED_RAD),
            'pose_crank_angle_deg': round(math.degrees(beak_q), 6),
            'nominal_pad_opening_mm': -round(bill_dz, 6),
            'lower_jaw_forward_shift_mm': round(bill_dx, 6),
            'source': 'robots/Goose_V0.1/design/kinematic_review.md',
            'source_sha256': hashlib.sha256(
                (root / 'robots/Goose_V0.1/design/kinematic_review.md').read_bytes()).hexdigest(),
            'status': 'ideal_visual_linkage_not_manufacturing_or_actual_pad_gap',
        },
        'beak_orange_shell_sweep': {
            'sample_count': len(beak_shell_sweep),
            'sampled_orange_shell_nonintersection': True,
            'samples': beak_shell_sweep,
            'limitations': 'Only orange upper/lower visual solids; soft pads, cranks, pins, motors, cheeks, tolerances and continuous swept volume are excluded.',
        },
        'beak_drive_package_hypothesis': ({
            'motor': 'XL330-M288-T',
            'motor_output_axis': 'visual_y',
            'fixed_output_A_visual_mm': [298 + head_visual_dx, 0,
                                         524 + head_visual_dz],
            'motor_input_axis_visual_mm': [285 + head_visual_dx, 0,
                                           559 + head_visual_dz],
            'tentative_drive': 'GT2 16T input / 32T output; 2:1; pulley and horn interface unverified',
            'gross_belt_lateral_center_visual_mm': (0 if args.reference_head_clearance_study else 20),
            'paired_four_bar_lateral_centers_visual_mm': (
                [-20, 20] if args.reference_head_clearance_study else [-30, 30]),
            'status': 'gross_visual_envelope_only_no_belt_horn_bearings_hollow_mounts_or_tensioner',
        } if args.r2_internal_belt_study else {
            'motor': 'XL330-M288-T',
            'motor_output_axis': 'visual_y',
            'fixed_output_A_visual_mm': [302.85 + head_visual_dx, 0,
                                         524 + head_visual_dz],
            'motor_input_axis_visual_mm': [round(302.85 + head_visual_dx - R2_GEAR_CENTER_MM, 3),
                                           0, 524 + head_visual_dz],
            'external_gear_module_mm': R2_GEAR_MODULE_MM,
            'input_output_teeth': [R2_INPUT_GEAR_TEETH, R2_OUTPUT_GEAR_TEETH],
            'pitch_centre_distance_mm': R2_GEAR_CENTER_MM,
            'cheek_visual_envelope_mm': {
                'min': [264 + head_visual_dx, -40, 495 + head_visual_dz],
                'max': [320 + head_visual_dx, 40, 549 + head_visual_dz]},
            'status': 'gross_visual_envelope_only_no_gears_bearings_or_hollow_mounts',
        } if args.r2_geared_cheek_study else None),
        'reference_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in references},
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'generated_part_count': len(parts),
        'coordinate_unit': 'provisional_mm',
        'visual_envelope_mm': {'min': bbox_min.round(2).tolist(),
                               'max': bbox_max.round(2).tolist(),
                               'size': (bbox_max - bbox_min).round(2).tolist()},
        'known_missing': ['functional hinges', 'camera mounting', 'internal accommodation', 'mass/inertia',
                          'whole-body motion', 'grasp load', 'print splits and fasteners'],
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'parts': len(parts)}, indent=2))


if __name__ == '__main__':
    main()
