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
        "int_pcb_power": make_pbr("Int_PCB_PowerEmerald", "#145A36", roughness=0.24, metallic=0.04, coat=0.45),
        "int_ic_black": make_pbr("Int_IC_Black", "#161920", roughness=0.36, metallic=0.12),
        "int_copper": make_pbr("Int_Copper_Coldplate", "#C87542", roughness=0.24, metallic=0.92, specular=0.55),
        "int_gunmetal": make_pbr("Int_Gunmetal_Actuator", "#1E232A", roughness=0.32, metallic=0.68, specular=0.45),
        "int_frame_titanium": make_pbr("Int_Frame_Titanium", "#2B323D", roughness=0.34, metallic=0.74, specular=0.45),
        "int_silver": make_pbr("Int_Silver_Bearing", "#CCD4E0", roughness=0.22, metallic=0.92, specular=0.55),
        "int_battery_blue": make_pbr("Int_Battery_Cobalt", "#1E468C", roughness=0.38, metallic=0.05),
        "int_contactor_slate": make_pbr("Int_Contactor_Slate", "#2D4258", roughness=0.34, metallic=0.15),
        "int_wire_copper": make_pbr("Int_Wire_Insulation", "#D65A28", roughness=0.40, metallic=0.05),
        "int_g10": make_pbr("Int_G10_Olive", "#556E5C", roughness=0.48, metallic=0.0),
        # Detailed Electronics Display Materials (strictly inscribed inside CAD nominal envelopes)
        "elec_alum_can": make_pbr("Elec_AlumCan", "#DCE2EC", roughness=0.19, metallic=0.94, specular=0.60),
        "elec_cap_stripe": make_pbr("Elec_CapPolarityPurple", "#3B2878", roughness=0.28, metallic=0.08, coat=0.35),
        "elec_cap_sleeve_navy": make_pbr("Elec_CapSleeveNavy", "#153466", roughness=0.22, metallic=0.06, coat=0.55),
        "elec_gold_pin": make_pbr("Elec_GoldPin", "#EAB949", roughness=0.18, metallic=0.96, specular=0.60),
        "elec_copper_winding": make_pbr("Elec_CopperWinding", "#C45D24", roughness=0.18, metallic=0.92, coat=0.45, specular=0.55),
        "elec_ferrite_core": make_pbr("Elec_FerriteCore", "#23272E", roughness=0.52, metallic=0.15),
        "elec_relay_blue": make_pbr("Elec_RelayBlue", "#1A60C2", roughness=0.20, metallic=0.0, coat=0.55),
        "elec_nylon_white": make_pbr("Elec_NylonWhite", "#E5E0D5", roughness=0.34, metallic=0.0),
        "elec_nylon_black": make_pbr("Elec_NylonBlack", "#1A1E25", roughness=0.38, metallic=0.05),
        "elec_ceramic_res": make_pbr("Elec_CeramicResistor", "#DFD8CA", roughness=0.58, metallic=0.0),
        "elec_phenolic_base": make_pbr("Elec_PhenolicBase", "#14171C", roughness=0.46, metallic=0.02),
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
        or any(
            k in nl
            for k in [
                "pcb",
                "substrate_allocation",
                "radxa_zero_3w",
                "perfboard",
                "tinybms_high_power_body",
                "audio_buck",
                "logic_buck",
                "servo_buck",
                "imu_wt901c",
            ]
        )
    ):
        return mats["int_pcb_power"] if "substrate_allocation" in nl else mats["int_pcb_emerald"]
    if "usb_hub_hat_b_oem_" in nl:
        return mats["int_ic_black"]
    if any(k in nl for k in ["brake_sink", "coldplate", "thermal_sink_top", "c110", "_cu_", "copper_bus", "copper_post", "copper_bridge", "make_current_choke"]):
        return mats["int_copper"]
    if nl.startswith(("p1_u_", "p2_u_", "p1_b_u", "p1_b_q", "p2_q_", "p1_rdy_u", "p1_rdy_q", "p1_d_tvs")):
        return mats["int_ic_black"]
    if nl.startswith(("p1_r_", "p2_r_", "p1_b_r", "p1_rdy_r", "p1_b_c")):
        return mats["elec_gold_pin"]
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


