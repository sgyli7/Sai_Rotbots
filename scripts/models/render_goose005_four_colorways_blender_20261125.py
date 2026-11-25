"""Render MicroDuck-inspired 4-colorway studio suite for Goose V0.2 (assembly_finish_005).

Uses Blender 4.0.2 Cycles on NVIDIA GB10 CUDA with AgX color management,
shadow-catcher studio floor, 3-point softbox lighting, and crisp PIL banner
composition for the 1x4 squad strip and 2x2 showcase grid.

Run rendering via:
    /home/ethan/Softwares/ai-3d-local/scripts/blender.sh -b --python \
        scripts/models/render_goose005_four_colorways_blender_20261125.py -- \
        --samples 80 --resolution 1600

Re-compose banners & JSON from existing RGBA caches via worktree .venv:
    .venv/bin/python scripts/models/render_goose005_four_colorways_blender_20261125.py --compose-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE_GLB = (
    ROOT
    / "robots/goose_v0_2/cad/exports/appearance_finish_execution_20261118_001/assembly/assembly_finish_sky_003.glb"
)
V01_PALETTE = ROOT / "robots/Goose_V0.1/configs/microduck_color_blocking_manual_wing_service.json"
OUT_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/showcase_renders/colorways"
RGBA_CACHE_DIR = ROOT / ".scratch/goose005_colorways_rgba"

STUDIO_BG_HEX = "#F8F9FB"
STUDIO_BG_RGB = (248, 249, 251)

COLORWAYS = [
    {
        "id": "sky",
        "label": "Sky",
        "label_full": "Sky Blue",
        "label_zh": "天空蓝",
        "subtitle": "Signature MicroDuck Cyan",
        "materials": {
            "shell": {"srgb_hex": "#6BC4E8", "roughness": 0.38, "metallic": 0.0},
            "accent": {"srgb_hex": "#FF6A13", "roughness": 0.34, "metallic": 0.0},
            "eye_ring": {"srgb_hex": "#FFB81C", "roughness": 0.32, "metallic": 0.0},
            "sole_accent": {"srgb_hex": "#FFB81C", "roughness": 0.32, "metallic": 0.0},
            "coachline": {"srgb_hex": "#FFB81C", "roughness": 0.22, "metallic": 0.05},
            "dark_mechanics": {"srgb_hex": "#1A1E24", "roughness": 0.40, "metallic": 0.25},
        },
    },
    {
        "id": "graphite",
        "label": "Graphite",
        "label_full": "Graphite · Purple · Yellow",
        "label_zh": "石墨灰·紫·黄",
        "subtitle": "Flagship Contrast Edition",
        "materials": {
            "shell": {"srgb_hex": "#454952", "roughness": 0.42, "metallic": 0.0},
            "accent": {"srgb_hex": "#F5C724", "roughness": 0.34, "metallic": 0.0},
            "eye_ring": {"srgb_hex": "#845EC2", "roughness": 0.34, "metallic": 0.0},
            "sole_accent": {"srgb_hex": "#845EC2", "roughness": 0.34, "metallic": 0.0},
            "coachline": {"srgb_hex": "#845EC2", "roughness": 0.22, "metallic": 0.05},
            "dark_mechanics": {"srgb_hex": "#16191E", "roughness": 0.40, "metallic": 0.28},
        },
    },
    {
        "id": "cream",
        "label": "Cream",
        "label_full": "Warm Cream",
        "label_zh": "奶油白",
        "subtitle": "Flagship Goose Ivory Edition",
        "materials": {
            "shell": {"srgb_hex": "#F2E5CF", "roughness": 0.40, "metallic": 0.0},
            "accent": {"srgb_hex": "#FF6A13", "roughness": 0.34, "metallic": 0.0},
            "eye_ring": {"srgb_hex": "#FFC32B", "roughness": 0.32, "metallic": 0.0},
            "sole_accent": {"srgb_hex": "#FFC32B", "roughness": 0.32, "metallic": 0.0},
            "dark_mechanics": {"srgb_hex": "#1B1F24", "roughness": 0.40, "metallic": 0.25},
        },
    },
    {
        "id": "lavender",
        "label": "Lavender",
        "label_full": "Lavender",
        "label_zh": "薰衣草紫",
        "subtitle": "Pastel Violet & Cyan Eye",
        "materials": {
            "shell": {"srgb_hex": "#B69CE2", "roughness": 0.40, "metallic": 0.0},
            "accent": {"srgb_hex": "#F5C724", "roughness": 0.34, "metallic": 0.0},
            "eye_ring": {"srgb_hex": "#55C4E8", "roughness": 0.32, "metallic": 0.0},
            "sole_accent": {"srgb_hex": "#8B6BC7", "roughness": 0.34, "metallic": 0.0},
            "coachline": {"srgb_hex": "#55C4E8", "roughness": 0.22, "metallic": 0.05},
            "dark_mechanics": {"srgb_hex": "#1A1E24", "roughness": 0.40, "metallic": 0.25},
        },
    },
]

# Rolls-Royce inspired bespoke twin coachline applied ONLY to the main torso shell pieces
TORSO_COACHLINE_OBJECTS = ("body016_front", "body_continuous_rear")
JOINT_CAP_OBJECT_ROLES: dict[str, str] = {}

# Exact mapping from verified GLB materials in assembly_finish_sky_003.glb to finish roles
GLB_MAT_TO_ROLE = {
    "Sky finish / shell": "shell",
    "Sky finish / theme_structural_dark": "shell",
    "Sky finish / accent": "accent",
    "Sky finish / eye_ring": "eye_ring",
    "Sky finish / sole_trim": "sole_accent",
    "Sky finish / structural_dark": "dark_mechanics",
    "Sky finish / mechanism": "dark_mechanics",
    "Sky finish / faceplate": "dark_mechanics",
    "Sky finish / rubber": "rubber",
    "Sky finish / glass": "glass",
    "Sky finish / lens": "lens",
    "Sky finish / pcb_reference": "pcb_reference",
    "Sky finish / metal": "metal",
    "Sky finish / metal_connector": "metal_connector",
    "Sky finish / neutral_panel": "neutral_panel",
}

COMMON_MATERIALS = {
    "rubber": {"srgb_hex": "#14181D", "roughness": 0.72, "metallic": 0.0},
    "glass": {"linear_rgb": [0.008, 0.018, 0.025], "roughness": 0.06, "metallic": 0.50},
    "lens": {"linear_rgb": [0.003, 0.009, 0.016], "roughness": 0.06, "metallic": 0.40},
    "pcb_reference": {"srgb_hex": "#1C6F43", "roughness": 0.55, "metallic": 0.05},
    "metal": {"linear_rgb": [0.34, 0.37, 0.39], "roughness": 0.36, "metallic": 0.65},
    "metal_connector": {"linear_rgb": [0.38, 0.41, 0.43], "roughness": 0.34, "metallic": 0.60},
    "neutral_panel": {"linear_rgb": [0.46, 0.46, 0.42], "roughness": 0.36, "metallic": 0.0},
}


def srgb_hex_to_linear(hex_str: str) -> list[float]:
    """Convert an sRGB hex string (#RRGGBB) to linear RGB floats in [0, 1]."""
    h = hex_str.lstrip("#")
    vals = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in vals]


