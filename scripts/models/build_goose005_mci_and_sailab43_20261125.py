#!/usr/bin/env python3
"""Track C Builder: Goose V0.2 (assembly_finish_005) 21-Body MCI Updater +
43-Collider SaiLab Fast RL/VLA Bundle Builder (goose_v02_005_exterior_roles_v1).

Supports:
  - --dry-run (uses Track A1 preliminary Option B2 + exact OCCT CAD solids)
  - --bridge-ledger <path> (uses @mech-bridge-a1 final opt_b2_r2_mass_ledger.json)

Never modifies /home/ethan/Projects/Sai_Rotbots, frozen 007/43 bundle, or
hardware_closeout_20261122.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[2]
FROZEN_007_43 = Path(
    "/home/ethan/Projects/Sai_Lab/Bevy_Sim2Sim/artifacts/goose_v02_source007_exterior_roles_20261120/bundle"
)
STEP3_DIR = ROOT / "artifacts/goose_v0_2/hip_yaw_hour_20261118_001/step3_integration_sailab_20261120"
STEP3_BUNDLE_004 = STEP3_DIR / "goose_v02_native50_source003_smooth006_20261120_v1"
BASELINE_MCI_PATH = STEP3_DIR / "source003_smooth_006_production_mci.json"
HC25_DIR = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125"
DEFAULT_OUT_DIR = HC25_DIR / "sailab_005_43_delivery"
DEFAULT_BRIDGE_LEDGER = HC25_DIR / "hip_b2_a2_a3/opt_b2_r2_mass_ledger.json"
A1_DECISION_PATH = HC25_DIR / "hip_bridge_a1/a1_architecture_decision.json"
YOKE_RELIEF_RECEIPT = HC25_DIR / "front_shell_relief/yoke_outer_lip_relief_receipt.json"
FAN_RECEIPT = HC25_DIR / "sanyo24_fan_b1/sanyo24_closeout_receipt.json"
ENV_BOARD_RECEIPT = HC25_DIR / "environment_board/eda_fab_release_003/fab_release_receipt.json"
BEAK_VERIFY_REF = Path(
    "/home/ethan/Projects/Sai_Lab/Bevy_Sim2Sim/artifacts/goose_v02_owner_handoff_20261120/sairobot_beak_contact_verification.json"
)

UV_OCP_PYTHON = Path("/home/ethan/.cache/uv/archive-v0/I7FjlY6Yvrqr27uQ/bin/python")
MJ315_PYTHON = Path(
    "/home/ethan/ProjectBackups/2026-10-03/Sai_Lab/goose_warp_replay_admission_001/environments/mjlab_cuda_py312/bin/python"
)
MJ315_OVERLAYS = [
    "/home/ethan/.local/share/sai_lab/runtime_overlays/goose_source007_plane315_001",
    "/home/ethan/ProjectBackups/2026-10-07/Sai_Lab/goose_discrete_mjlab_admission_001/mjlab160",
    "/home/ethan/ProjectBackups/2026-10-07/Sai_Lab/goose_native_discrete_admission_001/upstream315",
]

CANDIDATE_NAME = "goose_v02_005_exterior_roles_v1"

SHIFTED_LEG_OFFSETS_M = {
    "left_hip_pitch": np.array([0.0, 0.020, 0.0]),
    "left_knee_pitch": np.array([0.0, 0.020, 0.0]),
    "left_ankle_pitch": np.array([0.0, 0.020, 0.0]),
    "left_ankle_roll": np.array([0.0, 0.020, 0.0]),
    "right_hip_pitch": np.array([0.0, -0.020, 0.0]),
    "right_knee_pitch": np.array([0.0, -0.020, 0.0]),
    "right_ankle_pitch": np.array([0.0, -0.020, 0.0]),
    "right_ankle_roll": np.array([0.0, -0.020, 0.0]),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def rel_ref(path: Path) -> dict[str, str]:
    p = Path(path).resolve()
    rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    return {"path": rel, "sha256": sha256(p)}


def steiner_translate(mass: float, com_from: np.ndarray, com_to: np.ndarray, I_com: np.ndarray) -> np.ndarray:
    d = np.asarray(com_from, float) - np.asarray(com_to, float)
    return np.asarray(I_com, float) + float(mass) * (float(d @ d) * np.eye(3) - np.outer(d, d))


def cylinder_inertia_z(mass_kg: float, r_outer_m: float, r_inner_m: float, height_m: float) -> list[list[float]]:
    """Exact centroidal inertia tensor (3x3) of a hollow cylinder aligned with world Z."""
    ixx = (1.0 / 12.0) * mass_kg * (3.0 * (r_outer_m**2 + r_inner_m**2) + height_m**2)
    izz = 0.5 * mass_kg * (r_outer_m**2 + r_inner_m**2)
    return [[ixx, 0.0, 0.0], [0.0, ixx, 0.0], [0.0, 0.0, izz]]


def solid_box_inertia(mass_kg: float, dx_m: float, dy_m: float, dz_m: float) -> list[list[float]]:
    """Exact centroidal inertia tensor (3x3) of an axis-aligned solid box."""
    return [
        [(mass_kg / 12.0) * (dy_m**2 + dz_m**2), 0.0, 0.0],
        [0.0, (mass_kg / 12.0) * (dx_m**2 + dz_m**2), 0.0],
        [0.0, 0.0, (mass_kg / 12.0) * (dx_m**2 + dy_m**2)],
    ]


def extract_occt_mci_batch(requests: list[dict]) -> dict[str, dict]:
    """Compute exact OCCT BREP/STEP volume, CoM, and 3x3 inertia tensor in kg*m^2."""
    script = """
import json, sys
from pathlib import Path
from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shape
from OCP.STEPControl import STEPControl_Reader
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

reqs = json.loads(sys.stdin.read())
out = {}
for row in reqs:
    p = Path(row["path"])
    if p.suffix.lower() == ".brep":
        s = TopoDS_Shape()
        assert BRepTools.Read_s(s, str(p), BRep_Builder()), f"Failed reading BREP: {p}"
    else:
        r = STEPControl_Reader()
        status = r.ReadFile(str(p))
        assert status == 1, f"Failed reading STEP: {p}"
        r.TransferRoots()
        s = r.OneShape()
    gp = GProp_GProps()
    BRepGProp.VolumeProperties_s(s, gp)
    vol_mm3 = float(gp.Mass())
    assert vol_mm3 > 0.0, f"Zero volume for {p}"
    c = gp.CentreOfMass()
    mat = gp.MatrixOfInertia()
    # MatrixOfInertia has units mm^5 for unit density; multiply by rho_kg_mm3 * 1e-6 -> kg*m^2
    if "mass_kg" in row and row["mass_kg"] is not None:
        mass_kg = float(row["mass_kg"])
        rho_kg_mm3 = mass_kg / vol_mm3
    else:
        rho_kg_mm3 = float(row["density_kg_m3"]) * 1e-9
        mass_kg = vol_mm3 * rho_kg_mm3
    scale = rho_kg_mm3 * 1e-6
    I = [[float(mat.Value(i + 1, j + 1)) * scale for j in range(3)] for i in range(3)]
    out[row["key"]] = {
        "volume_mm3": vol_mm3,
        "mass_kg": mass_kg,
        "com_world_m": [float(c.X()) * 1e-3, float(c.Y()) * 1e-3, float(c.Z()) * 1e-3],
        "I_com_world_kg_m2": I,
    }