def world_aabb(obj):
    from mathutils import Vector

    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    bmin = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    bmax = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return bmin, bmax


def _add_box_bm(bm, center, size, mat_idx=0, bevel_w=0.0):
    import bmesh

    ret = bmesh.ops.create_cube(bm, size=1.0)
    verts = ret["verts"]
    bmesh.ops.scale(bm, vec=size, verts=verts)
    bmesh.ops.translate(bm, vec=center, verts=verts)
    for f in set(f for v in verts for f in v.link_faces):
        f.material_index = mat_idx
    if bevel_w > 0.0:
        edges = list({e for v in verts for e in v.link_edges})
        bev = bmesh.ops.bevel(bm, geom=edges, offset=bevel_w, segments=2, affect="EDGES", clamp_overlap=True)
        for f in bev.get("faces", []):
            f.material_index = mat_idx
    return None


def _new_mesh_obj(name: str, bm, mat_list: list, smooth_mats: set[int] | None = None):
    import bpy

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mat_list:
        mesh.materials.append(m)
    if smooth_mats:
        for p in mesh.polygons:
            p.use_smooth = p.material_index in smooth_mats
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _make_smd_electrolytic_cap(name: str, bmin, bmax, mats: dict):
    """Panasonic 35SVPF-style SMD aluminum polymer electrolytic cap strictly inscribed in CAD AABB."""
    import bmesh
    import math
    from mathutils import Matrix, Vector

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    # Mounted on P1 PCB at y_max, protruding outward along -Y
    dx, dy, dz = ext.x, ext.y, ext.z
    y_pcb = bmax.y
    r_can = 0.455 * min(dx, dz)
    base_h = min(0.0014, dy * 0.14)
    can_h = max(0.002, dy - base_h - 0.0003)

    mat_list = [
        mats["elec_phenolic_base"],  # 0
        mats["elec_alum_can"],       # 1
        mats["elec_cap_stripe"],     # 2
        mats["int_silver"],          # 3
    ]
    bm = bmesh.new()

    # 1. Square black phenolic SMD base seat with chamfered edge
    ret = bmesh.ops.create_cube(bm, size=1.0)
    b_verts = ret["verts"]
    bmesh.ops.scale(bm, vec=(dx * 0.94, base_h, dz * 0.94), verts=b_verts)
    bmesh.ops.translate(bm, vec=(ctr.x, y_pcb - base_h * 0.5, ctr.z), verts=b_verts)
    b_edges = list({e for v in b_verts for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=b_edges, offset=0.00025, segments=1, affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        f.material_index = 0

    # 2. Two silver SMD solder tabs at +/-X along PCB plane
    for sx in (-1.0, 1.0):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        tv = ret["verts"]
        bmesh.ops.scale(bm, vec=(dx * 0.20, 0.00045, dz * 0.28), verts=tv)
        bmesh.ops.translate(bm, vec=(ctr.x + sx * dx * 0.39, y_pcb - 0.00025, ctr.z), verts=tv)
        for f in set(f for v in tv for f in v.link_faces):
            f.material_index = 3

    # 3. Brushed aluminum cylindrical can along Y axis (axis rotated +90 deg around X)
    y_can_ctr = y_pcb - base_h - can_h * 0.5
    rot_y = Matrix.Rotation(math.pi * 0.5, 4, "X")
    tf = Matrix.Translation(Vector((ctr.x, y_can_ctr, ctr.z))) @ rot_y
    ret = bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=36,
        radius1=r_can,
        radius2=r_can,
        depth=can_h,
        matrix=tf,
    )
    can_verts = ret["verts"]
    can_faces = list({f for v in can_verts for f in v.link_faces})
    for f in can_faces:
        f.material_index = 1
    # Bevel the front (-Y) rim of the aluminum can for realistic specular catchlight
    front_edges = [
        e for e in {e for v in can_verts for e in v.link_edges}
        if abs(e.verts[0].co.y - (y_can_ctr - can_h * 0.5)) < 1e-4
        and abs(e.verts[1].co.y - (y_can_ctr - can_h * 0.5)) < 1e-4
    ]
    if front_edges:
        bev = bmesh.ops.bevel(bm, geom=front_edges, offset=min(0.00055, r_can * 0.12), segments=2, affect="EDGES", clamp_overlap=True)
        for f in bev.get("faces", []):
            f.material_index = 1

    # 4. Crisp purple/indigo cathode polarity band flush inside the circular -Y top cap face
    y_face = y_can_ctr - can_h * 0.5 - 0.00005
    ret = bmesh.ops.create_cube(bm, size=1.0)
    sv = ret["verts"]
    bmesh.ops.scale(bm, vec=(r_can * 1.24, 0.00010, r_can * 0.34), verts=sv)
    bmesh.ops.translate(bm, vec=(ctr.x, y_face, ctr.z + r_can * 0.35), verts=sv)
    for f in set(f for v in sv for f in v.link_faces):
        f.material_index = 2

    # 5. Subtle stamped cross-vent score lines on front aluminum cap
    for sz_x, sz_z in ((r_can * 1.05, 0.00020), (0.00020, r_can * 0.66)):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        gv = ret["verts"]
        bmesh.ops.scale(bm, vec=(sz_x, 0.00008, sz_z), verts=gv)
        bmesh.ops.translate(bm, vec=(ctr.x, y_face + 0.00001, ctr.z - r_can * 0.16), verts=gv)
        for f in set(f for v in gv for f in v.link_faces):
            f.material_index = 0

    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list, smooth_mats={1})


