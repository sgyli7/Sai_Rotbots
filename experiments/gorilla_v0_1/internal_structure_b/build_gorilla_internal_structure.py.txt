#!/usr/bin/env python3
"""Build an independent net-stock and paired output-support Gorilla candidate.

The AA3 armor is copied exactly. Old shaft-seat stock is replaced, not discounted.
Frame unions are nominal welded material geometry, not qualified connections.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import MultiPoint

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_mesh(part):
    faces = [[f[0], f[i], f[i + 1]] for f in part["faces"] for i in range(1, len(f) - 1)]
    return trimesh.Trimesh(part["vertices_world_m"], faces, process=False)


def united(meshes):
    result = trimesh.boolean.union(meshes, engine="manifold") if len(meshes) > 1 else meshes[0].copy()
    if not (result.is_watertight and result.is_winding_consistent and result.volume > 0):
        raise ValueError("Invalid finite material union")
    return result


def cylinder(center, radius, length):
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=96)
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [0, 1, 0]))
    mesh.apply_translation(center)
    return mesh


def annulus(center, outer, inner, length):
    return trimesh.boolean.difference(
        [cylinder(center, outer, length), cylinder(center, inner, length + .002)], engine="manifold"
    )


def box_tube(a, b, width, depth, wall):
    a, b = np.asarray(a), np.asarray(b)
    axis = b - a
    length = np.linalg.norm(axis)
    if length < 1e-6:
        raise ValueError("Degenerate tube")
    # Local X is a transverse axis; local Z follows the centerline.
    outer = trimesh.creation.box(extents=[width, depth, length])
    inner = trimesh.creation.box(extents=[width - 2 * wall, depth - 2 * wall, length + .002])
    mesh = trimesh.boolean.difference([outer, inner], engine="manifold")
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], axis / length))
    mesh.apply_translation((a + b) / 2)
    return mesh


def solid_along(a, b, width, depth):
    a, b = np.asarray(a), np.asarray(b)
    direction = b - a
    shape = trimesh.creation.box(extents=[width, depth, np.linalg.norm(direction)])
    shape.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], direction / np.linalg.norm(direction)))
    shape.apply_translation((a + b) / 2)
    return shape


def part_row(identifier, body, mesh, role, rgba, **metadata):
    return {"name": identifier, "body": body, "vertices_world_m": mesh.vertices.tolist(),
            "faces": mesh.faces.tolist(), "color_rgba": rgba, "hardware": True,
            "edge_bevel_m": 0, "role": role, "internal_structure_b": metadata}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=ROBOT / "configs/internal_structure_b_spec.json")
    parser.add_argument("--output", type=Path, default=ROBOT / "cad/source/internal_structure_b_scene.json")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    base_path = ROOT / spec["base_scene"]
    if sha(base_path) != spec["base_scene_sha256"]:
        raise ValueError("Frozen C15 changed")
    base = json.loads(base_path.read_text())
    foot = None
    if spec.get("foot_candidate"):
        foot_path = ROOT / spec["foot_candidate"]
        if sha(foot_path) != spec["foot_candidate_sha256"]:
            raise ValueError("Foot candidate changed")
        foot = json.loads(foot_path.read_text())
        if foot["base_scene_sha256"] != sha(base_path):
            raise ValueError("Foot/base identity mismatch")
    removed_foot = set(foot["removed_part_names"] if foot else [])
    points = json.loads((ROOT / spec["geometry_spec"]).read_text())["points_world_m"]
    bearing, shaft, housing = spec["bearing"], spec["shaft"], spec["housing"]
    frames, source_names, replaced = {}, {}, []
    for p in base["parts"]:
        if p["name"] in removed_foot:
            continue
        if p["role"] == "primary_structure_candidate":
            frames.setdefault(p["body"], []).append(native_mesh(p))
            source_names.setdefault(p["body"], []).append(p["name"])
        elif p["role"] == "primary_structure_socket_candidate":
            replaced.append(p["name"])
    # Reconstruct the internal right upper-arm member by an exact left reflection.
    # A bent quad's triangulation previously produced unequal mirror volumes.
    if spec.get("reflect_left_upper_arm_frame", False):
        frames["right_upper_arm"] = [m.copy() for m in frames["left_upper_arm"]]
        for mesh in frames["right_upper_arm"]:
            mesh.apply_transform(np.diag([1, -1, 1, 1]))
    joints, bearings = [], []

    def end_direction(body, center, at_start):
        for p in base["parts"]:
            member = p.get("structural_member")
            if not member or p["body"] != body:
                continue
            path = np.asarray(member["centerline_world_m"])
            endpoint, neighbor = (path[0], path[1]) if at_start else (path[-1], path[-2])
            if np.linalg.norm(endpoint - center) < 1e-7:
                direction = neighbor - endpoint
                direction[1] = 0
                return direction / np.linalg.norm(direction)
        raise ValueError("No source endpoint at joint: " + body)

    for side in ("left", "right"):
        node_points = [np.asarray(points[side + "_" + k]) for k in ("hip", "knee", "fold", "ankle")]
        parents = ["pelvis", side + "_thigh", side + "_middle_shank", side + "_distal_shank"]
        children = [side + "_thigh", side + "_middle_shank", side + "_distal_shank", side + "_foot"]
        for index, (key, center, parent, child) in enumerate(zip(("hip", "knee", "fold", "ankle"), node_points, parents, children)):
            keepout = cylinder(center, spec["original_frame_joint_keepout_radius_m"], shaft["length_m"] + .010)
            for body in (parent, child):
                trimmed = []
                for mesh in frames[body]:
                    cutters = [keepout] if body == parent else [
                        cylinder(center + [0, s * bearing["center_half_span_m"], 0], housing["outer_radius_m"] + .001, housing["length_m"] + .002)
                        for s in (-1, 1)]
                    result = trimesh.boolean.difference([mesh, *cutters], engine="manifold")
                    if len(result.faces):
                        trimmed.append(result)
                frames[body] = trimmed
            if index == 0:
                fixed_direction = np.array([0., 0., 1.])
                anchor = np.array([0., center[1] / 2, center[2]])
            else:
                fixed_direction = end_direction(parent, center, False)
                anchor = center + fixed_direction * .170
            output_direction = end_direction(child, center, True)
            fork_root = center + fixed_direction * spec["fork_radial_station_m"]
            if index == 0:
                intermediate = np.array([anchor[0], anchor[1], fork_root[2]])
                frames[parent].extend([box_tube(anchor, intermediate, .055, .055, .006), box_tube(intermediate, fork_root, .055, .055, .006)])
            else:
                frames[parent].append(box_tube(anchor, fork_root, .055, .055, .006))
            cross_a = fork_root + [0, -bearing["center_half_span_m"] - .010, 0]
            cross_b = fork_root + [0, bearing["center_half_span_m"] + .010, 0]
            frames[parent].append(box_tube(cross_a, cross_b, .048, .048, .005))
            for sign in (-1, 1):
                seat_center = center + [0, sign * bearing["center_half_span_m"], 0]
                # Outer-ring seat with retaining lips: inner cage/shaft stay clear.
                shell = annulus(seat_center, housing["outer_radius_m"], housing["lip_bore_radius_m"], housing["length_m"])
                seat_cavity = cylinder(seat_center, bearing["outer_radius_m"] + housing["seat_radial_clearance_m"], bearing["width_m"] + .0002)
                shell = trimesh.boolean.difference([shell, seat_cavity], engine="manifold")
                arm_end = seat_center + fixed_direction * (housing["outer_radius_m"] - .012)
                frames[parent].extend([shell, box_tube(fork_root + [0, sign * bearing["center_half_span_m"], 0], arm_end, .035, .040, .005)])
                bm = annulus(seat_center, bearing["outer_radius_m"], bearing["inner_radius_m"], bearing["width_m"])
                bp = part_row(f"isb_{side}_{key}_bearing_{sign:+d}".replace("+", "positive").replace("-", "negative"), parent, bm,
                              "bearing_reference_envelope", [.42, .46, .50, 1],
                              mass_kg=bearing["mass_kg"], assembly_parent_body=parent, assembly_output_body=child,
                              motion_scope="Rolling elements, preload, seal, fits and pressure-center installation are not manufactured by this envelope.")
                bearings.append(bp)
            rotor = annulus(center, shaft["outer_radius_m"], shaft["bore_radius_m"], shaft["length_m"])
            collar = annulus(center, shaft["collar_outer_radius_m"], shaft["bore_radius_m"], shaft["collar_width_m"])
            frames[child].extend([rotor, collar, box_tube(center + output_direction * .040, center + output_direction * .170, .100, .080, .010)])
            joints.append({"id": side + "_" + key, "center_world_m": center.tolist(), "axis_world": [0, 1, 0],
                           "parent_body": parent, "output_body": child, "fixed_fork_direction_world": fixed_direction.tolist(),
                           "output_spider_direction_world": output_direction.tolist(),
                           "bearing_centers_world_m": [(center + [0, s * bearing["center_half_span_m"], 0]).tolist() for s in (-1, 1)],
                           "status": "Editable paired support and hollow output only; actuation, attachment and qualified contact remain open."})
    if foot:
        for p in foot["new_parts"]:
            frames.setdefault(p["body"], []).append(native_mesh(p))
    tray_records = []
    for side, sign in (("left", 1), ("right", -1)):
        for segment, pad_suffix, body_suffix in (("forefoot", "_composite_forepad", "forefoot_display"),
                                                 ("heel", "_composite_heel_pad", "heel_display")):
            pad = next(p for p in base["parts"] if p["name"] == side + pad_suffix)
            v = np.asarray(pad["vertices_world_m"])
            top = float(v[:, 2].max())
            polygon = MultiPoint(v[abs(v[:, 2] - top) < 1e-8, :2]).convex_hull
            outline = np.asarray(polygon.exterior.coords[:-1])
            area_twice = np.sum(outline[:, 0] * np.roll(outline[:, 1], -1) - outline[:, 1] * np.roll(outline[:, 0], -1))
            if area_twice < 0:
                outline = outline[::-1]
            triangles = [[0, i, i + 1] for i in range(1, len(outline) - 1)]
            tray = trimesh.creation.extrude_triangulation(outline, triangles, height=spec["segment_tray_thickness_m"])
            tray.apply_translation([0, 0, top])
            body = side + "_" + body_suffix
            frames[body].append(tray)
            # Short local ribs meet the material underside of this same segment.
            if segment == "forefoot":
                x0, x1, yc, half_width, target_z = .065, .345, sign * .620, .1195, .046
            else:
                x0, x1, yc, half_width, target_z = -.335, -.194, sign * .500, .1195, .051
            for offset in (-half_width, half_width):
                rib = trimesh.creation.box(extents=[x1 - x0, .012, target_z - (top + spec["segment_tray_thickness_m"])] )
                rib.apply_translation([(x0 + x1) / 2, yc + offset, (target_z + top + spec["segment_tray_thickness_m"]) / 2])
                frames[body].append(rib)
            tray_records.append({"body": body, "pad": pad["name"], "pad_top_z_m": top,
                                 "tray_thickness_m": spec["segment_tray_thickness_m"], "rib_top_z_m": target_z,
                                 "contact_scope": "Nominal separate segment metal tray shares the actual pad top plane and joins its own frame. Pad elasticity, fastening/bond, shear and plate/rib strength are unqualified. No tray spans the forefoot/heel gap."})
    retained = [copy.deepcopy(p) for p in base["parts"] if not p["role"].startswith("primary_structure") and p["name"] not in removed_foot]
    net_rows = []
    for body, meshes in frames.items():
        result = united(meshes)
        # Preserve the explicitly modeled bore after merging the output spider.
        bores = [cylinder(j["center_world_m"], shaft["bore_radius_m"], shaft["length_m"] + .002)
                 for j in joints if j["output_body"] == body]
        if bores:
            result = trimesh.boolean.difference([result, *bores], engine="manifold")
        surface_components = result.split(only_watertight=False)
        positive_shells = [m for m in surface_components if m.volume > 1e-10]
        negative_void_shells = [m for m in surface_components if m.volume < -1e-10]
        row = part_row("isb_" + body + "_net_frame", body, result, "net_primary_structure_candidate", [.11, .13, .15, 1],
                       density_kg_m3=spec["material"]["density_kg_m3"], source_members=source_names.get(body, []),
                       gross_piece_volume_m3=sum(m.volume for m in meshes), net_union_volume_m3=result.volume,
                       connected_material_components=len(positive_shells), enclosed_void_surface_components=len(negative_void_shells),
                       connection_scope="Nominal same-body material union. Weld/flange/fastener qualification and disconnected mounting details remain open.")
        retained.append(row)
        net_rows.append({"body": body, "volume_m3": result.volume, "mass_kg": result.volume * spec["material"]["density_kg_m3"],
                         "COM_world_m": result.center_mass.tolist(), "inertia_at_COM_kg_m2": (result.moment_inertia * spec["material"]["density_kg_m3"]).tolist(),
                         "connected_components": row["internal_structure_b"]["connected_material_components"]})
    retained.extend(bearings)
    layout_path = ROOT / spec["budget_layout"]
    layout = json.loads(layout_path.read_text())
    module_records = []
    for row in layout["modules"]:
        if row["route"] not in ("common", "central_hydraulic") or row["role"] == "service_space":
            continue
        if "central_hydraulic" in row["id"] and any(k in row["id"] for k in ("fold_pitch", "ankle_pitch")):
            continue
        if row["geometry"] == "box":
            shape = trimesh.creation.box(extents=row["dimensions_m"])
        else:
            shape = trimesh.creation.cylinder(radius=row["diameter_m"] / 2, height=row["length_m"], sections=64)
            shape.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], row["axis_world"]))
        shape.apply_translation(row["center_world_m"])
        identifier = "isb_module_" + row["id"]
        retained.append(part_row(identifier, "unresolved_module_allocation", shape, "complete_module_packaging_probe", row["rgba"],
                                 A_module=row, mass_geometry_scope="Complete-module mass allowance; this solid envelope is not solid material or a selected architecture."))
        module_records.append({"id": identifier, "A_module_id": row["id"], "source_module": row})
    actuator_records = []
    compact = spec["compact_cylinder_probe"]
    for side, sign in (("left", 1), ("right", -1)):
        for name in ("fold", "ankle"):
            row = compact[name]
            off_a = np.array(row["base_relative_to_fold_m"])
            off_b = np.array(row["output_relative_to_fold_m" if name == "fold" else "output_relative_to_ankle_m"])
            off_a[1] *= sign
            off_b[1] *= sign
            a = np.array(points[side + "_fold"]) + off_a
            b = np.array(points[side + "_" + name]) + off_b
            axis = (b - a) / np.linalg.norm(b - a)
            rear = a + axis * compact["mount_eye_allowance_m"] / 2
            front = rear + axis * row["body_length_m"]
            shapes = [("body", solid_along(rear, front, row["body_width_m"], row["body_width_m"])),
                      ("rod", trimesh.creation.cylinder(radius=row["rod_m"] / 2, height=np.linalg.norm(b - axis * .025 - front), sections=64)),
                      ("rear_eye_reserve", solid_along(a, rear, .060, .060)),
                      ("output_eye_reserve", solid_along(b - axis * .025, b, .060, .060))]
            rod = shapes[1][1]
            rod.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], axis))
            rod.apply_translation((front + b - axis * .025) / 2)
            for component, shape in shapes:
                retained.append(part_row("isb_" + side + "_" + name + "_cylinder_" + component,
                                         "unresolved_coupled_cylinder_allocation", shape, "compact_cylinder_packaging_probe", [.67, .40, .14, 1],
                                         side=side, cylinder=name, component=component,
                                         mass_geometry_scope="Manufacturer dimensional body/rod and custom eye-space reserves; no uniform solid-mass inference or qualified fittings."))
            actuator_records.append({"id": side + "_" + name, "base_world_m": a.tolist(), "output_world_m": b.tolist(),
                                     "base_body": side + "_" + row["base_body"], "output_body": side + "_" + row["output_body"],
                                     "manufacturer_reference": "Parker CHD80/45 T 4M S100", "body_side_m": row["body_width_m"],
                                     "body_length_m": row["body_length_m"], "bare_retracted_to_thread_tip_m": row["bare_retracted_to_thread_tip_m"],
                                     "stroke_m": compact["stroke_m"], "mount_eye_allowance_m": compact["mount_eye_allowance_m"], "spatial_acceptance": False})
    armor_roles = ("armor_cover", "armor_surface")
    before = [p for p in base["parts"] if p["role"] in armor_roles]
    after = [p for p in retained if p["role"] in armor_roles]
    if before != after:
        raise ValueError("Armor changed")
    report = {"schema": "gorilla_internal_structure_candidate_v1", "robot_id": "gorilla_v0_1", "candidate": "internal_structure_b",
              "base_scene": spec["base_scene"], "base_scene_sha256": sha(base_path), "spec_path": str(args.spec.relative_to(ROOT)),
              "spec_sha256": sha(args.spec), "builder_sha256": sha(Path(__file__)), "coordinate_frame": "SI; +X front, +Y left, +Z up",
              "parts": retained, "joint_supports": joints, "net_frame_rows": net_rows,
              "budget_layout_sha256": sha(layout_path), "context_module_probes": module_records,
              "coupled_cylinder_probes": actuator_records, "selected_route": None,
              "replaced_unqualified_socket_names": replaced, "armor_exact_copy_count": len(before),
              "replaced_foot_part_names": sorted(removed_foot),
              "separate_segment_trays": tray_records,
              "steel_net_frame_mass_kg": sum(r["mass_kg"] for r in net_rows),
              "bearing_reference_mass_kg": len(bearings) * bearing["mass_kg"],
              "stable_physical_contract": False, "geometry_accepted": False, "physics_accepted": False,
              "scope": "New nominal same-body material geometry and paired output supports. Original armor exact. Bearing envelopes are not steel solids. Actuators/module assumptions remain separate; fit, joints, sweep, contact, fatigue and thermal gates are not accepted."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "net_frame_kg": report["steel_net_frame_mass_kg"],
                      "bearing_kg": report["bearing_reference_mass_kg"], "supports": len(joints),
                      "disconnected_bodies": {r["body"]: r["connected_components"] for r in net_rows if r["connected_components"] != 1}}))


if __name__ == "__main__":
    main()