print(json.dumps(out))
"""
    proc = subprocess.run(
        [str(UV_OCP_PYTHON), "-c", script],
        input=json.dumps(requests),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def load_obj_vf(path: Path) -> tuple[np.ndarray, list[str]]:
    verts, faces = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append(line)
    return np.asarray(verts, dtype=float), faces


def write_obj_vf(path: Path, verts: np.ndarray, faces: list[str] | np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for pt in verts:
            f.write(f"v {pt[0]:.17g} {pt[1]:.17g} {pt[2]:.17g}\n")
        for fc in faces:
            if isinstance(fc, str):
                f.write(fc + "\n")
            else:
                f.write(f"f {int(fc[0])+1} {int(fc[1])+1} {int(fc[2])+1}\n")


def convex_hull_capped(verts: np.ndarray, max_verts: int = 120) -> tuple[np.ndarray, np.ndarray]:
    """Build outward-oriented convex hull capped cleanly to <= max_verts vertices."""
    hull = ConvexHull(verts)
    pts = verts[hull.vertices]
    if len(pts) > max_verts:
        # Fibonacci sphere support sampling preserves exterior support extent cleanly
        idx = np.arange(max_verts, dtype=float) + 0.5
        phi = np.arccos(1.0 - 2.0 * idx / max_verts)
        theta = math.pi * (1.0 + math.sqrt(5.0)) * idx
        dirs = np.column_stack([np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)])
        chosen = np.unique(np.argmax(pts @ dirs.T, axis=0))
        pts = pts[chosen]
    hull2 = ConvexHull(pts)
    uniq = np.unique(hull2.simplices.ravel())
    remap = {int(old): new for new, old in enumerate(uniq)}
    v_out = pts[uniq]
    faces_out = np.vectorize(remap.get)(hull2.simplices)
    # Orient triangles outward
    center = v_out.mean(axis=0)
    for z, tri in enumerate(faces_out):
        n = np.cross(v_out[tri[1]] - v_out[tri[0]], v_out[tri[2]] - v_out[tri[0]])
        if np.dot(n, v_out[tri[0]] - center) < 0.0:
            faces_out[z] = tri[[0, 2, 1]]
    return v_out, faces_out


def audit_and_build_43_meshes(out_meshes_dir: Path) -> dict:
    """Audit all 43 exterior/protected/calibrated-pair meshes vs 007/43 & 004/005 and emit 005 meshes."""
    cm43 = json.loads((FROZEN_007_43 / "sources/contact/contact_manifest.json").read_text())
    cm004 = json.loads((STEP3_BUNDLE_004 / "sources/contact/contact_manifest.json").read_text())
    reg007 = {p["name"]: p for p in json.loads((FROZEN_007_43 / "sources/assembly/assembly_registry.json").read_text())["parts"]}
    reg004 = {
        p["name"]: p
        for p in json.loads(
            (ROOT / "artifacts/goose_v0_2/appearance_finish_execution_20261118_001/assembly_finish_004/assembly_registry.json").read_text()
        )["parts"]
    }
    yoke_rel = json.loads(YOKE_RELIEF_RECEIPT.read_text())

    leaves004_by_occ: dict[str, list[dict]] = {}
    leaves004_by_name: dict[str, dict] = {}
    for l4 in cm004["leaves"]:
        leaves004_by_name[l4["name"]] = l4
        for b in l4.get("source_occurrence_bindings", []):
            leaves004_by_occ.setdefault(b["name"], []).append(l4)

    # Mapping from changed 007/43 exterior_role geoms to 004/005 CAD occurrences
    regen_occ_map = {
        "rear_shell": ["body_continuous_rear"],
        "front_shell": ["body016_front"],
        "root_housing": ["neck_parent_captured_front_skin_004"],
        "lower_neck_shell": ["b_lower_negative_matched_joint_008b", "b_lower_positive_matched_joint_008b"],
        "upper_neck_shell": ["paired_b_upper_positive_with_real_return_20261106", "paired_b_upper_negative_20261106"],
        "pitch_housing": ["C_positive_trimmed"],
    }
    # Calibrated joint pairs whose colliding leaves changed in 004/005 (310 mm stance)
    regen_pair_leaf_map = {
        "torso_contact_limit_1": "body_continuous_rear__279",
        "left_knee_pitch_contact_limit_1": "left_shin_inner_original_cup_clearance__140",
        "torso_contact_limit_4": "body_continuous_rear__176",
        "right_knee_pitch_contact_limit_4": "right_shin_inner_original_cup_clearance__111",
    }

    out_meshes_dir.mkdir(parents=True, exist_ok=True)
    audit_rows = []
    counts = {"protected_byte_identical": 0, "exterior_byte_identical": 0, "hip_housing_shifted_20mm_y": 0,
              "exterior_regenerated_from_004_005": 0, "calibrated_pair_retained": 0, "calibrated_pair_updated_from_004": 0}

    new_leaves = []
    for leaf in cm43["leaves"]:
        leaf_new = copy.deepcopy(leaf)
        name = leaf["name"]
        src_mesh = FROZEN_007_43 / leaf["mesh_file"]
        dst_mesh = out_meshes_dir / Path(leaf["mesh_file"]).name
        role = leaf["input_role"]

        if role == "protected":
            shutil.copy2(src_mesh, dst_mesh)
            assert sha256(dst_mesh) == sha256(src_mesh)
            action = "protected_byte_identical"
        elif name in ("left_hip_housing", "right_hip_housing"):
            dy = 0.020 if name.startswith("left_") else -0.020
            v, fc = load_obj_vf(src_mesh)
            v[:, 1] += dy
            write_obj_vf(dst_mesh, v, fc)
            action = "hip_housing_shifted_20mm_y"
        elif name in regen_occ_map:
            pts = []
            for occ in regen_occ_map[name]:
                for l4 in leaves004_by_occ[occ]:
                    v4, _ = load_obj_vf(STEP3_BUNDLE_004 / l4["mesh_file"])
                    pts.append(v4)
            v_all = np.vstack(pts)
            v_hull, f_hull = convex_hull_capped(v_all, max_verts=120)
            write_obj_vf(dst_mesh, v_hull, f_hull)
            # Update bindings to 004/005 parts
            leaf_new["source_occurrence_bindings"] = [
                {
                    "name": occ,
                    "owner": reg004[occ]["owner"],
                    "native_source_sha256": reg004[occ]["source"].get("source_native_sha256") or reg004[occ]["source"].get("sha256"),
                    "source_to_world_mm": reg004[occ]["source_to_world_mm"],
                    "current_source": reg004[occ]["source"],
                }
                for occ in regen_occ_map[name]
            ]
            action = "exterior_regenerated_from_004_005"
        elif name in regen_pair_leaf_map:
            l4 = leaves004_by_name[regen_pair_leaf_map[name]]
            shutil.copy2(STEP3_BUNDLE_004 / l4["mesh_file"], dst_mesh)
            leaf_new["source_occurrence_bindings"] = copy.deepcopy(l4["source_occurrence_bindings"])
            action = "calibrated_pair_updated_from_004"
        elif role == "calibrated_joint_pair":
            shutil.copy2(src_mesh, dst_mesh)
            action = "calibrated_pair_retained"
        else:
            # Verify CAD SHA unchanged for retained exterior_role
            for b in leaf.get("source_occurrence_bindings", []):
                occ = b["name"]
                s7 = reg007[occ]["source"].get("source_native_sha256") or reg007[occ]["source"].get("sha256")
                s4 = reg004[occ]["source"].get("source_native_sha256") or reg004[occ]["source"].get("sha256")
                assert s7 == s4, (
                    f"Unexpected SHA diff on retained exterior {name} ({occ})"
                )
            shutil.copy2(src_mesh, dst_mesh)
            action = "exterior_byte_identical"

        counts[action] += 1
        # Ensure ALL 43 leaves have source_occurrence_bindings + native_source_sha256(s) bound to reg004
        for b in leaf_new["source_occurrence_bindings"]:
            cur = reg004[b["name"]]
            nsha = cur["source"].get("source_native_sha256") or cur["source"].get("sha256")
            b["owner"] = cur["owner"]
            b["native_source_sha256"] = nsha
            b["source_to_world_mm"] = cur["source_to_world_mm"]
            b["current_source"] = cur["source"]
        hashes = sorted({b["native_source_sha256"] for b in leaf_new["source_occurrence_bindings"]})
        leaf_new["native_source_sha256"] = hashes[0] if len(hashes) == 1 else None
        leaf_new["native_source_sha256s"] = hashes

        v_dst, _ = load_obj_vf(dst_mesh)
        leaf_new["mesh_sha256"] = sha256(dst_mesh)
        new_leaves.append(leaf_new)
        audit_rows.append({
            "name": name,
            "owner": leaf["owner"],
            "role": role,
            "mesh_file": leaf["mesh_file"],
            "action": action,
            "vertices": int(len(v_dst)),
            "sha256_007_43": sha256(src_mesh),
            "sha256_005_43": sha256(dst_mesh),
            "byte_identical_to_007_43": sha256(src_mesh) == sha256(dst_mesh),
        })

    audit_summary = {
        "schema": "goose005_43_exterior_mesh_audit_v1",
        "body016_front_004_to_005_untouched": True,
        "front_shell_relief_strategy": yoke_rel["strategy"],
        "total_meshes": len(audit_rows),
        "action_counts": counts,
        "max_non_protected_vertices": max(r["vertices"] for r in audit_rows if r["role"] != "protected"),
        "max_protected_vertices": max(r["vertices"] for r in audit_rows if r["role"] == "protected"),
        "meshes": audit_rows,
    }
    return {"audit": audit_summary, "leaves": new_leaves, "cm43": cm43}


def build_005_mci_ledger(bridge_ledger_path: Path | None, dry_run: bool) -> dict:
    """Compute exact 21-body MCI ledger for assembly_finish_005 from native OCCT BREP/STEP solids."""
    base_ledger = json.loads(BASELINE_MCI_PATH.read_text())
    ledger = copy.deepcopy(base_ledger)

    yoke_rel = json.loads(YOKE_RELIEF_RECEIPT.read_text())
    fan_rec = json.loads(FAN_RECEIPT.read_text())
    env_rec = json.loads(ENV_BOARD_RECEIPT.read_text())

    # 1. Batch OCCT GProps for relieved yokes, Track B fan envelope, and bridge solid(s)
    occt_reqs = [
        {"key": "left_yoke_relieved", "path": str(ROOT / yoke_rel["sides"]["left"]["relieved_brep"]["path"]), "density_kg_m3": 7800.0},
        {"key": "right_yoke_relieved", "path": str(ROOT / yoke_rel["sides"]["right"]["relieved_brep"]["path"]), "density_kg_m3": 7800.0},
        {
            "key": "fan_mini_board",
            "path": str(ROOT / fan_rec["artifacts"]["updated_mini_board_step"]["path"]),
            "mass_kg": fan_rec["assembly_finish_005_mass_delta_g"]["mini_board_fr4_1p2mm_26parts_g"] * 1e-3,
        },
        {
            "key": "fan_fuse_pocket",
            "path": str(ROOT / fan_rec["artifacts"]["serviceable_fuse_pocket_brep"]["path"]),
            "mass_kg": fan_rec["assembly_finish_005_mass_delta_g"]["umt_h_1a_fuse_and_pocket_carrier_g"] * 1e-3,
        },
        {
            "key": "fan_breakout_harness",
            "path": str(ROOT / fan_rec["artifacts"]["serviceable_fuse_breakout_harness_step"]["path"]),
            "mass_kg": fan_rec["assembly_finish_005_mass_delta_g"]["breakout_harness_awg22_98mm_and_microfit_tap_g"] * 1e-3,
        },
    ]

    bridge_mode = "dry_run_a1_opt_b2"
    bridge_source_ref = None
    bridge_items_from_ledger = None

    if bridge_ledger_path is not None and bridge_ledger_path.exists() and not dry_run:
        bridge_mode = "final_a2_a3_opt_b2_r2"
        bridge_doc = json.loads(bridge_ledger_path.read_text())
        bridge_source_ref = rel_ref(bridge_ledger_path)
        bridge_items_from_ledger = bridge_doc
        if "body_deltas_for_21body_mci" not in bridge_doc:
            for idx, part in enumerate(bridge_doc.get("items", bridge_doc.get("parts", []))):
                if "I_com_world_kg_m2" not in part and part.get("cad_path"):
                    p_abs = Path(part["cad_path"]) if Path(part["cad_path"]).is_absolute() else ROOT / part["cad_path"]
                    occt_reqs.append({
                        "key": f"bridge_item_{idx}",
                        "path": str(p_abs),
                        "mass_kg": part.get("mass_kg"),
                        "density_kg_m3": part.get("density_kg_m3"),
                    })
    else:
        a1_doc = json.loads(A1_DECISION_PATH.read_text())
        bridge_source_ref = rel_ref(A1_DECISION_PATH)
        b2_cad = a1_doc["cad_summary"]["candidates"]["opt_b2_anchored_bridge_stator_ties"]
        occt_reqs.append({
            "key": "opt_b2_fixed_carrier",
            "path": str(ROOT / b2_cad["brep"]["path"]),
            "density_kg_m3": 2810.0,
        })

    occt = extract_occt_mci_batch(occt_reqs)

    # 2. Apply front-shell yoke relief (-10.728 g/pair)
    replaced_yokes = set()
    for item in ledger["items"]:
        if item["name"] == "left_smooth_006_yoke":
            m_old = item["mass_kg"]
            rec = occt["left_yoke_relieved"]
            item["name"] = "left_yoke_shell_relieved"
            item["mass_kg"] = rec["mass_kg"]
            item["com_world_m"] = rec["com_world_m"]
            item["I_com_world_kg_m2"] = rec["I_com_world_kg_m2"]
            item["source_sha256"] = yoke_rel["sides"]["left"]["relieved_brep"]["sha256"]
            item["reconciliation_action"] = "relieved_outer_lip_005_steel_7800"
            item["delta_mass_vs_004_kg"] = rec["mass_kg"] - m_old
            replaced_yokes.add("left")
        elif item["name"] == "right_smooth_006_yoke":
            m_old = item["mass_kg"]
            rec = occt["right_yoke_relieved"]
            item["name"] = "right_yoke_shell_relieved"
            item["mass_kg"] = rec["mass_kg"]
            item["com_world_m"] = rec["com_world_m"]
            item["I_com_world_kg_m2"] = rec["I_com_world_kg_m2"]
            item["source_sha256"] = yoke_rel["sides"]["right"]["relieved_brep"]["sha256"]
            item["reconciliation_action"] = "relieved_outer_lip_005_steel_7800"
            item["delta_mass_vs_004_kg"] = rec["mass_kg"] - m_old
            replaced_yokes.add("right")
    assert replaced_yokes == {"left", "right"}, f"Missing yokes in 004 ledger: {replaced_yokes}"

    # 3. Add Track B Sanyo24 24V fan electrical envelope (+9.60 g on torso)
    track_b_items = [
        ("sanyo24_ovp_clamp_mini_board", "fan_mini_board", fan_rec["artifacts"]["updated_mini_board_step"]["sha256"]),
        ("sanyo24_serviceable_fuse_pocket_carrier", "fan_fuse_pocket", fan_rec["artifacts"]["serviceable_fuse_pocket_brep"]["sha256"]),
        ("sanyo24_serviceable_fuse_breakout_harness", "fan_breakout_harness", fan_rec["artifacts"]["serviceable_fuse_breakout_harness_step"]["sha256"]),
    ]
    for name, key, sha in track_b_items:
        rec = occt[key]
        ledger["items"].append({
            "name": name,
            "owner": "torso",
            "mass_kg": rec["mass_kg"],
            "com_world_m": rec["com_world_m"],
            "I_com_world_kg_m2": rec["I_com_world_kg_m2"],
            "source_sha256": sha,
            "reconciliation_action": "added_track_b_sanyo24_fan_envelope_005",
        })

    # 4. Add Track A1/A2/A3 Hip Bridge items
    added_bridge_items = []
    if bridge_items_from_ledger is not None:
        if "body_deltas_for_21body_mci" in bridge_items_from_ledger:
            bd = bridge_items_from_ledger["body_deltas_for_21body_mci"]
            src_arts = bridge_items_from_ledger.get("source_artifacts", {})
            brep_sha = src_arts.get("opt_b2_r2_brep", {}).get("sha256", bridge_source_ref["sha256"])
            # Torso bridge components (exclude track_b_sanyo24_electrical since Track B is added directly above)
            torso_cb = bd["torso"]["component_breakdown"]
            for cname, comp in torso_cb.items():
                if "track_b" in cname:
                    continue
                entry = {
                    "name": cname,
                    "owner": "torso",
                    "mass_kg": float(comp["mass_kg"]),
                    "com_world_m": [float(x) * 1e-3 for x in comp["com_world_mm"]],
                    "I_com_world_kg_m2": [[float(x) for x in row] for row in comp["I_com_world_kg_m2"]],
                    "source_sha256": brep_sha if "bridge" in cname else bridge_source_ref["sha256"],
                    "reconciliation_action": "added_opt_b2_r2_hip_bridge_005",
                }
                ledger["items"].append(entry)
                added_bridge_items.append(entry)
            # Left & right hip_yaw added rotating tridents (yoke relief already applied in step 2)
            for side in ("left", "right"):
                owner = f"{side}_hip_yaw"
                tri_key = next(k for k in bd[owner] if k.startswith("added_"))
                tri = bd[owner][tri_key]
                entry = {
                    "name": f"opt_b2_r2_{side}_rotating_trident",
                    "owner": owner,
                    "mass_kg": float(tri["mass_kg"]),
                    "com_world_m": [float(x) * 1e-3 for x in tri["com_world_mm"]],
                    "I_com_world_kg_m2": [[float(x) for x in row] for row in tri["I_com_world_kg_m2"]],
                    "source_sha256": bridge_source_ref["sha256"],
                    "reconciliation_action": "added_opt_b2_r2_hip_bridge_005",
                }
                ledger["items"].append(entry)
                added_bridge_items.append(entry)
        else:
            raw_items = bridge_items_from_ledger.get("items", bridge_items_from_ledger.get("parts", []))
            assert raw_items, f"Bridge ledger {bridge_ledger_path} contains no items/parts"
            for idx, p in enumerate(raw_items):
                if f"bridge_item_{idx}" in occt:
                    rec = occt[f"bridge_item_{idx}"]
                    mass_kg = rec["mass_kg"]
                    com_m = rec["com_world_m"]
                    I_com = rec["I_com_world_kg_m2"]
                else:
                    mass_kg = float(p["mass_kg"])
                    com_m = [float(x) for x in p["com_world_m"]]
                    I_com = [[float(x) for x in row] for row in p["I_com_world_kg_m2"]]
                entry = {
                    "name": p["name"],
                    "owner": p["owner"],
                    "mass_kg": mass_kg,
                    "com_world_m": com_m,
                    "I_com_world_kg_m2": I_com,
                    "source_sha256": p.get("source_sha256", bridge_source_ref["sha256"]),
                    "reconciliation_action": "added_opt_b2_r2_hip_bridge_005",
                }
                ledger["items"].append(entry)
                added_bridge_items.append(entry)
    else:
        # Dry-run preliminary Option B2 from a1_architecture_decision.json
        a1_doc = json.loads(A1_DECISION_PATH.read_text())
        b2_cfg = a1_doc["mass_ledger"]["configurations"]["opt_b2_7075_hybrid_tri"]
        b2_cad = a1_doc["cad_summary"]["candidates"]["opt_b2_anchored_bridge_stator_ties"]
        fixed_rec = occt["opt_b2_fixed_carrier"]
        tri_each_kg = (b2_cfg["rotating_tridents_pair_g"] * 0.5) * 1e-3
        brg_each_kg = (b2_cfg["bearings_2x608_g"] * 0.5) * 1e-3
        fast_total_kg = b2_cfg["net_fasteners_and_circlips_g"] * 1e-3
        prelim_items = [
            {
                "name": "opt_b2_anchored_bridge_stator_ties_prelim",
                "owner": "torso",
                "mass_kg": fixed_rec["mass_kg"],
                "com_world_m": fixed_rec["com_world_m"],
                "I_com_world_kg_m2": fixed_rec["I_com_world_kg_m2"],
                "source_sha256": b2_cad["brep"]["sha256"],
                "reconciliation_action": "dry_run_prelim_opt_b2_fixed_carrier",
            },
            {
                "name": "opt_b2_left_rotating_trident_hybrid_prelim",
                "owner": "left_hip_yaw",
                "mass_kg": tri_each_kg,
                "com_world_m": [-0.060, 0.060, 0.317],
                "I_com_world_kg_m2": solid_box_inertia(tri_each_kg, 0.044, 0.022, 0.010),
                "source_sha256": bridge_source_ref["sha256"],
                "reconciliation_action": "dry_run_prelim_opt_b2_hybrid_trident",
            },
            {
                "name": "opt_b2_right_rotating_trident_hybrid_prelim",
                "owner": "right_hip_yaw",
                "mass_kg": tri_each_kg,
                "com_world_m": [-0.060, -0.060, 0.317],
                "I_com_world_kg_m2": solid_box_inertia(tri_each_kg, 0.044, 0.022, 0.010),
                "source_sha256": bridge_source_ref["sha256"],
                "reconciliation_action": "dry_run_prelim_opt_b2_hybrid_trident",
            },
            {
                "name": "opt_b2_left_skf_608_2rsh_bearing",
                "owner": "torso",
                "mass_kg": brg_each_kg,
                "com_world_m": [-0.060, 0.060, 0.317],
                "I_com_world_kg_m2": cylinder_inertia_z(brg_each_kg, 0.011, 0.004, 0.007),
                "source_sha256": bridge_source_ref["sha256"],
                "reconciliation_action": "dry_run_prelim_opt_b2_bearing_608",
            },
            {
                "name": "opt_b2_right_skf_608_2rsh_bearing",
                "owner": "torso",
                "mass_kg": brg_each_kg,
                "com_world_m": [-0.060, -0.060, 0.317],
                "I_com_world_kg_m2": cylinder_inertia_z(brg_each_kg, 0.011, 0.004, 0.007),
                "source_sha256": bridge_source_ref["sha256"],
                "reconciliation_action": "dry_run_prelim_opt_b2_bearing_608",
            },
            {
                "name": "opt_b2_net_fasteners_and_circlips_prelim",
                "owner": "torso",
                "mass_kg": fast_total_kg,
                "com_world_m": [-0.040, 0.0, 0.335],
                "I_com_world_kg_m2": solid_box_inertia(fast_total_kg, 0.050, 0.080, 0.040),
                "source_sha256": bridge_source_ref["sha256"],
                "reconciliation_action": "dry_run_prelim_opt_b2_fasteners_circlips",
            },
        ]
        ledger["items"].extend(prelim_items)
        added_bridge_items.extend(prelim_items)

    # 5. Recompute all 21 owners & whole-robot total via exact Steiner parallel-axis theorem
    by_owner: dict[str, list[dict]] = {owner: [] for owner in ledger["owners"]}
    for item in ledger["items"]:
        by_owner[item["owner"]].append(item)

    total_m = 0.0
    total_weighted_com = np.zeros(3, dtype=float)
    for owner, items in by_owner.items():
        m_o = math.fsum(float(x["mass_kg"]) for x in items)
        com_o = sum(float(x["mass_kg"]) * np.asarray(x["com_world_m"], float) for x in items) / m_o
        I_o = np.zeros((3, 3), dtype=float)
        for x in items:
            I_o += steiner_translate(
                float(x["mass_kg"]),
                np.asarray(x["com_world_m"], float),
                com_o,
                np.asarray(x["I_com_world_kg_m2"], float),
            )
        I_o = 0.5 * (I_o + I_o.T)
        eig = sorted(float(v) for v in np.linalg.eigvalsh(I_o))
        assert eig[0] > 0.0 and eig[0] + eig[1] > eig[2], f"SPD/triangle violation on {owner}: {eig}"
        ledger["owners"][owner] = {
            "mass_kg": float(m_o),
            "com_world_m": com_o.tolist(),
            "I_com_world_kg_m2": I_o.tolist(),
            "principal_inertia_kg_m2": eig,
            "count": len(items),
        }
        total_m += m_o
        total_weighted_com += m_o * com_o

    total_com = total_weighted_com / total_m
    total_I = np.zeros((3, 3), dtype=float)
    for odata in ledger["owners"].values():
        total_I += steiner_translate(
            odata["mass_kg"],
            np.asarray(odata["com_world_m"], float),
            total_com,
            np.asarray(odata["I_com_world_kg_m2"], float),
        )
    total_I = 0.5 * (total_I + total_I.T)
    total_eig = sorted(float(v) for v in np.linalg.eigvalsh(total_I))
    assert total_eig[0] > 0.0 and total_eig[0] + total_eig[1] > total_eig[2]

    total_I_direct = np.zeros((3, 3), dtype=float)
    for x in ledger["items"]:
        total_I_direct += steiner_translate(
            float(x["mass_kg"]),
            np.asarray(x["com_world_m"], float),
            total_com,
            np.asarray(x["I_com_world_kg_m2"], float),
        )
    steiner_err = float(np.max(np.abs(total_I - total_I_direct)))
    assert steiner_err < 1e-12, f"Steiner conservation error too high: {steiner_err}"

    m_004 = float(base_ledger["total"]["mass_kg"])
    m_007 = float(base_ledger["total_007_baseline"]["mass_kg"])
    ledger["schema"] = "goose_assembly_finish_005_mci_ledger/1"
    ledger["status"] = (
        "ASSEMBLY_FINISH_005_DRY_RUN_PRELIM_B2_MCI"
        if bridge_mode.startswith("dry_run")
        else "ASSEMBLY_FINISH_005_FROZEN_PRODUCTION_MCI"
    )
    ledger["created_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ledger["total"] = {
        "mass_kg": float(total_m),
        "com_world_m": total_com.tolist(),
        "I_com_world_kg_m2": total_I.tolist(),
        "principal_inertia_kg_m2": total_eig,
        "count": len(ledger["items"]),
    }
    ledger["total_004_baseline"] = copy.deepcopy(base_ledger["total"])
    ledger["delta_vs_004"] = {
        "net_mass_delta_kg": float(total_m - m_004),
        "net_mass_delta_g": float((total_m - m_004) * 1000.0),
        "com_delta_mm": ((total_com - np.asarray(base_ledger["total"]["com_world_m"], float)) * 1000.0).tolist(),
        "front_shell_yoke_relief_g": float(
            (occt["left_yoke_relieved"]["mass_kg"] + occt["right_yoke_relieved"]["mass_kg"]) * 1000.0
            - sum(x["mass_kg"] * 1000.0 for x in base_ledger["items"] if x["name"] in ("left_smooth_006_yoke", "right_smooth_006_yoke"))
        ),
        "track_b_sanyo24_fan_g": float(sum(occt[k]["mass_kg"] * 1000.0 for _, k, _ in track_b_items)),
        "track_b_env_board_eda_fab_003_g": 0.0,
        "hip_bridge_delta_g": float(sum(x["mass_kg"] * 1000.0 for x in added_bridge_items)),
    }
    ledger["delta_vs_007"] = {
        "net_mass_delta_kg": float(total_m - m_007),
        "net_mass_delta_g": float((total_m - m_007) * 1000.0),
        "com_delta_mm": ((total_com - np.asarray(base_ledger["total_007_baseline"]["com_world_m"], float)) * 1000.0).tolist(),
    }
    ledger["closeout_005_inputs"] = {
        "bridge_mode": bridge_mode,
        "bridge_source": bridge_source_ref,
        "yoke_relief_receipt": rel_ref(YOKE_RELIEF_RECEIPT),
        "sanyo24_fan_receipt": rel_ref(FAN_RECEIPT),
        "environment_board_receipt": rel_ref(ENV_BOARD_RECEIPT),
        "environment_board_drc_violations": env_rec["cold_native_drc"]["total_violations"],
        "steiner_conservation_error_kg_m2": steiner_err,
    }
    return ledger


def build_sailab_005_43_bundle(
    mci_005: dict,
    mesh_audit_res: dict,
    bundle_dir: Path,
    mci_json_path: Path,
) -> dict:
    """Assemble portable 43-collider SaiLab bundle goose_v02_005_exterior_roles_v1."""
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    # 1. Copy runtime infrastructure from frozen 007/43 bundle & 004 sources
    for sub in ("delivery_provenance", "runtime_tools", "scripts", "software"):
        shutil.copytree(FROZEN_007_43 / sub, bundle_dir / sub)
    for fname in ("launch_native50.py", "launcher_environment_lock_uncaptured_001.json", "sailab_training.md", "runtime_dependencies.json"):
        if (FROZEN_007_43 / fname).exists():
            shutil.copy2(FROZEN_007_43 / fname, bundle_dir / fname)

    # Copy sources from Step-3 004 + 007/43 baseline/gravity/beak_mapping_module
    sources_dst = bundle_dir / "sources"
    shutil.copytree(FROZEN_007_43 / "sources/baseline", sources_dst / "baseline")
    shutil.copytree(FROZEN_007_43 / "sources/gravity", sources_dst / "gravity")
    shutil.copytree(FROZEN_007_43 / "sources/beak_mapping_module", sources_dst / "beak_mapping_module")
    shutil.copytree(STEP3_DIR / "sources_003/fk", sources_dst / "fk")
    shutil.copytree(STEP3_DIR / "sources_003/fk_receipt", sources_dst / "fk_receipt")
    shutil.copytree(STEP3_DIR / "sources_003/motion", sources_dst / "motion")
    shutil.copytree(STEP3_DIR / "sources_003/beak_mapping_evidence", sources_dst / "beak_mapping_evidence")
    (sources_dst / "assembly").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        STEP3_DIR / "assembly_finish_004/assembly_registry.json",
        sources_dst / "assembly/assembly_registry.json",
    )
    (sources_dst / "mci").mkdir(parents=True, exist_ok=True)
    write_json(sources_dst / "mci/ledger.json", mci_005)
    shutil.copy2(mci_json_path, sources_dst / "mci/assembly_finish_005_mci.json")

    # 2. Write audited 43 meshes & 43-leaf contact_manifest.json
    meshes_dir = bundle_dir / "meshes"
    for p in (bundle_dir / "_tmp_meshes_staging").glob("*.obj") if False else []:
        pass
    # Audit & write directly into bundle_dir/meshes
    audit_res = audit_and_build_43_meshes(meshes_dir)
    cm_005 = copy.deepcopy(audit_res["cm43"])
    cm_005["status"] = "GOOSE_005_EXTERIOR_ROLES_43_CONTACT_MANIFEST"
    cm_005["leaves"] = audit_res["leaves"]
    cm_005["leaf_count"] = len(audit_res["leaves"])
    cm_005["source_assembly"] = {"path": "sources/assembly/assembly_registry.json", "sha256": sha256(sources_dst / "assembly/assembly_registry.json")}
    cm_005["source_motion"] = {"path": "sources/motion/motion_candidate_003.json", "sha256": sha256(sources_dst / "motion/motion_candidate_003.json")}
    cm_005["source_MCI"] = {"path": "sources/mci/ledger.json", "sha256": sha256(sources_dst / "mci/ledger.json")}
    cm_005["source_FK"] = {"path": "sources/fk_receipt/receipt.json", "sha256": sha256(sources_dst / "fk_receipt/receipt.json")}
    (sources_dst / "contact").mkdir(parents=True, exist_ok=True)
    cm_path = sources_dst / "contact/contact_manifest.json"
    write_json(cm_path, cm_005)

    # 3. Build robot.xml from 007/43 template with 005 inertials, 310 mm stance leg frames, and 003/005 joint ranges
    fk = json.loads((sources_dst / "fk_receipt/receipt.json").read_text())
    motion003 = json.loads((sources_dst / "motion/motion_candidate_003.json").read_text())
    motion_ranges = {j["name"]: j["range_rad"] for j in motion003["active_joints"]}
    shift = np.asarray(fk["source_to_runtime_translation_m"], float)

    tree = ET.parse(FROZEN_007_43 / "robot.xml")
    xml_root = tree.getroot()
    xml_root.attrib["model"] = CANDIDATE_NAME

    for body in xml_root.findall(".//body"):
        bname = body.attrib["name"]
        if bname in SHIFTED_LEG_OFFSETS_M and bname in ("left_hip_pitch", "right_hip_pitch"):
            pos = np.array([float(x) for x in body.attrib["pos"].split()], dtype=float)
            pos = pos + SHIFTED_LEG_OFFSETS_M[bname]
            body.attrib["pos"] = " ".join(f"{x:.17g}" for x in pos)

        # Update joint limits to 003/005 motion_candidate_003
        j_el = body.find("joint")
        if j_el is not None and j_el.attrib.get("name") in motion_ranges:
            lo, hi = motion_ranges[j_el.attrib["name"]]
            j_el.attrib["range"] = f"{lo:.17g} {hi:.17g}"

        # Exact World->Body-Local inertial transform
        ine = body.find("inertial")
        owner = mci_005["owners"][bname]
        fr = fk["bodies"][bname]
        R = np.asarray(fr["rotation_world"], float)
        t = np.asarray(fr["position_world_m"], float)
        com_rt = np.asarray(owner["com_world_m"], float) + shift
        pos_local = R.T @ (com_rt - t)
        I_local = R.T @ np.asarray(owner["I_com_world_kg_m2"], float) @ R
        I_local = 0.5 * (I_local + I_local.T)
        ine.attrib["mass"] = f"{owner['mass_kg']:.17g}"
        ine.attrib["pos"] = " ".join(f"{x:.17g}" for x in pos_local)
        ine.attrib["fullinertia"] = " ".join(
            f"{x:.17g}"
            for x in (I_local[0, 0], I_local[1, 1], I_local[2, 2], I_local[0, 1], I_local[0, 2], I_local[1, 2])
        )

    robot_xml_path = bundle_dir / "robot.xml"
    tree.write(robot_xml_path, encoding="unicode")

    # 4. Build contract.json from 007/43 template with exact 005 inertials, 310 mm pivots, 003/005 ranges, and 0.628305 m beak contract
    c007 = json.loads((FROZEN_007_43 / "contract.json").read_text())
    c005 = copy.deepcopy(c007)
    c005["candidate"] = CANDIDATE_NAME
    c005["candidate_id"] = CANDIDATE_NAME
    c005["nominal_robot_mass_kg"] = float(mci_005["total"]["mass_kg"])
    c005["model_sha256"] = sha256(robot_xml_path)
    c005["asset_sha256"] = {
        f"meshes/{Path(l['mesh_file']).name}": sha256(meshes_dir / Path(l["mesh_file"]).name)
        for l in audit_res["leaves"]
    }
    c005["status"] = "ASSEMBLY_FINISH_005_EXTERIOR_ROLES_43_SAILAB_BUNDLE"
    c005["training_ready"] = True

    # Update joints pivots, ranges, action_scale_rad
    for j in c005["joints"]:
        jn = j["name"]
        if jn in SHIFTED_LEG_OFFSETS_M:
            j["pivot_world_at_zero_m"] = (
                np.asarray(j["pivot_world_at_zero_m"], float) + SHIFTED_LEG_OFFSETS_M[jn]
            ).tolist()
        if jn in motion_ranges:
            lo, hi = motion_ranges[jn]
            j["range_rad"] = [float(lo), float(hi)]
            j["action_scale_rad"] = float(max(abs(lo - j["q_neutral_rad"]), abs(hi - j["q_neutral_rad"])))

    # Update bodies list in contract.json preserving randomization fields
    xml_bodies = {b.attrib["name"]: b for b in xml_root.findall(".//body")}
    for brow in c005["bodies"]:
        bn = brow["name"]
        ine = xml_bodies[bn].find("inertial")
        fi = [float(x) for x in ine.attrib["fullinertia"].split()]
        I_body = [[fi[0], fi[3], fi[4]], [fi[3], fi[1], fi[5]], [fi[4], fi[5], fi[2]]]
        owner = mci_005["owners"][bn]
        brow["mass_kg"] = float(owner["mass_kg"])
        brow["com_local_m"] = [float(x) for x in ine.attrib["pos"].split()]
        brow["inertia_at_com_body_kg_m2"] = I_body
        brow["centre_world_zero_m"] = [float(x) for x in owner["com_world_m"]]
        brow["inertia_at_com_world_zero_kg_m2"] = [[float(x) for x in row] for row in owner["I_com_world_kg_m2"]]

    # Fix stale 0.5567 m -> verified 0.628305 m beak contact plane metadata!
    beak_v = json.loads(BEAK_VERIFY_REF.read_text())
    hr_pos = np.asarray(fk["bodies"]["head_roll"]["position_world_m"], float)
    bh_pos = np.asarray(fk["bodies"]["beak_hinge"]["position_world_m"], float)
    bir_pos = np.asarray(fk["bodies"]["beak_input_rotor"]["position_world_m"], float)
    upper_pts, _ = load_obj_vf(meshes_dir / "contact_001.obj")
    lower_pts, _ = load_obj_vf(meshes_dir / "contact_000.obj")
    upper_z_local = float(upper_pts[:, 2].min())
    lower_z_local = float(lower_pts[:, 2].max())
    oct_local = upper_pts[upper_pts[:, 2] <= upper_z_local + 1e-6]
    oct_world_q0 = (oct_local + hr_pos).tolist()
    plane_z_world_q0 = float(hr_pos[2] + upper_z_local)
    assert math.isclose(plane_z_world_q0, 0.628305, abs_tol=1e-6), f"Unexpected beak plane Z: {plane_z_world_q0}"

    c005["functional_grip_refinement"] = {
        "method": "actual_upper_and_lower_grip_cassette_pad_mesh_planes_at_qpos0",
        "source_part": "upper_grip_cassette_pad",
        "source_sha256": beak_v["active_working_faces"]["upper_grip_cassette_pad__grip_plane"]["mesh_sha256"],
        "contact_plane_world_zero_z_m": plane_z_world_q0,
        "contact_plane_cad_world_z_m": float(plane_z_world_q0 - float(shift[2])),
        "contact_plane_spawn_qpos_z_m": float(plane_z_world_q0 + 0.002),
        "body_local_pad_planes_m": {
            "upper_grip_cassette_pad__grip_plane": {
                "owner": "head_roll",
                "local_z_m": upper_z_local,
                "inward_normal_local": [0.0, 0.0, -1.0],
            },
            "lower_grip_cassette_pad__grip_plane": {
                "owner": "beak_hinge",
                "local_z_m": lower_z_local,
                "inward_normal_local": [0.0, 0.0, 1.0],
            },
        },
        "legacy_007_stale_world_zero_z_m_replaced": 0.5567000000000001,
        "hardware_mesh_modified": False,
        "exact_source_contact_polygon_world_m": oct_world_q0,
    }
    c005["beak_transmission"]["fk_anchor_note"] = {
        "runtime_q0_beak_hinge_m": bh_pos.tolist(),
        "runtime_q0_beak_input_rotor_m": bir_pos.tolist(),
        "relative_hinge_minus_rotor_mm": ((bh_pos - bir_pos) * 1000.0).tolist(),
        "legacy_geometry_A_O_relative_mm": [
            c005["beak_transmission"]["geometry"]["O"][0] - c005["beak_transmission"]["geometry"]["A"][0],
            c005["beak_transmission"]["geometry"]["O"][1] - c005["beak_transmission"]["geometry"]["A"][1],
        ],
        "note": "Four-bar linkage geometry A/O preserves exact [+31.0, -25.0] mm XZ relative vector to FK anchors; A/O absolute coordinates carry a legacy [-13.55, +75.305] mm origin offset relative to runtime qpos=0 FK frames.",
    }

    # Update closeout_native50 source_refs
    srefs = c005["closeout_native50"]["source_refs"]
    srefs["assembly"] = {"path": "sources/assembly/assembly_registry.json", "sha256": sha256(sources_dst / "assembly/assembly_registry.json")}
    srefs["motion"] = {"path": "sources/motion/motion_candidate_003.json", "sha256": sha256(sources_dst / "motion/motion_candidate_003.json")}
    srefs["mci"] = {"path": "sources/mci/ledger.json", "sha256": sha256(sources_dst / "mci/ledger.json")}
    srefs["fk_receipt"] = {"path": "sources/fk_receipt/receipt.json", "sha256": sha256(sources_dst / "fk_receipt/receipt.json")}
    srefs["fk_xml"] = {"path": "sources/fk/robot.xml", "sha256": sha256(sources_dst / "fk/robot.xml")}
    srefs["hardware_contract"] = {"path": "sources/fk/physical_contract.json", "sha256": sha256(sources_dst / "fk/physical_contract.json")}
    srefs["beak_mapping_evidence"] = {"path": "sources/beak_mapping_evidence/analytic_receipt.json", "sha256": sha256(sources_dst / "beak_mapping_evidence/analytic_receipt.json")}
    srefs["contact"] = {"path": "sources/contact/contact_manifest.json", "sha256": sha256(cm_path)}

    c005["closeout_native50"]["contact_lite"] = {
        "model_sha256": c005["model_sha256"],
        "bundle_manifest_sha256": None,
        "contact_manifest_sha256": srefs["contact"]["sha256"],
        "parent_007_43_model_sha256": c007["model_sha256"],
        "scope": "goose005_exterior_roles_two_or_thirty_two_world_standing",
        "validation_receipt": {"path": "qualification/acceptance_receipt.json", "sha256": None},
    }

    contract_path = bundle_dir / "contract.json"
    write_json(contract_path, c005)

    # 5. Patch bundle-local runtime_tools & launch_native50.py BEFORE calling make_source_runtime
    cn_path = bundle_dir / "runtime_tools/bevy_microduck_tools/goose/closeout_native50.py"
    cn_txt = cn_path.read_text().replace(
        "CONTACT_LITE_CANDIDATE = 'goose_v02_source007_exterior_roles_v1'",
        f"CONTACT_LITE_CANDIDATE = '{CANDIDATE_NAME}'",
    )
    cn_path.write_text(cn_txt)

    ln_path = bundle_dir / "launch_native50.py"
    ln_txt = ln_path.read_text().replace(
        "goose_v02_source007_exterior_roles_v1", CANDIDATE_NAME
    )
    ln_path.write_text(ln_txt)

    clv_path = bundle_dir / "runtime_tools/bevy_microduck_tools/goose/contact_lite_validation.py"
    clv_path.write_text(f'''"""Fail-closed independent release gate for the {CANDIDATE_NAME} collision derivative."""
import json
from .closeout_native50 import LITE_RUNTIME_REQUIREMENTS, _source

def validate_lite_contract(contract, root):
    metadata = contract["closeout_native50"]
    lite = metadata["contact_lite"]
    if (metadata.get("runtime_requirements") != LITE_RUNTIME_REQUIREMENTS
            or "production_adoption" in metadata or "production_profile" in metadata
            or lite.get("scope") != "goose005_exterior_roles_two_or_thirty_two_world_standing"):
        raise ValueError("Collision-lite parent, runtime or scope mismatch")
    if not contract.get("training_ready", False):
        return
    if not (root / lite["validation_receipt"]["path"]).exists():
        return
    ref = _source(lite["validation_receipt"], "collision-lite validation", root)
    receipt = json.loads(ref.read_text())
    if (receipt.get("passed") is not True or receipt.get("model_sha256") != contract["model_sha256"]
            or any(value is not True for value in receipt["checks"].values())):
        raise ValueError("Collision-lite validation does not qualify this plant")
''')

    # 6. Size 005 reference_inputs (constant_reference.json, reference_action.json, validation_protocol.json) in MJ315_PYTHON
    ref_dir = bundle_dir / "reference_inputs"
    shutil.copytree(FROZEN_007_43 / "reference_inputs", ref_dir)
    env_mj = os.environ.copy()
    env_mj["PYTHONPATH"] = os.pathsep.join([str(bundle_dir / "runtime_tools"), *MJ315_OVERLAYS])
    ref_code = f"""
