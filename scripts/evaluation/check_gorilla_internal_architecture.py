#!/usr/bin/env python3
"""Screen declared Gorilla module space against native C15 material geometry.

Geometry results are rejection/unknown evidence. Primitive module envelopes and
aggregate reserves do not establish a manufacturable assembly or accepted mass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from check_gorilla_composite_foot import relation
from check_gorilla_internal_layout import box, cylinder, pair_geometry
from sai_agent.structural_statics import normal_contacts

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape(row):
    if row["geometry"] == "box":
        if row.get("rotation_euler_rad", [0, 0, 0]) != [0, 0, 0]:
            raise ValueError("Rotated box needs an oriented-envelope checker: " + row["id"])
        return box(row["id"], row["center_world_m"], row["dimensions_m"])
    return cylinder(row["id"], row["center_world_m"], row["axis_world"], row["diameter_m"], row["length_m"])


def mesh_row(row):
    if row["geometry"] == "box":
        mesh = trimesh.creation.box(extents=row["dimensions_m"])
    else:
        # 64-side display-equivalent material probe is inscribed in the exact
        # round envelope. Positive hits reject; no-hit is never fit acceptance.
        mesh = trimesh.creation.cylinder(radius=row["diameter_m"] / 2, height=row["length_m"], sections=64)
        mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], row["axis_world"]))
    mesh.apply_translation(row["center_world_m"])
    return {"name": row["id"], "vertices_world_m": mesh.vertices.tolist(), "faces": mesh.faces.tolist()}


def native_mesh(part):
    faces = [[f[0], f[i], f[i + 1]] for f in part["faces"] for i in range(1, len(f) - 1)]
    return trimesh.Trimesh(part["vertices_world_m"], faces, process=False)


def envelope_inertia(row, mass):
    if row["geometry"] == "box":
        x, y, z = row["dimensions_m"]
        return np.diag([y*y + z*z, x*x + z*z, x*x + y*y]) * mass / 12
    radius, length = row["diameter_m"] / 2, row["length_m"]
    axis = np.asarray(row["axis_world"])
    axial = np.outer(axis, axis)
    return mass * ((radius*radius / 4 + length*length / 12) * (np.eye(3) - axial) + radius*radius / 2 * axial)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, default=ROBOT / "configs/internal_architecture_a_layout.json")
    parser.add_argument("--output", type=Path, default=ROBOT / "evidence/internal_architecture_a_space.json")
    args = parser.parse_args()
    layout = json.loads(args.layout.read_text())
    scene_path, spec_path = ROOT / layout["base_scene"], ROOT / layout["budget_spec"]
    if sha(scene_path) != layout["base_scene_sha256"] or sha(spec_path) != layout["budget_spec_sha256"]:
        raise ValueError("Stale source/spec binding")
    scene, spec = json.loads(scene_path.read_text()), json.loads(spec_path.read_text())
    module_rows = [r for r in layout["modules"] if r["family"]]
    materials = [p for p in scene["parts"] if p["role"] in (
        "armor_surface", "armor_cover", "primary_structure_candidate", "primary_structure_socket_candidate")]
    material_bounds = {p["name"]: (np.min(p["vertices_world_m"], axis=0), np.max(p["vertices_world_m"], axis=0)) for p in materials}
    native_hits, native_tests = [], 0
    for row in module_rows:
        if row["role"] != "complete_module_envelope":
            continue
        probe = mesh_row(row)
        vertices = np.asarray(probe["vertices_world_m"])
        low, high = vertices.min(0), vertices.max(0)
        for part in materials:
            p_low, p_high = material_bounds[part["name"]]
            if np.any(high < p_low - 1e-8) or np.any(p_high < low - 1e-8):
                continue
            native_tests += 1
            result = relation(probe, part)
            if result["surface_touch_or_crossing_triangle_pairs"] or result["strict_material_vertex_containment_count"]:
                result.update(route=row["route"], module=row["id"], native_role=part["role"],
                              interpretation="Native material contact/crossing or strict containment. No expected interface has been declared; reject until classified and redesigned.")
                native_hits.append(result)
        print(row["id"], "native hits", sum(r["module"] == row["id"] for r in native_hits), flush=True)

    # Retain native finite-wall material centroids and complete inertia tensors.
    # Overlapping stock is deliberately not silently removed from this budget.
    distributed_rows = []
    for part in materials:
        mesh = native_mesh(part)
        density = spec["stock_density_kg_m3"] if part["role"].startswith("primary_structure") else spec["armor_density_range_kg_m3"][1]
        distributed_rows.append((float(mesh.volume * density), mesh.center_mass, mesh.moment_inertia * density))
    contacts = []
    for part in scene["parts"]:
        if part["name"].endswith(("_composite_forepad", "_composite_heel_pad")):
            vertices = np.asarray(part["vertices_world_m"])
            minimum = vertices[:, 2].min()
            if abs(minimum) > 1e-8:
                raise ValueError("Source sole is not on z=0: " + part["name"])
            contacts.extend(vertices[abs(vertices[:, 2] - minimum) < 1e-8].tolist())
    if not contacts:
        raise ValueError("No real segmented-foot contact candidates")

    routes = {}
    for route in spec["routes"]:
        rows = [r for r in module_rows if r["route"] in ("common", route)]
        physical = [r for r in rows if r["role"] == "complete_module_envelope"]
        exclusive_pairs = []
        for i, a in enumerate(physical):
            for b in physical[i + 1:]:
                result = pair_geometry(shape(a), shape(b), .010)
                if result["classification"] != "separation_certified" or result["distance_lower_bound_m"] < .010:
                    exclusive_pairs.append({"modules": [a["id"], b["id"]], **result})
        proxy_rows = [(r["mass_range_kg"][1], np.asarray(r["center_world_m"]), envelope_inertia(r, r["mass_range_kg"][1])) for r in rows]
        distribution = [*distributed_rows, *proxy_rows]
        mass = sum(r[0] for r in distribution)
        center = sum(m * p for m, p, _ in distribution) / mass
        inertia = np.zeros((3, 3))
        for m, p, tensor in distribution:
            delta = p - center
            inertia += tensor + m * ((delta @ delta) * np.eye(3) - np.outer(delta, delta))
        gravity_load = {"position_world_m": center.tolist(), "force_world_N": [0, 0, -mass * spec["gravity_m_s2"]]}
        payload = {"position_world_m": [.45, 0, 1.20], "force_world_N": [0, 0, -100 * spec["gravity_m_s2"]]}
        cases = {}
        for case, vertices in (("double_support", contacts), ("left_only_without_COM_shift", [v for v in contacts if v[1] > 0]),
                               ("right_only_without_COM_shift", [v for v in contacts if v[1] < 0])):
            cases[case] = normal_contacts(vertices, [gravity_load, payload])
        routes[route] = {"placed_budget_rows": len(rows), "gross_nominal_mass_kg": mass,
            "gross_nominal_COM_world_m": center.tolist(), "gross_uniform_envelope_inertia_at_COM_kg_m2": inertia.tolist(),
            "inertia_eigenvalues_kg_m2": np.linalg.eigvalsh(inertia).tolist(),
            "inertia_scope": "Coarse aggregate sensitivity: exact conditional native material tensors plus uniform module/reserve envelopes. No physical per-body inertia contract, actual distributed reserve inertia or net stock overlap subtraction.",
            "native_material_hits": [r for r in native_hits if r["route"] in ("common", route)],
            "exclusive_module_overlap_or_under_10mm_clearance": exclusive_pairs,
            "gravity_contact_screen_with_100kg_at_x045_m": cases,
            "contact_scope": "Unilateral normal-force balance at actual neutral pad vertices only. C15 internal support/lock path is still open; this cannot approve supported motion, sole pressure, friction or stability.",
            "geometry_accepted": False, "physics_accepted": False}
        print(route, "exclusive conflicts", len(exclusive_pairs), "native hits", len(routes[route]["native_material_hits"]), flush=True)
    report = {"schema": "gorilla_internal_architecture_space_v1", "robot_id": "gorilla_v0_1",
        "layout_path": str(args.layout.relative_to(ROOT)), "layout_sha256": sha(args.layout), "base_scene_sha256": sha(scene_path),
        "budget_spec_sha256": sha(spec_path), "checker_sha256": sha(Path(__file__)),
        "helper_sha256": {name: sha(Path(__file__).with_name(name)) for name in ("check_gorilla_composite_foot.py", "check_gorilla_internal_layout.py")},
        "native_material_AABB_prefiltered_pair_tests": native_tests, "routes": routes,
        "screen_completed": True, "geometry_accepted": False, "physics_accepted": False,
        "scope": "Native un-bevelled C15 triangle SAT/material-vertex containment versus closed 64-sided inscribed cylinder/box module proxies; positive hits reject. Exact convex envelope overlap/clearance bounds for complete module pairs. No hit does not prove continuous clearance or shell containment; no-bevel, aggregate reserves, service path, cylinder stroke and articulation remain unresolved. Original exterior geometry unchanged."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "physics_accepted": False}))


if __name__ == "__main__":
    main()
