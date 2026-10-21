"""Render frozen15 on the retained08 native body, using the exact V0.1 palette.

Only appearance output is written. The native replacement list, placements and
physical package stay immutable. --prepare-native needs the pinned CAD Python;
normal rendering uses the repository's existing CPU triangle renderer.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'artifacts/goose_v0_2/homepage_colorways_050'
OUTPUT = ROOT / 'robots/goose_v0_2/images/homepage_colorways_050'
EVIDENCE = ROOT / 'robots/goose_v0_2/evidence/homepage_colorways_050.json'
PALETTE = ROOT / 'robots/Goose_V0.1/configs/microduck_color_blocking_manual_wing_service.json'
HEAD = ROOT / 'robots/goose_v0_2/cad/exports/full_native_head_integration_026/r12_preload048_review/merged_native_manifest.json'
BINDING = ROOT / 'robots/goose_v0_2/evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json'
MODEL = ROOT / 'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/manifest.json'


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def reference(path):
    return {'path': str(Path(path).relative_to(ROOT)), 'sha256': sha(path)}


def linear(spec):
    if 'linear_rgb' in spec:
        return np.array(spec['linear_rgb'])
    x = np.array([int(spec['srgb_hex'][i:i + 2], 16) / 255 for i in (1, 3, 5)])
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def prepare_native():
    from cadgen import build123d as b, read_step
    head = json.loads(HEAD.read_text())
    shapes = []
    for part in head['new_parts']:
        source = ROOT / part['source']['path']
        assert sha(source) == part['source']['sha256'], source
        assert part['rotation_xyz_deg'] == [0, 0, 0]
        pose = head['poses']['closed'][part['body']]
        assert pose['rotation_y_deg'] == 0 and pose['translation_mm'] == [0, 0, 0]
        shape = read_step(str(source)).translate(tuple(part['translation_to_zero_mm']))
        shape.label = part['name']
        shape.color = b.Color(1, .46, .045) if 'grip_shell' in part['name'] else b.Color(.64, .68, .73)
        shapes.append(shape)
    RAW.mkdir(parents=True, exist_ok=True)
    b.export_step(b.Compound(children=shapes), str(RAW / 'native15_replacements.step'))
    print(json.dumps({'prepared_actual_replacements': len(shapes), 'head_manifest': reference(HEAD)}), flush=True)


def role(p):
    name = p['name']
    if name.startswith('native15_bill_'):
        return 'accent'
    if name.startswith('native15_metal_'):
        return 'metal_connector'
    if name == 'camera_open_eye_bezel':
        return 'eye_ring'
    if name == 'camera_fastened_open_face':
        return 'faceplate'
    if name == 'rear_service_cap':
        return 'neutral_panel'
    if name.endswith('flat_rounded_sole') or 'grip_cassette_pad' in name:
        return 'rubber'
    if 'integrated_AR_shoe_crown' in name:
        return 'accent'
    if ('bearing_outer_retainer' in name or 'ankle_pitch_bearing_cover' in name):
        return 'secondary_accent'
    if (name in {'front_main_shell', 'head_integral_print_shell'} or
            ('shell' in name and not any(x in name for x in ['screw', 'washer'])) or
            ('hood' in name and not any(x in name for x in ['screw', 'tube', 'sleeve', 'washer']))):
        return 'shell'
    material = p.get('material_name') or ''
    return {'ivory': 'structural_dark', 'orange': 'accent', 'rubber': 'rubber',
            'sole': 'rubber', 'core': 'mechanism', 'graphite': 'mechanism',
            'reference_neck_core': 'mechanism', 'glass': 'glass', 'lens': 'lens',
            'seam': 'seam', 'pcb': 'pcb_reference', 'pcb_reference': 'pcb_reference'
            }.get(material, 'metal_connector')


def split_sole(p):
    """Surface paint split only: original triangles are partitioned, never offset.

    The existing rubber sole receives a thin upper colour band and black tread.
    No new physical trim, extra thickness, or collision geometry is introduced.
    """
    z = p['vertices'][:, 2]
    plane = float(z.min() + .60 * np.ptp(z))
    result = []
    old_area = float(np.linalg.norm(np.cross(
        p['vertices'][p['indices'][:, 1]] - p['vertices'][p['indices'][:, 0]],
        p['vertices'][p['indices'][:, 2]] - p['vertices'][p['indices'][:, 0]]), axis=1).sum() / 2)
    new_area = 0.
    for upper in [False, True]:
        vs, ns = [], []
        for face in p['indices']:
            polygon = [(p['vertices'][i].copy(), p['normals'][i].copy()) for i in face]
            clipped = []
            for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                ain = a[0][2] >= plane if upper else a[0][2] <= plane
                bin = b[0][2] >= plane if upper else b[0][2] <= plane
                if ain:
                    clipped.append(a)
                if ain != bin:
                    u = (plane - a[0][2]) / (b[0][2] - a[0][2])
                    clipped.append((a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])))
            for i in range(1, len(clipped) - 1):
                for v, n in [clipped[0], clipped[i], clipped[i + 1]]:
                    vs.append(v)
                    ns.append(n)
        v, n = np.array(vs), np.array(ns)
        ind = np.arange(len(v), dtype=np.uint32).reshape(-1, 3)
        area = float(np.linalg.norm(np.cross(v[ind[:, 1]] - v[ind[:, 0]], v[ind[:, 2]] - v[ind[:, 0]]), axis=1).sum() / 2)
        new_area += area
        q = dict(p, vertices=v, normals=n, indices=ind, colour_role='secondary_accent' if upper else 'rubber')
        result.append(q)
    assert abs(new_area - old_area) <= max(1e-7, old_area * 1e-10)
    return result, {'name': p['name'], 'upper_paint_boundary_z_mm': plane,
                    'original_surface_area_mm2': old_area, 'paint_partition_surface_area_mm2': new_area,
                    'added_geometry_or_thickness': False}


def split_service_cap(p):
    """Colour the existing cap's side/chamfer; keep its front neutral gray."""
    v, ix = p['vertices'], p['indices']
    normal = np.cross(v[ix[:, 1]] - v[ix[:, 0]], v[ix[:, 2]] - v[ix[:, 0]])
    length = np.linalg.norm(normal, axis=1)
    is_rim = np.abs(normal[:, 1]) < .95 * length
    pieces = []
    for mask, colour_role in [(is_rim, 'secondary_accent'), (~is_rim, 'neutral_panel')]:
        if mask.any():
            pieces.append(dict(p, indices=ix[mask], colour_role=colour_role))
    assert sum(len(q['indices']) for q in pieces) == len(ix)
    return pieces