def _make_tall_radial_cap(name: str, bmin, bmax, mats: dict):
    """Tall navy-sleeved radial aluminum electrolytic bulk capacitor strictly inside CAD AABB."""
    import bmesh
    import math
    from mathutils import Matrix, Vector

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    dx, dy, dz = ext.x, ext.y, ext.z
    y_pcb = bmax.y
    r_can = 0.455 * min(dx, dz)
    sleeve_h = dy * 0.94

    mat_list = [
        mats["elec_cap_sleeve_navy"],  # 0
        mats["elec_alum_can"],         # 1
        mats["elec_phenolic_base"],    # 2
        mats["int_silver"],            # 3
    ]
    bm = bmesh.new()
    rot_y = Matrix.Rotation(math.pi * 0.5, 4, "X")

    # 1. Glossy cobalt-navy PVC-sleeved main barrel
    y_bar = y_pcb - dy * 0.49
    tf = Matrix.Translation(Vector((ctr.x, y_bar, ctr.z))) @ rot_y
    ret = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=36,
        radius1=r_can, radius2=r_can, depth=sleeve_h, matrix=tf,
    )
    for f in set(f for v in ret["verts"] for f in v.link_faces):
        f.material_index = 0

    # 2. Bright brushed aluminum top vent cap slightly proud of sleeve wrap at -Y end
    y_cap = bmin.y + 0.0007
    tf_cap = Matrix.Translation(Vector((ctr.x, y_cap, ctr.z))) @ rot_y
    ret = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=36,
        radius1=r_can * 0.87, radius2=r_can * 0.87, depth=0.0012, matrix=tf_cap,
    )
    for f in set(f for v in ret["verts"] for f in v.link_faces):
        f.material_index = 1

    # 3. Silver negative polarity stripe bar along +Z crest of sleeve
    ret = bmesh.ops.create_cube(bm, size=1.0)
    pv = ret["verts"]
    bmesh.ops.scale(bm, vec=(r_can * 0.34, sleeve_h * 0.88, 0.00028), verts=pv)
    bmesh.ops.translate(bm, vec=(ctr.x, y_bar, ctr.z + r_can * 0.985), verts=pv)
    for f in set(f for v in pv for f in v.link_faces):
        f.material_index = 3

    # 4. Scored K-vent lines on aluminum cap end
    for ang in (0.0, math.pi / 3.0, -math.pi / 3.0):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        kv = ret["verts"]
        bmesh.ops.scale(bm, vec=(r_can * 1.10, 0.00014, 0.00026), verts=kv)
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(ang, 3, "Y"), verts=kv)
        bmesh.ops.translate(bm, vec=(ctr.x, bmin.y + 0.00008, ctr.z), verts=kv)
        for f in set(f for v in kv for f in v.link_faces):
            f.material_index = 2

    # 5. Two radial tinned leads entering PCB at y_pcb
    for sz in (-r_can * 0.38, r_can * 0.38):
        tf_l = Matrix.Translation(Vector((ctr.x, y_pcb - 0.0012, ctr.z + sz))) @ rot_y
        ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.00045, radius2=0.00045, depth=0.0024, matrix=tf_l)
        for f in set(f for v in ret["verts"] for f in v.link_faces):
            f.material_index = 3

    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list, smooth_mats={0, 1})


