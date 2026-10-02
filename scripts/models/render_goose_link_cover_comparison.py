"""Render a six-cover visual A/B from the existing body-bay Blender assembly.

Read-only main scene: append only the six independently generated cover meshes
to a new comparison file. Lights/materials/cameras come from the same baseline.
"""
import argparse
import array
import ast
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import bpy
from mathutils import Vector


def read_npy(raw):
    if raw[:6] != b"\x93NUMPY":
        raise ValueError("NPY magic")
    size = 2 if raw[6] == 1 else 4 if raw[6] in (2, 3) else 0
    if not size:
        raise ValueError("NPY version")
    length = int.from_bytes(raw[8:8+size], "little")
    start = 8+size
    info = ast.literal_eval(raw[start:start+length].decode("latin1"))
    shape, kind = info["shape"], info["descr"]
    if info["fortran_order"] or len(shape) != 2 or kind not in ("<f8", ">f8", "<i8", ">i8"):
        raise ValueError("NPY layout")
    data = array.array("d" if kind.endswith("f8") else "q")
    data.frombytes(raw[start+length:])
    if (kind[0] == "<") != (sys.byteorder == "little"):
        data.byteswap()
    if len(data) != shape[0]*shape[1]:
        raise ValueError("NPY length")
    items = iter(data)
    return list(zip(*([items]*shape[1])))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--robot-root", type=Path, required=True)
parser.add_argument("--samples", type=int, default=32)
parser.add_argument("--resolution", type=int, default=900)
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
robot = args.robot_root.resolve()
base_blend = robot / "cad/source/body_bay_preview/quad_assembly.blend"
base_scene = robot / "cad/source/body_bay_preview/scene.json"
cover_scene = robot / "cad/source/link_cover_samples/quad_scene.json"
cover_manifest = robot / "cad/exports/link_cover_samples/manifest.json"
source = robot / "cad/source/link_cover_comparison"
output = robot / "images/link_cover_comparison"
source.mkdir(parents=True, exist_ok=True)
output.mkdir(parents=True, exist_ok=True)
input_hashes = {str(p.relative_to(robot)): sha(p) for p in [base_blend, base_scene, cover_scene, cover_manifest]}
base = json.loads(base_scene.read_text())
covers = json.loads(cover_scene.read_text())
offset = Vector(base.get("assembly_translation_m", [0, 0, 0]))
baseline = dict(base)
baseline.update(status="BASELINE_COMPARISON_CANDIDATE_NOT_RELEASED", cover_attachment_pass=False)
covered = dict(base)
covered["parts"] = base["parts"] + covers["parts"]
covered.update(status="LINK_COVER_VISUAL_SAMPLE_FIXING_UNFINISHED", cover_attachment_pass=False,
               final_appearance_pass=False, manufacturing_pass=False,
               comparison_note="same baseline rigid assembly and lighting; six shells only, fixing hardware not present",
               cover_shell_mass_kg=json.loads(cover_manifest.read_text())["total_shell_mass_kg"])
covered.pop("nominal_conditional_mass_kg", None)
(source / "baseline_scene.json").write_text(json.dumps(baseline, separators=(",", ":"))+"\n")
(source / "covered_scene.json").write_text(json.dumps(covered, separators=(",", ":"))+"\n")
bpy.ops.wm.open_mainfile(filepath=str(base_blend))
scene = bpy.context.scene
if not scene.camera:
    raise ValueError("Baseline review camera missing")
collection = bpy.data.collections.new("A link-cover sample - fixing unfinished")
scene.collection.children.link(collection)
material = bpy.data.materials.get("ivory")
if material is None:
    raise ValueError("Baseline ivory material missing")
new_objects = []
for part in covers["parts"]:
    path = (robot / part["geometry_npz"]).resolve()
    if not path.is_relative_to(robot) or sha(path) != part["source_sha256"]:
        raise ValueError("Cover geometry identity")
    with zipfile.ZipFile(path) as data:
        points = read_npy(data.read("vertices.npy"))
        faces = read_npy(data.read("faces.npy"))
    if any(len(f) != 4 for f in faces):
        raise ValueError("Cover must be all quad")
    center = Vector(tuple((min(v[i] for v in points)+max(v[i] for v in points))/2 for i in range(3)))
    mesh = bpy.data.meshes.new(part["name"])
    mesh.from_pydata([tuple(v[i]-center[i] for i in range(3)) for v in points], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(part["name"], mesh)
    collection.objects.link(obj)
    obj.location = center+offset
    obj.data.materials.append(material)
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.use_auto_smooth = True
    mesh.auto_smooth_angle = 1.3962634
    obj["source_sha256"] = part["source_sha256"]
    obj["part_role"] = part["role"]
    obj["attachment_pass"] = False
    obj["manufacturing_pass"] = False
    obj["assembly_translation_m"] = list(offset)
    new_objects.append(obj)

scene.cycles.samples = args.samples
scene.render.resolution_x = scene.render.resolution_y = args.resolution
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.use_stamp = True
scene.render.use_stamp_note = True
scene.render.use_stamp_date = scene.render.use_stamp_time = scene.render.use_stamp_frame = False
scene.render.use_stamp_filename = scene.render.use_stamp_scene = scene.render.use_stamp_camera = False
scene.render.use_stamp_render_time = False
scene.render.stamp_font_size = 14
camera = scene.camera
camera.data.ortho_scale = .78
views = {"three_quarter": ((1.15, -1.75, .99), (.05, 0, .325)),
         "side": ((.045, -2, .40), (.045, 0, .325))}
images = []
for mode in ["baseline", "covered"]:
    for obj in new_objects:
        obj.hide_render = obj.hide_viewport = mode == "baseline"
    scene.render.stamp_note_text = ("BASELINE CANDIDATE - NOT MANUFACTURING RELEASE" if mode == "baseline"
                                   else "COVER SAMPLE CANDIDATE - FIXING UNFINISHED")
    for view, (position, target) in views.items():
        camera.location = position
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z", "Y").to_euler()
        path = output / (mode+"_"+view+".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        images.append({"mode": mode, "view": view, "path": str(path.relative_to(robot)), "sha256": sha(path)})
for obj in new_objects:
    obj.hide_render = obj.hide_viewport = False
camera.location = views["three_quarter"][0]
camera.rotation_euler = (Vector(views["three_quarter"][1])-camera.location).to_track_quat("-Z", "Y").to_euler()
scene["status"] = "COVER SAMPLE COMPARISON - FIXING UNFINISHED - NOT RELEASED"
blend = source / "quad_comparison.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
report = {"status": "VISUAL_COMPARISON_ONLY_NOT_ATTACHMENT_RELEASE", "input_hashes": input_hashes,
          "input_unchanged": all(sha(robot/p) == h for p,h in input_hashes.items()),
          "cover_count": len(new_objects), "new_quad_faces": sum(len(o.data.polygons) for o in new_objects),
          "samples": args.samples, "resolution": args.resolution,
          "same_lights_materials_pose_camera": True, "cover_fixing_pass": False,
          "manufacturing_pass": False, "images": images,
          "blend_sha256": sha(blend), "generator_sha256": sha(Path(__file__))}
if not report["input_unchanged"]:
    raise ValueError("Baseline source changed during comparison")
(source / "comparison_record.json").write_text(json.dumps(report, indent=2)+"\n")
print("LINK_COVER_COMPARISON_COMPLETE", flush=True)