def render_all():
    from PIL import Image, ImageDraw
    from render_goose_reference_camera import load_glb, render, Rasterizer

    palette = json.loads(PALETTE.read_text())
    head = json.loads(HEAD.read_text())
    binding = json.loads(BINDING.read_text())
    scene = Path(binding['scene']['path'])
    assert sha(scene) == binding['scene']['sha256']
    assert sha(MODEL) == '41ee30e7eeb004986daa9ee55d67c4ae74b638615bb2c29f6dcc3c314197df89'
    original = load_glb(scene.read_bytes())
    names = {p['name'] for p in original}
    assert names == set(binding['occurrence_owners']) and set(head['retired']) <= names
    primitives = [p for p in original if p['name'] not in head['retired']]
    additions = load_glb((RAW / 'native15_replacements.glb').read_bytes())
    for i, p in enumerate(additions):
        c = np.mean(p['colours'], axis=0)
        is_bill = c[0] > .9 and c[1] < .7
        p['name'] = f'native15_{"bill" if is_bill else "metal"}_{i}'
        primitives.append(p)
    assert len(additions) == 2, 'Expected actual replacement shells and metal groups'
    for p in primitives:
        p['colour_role'] = role(p)
    painted, sole_records = [], []
    for p in primitives:
        if p['name'].endswith('flat_rounded_sole'):
            pieces, receipt = split_sole(p)
            painted.extend(pieces)
            sole_records.append(receipt)
        elif any(k in p['name'] for k in ['visible_thigh_HP_small_service_cap', 'visible_shin_K_small_service_cap']):
            painted.extend(split_service_cap(p))
        else:
            painted.append(p)
    roles = Counter(p['colour_role'] for p in painted)
    for required in ['shell', 'accent', 'secondary_accent', 'eye_ring', 'neutral_panel', 'faceplate', 'rubber', 'mechanism']:
        assert roles[required] > 0, required
    OUTPUT.mkdir(parents=True, exist_ok=True)
    size = [1000, 1100]
    rows = 1.30 * np.array([[.8, .6, 0.], [.18, -.24, -np.sqrt(.91)]])
    matrix = np.column_stack([rows, np.array(size) / 2 - rows @ [25., 0., 350.]])
    camera = {'kind': 'orthographic', 'viewport_px': size, 'matrix_2x4': matrix.tolist()}
    evidence = {'palette': reference(PALETTE), 'same_scheme_and_common_materials_as_v01': True,
                'physical_model': reference(MODEL), 'native_head15': reference(HEAD),
                'parent_body_display': reference(scene), 'parent_binding': reference(BINDING),
                'native_replacement_STEP': reference(RAW / 'native15_replacements.step'),
                'native_replacement_mesh': reference(RAW / 'native15_replacements.glb'),
                'native_replacement_mesh_export': 'cadgen0.7.21; mesh-tolerance0.001; angular0.25; explicit original source placements',
                'source': reference(Path(__file__)), 'retired_occurrences': head['retired'],
                'actual_added_native_occurrences': len(head['new_parts']),
                'native_display_occurrences': len(names) - len(head['retired']) + len(head['new_parts']),
                'required_colour_role_counts': dict(roles), 'sole_surface_paint': sole_records,
                'joint_trim': 'Secondary-colour side/chamfer of existing hip/knee service caps; gray front, unchanged triangles, no extra ring geometry',
                'camera': camera, 'physics_steps': 0, 'CAD_MCI_collision_actuation_unchanged': True,
                'images': [], 'source_label': 'Actual retained08 body plus actual frozen15 replacements, closed nominal pose'}
    with tempfile.TemporaryDirectory(prefix='goose-colour-raster-') as temp:
        raster = Rasterizer(temp)
        for scheme in palette['schemes']:
            specs = {**palette['common_materials'], **scheme['materials']}
            for p in painted:
                p['colours'] = np.broadcast_to(linear(specs[p['colour_role']]), p['vertices'].shape)
            image, metrics, _ = render(painted, camera, *size, 1, .1, raster)
            dest = OUTPUT / (scheme['id'] + '.png')
            image.save(dest)
            evidence['images'].append({'scheme': scheme['id'], **reference(dest), 'size': size,
                                       'triangles_submitted': metrics['triangles_submitted']})
            print(json.dumps({'rendered': scheme['id'], 'path': str(dest)}), flush=True)
    board = Image.new('RGB', (2000, 2290), '#f8f8f8')
    draw = ImageDraw.Draw(board)
    for i, scheme in enumerate(palette['schemes']):
        xy = (i % 2 * 1000, i // 2 * 1145)
        board.paste(Image.open(OUTPUT / (scheme['id'] + '.png')), (xy[0], xy[1] + 35))
        draw.text((xy[0] + 30, xy[1] + 12), scheme['label'] + ' | Goose V0.2 frozen15', fill='#313942')
    board.save(OUTPUT / 'four_colorways.png')
    evidence['board'] = reference(OUTPUT / 'four_colorways.png')
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare-native', action='store_true')
    args = ap.parse_args()
    prepare_native() if args.prepare_native else render_all()