def _make_power_choke(name: str, bmin, bmax, mats: dict, axis: str = "Z"):
    """Shielded ferrite E-core brake/power choke with visible wound enameled copper coil stack."""
    import bmesh
    import math
    from mathutils import Matrix, Vector

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    dx, dy, dz = ext.x, ext.y, ext.z

    mat_list = [
        mats["elec_ferrite_core"],    # 0
        mats["elec_copper_winding"],  # 1
        mats["int_silver"],           # 2
        mats["elec_phenolic_base"],   # 3
    ]
    bm = bmesh.new()

    # Chamfered top and bottom ferrite flanges + central ferrite bridge leaving side coil window open
    flange_z = dz * 0.19
    for sz in (-1.0, 1.0):
        _add_box_bm(
            bm,
            (ctr.x, ctr.y, ctr.z + sz * (dz * 0.5 - flange_z * 0.55)),
            (dx * 0.94, dy * 0.92, flange_z),
            mat_idx=0,
            bevel_w=0.0008,
        )

    # Side ferrite outer legs (thin pillars at +/-X so the copper coil gleams right out the -Y front window)
    leg_x = dx * 0.17
    for sx in (-1.0, 1.0):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        lv = ret["verts"]
        bmesh.ops.scale(bm, vec=(leg_x, dy * 0.88, dz * 0.64), verts=lv)
        bmesh.ops.translate(bm, vec=(ctr.x + sx * (dx * 0.47 - leg_x * 0.5), ctr.y, ctr.z), verts=lv)
        for f in set(f for v in lv for f in v.link_faces):
            f.material_index = 0

    # Stacked glossy enameled copper coil turns filling the middle window!
    n_turns = 9
    coil_h = dz * 0.56
    turn_pitch = coil_h / n_turns
    r_coil = min(dx * 0.37, dy * 0.43)
    for i in range(n_turns):
        tz = ctr.z - coil_h * 0.5 + (i + 0.5) * turn_pitch
        tf = Matrix.Translation(Vector((ctr.x, ctr.y, tz)))
        ret = bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=32,
            radius1=r_coil, radius2=r_coil, depth=turn_pitch * 0.82, matrix=tf,
        )
        for f in set(f for v in ret["verts"] for f in v.link_faces):
            f.material_index = 1

    # Two tinned silver mounting feet at PCB plane (y_max)
    for sz in (-dz * 0.34, dz * 0.34):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        tv = ret["verts"]
        bmesh.ops.scale(bm, vec=(dx * 0.45, 0.0014, dz * 0.14), verts=tv)
        bmesh.ops.translate(bm, vec=(ctr.x, bmax.y - 0.0008, ctr.z + sz), verts=tv)
        for f in set(f for v in tv for f in v.link_faces):
            f.material_index = 2

    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list, smooth_mats={1})


