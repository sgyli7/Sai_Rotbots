"""Native OCCT/build123d validation of the serviceable UMT-H 1 A fuse pocket,
6P pin-1 removable breakout harness, and updated 26-component mini-board fit
on Goose V0.2 assembly_finish_004.
"""
from __future__ import annotations

import json
from pathlib import Path

from goose004_charge_conductors_20261122 import bent_edges, emit_fit, sweep_wire
from goose004_charge_straight_cap_exit_20261122 import continuous_crossing
from goose004_lminus_enclosure_tolerance_20261122 import bd, bounds, box, metric, read, ref, write
from goose004_pfb40_power_fit_20261122 import check
from goose004_pfb40_split_stage_20261123 import COVER_DOMAIN, awg20_straight, scene


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/internal_layout/sanyo24_direct_power_001"
BMS_HOLD_PATH = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261122/power_harness/charge_architecture/shared_corridor_003/bms_service_001/manufacturer_envelope_assessment.json"
REG4_PATH = ROOT / "artifacts/goose_v0_2/appearance_finish_execution_20261118_001/assembly_finish_004/assembly_registry.json"
OUT_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1"

MINI_BOARD_CENTER = (-112.5, 52.8, 345.0)
MINI_BOARD_GUARD_BOUNDS = ((-119.0, 48.0, 335.65), (-106.0, 57.6, 354.35))

# 16 baseline components + 10 added input-side precision OVP components
UPDATED_COMPONENTS = (
    ("pulse_130r_a", +1, -2.2, -6.55, 7.5, 3.4, 0.9),
    ("pulse_130r_b", +1, -0.4, -2.45, 7.5, 3.4, 0.9),
    ("max17608atc", +1, -4.05, 2.0, 3.2, 3.2, 1.0),
    ("tlv1811dckr_clamp", +1, -0.15, 2.0, 2.4, 2.6, 1.2),
    ("si2308bds", +1, 3.35, 2.0, 3.25, 3.2, 1.35),
    ("lm4040a25_clamp", +1, -4.0, 6.35, 3.15, 3.1, 1.35),
    ("pmeg4050ep", +1, 0.75, 6.35, 4.75, 2.75, 1.25),
    ("panasonic_35tqs47meu", -1, -1.85, -6.15, 7.65, 4.5, 1.65),
    ("smaj28a", -1, 2.35, -1.7, 5.6, 3.05, 2.55),
    ("tps7a1601drbt_pilot", -1, -3.6, -1.7, 3.2, 3.2, 1.2),
    ("vos618a_8t", -1, -0.5, 2.1, 6.1, 3.3, 2.1),
    ("bleed_8p2k_1206", -1, -3.6, 6.4, 3.35, 1.85, 1.15),
    ("pilot_cout_reserve_0805", -1, -0.1, 6.4, 2.3, 1.55, 1.35),
    ("input_hv_cin_reserve_1206", -1, 3.3, 6.4, 3.35, 1.85, 1.7),
    ("pilot_current_limit_2k_a", +1, 3.55, -7.75, 3.6, 1.85, 1.15),
    ("pilot_current_limit_2k_b", +1, 3.55, -5.62, 3.6, 1.85, 1.15),
    # Added input-side OVP circuit block
    ("lm4040a25_in_ovp", -1, 4.10, -5.90, 3.15, 3.10, 1.35),
    ("ovp_rfeed_100k_0603", -1, 4.10, -8.10, 1.80, 1.00, 0.70),
    ("tlv1811dckr_in_ovp", -1, 4.30, 1.80, 2.40, 2.60, 1.20),
    ("zener_33v_in_ovp_sod323", -1, 4.30, 4.20, 2.70, 1.50, 1.10),
    ("ovp_rt_75k_0603", +1, 4.70, 5.40, 1.80, 1.00, 0.70),
    ("ovp_rb_8k06_0603", +1, 4.70, 6.60, 1.80, 1.00, 0.70),
    ("ovp_rfb_12m_0603", +1, 4.70, 7.80, 1.80, 1.00, 0.70),
    ("ovp_cin_0603", +1, 4.80, -3.50, 1.80, 1.00, 0.90),
    ("ovp_rlim_470_0603", +1, 4.80, -2.30, 1.80, 1.00, 0.70),
    ("ovp_rpd_100k_0603", +1, 4.80, -1.10, 1.80, 1.00, 0.70),
)

