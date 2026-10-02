#!/usr/bin/env python3
"""Assemble equal-scale original/actual 3D comparisons, without retouching.

Reference crops are uniformly resized. No model pixel is repainted, warped or
hidden. The sheet is review evidence, not a numerical fidelity/physical pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
REFERENCE_FRAME = {
    "front": ((112, 74, 539, 618), (325.5, 603)),
    "left": ((839, 73, 1073, 618), (971, 603)),
    "rear": ((112, 687, 539, 1230), (325.5, 1215)),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--views", default="front,left,rear")
    p.add_argument("--tag", required=True)
    p.add_argument("--output-dir", type=Path, default=ROBOT / "images")
    args = p.parse_args()
    snapshot = args.snapshot.resolve()
    identity = json.loads((snapshot / "snapshot_manifest.json").read_text())
    copies = {Path(i["snapshot_path"]).name: i for i in identity["copies"]}
    render = json.loads((snapshot / "appearance_c_render_manifest.json").read_text())
    cameras = {c["view"]: c for c in render["camera_definitions"]}
    n = render["resolution"]
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", round(.028*n))
    authority = snapshot / "user_confirmed_four_view.jpg"
    if sha(authority) != copies[authority.name]["sha256"]:
        raise ValueError("Frozen reference identity changed")
    reference = Image.open(authority).convert("RGB")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for view in args.views.split(","):
        crop, (u0, v0) = REFERENCE_FRAME[view]
        camera = cameras[view]
        if camera["projection"] != "ORTHO" or camera["hidden_mesh_names"] or camera["display_pose"]:
            raise ValueError("Comparison requires a complete neutral orthographic view")
        model_path = snapshot / f"appearance_c_{view}.png"
        if sha(model_path) != copies[model_path.name]["sha256"]:
            raise ValueError("Frozen model image identity changed")
        actual = Image.open(model_path).convert("RGBA")
        if actual.size != (n, n):
            raise ValueError("Frozen render resolution differs from manifest")
        scale = (n/camera["ortho_scale_m"]) * (2.65/516)
        panel = Image.new("RGB", (n, n), "white")
        patch = reference.crop(crop)
        patch = patch.resize((round(patch.width*scale), round(patch.height*scale)), Image.Resampling.LANCZOS)
        ground = n*(.5+camera["target_m"][2]/camera["ortho_scale_m"])
        origin = (round(n/2+(crop[0]-u0)*scale), round(ground+(crop[1]-v0)*scale))
        panel.paste(patch, origin)
        white_actual = Image.new("RGBA", actual.size, "white")
        white_actual.alpha_composite(actual)
        header = round(.06*n)
        sheet = Image.new("RGB", (2*n, n+header), "white")
        sheet.paste(panel, (0, header))
        sheet.paste(white_actual.convert("RGB"), (n, header))
        draw = ImageDraw.Draw(sheet)
        draw.text((round(.035*n), round(.014*n)), f"Sole original {view.upper()} | uniform scale", fill="#28313f", font=font)
        draw.text((n+round(.035*n), round(.014*n)), f"{args.tag} | actual complete geometry", fill="#28313f", font=font)
        out = args.output_dir / f"{args.tag}_{view}_comparison.png"
        sheet.save(out)
        results.append({"view":view,"path":str(out.relative_to(ROOT)),"sha256":sha(out),
            "reference_crop_uv":crop,"reference_origin_uv":[u0,v0],"reference_uniform_resize":scale,
            "actual_source_path":str(model_path.relative_to(ROOT)),"actual_source_sha256":sha(model_path)})
    record = {"schema":"gorilla_appearance_comparison_v1","scene_sha256":identity["scene_sha256"],
        "snapshot_manifest_sha256":sha(snapshot/"snapshot_manifest.json"),"image_authority_sha256":sha(authority),
        "script_sha256":sha(Path(__file__)),"method":"Uniformly resized original crops beside unchanged complete neutral orthographic renders on white. Same template height/ground; original cameras remain uncalibrated. No retouching, segmentation score or acceptance inference.",
        "appearance_accepted":False,"physics_accepted":False,"images":results}
    manifest = args.output_dir / f"{args.tag}_comparison_manifest.json"
    manifest.write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps({"manifest":str(manifest),"images":[i["path"] for i in results]}))


if __name__ == "__main__":
    main()
