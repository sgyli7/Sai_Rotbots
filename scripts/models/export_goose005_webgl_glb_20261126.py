"""Export a clean, artifact-free, interactive WebGL-ready dual-half GLB of Goose V0.2
(assembly_finish_005) with:
  - Toggleable Y<0 exterior shell half (EXT_LEFT_*) for live Half-Cutaway / Full Exterior
  - Intact Y>=0 exterior shell half (EXT_RIGHT_*) with role-tagged materials for live 4-colorway
    & Rolls-Royce twin torso coachline shading
  - 9 subsystem highlight groups (HL1..HL9) matching the flagship poster callouts 1-to-1
  - All 41 upgraded P1/P2/U2D2/precharge/L1 procedural electronics & real 005 CAD STLs
  - Per-object gentle collapse decimation (ZERO destructive planar dissolve, ZERO broken faces!)
    so every exterior thigh, shin, knee, torso, neck, head, and foot surface stays razor-smooth 360°.

Usage:
  /home/ethan/Softwares/ai-3d-local/scripts/blender.sh -b --python \
      scripts/models/export_goose005_webgl_glb_20261126.py
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/showcase_renders/interactive"
OUT_GLB = OUT_DIR / "goose_v02_005_interactive.glb"
OUT_GLB_GZ = OUT_DIR / "goose_v02_005_interactive.glb.gz"
OUT_RECEIPT = OUT_DIR / "webgl_glb_receipt.json"


def load_cutaway_module():
    mod_path = ROOT / "scripts/models/render_goose005_cutaway_hero_blender_20261125.py"
    spec = importlib.util.spec_from_file_location("cutaway_mod", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def world_center(obj):
    from mathutils import Vector

    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)


def boolean_intersect_or_diff(obj, cutter, op: str):
    import bpy

    mod = obj.modifiers.new(f"Cut_{op}", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception:
        obj.modifiers.remove(mod)
        mod2 = obj.modifiers.new(f"CutF_{op}", "BOOLEAN")
        mod2.operation = op
        mod2.solver = "FAST"
        mod2.object = cutter
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod2.name)


def classify_exterior_role(name: str, orig_mat: str) -> str:
    nl = name.lower()
    if name in ("body016_front", "body_continuous_rear"):
        return "TORSO_COACH"
    if orig_mat in ("Sky finish / glass", "Sky finish / lens") or "camera_catalog_" in nl:
        return "GLASS"
    if name == "camera_open_eye_bezel":
        return "EYE_RING"
    if name == "camera_fastened_open_face":
        return "DARK"
    if orig_mat == "Sky finish / accent" or "new_upper_front_" in nl or "lower_grip_shell" in nl or "ar_041_functional_shell" in nl:
        return "ACCENT"
    if orig_mat == "Sky finish / sole_trim" or name.endswith("flat_rounded_sole"):
        return "SOLE_TRIM"
    if orig_mat == "Sky finish / rubber" or "grip_cassette_pad" in nl:
        return "RUBBER"
    if orig_mat in ("Sky finish / shell", "Sky finish / theme_structural_dark"):
        return "SHELL"
    return "DARK"


def classify_internal_group(name: str, center) -> str:
    nl = name.lower()
    if name == "CAD005_opt_b2_r2":
        return "HL6_OPT_B2_R2"
    if name in ("CAD005_left_yoke_relieved", "CAD005_right_yoke_relieved"):
        return "HL7_YOKES"
    if name in ("CAD005_sanyo24_pcb", "CAD005_sanyo24_comps", "CAD005_fuse_pocket", "CAD005_fuse_harness") or any(
        k in nl for k in ("fan_", "sanyo", "fuse_pocket", "fuse_harness", "cold_hood")
    ):
        return "HL5_FAN_FUSE"
    if "camera" in nl or "lens" in nl or "optic" in nl:
        return "HL1_OPTICS"
    if any(k in nl for k in ("beak", "drive028", "thrust037", "preload048", "loadpath024", "lower_grip", "upper_grip", "xc330", "head_pitch", "head_roll")):
        return "HL2_BEAK"
    if any(k in nl for k in ("neck_", "pitch_housing")) or (center.z > 0.445 and center.z < 0.61):
        return "HL3_NECK"
    if any(
        k in nl
        for k in (
            "pcb",
            "radxa",
            "perfboard",
            "tinybms",
            "audio_buck",
            "logic_buck",
            "servo_buck",
            "imu_wt901c",
            "usb_hub",
            "p1_",
            "p2_",
            "substrate_allocation",
            "u2d2",
        )
    ):
        return "HL4_ENV_PCB"
    if any(k in nl for k in ("brake_sink", "coldplate", "thermal_sink", "c110", "_cu_", "make_current_choke", "precharge_r", "brake_rd_")):
        return "HL8_COLDPLATE"
    if any(k in nl for k in ("left_thigh", "right_thigh", "left_shin", "right_shin", "left_k_", "right_k_", "left_ap_", "right_ap_", "left_ar_", "right_ar_", "left_hp_", "right_hp_", "ak45", "flat_rounded_sole")) or center.z < 0.275:
        return "HL9_LEGS"
    return "INT_CHASSIS"


def gentle_per_object_decimate(obj, max_tris: int, min_ratio: float):
    """Per-object gentle edge collapse so large smooth surfaces never get starved or crumpled."""
    import bpy

    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.validate(verbose=False)
    n_tris = sum(max(1, len(p.vertices) - 2) for p in obj.data.polygons)
    if n_tris <= max_tris or n_tris < 120:
        return
    ratio = max(min_ratio, min(0.92, max_tris / float(n_tris)))
    if ratio >= 0.94:
        return
    mod = obj.modifiers.new("GentleDecimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.validate(verbose=False)


def join_bucket(objs: list, target_name: str, is_exterior: bool, bucket_cap: int):
    import bpy

    objs = [o for o in dict.fromkeys(objs) if o is not None and o.type == "MESH" and o.data is not None and len(o.data.polygons) > 0]
    if not objs:
        return None

    # Step 1: Per-object gentle cap (protects every curved shell & motor housing from starvation!)
    per_obj_max = 5200 if is_exterior else 650
    min_rat = 0.24 if is_exterior else 0.08
    for o in objs:
        o.hide_viewport = False
        o.hide_render = False
        gentle_per_object_decimate(o, max_tris=per_obj_max, min_ratio=min_rat)

    # Step 2: Join into single draw-call batch
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    merged = bpy.context.active_object
    if merged.data.users > 1:
        merged.data = merged.data.copy()
    merged.name = target_name
    merged.data.name = target_name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    merged.data.validate(verbose=False)

    # Step 3: Gentle bucket-level cap (never below 0.35 on exteriors, never below 0.14 on internals!)
    n_tris = sum(max(1, len(p.vertices) - 2) for p in merged.data.polygons)
    if bucket_cap > 0 and n_tris > bucket_cap * 1.12:
        floor_ratio = 0.38 if is_exterior else 0.14
        ratio = max(floor_ratio, min(0.92, bucket_cap / float(n_tris)))
        if ratio < 0.94:
            mod = merged.modifiers.new("BucketDecimate", "DECIMATE")
            mod.decimate_type = "COLLAPSE"
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            bpy.context.view_layer.objects.active = merged
            bpy.ops.object.modifier_apply(modifier=mod.name)
            merged.data.validate(verbose=False)

    return merged


def main():
    import bpy

    t0 = time.monotonic()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cm = load_cutaway_module()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(cm.GLB_PATH))
    mats = cm.build_materials()

    # Always-hidden legacy/replaced parts and empty-air service clearance envelopes
    always_hide = {
        "left_parent_yoke_003",
        "right_parent_yoke_003",
        "cold_hood_HT800_liner_01",
        "cold_hood_HT800_liner_03",
        "rear_usb_plug_service_installation_reserve",
        "dfplayer_lower_wire_bend_service",
        "dfplayer_upper_wire_bend_service",
        "dfplayer_sd_extract_service",
        "dfplayer_component_back_allocation",
        "dfplayer_component_front_allocation",
    }

    # Exterior shells belonging exclusively to the toggleable Y<0 (viewer-left) cutaway side
    left_only_shells = {
        "head_negative_retained",
        "head_negative_compression_sleeve",
        "b_lower_negative_matched_joint_008b",
        "paired_b_upper_negative_20261106",
        "new_upper_front_3",
        "c_parent_original_capture_026_retained",
        "right_thigh_primary_k_axial_edge",
        "right_thigh_inner_true_k_rear4",
        "right_knee_radial_grip_appearance_cover",
        "right_shin_primary_closeout_20261027",
        "right_shin_inner_original_cup_clearance",
        "right_ar_041_functional_shell",
        "right_visible_thigh_HP_small_service_cap",
        "right_hp_shell_compression_sleeve_0",
        "right_hp_shell_compression_sleeve_1",
        "right_hp_shell_compression_sleeve_2",
        "right_hp_shell_service_m2p5x8_0",
        "right_hp_shell_service_m2p5x8_1",
        "right_hp_shell_service_m2p5x8_2",
        "a006b_negative_C45_compression_tube_0",
        "a006b_negative_C45_compression_tube_1",
        "a006b_negative_C45_compression_tube_2",
    }

    # Exterior shells belonging exclusively to the intact Y>=0 (viewer-right) side
    right_only_shells = {
        "left_thigh_primary_k_task_port",
        "left_thigh_inner_true_k_rear4",
        "left_knee_radial_grip_appearance_cover",
        "left_shin_primary_closeout_20261027",
        "left_shin_inner_original_cup_clearance",
        "left_ar_041_functional_shell",
        "left_visible_thigh_HP_small_service_cap",
        "left_flat_rounded_sole",
        "a006b_positive_C45_compression_tube_0",
        "a006b_positive_C45_compression_tube_1",
        "a006b_positive_C45_compression_tube_2",
    }

    # Midline exterior shells crossing Y=0 -> split cleanly into EXT_RIGHT_* (Y>=0) and EXT_LEFT_* (Y<0)
    midline_shells = {
        "body016_front",
        "body_continuous_rear",
        "H_rear_cover_direct",
        "head_positive_retained",
        "a_child_complete_transition_008b",
        "b_lower_positive_matched_joint_008b",
        "paired_b_upper_positive_with_real_return_20261106",
        "neck_parent_captured_front_skin_004",
        "neck_yaw_moving_cover_sector_01",
        "neck_yaw_moving_cover_sector_02",
        "C_positive_trimmed",
        "camera_open_eye_bezel",
        "camera_fastened_open_face",
        "new_upper_front_0",
        "new_upper_front_1",
        "new_upper_front_2",
        "preload048_lower_grip_shell_internal_preload_relief",
    }

    internal_cut_only = {
        "passive_cold_hood",
        "cold_hood_HT800_liner_00",
        "fan_rear_antirecirculation_duct",
        "fan_original_pose_highrail_carrier_002",
        "rear_auxiliary_service_receiving_frame_056",
    }

    ext_orig_mats = {
        "Sky finish / shell",
        "Sky finish / theme_structural_dark",
        "Sky finish / accent",
        "Sky finish / eye_ring",
        "Sky finish / sole_trim",
        "Sky finish / structural_dark",
    }

    orig_mat_map: dict[str, str] = {}
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        if obj.name in always_hide:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        orig_mat = obj.data.materials[0].name if obj.data.materials else ""
        orig_mat_map[obj.name] = orig_mat
        if obj.name in ("left_flat_rounded_sole", "right_flat_rounded_sole"):
            cm.split_sole_trim_and_tread(obj, mats["ext_golden_amber"], mats["ext_rubber"])
        else:
            mat = cm.classify_object_material(obj.name, orig_mat, mats)
            obj.data.materials.clear()
            obj.data.materials.append(mat)

    # Upgrade 41 nominal CAD electronic boxes on P1/P2/U2D2/precharge/L1
    cm.upgrade_nominal_electronic_envelopes(mats)
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.hide_render:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Half-space cutter for Y < 0
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -0.5, 0.35))
    cutter_neg = bpy.context.active_object
    cutter_neg.name = "CUTTER_Y_NEG"
    cutter_neg.scale = (2.0, 1.0, 2.0)
    bpy.ops.object.transform_apply(scale=True)

    split_left_objs: list[tuple[object, str]] = []
    split_right_objs: list[tuple[object, str]] = []

    for name in sorted(midline_shells):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        role = classify_exterior_role(name, orig_mat_map.get(name, ""))
        dup = obj.copy()
        dup.data = obj.data.copy()
        dup.name = f"{name}__LEFT_HALF"
        bpy.context.collection.objects.link(dup)

        boolean_intersect_or_diff(obj, cutter_neg, "DIFFERENCE")
        boolean_intersect_or_diff(dup, cutter_neg, "INTERSECT")

        if len(obj.data.polygons) > 0:
            split_right_objs.append((obj, role))
        else:
            bpy.data.objects.remove(obj, do_unlink=True)
        if len(dup.data.polygons) > 0:
            split_left_objs.append((dup, role))
        else:
            bpy.data.objects.remove(dup, do_unlink=True)

    for name in sorted(internal_cut_only):
        obj = bpy.data.objects.get(name)
        if obj is not None:
            boolean_intersect_or_diff(obj, cutter_neg, "DIFFERENCE")

    # Split right_flat_rounded_sole at foot centerline Y=-0.155
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, -0.655, 0.0))
    foot_cutter = bpy.context.active_object
    foot_cutter.name = "CUTTER_FOOT_NEG"
    foot_cutter.scale = (2.0, 1.0, 2.0)
    bpy.ops.object.transform_apply(scale=True)
    rsole = bpy.data.objects.get("right_flat_rounded_sole")
    if rsole is not None:
        rsole_left = rsole.copy()
        rsole_left.data = rsole.data.copy()
        rsole_left.name = "right_flat_rounded_sole__LEFT_HALF"
        bpy.context.collection.objects.link(rsole_left)
        boolean_intersect_or_diff(rsole, foot_cutter, "DIFFERENCE")
        boolean_intersect_or_diff(rsole_left, foot_cutter, "INTERSECT")
        split_right_objs.append((rsole, "SOLE_TRIM"))
        split_left_objs.append((rsole_left, "SOLE_TRIM"))

    bpy.data.objects.remove(cutter_neg, do_unlink=True)
    bpy.data.objects.remove(foot_cutter, do_unlink=True)

    # Import real assembly_finish_005 CAD STLs
    cm.import_stl_object(cm.MESH_005_DIR / "opt_b2_r2_anchored_bridge.stl", "CAD005_opt_b2_r2", mats["cad005_bridge_billet"], smooth=False)
    cm.import_stl_object(cm.MESH_005_DIR / "left_yoke_shell_relieved.stl", "CAD005_left_yoke_relieved", mats["cad005_yoke_steel"], smooth=True)
    cm.import_stl_object(cm.MESH_005_DIR / "right_yoke_shell_relieved.stl", "CAD005_right_yoke_relieved", mats["cad005_yoke_steel"], smooth=True)
    cm.import_stl_object(cm.MESH_005_DIR / "sanyo24_miniboard_pcb.stl", "CAD005_sanyo24_pcb", mats["int_pcb_emerald"], smooth=False)
    cm.import_stl_object(cm.MESH_005_DIR / "sanyo24_miniboard_components.stl", "CAD005_sanyo24_comps", mats["int_ic_black"], smooth=False)
    cm.import_stl_object(cm.MESH_005_DIR / "serviceable_fuse_pocket_guard.stl", "CAD005_fuse_pocket", mats["cad005_fuse_guard"], smooth=False)
    cm.import_stl_object(cm.MESH_005_DIR / "serviceable_fuse_breakout_harness.stl", "CAD005_fuse_harness", mats["cad005_harness_orange"], smooth=True)

    # Bake world transforms before bucketing
    for obj in list(bpy.data.objects):
        if obj.type == "MESH":
            mw = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = mw
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)

    buckets: dict[str, list] = {}
    handled_ids: set[int] = set()

    for obj, role in split_right_objs:
        buckets.setdefault(f"EXT_RIGHT_{role}", []).append(obj)
        handled_ids.add(obj.as_pointer())
    for obj, role in split_left_objs:
        buckets.setdefault(f"EXT_LEFT_{role}", []).append(obj)
        handled_ids.add(obj.as_pointer())

    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or obj.as_pointer() in handled_ids:
            continue
        if len(obj.data.polygons) == 0:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        orig_mat = orig_mat_map.get(obj.name, "")
        if obj.name in left_only_shells:
            role = classify_exterior_role(obj.name, orig_mat)
            buckets.setdefault(f"EXT_LEFT_{role}", []).append(obj)
            continue
        if obj.name in right_only_shells:
            role = classify_exterior_role(obj.name, orig_mat)
            buckets.setdefault(f"EXT_RIGHT_{role}", []).append(obj)
            continue
        # Automatic safety net: NO exterior-material shell can ever accidentally enter internal buckets!
        if orig_mat in ext_orig_mats:
            c = world_center(obj)
            role = classify_exterior_role(obj.name, orig_mat)
            side = "EXT_LEFT" if c.y < 0.0 else "EXT_RIGHT"
            buckets.setdefault(f"{side}_{role}", []).append(obj)
            continue

        # Drop tiny invisible buried micro-fasteners (< 9.5 mm) inside deep chassis
        bmin, bmax = cm.world_aabb(obj)
        ext = bmax - bmin
        nl = obj.name.lower()
        if max(ext.x, ext.y, ext.z) < 0.0095 and any(k in nl for k in ("washer", "nut", "m2x", "m2p5", "m3x", "m4x", "screw", "bolt", "insert", "dowel", "pin_")) and not nl.startswith("detail_"):
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        grp = classify_internal_group(obj.name, world_center(obj))
        buckets.setdefault(grp, []).append(obj)

    # Generous exterior budgets + crisp internal budgets (total ~190k smooth tris, ~3.4 MB gzip)
    bucket_caps = {
        "EXT_RIGHT_TORSO_COACH": 14000,
        "EXT_LEFT_TORSO_COACH": 14000,
        "EXT_RIGHT_SHELL": 20000,
        "EXT_LEFT_SHELL": 20000,
        "EXT_RIGHT_ACCENT": 8500,
        "EXT_LEFT_ACCENT": 8500,
        "EXT_RIGHT_DARK": 12000,
        "EXT_LEFT_DARK": 12000,
        "EXT_RIGHT_SOLE_TRIM": 3200,
        "EXT_LEFT_SOLE_TRIM": 2200,
        "EXT_RIGHT_EYE_RING": 800,
        "EXT_LEFT_EYE_RING": 800,
        "HL6_OPT_B2_R2": 3000,
        "HL7_YOKES": 7000,
        "HL5_FAN_FUSE": 6500,
        "HL1_OPTICS": 5000,
        "HL4_ENV_PCB": 14000,
        "HL8_COLDPLATE": 8000,
        "HL2_BEAK": 10000,
        "HL3_NECK": 8000,
        "HL9_LEGS": 22000,
        "INT_CHASSIS": 24000,
    }

    stats = {}
    total_tris = 0
    for bname, objs in sorted(buckets.items()):
        is_ext = bname.startswith(("EXT_RIGHT_", "EXT_LEFT_"))
        merged = join_bucket(objs, bname, is_exterior=is_ext, bucket_cap=bucket_caps.get(bname, 8000))
        if merged is not None:
            nt = sum(max(1, len(p.vertices) - 2) for p in merged.data.polygons)
            stats[bname] = nt
            total_tris += nt

    print(f"[WEBGL_GLB] Merged into {len(stats)} batches, total_tris={total_tris:,}", flush=True)
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<28} {v:>7,} tris", flush=True)

    bpy.ops.export_scene.gltf(
        filepath=str(OUT_GLB),
        export_format="GLB",
        use_selection=False,
        export_materials="EXPORT",
        export_normals=True,
        export_texcoords=False,
        export_colors=False,
        export_yup=True,
    )

    raw_bytes = OUT_GLB.read_bytes()
    gz_bytes = gzip.compress(raw_bytes, compresslevel=9)
    OUT_GLB_GZ.write_bytes(gz_bytes)

    receipt = {
        "schema": "goose005_webgl_glb_v2_smooth",
        "elapsed_s": round(time.monotonic() - t0, 2),
        "batches": stats,
        "total_triangles": total_tris,
        "glb_bytes": len(raw_bytes),
        "glb_gz_bytes": len(gz_bytes),
        "glb_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "glb_gz_sha256": hashlib.sha256(gz_bytes).hexdigest(),
    }
    OUT_RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"SAVED {OUT_GLB} ({len(raw_bytes)/1e6:.2f} MB) | gzip={len(gz_bytes)/1e6:.2f} MB in {receipt['elapsed_s']}s", flush=True)


if __name__ == "__main__":
    main()
