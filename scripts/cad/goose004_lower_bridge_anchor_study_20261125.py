"""Track A1 Native 3D CAD Spatial, Serviceability & Architecture Study on assembly_finish_004.

Constructs cold-verified single-solid STEP/BREP candidates on the real assembly_finish_004 frame
(NOT the +494 g t40 replacement block) for:
  - Option A  (opt_a_bare_bridge): Bare bending/shear-stiff lower cross-bridge (no frame anchor)
  - Option B1 (opt_b1_anchored_lower_bridge): Lower cross-bridge + local 004 lower chassis anchors
              (Left-of-K2 forward shear web + forward bay cross-tie to 6 lower M4 roots + neck_root)
  - Option B2 (opt_b2_anchored_bridge_stator_ties): Option B1 + bilateral symmetric front-inboard
              vertical C-frame tie columns to left/right_stator_base underside (Z=367.1)
  - Option C  (opt_c_left_bracket, opt_c_right_bracket): Bilateral independent short lower-seat
              brackets (no cross-bridge), including the K2-pinched right-side detour

Audits Astra's X=-53, Z=315 corridor vs discovered zero-collision corridors against all 004 fixed
torso parts, active closeout overlays, and swept bilateral moving hip parts, verifies fastener/tool
access and 608 -Z extraction, and exports exact OCCT XZ/XY/YZ cross-section polylines for plotting.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
import time
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/cad"))
import goose_004_hip_support_routes as geo

V = App.Vector

OUT_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/hip_bridge_a1"
CAD_DIR = OUT_DIR / "cad"
WORLD_PATH = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/cad_master/source004_smooth006_001/world_bbox_inventory.json"
REG_PATH = ROOT / "artifacts/goose_v0_2/appearance_finish_execution_20261118_001/assembly_finish_004/assembly_registry.json"
NAT_Z312 = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/hip/support_routes/dual_support_z312_joint_002/native"
CORRIDORS_Z312 = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/hip/support_routes/dual_support_z312_joint_002/candidate_corridors.json"

OVERLAY_STEPS = {
    "installed_env_106": ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/owner/env_service_pose_001/installed_env_106.step",
    "first_bend_reservation": ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/owner/env_service_pose_001/first_bend_reservation.step",
    "electrical_forearm_relief": ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/internal_layout/ak45_forearm_relief_001/electrical_forearm_relief.step",
    "can_a_nominal_parts_001": ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/internal_layout/can_a_source_004_layout_001/can_a_nominal_parts_001.step",
    "wt901_split_clamp_candidate": ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/acceptance/wt901_split_clamp_candidate.step",
}

RHO_7075_G_MM3 = 2.81e-3
RHO_STEEL_G_MM3 = 7.80e-3
RHO_TI_G_MM3 = 4.43e-3

# Preexisting bolts & head washers replaced with +4..+5 mm longer M4 fasteners at bracket seats
REPLACED_FASTENERS = {
    "left_corner_x_0_bolt", "left_corner_x_0_head_washer",
    "right_corner_x_0_bolt", "right_corner_x_0_head_washer",
    "left_corner_y_0_bolt", "left_corner_y_0_head_washer",
    "left_corner_y_1_bolt", "left_corner_y_1_head_washer",
    "right_corner_y_0_bolt", "right_corner_y_0_head_washer",
    "right_corner_y_1_bolt", "right_corner_y_1_head_washer",
}

# Legacy superseded WT901 reserve (replaced in active closeout by wt901_split_clamp_candidate.step at Z=397.7..424.7)
LEGACY_SUPERSEDED_RESERVES = {"imu_wt901c_ttl_installation_reserve"}

YAW_SAMPLES = (-0.06, 0.0, 0.25, 0.57)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_ref(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def make_box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part.Shape:
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def make_cyl(r: float, h: float, pt: tuple[float, float, float], axis=(0.0, 0.0, 1.0)) -> Part.Shape:
    return Part.makeCylinder(r, h, V(*pt), V(*axis))


def path_tube(points: list[list[float]], radius: float) -> Part.Shape:
    pts = [V(*p) for p in points]
    sh = Part.makeSphere(radius + 0.05, pts[0])
    for a, b in itertools.pairwise(pts):
        d = b - a
        if d.Length < 1e-6:
            continue
        sh = sh.fuse(Part.makeCylinder(radius, d.Length, a, d)).fuse(Part.makeSphere(radius + 0.05, b))
    return sh


def fuse_all(shapes: list[Part.Shape]) -> Part.Shape:
    cur = shapes[0]
    for s in shapes[1:]:
        cur = cur.fuse(s)
    return cur


def save_cold_solid(tag: str, solid: Part.Shape) -> dict:
    CAD_DIR.mkdir(parents=True, exist_ok=True)
    refined = solid.removeSplitter()
    if len(refined.Solids) == 1 and refined.isValid():
        sh = refined
    elif len(solid.Solids) == 1 and solid.isValid():
        sh = solid
    else:
        raise ValueError(f"{tag}: invalid solid count={len(solid.Solids)}/{len(refined.Solids)} valid={solid.isValid()}/{refined.isValid()}")
    brep = CAD_DIR / f"{tag}.brep"
    step = CAD_DIR / f"{tag}.step"
    sh.exportBrep(str(brep))
    sh.exportStep(str(step))
    cold = Part.read(str(step))
    if len(cold.Solids) != 1 or not cold.isValid():
        raise ValueError(f"{tag}: cold STEP readback failed: solids={len(cold.Solids)}, valid={cold.isValid()}")
    vol_warm = float(sh.Volume)
    vol_cold = float(cold.Volume)
    bb = cold.BoundBox
    com = cold.Solids[0].CenterOfMass
    return {
        "tag": tag,
        "step": file_ref(step),
        "brep": file_ref(brep),
        "cold_solid_count": len(cold.Solids),
        "cold_valid": bool(cold.isValid()),
        "volume_mm3": vol_cold,
        "warm_cold_vol_diff_mm3": abs(vol_warm - vol_cold),
        "mass_7075_g": vol_cold * RHO_7075_G_MM3,
        "mass_ti_g": vol_cold * RHO_TI_G_MM3,
        "mass_steel_g": vol_cold * RHO_STEEL_G_MM3,
        "bbox_mm": [round(bb.XMin, 3), round(bb.YMin, 3), round(bb.ZMin, 3), round(bb.XMax, 3), round(bb.YMax, 3), round(bb.ZMax, 3)],
        "com_mm": [round(com.x, 3), round(com.y, 3), round(com.z, 3)],
        "shape": cold,
    }


def bearing_cup(side_sign: float, r_out: float = 14.0, z0: float = 308.0, z1: float = 316.8) -> Part.Shape:
    """608-2RSH outer-race housing centered at (-60, ±60, 312), OD 28 mm (3.0 mm radial wall), open -Z."""
    y = side_sign * 60.0
    return make_cyl(r_out, z1 - z0, (-60.0, y, z0))


def drill_608_bores(sh: Part.Shape, sides=(1.0, -1.0)) -> Part.Shape:
    for sg in sides:
        y = sg * 60.0
        # Main Ø22 bore from Z=305.0 to Z=315.6 (open bottom for -Z bearing insertion + retaining circlip)
        sh = sh.cut(make_cyl(11.0, 10.6, (-60.0, y, 305.0)))
        # Top clearance bore Ø19.0 through upper retaining shoulder for trident journal & seal clearance
        sh = sh.cut(make_cyl(9.5, 5.0, (-60.0, y, 315.5)))
    return sh


def build_opt_a_bare_bridge() -> Part.Shape:
    """Option A: Bare bending/shear-stiff lower cross-bridge (no 004 frame anchor)."""
    parts = [
        bearing_cup(1.0),
        bearing_cup(-1.0),
        # Full-span under-AK45 beam: X[-63.5, -52.5], Y[-50, +50], Z[312.5, 321.5] (11x9 mm)
        make_box(-63.5, -52.5, -50.0, 50.0, 312.5, 321.5),
        # Lower blending gussets into bearing cups (Z=308.5..313.5, |Y|=44..52)
        make_box(-63.5, -53.5, 44.0, 52.0, 308.5, 313.5),
        make_box(-63.5, -53.5, -52.0, -44.0, 308.5, 313.5),
        # Deep central bay I-beam web: X[-63.5, -46.0], Y[-30.5, +30.5], Z[312.5, 340.0]
        make_box(-63.5, -46.0, -30.5, 30.5, 312.5, 340.0),
    ]
    sh = fuse_all(parts)
    # Pocket under-AK45 outer arms into stiff H/C-channels (leaving 3.0 mm top/bottom flanges + 3.5 mm web)
    for y0, y1 in ((-45.5, -32.0), (32.0, 45.5)):
        sh = sh.cut(make_box(-64.0, -56.5, y0, y1, 315.0, 319.0))
        sh = sh.cut(make_box(-55.5, -52.0, y0, y1, 315.0, 319.0))
    # Lightweighting pockets on central bay web (I-beam cross-section: 3.2 mm center web + 4.0 mm flanges)
    sh = sh.cut(make_box(-64.0, -56.4, -27.0, 27.0, 316.5, 336.0))
    sh = sh.cut(make_box(-53.2, -45.5, -27.0, 27.0, 316.5, 336.0))
    sh = sh.cut(make_box(-64.0, -45.0, -24.0, -3.5, 319.0, 333.5))
    sh = sh.cut(make_box(-64.0, -45.0, 3.5, 24.0, 319.0, 333.5))
    sh = drill_608_bores(sh)
    return sh


def build_opt_b1_anchored_lower_bridge() -> Part.Shape:
    """Option B1: Anchored lower cross-bridge (6 lower 004 M4 roots + neck_root_base, ZERO K2 touch)."""
    parts = [
        bearing_cup(1.0),
        bearing_cup(-1.0),
        # Under-AK45 full-span beam (11x9 mm, pocketed below into H-section)
        make_box(-63.5, -52.5, -50.0, 50.0, 312.5, 321.5),
        make_box(-63.5, -53.5, 44.0, 52.0, 308.5, 313.5),
        make_box(-63.5, -53.5, -52.0, -44.0, 308.5, 313.5),
        # Central bay deep shear web (X[-63.5, -46.0], Y[-30.5, +30.5], Z[312.5, 340.5])
        make_box(-63.5, -46.0, -30.5, 30.5, 312.5, 340.5),
        # Left-of-K2 straight forward shear box/channel: X[-46.5, 0.0], Y[+19.8, +30.5], Z[314.5, 340.5]
        make_box(-46.5, 0.0, 19.8, 30.5, 314.5, 340.5),
        # Transition through opening inboard of left_front_bulkhead (Y_min=25.6 -> Y[19.8, 25.0]) into forward bay
        make_box(-1.0, 9.0, 19.8, 25.0, 314.5, 340.5),
        # Forward bay closed cross-tie box under neck_root_base (Z=345.205): X[8.5, 25.0], Y[-30.95, +30.95], Z[333.5, 345.2]
        # Stops at X=25.0 to clear audio_buck by 4.4 mm AND leave straight hex-key access to panel_30_339 at X=30!
        make_box(8.5, 25.0, -30.95, 30.95, 333.5, 345.2),
        # Left & right sideplate mounting flanges (3.5 mm thick in Y, X=[23.5, 34.5], Z=[321.5, 344.2]) picking up all 4 panel M4 bolts
        make_box(23.5, 34.5, 27.45, 30.95, 321.5, 344.2),
        make_box(23.5, 34.5, -30.95, -27.45, 321.5, 344.2),
        # Left bulkhead corner_low_x ear (3.5 mm thick in X, X=[-3.5, -0.05], Y=[25.0, 56.0], Z=[320.5, 332.5])
        make_box(-3.5, -0.05, 25.0, 56.0, 320.5, 332.5),
        # Right bulkhead corner_low_x ear (3.5 mm thick in X, X=[-3.5, -0.05], Y=[-56.0, -45.0], Z=[320.5, 332.5])
        make_box(-3.5, -0.05, -56.0, -45.0, 320.5, 332.5),
        # Right over-K2-ear diagonal bridge link from central bay (Z=336..340.5) to right corner_low_x ear
        make_box(-46.5, -31.5, -30.5, -18.0, 336.0, 340.5),
        path_tube([[-35.0, -29.0, 338.2], [-33.0, -35.0, 339.0], [-20.0, -36.5, 338.0], [-10.0, -45.5, 330.0], [-2.5, -50.5, 326.0]], 3.1),
    ]
    sh = fuse_all(parts)

    # Trim any tiny tangent protrusion into bulkheads
    sh = sh.cut(make_box(0.0, 8.0, 25.5, 80.0, 319.5, 390.0))
    sh = sh.cut(make_box(0.0, 8.0, -80.0, -29.2, 319.5, 390.0))

    # Structural pocketing for <= 200 g total system delta while maintaining high I-beam/closed-box stiffness!
    # 1. Under-AK45 outer arms H-channel pockets
    for y0, y1 in ((-45.5, -32.0), (32.0, 45.5)):
        sh = sh.cut(make_box(-64.0, -56.5, y0, y1, 315.0, 319.0))
        sh = sh.cut(make_box(-55.5, -52.0, y0, y1, 315.0, 319.0))
    # 2. Central bay deep I-beam pockets + lightening windows
    sh = sh.cut(make_box(-64.0, -56.4, -27.0, 17.5, 316.5, 336.0))
    sh = sh.cut(make_box(-53.2, -45.5, -27.0, 17.5, 316.5, 336.0))
    sh = sh.cut(make_box(-64.0, -45.0, -23.5, -3.5, 319.0, 333.5))
    sh = sh.cut(make_box(-64.0, -45.0, 3.5, 16.5, 319.0, 333.5))
    # 3. Left-of-K2 forward highway: pocket into a stiff 3.2 mm truss/C-channel web
    sh = sh.cut(make_box(-43.0, -3.5, 22.8, 31.0, 318.0, 337.0))
    sh = sh.cut(make_box(-40.0, -23.0, 19.0, 31.0, 319.0, 336.0))
    sh = sh.cut(make_box(-19.0, -5.5, 19.0, 31.0, 319.0, 336.0))
    # Also pocket transition neck at X[-1, 9]
    sh = sh.cut(make_box(-1.5, 9.5, 19.0, 26.0, 319.0, 333.5))
    # 4. Forward bay cross-tie box: hollow closed box leaving 3.2 mm front/rear walls + 3.2 mm top/bottom flanges
    sh = sh.cut(make_box(11.7, 21.8, -27.0, 27.0, 333.0, 342.0))
    sh = sh.cut(make_box(11.7, 21.8, -10.5, 10.5, 333.0, 346.0))
    # Lightening slot in left bulkhead ear between Y=30 and Y=44
    sh = sh.cut(make_box(-4.0, 0.5, 31.5, 44.5, 323.0, 329.5))

    # Drill 608 bearing bores & all M4/M3 mounting holes
    sh = drill_608_bores(sh)
    for sg in (1.0, -1.0):
        sh = sh.cut(make_cyl(2.15, 14.0, (-9.0, sg * 51.0, 326.0), (1.0, 0.0, 0.0)))
        for z_h in (326.0, 339.205):
            sh = sh.cut(make_cyl(2.15, 12.0, (30.0, sg * 24.0, z_h), (0.0, sg, 0.0)))
    # Two M3 upward vertical bolt holes into neck_root_base underside at (14.5, ±13.5, 345.2) — clear of L1 & K4!
    for sg in (1.0, -1.0):
        sh = sh.cut(make_cyl(1.65, 15.0, (14.5, sg * 13.5, 332.0), (0.0, 0.0, 1.0)))
    return sh


def build_opt_b2_anchored_bridge_stator_ties() -> Part.Shape:
    """Option B2 (RECOMMENDED): Option B1 + symmetric front-inboard vertical C-frame tie columns
    to left/right_stator_base underside (Z=367.1) with >= 1.5 mm AK45 clearance."""
    sh = build_opt_b1_anchored_lower_bridge()

    # Symmetric Left & Right Vertical C-Frame Tie Columns:
    # Column: X[-39.0, -31.5], |Y|[32.5, 41.0], Z[336.0, 367.05]
    # Top flange under stator_base (Z=[362.5, 367.05]): X[-39.0, -30.5], |Y|[32.5, 42.5] (trimmed against r=28.0 AK45 keepout!)
    # Upper cross-bar at Z=[336.0, 340.5] tying left & right column bases directly across Y[-41, +41]
    add_parts = [
        make_box(-39.0, -31.5, 32.5, 41.0, 336.0, 367.05),
        make_box(-39.0, -30.5, 32.5, 42.5, 362.5, 367.05),
        make_box(-39.0, -31.5, 26.0, 41.0, 336.0, 340.5),
        make_box(-46.5, -31.5, 19.8, 30.5, 336.0, 340.5),
        make_box(-39.0, -31.5, -41.0, -32.5, 336.0, 367.05),
        make_box(-39.0, -30.5, -42.5, -32.5, 362.5, 367.05),
        make_box(-39.0, -31.5, -41.0, -26.0, 336.0, 340.5),
        make_box(-46.5, -31.5, -30.5, -18.0, 336.0, 340.5),
        make_box(-39.0, -31.5, -33.0, 33.0, 336.0, 340.5),
    ]
    sh = fuse_all([sh, *add_parts])
    # Guaranteed >= 1.5 mm radial clearance keepout around both AK45 motor cases (r=26.5 -> cut r=28.0, Z=322.5..368)
    for sg in (1.0, -1.0):
        sh = sh.cut(make_cyl(28.0, 46.0, (-60.0, sg * 60.0, 322.5)))
    # Trim unused center-front notch on upper bar (leaving 3.5 mm stiff continuous cross-bar at X[-39.0, -35.5])
    sh = sh.cut(make_box(-35.5, -31.0, -17.0, 17.0, 335.5, 341.0))
    # Drill M4x38 vertical through-bore straight up each vertical column at (-35.5, ±37.0) into tapped stator_base!
    for sg in (1.0, -1.0):
        sh = sh.cut(make_cyl(2.15, 36.0, (-35.5, sg * 37.0, 334.0), (0.0, 0.0, 1.0)))
    return sh


def build_opt_c_independent_brackets() -> tuple[Part.Shape, Part.Shape]:
    """Option C: Bilateral independent short lower-seat brackets (NO cross-bridge connecting L & R)."""
    corr = json.loads(CORRIDORS_Z312.read_text())

    # LEFT independent bracket: exploits clean Left-of-K2 straight highway to left_corner_low_x & left_panel_30
    left_parts = [
        bearing_cup(1.0),
        # Short straight lower arm under left AK45 into Left-of-K2 corridor
        make_box(-63.5, -52.5, 22.0, 52.0, 312.5, 321.5),
        make_box(-63.5, -53.5, 45.0, 54.0, 308.5, 313.5),
        # Left-of-K2 forward shear web (Y >= +19.8, strictly left side, no cross-bridge!)
        make_box(-63.5, -45.5, 20.0, 30.5, 312.5, 340.0),
        make_box(-46.5, 0.0, 19.8, 30.5, 314.5, 340.0),
        make_box(-1.0, 9.0, 19.8, 25.0, 314.5, 340.0),
        make_box(8.5, 28.5, 19.8, 30.95, 333.5, 344.2),
        # Left bulkhead corner_low_x ear
        make_box(-4.0, -0.05, 25.0, 56.5, 320.5, 333.5),
        # Left sideplate pad (X=24..35, Y=27..30.95)
        make_box(24.0, 35.0, 27.0, 30.95, 321.5, 344.2),
    ]
    left_sh = fuse_all(left_parts)
    left_sh = left_sh.cut(make_box(0.0, 8.0, 25.5, 80.0, 319.5, 390.0))
    # Pocket left web
    left_sh = left_sh.cut(make_box(-42.0, -4.5, 23.0, 31.0, 318.5, 336.5))
    left_sh = left_sh.cut(make_box(-38.0, -23.0, 19.0, 31.0, 320.0, 335.0))
    left_sh = left_sh.cut(make_box(-18.0, -6.5, 19.0, 31.0, 320.0, 335.0))
    left_sh = drill_608_bores(left_sh, sides=(1.0,))
    left_sh = left_sh.cut(make_cyl(2.15, 14.0, (-9.0, 51.0, 326.0), (1.0, 0.0, 0.0)))
    for z_h in (326.0, 339.205):
        left_sh = left_sh.cut(make_cyl(2.15, 12.0, (30.0, 24.0, z_h), (0.0, 1.0, 0.0)))

    # RIGHT independent bracket: K2 & swept yoke pinch out straight forward corridor -> MUST detour
    # over K2 ear (front_upper_x) AND under K2 body (sideplate_y)!
    r_front = corr["right_fixed"]["front_upper_x"]["controls_mm"]
    r_side = corr["right_fixed"]["sideplate_y"]["controls_mm"]
    right_parts = [
        bearing_cup(-1.0),
        make_box(-63.5, -53.5, -54.0, -45.0, 308.5, 313.5),
        # Hub transition sphere
        Part.makeSphere(5.0, V(*r_front[0])),
        # Over-K2-ear detour to right_corner_low_x (0, -51, 326)
        path_tube([*r_front, [-3.0, -49.5, 326.0]], 3.45),
        # Under-K2 detour to right_panel_30 (30, -31, 326/339.2)
        path_tube([*r_side, [26.0, -24.0, 326.0], [27.0, -28.5, 329.0]], 3.45),
        # Right bulkhead ear & sideplate pad
        make_box(-4.0, -0.05, -56.5, -44.5, 320.5, 333.5),
        make_box(24.0, 35.0, -30.95, -27.0, 321.5, 344.2),
    ]
    right_sh = fuse_all(right_parts)
    # Trim any tangent intrusion into right_front_bulkhead or right_longitudinal_sideplate
    right_sh = right_sh.cut(make_box(0.0, 8.0, -80.0, -29.2, 319.5, 390.0))
    right_sh = right_sh.cut(make_box(8.0, 60.0, -37.0, -31.0, 319.5, 386.0))
    right_sh = drill_608_bores(right_sh, sides=(-1.0,))
    right_sh = right_sh.cut(make_cyl(2.15, 14.0, (-9.0, -51.0, 326.0), (1.0, 0.0, 0.0)))
    for z_h in (326.0, 339.205):
        right_sh = right_sh.cut(make_cyl(2.15, 12.0, (30.0, -24.0, z_h), (0.0, -1.0, 0.0)))

    return left_sh, right_sh


def load_moving_shapes(obs_cache: dict) -> dict[str, list[tuple[str, Part.Shape]]]:
    def get_obs(nm: str) -> Part.Shape:
        if nm not in obs_cache:
            obs_cache[nm] = geo.careful_obstacle(nm)
        return obs_cache[nm]

    mov = {}
    for side in ("left", "right"):
        tri = Part.Shape()
        tri.read(str(NAT_Z312 / f"{side}_rotating_trident.brep"))
        yoke = get_obs(f"{side}_parent_yoke_003")
        hr_case = get_obs(f"{side}_hip_roll_catalog_case")
        hr_env = get_obs(f"{side}_hip_rotor_output_envelope")
        mov[side] = [
            (f"{side}_rotating_trident", tri),
            (f"{side}_parent_yoke_003", yoke),
            (f"{side}_hip_roll_catalog_case", hr_case),
            (f"{side}_hip_rotor_output_envelope", hr_env),
        ]
    return mov


def audit_shape(
    label: str,
    shape: Part.Shape,
    world_torso: list[dict],
    overlays: dict[str, Part.Shape],
    mov_shapes: dict[str, list[tuple[str, Part.Shape]]],
    obs_cache: dict[str, Part.Shape],
    check_bearing: bool = True,
) -> dict:
    bb = shape.BoundBox
    pad = 8.0

    def get_obs(nm: str) -> Part.Shape:
        if nm not in obs_cache:
            obs_cache[nm] = geo.careful_obstacle(nm)
        return obs_cache[nm]

    hard_collisions = []
    replaced_fastener_overlaps = []
    legacy_reserve_overlaps = []
    mating_contacts = []
    key_clearances = {}

    KEY_OBSTACLES = {
        "k1_main_load_contactor",
        "k1_main_load_contactor_A1_lug",
        "k1_main_load_contactor_A2_lug",
        "k1_narrow_mount_ear_0",
        "k1_narrow_mount_ear_1",
        "k2_precharge_contactor",
        "k2_narrow_mount_ear_0",
        "k2_narrow_mount_ear_0_frame_m3x10",
        "k2_narrow_mount_ear_0_m4x16",
        "electrical_cassette_front_yoke_and_forearm",
        "electrical_cassette_BMS_bypass_rear_spine",
        "left_hip_yaw_ak45_10_case_009_c01",
        "right_hip_yaw_ak45_10_case_009_c01",
        "l1_inductive_turnoff_tvs",
        "l1_body_side_cradle_g10",
        "audio_buck_d36v6alv_oem_000",
        "left_front_bulkhead",
        "right_front_bulkhead",
        "left_longitudinal_sideplate",
        "right_longitudinal_sideplate",
        "neck_root_base",
        "left_stator_base",
        "right_stator_base",
    }

    MATING_TARGETS = {
        "left_front_bulkhead", "right_front_bulkhead",
        "left_longitudinal_sideplate", "right_longitudinal_sideplate",
        "neck_root_base", "left_stator_base", "right_stator_base",
        "left_clamp_negative_y", "right_clamp_positive_y",
    }

    min_non_mating_fixed = {"gap_mm": 999.0, "part": None}

    for r in world_torso:
        nm = r["name"]
        b = r["bbox_world_mm"]
        near = not (
            b[3] < bb.XMin - pad or b[0] > bb.XMax + pad
            or b[4] < bb.YMin - pad or b[1] > bb.YMax + pad
            or b[5] < bb.ZMin - pad or b[2] > bb.ZMax + pad
        )
        if not near and nm not in KEY_OBSTACLES:
            continue
        obs = get_obs(nm)
        ov = float(shape.common(obs).Volume) if near else 0.0
        gap = 0.0 if ov > 0.001 else float(shape.distToShape(obs)[0])
        if nm in KEY_OBSTACLES:
            key_clearances[nm] = {"overlap_mm3": round(ov, 4), "gap_mm": round(gap, 3)}
        if ov > 0.05:
            if nm in REPLACED_FASTENERS:
                replaced_fastener_overlaps.append({"part": nm, "overlap_mm3": round(ov, 2)})
            elif nm in LEGACY_SUPERSEDED_RESERVES:
                legacy_reserve_overlaps.append({"part": nm, "overlap_mm3": round(ov, 2)})
            else:
                hard_collisions.append({"part": nm, "overlap_mm3": round(ov, 3)})
        else:
            if nm in MATING_TARGETS and gap <= 0.25:
                mating_contacts.append({"part": nm, "gap_mm": round(gap, 4)})
            elif nm not in REPLACED_FASTENERS and nm not in LEGACY_SUPERSEDED_RESERVES and nm not in MATING_TARGETS:
                if gap < min_non_mating_fixed["gap_mm"]:
                    min_non_mating_fixed = {"gap_mm": round(gap, 3), "part": nm}

    # Check active closeout overlays
    overlay_audit = {}
    for oname, osh in overlays.items():
        ov = float(shape.common(osh).Volume)
        gap = 0.0 if ov > 0.001 else float(shape.distToShape(osh)[0])
        overlay_audit[oname] = {"overlap_mm3": round(ov, 4), "gap_mm": round(gap, 3)}
        if ov > 0.05:
            hard_collisions.append({"part": f"overlay/{oname}", "overlap_mm3": round(ov, 3)})

    # Check swept bilateral moving hip parts
    moving_collisions = []
    min_moving_gap = {"gap_mm": 999.0, "part": None, "yaw_rad": None}
    for side, sg in [("left", 1.0), ("right", -1.0)]:
        for q_yaw in YAW_SAMPLES:
            sh_rot = shape.copy()
            sh_rot.rotate(V(-60.0, sg * 60.0, 351.675), V(0, 0, 1), math.degrees(-q_yaw * sg))
            rbb = sh_rot.BoundBox
            for mname, msh in mov_shapes[side]:
                mbb = msh.BoundBox
                if (
                    mbb.XMax < rbb.XMin - pad or mbb.XMin > rbb.XMax + pad
                    or mbb.YMax < rbb.YMin - pad or mbb.YMin > rbb.YMax + pad
                    or mbb.ZMax < rbb.ZMin - pad or mbb.ZMin > rbb.ZMax + pad
                ):
                    continue
                ov = float(sh_rot.common(msh).Volume)
                if ov > 0.05:
                    moving_collisions.append({"part": mname, "yaw_rad": round(q_yaw * sg, 3), "overlap_mm3": round(ov, 3)})
                else:
                    gap = float(sh_rot.distToShape(msh)[0])
                    if gap < min_moving_gap["gap_mm"]:
                        min_moving_gap = {"gap_mm": round(gap, 3), "part": mname, "yaw_rad": round(q_yaw * sg, 3)}

    # Check nominal SKF 608-2RSH outer-race fit (zero overlap with 8/22/7 bearing envelope)
    bearing_check = {}
    if check_bearing:
        for side, sg in [("left", 1.0), ("right", -1.0)]:
            b_env = make_cyl(11.0, 7.0, (-60.0, sg * 60.0, 308.5)).cut(make_cyl(4.0, 7.0, (-60.0, sg * 60.0, 308.5)))
            ov = float(shape.common(b_env).Volume)
            bearing_check[side] = {"bearing_overlap_mm3": round(ov, 4)}
            if ov > 0.05:
                hard_collisions.append({"part": f"{side}_608_2RSH", "overlap_mm3": round(ov, 3)})

    return {
        "label": label,
        "hard_fixed_collisions": hard_collisions,
        "moving_collisions": moving_collisions,
        "zero_hard_collision": len(hard_collisions) == 0 and len(moving_collisions) == 0,
        "replaced_fastener_overlaps": replaced_fastener_overlaps,
        "legacy_wt901_reserve_overlaps": legacy_reserve_overlaps,
        "mating_contacts": mating_contacts,
        "min_non_mating_fixed_gap": min_non_mating_fixed,
        "min_swept_moving_gap": min_moving_gap,
        "key_clearances": key_clearances,
        "overlay_audit": overlay_audit,
        "bearing_envelope_check": bearing_check,
    }


def audit_corridors_and_serviceability(
    world_torso: list[dict],
    overlays: dict[str, Part.Shape],
    mov_shapes: dict[str, list[tuple[str, Part.Shape]]],
    obs_cache: dict[str, Part.Shape],
    opt_b2_shape: Part.Shape,
) -> dict:
    """Explicitly audit Astra's X=-53, Z=315 corridor vs discovered corridors & tool/608 service envelopes."""
    corridor_probes = [
        ("astra_x53_z315_6x6", make_box(-56.0, -50.0, -45.0, 45.0, 312.0, 318.0)),
        ("astra_x53_z315_10x10", make_box(-58.0, -48.0, -45.0, 45.0, 310.0, 320.0)),
        ("shifted_under_ak45_11x9", make_box(-63.5, -52.5, -48.0, 48.0, 312.5, 321.5)),
        ("central_bay_deep_web", make_box(-63.5, -46.0, -30.5, 30.5, 312.5, 340.5)),
        ("left_of_k2_fwd_highway", make_box(-45.5, 0.0, 19.8, 30.5, 314.5, 340.5)),
        ("right_straight_fwd_pinch_test", make_box(-45.5, 0.0, -30.5, -19.8, 314.5, 340.5)),
        ("left_front_inb_vertical_col", make_box(-39.0, -31.5, 32.5, 41.0, 336.0, 367.0)),
        ("right_front_inb_vertical_col", make_box(-39.0, -31.5, -41.0, -32.5, 336.0, 367.0)),
        ("fwd_bay_cross_box", make_box(8.5, 28.5, -30.5, 30.5, 333.5, 345.0)),
    ]
    corridor_results = {}
    for name, box in corridor_probes:
        res = audit_shape(name, box, world_torso, overlays, mov_shapes, obs_cache, check_bearing=False)
        corridor_results[name] = {
            "bbox_mm": [round(v, 2) for v in (box.BoundBox.XMin, box.BoundBox.YMin, box.BoundBox.ZMin, box.BoundBox.XMax, box.BoundBox.YMax, box.BoundBox.ZMax)],
            "zero_hard_collision": res["zero_hard_collision"],
            "hard_fixed_collisions": res["hard_fixed_collisions"][:5],
            "moving_collisions": res["moving_collisions"][:3],
            "min_non_mating_fixed_gap": res["min_non_mating_fixed_gap"],
            "min_swept_moving_gap": res["min_swept_moving_gap"],
            "k1_gap_mm": res["key_clearances"].get("k1_main_load_contactor", {}),
            "k2_gap_mm": res["key_clearances"].get("k2_precharge_contactor", {}),
            "k2_ear_m3_gap_mm": res["key_clearances"].get("k2_narrow_mount_ear_0_frame_m3x10", {}),
        }

    # Serviceability & Tool-Access Probes
    def get_obs(nm: str) -> Part.Shape:
        if nm not in obs_cache:
            obs_cache[nm] = geo.careful_obstacle(nm)
        return obs_cache[nm]

    service_probes = {
        # 608-2RSH -Z extraction/insertion drop cylinder (Ø22.2 mm x 10 mm clear drop Z=298.5..308.4)
        "left_608_minus_z_drop_10mm": make_cyl(11.1, 9.9, (-60.0, 60.0, 298.5)),
        "right_608_minus_z_drop_10mm": make_cyl(11.1, 9.9, (-60.0, -60.0, 298.5)),
        # 3 mm hex-key tool cylinder (Ø6 mm) for corner_low_x M4 SHCS from -X (X=-31..-5, Y=±51, Z=326)
        "left_corner_low_x_hex_access": make_cyl(3.0, 26.0, (-31.0, 51.0, 326.0), (1.0, 0.0, 0.0)),
        "right_corner_low_x_hex_access": make_cyl(3.0, 26.0, (-31.0, -51.0, 326.0), (1.0, 0.0, 0.0)),
        # 3 mm hex-key ball-end access for panel_30_326 & 339.2 from inboard center (Y=±24..0)
        "left_panel_30_326_hex_access": make_cyl(3.0, 22.0, (30.0, 4.0, 326.0), (0.0, 1.0, 0.0)),
        "right_panel_30_326_hex_access": make_cyl(3.0, 22.0, (30.0, -4.0, 326.0), (0.0, -1.0, 0.0)),
        "left_panel_30_339_hex_access": make_cyl(3.0, 22.0, (30.0, 4.0, 339.205), (0.0, 1.0, 0.0)),
        "right_panel_30_339_hex_access": make_cyl(3.0, 22.0, (30.0, -4.0, 339.205), (0.0, -1.0, 0.0)),
        # Vertical 2.5 mm hex-key access from -Z for neck_root M3 screws at (14.5, ±13.5, Z=305..333)
        "left_neck_root_m3_hex_access": make_cyl(2.5, 28.0, (14.5, 13.5, 305.0), (0.0, 0.0, 1.0)),
        "right_neck_root_m3_hex_access": make_cyl(2.5, 28.0, (14.5, -13.5, 305.0), (0.0, 0.0, 1.0)),
        # Vertical 3 mm hex-key access from -Z driving M4x38 upward through vertical column into stator_base at (-35.5, ±37.0)
        "left_stator_tie_bottom_hex_access": make_cyl(3.0, 26.0, (-35.5, 37.0, 309.5), (0.0, 0.0, 1.0)),
        "right_stator_tie_bottom_hex_access": make_cyl(3.0, 26.0, (-35.5, -37.0, 309.5), (0.0, 0.0, 1.0)),
    }
    service_results = {}
    for sname, cyl in service_probes.items():
        hits = []
        bb = cyl.BoundBox
        for r in world_torso:
            nm = r["name"]
            if nm in REPLACED_FASTENERS or nm in LEGACY_SUPERSEDED_RESERVES:
                continue
            b = r["bbox_world_mm"]
            if b[3] < bb.XMin - 0.5 or b[0] > bb.XMax + 0.5 or b[4] < bb.YMin - 0.5 or b[1] > bb.YMax + 0.5 or b[5] < bb.ZMin - 0.5 or b[2] > bb.ZMax + 0.5:
                continue
            ov = float(cyl.common(get_obs(nm)).Volume)
            if ov > 0.5:
                hits.append({"part": nm, "overlap_mm3": round(ov, 1)})
        # Also check self-obstruction against opt_b2_shape
        self_ov = float(cyl.common(opt_b2_shape).Volume)
        service_results[sname] = {
            "clear_of_fixed_obstacles": len(hits) == 0,
            "fixed_obstructions": hits[:5],
            "self_opt_b2_overlap_mm3": round(self_ov, 2),
        }
    return {"corridor_audit": corridor_results, "serviceability_tool_access": service_results}