def _make_shrouded_header(name: str, bmin, bmax, mats: dict, white: bool = True):
    """Shrouded Molex/JST power header with recessed socket pocket and gleaming gold pins."""
    import bmesh
    from mathutils import Vector

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    dx, dy, dz = ext.x, ext.y, ext.z
    y_pcb = bmax.y
    wall = min(0.0013, min(dx, dz) * 0.14)

    mat_list = [
        mats["elec_nylon_white"] if white else mats["elec_nylon_black"],  # 0
        mats["elec_gold_pin"],  # 1
    ]
    bm = bmesh.new()

    # Back floor wall against PCB
    back_d = dy * 0.30
    walls = [
        ((ctr.x, y_pcb - back_d * 0.5, ctr.z), (dx * 0.94, back_d, dz * 0.94)),
        # Top & bottom shroud walls
        ((ctr.x, ctr.y, ctr.z + dz * 0.47 - wall * 0.5), (dx * 0.94, dy * 0.94, wall)),
        ((ctr.x, ctr.y, ctr.z - dz * 0.47 + wall * 0.5), (dx * 0.94, dy * 0.94, wall)),
        # Left & right shroud walls
        ((ctr.x - dx * 0.47 + wall * 0.5, ctr.y, ctr.z), (wall, dy * 0.94, dz * 0.94)),
        ((ctr.x + dx * 0.47 - wall * 0.5, ctr.y, ctr.z), (wall, dy * 0.94, dz * 0.94)),
        # Top keying latch tab
        ((ctr.x, bmin.y + dy * 0.28, ctr.z + dz * 0.47), (dx * 0.34, dy * 0.36, wall * 0.7)),
    ]
    for c_w, s_w in walls:
        ret = bmesh.ops.create_cube(bm, size=1.0)
        wv = ret["verts"]
        bmesh.ops.scale(bm, vec=s_w, verts=wv)
        bmesh.ops.translate(bm, vec=c_w, verts=wv)
        for f in set(f for v in wv for f in v.link_faces):
            f.material_index = 0

    # Gold-plated square pin array inside recessed cavity
    nx = max(2, min(6, int(round((dx - 2 * wall) / 0.0028))))
    nz = 2 if (dz - 2 * wall) > 0.005 else 1
    pin_len = dy * 0.56
    pin_w = min(0.00085, (dx - 2 * wall) / (nx * 2.4))
    for ix in range(nx):
        px = ctr.x + ((ix + 0.5) / nx - 0.5) * (dx - 2.6 * wall)
        for iz in range(nz):
            pz = ctr.z if nz == 1 else ctr.z + ((iz + 0.5) / nz - 0.5) * (dz - 2.8 * wall)
            ret = bmesh.ops.create_cube(bm, size=1.0)
            pv = ret["verts"]
            bmesh.ops.scale(bm, vec=(pin_w, pin_len, pin_w), verts=pv)
            bmesh.ops.translate(bm, vec=(px, y_pcb - back_d - pin_len * 0.45, pz), verts=pv)
            for f in set(f for v in pv for f in v.link_faces):
                f.material_index = 1

    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list)


def _make_signal_relay(name: str, bmin, bmax, mats: dict):
    """Glossy Omron-style royal blue chamfered signal relay."""
    import bmesh

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    mat_list = [mats["elec_relay_blue"], mats["elec_phenolic_base"]]
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    rv = ret["verts"]
    bmesh.ops.scale(bm, vec=(ext.x * 0.94, ext.y * 0.90, ext.z * 0.94), verts=rv)
    bmesh.ops.translate(bm, vec=(ctr.x, ctr.y - ext.y * 0.03, ctr.z), verts=rv)
    re = list({e for v in rv for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=re, offset=0.0005, segments=2, affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        f.material_index = 0
    # Thin dark epoxy seal base against PCB
    ret = bmesh.ops.create_cube(bm, size=1.0)
    bv = ret["verts"]
    bmesh.ops.scale(bm, vec=(ext.x * 0.92, ext.y * 0.12, ext.z * 0.92), verts=bv)
    bmesh.ops.translate(bm, vec=(ctr.x, bmax.y - ext.y * 0.06, ctr.z), verts=bv)
    for f in set(f for v in bv for f in v.link_faces):
        f.material_index = 1
    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list)


def _make_to220_diode(name: str, bmin, bmax, mats: dict):
    """TO-220 power diode with bright tinned heatsink tab, beveled epoxy body, and silver leads."""
    import bmesh

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    dx, dy, dz = ext.x, ext.y, ext.z
    mat_list = [mats["int_ic_black"], mats["int_silver"]]
    bm = bmesh.new()

    # Shiny metallic heatsink backplate tab extending out to bmin.y
    ret = bmesh.ops.create_cube(bm, size=1.0)
    tv = ret["verts"]
    bmesh.ops.scale(bm, vec=(dx * 0.92, dy * 0.72, dz * 0.28), verts=tv)
    bmesh.ops.translate(bm, vec=(ctr.x, bmin.y + dy * 0.36, ctr.z + dz * 0.30), verts=tv)
    for f in set(f for v in tv for f in v.link_faces):
        f.material_index = 1

    # Matte black beveled epoxy body
    _add_box_bm(
        bm,
        (ctr.x, bmin.y + dy * 0.52, ctr.z - dz * 0.10),
        (dx * 0.90, dy * 0.48, dz * 0.62),
        mat_idx=0,
        bevel_w=0.00035,
    )

    # Two bent silver leads entering PCB at bmax.y
    for sx in (-dx * 0.24, dx * 0.24):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        lv = ret["verts"]
        bmesh.ops.scale(bm, vec=(0.0010, dy * 0.30, 0.0007), verts=lv)
        bmesh.ops.translate(bm, vec=(ctr.x + sx, bmax.y - dy * 0.15, ctr.z - dz * 0.08), verts=lv)
        for f in set(f for v in lv for f in v.link_faces):
            f.material_index = 1

    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list)