# Selected Option (a): Rear-cover direct-access fuse pocket in 13 mm portal directly above mini-board
FUSE_POCKET_BOUNDS = ((-116.0, 49.0, 357.5), (-109.0, 56.0, 375.5))  # 7.0 x 7.0 x 18.0 mm
FUSE_PROBE_BOUNDS = ((-116.5, 48.5, 357.0), (-108.5, 56.5, 376.0))   # +0.5 mm all faces
FUSE_PULL_Y_BOUNDS = ((-116.0, 49.0, 357.5), (-109.0, 108.0, 375.5))
FUSE_GRIPPER_BOUNDS = ((-118.4, 53.4, 357.5), (-106.6, 108.0, 375.5))

# Wire 1: 6P Pin-1 (+X mating breakout) -> Fuse Pocket top
WIRE_6P_TO_FUSE_PTS = [
    (-126.2, 25.0, 423.5),
    (-125.2, 32.0, 426.5),
    (-108.5, 35.5, 426.8),
    (-108.5, 39.5, 415.0),
    (-112.5, 39.5, 400.2),
    (-112.5, 48.8, 400.2),
    (-112.5, 48.8, 376.2),
    (-112.5, 52.5, 375.5),
]

# Wire 2: Fuse Pocket bottom -> Mini-Board VBAT_FUSED pad (-117.9, 53.41, 349.18)
WIRE_FUSE_TO_PAD_PTS = [
    (-112.5, 52.5, 357.5),
    (-115.0, 54.0, 355.0),
    (-117.9, 54.0, 352.0),
    (-117.9, 53.41, 349.18),
]


def build_updated_board() -> dict[str, object]:
    """Build 26-component mini-board compound and prove zero internal overlap."""
    x, y, z = MINI_BOARD_CENTER
    parts = {"fr4_placement": box((x - 6.2, y - 0.6, z - 8.9), (x + 6.2, y + 0.6, z + 8.9))}
    for name, side, px, pz, dx, dz, height in UPDATED_COMPONENTS:
        floor = y + side * 0.6
        top = floor + side * height
        parts[name] = box(
            (x + px - dx / 2.0, min(top, floor), z + pz - dz / 2.0),
            (x + px + dx / 2.0, max(top, floor), z + pz + dz / 2.0),
        )
    low, high = MINI_BOARD_GUARD_BOUNDS
    for name, solid in parts.items():
        s_lo, s_hi = bounds(solid)
        assert all(gl <= sl and sh <= gh for gl, sl, sh, gh in zip(low, s_lo, s_hi, high, strict=True)), name

    names = list(parts)
    for j, name in enumerate(names):
        a = parts[name]
        for older in names[:j]:
            common = metric(a, parts[older])
            assert common["volume_mm3"] <= 0.001, (name, older, common)
        a.label = name

    step_path = OUT_DIR / "updated_direct_power_component_placement.step"
    compound = bd.Compound(children=list(parts.values()))
    bd.export_step(compound, step_path)
    reopen = bd.import_step(step_path)
    assert len(reopen.solids()) == len(parts) and reopen.is_valid
    return {
        "component_count": len(UPDATED_COMPONENTS),
        "solid_count_with_fr4": len(reopen.solids()),
        "guard_world_bounds_mm": [list(low), list(high)],
        "guard_dimensions_mm": [13.0, 9.6, 18.7],
        "envelope_unchanged_from_baseline": True,
        "internal_overlaps": [],
        "STEP": ref(step_path),
    }