def slice_polylines(shape: Part.Shape, axis: str, pos: float, n_pts: int = 32) -> list[list[list[float]]]:
    """Return 2D polylines [(u, v), ...] from exact OCCT planar slice."""
    normal = {"x": V(1, 0, 0), "y": V(0, 1, 0), "z": V(0, 0, 1)}[axis]
    try:
        wires = shape.slice(normal, pos)
    except Exception:
        return []
    polys = []
    for w in wires:
        pts = []
        for e in w.Edges:
            try:
                disc = e.discretize(max(4, min(n_pts, int(max(e.Length / 1.5, 4)))))
            except Exception:
                continue
            for p in disc:
                if axis == "x":
                    uv = [round(p.y, 2), round(p.z, 2)]
                elif axis == "y":
                    uv = [round(p.x, 2), round(p.z, 2)]
                else:
                    uv = [round(p.x, 2), round(p.y, 2)]
                if not pts or (abs(pts[-1][0] - uv[0]) > 1e-3 or abs(pts[-1][1] - uv[1]) > 1e-3):
                    pts.append(uv)
        if len(pts) >= 2:
            polys.append(pts)
    return polys


def export_cad_sections(
    candidates: dict[str, Part.Shape],
    obs_cache: dict[str, Part.Shape],
    mov_shapes: dict[str, list[tuple[str, Part.Shape]]],
) -> Path:
    """Export exact OCCT 2D cross-section polylines for multi-panel engineering figure."""
    def get_obs(nm: str) -> Part.Shape:
        if nm not in obs_cache:
            obs_cache[nm] = geo.careful_obstacle(nm)
        return obs_cache[nm]

    named_shapes = {
        "k1_contactor": get_obs("k1_main_load_contactor"),
        "k1_ear_0": get_obs("k1_narrow_mount_ear_0"),
        "k1_ear_1": get_obs("k1_narrow_mount_ear_1"),
        "k1_a1_lead": get_obs("k1_main_load_contactor_A1_local_power_lead"),
        "k1_a2_lead": get_obs("k1_main_load_contactor_A2_local_power_lead"),
        "k2_contactor": get_obs("k2_precharge_contactor"),
        "k2_ear_0": get_obs("k2_narrow_mount_ear_0"),
        "k2_ear_m3": get_obs("k2_narrow_mount_ear_0_frame_m3x10"),
        "k2_ear_m4": get_obs("k2_narrow_mount_ear_0_m4x16"),
        "cassette_forearm": get_obs("electrical_cassette_front_yoke_and_forearm"),
        "cassette_spine": get_obs("electrical_cassette_BMS_bypass_rear_spine"),
        "l1_tvs": get_obs("l1_inductive_turnoff_tvs"),
        "l1_cradle": get_obs("l1_body_side_cradle_g10"),
        "ak45_left": get_obs("left_hip_yaw_ak45_10_case_009_c01"),
        "ak45_right": get_obs("right_hip_yaw_ak45_10_case_009_c01"),
        "frame_l_bh": get_obs("left_front_bulkhead"),
        "frame_r_bh": get_obs("right_front_bulkhead"),
        "frame_l_sp": get_obs("left_longitudinal_sideplate"),
        "frame_r_sp": get_obs("right_longitudinal_sideplate"),
        "frame_neck": get_obs("neck_root_base"),
        "frame_l_stator": get_obs("left_stator_base"),
        "frame_r_stator": get_obs("right_stator_base"),
        "frame_l_clamp": get_obs("left_clamp_negative_y"),
        "frame_r_clamp": get_obs("right_clamp_positive_y"),
        "left_yoke": get_obs("left_parent_yoke_003"),
        "right_yoke": get_obs("right_parent_yoke_003"),
        "left_trident": mov_shapes["left"][0][1],
        "right_trident": mov_shapes["right"][0][1],
        "left_608": make_cyl(11.0, 7.0, (-60.0, 60.0, 308.5)).cut(make_cyl(4.0, 7.0, (-60.0, 60.0, 308.5))),
        "right_608": make_cyl(11.0, 7.0, (-60.0, -60.0, 308.5)).cut(make_cyl(4.0, 7.0, (-60.0, -60.0, 308.5))),
        **candidates,
    }
    # Add swept extreme yoke envelopes for XY/YZ plots
    for side, sg, q in [("left", 1.0, -0.06), ("right", -1.0, 0.06)]:
        yk = get_obs(f"{side}_parent_yoke_003").copy()
        yk.rotate(V(-60.0, sg * 60.0, 351.675), V(0, 0, 1), math.degrees(q))
        named_shapes[f"{side}_yoke_inward_extreme"] = yk

    planes = [
        ("xz_y0", "y", 0.0),
        ("xz_ym20_k2ear", "y", -20.0),
        ("xz_yp25_highway", "y", 25.0),
        ("xy_z317_bridge", "z", 317.0),
        ("xy_z338_anchor", "z", 338.0),
        ("yz_xm58_bridge", "x", -58.0),
        ("yz_xm35p5_cols", "x", -35.5),
    ]
    sections = {}
    for pid, ax, pos in planes:
        sec = {"axis": ax, "pos_mm": pos, "objects": {}}
        for nm, sh in named_shapes.items():
            polys = slice_polylines(sh, ax, pos)
            if polys:
                sec["objects"][nm] = polys
        sections[pid] = sec

    out_path = OUT_DIR / "cad_sections_a1.json"
    out_path.write_text(json.dumps(sections, indent=1) + "\n")
    return out_path


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CAD_DIR.mkdir(parents=True, exist_ok=True)

    world = json.loads(WORLD_PATH.read_text())["parts"]
    world_torso = [r for r in world if r["owner"] == "torso"]
    obs_cache: dict[str, Part.Shape] = {}
    overlays = {k: Part.read(str(p)) for k, p in OVERLAY_STEPS.items() if p.exists()}
    mov_shapes = load_moving_shapes(obs_cache)

    print("Building native 3D single-solid CAD candidates on assembly_finish_004...", flush=True)
    raw_candidates = {
        "opt_a_bare_bridge": build_opt_a_bare_bridge(),
        "opt_b1_anchored_lower_bridge": build_opt_b1_anchored_lower_bridge(),
        "opt_b2_anchored_bridge_stator_ties": build_opt_b2_anchored_bridge_stator_ties(),
    }
    opt_c_l, opt_c_r = build_opt_c_independent_brackets()
    raw_candidates["opt_c_left_bracket"] = opt_c_l
    raw_candidates["opt_c_right_bracket"] = opt_c_r

    saved = {}
    audits = {}
    for tag, sh in raw_candidates.items():
        meta = save_cold_solid(tag, sh)
        cold_sh = meta.pop("shape")
        saved[tag] = meta
        aud = audit_shape(tag, cold_sh, world_torso, overlays, mov_shapes, obs_cache, check_bearing=True)
        audits[tag] = aud
        print(
            f"  {tag:36s} | vol={meta['volume_mm3']:7.1f} mm3 | 7075={meta['mass_7075_g']:5.1f}g "
            f"| zero_hard_col={aud['zero_hard_collision']} | min_fix={aud['min_non_mating_fixed_gap']} "
            f"| min_mov={aud['min_swept_moving_gap']}",
            flush=True,
        )
        if not aud["zero_hard_collision"]:
            print("    HARD FIXED:", aud["hard_fixed_collisions"][:6], flush=True)
            print("    MOVING:    ", aud["moving_collisions"][:6], flush=True)

    # Audit rotating trident lightweighting opportunity (baseline steel vs hybrid 7075-T6 + Ø8 hardened steel pin)
    tri_l = mov_shapes["left"][0][1]
    tri_r = mov_shapes["right"][0][1]
    # Pin envelope: Ø8 x 16.7 mm steel journal + Ø10.8 x 4 mm shoulder step -> ~1205 mm3 (~9.4 g steel)
    # Remaining 3 arms + collar: ~3792 mm3 (34.56 g net added steel after 573.5 mm3 yoke overlap vs hybrid Al+pin)
    pin_vol_mm3 = math.pi * (4.0 ** 2) * 16.7  # 839.4 mm3 -> 6.55 g hardened steel dowel pin
    tri_net_vol_per_side = 4423.5  # from dual_support_z312_joint_002/native/construction.json (exact yoke-subtracted net)
    trident_study = {
        "baseline_steel_net_vol_per_side_mm3": tri_net_vol_per_side,
        "baseline_steel_pair_mass_g": round(2.0 * tri_net_vol_per_side * RHO_STEEL_G_MM3, 2),
        "hybrid_7075_arm_plus_hardened_steel_dowel_pin": {
            "steel_pin_8x16p7_vol_mm3": round(pin_vol_mm3, 1),
            "steel_pin_mass_g_per_side": round(pin_vol_mm3 * RHO_STEEL_G_MM3, 2),
            "al7075_triarm_net_vol_mm3": round(tri_net_vol_per_side - pin_vol_mm3, 1),
            "al7075_triarm_mass_g_per_side": round((tri_net_vol_per_side - pin_vol_mm3) * RHO_7075_G_MM3, 2),
            "total_hybrid_mass_g_per_side": round(pin_vol_mm3 * RHO_STEEL_G_MM3 + (tri_net_vol_per_side - pin_vol_mm3) * RHO_7075_G_MM3, 2),
            "total_hybrid_pair_mass_g": round(2.0 * (pin_vol_mm3 * RHO_STEEL_G_MM3 + (tri_net_vol_per_side - pin_vol_mm3) * RHO_7075_G_MM3), 2),
            "mass_savings_vs_steel_pair_g": round(2.0 * (tri_net_vol_per_side - pin_vol_mm3) * (RHO_STEEL_G_MM3 - RHO_7075_G_MM3), 2),
        },
        "pocketed_tubular_steel_pair_mass_g": round(2.0 * (tri_net_vol_per_side * 0.78) * RHO_STEEL_G_MM3, 2),
    }
    print(f"  Rotating trident mass: baseline steel pair={trident_study['baseline_steel_pair_mass_g']}g | hybrid 7075+steel-pin pair={trident_study['hybrid_7075_arm_plus_hardened_steel_dowel_pin']['total_hybrid_pair_mass_g']}g (saves {trident_study['hybrid_7075_arm_plus_hardened_steel_dowel_pin']['mass_savings_vs_steel_pair_g']}g)", flush=True)

    print("Running corridor & tool-access serviceability audit...", flush=True)
    cold_shapes = {k: Part.read(str(CAD_DIR / f"{k}.step")) for k in saved}
    svc = audit_corridors_and_serviceability(world_torso, overlays, mov_shapes, obs_cache, cold_shapes["opt_b2_anchored_bridge_stator_ties"])

    print("Exporting exact OCCT 2D cross-section polylines...", flush=True)
    sec_path = export_cad_sections(cold_shapes, obs_cache, mov_shapes)

    receipt = {
        "schema": "goose_v0_2_a1_cad_anchor_study_20261125",
        "elapsed_s": round(time.time() - t0, 2),
        "inputs": {
            "assembly_registry_004": file_ref(REG_PATH),
            "world_bbox_inventory_004": file_ref(WORLD_PATH),
            "corridors_z312": file_ref(CORRIDORS_Z312),
            "overlays": {k: file_ref(p) for k, p in OVERLAY_STEPS.items() if p.exists()},
        },
        "candidates": saved,
        "clearance_audits": audits,
        "corridor_audit": svc["corridor_audit"],
        "serviceability_tool_access": svc["serviceability_tool_access"],
        "rotating_trident_lightweighting": trident_study,
        "sections_export": file_ref(sec_path),
    }
    rec_path = OUT_DIR / "cad_anchor_study_receipt.json"
    rec_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Wrote {rec_path} in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
