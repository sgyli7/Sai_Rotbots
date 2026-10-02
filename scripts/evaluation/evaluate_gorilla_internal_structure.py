#!/usr/bin/env python3
"""Actual-pose macro statics and coupled-cylinder probes for Gorilla structure B.

This is a gravity/contact sensitivity calculation. It supplies no hidden support,
motor torque, dynamic gait, bearing contact law or manufactured assembly evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh
from sai_agent.structural_statics import contact_extreme_allocations, normal_contacts, resultant

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(part):
    faces = [[f[0], f[k], f[k + 1]] for f in part["faces"] for k in range(1, len(f) - 1)]
    return trimesh.Trimesh(part["vertices_world_m"], faces, process=False)


def rotation(point, degrees):
    angle = np.deg2rad(degrees)
    c, s = np.cos(angle), np.sin(angle)
    out = np.eye(4)
    out[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    point = np.asarray(point)
    out[:3, 3] = point - out[:3, :3] @ point
    return out


def transformed(transform, point):
    return (transform @ np.r_[point, 1.])[:3]


def transforms(points, angles):
    parents = {"pelvis": None, "torso": "pelvis"}
    matrices = {"pelvis": np.eye(4), "torso": rotation([0, 0, 1.74], angles["torso"])}
    for side in ("left", "right"):
        for body, parent, pivot, angle in (
            ("upper_arm", "torso", "shoulder", "shoulder"),
            ("forearm", side + "_upper_arm", "elbow", "elbow"),
            ("palm", side + "_forearm", "wrist", None),
            ("thigh", "pelvis", "hip", "hip"),
            ("middle_shank", side + "_thigh", "knee", "knee"),
            ("distal_shank", side + "_middle_shank", "fold", "fold"),
            ("foot", side + "_distal_shank", "ankle", "ankle"),
        ):
            identifier = side + "_" + body
            parents[identifier] = parent
            matrices[identifier] = matrices[parent] @ rotation(points[side + "_" + pivot], angles[angle] if angle else 0)
        for body in ("forefoot_display", "heel_display"):
            identifier = side + "_" + body
            parents[identifier] = side + "_foot"
            matrices[identifier] = matrices[side + "_foot"].copy()
    return parents, matrices


def canonical(body):
    if "finger" in body or "thumb" in body:
        return body.split("_")[0] + "_palm"
    return body


def descendants(parents, body):
    result = {body}
    for candidate in parents:
        p = parents[candidate]
        while p:
            if p == body:
                result.add(candidate)
                break
            p = parents[p]
    return result


def module_body(row):
    identifier = row["id"]
    side = next((s for s in ("left", "right") if "_" + s + "_" in identifier), None)
    if not side:
        return "pelvis" if "waist_" in identifier or row["category"] == "connections" else "torso"
    if "battery" in identifier or row["category"] in ("thermal", "compute"):
        return "torso"
    if "wrist_" in identifier or "hand_mechanisms" in identifier:
        return side + "_palm"
    if "elbow" in identifier:
        return side + "_forearm"
    if "shoulder_" in identifier or "upper_arm_" in identifier:
        return side + "_upper_arm"
    if "lock_and_feedback" in identifier or "ankle" in identifier:
        return side + "_foot"
    if "fold" in identifier:
        return side + "_distal_shank"
    if "knee" in identifier:
        return side + "_middle_shank"
    return side + "_thigh"


def cylinder_endpoints(spec, points, matrices, side, name):
    row = spec["compact_cylinder_probe"][name]
    sign = 1 if side == "left" else -1
    base_offset = np.array(row["base_relative_to_fold_m"])
    base_offset[1] *= sign
    output_key = "output_relative_to_fold_m" if name == "fold" else "output_relative_to_ankle_m"
    output_offset = np.array(row[output_key])
    output_offset[1] *= sign
    a = transformed(matrices[side + "_" + row["base_body"]], np.array(points[side + "_fold"]) + base_offset)
    b = transformed(matrices[side + "_" + row["output_body"]], np.array(points[side + "_" + name]) + output_offset)
    return a, b


def cylinder_probe(spec, points, angles, side):
    _, matrices = transforms(points, angles)
    rows, lengths = [], []
    jacobian = np.zeros((2, 2))
    for index, name in enumerate(("fold", "ankle")):
        row = spec["compact_cylinder_probe"][name]
        a, b = cylinder_endpoints(spec, points, matrices, side, name)
        length = np.linalg.norm(b - a)
        lengths.append(length)
        minimum = row["bare_retracted_to_thread_tip_m"] + spec["compact_cylinder_probe"]["mount_eye_allowance_m"]
        rows.append({"id": side + "_" + name, "base_world_m": a.tolist(), "output_world_m": b.tolist(),
                     "length_m": float(length), "conditional_eye_length_range_m": [minimum, minimum + spec["compact_cylinder_probe"]["stroke_m"]],
                     "stroke_within_conditional_range": bool(minimum <= length <= minimum + spec["compact_cylinder_probe"]["stroke_m"]),
                     "direction_base_to_output_world": ((b - a) / length).tolist()})
        for j, angle_name in enumerate(("fold", "ankle")):
            delta = 1e-5
            a_plus, a_minus = dict(angles), dict(angles)
            a_plus[angle_name] += np.rad2deg(delta)
            a_minus[angle_name] -= np.rad2deg(delta)
            _, plus = transforms(points, a_plus)
            _, minus = transforms(points, a_minus)
            ap, bp = cylinder_endpoints(spec, points, plus, side, name)
            am, bm = cylinder_endpoints(spec, points, minus, side, name)
            jacobian[index, j] = (np.linalg.norm(bp - ap) - np.linalg.norm(bm - am)) / (2 * delta)
    return rows, jacobian


def bearing_screen(force, moment, spec, transmitted_pitch_torque=None):
    bearing, shaft, material = spec["bearing"], spec["shaft"], spec["material"]
    h = bearing["conditional_O_pressure_center_half_span_m"]
    radial_a = np.column_stack([force[:, 0] / 2 + moment[:, 2] / (2 * h), force[:, 2] / 2 - moment[:, 0] / (2 * h)])
    radial_b = np.column_stack([force[:, 0] / 2 - moment[:, 2] / (2 * h), force[:, 2] / 2 + moment[:, 0] / (2 * h)])
    fr_a, fr_b = np.linalg.norm(radial_a, axis=1), np.linalg.norm(radial_b, axis=1)
    # External axial load changes the A/B designation under the catalogue diagram.
    reverse = force[:, 1] < 0
    ra, rb = np.where(reverse, fr_b, fr_a), np.where(reverse, fr_a, fr_b)
    ka = abs(force[:, 1])
    ua, ub = ra / bearing["Y"], rb / bearing["Y"]
    use_a = (ua <= ub) | (ka > bearing["induced_axial_coefficient"] * (ua - ub))
    fa = np.where(use_a, ka + bearing["induced_axial_coefficient"] * ub, 0)
    fb = np.where(use_a, 0, bearing["induced_axial_coefficient"] * ua - ka)
    p0a = np.maximum(ra, .5 * ra + bearing["Y0"] * fa)
    p0b = np.maximum(rb, .5 * rb + bearing["Y0"] * fb)
    p0 = max(p0a.max(), p0b.max())
    outer, inner = shaft["outer_radius_m"], shaft["bore_radius_m"]
    area = np.pi * (outer ** 2 - inner ** 2)
    polar = np.pi / 2 * (outer ** 4 - inner ** 4)
    bending_bound = np.linalg.norm(moment[:, [0, 2]], axis=1) + np.linalg.norm(force[:, [0, 2]], axis=1) * (2 * h) / 4
    sigma = bending_bound * outer / (polar / 2) + abs(force[:, 1]) / area
    shaft_torque = moment[:, 1] if transmitted_pitch_torque is None else transmitted_pitch_torque
    tau = abs(shaft_torque) * outer / polar
    vm = np.sqrt(sigma ** 2 + 3 * tau ** 2)
    return {"maximum_radial_reaction_each_bearing_N": [float(fr_a.max()), float(fr_b.max())],
            "maximum_single_bearing_catalogue_P0_N": float(p0),
            "minimum_conditional_static_s0": float(bearing["static_radial_C0r_N"] / p0) if p0 > 0 else None,
            "shaft_nominal_combined_von_mises_bound_Pa": float(vm.max()),
            "shaft_conditional_yield_ratio": float(material["minimum_yield_Pa"] / vm.max()) if vm.max() else None,
            "scope": "Conditional O pressure centers; no-play/no-preload catalogue static load formula. Shaft conservative central-span nominal section bound omits shoulder/key/weld concentration, stiffness, preload, fatigue, contact and certificates. Not component acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=ROBOT / "cad/source/internal_structure_b_scene.json")
    parser.add_argument("--output", type=Path, default=ROBOT / "evidence/internal_structure_b_statics.json")
    args = parser.parse_args()
    scene = json.loads(args.scene.read_text())
    spec_path = ROOT / scene["spec_path"]
    if sha(spec_path) != scene["spec_sha256"]:
        raise ValueError("Scene/spec mismatch")
    spec = json.loads(spec_path.read_text())
    geometry_path = ROOT / spec["geometry_spec"]
    points = json.loads(geometry_path.read_text())["points_world_m"]
    layout_path, budget_path = ROOT / spec["budget_layout"], ROOT / spec["budget_spec"]
    layout, budget = json.loads(layout_path.read_text()), json.loads(budget_path.read_text())
    material_rows, contacts = [], []
    for p in scene["parts"]:
        role = p["role"]
        is_pad = p["name"].endswith(("_composite_forepad", "_composite_heel_pad"))
        if role in ("net_primary_structure_candidate", "armor_surface", "armor_cover", "bearing_reference_envelope") or is_pad:
            m = mesh(p)
            if not (m.is_watertight and m.is_winding_consistent and m.volume > 0):
                raise ValueError("Invalid mass material: " + p["name"])
            if is_pad:
                masses = [m.volume * rho for rho in spec["pad_density_range_kg_m3_hypothesis"]]
            elif role == "net_primary_structure_candidate":
                masses = [m.volume * spec["material"]["density_kg_m3"]] * 3
            elif role == "bearing_reference_envelope":
                masses = [p["internal_structure_b"]["mass_kg"]] * 3
            else:
                masses = [m.volume * rho for rho in budget["armor_density_range_kg_m3"]]
            material_rows.append({"id": p["name"], "body": canonical(p["body"]), "position": m.center_mass, "mass_range_kg": masses})
        if p["name"].endswith(("_composite_forepad", "_composite_heel_pad")):
            vertices = np.asarray(p["vertices_world_m"])
            for v in vertices[abs(vertices[:, 2]) < 1e-8]:
                contacts.append((p["body"], v))
    module_rows = []
    for r in layout["modules"]:
        if not r["family"] or r["route"] not in ("common", "central_hydraulic"):
            continue
        if "central_hydraulic" in r["id"] and ("fold_pitch" in r["id"] or "ankle_pitch" in r["id"]):
            continue
        module_rows.append({"id": r["id"], "body": module_body(r), "position": np.array(r["center_world_m"]), "mass_range_kg": r["mass_range_kg"]})
    for side in ("left", "right"):
        for name in ("fold", "ankle"):
            c = spec["compact_cylinder_probe"][name]
            _, neutral_matrices = transforms(points, spec["candidate_pose_angles_deg"]["neutral"])
            a, b = cylinder_endpoints(spec, points, neutral_matrices, side, name)
            # Explicit coarse owner/centroid sensitivity; rod/body mass split is unknown.
            masses = [c["bare_mass_kg"] + reserve for reserve in spec["compact_cylinder_probe"]["mount_mass_range_kg"]]
            module_rows.append({"id": "isb_" + side + "_" + name + "_complete_cylinder_allowance", "body": side + "_middle_shank", "position": (a + b) / 2, "mass_range_kg": masses})
    rows = material_rows + module_rows
    masses = [sum(r["mass_range_kg"][i] for r in rows) for i in range(3)]
    pose_results = []
    for pose_name, angles in spec["candidate_pose_angles_deg"].items():
        parents, matrices = transforms(points, angles)
        pad_rows = [(body, transformed(matrices[canonical(body)], v)) for body, v in contacts]
        min_z = min(v[2] for _, v in pad_rows)
        root_shift = np.array([0, 0, -min_z])
        for matrix in matrices.values():
            matrix[:3, 3] += root_shift
        pad_rows = [(body, v + root_shift) for body, v in pad_rows]
        if max(abs(v[2]) for _, v in pad_rows) > 1e-7:
            raise ValueError("This finite contact probe requires coplanar pads")
        # Preserve distinct actual vertices; coincident points do not add support.
        unique = {(canonical(body), tuple(np.round(v, 12))) for body, v in pad_rows}
        pad_rows = sorted(unique)
        vertices = np.array([v for _, v in pad_rows])
        contact_bodies = [body for body, _ in pad_rows]
        cyl_rows, jacobians = {}, {}
        for side in ("left", "right"):
            cr, jacobian = cylinder_probe(spec, points, angles, side)
            for r in cr:
                r["base_world_m"] = (np.array(r["base_world_m"]) + root_shift).tolist()
                r["output_world_m"] = (np.array(r["output_world_m"]) + root_shift).tolist()
            cyl_rows[side], jacobians[side] = cr, jacobian
        pose = {"id": pose_name, "angles_deg": angles, "root_z_alignment_m": float(root_shift[2]),
                "body_rest_world_to_pose_transforms": {b: m.tolist() for b, m in matrices.items()},
                "cylinders": cyl_rows, "jacobian_m_per_rad": {s: j.tolist() for s, j in jacobians.items()},
                "jacobian_singular_values_m_per_rad": {s: np.linalg.svd(j, compute_uv=False).tolist() for s, j in jacobians.items()}, "cases": []}
        for payload, pressure, multiplier in ((0, 0, 1.), (100, 0, 1.), (100, 0, 1.5), (0, 3000, 1.)):
            loads = []
            for row in rows:
                if row["body"] not in matrices:
                    raise ValueError("Unknown allocated body: " + row["body"])
                loads.append({"id": row["id"], "body": row["body"], "position_world_m": transformed(matrices[row["body"]], row["position"]).tolist(),
                              "force_world_N": [0, 0, -row["mass_range_kg"][1] * budget["gravity_m_s2"] * multiplier]})
            for side in ("left", "right"):
                if payload:
                    loads.append({"id": side + "_held_payload", "body": side + "_palm", "position_world_m": transformed(matrices[side + "_palm"], points[side + "_palm"]).tolist(),
                                  "force_world_N": [0, 0, -payload / 2 * budget["gravity_m_s2"] * multiplier]})
            if pressure:
                loads.append({"id": "crown_pressure_demand", "body": "torso", "position_world_m": transformed(matrices["torso"], [0, 0, 2.45]).tolist(),
                              "force_world_N": [0, 0, -pressure * budget["gravity_m_s2"] * multiplier]})
            contact = normal_contacts(vertices, loads)
            case = {"payload_kg_hypothesis": payload, "external_pressure_demand_kg": pressure, "load_multiplier_hypothesis": multiplier,
                    "double_support_contact": contact, "joint_wrenches": [], "coupled_actuation": {}, "physics_accepted": False}
            if contact["feasible"]:
                allocations = contact_extreme_allocations(vertices, loads)
                if not len(allocations):
                    raise ValueError("Feasible normal balance without extreme allocation")
                case["extreme_contact_allocation_count"] = len(allocations)
                per_joint = {}
                for joint in scene["joint_supports"]:
                    distal = descendants(parents, joint["output_body"])
                    origin = transformed(matrices[joint["parent_body"]], joint["center_world_m"])
                    f, m = resultant([r for r in loads if r["body"] in distal], origin)
                    active = allocations * np.array([b in distal for b in contact_bodies])
                    forces = np.tile(f, (len(active), 1))
                    forces[:, 2] += active.sum(1)
                    moments = m + active @ np.cross(vertices - origin, [0, 0, 1])
                    per_joint[joint["id"]] = (origin, forces, moments)
                    case["joint_wrenches"].append({"joint": joint["id"], "holding_pitch_max_abs_Nm": float(abs(moments[:, 1]).max()),
                                                  "maximum_six_dimensional_force_N": float(np.linalg.norm(forces, axis=1).max()),
                                                  "passive_only_bearing_and_nominal_shaft_screen": bearing_screen(-forces, -moments, spec),
                                                  "scope": "Body gravity and true pad-normal extreme reactions before actuator radial forces. Bearings do not supply holding torque."})
                for side in ("left", "right"):
                    jacobian = jacobians[side]
                    fold_origin, ff, mf = per_joint[side + "_fold"]
                    ankle_origin, fa, ma = per_joint[side + "_ankle"]
                    target = -np.column_stack([mf[:, 1], ma[:, 1]])
                    if np.linalg.svd(jacobian, compute_uv=False).min() < 1e-5:
                        case["coupled_actuation"][side] = {"rejected": "Near singular length Jacobian"}
                        continue
                    actual = np.linalg.solve(jacobian.T, target.T).T
                    maxima = abs(target).max(0)
                    opposite = np.array(list(itertools.product((-1, 1), repeat=2))) * maxima
                    corners = np.linalg.solve(jacobian.T, opposite.T).T
                    demand_rows = []
                    ideal_output_forces = []
                    for index, name in enumerate(("fold", "ankle")):
                        c = spec["compact_cylinder_probe"][name]
                        area = np.pi * c["bore_m"] ** 2 / 4
                        annulus_area = area - np.pi * c["rod_m"] ** 2 / 4
                        p = spec["compact_cylinder_probe"]["nominal_pressure_Pa"]
                        back = spec["compact_cylinder_probe"]["return_pressure_sensitivity_Pa"]
                        push_capacity, pull_capacity = p * area - back * annulus_area, p * annulus_area - back * area
                        need = actual[:, index] / spec["compact_cylinder_probe"]["link_loss_sensitivity_efficiency"]
                        demand_rows.append({"cylinder": name, "ideal_signed_force_min_max_N": [float(actual[:, index].min()), float(actual[:, index].max())],
                                            "loss_sensitivity_signed_force_min_max_N": [float(need.min()), float(need.max())],
                                            "opposite_torque_box_ideal_signed_force_min_max_N": [float(corners[:, index].min()), float(corners[:, index].max())],
                                            "push_pull_capacity_at_pressure_and_return_hypotheses_N": [push_capacity, pull_capacity],
                                            "real_contact_case_force_within_hypothesis": bool(need.min() >= -pull_capacity and need.max() <= push_capacity)})
                        direction = np.array(cyl_rows[side][index]["direction_base_to_output_world"])
                        ideal_output_forces.append(actual[:, index, None] * direction)
                    fold_correction = sum(ideal_output_forces)
                    fold_moment_correction = sum(np.cross(np.array(cyl_rows[side][i]["output_world_m"]) - fold_origin, f) for i, f in enumerate(ideal_output_forces))
                    ankle_correction = ideal_output_forces[1]
                    ankle_moment_correction = np.cross(np.array(cyl_rows[side][1]["output_world_m"]) - ankle_origin, ankle_correction)
                    case["coupled_actuation"][side] = {"cylinders": demand_rows,
                        "virtual_work_balance_max_abs_Nm": float(abs(actual @ jacobian - target).max()),
                        "fold_pitch_ideal_equilibrium_residual_Nm": float(abs((mf + fold_moment_correction)[:, 1]).max()),
                        "ankle_pitch_ideal_equilibrium_residual_Nm": float(abs((ma + ankle_moment_correction)[:, 1]).max()),
                        "fold_bearings_with_ideal_cylinder_radial_loads": bearing_screen(-(ff + fold_correction), -(mf + fold_moment_correction), spec, target[:, 0]),
                        "ankle_bearings_with_ideal_cylinder_radial_loads": bearing_screen(-(fa + ankle_correction), -(ma + ankle_moment_correction), spec, target[:, 1]),
                        "scope": "Signed coupled ideal endpoint forces and actual finite contact cases. Loss/backpressure and independent opposite-torque corners are separate sensitivities, not dynamics, preload or continuous qualification."}
            single_vertices = vertices[[body.startswith("left_") for body in contact_bodies]]
            case["unchanged_pose_single_left_normal_balance"] = normal_contacts(single_vertices, loads)
            pose["cases"].append(case)
        pose_results.append(pose)
        print(pose_name, "stroke", [r["stroke_within_conditional_range"] for r in cyl_rows["left"]],
              "double", [c["double_support_contact"]["feasible"] for c in pose["cases"]], flush=True)
    report = {"schema": "gorilla_internal_structure_statics_v1", "robot_id": "gorilla_v0_1", "scene_sha256": sha(args.scene),
              "spec_sha256": sha(spec_path), "geometry_spec_sha256": sha(geometry_path), "budget_spec_sha256": sha(budget_path),
              "budget_layout_sha256": sha(layout_path), "evaluator_sha256": sha(Path(__file__)),
              "conditional_robot_mass_range_kg": masses, "material_mass_rows": [{**r, "position": r["position"].tolist()} for r in material_rows],
              "complete_module_allocation_rows": [{**r, "position": r["position"].tolist()} for r in module_rows], "poses": pose_results,
              "geometry_accepted": False, "physics_accepted": False, "stable_physical_contract": False,
              "scope": "Actual rigid-body candidate poses and finite gravity normal contacts; exact net material mass plus complete-module allocation hypotheses. Includes signed coupling, conditional pressure/stroke and bearing/shaft macro screens. Allocation owner/centroid, rod/body mass split, complete drive topology, friction/strength/buckling/fatigue, dynamics, power/thermal and hardware validation remain open."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "conditional_mass_kg": masses}))


if __name__ == "__main__":
    main()