def evaluate_cad() -> dict[str, object]:
    """Run native OCCT checks on assembly_finish_004 for fuse access & breakout."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src, refs, overlay, retired, cover, _ = scene()

    # Verify assembly_finish_004 2529-part registry parity
    reg4 = read(REG4_PATH)
    reg4_names = {r["name"] for r in reg4["parts"]}
    assert reg4_names == set(src.parts), "Mismatch between assembly_finish_004 and source004 registry"

    open_overlay = {n: s for n, s in overlay.items() if n not in cover}
    open_retired = retired | set(cover)
    cover_domain = bd.import_brep(COVER_DOMAIN)
    cover_poses = read(refs["selected_cover"])["selected_cap_departure_xyz_mm"]

    # 1. Updated 26-component mini-board check
    board_fit = build_updated_board()

    # 2. Baseline blocked fuse site + original AWG20 clamped stub proof
    baseline_native = read(BASELINE_DIR / "native_candidate.json")
    baseline_awg20 = awg20_straight(src, overlay)
    old_fuse = baseline_native["separate_1A_fuse_station"]

    # 3. Rejected corridor / alternate fuse candidates (Option b evaluation)
    rejected_candidates = {}
    cand_b_defs = {
        "B1_upper_portal_corridor": (
            ((-116.0, 49.0, 377.5), (-109.0, 56.0, 395.5)),
            ((-116.0, 49.0, 377.5), (-109.0, 108.0, 395.5)),
        ),
        "B2_lower_portal": (((-117.0, 48.5, 315.0), (-108.0, 56.5, 334.0)), None),
        "B3_6p_minusY_side": (((-154.0, 8.0, 400.0), (-136.0, 15.0, 407.0)), None),
        "B4_rear_bay_Y38": (((-134.0, 35.0, 357.0), (-127.0, 42.0, 376.0)), None),
    }
    for cname, (b_static, b_pull) in cand_b_defs.items():
        st = check(src, overlay, retired, {cname: box(*b_static)}, 0.5)
        entry = {
            "bounds_mm": [list(b_static[0]), list(b_static[1])],
            "static_overlaps": st["positive_overlaps"],
        }
        if b_pull is not None:
            sv = check(src, open_overlay, open_retired, {cname + "_pull_y": box(*b_pull)}, 0.5)
            entry["service_plus_y_overlaps"] = sv["positive_overlaps"]
            entry["rejected_reason"] = "Blocked along +Y tool extraction path by samtec_fixed_peek_receiving_frame / samtec_keyed_6061_guide_rail"
        else:
            entry["rejected_reason"] = "Static collision with fixed 004 chassis/harness solids"
        rejected_candidates[cname] = entry

    # 4. Selected Option (a): Rear-cover direct-access fuse pocket + 6P pin-1 breakout
    pocket = box(*FUSE_POCKET_BOUNDS)
    probe = box(*FUSE_PROBE_BOUNDS)
    pull_y = box(*FUSE_PULL_Y_BOUNDS)
    gripper = box(*FUSE_GRIPPER_BOUNDS)
    fuse_body = box((-115.15, 49.85, 358.5), (-109.85, 55.15, 374.5))  # 5.3 x 5.3 x 16.0 mm UMT-H envelope

    in_cover_vol = metric(pocket, cover_domain)["volume_mm3"]
    assert abs(in_cover_vol - pocket.volume) < 0.001

    static_res = check(src, overlay, retired, {"fuse_pocket_guard": pocket, "fuse_0p5mm_probe": probe}, 1.0)
    assert not static_res["positive_overlaps"], static_res["positive_overlaps"]

    service_res = check(src, open_overlay, open_retired, {"fuse_plus_y_pull": pull_y, "fuse_gripper_gauge": gripper}, 1.0)
    assert not service_res["positive_overlaps"], service_res["positive_overlaps"]

    # Check continuous rear-cover departure
    cover_clear = [
        {"member": n, "from_mm": a, "to_mm": b, **continuous_crossing(s, a, b, {"fuse_pocket_guard": pocket})}
        for n, s in cover.items()
        for a, b in zip(cover_poses[:-1], cover_poses[1:], strict=True)
    ]
    assert all(r["all_swept_boxes_clear"] for r in cover_clear)

    # Swept 6P Pin-1 breakout harness wires (OD 1.4 mm AWG22 PTFE)
    edges1 = bent_edges(WIRE_6P_TO_FUSE_PTS, 1.4)
    wire1, len1 = sweep_wire(edges1, edges1[0].position_at(0), edges1[0].tangent_at(0), 1.4)
    edges2 = bent_edges(WIRE_FUSE_TO_PAD_PTS, 1.2)
    wire2, len2 = sweep_wire(edges2, edges2[0].position_at(0), edges2[0].tangent_at(0), 1.4)

    wire_static = check(src, overlay, retired, {"wire_6p_to_fuse": wire1, "wire_fuse_to_pad": wire2}, 0.5)
    assert not wire_static["positive_overlaps"], wire_static["positive_overlaps"]

    # Verify exact 15-pose rear-cover departure against pocket & swept wires
    cover_pose_hits = []
    for pose in cover_poses:
        loc = bd.Location(tuple(pose))
        for cname, csolid in cover.items():
            moved = csolid.moved(loc)
            for tname, tsolid in [("fuse_pocket", pocket), ("wire_6p_to_fuse", wire1), ("wire_fuse_to_pad", wire2)]:
                m = metric(moved, tsolid)
                if m.get("volume_mm3", 0.0) > 0.001:
                    cover_pose_hits.append({"pose": pose, "cover_member": cname, "target": tname, **m})
    assert not cover_pose_hits, cover_pose_hits

    # Export native CAD witness files
    pocket_witness = emit_fit(OUT_DIR, "serviceable_fuse_pocket_guard", pocket, "Option A rear-cover direct-access UMT-H 1A pocket")
    fuse_body.label = "umt_h_1a_fuse_body"
    wire1.label = "wire_6p_pin1_to_fuse_pocket"
    wire2.label = "wire_fuse_pocket_to_vbat_fused"
    harness_step = OUT_DIR / "serviceable_fuse_breakout_harness.step"
    bd.export_step(bd.Compound(children=[fuse_body, wire1, wire2]), harness_step)

    # Extract Y-Z projection bounds of key context parts around the portal (X in [-160, -100]) for figure plotting
    context_parts = [
        "Flogic_all_loads_service_MicroFit_6p",
        "BMS_service_disconnect_unclad_G10_carrier",
        "left_thermal_high_rail",
        "tail_controls_and_fan_service_MicroFit_12p",
        "samtec_fixed_peek_receiving_frame",
        "samtec_cap_peek_receiver_and_guide_shoe",
        "tinybms_high_power_body",
        "bminus_route_00",
        "imu_wt901c_ttl_installation_reserve",
        "body_continuous_rear",
        "body016_front",
    ]
    context_bboxes = {n: [list(bounds(src.shape(n))[0]), list(bounds(src.shape(n))[1])] if n not in overlay else [list(bounds(overlay[n])[0]), list(bounds(overlay[n])[1])] for n in context_parts}
    context_bboxes["mini_board_guard"] = [list(MINI_BOARD_GUARD_BOUNDS[0]), list(MINI_BOARD_GUARD_BOUNDS[1])]
    context_bboxes["old_fuse_blocked_guard"] = old_fuse["guard_world_bounds_mm"]
    context_bboxes["new_fuse_pocket_guard"] = [list(FUSE_POCKET_BOUNDS[0]), list(FUSE_POCKET_BOUNDS[1])]
    context_bboxes["new_fuse_plus_y_pull"] = [list(FUSE_PULL_Y_BOUNDS[0]), list(FUSE_PULL_Y_BOUNDS[1])]

    receipt = {
        "status": "SERVICEABLE_FUSE_POCKET_AND_6P_BREAKOUT_CAD_VERIFIED",
        "assembly_basis": "assembly_finish_004 (2529 occurrences parity verified)",
        "assembly_registry": ref(REG4_PATH),
        "generator": ref(Path(__file__).resolve()),
        "updated_mini_board_fit": board_fit,
        "legacy_blocked_fuse_site": {
            "world_center_mm": old_fuse["world_center_mm"],
            "guard_world_bounds_mm": old_fuse["guard_world_bounds_mm"],
            "awg20_contiguous_free_z_mm": baseline_awg20["contiguous_free_z_mm"],
            "te_34130_required_mm": baseline_awg20["TE_34130_minimum_bare_barrel_length_mm"],
            "blocked_positive_overlaps": old_fuse["local_and_full_straight_service"]["positive_overlaps"],
        },
        "rejected_corridor_candidates": rejected_candidates,
        "selected_serviceable_fuse_architecture": {
            "option": "Option (a) Rear-cover direct-access fuse pocket in 13 mm portal + clean removable 6P pin-1 breakout",
            "pocket_world_bounds_mm": [list(FUSE_POCKET_BOUNDS[0]), list(FUSE_POCKET_BOUNDS[1])],
            "pocket_center_mm": [-112.5, 52.5, 366.5],
            "pocket_dimensions_mm": [7.0, 7.0, 18.0],
            "inside_cover_inner_domain_mm3": in_cover_vol,
            "pocket_witness": pocket_witness,
            "harness_step": ref(harness_step),
            "static_and_0p5mm_probe": static_res,
            "after_cover_plus_y_extraction": service_res,
            "continuous_cover_clear": True,
            "cover_15pose_hits": cover_pose_hits,
            "breakout_wires": {
                "takeoff_method": "Removable Molex Micro-Fit 3.0 Pin-1 dual-crimp / breakout tap at Flogic_all_loads_service_MicroFit_6p +X load-side Pin 1 (-126.2, 25.0, 423.5) mm; leaves clamped AWG20 source stub untouched.",
                "wire_6p_to_fuse_mm": len1,
                "wire_fuse_to_pad_mm": len2,
                "total_fused_feed_length_mm": len1 + len2,
                "waypoints_6p_to_fuse_mm": WIRE_6P_TO_FUSE_PTS,
                "waypoints_fuse_to_pad_mm": WIRE_FUSE_TO_PAD_PTS,
                "static_check": wire_static,
            },
        },
        "yz_context_bboxes_mm": context_bboxes,
        "bms_physical_sample_hold": {
            "source": ref(BMS_HOLD_PATH),
            "sku": "TinyBMS v2.1 high power with cooling plate",
            "status": "OPEN_STEP2_PHYSICAL_SAMPLE_HOLD",
            "upper_rail_overlap_mm3": 10.207124999999719,
            "right_rail_overlap_mm3": 6.170007667499769,
            "two_solid_nominal_upper_rail_overlap_mm3": 9.020249999999734,
            "note": "Zero fabricated clearance; physical v2.1 unit contour & rail datum check deferred to Step-2 hardware procurement.",
        },
    }
    write(OUT_DIR / "fuse_access_cad_receipt.json", receipt)
    print(f"Wrote { (OUT_DIR / 'fuse_access_cad_receipt.json').relative_to(ROOT) }")
    print(f"26-component mini-board: {board_fit['solid_count_with_fr4']} solids inside 13x9.6x18.7 mm, 0 overlaps")
    print(f"Pocket static/probe overlaps: {len(static_res['positive_overlaps'])}, +Y pull overlaps: {len(service_res['positive_overlaps'])}, wire overlaps: {len(wire_static['positive_overlaps'])}, cover hits: {len(cover_pose_hits)}")
    print(f"Wire lengths: 6P->fuse = {len1:.2f} mm, fuse->pad = {len2:.2f} mm, total = {len1+len2:.2f} mm")
    return receipt


if __name__ == "__main__":
    evaluate_cad()