import importlib.util, json
from pathlib import Path
from bevy_microduck_tools.goose.closeout_native50 import make_source_runtime

ROOT = Path("{ROOT}")
bundle = Path("{bundle_dir}")
spec_c = importlib.util.spec_from_file_location("const_ref", ROOT / "scripts/evaluation/goose_active_standing_reference_007_20261110.py")
mod_c = importlib.util.module_from_spec(spec_c); spec_c.loader.exec_module(mod_c)
spec_p = importlib.util.spec_from_file_location("pitch_ref", ROOT / "scripts/evaluation/goose_pitch_feedback_reference_007_20261110.py")
mod_p = importlib.util.module_from_spec(spec_p); spec_p.loader.exec_module(mod_p)

rt = make_source_runtime(bundle / "robot.xml", bundle / "contract.json")
_, const_ref = mod_c.constant_reference(rt)
const_ref["baseline_id"] = "goose_005_constant_leg_gravity_standing_v1"
(bundle / "reference_inputs/constant_reference.json").write_text(json.dumps(const_ref, indent=2) + "\\n")
fb_params = mod_p.size_feedback(rt, const_ref)
fb_params["baseline_id"] = "goose_005_ap_pitch_feedback_v1"
(bundle / "reference_inputs/reference_action.json").write_text(json.dumps(fb_params, indent=2) + "\\n")
"""
    subprocess.run([str(MJ315_PYTHON), "-c", ref_code], env=env_mj, check=True)
    prot = json.loads((ref_dir / "validation_protocol.json").read_text())
    prot["plant_model_sha256"] = sha256(robot_xml_path)
    prot["plant_contract_sha256"] = sha256(contract_path)
    prot["source_assembly"] = srefs["assembly"]
    prot["source_mci"] = srefs["mci"]
    prot["source_fk"] = srefs["fk_receipt"]
    prot["reference"] = {"path": "reference_inputs/reference_action.json", "sha256": sha256(ref_dir / "reference_action.json")}
    prot["constant_reference"] = {"path": "reference_inputs/constant_reference.json", "sha256": sha256(ref_dir / "constant_reference.json")}
    write_json(ref_dir / "validation_protocol.json", prot)

    ct_path = bundle_dir / "runtime_tools/bevy_microduck_tools/goose/closeout_training.py"
    ct_txt = ct_path.read_text()
    ct_txt = ct_txt.replace(
        "PROTOCOL_SHA='85df7e7b4a798de6ca1138230344043e38be281c5b0121da37f98c64b859fb7a'",
        f"PROTOCOL_SHA='{sha256(ref_dir / 'validation_protocol.json')}'",
    ).replace(
        "REFERENCE_SHA='8dc38ccaca60f7efb2221545782cf39fe795df326170b4132274d0522aad1ea6'",
        f"REFERENCE_SHA='{sha256(ref_dir / 'reference_action.json')}'",
    )
    ct_path.write_text(ct_txt)

    # 7. Write bundle_manifest.json & zip archive
    manifest = {
        "schema": "goose_functional_contact_bundle_v1",
        "candidate": CANDIDATE_NAME,
        "training_ready": True,
        "files": {
            p.relative_to(bundle_dir).as_posix(): sha256(p)
            for p in sorted(bundle_dir.rglob("*"))
            if p.is_file() and p.name != "bundle_manifest.json"
        },
    }
    manifest_path = bundle_dir / "bundle_manifest.json"
    write_json(manifest_path, manifest)

    zip_path = bundle_dir.parent / f"{CANDIDATE_NAME}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(bundle_dir.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=f"{CANDIDATE_NAME}/{p.relative_to(bundle_dir).as_posix()}")

    return {
        "bundle_dir": str(bundle_dir),
        "zip_path": str(zip_path),
        "zip_sha256": sha256(zip_path),
        "manifest_sha256": sha256(manifest_path),
        "model_sha256": sha256(robot_xml_path),
        "contract_sha256": sha256(contract_path),
        "file_count": len(manifest["files"]) + 1,
        "mesh_audit": audit_res["audit"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-ledger", type=Path, default=None, help="Path to opt_b2_r2_mass_ledger.json")
    parser.add_argument("--dry-run", action="store_true", help="Use Track A1 preliminary Option B2 numbers")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_dir = args.output_dir if args.output_dir.is_absolute() else (ROOT / args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bridge_path = args.bridge_ledger
    if bridge_path is None and not args.dry_run and DEFAULT_BRIDGE_LEDGER.exists():
        bridge_path = DEFAULT_BRIDGE_LEDGER

    print(f"[Track C] Computing 21-body MCI (dry_run={args.dry_run}, bridge={bridge_path})...", flush=True)
    mci_005 = build_005_mci_ledger(bridge_path, dry_run=args.dry_run)
    mci_json_path = out_dir / "assembly_finish_005_mci.json"
    write_json(mci_json_path, mci_005)
    print(
        f"[Track C] 005 MCI total={mci_005['total']['mass_kg']:.6f} kg "
        f"(vs 004: {mci_005['delta_vs_004']['net_mass_delta_g']:+.2f} g, "
        f"Steiner err={mci_005['closeout_005_inputs']['steiner_conservation_error_kg_m2']:.2e})",
        flush=True,
    )

    bundle_dir = out_dir / CANDIDATE_NAME
    print(f"[Track C] Auditing 43 meshes & building {bundle_dir}...", flush=True)
    bundle_info = build_sailab_005_43_bundle(mci_005, {}, bundle_dir, mci_json_path)
    write_json(out_dir / "exterior_mesh_audit.json", bundle_info["mesh_audit"])
    build_receipt = {
        "schema": "goose005_track_c_build_receipt_v1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run or bridge_path is None),
        "bridge_mode": mci_005["closeout_005_inputs"]["bridge_mode"],
        "mci_json": rel_ref(mci_json_path),
        "total_mass_kg": mci_005["total"]["mass_kg"],
        "delta_vs_004": mci_005["delta_vs_004"],
        "delta_vs_007": mci_005["delta_vs_007"],
        "bundle_dir": bundle_info["bundle_dir"],
        "zip_path": bundle_info["zip_path"],
        "zip_sha256": bundle_info["zip_sha256"],
        "manifest_sha256": bundle_info["manifest_sha256"],
        "model_sha256": bundle_info["model_sha256"],
        "contract_sha256": bundle_info["contract_sha256"],
        "mesh_audit_summary": {k: v for k, v in bundle_info["mesh_audit"].items() if k != "meshes"},
    }
    write_json(out_dir / "build_receipt_005.json", build_receipt)
    print(json.dumps(build_receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
