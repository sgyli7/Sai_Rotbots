"""Verify colour-review artifacts without granting appearance/manufacturing approval.

The --reviewed arguments attest to a person's actual image inspection; PNG
statistics alone do not establish that a render looks good or is manufacturable.
"""
import argparse
import fnmatch
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robot-root', type=Path, required=True)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--snapshot-root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--renderer', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--document', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reviewed', action='append', default=[], help='Filename actually inspected')
    args = parser.parse_args()
    robot = args.robot_root.resolve()
    source, config, manifest = load(args.scene), load(args.config), load(args.manifest)
    source_hash = sha256(args.scene)
    check(source_hash == config['source_scene_sha256'] == manifest['source_scene_sha256'], 'Source identity mismatch')
    check(sha256(args.config) == manifest['config_sha256'], 'Configuration changed after render')
    check(sha256(args.renderer) == manifest['renderer_sha256'], 'Renderer changed after render')
    check(sha256(args.snapshot_root / 'scene.json') == source_hash, 'Frozen scene differs from canonical source')
    check(not manifest['physical_model_changed'] and not manifest['manufacturing_release'], 'Review cannot release manufacturing')
    check(manifest['geometry_modifiers_created'] == 0, 'Unexpected geometry modifier')
    check(manifest['source_guard']['expected_sha256'] == source_hash and manifest['source_guard']['abort_on_change'], 'Missing source guard')
    names = {part['name']: part for part in source['parts']}
    check(len(names) == len(source['parts']), 'Duplicate source part names')
    actual_roles = {row['name']: row['color_role'] for row in manifest['source_parts']}
    check(set(actual_roles) == set(names), 'Manifest part list differs from source')
    geometry_counts = {'parts': len(names), 'vertices': 0, 'quads': 0}
    external_files = 0
    for part in source['parts']:
        role = config['material_roles'][part['material']]
        for override in config['part_role_overrides']:
            if fnmatch.fnmatchcase(part['name'], override['pattern']):
                role = override['role']
        check(actual_roles[part['name']] == role, f"Wrong role: {part['name']}")
        if 'geometry_npz' in part:
            relative = Path(part['geometry_npz'])
            live = (robot / relative).resolve()
            frozen = (args.snapshot_root / relative).resolve()
            check(live.is_relative_to(robot) and frozen.is_relative_to(args.snapshot_root.resolve()), 'Geometry path escapes root')
            check(sha256(live) == sha256(frozen) == part['source_sha256'], f"Geometry hash changed: {part['name']}")
            with np.load(frozen, allow_pickle=False) as data:
                vertices, faces = data['vertices'], data['faces']
                check(vertices.ndim == 2 and vertices.shape[1] == 3 and np.isfinite(vertices).all(), 'Invalid source vertices')
                check(faces.ndim == 2 and faces.shape[1] == 4 and faces.size > 0, 'Source is not all quad')
                geometry_counts['vertices'] += len(vertices)
                geometry_counts['quads'] += len(faces)
            external_files += 1
        else:
            check(all(len(face) == 4 for face in part['faces']), 'Inline source is not all quad')
            geometry_counts['vertices'] += len(part['vertices'])
            geometry_counts['quads'] += len(part['faces'])
    check(geometry_counts == manifest['geometry_counts'], 'Manifest geometry counts differ from source')
    normal_bindings = []
    for name, field in config.get('display_normal_fields', {}).items():
        path = robot / field['path']
        check(sha256(path) == field['sha256'] and names[name]['source_sha256'] == field['geometry_sha256'], 'Display normal binding changed')
        check(sha256(args.snapshot_root / field['path']) == field['sha256'], 'Frozen display normal differs')
        normal_bindings.append({'name': name, 'geometry_sha256': field['geometry_sha256'], 'field_sha256': field['sha256']})
    check({r['scheme'] for r in manifest['renders']} == {'cream', 'graphite', 'lavender', 'sky'} and len(manifest['renders']) == 4, 'Four whole views required')
    records = manifest['renders'] + manifest.get('review_details', [])
    check(len(records) == 5 and records[-1].get('view') == 'head_detail', 'Cream head detail required')
    images = []
    for row in records:
        check(row['geometry_fingerprint'] == manifest['geometry_fingerprint'] and row['source_scene_sha256'] == source_hash, 'Mixed render source')
        path = args.images / row['file']
        check(sha256(path) == row['sha256'], 'Render PNG changed')
        with Image.open(path) as image:
            check(image.size == (1200, 1200), 'Wrong image resolution')
            stats = ImageStat.Stat(image.convert('RGB'))
            check(min(stats.stddev) > 1, 'Blank image')
            images.append({'scheme': row['scheme'], 'view': row.get('view', 'whole'), 'file': row['file'], 'sha256': row['sha256'], 'width': image.width, 'height': image.height, 'rgb_standard_deviation': stats.stddev, 'actual_pixels_inspected': row['file'] in args.reviewed})
    check(all(row['actual_pixels_inspected'] for row in images), 'Each final image must be actually inspected')
    historical_integrity = []
    histories = [
        (419, 'microduck_color_blocking_419_parts', 'microduck_color_blocking_419_parts_render_manifest.json', 'render_goose_color_blocking_419_parts.py'),
        (344, 'microduck_color_blocking_344_parts', 'microduck_color_blocking_344_parts_render_manifest.json', 'render_goose_color_blocking_344_parts.py'),
        (314, 'microduck_color_blocking_314_parts', 'microduck_color_blocking_314_parts_render_manifest.json', 'render_goose_color_blocking_current.py'),
        (292, 'microduck_color_blocking', 'microduck_color_blocking_render_manifest.json', 'render_goose_color_blocking.py'),
        ('first_rejected', 'microduck_color_schemes', 'microduck_color_scheme_render_manifest.json', 'render_goose_color_schemes.py'),
    ]
    for version, image_dir, evidence_file, script in histories:
        historic = load(robot / 'evidence' / evidence_file)
        config_name = 'color_schemes.json' if version == 'first_rejected' else image_dir + '.json'
        check(sha256(robot / 'configs' / config_name) == historic['config_sha256'], f'Historical configuration changed: {version}')
        check(sha256(robot.parent.parent / 'scripts/models' / script) == historic['renderer_sha256'], f'Historical renderer changed: {version}')
        for row in historic['renders']:
            check(sha256(robot / 'images' / image_dir / row['file']) == row['sha256'], f'Historical image changed: {version}')
        historical_integrity.append({'version': version, 'config_script_four_png_hashes_preserved': True})
    local_links = []
    for target in re.findall(r'\]\(([^)]+)\)', args.document.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        path = (args.document.parent / target.split('#')[0]).resolve()
        exists = path.exists() or path == args.report.resolve()
        check(exists, f'Missing local document link: {target}')
        local_links.append({'link': target, 'exists': exists})
    references = {name: {'source_role': names[name].get('role'), 'color_role': actual_roles[name]} for name in config.get('reference_parts', {})}
    for name, row in references.items():
        check(row['source_role'] == 'vendor_dimension_display_reference_not_printable', f'OEM display reference mislabeled: {name}')
    report = {
        'schema_version': 1, 'robot_id': 'Goose_V0.1', 'status': 'color_candidate_actual_render_inspected_user_appearance_acceptance_pending',
        'source_scene_sha256': source_hash, 'config_sha256': sha256(args.config), 'renderer_sha256': sha256(args.renderer), 'render_manifest_sha256': sha256(args.manifest),
        'geometry_fingerprint': manifest['geometry_fingerprint'], 'geometry_counts': geometry_counts, 'external_geometry_hashes_verified': external_files,
        'all_four_same_geometry_source_and_camera': True, 'head_detail_same_geometry_separate_camera': True, 'geometry_modifiers_created': 0,
        'semantic_roles_verified': actual_roles, 'normal_field_geometry_bindings_verified': normal_bindings, 'reference_parts_verified': references,
        'images': images, 'historical_integrity': historical_integrity, 'local_links_verified': local_links,
        'physical_model_changed_by_palette_task': False, 'manufacturing_release': False, 'appearance_accepted_by_user': False,
        'limitations': ['Actual pixel inspection is colour review, not an engineering or aesthetic release.', 'Body display normals approximate existing profile derivatives; they cannot certify native CAD surface quality or manufacture.', 'OEM camera references are dimensional displays, not printable parts or full vendor optical CAD.', 'No modifier, substitute glass, aperture cover or additional placement change hides source geometry.', 'Accent colours are photo-informed adaptation, not calibrated filament/paint specifications; coating mass is outside the mechanical ledger.'],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'report': str(args.report), 'source_scene_sha256': source_hash, 'geometry_counts': geometry_counts, 'all_five_actually_inspected': True}))


if __name__ == '__main__':
    main()