def _make_power_stud(name: str, bmin, bmax, mats: dict):
    """Machined brass/copper hex power terminal stud + nut on C110 strip."""
    import bmesh
    import math
    from mathutils import Matrix, Vector

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    r_stud = 0.26 * min(ext.x, ext.z)
    r_nut = 0.46 * min(ext.x, ext.z)
    rot_y = Matrix.Rotation(math.pi * 0.5, 4, "X")
    mat_list = [mats["elec_gold_pin"], mats["int_silver"]]
    bm = bmesh.new()

    # Brass stud shaft
    tf_s = Matrix.Translation(ctr) @ rot_y
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r_stud, radius2=r_stud, depth=ext.y * 0.92, matrix=tf_s)
    for f in set(f for v in ret["verts"] for f in v.link_faces):
        f.material_index = 0

    # Hex nut near mid-shaft
    tf_n = Matrix.Translation(Vector((ctr.x, ctr.y - ext.y * 0.08, ctr.z))) @ rot_y
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r_nut, radius2=r_nut, depth=ext.y * 0.38, matrix=tf_n)
    for f in set(f for v in ret["verts"] for f in v.link_faces):
        f.material_index = 1

    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list, smooth_mats={0})


def _make_ceramic_resistor(name: str, bmin, bmax, mats: dict):
    """Beveled ceramic cement power precharge resistor with silver end caps."""
    import bmesh

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    mat_list = [mats["elec_ceramic_res"], mats["int_silver"]]
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    rv = ret["verts"]
    bmesh.ops.scale(bm, vec=(ext.x * 0.90, ext.y * 0.82, ext.z * 0.90), verts=rv)
    bmesh.ops.translate(bm, vec=ctr, verts=rv)
    re = list({e for v in rv for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=re, offset=0.0005, segments=1, affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        f.material_index = 0
    for sy in (-1.0, 1.0):
        ret = bmesh.ops.create_cube(bm, size=1.0)
        cv = ret["verts"]
        bmesh.ops.scale(bm, vec=(ext.x * 0.92, ext.y * 0.09, ext.z * 0.92), verts=cv)
        bmesh.ops.translate(bm, vec=(ctr.x, ctr.y + sy * ext.y * 0.43, ctr.z), verts=cv)
        for f in set(f for v in cv for f in v.link_faces):
            f.material_index = 1
    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list)


def _make_u2d2_module(name: str, bmin, bmax, mats: dict):
    """Beveled U2D2 USB-to-Dynamixel enclosure with metallic trim strip."""
    import bmesh

    ext = bmax - bmin
    ctr = 0.5 * (bmin + bmax)
    mat_list = [mats["elec_nylon_black"], mats["int_silver"], mats["elec_relay_blue"]]
    bm = bmesh.new()
    ret = bmesh.ops.create_cube(bm, size=1.0)
    bv = ret["verts"]
    bmesh.ops.scale(bm, vec=(ext.x * 0.96, ext.y * 0.94, ext.z * 0.94), verts=bv)
    bmesh.ops.translate(bm, vec=ctr, verts=bv)
    be = list({e for v in bv for e in v.link_edges})
    bmesh.ops.bevel(bm, geom=be, offset=0.0012, segments=2, affect="EDGES", clamp_overlap=True)
    for f in bm.faces:
        f.material_index = 0
    # Subtle blue ROBOTIS-style accent label bar on the -Y outer face
    ret = bmesh.ops.create_cube(bm, size=1.0)
    lv = ret["verts"]
    bmesh.ops.scale(bm, vec=(ext.x * 0.62, 0.0003, ext.z * 0.34), verts=lv)
    bmesh.ops.translate(bm, vec=(ctr.x, bmin.y + 0.00035, ctr.z), verts=lv)
    for f in set(f for v in lv for f in v.link_faces):
        f.material_index = 2
    return _new_mesh_obj(f"DETAIL_{name}", bm, mat_list)


def upgrade_nominal_electronic_envelopes(mats: dict):
    """Replace 24-vertex nominal CAD keepout boxes on P1/P2/U2D2/precharge with
    photorealistic procedural electronic display geometry strictly inscribed inside
    each part's exact CAD AABB (display-only; zero CAD/physics/MCI modification).
    """
    import bpy

    replaced = 0
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or obj.hide_render:
            continue
        nl = obj.name.lower()
        bmin, bmax = world_aabb(obj)

        detail_obj = None
        if nl.startswith("p1_bus_c") or nl == "p1_c_sc_out":
            detail_obj = _make_smd_electrolytic_cap(obj.name, bmin, bmax, mats)
        elif nl in ("p1_c_sc_top", "p1_c_sc_bot"):
            detail_obj = _make_tall_radial_cap(obj.name, bmin, bmax, mats)
        elif nl in ("p1_l_brake", "l1_main_make_current_choke"):
            detail_obj = _make_power_choke(obj.name, bmin, bmax, mats)
        elif nl in ("p1_rdy_k_ready1", "p1_rdy_k_ready2"):
            detail_obj = _make_signal_relay(obj.name, bmin, bmax, mats)
        elif nl in ("p1_j_branch", "p1_j_bus_sw", "p1_j_ready_p1", "p1_j_link_p1", "coil12_service_microfit_4p"):
            detail_obj = _make_shrouded_header(obj.name, bmin, bmax, mats, white=(nl in ("p1_j_branch", "p1_j_ready_p1", "p1_j_link_p1")))
        elif nl == "p1_d_free":
            detail_obj = _make_to220_diode(obj.name, bmin, bmax, mats)
        elif nl in ("p1_j_bus_power", "p1_j_gnd_power"):
            detail_obj = _make_power_stud(obj.name, bmin, bmax, mats)
        elif nl.startswith("precharge_r0"):
            detail_obj = _make_ceramic_resistor(obj.name, bmin, bmax, mats)
        elif nl == "u2d2_xc330_body":
            detail_obj = _make_u2d2_module(obj.name, bmin, bmax, mats)
        elif nl == "u2d2_usb_plug":
            import bmesh as _bm
            bm_u = _bm.new()
            ext_u = bmax - bmin
            ctr_u = 0.5 * (bmin + bmax)
            _add_box_bm(bm_u, ctr_u, (ext_u.x * 0.94, ext_u.y * 0.90, ext_u.z * 0.88), mat_idx=0, bevel_w=0.0007)
            _add_box_bm(bm_u, (ctr_u.x - ext_u.x * 0.18, bmin.y + 0.0006, ctr_u.z), (ext_u.x * 0.24, 0.0004, ext_u.z * 0.34), mat_idx=1, bevel_w=0.0)
            detail_obj = _new_mesh_obj(f"DETAIL_{obj.name}", bm_u, [mats["int_silver"], mats["elec_phenolic_base"]])
        elif nl == "u2d2_ttl_plug":
            detail_obj = _make_shrouded_header(obj.name, bmin, bmax, mats, white=True)

        if detail_obj is not None:
            obj.hide_render = True
            obj.hide_viewport = True
            replaced += 1

    print(f"[CUTAWAY] Upgraded {replaced} nominal CAD electronic envelopes to detailed display geometry", flush=True)


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
        "rear_usb_plug_service_installation_reserve",
        "dfplayer_lower_wire_bend_service",
        "dfplayer_upper_wire_bend_service",
        "dfplayer_sd_extract_service",
        "dfplayer_component_back_allocation",
        "dfplayer_component_front_allocation",
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

    # Upgrade 24-vertex nominal CAD electronic envelopes strictly inside exact AABBs (display-only)
    upgrade_nominal_electronic_envelopes(mats)

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
