#!/usr/bin/env python3
"""Render a Gorilla internal architecture candidate over unchanged C15 meshes.

This is a source-bound visual layout entry, not geometric or physical acceptance.
OEM derivatives are opt-in and every resulting file stays under ignored artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
BLENDER_ROOT = Path("/home/ethan/Softwares/blender-local/root")
ROUTES = ("rotary_electric", "linear_electric", "central_hydraulic", "distributed_eha")
VIEWS = {
    "front": ((8, 0, 1.325), (0, 0, 1.325), 3.04),
    "left": ((0, 8, 1.325), (0, 0, 1.325), 3.04),
    "rear": ((-8, 0, 1.325), (0, 0, 1.325), 3.04),
    "cutaway_front": ((8, 0, 1.325), (0, 0, 1.325), 3.04),
    "cutaway_left": ((0, 8, 1.325), (0, 0, 1.325), 3.04),
    "cutaway_threequarter": ((4, -6, 3.7), (0, 0, 1.325), 3.10),
    "torso_detail": ((-6, -2.2, 2.65), (-.26, 0, 2.14), 1.08),
    "wrist_detail": ((-3, 4.5, 1.7), (-.085, .815, 1.21), .44),
}
DEFAULT_VIEWS = tuple(VIEWS)[:6]
DETAIL_VIEWS = ("torso_detail", "wrist_detail")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolved(path):
    path = Path(path)
    return (path if path.is_absolute() else ROOT / path).resolve()


def record_path(path):
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, default=ROBOT / "configs/internal_architecture_a_layout.json")
    parser.add_argument("--route", choices=ROUTES, required=True)
    parser.add_argument("--resolution", type=int, default=768)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--include-oem", action="store_true")
    parser.add_argument("--show-service", action="store_true", help="Show external maintenance clearance transparently; separate diagnostic exports")
    parser.add_argument("--views", default=",".join(DEFAULT_VIEWS), help="Comma-separated views; default is the six whole-robot views")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    args = parser.parse_args(argv)
    if args.resolution < 64 or args.samples < 1:
        parser.error("resolution must be at least 64; samples must be positive")
    requested_views = args.views.split(",")
    if len(set(requested_views)) != len(requested_views) or any(view not in VIEWS for view in requested_views):
        parser.error("views must be distinct names from: " + ",".join(VIEWS))
    args.layout = resolved(args.layout)
    return args


def output_paths(args):
    tag = "internal_architecture_a_" + args.route
    if args.show_service:
        tag += "_service"
    if args.include_oem:
        root = ROOT / "artifacts/gorilla_v0_1/internal_architecture_a_oem" / args.route
        source, exports, images = root / "cad/source", root / "cad/exports", root / "images"
    else:
        source = ROBOT / "cad/source"
        exports = ROBOT / "cad/exports/internal_architecture_a"
        images = ROBOT / "images"
    for directory in (source, exports, images):
        directory.mkdir(parents=True, exist_ok=True)
    return tag, source, exports, images


def load_layout(args):
    layout = json.loads(args.layout.read_text())
    if layout.get("robot_id", "gorilla_v0_1") != "gorilla_v0_1":
        raise ValueError("This renderer only accepts Gorilla V0.1 layouts")
    for field in ("base_blend", "base_scene"):
        path = resolved(layout[field])
        if sha(path) != layout[field + "_sha256"]:
            raise ValueError("Stale base source: " + str(path))
    identifiers = [module["id"] for module in layout["modules"]]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate module ids")
    for module in layout["modules"]:
        if module["route"] not in ("common", *ROUTES):
            raise ValueError("Unknown module route: " + module["id"])
    return layout


def wrapper(args):
    layout = load_layout(args)
    layout_sha = sha(args.layout)
    tag, _, _, _ = output_paths(args)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ":".join(str(BLENDER_ROOT / path) for path in (
        "usr/lib", "usr/lib/aarch64-linux-gnu", "usr/lib/aarch64-linux-gnu/lapack",
        "usr/lib/aarch64-linux-gnu/blas"))
    env["BLENDER_SYSTEM_SCRIPTS"] = str(BLENDER_ROOT / "usr/share/blender/scripts")
    env["BLENDER_SYSTEM_DATAFILES"] = str(BLENDER_ROOT / "usr/share/blender/datafiles")
    env["PYTHONHOME"] = "/usr"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = str(ROOT / ".venv/lib/python3.12/site-packages")
    command = [str(BLENDER_ROOT / "usr/bin/blender"), "-b", "--threads", "12",
               "--python-exit-code", "1", "--python", str(Path(__file__).resolve()), "--",
               "--layout", str(args.layout), "--route", args.route,
               "--resolution", str(args.resolution), "--samples", str(args.samples), "--views", args.views]
    if args.include_oem:
        command.append("--include-oem")
    if args.show_service:
        command.append("--show-service")
    logs = (ROOT / "artifacts/gorilla_v0_1/internal_architecture_a_oem" / args.route / "logs"
            if args.include_oem else ROOT / "artifacts/gorilla_v0_1/internal_architecture_a_render")
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / (tag + ("_oem" if args.include_oem else "") + ".log")
    print("Gorilla Cycles CPU render: " + str(log_path), flush=True)
    with log_path.open("w") as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log_path.read_text()[-7000:])
        raise RuntimeError("Gorilla internal renderer failed: " + str(log_path))
    if sha(args.layout) != layout_sha:
        raise ValueError("Layout changed during rendering")
    for field in ("base_blend", "base_scene"):
        if sha(resolved(layout[field])) != layout[field + "_sha256"]:
            raise ValueError("Base source changed during rendering")
    contact_sheets(args)
    print("Gorilla candidate render complete; no geometric/physical acceptance.")


def contact_sheets(args):
    """Only white alpha composition, labels and configuration-derived legends."""
    from PIL import Image, ImageDraw, ImageFont

    if args.show_service:
        return
    tag, _, export_dir, image_dir = output_paths(args)
    own_render = export_dir / (tag + "_render_manifest.json")
    if args.include_oem:
        view_names = ("cutaway_front", "cutaway_left", "cutaway_threequarter", "torso_detail", "wrist_detail")
        renders = [(args.route, json.loads(own_render.read_text()), own_render)]
        if not all(view in {image["view"] for image in renders[0][1]["images"]} for view in view_names):
            return
        title = "GORILLA V0.1 | OEM source meshes | recorded cutaway visibility"
        labels = {"torso_detail": "TORSO: 4 battery reference sites", "wrist_detail": "LEFT WRIST: 3 of 6 AK reference sites"}
        cells = [(route, view, labels.get(view, view.upper()), render, path)
                 for route, render, path in renders for view in view_names]
        columns, sheet_name = 3, tag + "_oem_contact_sheet"
        same_scale = False
    else:
        renders = []
        for route in ("rotary_electric", "central_hydraulic"):
            path = export_dir / ("internal_architecture_a_" + route + "_render_manifest.json")
            if not path.exists():
                return
            render = json.loads(path.read_text())
            source = json.loads(resolved(render["manifests"]["source"]["path"]).read_text())
            if source["renderer_script_sha256"] != sha(Path(__file__).resolve()) or render["layout_sha256"] != sha(args.layout):
                print("Gorilla comparison waits for both route renders with the same current source.")
                return
            renders.append((route, render, path))
        title = "GORILLA V0.1 | Internal architecture A | FRONT / LEFT at identical scale"
        cells = [(route, view, route.replace("_", " ").upper() + " | " + view.upper(), render, path)
                 for route, render, path in renders for view in ("front", "left")]
        columns, sheet_name, same_scale = 2, "internal_architecture_a_route_comparison", True
    n = args.resolution
    label_height, header, footer = 40, 60, 105
    rows = (len(cells) + columns - 1) // columns
    sheet = Image.new("RGB", (columns*n, header + rows*(n+label_height) + footer), "white")
    draw = ImageDraw.Draw(sheet)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        font = ImageFont.truetype(font_path, 16)
        title_font = ImageFont.truetype(font_path, 20)
    except OSError:
        font = title_font = ImageFont.load_default()
    draw.text((18, 18), title, fill="#25394a", font=title_font)
    inputs, scales = [], []
    for index, (route, view, label, render, render_path) in enumerate(cells):
        item = next(image for image in render["images"] if image["view"] == view)
        path = resolved(item["path"])
        if sha(path) != item["sha256"]:
            raise ValueError("Stale contact-sheet input: " + str(path))
        rgba = Image.open(path).convert("RGBA")
        if rgba.size != (n, n):
            raise ValueError("Contact-sheet images must have identical native resolution; no rescaling")
        x, y = (index % columns)*n, header + (index // columns)*(n+label_height)
        draw.text((x+16, y+10), label, fill="#25394a", font=font)
        white = Image.new("RGBA", rgba.size, (255,255,255,255))
        sheet.paste(Image.alpha_composite(white, rgba).convert("RGB"), (x, y+label_height))
        camera_reference = render["manifests"]["camera"]
        camera_manifest = json.loads(resolved(camera_reference["path"]).read_text())
        camera = next(camera for camera in camera_manifest["cameras"] if camera["view"] == view)
        scales.append(camera["ortho_scale_m"])
        inputs.append({"route": route, "view": view, **item,
                       "render_manifest_path": record_path(render_path), "render_manifest_sha256": sha(render_path),
                       "camera_manifest": camera_reference, "ortho_scale_m": camera["ortho_scale_m"],
                       "hidden_mesh_names": camera["hidden_mesh_names"]})
    if same_scale and len(set(scales)) != 1:
        raise ValueError("Route comparison cameras do not share an identical scale")
    legend_y = sheet.height - footer + 15
    layout = json.loads(args.layout.read_text())
    categories = {}
    for module in layout["modules"]:
        if module["role"] != "service_space":
            categories.setdefault(module["category"], module["rgba"][:3])
    x = 18
    for category, color in categories.items():
        swatch = tuple(round(channel*255) for channel in color)
        draw.rectangle((x,legend_y,x+16,legend_y+16), fill=swatch)
        draw.text((x+24,legend_y), category, fill="#25394a", font=font)
        x += 150
    draw.text((18,legend_y+31), "Service clearance hidden: external maintenance space, not robot hardware.", fill="#25394a", font=font)
    draw.text((18,legend_y+57), "Actual candidate meshes; no geometric or physical acceptance. Internal occlusion retained.", fill="#25394a", font=font)
    sheet_path = image_dir / (sheet_name + ".png")
    sheet.save(sheet_path)
    manifest_path = export_dir / (sheet_name + "_manifest.json")
    write_json(manifest_path, {"schema": "gorilla_internal_architecture_contact_sheet_v1", "robot_id": "gorilla_v0_1",
                              "renderer_script_path": record_path(Path(__file__).resolve()), "renderer_script_sha256": sha(Path(__file__).resolve()),
                              "layout_sha256": sha(args.layout), "include_oem": args.include_oem,
                              "image": {"path": record_path(sheet_path), "sha256": sha(sheet_path)}, "inputs": inputs,
                              "same_scale": same_scale, "ortho_scales_m": scales, "legend_from_layout_categories": categories,
                              "post_processing": "Native-resolution alpha composition onto white, labels and legend only. No image scaling, shape, color, or geometry edits.",
                              "geometry_accepted": False, "physics_accepted": False})
    print("Gorilla white contact sheet: " + str(sheet_path))


def mesh_identity(obj):
    """Exact source mesh topology and local coordinates, plus world transform."""
    digest = hashlib.sha256()
    digest.update(struct.pack("<II", len(obj.data.vertices), len(obj.data.polygons)))
    for vertex in obj.data.vertices:
        digest.update(struct.pack("<3d", *vertex.co))
    for polygon in obj.data.polygons:
        digest.update(struct.pack("<I", len(polygon.vertices)))
        digest.update(struct.pack("<" + "I" * len(polygon.vertices), *polygon.vertices))
    transform = [value for row in obj.matrix_world for value in row]
    transform_hash = hashlib.sha256(struct.pack("<16d", *transform)).hexdigest()
    return {"name": obj.name, "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons), "mesh_sha256": digest.hexdigest(),
            "world_transform_sha256": transform_hash}


def obj_mesh(path):
    """Read local SI OBJ without importer axis remapping or implicit scale."""
    vertices, faces = [], []
    for line in Path(path).read_text().splitlines():
        tokens = line.split()
        if not tokens or tokens[0].startswith("#"):
            continue
        if tokens[0] == "v":
            vertices.append(tuple(float(value) for value in tokens[1:4]))
        elif tokens[0] == "f":
            face = []
            for token in tokens[1:]:
                index = int(token.split("/")[0])
                face.append(index - 1 if index > 0 else len(vertices) + index)
            if len(face) < 3 or any(index < 0 or index >= len(vertices) for index in face):
                raise ValueError("Invalid source OBJ face: " + str(path))
            faces.append(face)
    if not vertices or not faces:
        raise ValueError("Empty source OBJ: " + str(path))
    if not all(math.isfinite(value) for vertex in vertices for value in vertex):
        raise ValueError("Nonfinite source OBJ: " + str(path))
    return vertices, faces


def blender_render(args):
    import bpy
    from mathutils import Euler, Quaternion, Vector

    layout = load_layout(args)
    layout_sha, script_sha = sha(args.layout), sha(Path(__file__).resolve())
    base_scene = json.loads(resolved(layout["base_scene"]).read_text())
    parts = {part["name"]: part for part in base_scene["parts"]}
    if len(parts) != 613:
        raise ValueError("Expected frozen Gorilla C15 base with exactly 613 named parts")
    bpy.ops.wm.open_mainfile(filepath=str(resolved(layout["base_blend"])))
    base_objects = []
    for name in parts:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise ValueError("Missing frozen base mesh: " + name)
        base_objects.append(obj)
    before = [mesh_identity(obj) for obj in base_objects]
    visibility = {obj.name: obj.hide_render for obj in base_objects}
    tag, source_dir, export_dir, image_dir = output_paths(args)
    blend_path, glb_path = source_dir / (tag + ".blend"), export_dir / (tag + ".glb")
    if blend_path.resolve() == resolved(layout["base_blend"]):
        raise ValueError("Refusing to overwrite the appearance source")

    collection = bpy.data.collections.new(tag + "_modules")
    bpy.context.scene.collection.children.link(collection)
    module_objects, module_records = [], []

    def create_mesh(name, vertices, faces, color, transform, module, kind):
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.matrix_world = transform
        obj["robot_id"] = "gorilla_v0_1"
        obj["internal_module_id"] = module["id"]
        obj["module_label"] = module["label"]
        obj["family"] = module["family"]
        obj["category"] = module["category"]
        obj["route"] = module["route"]
        obj["role"] = module["role"]
        obj["display_kind"] = kind
        obj["geometry_accepted"] = False
        obj["physics_accepted"] = False
        if module["role"] == "service_space":
            color = [*color[:3], min(color[3], .08)]
            obj["space_interpretation"] = "External maintenance clearance, not physical robot hardware"
            obj.hide_render = not args.show_service
        linear = lambda c: c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
        rgba = tuple(linear(value) for value in color[:3]) + (color[3],)
        material = bpy.data.materials.new(name + "_material")
        material.use_nodes = True
        material.diffuse_color = rgba
        material.blend_method = "BLEND" if color[3] < 1 else "OPAQUE"
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Alpha"].default_value = color[3]
        bsdf.inputs["Metallic"].default_value = .05
        bsdf.inputs["Roughness"].default_value = .42
        mesh.materials.append(material)
        module_objects.append(obj)
        return obj

    def world_bounds(obj):
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        return {"min": [min(point[i] for point in points) for i in range(3)],
                "max": [max(point[i] for point in points) for i in range(3)]}

    from mathutils import Matrix
    for module in layout["modules"]:
        if module["route"] not in ("common", args.route):
            continue
        center = module["center_world_m"]
        if len(center) != 3 or not all(math.isfinite(value) for value in center):
            raise ValueError("Invalid module center: " + module["id"])
        geometry = module["geometry"]
        rotation = Quaternion((1, 0, 0, 0))
        if geometry == "box":
            dimensions = module["dimensions_m"]
            if len(dimensions) != 3 or any(value <= 0 or not math.isfinite(value) for value in dimensions):
                raise ValueError("Invalid box dimensions: " + module["id"])
            x, y, z = [value / 2 for value in dimensions]
            vertices = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                        (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
            faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
            if "rotation_euler_rad" in module:
                rotation = Euler(module["rotation_euler_rad"], "XYZ").to_quaternion()
        elif geometry == "cylinder":
            radius, half_length = module["diameter_m"] / 2, module["length_m"] / 2
            axis = Vector(module["axis_world"])
            if min(radius, half_length) <= 0 or not all(math.isfinite(value) for value in (radius, half_length, *axis)) or axis.length < 1e-9:
                raise ValueError("Invalid cylinder: " + module["id"])
            rotation = Vector((0,0,1)).rotation_difference(axis.normalized())
            n = 64
            vertices = [(radius*math.cos(2*math.pi*i/n), radius*math.sin(2*math.pi*i/n), z)
                        for z in (-half_length, half_length) for i in range(n)]
            faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
            faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        else:
            raise ValueError("Unsupported module geometry: " + str(geometry))
        rgba = module["rgba"]
        if len(rgba) != 4 or not all(0 <= value <= 1 for value in rgba):
            raise ValueError("Invalid module RGBA: " + module["id"])
        transform = Matrix.Translation(Vector(center)) @ rotation.to_matrix().to_4x4()
        obj = create_mesh("internal_" + module["id"] + "_envelope", vertices, faces, rgba, transform, module, "own_module_envelope")
        item = {"id": module["id"], "layout_module": module, "envelope_mesh": mesh_identity(obj),
                "envelope_bounds_world_m": world_bounds(obj), "matrix_world": [list(row) for row in transform],
                "envelope_render_alpha": obj.active_material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value,
                "oem_included": False, "interpretation": "External maintenance clearance, not robot hardware; default hidden from all renders." if module["role"] == "service_space" else "Editable module envelope or reserved space; physical capability and placement unaccepted."}
        if args.include_oem and module.get("source_geometry_local_path"):
            oem_path = resolved(module["source_geometry_local_path"])
            if oem_path.suffix.lower() != ".obj" or sha(oem_path) != module["source_geometry_sha256"]:
                raise ValueError("Missing or stale local SI OEM OBJ: " + str(oem_path))
            vertices, faces = obj_mesh(oem_path)
            local_rotation = Euler(module.get("source_geometry_rotation_euler_rad", [0,0,0]), "XYZ").to_matrix().to_4x4()
            oem_transform = transform @ local_rotation
            oem_color = [*rgba[:3], 1]
            oem = create_mesh("internal_" + module["id"] + "_oem_reference", vertices, faces, oem_color, oem_transform, module, "oem_geometry_reference")
            # Keep the specified complete envelope visible as a transparent fit reference.
            obj.active_material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = min(rgba[3], .12)
            obj.active_material.blend_method = "BLEND"
            obj.active_material.diffuse_color = (*obj.active_material.diffuse_color[:3], min(rgba[3], .12))
            item.update({"oem_included": True, "source_path": record_path(oem_path),
                         "envelope_render_alpha": min(rgba[3], .12),
                         "source_sha256": sha(oem_path), "oem_mesh": mesh_identity(oem),
                         "oem_bounds_world_m": world_bounds(oem), "oem_matrix_world": [list(row) for row in oem_transform],
                         "oem_transform_scope": "Local source meters and axes retained; module rigid rotation plus explicitly configured local source rotation only. No scaling or inferred OEM shaft fit."})
        module_records.append(item)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    bpy.context.preferences.filepaths.save_version = 0
    scene["internal_architecture_layout_sha256"] = layout_sha
    scene["internal_architecture_route"] = args.route
    scene["geometry_accepted"] = False
    scene["physics_accepted"] = False
    camera_data = bpy.data.cameras.new(tag + "_orthographic_camera")
    camera = bpy.data.objects.new(tag + "_orthographic_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"

    def set_camera(view):
        position, target, scale = VIEWS[view]
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera_data.ortho_scale = scale

    set_camera("cutaway_threequarter")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [*base_objects, *module_objects]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base_objects[0]
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True,
                            export_yup=True, export_extras=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    camera_records, images = [], []
    for view in args.views.split(","):
        set_camera(view)
        hidden = []
        for obj in base_objects:
            part = parts[obj.name]
            reason = None
            if visibility[obj.name]:
                reason = "frozen_base_hide_render"
            if view.startswith("cutaway_") or view in DETAIL_VIEWS:
                if part["role"] in ("armor_surface", "armor_cover"):
                    reason = "cutaway_remove_original_armor"
                elif part["role"] == "visible_mechanism" and not part.get("structure_view_visible", False):
                    reason = "cutaway_remove_old_mechanism_proxy"
            obj.hide_render = reason is not None
            if reason is not None:
                hidden.append({"name": obj.name, "role": part["role"], "reason": reason})
        for obj in module_objects:
            if obj["role"] == "service_space" and not args.show_service:
                obj.hide_render = True
                hidden.append({"name": obj.name, "role": "service_space", "reason": "external_maintenance_clearance_not_hardware_default_hidden"})
        image_path = image_dir / (tag + "_" + view + ".png")
        scene.render.filepath = str(image_path)
        bpy.ops.render.render(write_still=True)
        position, target, scale = VIEWS[view]
        camera_records.append({"view": view, "projection": "ORTHO", "position_world_m": list(position),
                               "target_world_m": list(target), "rotation_euler_rad": list(camera.rotation_euler),
                               "ortho_scale_m": scale, "resolution_px": [args.resolution]*2,
                               "hidden_mesh_names": [item["name"] for item in hidden], "hidden_mesh_reasons": hidden,
                               "module_visibility": "Only external service clearance hidden by default; no internal candidate modules hidden to reveal OEM meshes.",
                               "interpretation": "Source mesh cutaway visibility, also used for detail cameras; no internal module isolation and no physical acceptance." if view.startswith("cutaway_") or view in DETAIL_VIEWS else "Actual unchanged C15 shell over route candidate modules; service clearance hidden, no fit acceptance."})
        images.append({"view": view, "path": record_path(image_path), "sha256": sha(image_path)})
        for obj in base_objects:
            obj.hide_render = visibility[obj.name]

    after = [mesh_identity(obj) for obj in base_objects]
    if before != after:
        raise ValueError("Frozen C15 mesh geometry or world transform changed")
    if sha(args.layout) != layout_sha or sha(Path(__file__).resolve()) != script_sha:
        raise ValueError("Render configuration/source changed during rendering")
    for field in ("base_blend", "base_scene"):
        if sha(resolved(layout[field])) != layout[field + "_sha256"]:
            raise ValueError("Frozen base changed during rendering")
    shared = {"robot_id": "gorilla_v0_1", "route": args.route, "layout_path": record_path(args.layout),
              "layout_sha256": layout_sha, "include_oem": args.include_oem,
              "show_service": args.show_service, "service_space_policy": "External maintenance clearance; retained as editable transparent objects in exports, hidden from images by default.",
              "geometry_accepted": False, "physics_accepted": False}
    source_manifest = {**shared, "schema": "gorilla_internal_architecture_source_v1",
                       "renderer_script_path": record_path(Path(__file__).resolve()), "renderer_script_sha256": script_sha,
                       "base_blend": layout["base_blend"], "base_blend_sha256": layout["base_blend_sha256"],
                       "base_scene": layout["base_scene"], "base_scene_sha256": layout["base_scene_sha256"],
                       "base_mesh_count": len(before), "base_meshes_exactly_preserved": before == after,
                       "base_mesh_identity": before, "identity_algorithm": "SHA256 little-endian float64 mesh-local vertex xyz and uint32 polygon index order; separate float64 world matrix hash.",
                       "route_filter": "Only common plus the selected route instantiated.",
                       "excluded_module_ids": [module["id"] for module in layout["modules"] if module["route"] not in ("common", args.route)],
                       "source_scope": "Frozen evaluated C15 meshes retained without bevel, remesh, axis, material, or topology reconstruction. Candidate envelopes are visualization inputs, not verified hardware."}
    module_manifest = {**shared, "schema": "gorilla_internal_architecture_modules_v1", "modules": module_records}
    camera_manifest = {**shared, "schema": "gorilla_internal_architecture_cameras_v1", "cameras": camera_records}
    manifest_paths = {}
    for name, value in (("source", source_manifest), ("module", module_manifest), ("camera", camera_manifest)):
        path = export_dir / (tag + "_" + name + "_manifest.json")
        write_json(path, value)
        manifest_paths[name] = {"path": record_path(path), "sha256": sha(path)}
    render_manifest = {**shared, "schema": "gorilla_internal_architecture_render_v1",
                       "renderer": "Blender " + bpy.app.version_string + " Cycles CPU", "samples": args.samples,
                       "resolution_px": [args.resolution]*2, "post_processing": "None; actual mesh RGBA renders.",
                       "images": images, "manifests": manifest_paths,
                       "exports": [{"path": record_path(path), "sha256": sha(path)} for path in (blend_path, glb_path)],
                       "acceptance_scope": "No geometric/physical acceptance. No inferred procurement, torque, mass, thermal performance, manufacturability, contact, or strength approval.",
                       "oem_scope": "All OEM-mode exports and images confined to ignored artifacts; OEM reference topology is not asserted to be a watertight collision body." if args.include_oem else "Own candidate envelopes only; no OEM geometry loaded or embedded."}
    render_path = export_dir / (tag + "_render_manifest.json")
    write_json(render_path, render_manifest)
    print(json.dumps({"robot_id": "gorilla_v0_1", "render_manifest": str(render_path),
                      "base_mesh_count": len(before), "base_preserved": True, "selected_modules": len(module_records),
                      "images": [image["path"] for image in images], "geometry_accepted": False, "physics_accepted": False}))


if __name__ == "__main__":
    arguments_value = arguments()
    try:
        import bpy
    except ImportError:
        wrapper(arguments_value)
    else:
        blender_render(arguments_value)
