#!/usr/bin/env python3
"""Reject native-material and module-envelope conflicts in Gorilla Internal B.

Positive volume is a penetration; touching surfaces are not. Catalog envelopes
are spatial reservations, not solid material or qualified mounts. Sampled poses
and cylinder-length paths do not establish continuous motion clearance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def posed_cylinder(part, cylinders, spec, builder):
    metadata = part["internal_structure_b"]
    side, name = metadata["side"], metadata["cylinder"]
    row = next(r for r in cylinders[side] if r["id"] == side + "_" + name)
    a, b = np.array(row["base_world_m"]), np.array(row["output_world_m"])
    direction = (b - a) / np.linalg.norm(b - a)
    params = spec["compact_cylinder_probe"][name]
    rear = a + direction * spec["compact_cylinder_probe"]["mount_eye_allowance_m"] / 2
    front = rear + direction * params["body_length_m"]
    component = metadata["component"]
    if component == "body":
        return builder.solid_along(rear, front, params["body_width_m"], params["body_width_m"])
    if component == "rear_eye_reserve":
        return builder.solid_along(a, rear, .060, .060)
    tip = b - direction * .025
    if component == "output_eye_reserve":
        return builder.solid_along(tip, b, .060, .060)
    shape = trimesh.creation.cylinder(radius=params["rod_m"] / 2, height=np.linalg.norm(tip - front), sections=64)
    shape.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction))
    shape.apply_translation((front + tip) / 2)
    return shape


def pair_category(a, b):
    ra, rb = a["role"], b["role"]
    frame = "net_primary_structure_candidate"
    bearing = "bearing_reference_envelope"
    armor = {"armor_surface", "armor_cover"}
    probes = {"complete_module_packaging_probe", "compact_cylinder_packaging_probe"}
    if ra == rb == frame:
        return "different_body_material" if a["body"] != b["body"] else None
    if frame in (ra, rb) and bearing in (ra, rb):
        return "frame_bearing_reservation"
    if frame in (ra, rb) and (ra in armor or rb in armor):
        return "frame_armor"
    if (ra in probes or rb in probes) and (ra in probes or ra in armor or ra in (frame, bearing)) and (rb in probes or rb in armor or rb in (frame, bearing)):
        # A cylinder's body/rod/eye reservations form one assembly. Their mutual
        # boundaries have no independent clearance requirement in this screen.
        ma, mb = a.get("internal_structure_b", {}), b.get("internal_structure_b", {})
        if ra == rb == "compact_cylinder_packaging_probe" and (ma["side"], ma["cylinder"]) == (mb["side"], mb["cylinder"]):
            return None
        return "module_reservation_conflict"
    return None


def screen(parts, meshes, volume_tolerance):
    hits, uncertainties = [], []
    candidates = 0
    for (a, ma), (b, mb) in itertools.combinations(zip(parts, meshes), 2):
        category = pair_category(a, b)
        if category is None:
            continue
        overlap = np.minimum(ma.bounds[1], mb.bounds[1]) - np.maximum(ma.bounds[0], mb.bounds[0])
        if np.any(overlap <= 1e-8):
            continue
        candidates += 1
        if not (ma.is_volume and mb.is_volume):
            uncertainties.append({"parts": [a["name"], b["name"]], "reason": "Non-volume native input", "category": category})
            continue
        try:
            intersection = trimesh.boolean.intersection([ma, mb], engine="manifold")
            volume = max(0., float(intersection.volume)) if len(intersection.faces) else 0.
            if not np.isfinite(volume):
                raise ValueError("Nonfinite intersection volume")
        except (ValueError, RuntimeError) as error:
            uncertainties.append({"parts": [a["name"], b["name"]], "reason": str(error), "category": category})
            continue
        if volume > volume_tolerance:
            hits.append({"parts": [a["name"], b["name"]], "category": category, "positive_overlap_volume_m3": volume})
    return {"aabb_candidate_pair_count": candidates, "positive_volume_intersections": sorted(hits, key=lambda r: r["positive_overlap_volume_m3"], reverse=True),
            "unresolved_pairs": uncertainties, "accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=ROBOT / "cad/source/internal_structure_b_scene.json")
    parser.add_argument("--statics", type=Path, default=ROBOT / "evidence/internal_structure_b_statics.json")
    parser.add_argument("--output", type=Path, default=ROBOT / "evidence/internal_structure_b_space.json")
    args = parser.parse_args()
    evaluator_path = ROOT / "scripts/evaluation/evaluate_gorilla_internal_structure.py"
    builder_path = ROOT / "scripts/models/build_gorilla_internal_structure.py"
    evaluator = load_module("gorilla_b_eval", evaluator_path)
    builder = load_module("gorilla_b_builder", builder_path)
    scene, statics = json.loads(args.scene.read_text()), json.loads(args.statics.read_text())
    spec_path = ROOT / scene["spec_path"]
    spec = json.loads(spec_path.read_text())
    paths = {"scene": args.scene, "statics": args.statics, "spec": spec_path, "builder": builder_path,
             "evaluator": evaluator_path, "checker": Path(__file__), "base_scene": ROOT / scene["base_scene"],
             "geometry_spec": ROOT / spec["geometry_spec"], "budget_spec": ROOT / spec["budget_spec"],
             "budget_layout": ROOT / spec["budget_layout"]}
    hashes = {key: sha(path) for key, path in paths.items()}
    for field in ("scene", "spec", "evaluator", "geometry_spec", "budget_spec", "budget_layout"):
        if statics[field + "_sha256"] != hashes[field]:
            raise ValueError("Stale statics: " + field)
    for field in ("spec", "builder", "base_scene", "budget_layout"):
        if scene[field + "_sha256"] != hashes[field]:
            raise ValueError("Stale geometry: " + field)
    base = json.loads(paths["base_scene"].read_text())
    by_name = {p["name"]: p for p in scene["parts"]}
    exact_names = [p["name"] for p in base["parts"] if p["role"] in ("armor_surface", "armor_cover") or p["name"].endswith(("_composite_forepad", "_composite_heel_pad"))]
    if any(by_name[name] != next(p for p in base["parts"] if p["name"] == name) for name in exact_names):
        raise ValueError("Original armor or pads changed")
    selected_roles = {"net_primary_structure_candidate", "bearing_reference_envelope", "armor_surface", "armor_cover", "complete_module_packaging_probe", "compact_cylinder_packaging_probe"}
    parts = [p for p in scene["parts"] if p["role"] in selected_roles]
    base_meshes = [evaluator.mesh(p) for p in parts]
    material_checks = []
    for part, shape in zip(parts, base_meshes):
        if part["role"] != "net_primary_structure_candidate":
            continue
        eigenvalues = np.linalg.eigvalsh(shape.moment_inertia * spec["material"]["density_kg_m3"])
        material_checks.append({"part": part["name"], "volume_m3": float(shape.volume), "positive_material_components": part["internal_structure_b"]["connected_material_components"],
                                "full_inertia_eigenvalues_kg_m2": eigenvalues.tolist(), "valid_volume_and_inertia": bool(shape.is_volume and np.all(eigenvalues > 0))})
    reports = []
    for pose in statics["poses"]:
        matrices = {body: np.array(matrix) for body, matrix in pose["body_rest_world_to_pose_transforms"].items()}
        meshes = []
        for part, shape in zip(parts, base_meshes):
            if part["role"] == "compact_cylinder_packaging_probe":
                posed = posed_cylinder(part, pose["cylinders"], spec, builder)
            else:
                posed = shape.copy()
                body = evaluator.module_body(part["internal_structure_b"]["A_module"]) if part["role"] == "complete_module_packaging_probe" else evaluator.canonical(part["body"])
                posed.apply_transform(matrices[body])
            meshes.append(posed)
        report = screen(parts, meshes, 1e-9)
        report["pose"] = pose["id"]
        reports.append(report)
        print(pose["id"], "positive intersections", len(report["positive_volume_intersections"]), "unknown", len(report["unresolved_pairs"]), flush=True)
    points = json.loads(paths["geometry_spec"].read_text())["points_world_m"]
    lengths = []
    neutral = spec["candidate_pose_angles_deg"]["neutral"]
    for name, target in spec["candidate_pose_angles_deg"].items():
        samples = []
        for fraction in np.linspace(0, 1, 21):
            angles = {key: neutral[key] + fraction * (target[key] - neutral[key]) for key in neutral}
            rows, jacobian = evaluator.cylinder_probe(spec, points, angles, "left")
            samples.append({"fraction": float(fraction), "lengths_m": [r["length_m"] for r in rows],
                            "all_strokes_within_hypothesis": all(r["stroke_within_conditional_range"] for r in rows),
                            "minimum_jacobian_singular_value_m_per_rad": float(np.linalg.svd(jacobian, compute_uv=False).min())})
        lengths.append({"target_pose": name, "samples": samples, "scope": "21 kinematic samples only, not swept geometry or motion acceptance."})
    for key, path in paths.items():
        if sha(path) != hashes[key]:
            raise ValueError("Inputs changed during screen: " + key)
    result = {"schema": "gorilla_internal_structure_space_v1", "robot_id": "gorilla_v0_1", "input_paths": {k: str(v.relative_to(ROOT)) for k, v in paths.items()},
              "input_hashes": hashes, "original_armor_and_pad_rows_exact": len(exact_names), "net_material_checks": material_checks,
              "positive_volume_tolerance_m3": 1e-9, "poses": reports, "sampled_length_paths": lengths,
              "geometry_accepted": False, "physics_accepted": False, "stable_physical_contract": False,
              "scope": "Native closed-material positive-volume rejection; finite catalog/custom envelopes with conditional owner transforms. Original armor exact. Original decorative joint proxies excluded, new modules never hidden. Body-union connectivity is not joint, weld, pad fastening or strength proof. Full axes, brackets, hoses, seals, continuous sweep and thermal interfaces remain open."}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(str(args.output))


if __name__ == "__main__":
    main()
