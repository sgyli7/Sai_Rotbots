#!/usr/bin/env python3
"""Check B source/export identity and independent endpoint virtual work.

These checks validate the recorded candidate, including its rejected layout;
they cannot approve contact, manufacturing, strength or drive capability.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
import trimesh

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROBOT / "evidence/internal_structure_b_resource_check.json")
    args = parser.parse_args()
    scene_path = ROBOT / "cad/source/internal_structure_b_scene.json"
    statics_path = ROBOT / "evidence/internal_structure_b_statics.json"
    render_path = ROBOT / "cad/exports/internal_structure_b/internal_structure_b_render_manifest.json"
    scene, statics, render = [json.loads(p.read_text()) for p in (scene_path, statics_path, render_path)]
    source_hash = sha(scene_path)
    if source_hash != statics["scene_sha256"] or source_hash != render["scene_sha256"]:
        raise ValueError("Candidate source mismatch")
    file_checks = []
    for row in [*render["images"], *render["exports"], *render["manifests"].values()]:
        path = ROOT / row["path"]
        if sha(path) != row["sha256"]:
            raise ValueError("Changed render/export: " + row["path"])
        file_checks.append(row)
    for name, expected in render["input_hashes"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Changed render input: " + name)
    source_manifest = json.loads((ROOT / render["manifests"]["source"]["path"]).read_text())
    if source_manifest["retained_mesh_identity_before"] != source_manifest["retained_mesh_identity_after"]:
        raise ValueError("Original meshes/materials changed")
    glb_path = next(ROOT / r["path"] for r in render["exports"] if r["path"].endswith(".glb"))
    exported = trimesh.load(glb_path, force="scene", process=False)
    if set(exported.graph.nodes_geometry) != {p["name"] for p in scene["parts"]}:
        raise ValueError("Exported part-name set differs")
    added = set(source_manifest["added_native_part_names"])
    # Standard glTF +Y-up -> source Blender +Z-up coordinates.
    to_source = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    export_checks = []
    for part in scene["parts"]:
        if part["name"] not in added:
            continue
        transform, geometry_name = exported.graph[part["name"]]
        shape = exported.geometry[geometry_name].copy()
        shape.apply_transform(to_source @ transform)
        source_vertices = np.asarray(part["vertices_world_m"])
        distances = np.r_[cKDTree(shape.vertices).query(source_vertices)[0], cKDTree(source_vertices).query(shape.vertices)[0]]
        error = float(distances.max())
        if error > 3e-7:
            raise ValueError("Exported native vertices differ: " + part["name"])
        export_checks.append({"part": part["name"], "maximum_bidirectional_vertex_error_m": error})
    evaluator_path = ROOT / "scripts/evaluation/evaluate_gorilla_internal_structure.py"
    module_spec = importlib.util.spec_from_file_location("gorilla_b_resource_eval", evaluator_path)
    evaluator = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(evaluator)
    spec = json.loads((ROOT / scene["spec_path"]).read_text())
    points = json.loads((ROOT / spec["geometry_spec"]).read_text())["points_world_m"]
    jacobian_checks = []
    for pose in statics["poses"]:
        matrices = {body: np.asarray(value) for body, value in pose["body_rest_world_to_pose_transforms"].items()}
        for side in ("left", "right"):
            analytic = np.zeros((2, 2))
            for i, name in enumerate(("fold", "ankle")):
                cylinder = pose["cylinders"][side][i]
                output = np.array(cylinder["output_world_m"])
                direction = np.array(cylinder["direction_base_to_output_world"])
                fold_origin = evaluator.transformed(matrices[side + "_middle_shank"], points[side + "_fold"])
                analytic[i, 0] = np.cross(output - fold_origin, direction)[1]
                if name == "ankle":
                    ankle_origin = evaluator.transformed(matrices[side + "_distal_shank"], points[side + "_ankle"])
                    analytic[i, 1] = np.cross(output - ankle_origin, direction)[1]
            recorded = np.asarray(pose["jacobian_m_per_rad"][side])
            error = float(abs(recorded - analytic).max())
            if error > 1e-8:
                raise ValueError("Virtual-work Jacobian disagrees with actual endpoint torque")
            jacobian_checks.append({"pose": pose["id"], "side": side, "maximum_analytic_endpoint_vs_finite_difference_error_m_per_rad": error})
    steel_mass = sum(r["mass_range_kg"][1] for r in statics["material_mass_rows"] if r["id"].endswith("_net_frame"))
    if abs(steel_mass - scene["steel_net_frame_mass_kg"]) > 1e-8:
        raise ValueError("Net steel ledger does not match geometry")
    c15_path = ROOT / "experiments/gorilla_v0_1/appearance_c_round_fifteen/snapshot_manifest.json"
    c15 = json.loads(c15_path.read_text())
    for row in c15["copies"]:
        if sha(ROOT / row["snapshot_path"]) != row["sha256"] or sha(ROOT / row["original_path"]) != row["sha256"]:
            raise ValueError("Frozen C15 or original input changed")
    report = {"schema": "gorilla_internal_structure_resource_check_v1", "robot_id": "gorilla_v0_1",
              "scene_sha256": source_hash, "statics_sha256": sha(statics_path), "render_manifest_sha256": sha(render_path),
              "checker_sha256": sha(Path(__file__)), "file_checks": file_checks,
              "source_part_count": len(scene["parts"]), "export_part_count": len(exported.graph.nodes_geometry),
              "retained_geometry_transform_material_preserved": True, "new_native_export_checks": export_checks,
              "independent_analytic_virtual_work_checks": jacobian_checks, "net_steel_mass_kg": steel_mass,
              "c15_frozen_and_original_hash_checks": len(c15["copies"]), "resource_checks_passed": True,
              "geometry_accepted": False, "physics_accepted": False, "stable_physical_contract": False,
              "scope": "Source/export identities and independent actual endpoint torque/Jacobian consistency. Rejected assembly remains rejected; no dynamic, thermal, mounting or hardware qualification."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "new_native_meshes": len(export_checks), "part_count": len(scene["parts"]), "jacobian_checks": len(jacobian_checks)}))


if __name__ == "__main__":
    main()
