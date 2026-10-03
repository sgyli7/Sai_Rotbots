#!/usr/bin/env python3
"""Verify C diagnostic source/export identities; never approve its assembly."""
from __future__ import annotations

import argparse
import hashlib
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
    parser.add_argument("--output", type=Path, default=ROBOT / "evidence/internal_structure_c_resource_check.json")
    args = parser.parse_args()
    scene_path = ROBOT / "cad/source/internal_structure_c_scene.json"
    screen_path = ROBOT / "evidence/internal_structure_c_screen.json"
    space_path = ROBOT / "evidence/internal_structure_c_space.json"
    render_path = ROBOT / "cad/exports/internal_structure_c/internal_structure_c_render_manifest.json"
    scene, screen, space, render = [json.loads(p.read_text()) for p in (scene_path, screen_path, space_path, render_path)]
    source_hash = sha(scene_path)
    if any(r["scene_sha256"] != source_hash for r in (screen, space, render)):
        raise ValueError("Candidate source mismatch")
    evaluator_path = ROOT / "scripts/evaluation/evaluate_gorilla_internal_co_design.py"
    if any(r["evaluator_sha256"] != sha(evaluator_path) for r in (screen, space)):
        raise ValueError("Evaluator binding changed")
    file_checks = []
    for row in [*render["images"], *render["exports"], *render["manifests"].values()]:
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("Changed render/export: " + row["path"])
        file_checks.append(row)
    for name, expected in render["input_hashes"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Changed render input: " + name)
    source_manifest = json.loads((ROOT / render["manifests"]["source"]["path"]).read_text())
    if source_manifest["retained_mesh_identity_before"] != source_manifest["retained_mesh_identity_after"]:
        raise ValueError("Original meshes/materials/transforms changed")
    glb_path = next(ROOT / r["path"] for r in render["exports"] if r["path"].endswith(".glb"))
    exported = trimesh.load(glb_path, force="scene", process=False)
    if set(exported.graph.nodes_geometry) != {p["name"] for p in scene["parts"]}:
        raise ValueError("Exported part-name set differs")
    added = set(source_manifest["added_native_part_names"])
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
    steel_mass = sum(r["mass_range_kg"][1] for r in screen["mass_rows"] if r["id"].endswith("_net_frame"))
    if abs(steel_mass - scene["steel_net_frame_mass_kg"]) > 1e-8:
        raise ValueError("Net steel ledger does not match geometry")
    c15 = json.loads((ROOT / "experiments/gorilla_v0_1/appearance_c_round_fifteen/snapshot_manifest.json").read_text())
    for row in c15["copies"]:
        if any(sha(ROOT / row[k]) != row["sha256"] for k in ("original_path", "snapshot_path")):
            raise ValueError("Frozen C15 or original input changed")
    frozen_b = json.loads((ROOT / "experiments/gorilla_v0_1/internal_structure_b/snapshot_manifest.json").read_text())
    frozen_checks = []
    for row in frozen_b["canonical_frozen_files"]:
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("Frozen B canonical changed: " + row["path"])
        frozen_checks.append(row["path"])
    for key in ("source_byte_copies", "independent_review_byte_copies"):
        for row in frozen_b[key]:
            if sha(ROOT / row["snapshot_path"]) != row["sha256"]:
                raise ValueError("Frozen B snapshot changed: " + row["snapshot_path"])
            frozen_checks.append(row["snapshot_path"])
            if key == "source_byte_copies":
                if sha(ROOT / row["original_path"]) != row["sha256"]:
                    raise ValueError("Frozen B script changed: " + row["original_path"])
                frozen_checks.append(row["original_path"])
    frozen_checks = sorted(set(frozen_checks))
    report = {"schema": "gorilla_internal_co_design_resource_check_v1", "robot_id": "gorilla_v0_1",
              "scene_sha256": source_hash, "screen_sha256": sha(screen_path), "space_sha256": sha(space_path),
              "render_manifest_sha256": sha(render_path), "checker_sha256": sha(Path(__file__)),
              "file_checks": file_checks, "source_part_count": len(scene["parts"]), "export_part_count": len(exported.graph.nodes_geometry),
              "retained_geometry_transform_material_preserved": True, "new_native_export_checks": export_checks,
              "net_steel_mass_kg": steel_mass, "c15_frozen_and_original_hash_checks": len(c15["copies"]),
              "b_frozen_hash_checks": frozen_checks, "resource_checks_passed": True,
              "geometry_accepted": False, "physics_accepted": False, "stable_physical_contract": False,
              "scope": "Source/export identities and finite net-material ledger only. Rejected geometry, disconnected load paths and incomplete electromechanical assemblies remain rejected."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "new_native_meshes": len(export_checks), "part_count": len(scene["parts"]), "frozen_b_checks": len(frozen_checks)}))


if __name__ == "__main__":
    main()
