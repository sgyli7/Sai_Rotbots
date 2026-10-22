"""Lay out unretouched, source-bound native CAD renders for review."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / 'robots/goose_v0_2/images/enclosure_refinement_056'
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def board(items, target, columns, title, subtitle):
    width, image_height = 700, 756
    margin, header, footer = 32, 115, 50
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new('RGB', (columns * width + 2*margin,
                              rows * (image_height+56) + header + footer), '#f7f7f5')
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(str(FONT), 34)
    label_font = ImageFont.truetype(str(FONT), 22)
    small_font = ImageFont.truetype(str(FONT), 16)
    draw.text((margin, 26), title, font=title_font, fill='#242b30')
    draw.text((margin, 72), subtitle, font=small_font, fill='#667078')
    inputs = []
    for index, (name, label) in enumerate(items):
        path = target.parent / name
        image = Image.open(path).convert('RGB')
        original_size = list(image.size)
        image.thumbnail((width-20, image_height), Image.Resampling.LANCZOS)
        col, row = index % columns, index // columns
        left = margin + col*width
        top = header + row*(image_height+56)
        canvas.paste(image, (left + (width-image.width)//2, top + (image_height-image.height)//2))
        draw.text((left+10, top+image_height+12), label, font=label_font, fill='#343d43')
        inputs.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
                       'original_size': original_size, 'display_size': list(image.size)})
    draw.text((margin, canvas.height-30), 'Goose V0.2 / 056 / Actual native CAD',
              font=small_font, fill='#667078')
    canvas.save(target)
    return {'path': str(target.relative_to(ROOT)), 'sha256': sha(target),
            'source_images': inputs, 'retouched_geometry_or_surfaces': False,
            'operations': ['uniform resize with aspect ratio preserved', 'layout', 'text labels']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--images', type=Path, default=IMAGES)
    parser.add_argument('--boards', nargs='+', choices=['clay', 'colour'], default=['clay', 'colour'])
    args = parser.parse_args()
    result = []
    if 'clay' in args.boards:
        result.append(board([('clay_front.png', 'Front'), ('clay_side.png', 'Right side'),
                             ('clay_rear.png', 'Rear')], args.images/'clay_three_views.png', 3,
                            'Goose V0.2', '056 / Monochrome form review / One saved assembly'))
        result.append(board([('clay_neck.png', 'Head / neck'), ('clay_feet.png', 'Front / ankle'),
                             ('clay_heel.png', 'Heel')], args.images/'clay_interface_details.png', 3,
                            'Goose V0.2', '056 / Actual cover interfaces'))
        result.append(board([('clay_inboard_left.png', 'Left leg / inboard'),
                             ('clay_inboard_right.png', 'Right leg / inboard'),
                             ('clay_top.png', 'Top'), ('clay_bottom.png', 'Underside')],
                            args.images/'clay_hidden_surfaces.png', 2,
                            'Goose V0.2', '056 / Inboard and underside / No hardware omitted'))
    if 'colour' in args.boards:
        receipts = [json.loads((args.images/(scheme+'_render_receipt.json')).read_text())
                    for scheme in ['cream', 'graphite', 'lavender', 'sky']]
        identities = {(r['source_sha256'], r['display_objects'], r['source_triangles']) for r in receipts}
        assert len(identities) == 1, 'Colourways must show the same complete saved geometry'
        result.append(board([(scheme+'_oblique.png', label) for scheme, label in
                            [('cream', 'Cream'), ('graphite', 'Graphite'),
                             ('lavender', 'Lavender'), ('sky', 'Sky')]],
                            args.images/'four_colorways.png', 2, 'Goose V0.2',
                            '056 / Four MicroDuck colour families / Whole-part finishes'))
    (args.images/'board_receipt.json').write_text(json.dumps({'source': str(Path(__file__).relative_to(ROOT)),
        'source_sha256': sha(Path(__file__)), 'boards': result}, indent=2)+'\n')


if __name__ == '__main__':
    main()
