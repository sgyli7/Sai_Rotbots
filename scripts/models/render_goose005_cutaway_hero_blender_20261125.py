"""Render Goose V0.2 (assembly_finish_005) NAO-style Half-Cutaway / Half-Exterior
hero views and hip-bay macro close-up in Blender 4.0.2 Cycles.

Usage:
  /home/ethan/Softwares/ai-3d-local/scripts/blender.sh -b --python \
      scripts/models/render_goose005_cutaway_hero_blender_20261125.py -- \
      --mode all --samples 160
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
GLB_PATH = ROOT / "robots/goose_v0_2/cad/exports/appearance_finish_execution_20261118_001/assembly/assembly_finish_sky_003.glb"
OUT_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/showcase_renders/cutaway_poster"
MESH_005_DIR = OUT_DIR / "meshes_005"
SCRATCH_SHADOW_DIR = ROOT / ".scratch/goose005_cutaway_shadows"


def srgb_to_linear(hex_str: str) -> tuple[float, float, float]:
    h = hex_str.lstrip("#")
    vals = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in vals)


def make_pbr(
    name: str,
    hex_color: str,
    roughness: float = 0.4,
    metallic: float = 0.0,
    coat: float = 0.0,
    specular: float = 0.30,
    emission_strength: float = 0.0,
):
    import bpy

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    rgb = srgb_to_linear(hex_color)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    if "Emission Color" in bsdf.inputs and emission_strength > 0:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.diffuse_color = (*rgb, 1.0)
    return mat


def configure_cycles_render(samples: int):
    import bpy

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    # Local Blender 4.0.2 CUDA kernel config.h caps arch at <= 899 (sm_121 unsupported) and has no OIDN
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 20
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.007
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 3
    scene.cycles.transparent_max_bounces = 4
    scene.cycles.sample_clamp_indirect = 4.0
    scene.cycles.filter_glossy = 1.0
    scene.cycles.seed = 42
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = -0.45
    print(f"Cycles configured: device={scene.cycles.device}, threads=20, samples={samples}", flush=True)


def aim(obj, target: tuple[float, float, float]):
    from mathutils import Vector

    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_materials() -> dict:
    return {
        # Exterior Warm Cream + Tangerine Orange + Golden Amber (user-selected flagship theme!)
        "ext_cream": make_pbr("Ext_WarmCream", "#F2E5CF", roughness=0.38, metallic=0.0, specular=0.26),
        "ext_dark_charcoal": make_pbr("Ext_DarkCharcoal", "#1B1F24", roughness=0.40, metallic=0.25, specular=0.30),
        "ext_tangerine": make_pbr("Ext_TangerineOrange", "#FF6A13", roughness=0.34, metallic=0.0, specular=0.24),
        "ext_golden_amber": make_pbr("Ext_GoldenAmber", "#FFC32B", roughness=0.32, metallic=0.0, specular=0.26),
        "ext_rubber": make_pbr("Ext_Rubber", "#14181D", roughness=0.72, metallic=0.0, specular=0.22),
        "ext_faceplate": make_pbr("Ext_Faceplate", "#1B1F24", roughness=0.40, metallic=0.25, specular=0.28),
        "ext_cut_edge": make_pbr("Ext_CutEdge", "#FAF5EC", roughness=0.26, metallic=0.15),
        "ext_cut_dark": make_pbr("Ext_CutDark", "#9AA5B4", roughness=0.28, metallic=0.25),
        "ext_cut_orange": make_pbr("Ext_CutOrange", "#FF9A56", roughness=0.30, metallic=0.10),
        "ext_cut_amber": make_pbr("Ext_CutAmber", "#FFE07A", roughness=0.30, metallic=0.10),
        # Optics
        "optic_glass": make_pbr("Optic_Glass", "#040812", roughness=0.04, metallic=0.40, coat=1.0, specular=0.60),
        # New 005 CAD Hardware
        "cad005_bridge_billet": make_pbr("CAD005_Al7075_Billet", "#EBC368", roughness=0.20, metallic=0.88, specular=0.55),
        "cad005_yoke_steel": make_pbr("CAD005_Steel_Yoke", "#B4BECB", roughness=0.24, metallic=0.90, specular=0.55),
        "cad005_fuse_guard": make_pbr("CAD005_FuseGuard_Amber", "#F09C24", roughness=0.28, metallic=0.10, coat=0.5),
        "cad005_harness_orange": make_pbr("CAD005_Harness_Orange", "#E8562A", roughness=0.38, metallic=0.0),
        # Internal Engineering Hardware
        "int_pcb_emerald": make_pbr("Int_PCB_Emerald", "#1C6F43", roughness=0.28, metallic=0.05, coat=0.35),
        "int_ic_black": make_pbr("Int_IC_Black", "#161920", roughness=0.36, metallic=0.12),
        "int_copper": make_pbr("Int_Copper_Coldplate", "#C87542", roughness=0.24, metallic=0.92, specular=0.55),
        "int_gunmetal": make_pbr("Int_Gunmetal_Actuator", "#1E232A", roughness=0.32, metallic=0.68, specular=0.45),
        "int_frame_titanium": make_pbr("Int_Frame_Titanium", "#2B323D", roughness=0.34, metallic=0.74, specular=0.45),
        "int_silver": make_pbr("Int_Silver_Bearing", "#CCD4E0", roughness=0.22, metallic=0.92, specular=0.55),
        "int_battery_blue": make_pbr("Int_Battery_Cobalt", "#1E468C", roughness=0.38, metallic=0.05),
        "int_contactor_slate": make_pbr("Int_Contactor_Slate", "#2D4258", roughness=0.34, metallic=0.15),
        "int_wire_copper": make_pbr("Int_Wire_Insulation", "#D65A28", roughness=0.40, metallic=0.05),
        "int_g10": make_pbr("Int_G10_Olive", "#556E5C", roughness=0.48, metallic=0.0),
    }


def classify_object_material(name: str, orig_mat: str, mats: dict):
    nl = name.lower()
    if orig_mat in ("Sky finish / glass", "Sky finish / lens") or "camera_catalog_" in nl:
        return mats["optic_glass"]
    if name == "camera_open_eye_bezel":
        return mats["ext_golden_amber"]
    if name == "camera_fastened_open_face":
        return mats["ext_faceplate"]
    if orig_mat == "Sky finish / accent" or "new_upper_front_" in nl or "lower_grip_shell" in nl or "ar_041_functional_shell" in nl:
        return mats["ext_tangerine"]
    if orig_mat == "Sky finish / sole_trim" or name.endswith("flat_rounded_sole"):
        return mats["ext_golden_amber"]
    if orig_mat == "Sky finish / rubber" or "grip_cassette_pad" in nl:
        return mats["ext_rubber"]
    if orig_mat in ("Sky finish / shell", "Sky finish / theme_structural_dark"):
        return mats["ext_cream"]
    if orig_mat == "Sky finish / structural_dark":
        return mats["ext_dark_charcoal"]

    if (
        orig_mat == "Sky finish / pcb_reference"
        or nl.endswith("_oem_000")
        or any(k in nl for k in ["pcb", "radxa_zero_3w", "perfboard", "tinybms_high_power_body", "audio_buck", "logic_buck", "servo_buck", "imu_wt901c"])
    ):
        return mats["int_pcb_emerald"]
    if "usb_hub_hat_b_oem_" in nl:
        return mats["int_ic_black"]
    if any(k in nl for k in ["brake_sink", "coldplate", "thermal_sink_top", "c110", "_cu_", "make_current_choke"]):
        return mats["int_copper"]
    if "battery_" in nl and "nominal" in nl:
        return mats["int_battery_blue"]
    if any(k in nl for k in ["k1_main_load", "k2_precharge", "k3_manual", "k4_load"]):
        return mats["int_contactor_slate"]
    if any(k in nl for k in ["fit221", "harness", "breakout", "wire"]):
        return mats["int_wire_copper"]
    if "g10" in nl:
        return mats["int_g10"]
    if any(k in nl for k in ["ak45", "catalog_case", "stator", "rotor", "motor", "output_disc", "output_envelope", "xc330", "fork", "spider", "fan_body"]):
        return mats["int_gunmetal"]
    if any(k in nl for k in ["sideplate", "bulkhead", "bracket", "clamp", "rail", "carrier", "cradle", "saddle", "receiving_frame"]):
        return mats["int_frame_titanium"]
    if orig_mat in ("Sky finish / metal", "Sky finish / metal_connector") or any(
        k in nl for k in ["bearing", "retainer", "shaft", "screw", "bolt", "washer", "nut", "pin", "adapter", "bridge"]
    ):
        return mats["int_silver"]
    return mats["int_gunmetal"]


def split_sole_trim_and_tread(obj, trim_mat, tread_mat):
    """Bisect sole mesh cleanly along a horizontal Z plane so the purple/rubber seam is razor-sharp."""
    import bmesh
    from mathutils import Vector

    mesh = obj.data
    mw = obj.matrix_world
    mw_inv = mw.inverted()
    zs = [(mw @ v.co).z for v in mesh.vertices]
    z_split = min(zs) + 0.42 * (max(zs) - min(zs))

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.transform(bm, matrix=mw, verts=bm.verts)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        plane_co=Vector((0.0, 0.0, z_split)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=False,
        clear_outer=False,
    )
    bmesh.ops.transform(bm, matrix=mw_inv, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()

    mesh.materials.clear()
    mesh.materials.append(trim_mat)
    mesh.materials.append(tread_mat)
    for poly in mesh.polygons:
        c_world = mw @ poly.center
        poly.material_index = 0 if c_world.z >= z_split else 1
    mesh.update()


def import_stl_object(stl_path: Path, name: str, mat, smooth: bool = False):
    import bpy

    bpy.ops.wm.stl_import(filepath=str(stl_path))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def boolean_cut_y0(obj, cutter, cut_mat):
    import bpy

    mod = obj.modifiers.new("CutY0", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

    if cut_mat not in list(obj.data.materials):
        obj.data.materials.append(cut_mat)
    cut_idx = list(obj.data.materials).index(cut_mat)
    mw = obj.matrix_world
    rot = mw.to_3x3()
    for poly in obj.data.polygons:
        cw = mw @ poly.center
        nw = (rot @ poly.normal).normalized()
        if abs(cw.y) < 0.00045 and abs(nw.y) > 0.90:
            poly.material_index = cut_idx


def setup_studio(theme: str):
    import bpy

    for obj in list(bpy.data.objects):
        if obj.type in ("LIGHT", "CAMERA") or obj.name.startswith("STUDIO_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    scene = bpy.context.scene
    world = bpy.data.worlds.new(f"World_{theme}")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    if theme == "dark":
        bg.inputs[0].default_value = (*srgb_to_linear("#161E2C"), 1.0)
        bg.inputs[1].default_value = 0.34
    else:
        bg.inputs[0].default_value = (*srgb_to_linear("#EEF2F7"), 1.0)
        bg.inputs[1].default_value = 0.36
    scene.world = world

    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0.0, 0.0, -0.0152))
    floor = bpy.context.active_object
    floor.name = "STUDIO_shadow_catcher"
    floor.is_shadow_catcher = True

    if theme == "dark":
        lights = [
            ("key_front", (1.40, -1.25, 1.50), 76.0, 1.45, "#FFFDF8"),
            ("fill_cutaway", (0.50, -1.55, 0.50), 42.0, 1.55, "#EAF4FF"),
            ("top_softbox", (0.04, -0.10, 1.90), 36.0, 1.80, "#FFFFFF"),
            ("rim_cyan", (-1.15, -0.95, 1.15), 86.0, 0.85, "#6AD0FF"),
            ("rim_violet", (-0.95, 1.25, 1.20), 96.0, 0.90, "#B084FF"),
            ("hip_bay_accent", (0.18, -0.70, 0.65), 18.0, 0.45, "#FFF6E5"),
        ]
    else:
        lights = [
            ("key_front", (1.35, -1.35, 1.55), 78.0, 1.45, "#FFFDF9"),
            ("fill_cutaway", (-0.95, -1.30, 0.95), 34.0, 1.85, "#F5F9FF"),
            ("top_softbox", (0.04, -0.04, 1.95), 38.0, 1.85, "#FFFFFF"),
            ("rim_back", (-1.20, 1.25, 1.40), 86.0, 0.95, "#F4F2FF"),
            ("hip_bay_accent", (0.18, -0.70, 0.65), 14.0, 0.45, "#FFF9EE"),
        ]

    for lname, loc, energy, size, hex_c in lights:
        ldata = bpy.data.lights.new(name=f"STUDIO_{lname}", type="AREA")
        ldata.energy = energy
        ldata.shape = "DISK"
        ldata.size = size
        ldata.color = srgb_to_linear(hex_c)
        lobj = bpy.data.objects.new(name=ldata.name, object_data=ldata)
        bpy.context.collection.objects.link(lobj)
        lobj.location = loc
        aim(lobj, (-0.015, 0.0, 0.34))

    SCRATCH_SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    scene.view_layers[0].cycles.use_pass_shadow_catcher = True
    scene.use_nodes = True
    ct = scene.node_tree
    ct.nodes.clear()
    rl = ct.nodes.new("CompositorNodeRLayers")
    comp_out = ct.nodes.new("CompositorNodeComposite")
    ct.links.new(rl.outputs["Image"], comp_out.inputs["Image"])
    shadow_out = ct.nodes.new("CompositorNodeOutputFile")
    shadow_out.base_path = str(SCRATCH_SHADOW_DIR)
    shadow_out.format.file_format = "PNG"
    shadow_out.format.color_mode = "RGB"
    shadow_out.file_slots[0].path = f"shadow_{theme}_"
    ct.links.new(rl.outputs["Shadow Catcher"], shadow_out.inputs[0])
    return shadow_out


def composite_backdrop(rgba_path: Path, shadow_path: Path, out_path: Path, theme: str):
    """Composite transparent RGBA + Shadow Catcher over a seamless dark vignette or crisp light studio."""
    import numpy as np
    from PIL import Image

    fg = np.asarray(Image.open(rgba_path).convert("RGBA"), dtype=np.float32) / 255.0
    h, w = fg.shape[:2]
    if shadow_path.exists():
        sh = np.asarray(Image.open(shadow_path).convert("RGB").resize((w, h), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
        p95 = float(np.percentile(sh, 95))
        sh = np.clip(sh / max(p95, 1e-4), 0.0, 1.0)
    else:
        sh = np.ones((h, w, 3), dtype=np.float32)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx / w - 0.50) * 1.35
    ny = (yy / h - 0.50) * 1.10
    r2 = np.clip(nx * nx + ny * ny, 0.0, 1.5)

    if theme == "dark":
        c_center = np.array([32, 42, 62], dtype=np.float32) / 255.0  # #202A3E subtle hero spotlight
        c_edge = np.array([12, 16, 25], dtype=np.float32) / 255.0    # #0C1019 deep obsidian edge
        t = np.clip(r2 / 0.85, 0.0, 1.0)[..., None]
        bg = c_center * (1.0 - t) + c_edge * t
        sh_strength = 0.72
        bg = bg * (1.0 - sh_strength + sh_strength * sh)
    else:
        bg = np.full((h, w, 3), np.array([248, 250, 252], dtype=np.float32) / 255.0)  # #F8FAFC
        sh_strength = 0.78
        bg = bg * (1.0 - sh_strength + sh_strength * sh)

    alpha = fg[..., 3:4]
    comp = fg[..., :3] * alpha + bg * (1.0 - alpha)
    comp_u8 = np.clip(comp * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(comp_u8, "RGB").save(out_path, optimize=True)
    return True


def build_scene(samples: int):
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    configure_cycles_render(samples)
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))

    mats = build_materials()

    hide_names = {
        "left_parent_yoke_003",
        "right_parent_yoke_003",
        "head_negative_retained",
        "head_negative_compression_sleeve",
        "b_lower_negative_matched_joint_008b",
        "paired_b_upper_negative_20261106",
        "new_upper_front_3",
        "right_thigh_primary_k_axial_edge",
        "right_knee_radial_grip_appearance_cover",
        "right_shin_primary_closeout_20261027",
        "right_ar_041_functional_shell",
        "right_visible_thigh_HP_small_service_cap",
        "right_hp_shell_compression_sleeve_0",
        "right_hp_shell_compression_sleeve_1",
        "right_hp_shell_compression_sleeve_2",
        "right_hp_shell_service_m2p5x8_0",
        "right_hp_shell_service_m2p5x8_1",
        "right_hp_shell_service_m2p5x8_2",
        "c_parent_original_capture_026_retained",
        "cold_hood_HT800_liner_01",
        "cold_hood_HT800_liner_03",
    }

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if obj.name in hide_names:
            obj.hide_render = True
            obj.hide_viewport = True
            continue

        orig_mat = obj.data.materials[0].name if obj.data.materials else ""
        if obj.name in ("left_flat_rounded_sole", "right_flat_rounded_sole"):
            split_sole_trim_and_tread(obj, mats["ext_golden_amber"], mats["ext_rubber"])
        else:
            mat = classify_object_material(obj.name, orig_mat, mats)
            obj.data.materials.clear()
            obj.data.materials.append(mat)

    # Half-space Y < 0 cutter box at exact sagittal midline Y=0
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -0.5, 0.35))
    cutter = bpy.context.active_object
    cutter.name = "CUTTER_Y0"
    cutter.scale = (2.0, 1.0, 2.0)
    bpy.ops.object.transform_apply(scale=True)
    cutter.hide_render = True
    cutter.hide_viewport = True

    cut_targets = [
        ("body016_front", mats["ext_cut_edge"]),
        ("body_continuous_rear", mats["ext_cut_edge"]),
        ("H_rear_cover_direct", mats["ext_cut_edge"]),
        ("head_positive_retained", mats["ext_cut_edge"]),
        ("a_child_complete_transition_008b", mats["ext_cut_edge"]),
        ("b_lower_positive_matched_joint_008b", mats["ext_cut_edge"]),
        ("paired_b_upper_positive_with_real_return_20261106", mats["ext_cut_edge"]),
        ("neck_parent_captured_front_skin_004", mats["ext_cut_edge"]),
        ("neck_yaw_moving_cover_sector_01", mats["ext_cut_edge"]),
        ("neck_yaw_moving_cover_sector_02", mats["ext_cut_edge"]),
        ("C_positive_trimmed", mats["ext_cut_dark"]),
        ("camera_open_eye_bezel", mats["ext_cut_amber"]),
        ("camera_fastened_open_face", mats["ext_cut_dark"]),
        ("new_upper_front_0", mats["ext_cut_orange"]),
        ("new_upper_front_2", mats["ext_cut_orange"]),
        ("preload048_lower_grip_shell_internal_preload_relief", mats["ext_cut_orange"]),
        ("passive_cold_hood", mats["ext_cut_dark"]),
        ("cold_hood_HT800_liner_00", mats["ext_cut_dark"]),
        ("fan_rear_antirecirculation_duct", mats["ext_cut_dark"]),
        ("fan_original_pose_highrail_carrier_002", mats["ext_cut_dark"]),
        ("rear_auxiliary_service_receiving_frame_056", mats["ext_cut_dark"]),
    ]
    for name, cmat in cut_targets:
        if name in bpy.data.objects:
            boolean_cut_y0(bpy.data.objects[name], cutter, cmat)

    # Slice right_flat_rounded_sole at its foot centerline Y=-0.155
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -0.655, 0.0))
    foot_cutter = bpy.context.active_object
    foot_cutter.name = "CUTTER_FOOT"
    foot_cutter.scale = (2.0, 1.0, 2.0)
    bpy.ops.object.transform_apply(scale=True)
    foot_cutter.hide_render = True
    foot_cutter.hide_viewport = True
    if "right_flat_rounded_sole" in bpy.data.objects:
        boolean_cut_y0(bpy.data.objects["right_flat_rounded_sole"], foot_cutter, mats["ext_cut_amber"])

    # Import assembly_finish_005 CAD STLs
    import_stl_object(MESH_005_DIR / "opt_b2_r2_anchored_bridge.stl", "CAD005_opt_b2_r2", mats["cad005_bridge_billet"], smooth=False)
    import_stl_object(MESH_005_DIR / "left_yoke_shell_relieved.stl", "CAD005_left_yoke_relieved", mats["cad005_yoke_steel"], smooth=True)
    import_stl_object(MESH_005_DIR / "right_yoke_shell_relieved.stl", "CAD005_right_yoke_relieved", mats["cad005_yoke_steel"], smooth=True)
    import_stl_object(MESH_005_DIR / "sanyo24_miniboard_pcb.stl", "CAD005_sanyo24_pcb", mats["int_pcb_emerald"], smooth=False)
    import_stl_object(MESH_005_DIR / "sanyo24_miniboard_components.stl", "CAD005_sanyo24_comps", mats["int_ic_black"], smooth=False)
    import_stl_object(MESH_005_DIR / "serviceable_fuse_pocket_guard.stl", "CAD005_fuse_pocket", mats["cad005_fuse_guard"], smooth=False)
    import_stl_object(MESH_005_DIR / "serviceable_fuse_breakout_harness.stl", "CAD005_fuse_harness", mats["cad005_harness_orange"], smooth=True)


def render_shot(
    out_path: Path,
    res_x: int,
    res_y: int,
    cam_loc: tuple[float, float, float],
    target: tuple[float, float, float],
    lens_mm: float,
    theme: str,
    shadow_out,
):
    import bpy

    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("RenderCam")
    cam_data.type = "PERSP"
    cam_data.lens = lens_mm
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.01
    cam_data.clip_end = 50.0
    cam_obj = bpy.data.objects.new("RenderCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = cam_loc
    aim(cam_obj, target)
    scene.camera = cam_obj
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True

    rgba_raw = SCRATCH_SHADOW_DIR / f"{out_path.stem}_rgba.png"
    shadow_out.file_slots[0].path = f"{out_path.stem}_sh_"
    scene.render.filepath = str(rgba_raw)
    bpy.ops.render.render(write_still=True)

    sh_candidates = sorted(SCRATCH_SHADOW_DIR.glob(f"{out_path.stem}_sh_*.png"))
    shadow_file = sh_candidates[-1] if sh_candidates else Path("")
    composite_backdrop(rgba_raw, shadow_file, out_path, theme)
    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    print(f"RENDERED {out_path} ({res_x}x{res_y})", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["preview", "all", "dark", "light", "closeup", "heroes"], default="all")
    ap.add_argument("--samples", type=int, default=160)
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    build_scene(args.samples)

    # 50/50 NAO-style half-exterior / half-cutaway 3/4 hero framing (~29 deg azimuth)
    hero_cam = (1.40, -0.78, 0.56)
    hero_target = (-0.015, 0.002, 0.325)
    hero_lens = 64.0

    # Elevated macro close-up looking down into torso/hip cutaway bay
    hip_cam = (0.04, -0.50, 0.62)
    hip_target = (-0.085, 0.010, 0.345)
    hip_lens = 54.0

    receipt = {"schema": "goose005_cutaway_renders_v1", "samples": args.samples, "renders": []}

    if args.mode == "preview":
        sh_out = setup_studio("dark")
        render_shot(OUT_DIR / "preview_cutaway_dark.png", 900, 1064, hero_cam, hero_target, hero_lens, "dark", sh_out)
        render_shot(OUT_DIR / "preview_hip_closeup.png", 900, 750, hip_cam, hip_target, hip_lens, "dark", sh_out)
        return

    if args.mode in ("all", "dark", "heroes"):
        sh_out = setup_studio("dark")
        p = OUT_DIR / "goose_v02_cutaway_hero_dark.png"
        render_shot(p, 2200, 2600, hero_cam, hero_target, hero_lens, "dark", sh_out)
        receipt["renders"].append({"name": p.name, "res": [2200, 2600], "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})

    if args.mode in ("all", "closeup"):
        sh_out = setup_studio("dark")
        p = OUT_DIR / "goose_v02_cutaway_hip_closeup.png"
        render_shot(p, 1800, 1500, hip_cam, hip_target, hip_lens, "dark", sh_out)
        receipt["renders"].append({"name": p.name, "res": [1800, 1500], "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    elif args.mode == "heroes":
        p_cl = OUT_DIR / "goose_v02_cutaway_hip_closeup.png"
        if p_cl.exists():
            receipt["renders"].append({"name": p_cl.name, "res": [1800, 1500], "sha256": hashlib.sha256(p_cl.read_bytes()).hexdigest()})

    if args.mode in ("all", "light", "heroes"):
        sh_out = setup_studio("light")
        p = OUT_DIR / "goose_v02_cutaway_hero_light.png"
        render_shot(p, 2200, 2600, hero_cam, hero_target, hero_lens, "light", sh_out)
        receipt["renders"].append({"name": p.name, "res": [2200, 2600], "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})

    receipt["elapsed_s"] = round(time.monotonic() - t0, 2)
    (OUT_DIR / "cutaway_render_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("COMPLETE in", receipt["elapsed_s"], "s", flush=True)


if __name__ == "__main__":
    main()
