"""CPU-only whole-scene visual review of actual saved 009 native appearance."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/models"))
from render_goose_reference_camera import load_glb, render, Rasterizer
import hashlib
def ident(p):
 p=Path(p).resolve();return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')


def main():
    os.sched_setaffinity(0, {18})
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--centre", type=float, nargs=3, default=[25., 0., 350.])
    parser.add_argument("--scale", type=float, default=1.13)
    parser.add_argument("--size", type=int, default=900)
    parser.add_argument("--views", nargs="+", choices=["front", "right_side", "oblique"], default=["front", "right_side", "oblique"])
    parser.add_argument("--native-override", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    binding = read(args.binding)
    scene = Path(binding["scene"]["path"])
    assert ident(scene)["sha256"] == binding["scene"]["sha256"]
    primitives = load_glb(scene.read_bytes())
    names = {row["name"] for row in primitives}
    assert names == set(binding["occurrence_owners"])
    override = None
    if args.native_override:
        override = read(args.native_override)
        extra_path = ROOT / override["scene"]["repository_path"]
        assert ident(extra_path)["sha256"] == override["scene"]["sha256"]
        extra = load_glb(extra_path.read_bytes())
        selected = {row["name"] for row in extra}
        assert selected == {row["name"] for row in override["sources"]} and selected <= names
        primitives = [row for row in primitives if row["name"] not in selected] + extra
        assert {row["name"] for row in primitives} == names
    centre, size, scale = np.array(args.centre), args.size, args.scale
    cameras = {
        "front": (np.array([0., 1., 0.]), np.array([0., 0., -1.])),
        "right_side": (np.array([1., 0., 0.]), np.array([0., 0., -1.])),
        "oblique": (np.array([.8, .6, 0.]), np.array([.18, -.24, -np.sqrt(.91)])),
    }
    records = []
    cameras = {name: cameras[name] for name in args.views}
    board = Image.new("RGB", (len(cameras) * size, size + 55), (248, 248, 248))
    draw = ImageDraw.Draw(board)
    with tempfile.TemporaryDirectory(prefix="goose_009_whole_review_") as temporary:
        raster = Rasterizer(temporary)
        for column, (name, (xrow, yrow)) in enumerate(cameras.items()):
            rows = scale * np.vstack([xrow, yrow])
            mat = np.column_stack([rows, np.array([size / 2, size / 2]) - rows @ centre])
            camera = dict(kind="orthographic", viewport_px=[size, size], matrix_2x4=mat.tolist())
            image, metrics, _ = render(primitives, camera, size, size, 1, .1, raster)
            path = args.output / (name + ".png")
            image.save(path)
            board.paste(image, (column * size, 25))
            draw.text((column * size + 15, 6), name + " | complete actual native source display", fill=(28, 32, 35))
            records.append(dict(view=name, image=ident(path), camera=camera, metrics=metrics))
            print(json.dumps(dict(stage="review", view=name, triangles=metrics["triangles_submitted"])), flush=True)
    draw.text((15, size + 33), "Actual saved source surfaces. Static geometry review only; not a motion, structural or manufacturing pass.", fill=(28, 32, 35))
    target = args.output / "whole_three_views.png"
    board.save(target)
    save(args.output / "visual_review.json", dict(scene=ident(scene), binding=ident(args.binding),
        complete_occurrences=len(names), omitted_occurrences=[], camera_or_geometry_fitting=False,
        native_display_override=None if override is None else dict(source=ident(args.native_override), replacements=override),
        actual_steps=0, renderer="CPU triangles/depth buffer", views=records, board=ident(target)))
    print(json.dumps(dict(stage="review_complete", board=str(target))), flush=True)


if __name__ == "__main__":
    main()