def spec_to_linear_rgb(spec: dict) -> list[float]:
    if "linear_rgb" in spec:
        return [float(x) for x in spec["linear_rgb"]]
    return srgb_hex_to_linear(spec["srgb_hex"])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_principled_material(mat, spec: dict, specular_level: float = 0.30) -> None:
    """Update a Blender Principled BSDF material with linear RGB, roughness, metallic."""
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        nodes.clear()
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    lin = spec_to_linear_rgb(spec)
    bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1.0)
    bsdf.inputs["Roughness"].default_value = float(spec["roughness"])
    bsdf.inputs["Metallic"].default_value = float(spec.get("metallic", 0.0))
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular_level
    mat.diffuse_color = (lin[0], lin[1], lin[2], 1.0)


def build_torso_coachline_material(mat, shell_spec: dict, coach_spec: dict | None) -> None:
    """Apply shell BSDF + optional Rolls-Royce bespoke twin coachline on torso exterior."""
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf_shell = nt.nodes.new("ShaderNodeBsdfPrincipled")
    lin_s = spec_to_linear_rgb(shell_spec)
    bsdf_shell.inputs["Base Color"].default_value = (lin_s[0], lin_s[1], lin_s[2], 1.0)
    bsdf_shell.inputs["Roughness"].default_value = float(shell_spec["roughness"])
    bsdf_shell.inputs["Metallic"].default_value = float(shell_spec.get("metallic", 0.0))
    if "Specular IOR Level" in bsdf_shell.inputs:
        bsdf_shell.inputs["Specular IOR Level"].default_value = 0.28
    mat.diffuse_color = (lin_s[0], lin_s[1], lin_s[2], 1.0)

    if coach_spec is None:
        nt.links.new(bsdf_shell.outputs["BSDF"], out.inputs["Surface"])
        return

    bsdf_coach = nt.nodes.new("ShaderNodeBsdfPrincipled")
    lin_c = spec_to_linear_rgb(coach_spec)
    bsdf_coach.inputs["Base Color"].default_value = (lin_c[0], lin_c[1], lin_c[2], 1.0)
    bsdf_coach.inputs["Roughness"].default_value = float(coach_spec["roughness"])
    bsdf_coach.inputs["Metallic"].default_value = float(coach_spec.get("metallic", 0.05))
    if "Specular IOR Level" in bsdf_coach.inputs:
        bsdf_coach.inputs["Specular IOR Level"].default_value = 0.45
    if "Coat Weight" in bsdf_coach.inputs:
        bsdf_coach.inputs["Coat Weight"].default_value = 0.35
        bsdf_coach.inputs["Coat Roughness"].default_value = 0.12

    # Procedural world-space Rolls-Royce Twin Coachline:
    # Z_line(X) = 0.391 - 0.015 * X (gracefully clears hip arch 0.375 m and sweeps to tail crest 0.395 m)
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geom.outputs["Position"], sep.inputs["Vector"])

    # Compute outward-facing exterior mask: dot(Normal, Position - (-0.05, 0.0, 0.35)) > 0
    sub_c = nt.nodes.new("ShaderNodeVectorMath")
    sub_c.operation = "SUBTRACT"
    sub_c.inputs[1].default_value = (-0.05, 0.0, 0.35)
    nt.links.new(geom.outputs["Position"], sub_c.inputs[0])

    dot_out = nt.nodes.new("ShaderNodeVectorMath")
    dot_out.operation = "DOT_PRODUCT"
    nt.links.new(geom.outputs["Normal"], dot_out.inputs[0])
    nt.links.new(sub_c.outputs["Vector"], dot_out.inputs[1])

    ext_mask = nt.nodes.new("ShaderNodeMapRange")
    ext_mask.clamp = True
    ext_mask.inputs["From Min"].default_value = 0.01
    ext_mask.inputs["From Max"].default_value = 0.03
    nt.links.new(dot_out.outputs["Value"], ext_mask.inputs["Value"])

    # Z_line = 0.391 - 0.015 * X
    mul_x = nt.nodes.new("ShaderNodeMath")
    mul_x.operation = "MULTIPLY"
    mul_x.inputs[1].default_value = -0.015
    nt.links.new(sep.outputs["X"], mul_x.inputs[0])

    z_line = nt.nodes.new("ShaderNodeMath")
    z_line.operation = "ADD"
    z_line.inputs[1].default_value = 0.391
    nt.links.new(mul_x.outputs["Value"], z_line.inputs[0])

    # Helper to build a crisp anti-aliased horizontal band around (z_line + z_offset) with x_min rear taper
    def add_band(z_offset: float, half_w: float, x_tail_end: float, x_tail_fade: float):
        zc = z_line.outputs["Value"]
        if abs(z_offset) > 1e-9:
            add_o = nt.nodes.new("ShaderNodeMath")
            add_o.operation = "ADD"
            add_o.inputs[1].default_value = z_offset
            nt.links.new(zc, add_o.inputs[0])
            zc = add_o.outputs["Value"]

        dz = nt.nodes.new("ShaderNodeMath")
        dz.operation = "SUBTRACT"
        nt.links.new(sep.outputs["Z"], dz.inputs[0])
        nt.links.new(zc, dz.inputs[1])

        adz = nt.nodes.new("ShaderNodeMath")
        adz.operation = "ABSOLUTE"
        nt.links.new(dz.outputs["Value"], adz.inputs[0])

        # Inverted ramp: 1 inside half_w, smoothly 0 outside half_w + 0.25mm
        band = nt.nodes.new("ShaderNodeMapRange")
        band.clamp = True
        band.interpolation_type = "SMOOTHSTEP"
        band.inputs["From Min"].default_value = half_w
        band.inputs["From Max"].default_value = half_w + 0.0003
        band.inputs["To Min"].default_value = 1.0
        band.inputs["To Max"].default_value = 0.0
        nt.links.new(adz.outputs["Value"], band.inputs["Value"])

        # Rear X taper mask: 0 for X <= x_tail_end, 1 for X >= x_tail_fade
        x_mask = nt.nodes.new("ShaderNodeMapRange")
        x_mask.clamp = True
        x_mask.interpolation_type = "SMOOTHSTEP"
        x_mask.inputs["From Min"].default_value = x_tail_end
        x_mask.inputs["From Max"].default_value = x_tail_fade
        nt.links.new(sep.outputs["X"], x_mask.inputs["Value"])

        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(band.outputs["Result"], mul.inputs[0])
        nt.links.new(x_mask.outputs["Result"], mul.inputs[1])
        return mul.outputs["Value"]

    # Primary bespoke coachline (3.8 mm wide, terminates gracefully at X=-0.272 m before tail tip)
    b1 = add_band(z_offset=0.0, half_w=0.0019, x_tail_end=-0.276, x_tail_fade=-0.264)
    # Companion Rolls-Royce hairline (1.5 mm wide, 5.2 mm below primary, staggered finish at X=-0.236 m)
    b2 = add_band(z_offset=-0.0052, half_w=0.00075, x_tail_end=-0.242, x_tail_fade=-0.230)

    comb = nt.nodes.new("ShaderNodeMath")
    comb.operation = "MAXIMUM"
    nt.links.new(b1, comb.inputs[0])
    nt.links.new(b2, comb.inputs[1])

    final_fac = nt.nodes.new("ShaderNodeMath")
    final_fac.operation = "MULTIPLY"
    nt.links.new(comb.outputs["Value"], final_fac.inputs[0])
    nt.links.new(ext_mask.outputs["Result"], final_fac.inputs[1])

    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(final_fac.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(bsdf_shell.outputs["BSDF"], mix.inputs[1])
    nt.links.new(bsdf_coach.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])


