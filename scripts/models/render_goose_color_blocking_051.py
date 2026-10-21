"""Rebalance MicroDuck colours on the unchanged frozen15 assembly.

Named native covers and surface paint carry colour; no geometry or physical
asset is edited. The local primitive cache is only a disposable render input.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import pickle
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render_goose_homepage_colorways_050 as base
from render_goose_reference_camera import Rasterizer, load_glb, render

ROOT = base.ROOT
RAW = ROOT / 'artifacts/goose_v0_2/appearance_color_blocking_051'
OUTPUT = ROOT / 'robots/goose_v0_2/images/appearance_color_blocking_051'
CONFIG = ROOT / 'robots/goose_v0_2/configs/appearance_color_blocking_051.json'
EVIDENCE = ROOT / 'robots/goose_v0_2/evidence/appearance_color_blocking_051.json'


def load_current():
    binding = json.loads(base.BINDING.read_text())
    head = json.loads(base.HEAD.read_text())
    scene = Path(binding['scene']['path'])
    assert base.sha(scene) == binding['scene']['sha256']
    assert base.sha(base.MODEL) == '41ee30e7eeb004986daa9ee55d67c4ae74b638615bb2c29f6dcc3c314197df89'
    cache = RAW / 'current_primitives.pkl'
    if cache.exists():
        with cache.open('rb') as f:
            parts = pickle.load(f)
    else:
        parts = [p for p in load_glb(scene.read_bytes()) if p['name'] not in head['retired']]
        for i, p in enumerate(load_glb((base.RAW / 'native15_replacements.glb').read_bytes())):
            c = p['colours'].mean(axis=0)
            p['name'] = f'native15_{"bill" if c[0] > .9 and c[1] < .7 else "metal"}_{i}'
            parts.append(p)
    expected = set(binding['occurrence_owners']) - set(head['retired'])
    assert {p['name'] for p in parts if not p['name'].startswith('native15_')} == expected
    return parts, binding, head


def region_role(p, study):
    name = p['name']
    if name in {'front_main_shell', 'rear_service_cap'}:
        return 'shell'
    if 'integrated_clamshell' in name:
        return 'structural_dark' if study == 'classic' or '_rear_' in name else 'neutral_panel'
    if name.startswith(('head_pitch_joint_', 'neck_yaw_root_')) and name.endswith('_hood'):
        return 'structural_dark'
    if 'structural_thigh_primary_shell' in name or 'structural_shin_primary_shell' in name:
        return 'neutral_panel' if study == 'layered' else 'structural_dark'
    if 'AP_' in name and 'coaxial_service_shell' in name:
        return 'structural_dark'
    if 'ankle_' in name and 'bearing_cover' in name:
        return 'structural_dark'
    if 'foot_' in name and 'saddle' in name and not any(k in name for k in ['screw', 'washer', 'M3', 'm3']):
        return 'structural_dark'
    if 'bearing_outer_retainer' in name:
        return 'structural_dark'
    return base.role(p)


def refine_paint_surface(p):
    """Subdivide planar display triangles for curved finish boundaries only."""
    v, n = p['vertices'][p['indices']], p['normals'][p['indices']]
    for _ in range(9):
        edge = np.linalg.norm(v - np.roll(v, 1, axis=1), axis=2).max(axis=1)
        split = edge > 7
        if not split.any():
            break
        a, b, c = (v[split, i] for i in range(3))
        an, bn, cn = (n[split, i] for i in range(3))
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        abn, bcn, can = (an + bn) / 2, (bn + cn) / 2, (cn + an) / 2
        v = np.concatenate([v[~split], np.stack([a, ab, ca], 1), np.stack([ab, b, bc], 1),
                            np.stack([ca, bc, c], 1), np.stack([ab, bc, ca], 1)])
        n = np.concatenate([n[~split], np.stack([an, abn, can], 1), np.stack([abn, bn, bcn], 1),
                            np.stack([can, bcn, cn], 1), np.stack([abn, bcn, can], 1)])
    return dict(p, vertices=v.reshape(-1, 3), normals=n.reshape(-1, 3),
                indices=np.arange(v.size // 3, dtype=np.uint32).reshape(-1, 3))


def partition_finish(p, field):
    """Cut triangles at a paint boundary, preserving their original surface."""
    vertices, normals, ix = p['vertices'], p['normals'], p['indices']
    values = field(vertices)
    pieces = []
    for inside in [True, False]:
        all_in = (values[ix] <= 0).all(axis=1) if inside else (values[ix] >= 0).all(axis=1)
        all_out = (values[ix] > 0).all(axis=1) if inside else (values[ix] < 0).all(axis=1)
        v, n = [vertices[ix[all_in]].reshape(-1, 3)], [normals[ix[all_in]].reshape(-1, 3)]
        for face in ix[~(all_in | all_out)]:
            polygon = [(vertices[j], normals[j], values[j]) for j in face]
            clipped = []
            for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                ain = a[2] <= 0 if inside else a[2] >= 0
                bin = b[2] <= 0 if inside else b[2] >= 0
                if ain:
                    clipped.append(a)
                if ain != bin:
                    u = a[2] / (a[2] - b[2])
                    clipped.append((a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]), 0))
            for j in range(1, len(clipped) - 1):
                tri = [clipped[0], clipped[j], clipped[j + 1]]
                v.append(np.array([x[0] for x in tri]))
                n.append(np.array([x[1] for x in tri]))
        vs, ns = np.concatenate(v), np.concatenate(n)
        pieces.append(dict(p, vertices=vs, normals=ns,
                           indices=np.arange(len(vs), dtype=np.uint32).reshape(-1, 3)))
    return pieces


def surface_area(p):
    v = p['vertices'][p['indices']]
    return float(np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1).sum() / 2)


def paint(parts, study):
    painted, sole_records = [], []
    for source in parts:
        p = dict(source, colour_role=region_role(source, study))
        name = p['name']
        if name.endswith('flat_rounded_sole'):
            pieces, record = base.split_sole(p)
            painted.extend(pieces)
            sole_records.append(record)
        elif any(k in name for k in ['visible_thigh_HP_small_service_cap', 'visible_shin_K_small_service_cap']):
            painted.extend(base.split_service_cap(p))
        elif name in {'front_main_shell', 'rear_service_cap'}:
            # Existing exterior triangles only: a continuous saddle, gray belly,
            # and a soft wing-shaped side patch. These are finish boundaries,
            # not fabricated service doors or new mechanical seams.
            refined = refine_paint_surface(p)
            belly, upper = partition_finish(refined, lambda v: v[:, 2] - (278 + .05 * (v[:, 0] + 243)))
            wing, saddle = partition_finish(upper, lambda v: np.maximum(
                ((v[:, 0] + 137) / 82) ** 2 + ((v[:, 2] - 350) / 33) ** 2 - 1,
                (60 - np.abs(v[:, 1])) / 60))
            pieces = [dict(belly, colour_role='neutral_panel'), dict(wing, colour_role='neutral_panel'),
                      dict(saddle, colour_role='shell')]
            assert abs(sum(surface_area(q) for q in pieces) - surface_area(p)) < surface_area(p) * 1e-9
            painted.extend(q for q in pieces if len(q['indices']))
        else:
            painted.append(p)
    return painted, sole_records


def camera(view, size):
    if view == 'front':
        rows = 1.30 * np.array([[0., 1., 0.], [.05, 0., -np.sqrt(.9975)]])
    elif view == 'side':
        rows = 1.30 * np.array([[1., 0., 0.], [0., 0., -1.]])
    else:
        rows = 1.30 * np.array([[.8, .6, 0.], [.18, -.24, -np.sqrt(.91)]])
    matrix = np.column_stack([rows, np.array(size) / 2 - rows @ [25., 0., 350.]])
    return {'kind': 'orthographic', 'viewport_px': size, 'matrix_2x4': matrix.tolist()}


def board(paths, labels, dest, columns):
    width, height = Image.open(paths[0]).size
    margin, heading = 24, 70
    canvas = Image.new('RGB', (columns * width, ((len(paths) + columns - 1) // columns) * (height + heading)), '#f8f8f8')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 26)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    for i, (path, label) in enumerate(zip(paths, labels)):
        x, y = (i % columns) * width, (i // columns) * (height + heading)
        canvas.paste(Image.open(path), (x, y + heading))
        draw.text((x + margin, y + 12), label, font=font, fill='#28313a')
        draw.text((x + margin, y + 44), 'Same frozen15 geometry / surface finishes only', font=small, fill='#737d84')
    canvas.save(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--study', action='store_true')
    ap.add_argument('--selected', choices=['classic', 'layered', 'balanced'], default='balanced')
    args = ap.parse_args()
    parts, binding, head = load_current()
    palette = json.loads(base.PALETTE.read_text())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    size = [1000, 1100]
    jobs = [('classic', 'sky', 'oblique'), ('layered', 'sky', 'oblique')] if args.study else [
        (args.selected, s['id'], 'oblique') for s in palette['schemes']]
    if not args.study:
        jobs += [(args.selected, 'sky', view) for view in ['front', 'side']]
    receipt = {'physical_model': base.reference(base.MODEL), 'head': base.reference(base.HEAD),
               'body': binding['scene'], 'palette': base.reference(base.PALETTE),
               'source': base.reference(Path(__file__)), 'geometry_or_physics_changes': False,
               'native_occurrences': len(binding['occurrence_owners']) - len(head['retired']) + len(head['new_parts']),
               'physics_steps': 0, 'selected_distribution': args.selected, 'images': []}
    with tempfile.TemporaryDirectory(prefix='goose-colour-051-') as temp:
        raster = Rasterizer(temp)
        for study, scheme_id, view in jobs:
            scheme = next(s for s in palette['schemes'] if s['id'] == scheme_id)
            specs = {**palette['common_materials'], **scheme['materials']}
            painted, sole = paint(parts, study)
            for p in painted:
                p['colours'] = np.broadcast_to(base.linear(specs[p['colour_role']]), p['vertices'].shape)
            image, metrics, _ = render(painted, camera(view, size), *size, 2, .1, raster)
            path = (RAW / (study + '.png')) if args.study else OUTPUT / (scheme_id + ('' if view == 'oblique' else '_' + view) + '.png')
            image.save(path)
            receipt['images'].append({'study': study, 'scheme': scheme_id, 'view': view,
                                      **base.reference(path), 'colour_roles': dict(Counter(p['colour_role'] for p in painted)),
                                      'triangles': metrics['triangles_submitted'], 'sole_surface_partition': sole})
            print(json.dumps({'rendered': str(path)}), flush=True)
    if args.study:
        board([ROOT / r['path'] for r in receipt['images']], ['A / MicroDuck dark mechanics', 'B / Two-tone covers'], RAW / 'distribution_studies.png', 2)
        return
    board([OUTPUT / (s['id'] + '.png') for s in palette['schemes']],
          [s['label'] + ' / Goose V0.2' for s in palette['schemes']], OUTPUT / 'four_colorways.png', 2)
    board([ROOT / 'robots/goose_v0_2/images/homepage_colorways_050/sky.png', OUTPUT / 'sky.png'],
          ['Before / uniform covers', 'Revised / MicroDuck colour hierarchy'], OUTPUT / 'sky_before_after.png', 2)
    board([OUTPUT / 'sky_front.png', OUTPUT / 'sky_side.png', OUTPUT / 'sky.png'],
          ['Front', 'Right side', 'Three-quarter'], OUTPUT / 'sky_three_views.png', 3)
    CONFIG.write_text(json.dumps({'robot_id': 'goose_v0_2', 'palette_source': str(base.PALETTE.relative_to(ROOT)),
                                'selected_distribution': args.selected,
                                'zones': {'body_and_head': 'scheme.shell', 'neck_front': 'structural_dark' if args.selected == 'classic' else 'neutral_panel',
                                          'neck_rear': 'structural_dark', 'leg_primary_covers': 'neutral_panel' if args.selected == 'layered' else 'structural_dark',
                                          'belly_wing_joint_cap_faces': 'neutral_panel', 'bill_and_shoes': 'scheme.accent',
                                          'sole_band_and_joint_cap_rim': 'scheme.secondary_accent', 'camera_ring': 'scheme.eye_ring'},
                                'surface_finish_only': True,
                                'wing_patch': 'Paint on existing shell; not a service door, recess or structural component'}, indent=2) + '\n')
    receipt['config'] = base.reference(CONFIG)
    for name in ['four_colorways', 'sky_before_after', 'sky_three_views']:
        receipt[name] = base.reference(OUTPUT / (name + '.png'))
    EVIDENCE.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
