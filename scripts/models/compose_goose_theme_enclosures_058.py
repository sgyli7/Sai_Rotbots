"""Archive and compare the four existing 058 renders without rerendering."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import PIL
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'artifacts/goose_v0_2/theme_enclosure_study_058'
IMAGES = ROOT / 'robots/goose_v0_2/images/theme_enclosure_study_058'
EVIDENCE = ROOT / 'robots/goose_v0_2/evidence/theme_enclosure_study_058'
CONFIG = ROOT / 'robots/goose_v0_2/configs/enclosure_theme_finish_058.json'
WRAPPER = ROOT / 'scripts/models/render_goose_theme_enclosures_058.py'
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
SCHEMES = ('cream', 'sky', 'lavender', 'graphite')


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def reference(path: Path) -> dict:
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
            'bytes': path.stat().st_size}


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text())
    overrides = config['whole_part_role_overrides']
    assert len(overrides) == 11 and set(overrides.values()) == {'shell'}
    assert sha(ROOT / config['base_renderer']['path']) == config['base_renderer']['sha256']
    assert sha(ROOT / config['assembly_manifest']['path']) == config['assembly_manifest']['sha256']

    archive, audits, receipts, baselines = [], [], [], []
    checked_inputs = {}

    def verify_input(item: dict) -> None:
        path = ROOT / item['path']
        key = str(path.relative_to(ROOT))
        if key not in checked_inputs:
            actual = reference(path)
            assert actual['sha256'] == item['sha256'], key
            checked_inputs[key] = actual
        else:
            assert checked_inputs[key]['sha256'] == item['sha256'], key

    for scheme in SCHEMES:
        src_image = RAW / scheme / f'{scheme}_oblique.png'
        src_receipt = RAW / scheme / f'{scheme}_render_receipt.json'
        receipt = json.loads(src_receipt.read_text())
        baseline_path = ROOT / f'robots/goose_v0_2/images/enclosure_refinement_056/{scheme}_render_receipt.json'
        baseline = json.loads(baseline_path.read_text())
        assert receipt['colorway'] == scheme
        assert receipt['display_objects'] == 1944
        assert receipt['omitted_objects'] == [] and not receipt['hardware_geometry_hidden']
        assert receipt['geometry_modifiers'] == receipt['physics_steps'] == 0
        assert receipt['new_colour_boundary_geometry'] == receipt['face_colour_partitions'] == 0
        assert receipt['identity_status'] == 'SOURCE_BOUND_NATIVE_ASSEMBLY'
        assert receipt['source_sha256'] == baseline['source_sha256']
        assert receipt['source_bound_meshes'] == baseline['source_bound_meshes']
        assert receipt['assembly_binding'] == baseline['assembly_binding']
        assert receipt['palette_sha256'] == baseline['palette_sha256']
        assert len(receipt['source_bound_meshes']) == 1944
        assert len(receipt['views']) == 1 and receipt['views'][0]['view'] == 'oblique'
        assert receipt['views'][0]['sha256'] == sha(src_image)
        current = {r['part']: r['finish'] for r in receipt['whole_part_finish_bindings']}
        previous = {r['part']: r['finish'] for r in baseline['whole_part_finish_bindings']}
        assert len(current) == len(previous) == 1944 and current.keys() == previous.keys()
        changes = [{'part': name, 'before': previous[name], 'after': current[name]}
                   for name in current if current[name] != previous[name]]
        assert {r['part'] for r in changes} == overrides.keys()
        assert all(r['before'] == 'structural_dark' and r['after'] == 'shell' for r in changes)
        extension = receipt['renderer_extension']
        assert extension['whole_part_role_overrides'] == overrides
        assert extension['sha256'] == sha(WRAPPER)
        assert extension['config']['sha256'] == sha(CONFIG)
        for item in receipt['assembly_binding'].values():
            if isinstance(item, dict) and 'path' in item:
                verify_input(item)
        verify_input({'path': receipt['palette_source'], 'sha256': receipt['palette_sha256']})
        for mesh in receipt['source_bound_meshes']:
            item = mesh['native_source']
            verify_input(item.get('input', item))
        for source, target in ((src_image, IMAGES / src_image.name),
                               (src_receipt, EVIDENCE / src_receipt.name)):
            before = sha(source)
            shutil.copyfile(source, target)
            assert sha(source) == before == sha(target)
            archive.append({'original': reference(source), 'archived': reference(target),
                            'byte_identical': True})
        audits.append({'scheme': scheme, 'baseline_receipt': reference(baseline_path),
                       'archived_receipt': reference(EVIDENCE / src_receipt.name),
                       'geometry_meshes_unchanged': 1944, 'whole_part_role_changes': changes,
                       'other_whole_part_roles_unchanged': 1933})
        receipts.append(receipt)
        baselines.append(reference(baseline_path))

    # Independent reviews are copied as immutable evidence, never rewritten here.
    independent_reviews = []
    for name in ('independent_cream_theme_review_012.json',
                 'independent_theme_colour_review_013.json'):
        source = RAW / name
        if not source.exists():
            continue
        target = EVIDENCE / name
        before = sha(source)
        shutil.copyfile(source, target)
        assert sha(source) == before == sha(target)
        archive.append({'original': reference(source), 'archived': reference(target),
                        'byte_identical': True})
        independent_reviews.append(reference(target))

    # Camera, lighting settings and geometry are inherited from one saved 056 view.
    def frame(receipt: dict) -> dict:
        view = receipt['views'][0]
        return {k: view[k] for k in ('camera_position_m', 'target_m', 'ortho_scale_m',
                                     'studio_floor_hidden')}

    assert all(frame(r) == frame(receipts[0]) for r in receipts)
    assert all(r['source_bound_meshes'] == receipts[0]['source_bound_meshes'] for r in receipts)
    assert all(r['source_triangles'] == receipts[0]['source_triangles'] for r in receipts)
    write(EVIDENCE / 'source_archive_map.json', {'schema': 'byte_exact_render_archive/1',
          'records': archive, 'original_receipts_not_rewritten': True})
    write(EVIDENCE / 'display_scope_audit.json', {
        'schema': 'goose_theme_finish_scope_audit/1', 'status': 'PASS_STATIC_DISPLAY_IDENTITY_ONLY',
        'assembly_binding': receipts[0]['assembly_binding'], 'camera': frame(receipts[0]),
        'same_geometry_across_four_schemes': True, 'mesh_occurrences': 1944,
        'source_triangles': receipts[0]['source_triangles'], 'whole_part_overrides': overrides,
        'qualification_scope': 'Only 11 whole-part finish roles change relative to each same-theme 056 baseline. '
                               'The other 1933 roles and all 1944 geometries are preserved; this does not claim '
                               'that pixels or colours are identical between different palettes.',
        'motion_qualification': 'NOT_INCLUDED', 'geometry_or_physics_modified': False,
        'per_scheme': audits, 'checked_existing_source_files': list(checked_inputs.values())})

    canvas = Image.new('RGB', (1800, 2180), '#f7f7f5')
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(str(FONT), 46)
    label_font = ImageFont.truetype(str(FONT), 34)
    small_font = ImageFont.truetype(str(FONT), 23)
    title = 'Goose V0.2 · Theme-coloured enclosures'
    note = 'Static colour proposal · Motion validation not included'
    draw.text((60, 46), title, fill='#26313a', font=title_font)
    inputs = []
    for index, scheme in enumerate(SCHEMES):
        source = IMAGES / f'{scheme}_oblique.png'
        with Image.open(source) as raw:
            assert raw.size == (1400, 1512), source
            assert raw.mode in ('RGB', 'RGBA'), source
            if raw.mode == 'RGBA':
                assert raw.getchannel('A').getextrema() == (255, 255), 'Unexpected nonopaque image'
            tile = raw.convert('RGB').resize((800, 864), Image.Resampling.LANCZOS)
        left = 60 + (index % 2) * 880
        top = 144 + (index // 2) * 980
        canvas.paste(tile, (left, top))
        assert canvas.crop((left, top, left+800, top+864)).tobytes() == tile.tobytes()
        draw.text((left+12, top+884), scheme.title(), fill='#34424b', font=label_font)
        inputs.append({'source': reference(source), 'label': scheme.title(),
                       'source_size': [1400, 1512], 'display_size': [800, 864],
                       'scale': 4/7, 'image_box_xyxy': [left, top, left+800, top+864],
                       'cropped': False, 'retouched': False,
                       'pasted_pixels_equal_uniformly_resized_original': True})
    draw.text((60, 2114), note, fill='#667078', font=small_font)
    board = IMAGES / 'theme_enclosure_comparison.png'
    canvas.save(board, format='PNG', compress_level=9, optimize=False)
    composition = {'schema': 'goose_theme_board_composition/1',
                   'source': reference(Path(__file__)), 'Pillow_version': PIL.__version__,
                   'font': {'path': str(FONT), 'sha256': sha(FONT)},
                   'board': reference(board), 'canvas_size': list(canvas.size),
                   'title': title, 'note': note, 'scheme_order': list(SCHEMES),
                   'operations': ['uniform aspect-preserving resize', 'padding', 'text labels'],
                   'rerendered': False, 'retouched': False, 'inputs': inputs}
    write(EVIDENCE / 'composition_receipt.json', composition)
    review_path = EVIDENCE / 'visual_review.json'
    review = json.loads(review_path.read_text()) if review_path.exists() else None
    reviewed = bool(review and review.get('board_sha256') == sha(board)
                    and review.get('board_opened_and_reviewed') is True)
    files = sorted([p for p in IMAGES.iterdir() if p.is_file()] +
                   [p for p in EVIDENCE.iterdir() if p.is_file() and p.name != 'manifest.json'])
    manifest = {'schema': 'goose_theme_enclosure_study/1', 'revision': '058',
                'status': 'STATIC_DISPLAY_PACKET_COMPLETE' if reviewed else 'PACKAGED_AWAITING_VISUAL_REVIEW',
                'purpose': 'User-requested theme-coloured enclosure comparison on the unchanged static b5a assembly.',
                'physical_or_motion_release': False, 'motion_qualification': 'NOT_INCLUDED',
                'source_assembly': config['assembly_manifest'],
                'unchanged_geometry_occurrences': 1944, 'whole_part_finish_overrides': 11,
                'other_whole_part_roles_unchanged': 1933,
                'source_inputs': [reference(CONFIG), reference(WRAPPER),
                                  reference(ROOT / config['base_renderer']['path'])],
                'baseline_receipts': baselines, 'independent_reviews': independent_reviews,
                'compositor': reference(Path(__file__)),
                'board': reference(board), 'source_receipts_byte_identical': True,
                'original_images_byte_identical': True, 'actual_board_visually_reviewed': reviewed,
                'files': [reference(p) for p in files],
                'publication_files_excluding_manifest_itself':
                    [reference(p) for p in files] +
                    [reference(Path(__file__)), reference(CONFIG), reference(WRAPPER)],
                'manifest_self': {'path': str((EVIDENCE / 'manifest.json').relative_to(ROOT)),
                                  'sha256_recorded_externally': True}}
    assert all(p['bytes'] < 100_000_000 for p in manifest['files'])
    write(EVIDENCE / 'manifest.json', manifest)
    print(json.dumps({'manifest': reference(EVIDENCE / 'manifest.json'),
                      'board': reference(board), 'status': manifest['status']}, indent=2))


if __name__ == '__main__':
    main()
