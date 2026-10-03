#!/usr/bin/env python3
"""C macro mass/contact/torque/space diagnostic, explicitly not acceptance."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.optimize import linprog

from sai_agent.structural_statics import contact_extreme_allocations, normal_contacts, resultant

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
HELPER = ROOT / "scripts/evaluation/evaluate_gorilla_internal_structure.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mesh(p):
    faces = [[f[0], f[i], f[i + 1]] for f in p["faces"] for i in range(1, len(f) - 1)]
    return trimesh.Trimesh(p["vertices_world_m"], faces, process=False)


def bounds_overlap(a, b):
    return np.all(a.bounds[0] < b.bounds[1]) and np.all(b.bounds[0] < a.bounds[1])


def contact_with_drive_hypotheses(vertices, loads, joint_models, speed, eta, motor_factor):
    """Minimize peak mapped-capacity use over finite unilateral reactions.

    A large unconstrained contact extreme is not proof that all feasible force
    allocations exceed the actuators. This LP only tests the stated optimistic
    gravity/normal/contact/mapped-output model, never the actual machine.
    """
    force, moment = resultant(loads, np.zeros(3))
    target = np.array([-force[2], moment[1], -moment[0]])
    equilibrium = np.vstack([np.ones(len(vertices)), vertices[:, 0], vertices[:, 1]])
    bounds, limits = [], []
    for row in joint_models:
        j = row["joint"]
        reference = j["catalogue_motor_Ts_Nm"] if speed == 0 else j["catalogue_motor_Tc_Nm"]
        cap = min(j["catalogue_gear_rated_Nm"], eta * j["ratio"] * motor_factor * reference)
        k = np.asarray(row["contact_torque_coefficients_m"])
        c = row["gravity_torque_Nm"]
        bounds.extend([np.r_[k / cap, -1.], np.r_[-k / cap, -1.]])
        limits.extend([-c / cap, c / cap])
    objective = np.r_[np.zeros(len(vertices)), 1.]
    eq = np.column_stack([equilibrium, np.zeros(3)])
    result = linprog(objective, A_ub=np.asarray(bounds), b_ub=np.asarray(limits), A_eq=eq, b_eq=target,
                     bounds=[(0, None)] * (len(vertices) + 1), method="highs")
    report = {"speed_rad_s": speed, "efficiency_hypothesis": eta, "motor_reference_factor": motor_factor,
              "solver_success": bool(result.success), "solver_message": result.message,
              "feasible_under_contact_and_mapped_torque_hypotheses": False, "physics_accepted": False,
              "scope": "Finite normal-only gravity model; eight sagittal torque comparisons only. Static efficiency/capability is an algebraic hypothesis; full T-n/bus/thermal/holding/bearings/other axes/connectivity/friction/dynamics unknown."}
    if result.success:
        reactions, peak = result.x[:-1], float(result.x[-1])
        equilibrium_error = float(abs(equilibrium @ reactions - target).max())
        violation = float(max(0., (np.asarray(bounds) @ result.x - np.asarray(limits)).max()))
        if equilibrium_error > 1e-5 or violation > 1e-7 or reactions.min() < -1e-8:
            raise ValueError("Contact/drive LP primal constraints do not match recorded solution")
        report.update({"minimum_peak_mapped_capacity_fraction": peak,
                       "feasible_under_contact_and_mapped_torque_hypotheses": peak <= 1 + 1e-7,
                       "normal_reactions_at_actual_vertices_N": reactions.tolist(),
                       "maximum_equilibrium_residual_N_or_Nm": equilibrium_error,
                       "maximum_normalized_inequality_violation": violation})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=ROBOT / "cad/source/internal_structure_c_scene.json")
    parser.add_argument("--output", type=Path, default=ROBOT / "evidence/internal_structure_c_screen.json")
    parser.add_argument("--space-output", type=Path, default=ROBOT / "evidence/internal_structure_c_space.json")
    parser.add_argument("--no-space", action="store_true")
    args = parser.parse_args()
    definition = importlib.util.spec_from_file_location("gorilla_b_pose_math", HELPER)
    h = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(h)
    scene = json.loads(args.scene.read_text())
    spec_path = ROOT / scene["spec_path"]
    if sha(spec_path) != scene["spec_sha256"]:
        raise ValueError("Scene/spec mismatch")
    spec = json.loads(spec_path.read_text())
    geometry_path = ROOT / spec["geometry_spec"]
    if sha(geometry_path) != spec["geometry_spec_sha256"]:
        raise ValueError("Geometry source changed")
    points = json.loads(geometry_path.read_text())["points_world_m"]
    meshes = {p["name"]: mesh(p) for p in scene["parts"]}
    parts = {p["name"]: p for p in scene["parts"]}
    rows, contacts = [], []

    def mass_row(name, body, mass_range, position=None, scope="finite material"):
        m = meshes[name]
        if not (m.is_watertight and m.is_winding_consistent and m.volume > 0):
            raise ValueError("Invalid mass source: " + name)
        centroid = np.asarray(position) if position is not None else m.center_mass
        # Component/reserve inertia uses an explicitly homogeneous-envelope
        # proxy. It never becomes an OEM inertia or released SI parameter.
        nominal = mass_range[1]
        proxy = m.moment_inertia * (nominal / m.volume)
        rows.append({"id": name, "body": body, "mass_range_kg": list(mass_range), "COM_world_m": centroid.tolist(),
                     "inertia_at_centroid_nominal_kg_m2": proxy.tolist(), "scope": scope})

    for p in scene["parts"]:
        name, role = p["name"], p["role"]
        is_pad = name.endswith(("_composite_forepad", "_composite_heel_pad"))
        m = meshes[name]
        if role == "net_primary_structure_candidate":
            masses = [m.volume * spec["material"]["density_kg_m3"]] * 3
            mass_row(name, h.canonical(p["body"]), masses)
        elif role in ("armor_surface", "armor_cover"):
            mass_row(name, h.canonical(p["body"]), [m.volume * rho for rho in spec["armor_density_range_kg_m3_hypothesis"]], scope="nominal armor geometry, density hypotheses")
        elif is_pad:
            mass_row(name, p["body"], [m.volume * rho for rho in spec["pad_density_range_kg_m3_hypothesis"]], scope="nominal pad geometry, density hypotheses")
            v = np.asarray(p["vertices_world_m"])
            contacts.extend((p["body"], x) for x in v[abs(v[:, 2]) < 1e-8])
    for r in scene["catalogue_constituent_and_auxiliary_rows"]:
        mass_row(r["id"], r["body"], r["mass_range_kg"], r["centroid_hypothesis_world_m"],
                 scope=r["mass_distribution_status"] + " Homogeneous envelope inertia proxy, not physical contract.")
    for r in scene["context_module_probes"]:
        source = r["source_module"]
        mass_row(r["id"], h.module_body(source), source["mass_range_kg"], source["center_world_m"],
                 scope="Inherited A complete reserve, unqualified owner/centroid/size/output/thermal; homogeneous inertia proxy.")
    total = [sum(r["mass_range_kg"][i] for r in rows) for i in range(3)]
    body_rows = []
    for body in sorted({r["body"] for r in rows}):
        selected = [r for r in rows if r["body"] == body]
        bm = sum(r["mass_range_kg"][1] for r in selected)
        com = sum(r["mass_range_kg"][1] * np.asarray(r["COM_world_m"]) for r in selected) / bm
        inertia = np.zeros((3, 3))
        for r in selected:
            d = np.asarray(r["COM_world_m"]) - com
            inertia += np.asarray(r["inertia_at_centroid_nominal_kg_m2"]) + r["mass_range_kg"][1] * (d @ d * np.eye(3) - np.outer(d, d))
        body_rows.append({"body": body, "mass_range_kg": [sum(r["mass_range_kg"][i] for r in selected) for i in range(3)],
                          "COM_world_m_hypothesis": com.tolist(), "complete_3x3_inertia_proxy_kg_m2": inertia.tolist(),
                          "inertia_eigenvalues_kg_m2": np.linalg.eigvalsh(inertia).tolist(),
                          "inertia_status": "Diagnostic only. Geometry-derived frame tensors mixed with unverified catalogue/reserve mass distribution. Not an OEM/full robot SI contract."})

    pose_reports, space_reports = [], []
    for pose_name, angles in spec["candidate_pose_angles_deg"].items():
        parents, transforms = h.transforms(points, angles)
        posed_contacts = [(body, h.transformed(transforms[body], p)) for body, p in contacts]
        root_shift = np.array([0., 0., -min(p[2] for _, p in posed_contacts)])
        for t in transforms.values():
            t[:3, 3] += root_shift
        posed_contacts = sorted({(body, tuple(np.round(p + root_shift, 12))) for body, p in posed_contacts})
        vertices = np.array([p for _, p in posed_contacts])
        contact_bodies = [body for body, _ in posed_contacts]
        if abs(vertices[:, 2]).max() > 1e-7:
            raise ValueError("Non-coplanar contact; normal-only diagnostic invalid")
        pose = {"id": pose_name, "angles_deg": angles, "root_z_alignment_m": float(root_shift[2]),
                "body_transforms": {b: m.tolist() for b, m in transforms.items()}, "cases": []}
        for payload, pressure, factor in ((0, 0, 1.), (100, 0, 1.), (100, 0, 1.5), (0, 3000, 1.)):
            loads = [{"id": r["id"], "body": r["body"], "position_world_m": h.transformed(transforms[r["body"]], r["COM_world_m"]).tolist(),
                      "force_world_N": [0., 0., -r["mass_range_kg"][1] * spec["gravity_m_s2"] * factor]} for r in rows]
            for side in ("left", "right"):
                if payload:
                    loads.append({"id": side + "_payload", "body": side + "_palm", "position_world_m": h.transformed(transforms[side + "_palm"], points[side + "_palm"]).tolist(),
                                  "force_world_N": [0., 0., -payload / 2 * spec["gravity_m_s2"] * factor]})
            if pressure:
                loads.append({"id": "crown_pressure", "body": "torso", "position_world_m": h.transformed(transforms["torso"], [0, 0, 2.45]).tolist(),
                              "force_world_N": [0., 0., -pressure * spec["gravity_m_s2"] * factor]})
            case = {"payload_kg_hypothesis": payload, "external_pressure_demand_kg": pressure, "gravity_factor_sensitivity": factor,
                    "double_normal_contact": normal_contacts(vertices, loads),
                    "single_left_unchanged_pose_normal_contact": normal_contacts(vertices[[b.startswith("left_") for b in contact_bodies]], loads),
                    "joint_wrenches": [], "physics_accepted": False}
            if case["double_normal_contact"]["feasible"]:
                allocations = contact_extreme_allocations(vertices, loads)
                case["contact_extreme_count"] = len(allocations)
                joint_models = []
                for j in scene["joint_supports"]:
                    distal = h.descendants(parents, j["output_body"])
                    origin = h.transformed(transforms[j["parent_body"]], j["center_world_m"])
                    f, moment = resultant([r for r in loads if r["body"] in distal], origin)
                    active = allocations * np.array([b in distal for b in contact_bodies])
                    forces = np.tile(f, (len(active), 1))
                    forces[:, 2] += active.sum(1)
                    moments = moment + active @ np.cross(vertices - origin, [0, 0, 1])
                    axis = transforms[j["parent_body"]][:3, :3] @ np.asarray(j["axis_world"])
                    holding = moments @ axis
                    coefficients = np.cross(vertices - origin, [0, 0, 1]) @ axis
                    coefficients *= np.array([b in distal for b in contact_bodies])
                    joint_models.append({"joint": j, "gravity_torque_Nm": float(moment @ axis),
                                         "contact_torque_coefficients_m": coefficients.tolist()})
                    demand = float(abs(holding).max())
                    operating = []
                    for speed, eta in itertools.product(spec["output_speed_samples_rad_s"], spec["efficiency_sensitivity"]):
                        need = demand / (eta * j["ratio"])
                        torque_ref = j["catalogue_motor_Ts_Nm"] if speed == 0 else j["catalogue_motor_Tc_Nm"]
                        rpm = speed * j["ratio"] * 60 / (2 * np.pi)
                        operating.append({"speed_rad_s": speed, "efficiency_hypothesis": eta, "input_speed_rpm": rpm,
                                          "input_torque_Nm_hypothesis": need,
                                          "nominal_motor_torque_reference_Nm": torque_ref,
                                          "exceeds_nominal_motor_reference": need > torque_ref,
                                          "exceeds_reference_minus10_percent_sensitivity": need > .9 * torque_ref,
                                          "exceeds_gear_catalogue_rated_comparison": demand > j["catalogue_gear_rated_Nm"],
                                          "above_published_speed_at_Tc": rpm > j["nmax_at_Tc_and_Umax_rpm"],
                                          "mechanical_power_bound_W": demand * speed,
                                          "gear_loss_hypothesis_W": None if speed == 0 else demand * speed * (1 / eta - 1),
                                          "joint_qualified": False,
                                          "scope": "Static efficiency mapping at zero speed is only algebraic sensitivity. Motor curve/bus/20C mount/static transmission/actual thermal remain unknown."})
                    case["joint_wrenches"].append({"id": j["id"], "holding_pitch_signed_min_max_Nm": [float(holding.min()), float(holding.max())],
                                                  "maximum_resultant_force_N": float(np.linalg.norm(forces, axis=1).max()),
                                                  "maximum_off_axis_moment_Nm": float(np.linalg.norm(moments - holding[:, None] * axis, axis=1).max()),
                                                  "operating_comparisons": operating})
                case["contact_and_drive_hypotheses"] = [contact_with_drive_hypotheses(vertices, loads, joint_models, speed, eta, motor_factor)
                                                        for speed, eta, motor_factor in itertools.product(spec["output_speed_samples_rad_s"], spec["efficiency_sensitivity"], (1., .9))]
                case["extreme_scope"] = "Unconstrained normal-contact extremes characterize potential demand. They do not prove no actuator-constrained allocation exists; see separate minimax LP."
            pose["cases"].append(case)
        pose_reports.append(pose)

        if not args.no_space:
            selected = [p for p in scene["parts"] if p["role"] in ("net_primary_structure_candidate", "armor_cover", "armor_surface", "catalogue_constituent_envelope", "unqualified_installation_reserve", "complete_module_packaging_probe")]
            posed = {}
            for p in selected:
                m = meshes[p["name"]].copy()
                body = p["body"]
                if body == "unresolved_module_allocation":
                    body = h.module_body(p["internal_structure_c"]["A_module"])
                m.apply_transform(transforms[h.canonical(body)])
                posed[p["name"]] = m
            conflicts, unknown = [], []
            for a, b in itertools.combinations(selected, 2):
                ra, rb = a["role"], b["role"]
                if ra in ("armor_surface", "armor_cover") and rb in ("armor_surface", "armor_cover"):
                    continue
                if ra == rb == "net_primary_structure_candidate" and a["body"] == b["body"]:
                    continue
                ma, mb = posed[a["name"]], posed[b["name"]]
                if not bounds_overlap(ma, mb):
                    continue
                try:
                    intersection = trimesh.boolean.intersection([ma, mb], engine="manifold")
                    volume = float(intersection.volume) if len(intersection.faces) else 0.
                except Exception as exc:
                    unknown.append({"parts": [a["name"], b["name"]], "error": str(exc)})
                    continue
                if volume > 1e-9:
                    conflicts.append({"parts": [a["name"], b["name"]], "roles": [ra, rb], "bodies": [a["body"], b["body"]], "positive_volume_m3": volume})
            space_reports.append({"pose": pose_name, "positive_volume_threshold_m3": 1e-9, "conflict_count": len(conflicts),
                                  "conflicts": conflicts, "unknown_intersections": unknown,
                                  "scope": "Native finite materials and explicit catalogue/reserve envelopes only; legacy visual mechanisms, full cables/tools/sweep/contacts not accepted.", "geometry_accepted": False})
        print(pose_name, "completed", flush=True)
    bindings = {"robot_id": "gorilla_v0_1", "candidate": "internal_structure_c", "scene_path": str(args.scene.relative_to(ROOT)), "scene_sha256": sha(args.scene),
                "spec_sha256": sha(spec_path), "evaluator_sha256": sha(Path(__file__)), "pose_helper_sha256": sha(HELPER),
                "geometry_accepted": False, "physics_accepted": False, "stable_physical_contract": False}
    report = {**bindings, "schema": "gorilla_internal_co_design_macro_v1", "conditional_mass_range_kg": total, "mass_rows": rows,
              "body_mass_and_inertia_proxies": body_rows, "poses": pose_reports,
              "scope": "Actual finite geometry, catalogue component masses and unqualified remainder/context reserves. Finite gravity/normal contact and algebraic motor/gear comparisons. No dynamics, continuous joint capability, friction, thermal or stable SI release."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not args.no_space:
        args.space_output.write_text(json.dumps({**bindings, "schema": "gorilla_internal_co_design_space_v1", "poses": space_reports}, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"conditional_mass_range_kg": total, "material_components": {r["body"]: r["connected_material_components"] for r in scene["net_frame_rows"]},
                      "space_conflict_counts": {p["pose"]: p["conflict_count"] for p in space_reports}}))


if __name__ == "__main__":
    main()