def setup_blender_scene(samples: int, resolution: int, exposure: float, device: str = "CPU") -> dict:
    """Import GLB, configure Cycles (CPU 20-thread or CUDA), studio lighting, and camera."""
    import os
    import bpy
    from mathutils import Vector

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    t0 = time.monotonic()
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_GLB))
    import_s = time.monotonic() - t0

    mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
    assert len(mesh_objs) == 2529, f"Expected 2529 meshes, got {len(mesh_objs)}"

    # Compute exact world-space bounding box of robot
    bmin = [1e9, 1e9, 1e9]
    bmax = [-1e9, -1e9, -1e9]
    role_counts: dict[str, int] = {}
    for o in mesh_objs:
        for c in o.bound_box:
            wc = o.matrix_world @ Vector(c)
            for i in range(3):
                bmin[i] = min(bmin[i], wc[i])
                bmax[i] = max(bmax[i], wc[i])
        for slot in o.material_slots:
            if slot.material:
                mname = slot.material.name
                assert mname in GLB_MAT_TO_ROLE, f"Unmapped GLB material: {mname}"
                r = GLB_MAT_TO_ROLE[mname]
                role_counts[r] = role_counts.get(r, 0) + 1

    # Assign dedicated Blender material to main torso shell pieces for optional Rolls-Royce coachline
    torso_coach_mat = bpy.data.materials.new(name="Role / torso_coachline_shell")
    torso_coach_mat.use_nodes = True
    coach_obj_count = 0
    for o in mesh_objs:
        base_name = o.name.split(".")[0]
        if o.name in TORSO_COACHLINE_OBJECTS or base_name in TORSO_COACHLINE_OBJECTS:
            o.data.materials.clear()
            o.data.materials.append(torso_coach_mat)
            coach_obj_count += 1
    print(f"[BLENDER] Assigned torso coachline shader to {coach_obj_count} shell objects", flush=True)

    # Apply common materials once
    for mname, role in GLB_MAT_TO_ROLE.items():
        if role in COMMON_MATERIALS and mname in bpy.data.materials:
            spec_lvl = 0.55 if role in ("glass", "lens", "metal", "metal_connector") else 0.30
            set_principled_material(bpy.data.materials[mname], COMMON_MATERIALS[role], specular_level=spec_lvl)

    # Shadow-catcher ground plane directly beneath the soles (z = bmin[2])
    floor_z = float(bmin[2]) - 0.0002
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0.0, 0.0, floor_z))
    floor = bpy.context.object
    floor.name = "STUDIO_shadow_catcher"
    floor.is_shadow_catcher = True

    def aim_obj(obj, target):
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

    # Calibrated 3-point softbox + gentle overhead key for rich color & grounded contact shadow
    lights = [
        ("STUDIO_key", (1.35, -1.40, 1.55), 78.0, 1.45, (1.0, 0.99, 0.97), (0.0, 0.0, 0.34)),
        ("STUDIO_fill", (-1.15, -1.25, 1.00), 30.0, 1.90, (0.97, 0.99, 1.0), (0.0, 0.0, 0.34)),
        ("STUDIO_rim", (-1.20, 1.25, 1.40), 88.0, 0.95, (0.98, 0.99, 1.0), (0.0, 0.0, 0.36)),
        ("STUDIO_top", (0.04, -0.04, 1.95), 38.0, 1.85, (1.0, 1.0, 1.0), (0.0, 0.0, 0.20)),
    ]
    for lname, loc, power, size, col, target in lights:
        ldata = bpy.data.lights.new(lname, "AREA")
        ldata.energy = power
        ldata.shape = "DISK"
        ldata.size = size
        ldata.color = col
        lobj = bpy.data.objects.new(lname, ldata)
        bpy.context.collection.objects.link(lobj)
        lobj.location = loc
        aim_obj(lobj, target)

    # Controlled neutral studio environment (low enough to preserve rich darks & saturation)
    world = bpy.data.worlds.new("StudioWorld")
    world.use_nodes = True
    bg_node = world.node_tree.nodes["Background"]
    bg_node.inputs[0].default_value = (0.88, 0.90, 0.93, 1.0)
    bg_node.inputs[1].default_value = 0.32

    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = "CYCLES"
    threads = min(os.cpu_count() or 8, 20)
    scene.render.threads_mode = "FIXED"
    scene.render.threads = threads

    cuda_names = []
    if device == "CUDA":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "CUDA"
            if d.use:
                cuda_names.append(d.name)
        scene.cycles.device = "GPU" if cuda_names else "CPU"
    else:
        scene.cycles.device = "CPU"

    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.005
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.sample_clamp_indirect = 4.0
    scene.cycles.seed = 42

    # Separate Shadow Catcher pass via Compositor for silky-smooth, seamless ground shadows
    scene.view_layers[0].cycles.use_pass_shadow_catcher = True
    scene.use_nodes = True
    ct = scene.node_tree
    ct.nodes.clear()
    rl = ct.nodes.new("CompositorNodeRLayers")
    comp_out = ct.nodes.new("CompositorNodeComposite")
    ct.links.new(rl.outputs["Image"], comp_out.inputs["Image"])

    shadow_out = ct.nodes.new("CompositorNodeOutputFile")
    shadow_out.base_path = str(RGBA_CACHE_DIR)
    shadow_out.format.file_format = "PNG"
    shadow_out.format.color_mode = "RGB"
    shadow_out.file_slots[0].path = "shadow_tmp_"
    ct.links.new(rl.outputs["Shadow Catcher"], shadow_out.inputs[0])

    scene.render.film_transparent = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = exposure

    # Flattering 3/4 standing perspective matching Figure 2 Panel A (62 mm lens)
    cam_data = bpy.data.cameras.new("StudioCamera")
    cam_data.lens = 62.0
    cam_data.sensor_width = 36.0
    cam_obj = bpy.data.objects.new("StudioCamera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Azimuth ~43 deg from +X toward -Y with balanced head/foot studio margin
    cam_loc = (1.16, -1.08, 0.60)
    cam_target = (-0.015, 0.0, 0.315)
    cam_obj.location = cam_loc
    aim_obj(cam_obj, cam_target)

    return {
        "import_seconds": round(import_s, 3),
        "mesh_count": len(mesh_objs),
        "bbox_min_m": [round(x, 5) for x in bmin],
        "bbox_max_m": [round(x, 5) for x in bmax],
        "floor_z_m": round(floor_z, 5),
        "cycles_device": scene.cycles.device,
        "cpu_threads": threads,
        "cuda_devices": cuda_names,
        "role_object_counts": role_counts,
        "camera": {
            "lens_mm": cam_data.lens,
            "location_m": list(cam_loc),
            "target_m": list(cam_target),
        },
        "shadow_out_node": shadow_out.name,
    }


def apply_colorway_to_scene(scheme: dict) -> None:
    import bpy

    mats = scheme["materials"]
    for mname, role in GLB_MAT_TO_ROLE.items():
        if role in mats and mname in bpy.data.materials:
            spec_lvl = 0.28 if role in ("shell", "accent", "eye_ring", "sole_accent") else 0.35
            set_principled_material(bpy.data.materials[mname], mats[role], specular_level=spec_lvl)
    torso_mat = bpy.data.materials.get("Role / torso_coachline_shell")
    if torso_mat is not None:
        build_torso_coachline_material(torso_mat, mats["shell"], mats.get("coachline"))


def render_colorways_blender(
    colorway_ids: list[str], samples: int, resolution: int, exposure: float, device: str = "CPU"
) -> dict:
    import shutil
    import bpy

    RGBA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    info = setup_blender_scene(samples=samples, resolution=resolution, exposure=exposure, device=device)
    shadow_node_name = info.pop("shadow_out_node")
    shadow_node = bpy.context.scene.node_tree.nodes[shadow_node_name]
    scene = bpy.context.scene

    timings = {}
    for cid in colorway_ids:
        scheme = next(c for c in COLORWAYS if c["id"] == cid)
        apply_colorway_to_scene(scheme)
        rgba_path = RGBA_CACHE_DIR / f"goose_v02_theme_{cid}_rgba.png"
        shadow_slot = f"shadow_{cid}_"
        shadow_node.file_slots[0].path = shadow_slot
        scene.render.filepath = str(rgba_path)
        t0 = time.monotonic()
        bpy.ops.render.render(write_still=True)
        timings[cid] = round(time.monotonic() - t0, 2)

        # Rename Blender's frame-suffixed shadow file (e.g., shadow_sky_0001.png) cleanly
        src_shadow = RGBA_CACHE_DIR / f"{shadow_slot}0001.png"
        dst_shadow = RGBA_CACHE_DIR / f"goose_v02_theme_{cid}_shadow.png"
        if src_shadow.exists():
            shutil.move(str(src_shadow), str(dst_shadow))
        print(f"[BLENDER] Rendered {cid} -> {rgba_path} ({timings[cid]}s)", flush=True)

    info["render_seconds"] = timings
    return info


def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = (
        [
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _tight_robot_crop(rgba_img):
    """Find horizontal & vertical bounding box of non-transparent pixels (robot + shadow)."""
    import numpy as np

    arr = np.asarray(rgba_img)
    # Use alpha > 8 to include soft contact shadow cleanly
    ys, xs = np.where(arr[:, :, 3] > 8)
    if len(xs) == 0:
        return rgba_img
    return rgba_img.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def _draw_swatch_pills(draw, center_x: int, y: int, hex_list: list[str], pill_r: int = 12, gap: int = 10):
    """Draw minimalist circular color swatch pills with subtle border."""
    total_w = len(hex_list) * (2 * pill_r) + (len(hex_list) - 1) * gap
    x0 = center_x - total_w // 2
    for idx, hx in enumerate(hex_list):
        cx = x0 + idx * (2 * pill_r + gap) + pill_r
        rgb = _hex_to_rgb(hx)
        draw.ellipse(
            [cx - pill_r, y - pill_r, cx + pill_r, y + pill_r],
            fill=rgb,
            outline=(210, 214, 222),
            width=2,
        )


def _build_combined_rgba(rgba_path: Path, shadow_path: Path, target_size: int):
    """Combine crisp robot RGBA with smoothed, radially-faded Shadow Catcher pass."""
    import numpy as np
    from PIL import Image, ImageFilter

    robot = Image.open(rgba_path).convert("RGBA")
    if robot.size != (target_size, target_size):
        robot = robot.resize((target_size, target_size), Image.Resampling.LANCZOS)

    if not shadow_path.exists():
        return robot

    shadow_img = Image.open(shadow_path).convert("L")
    if shadow_img.size != (target_size, target_size):
        shadow_img = shadow_img.resize((target_size, target_size), Image.Resampling.LANCZOS)

    # Smooth out Monte Carlo shadow noise before thresholding/fading
    blur_r = max(3.0, target_size * 0.0045)
    shadow_smooth = shadow_img.filter(ImageFilter.GaussianBlur(radius=blur_r))
    s_arr = np.asarray(shadow_smooth, dtype=np.float32) / 255.0

    # Shadow Catcher pass is ~1.0 where fully lit and <1.0 in shadow; subtract ambient floor cleanly
    shadow_alpha = np.clip((0.945 - s_arr) / 0.945, 0.0, 1.0)
    # Soft gamma curve so core contact shadow under shoes stays grounded while penumbra fades cleanly
    shadow_alpha = np.power(shadow_alpha, 1.45) * 0.62

    # Elliptical radial falloff anchored to the feet, strictly bounded inside canvas edges
    r_arr = np.asarray(robot)
    ys, xs = np.where(r_arr[:, :, 3] > 128)
    if len(xs) > 0:
        x_min, x_max = float(xs.min()), float(xs.max())
        y_min, y_max = float(ys.min()), float(ys.max())
        cx = 0.5 * (x_min + x_max)
        cy = y_max - 0.04 * (y_max - y_min)
        rx = min(0.42 * target_size, max(0.24 * target_size, 0.56 * (x_max - x_min)))
        ry = min(max(0.06 * target_size, (target_size - 12 - cy)), 0.14 * (y_max - y_min))
    else:
        cx, cy = target_size * 0.5, target_size * 0.85
        rx, ry = target_size * 0.28, target_size * 0.11

    yy, xx = np.mgrid[0:target_size, 0:target_size]
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    radial = np.clip(1.0 - np.clip((dist - 0.25) / 0.75, 0.0, 1.0), 0.0, 1.0)
    radial = radial * radial * (3.0 - 2.0 * radial)  # smoothstep to exact 0.0 before canvas edge
    shadow_alpha *= radial
    shadow_alpha[shadow_alpha < 0.008] = 0.0  # eliminate sub-1% residual haze on white cards

    # Cool neutral studio shadow color (#1C222B)
    shadow_rgba = np.zeros((target_size, target_size, 4), dtype=np.uint8)
    shadow_rgba[:, :, 0] = 28
    shadow_rgba[:, :, 1] = 34
    shadow_rgba[:, :, 2] = 43
    shadow_rgba[:, :, 3] = np.clip(shadow_alpha * 255.0, 0, 255).astype(np.uint8)

    canvas = Image.fromarray(shadow_rgba, mode="RGBA")
    canvas.alpha_composite(robot)
    return canvas


def compose_outputs(target_size: int = 1600) -> dict:
    """Composite #F8F9FB individual renders, 1x4 squad banner (3600x1150), 2x2 grid (2400x2400), and JSON."""
    from PIL import Image, ImageDraw

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rgba_by_id = {}
    output_files = {}

    for scheme in COLORWAYS:
        cid = scheme["id"]
        rgba_path = RGBA_CACHE_DIR / f"goose_v02_theme_{cid}_rgba.png"
        shadow_path = RGBA_CACHE_DIR / f"goose_v02_theme_{cid}_shadow.png"
        if not rgba_path.exists():
            raise FileNotFoundError(f"Missing RGBA render: {rgba_path}")
        rgba = _build_combined_rgba(rgba_path, shadow_path, target_size=target_size)
        rgba_by_id[cid] = rgba

        # Composite onto crisp #F8F9FB studio backdrop
        bg = Image.new("RGBA", rgba.size, (*STUDIO_BG_RGB, 255))
        comp = Image.alpha_composite(bg, rgba).convert("RGB")
        out_path = OUT_DIR / f"goose_v02_theme_{cid}.png"
        comp.save(out_path, format="PNG", optimize=True)
        output_files[f"theme_{cid}"] = out_path
        print(f"[COMPOSE] Saved {out_path} ({comp.size})", flush=True)

    # 1. 1x4 Horizontal Squad Banner (3600 x 1150 px) matching Figure 3
    squad_w, squad_h = 3600, 1150
    squad = Image.new("RGBA", (squad_w, squad_h), (*STUDIO_BG_RGB, 255))
    draw = ImageDraw.Draw(squad)

    font_title = _load_font(34, bold=True)
    font_sub = _load_font(20, bold=False)
    font_header = _load_font(30, bold=True)
    font_caption = _load_font(19, bold=False)

    # Clean minimalist top header
    draw.text(
        (90, 42),
        "GOOSE V0.2  ·  MICRODUCK-INSPIRED STUDIO COLORWAYS",
        fill=(28, 34, 44),
        font=font_header,
    )
    draw.text(
        (squad_w - 90, 48),
        "assembly_finish_005  |  2,529 CAD Parts",
        fill=(108, 116, 128),
        font=font_caption,
        anchor="ra",
    )
    draw.line([(90, 92), (squad_w - 90, 92)], fill=(224, 228, 236), width=2)

    # Place all 4 robots at identical scale & aligned baseline (with subtle overlap allowance)
    margin_x = 120
    usable_w = squad_w - 2 * margin_x
    col_w = usable_w / 4.0
    robot_top_y = 110
    robot_bot_y = 955
    robot_box_h = robot_bot_y - robot_top_y

    # Use full uncropped scale consistency: scale the 1600x1600 canvas cleanly
    # Check max tight crop height across all 4 so scale is identical
    tight_crops = {cid: _tight_robot_crop(img) for cid, img in rgba_by_id.items()}
    max_crop_h = max(c.height for c in tight_crops.values())
    max_crop_w = max(c.width for c in tight_crops.values())
    scale = min(robot_box_h / max_crop_h, (col_w * 0.96) / max_crop_w)

    for idx, scheme in enumerate(COLORWAYS):
        cid = scheme["id"]
        crop = tight_crops[cid]
        new_w = round(crop.width * scale)
        new_h = round(crop.height * scale)
        resized = crop.resize((new_w, new_h), Image.Resampling.LANCZOS)
        cx = round(margin_x + (idx + 0.5) * col_w)
        px = cx - new_w // 2
        # Align all 4 by bottom edge (ground plane + contact shadow)
        py = robot_bot_y - new_h
        squad.alpha_composite(resized, dest=(px, py))

        # Minimalist label + color swatch pills underneath
        mats = scheme["materials"]
        swatches = [
            mats["shell"]["srgb_hex"],
            mats["accent"]["srgb_hex"],
            mats["eye_ring"]["srgb_hex"],
        ]
        if mats["sole_accent"]["srgb_hex"].upper() != mats["eye_ring"]["srgb_hex"].upper():
            swatches.append(mats["sole_accent"]["srgb_hex"])
        swatches.append(mats["dark_mechanics"]["srgb_hex"])

        draw.text((cx, 998), scheme["label_full"], fill=(26, 31, 39), font=font_title, anchor="mm")
        draw.text((cx, 1036), scheme["subtitle"], fill=(104, 112, 126), font=font_sub, anchor="mm")
        _draw_swatch_pills(draw, cx, 1082, swatches, pill_r=12, gap=12)

    squad_path = OUT_DIR / "goose_v02_four_colorways_squad.png"
    squad.convert("RGB").save(squad_path, format="PNG", optimize=True)
    output_files["squad"] = squad_path
    print(f"[COMPOSE] Saved {squad_path} ({squad.size})", flush=True)

    # 2. 2x2 Showcase Grid (2400 x 2400 px)
    grid_sz = 2400
    grid = Image.new("RGBA", (grid_sz, grid_sz), (*STUDIO_BG_RGB, 255))
    gdraw = ImageDraw.Draw(grid)
    g_title = _load_font(40, bold=True)
    g_sub = _load_font(23, bold=False)
    g_card_title = _load_font(34, bold=True)
    g_hex = _load_font(20, bold=False)

    gdraw.text(
        (96, 52),
        "GOOSE V0.2  ·  4-COLORWAY STUDIO THEME SUITE",
        fill=(24, 29, 38),
        font=g_title,
    )
    gdraw.text(
        (96, 102),
        "MicroDuck-Inspired Finish Blocking · Blender 4.0.2 Cycles · assembly_finish_005",
        fill=(102, 110, 124),
        font=g_sub,
    )
    gdraw.line([(96, 146), (grid_sz - 96, 146)], fill=(222, 226, 234), width=2)

    pad_outer = 96
    gap_card = 44
    top_y = 176
    bot_y = 2324
    card_w = (grid_sz - 2 * pad_outer - gap_card) // 2
    card_h = (bot_y - top_y - gap_card) // 2

    for idx, scheme in enumerate(COLORWAYS):
        cid = scheme["id"]
        row, col = divmod(idx, 2)
        x0 = pad_outer + col * (card_w + gap_card)
        y0 = top_y + row * (card_h + gap_card)
        x1 = x0 + card_w
        y1 = y0 + card_h

        # Subtle white elevated card on #F8F9FB canvas
        gdraw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=24,
            fill=(255, 255, 255, 255),
            outline=(226, 230, 238, 255),
            width=2,
        )

        crop = tight_crops[cid]
        avail_h = card_h - 190
        avail_w = card_w - 80
        sc = min(avail_h / crop.height, avail_w / crop.width)
        rw, rh = round(crop.width * sc), round(crop.height * sc)
        resized = crop.resize((rw, rh), Image.Resampling.LANCZOS)
        rx = x0 + (card_w - rw) // 2
        ry = y0 + 28 + (avail_h - rh) // 2
        grid.alpha_composite(resized, dest=(rx, ry))

        # Card footer label + swatches + hex summary
        cx = x0 + card_w // 2
        mats = scheme["materials"]
        swatches = [
            mats["shell"]["srgb_hex"],
            mats["accent"]["srgb_hex"],
            mats["eye_ring"]["srgb_hex"],
        ]
        if mats["sole_accent"]["srgb_hex"].upper() != mats["eye_ring"]["srgb_hex"].upper():
            swatches.append(mats["sole_accent"]["srgb_hex"])
        swatches.append(mats["dark_mechanics"]["srgb_hex"])

        gdraw.text((cx, y1 - 122), scheme["label_full"], fill=(26, 31, 39), font=g_card_title, anchor="mm")
        _draw_swatch_pills(gdraw, cx, y1 - 76, swatches, pill_r=12, gap=12)
        hex_summary = "  ·  ".join(swatches)
        gdraw.text((cx, y1 - 36), hex_summary, fill=(108, 116, 128), font=g_hex, anchor="mm")

    grid_path = OUT_DIR / "goose_v02_four_colorways_grid.png"
    grid.convert("RGB").save(grid_path, format="PNG", optimize=True)
    output_files["grid"] = grid_path
    print(f"[COMPOSE] Saved {grid_path} ({grid.size})", flush=True)

    return {k: str(v.relative_to(ROOT)) for k, v in output_files.items()}, output_files


def write_theme_config_json(output_files: dict[str, Path], blender_info: dict | None = None) -> Path:
    """Write formal microduck_four_colorways_005.json with exact color specs & SHA-256 hashes."""
    enriched_schemes = []
    for scheme in COLORWAYS:
        mats_out = {}
        for role, spec in scheme["materials"].items():
            mats_out[role] = {
                "srgb_hex": spec["srgb_hex"],
                "linear_rgb": [round(x, 6) for x in srgb_hex_to_linear(spec["srgb_hex"])],
                "roughness": spec["roughness"],
                "metallic": spec["metallic"],
            }
        enriched_schemes.append(
            {
                "id": scheme["id"],
                "label": scheme["label"],
                "label_full": scheme["label_full"],
                "label_zh": scheme["label_zh"],
                "subtitle": scheme["subtitle"],
                "materials": mats_out,
            }
        )

    common_out = {}
    for role, spec in COMMON_MATERIALS.items():
        lin = spec_to_linear_rgb(spec)
        entry = {
            "linear_rgb": [round(x, 6) for x in lin],
            "roughness": spec["roughness"],
            "metallic": spec["metallic"],
        }
        if "srgb_hex" in spec:
            entry["srgb_hex"] = spec["srgb_hex"]
        common_out[role] = entry

    rendered_assets = {}
    for key, p in output_files.items():
        rendered_assets[key] = {
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
        }

    payload = {
        "schema_version": 1,
        "robot_id": "goose_v0_2",
        "assembly_target": "assembly_finish_005",
        "source_geometry": {
            "path": str(SOURCE_GLB.relative_to(ROOT)),
            "sha256": sha256_file(SOURCE_GLB),
            "mesh_count": 2529,
        },
        "v01_palette_reference": {
            "path": str(V01_PALETTE.relative_to(ROOT)),
            "sha256": sha256_file(V01_PALETTE),
        },
        "studio_render": {
            "engine": "CYCLES",
            "device": (blender_info or {}).get("cycles_device", "CPU"),
            "view_transform": "AgX",
            "look": "AgX - Punchy",
            "background_srgb_hex": STUDIO_BG_HEX,
            "blender_info": blender_info or {},
        },
        "glb_material_role_map": GLB_MAT_TO_ROLE,
        "joint_cap_object_roles": JOINT_CAP_OBJECT_ROLES,
        "common_materials": common_out,
        "schemes": enriched_schemes,
        "rendered_assets": rendered_assets,
    }
    json_path = OUT_DIR / "microduck_four_colorways_005.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"[JSON] Saved {json_path}", flush=True)
    return json_path


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--colorways",
        nargs="+",
        choices=[c["id"] for c in COLORWAYS],
        default=[c["id"] for c in COLORWAYS],
    )
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--resolution", type=int, default=1600)
    ap.add_argument("--exposure", type=float, default=-0.92)
    ap.add_argument("--device", choices=["CPU", "CUDA"], default="CPU")
    ap.add_argument("--compose-only", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args(argv)

    blender_info = None
    if not args.compose_only:
        blender_info = render_colorways_blender(
            colorway_ids=args.colorways,
            samples=args.samples,
            resolution=args.resolution,
            exposure=args.exposure,
            device=args.device,
        )
        info_path = RGBA_CACHE_DIR / "blender_render_info.json"
        info_path.write_text(json.dumps(blender_info, indent=2) + "\n")

    if not args.render_only:
        if blender_info is None and (RGBA_CACHE_DIR / "blender_render_info.json").exists():
            blender_info = json.loads((RGBA_CACHE_DIR / "blender_render_info.json").read_text())
        _, output_files = compose_outputs(target_size=args.resolution)
        write_theme_config_json(output_files, blender_info=blender_info)


if __name__ == "__main__":
    main()
