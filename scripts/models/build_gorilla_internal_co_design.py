#!/usr/bin/env python3
"""Build C's explicit gear/motor/housing layers, without changing frozen B.

This is an assembly diagnostic, not a selected drivetrain or physical contract.
OEM constituent envelopes retain catalogue dimensions and catalogue mass.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
HELPER = ROOT / "scripts/models/build_gorilla_internal_structure.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_helper():
    definition = importlib.util.spec_from_file_location("gorilla_b_finite_mesh_helpers", HELPER)
    helper = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(helper)
    return helper


def slab(a, b, width_xz, thickness_y):
    """Finite plate along an XZ direction, with explicit Y thickness."""
    a, b = np.asarray(a), np.asarray(b)
    d = b - a
    if abs(d[1]) > 1e-8 or np.linalg.norm(d) < 1e-6:
        raise ValueError("Slab must follow a finite XZ direction")
    z = d / np.linalg.norm(d)
    y = np.array([0., 1., 0.])
    x = np.cross(y, z)
    transform = np.eye(4)
    transform[:3, :3] = np.column_stack([x, y, z])
    transform[:3, 3] = (a + b) / 2
    mesh = trimesh.creation.box(extents=[width_xz, thickness_y, np.linalg.norm(d)])
    mesh.apply_transform(transform)
    return mesh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=ROBOT / "configs/internal_structure_c_spec.json")
    parser.add_argument("--output", type=Path, default=ROBOT / "cad/source/internal_structure_c_scene.json")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    paths = {key: ROOT / spec[key] for key in ("base_scene", "previous_scene", "geometry_spec", "budget_layout", "component_references")}
    for key, path in paths.items():
        if sha(path) != spec[key + "_sha256"]:
            raise ValueError("Changed input: " + key)
    base = json.loads(paths["base_scene"].read_text())
    previous = json.loads(paths["previous_scene"].read_text())
    geometry = json.loads(paths["geometry_spec"].read_text())
    points = geometry["points_world_m"]
    helper = load_helper()
    feet = {side + "_" + body for side in ("left", "right") for body in ("foot", "forefoot_display", "heel_display")}
    frames = {}
    source_members = {}
    for p in base["parts"]:
        if p["role"] == "primary_structure_candidate" and p["body"] not in feet:
            frames.setdefault(p["body"], []).append(helper.native_mesh(p))
            source_members.setdefault(p["body"], []).append(p["name"])
    for p in previous["parts"]:
        if p["role"] == "net_primary_structure_candidate" and p["body"] in feet:
            frames.setdefault(p["body"], []).append(helper.native_mesh(p))
            source_members.setdefault(p["body"], []).append(p["name"])
    frames["right_upper_arm"] = [m.copy() for m in frames["left_upper_arm"]]
    for m in frames["right_upper_arm"]:
        m.apply_transform(np.diag([1, -1, 1, 1]))
    metadata, constituent_rows, added = [], [], []
    density = spec["material"]["density_kg_m3"]

    def native(name, body, mesh, role, color, details):
        return {"name": name, "body": body, "role": role, "vertices_world_m": mesh.vertices.tolist(),
                "faces": mesh.faces.tolist(), "color_rgba": color, "edge_bevel_m": 0,
                "internal_structure_c": details}

    def direction(body, origin):
        for p in base["parts"]:
            member = p.get("structural_member")
            if not member or p["body"] != body:
                continue
            path = np.asarray(member["centerline_world_m"])
            if np.linalg.norm(path[0] - origin) < 1e-7:
                d = path[1] - path[0]
                d[1] = 0
                return d / np.linalg.norm(d)
        raise ValueError("Missing child centerline: " + body)

    for side, mirror in (("left", 1), ("right", -1)):
        for key, parent, child in (("hip", "pelvis", "thigh"), ("knee", "thigh", "middle_shank"),
                                   ("fold", "middle_shank", "distal_shank"), ("ankle", "distal_shank", "foot")):
            parent = parent if parent == "pelvis" else side + "_" + parent
            child = side + "_" + child
            family = spec["axis_families"][key]
            gear, motor = spec["gear_components"][family["gear"]], spec["motor_components"][family["motor"]]
            origin = np.array(points[side + "_" + key], dtype=float)
            axis = np.array([0., float(mirror), 0.])
            bias = family["gear_center_axial_bias_m"]
            input_sign = family["input_side_sign"]
            gc = origin + bias * axis
            gl = gear["length_m"]
            mc = gc + input_sign * axis * (gl / 2 + spec["gear_motor_interface_gap_m"] + motor["height_m"] / 2)
            identifier = "isc_" + side + "_" + key
            gear_mesh = helper.cylinder(gc, gear["diameter_m"] / 2, gl)
            motor_mesh = helper.cylinder(mc, motor["diameter_m"] / 2, motor["height_m"])
            for layer, cm, m, mass, reference, color in (
                ("gear", gc, gear_mesh, gear["mass_kg"], gear["reference"], [.48, .48, .43, 1]),
                ("motor", mc, motor_mesh, motor["mass_kg"], motor["reference"], [.24, .30, .32, 1]),
            ):
                added.append(native(identifier + "_" + layer, parent, m, "catalogue_constituent_envelope", color,
                                    {"catalogue_reference": reference, "catalogue_mass_kg": mass,
                                     "mass_scope": "Catalogue component mass; envelope is not uniform material. Rotor/input inertia and true mass distribution unknown."}))
                constituent_rows.append({"id": identifier + "_" + layer, "body": parent, "centroid_hypothesis_world_m": cm.tolist(),
                                         "mass_range_kg": [mass] * 3, "catalogue_reference": reference,
                                         "mass_distribution_status": "Unknown; geometric center is a coarse allocation, not OEM COM/inertia."})
            clear = spec["housing"]["component_radial_clearance_m"]
            wall = spec["housing"]["radial_wall_m"]
            length = gl + 2 * spec["housing"]["axial_extension_m"]
            inner = gear["diameter_m"] / 2 + clear
            case = helper.annulus(gc, inner + wall, inner, length)
            motor_case = helper.annulus(mc, motor["diameter_m"] / 2 + clear + wall,
                                       motor["diameter_m"] / 2 + clear, motor["height_m"])
            # Cut real frame material around both full constituent envelopes.
            cutters = [helper.cylinder(gc, inner + wall + .001, length + .002),
                       helper.cylinder(mc, motor["diameter_m"] / 2 + clear + wall + .001, motor["height_m"] + .002)]
            for body in (parent, child):
                cut = []
                for m in frames[body]:
                    result = trimesh.boolean.difference([m, *cutters], engine="manifold")
                    if len(result.faces):
                        cut.append(result)
                frames[body] = cut
            frames[parent].extend([case, motor_case])
            # A finite input-side neck connects the two cases; its opening does
            # not assert a known sun-gear or rotor hub interface.
            neck_center = (gc + input_sign * axis * gl / 2 + mc - input_sign * axis * motor["height_m"] / 2) / 2
            neck = helper.annulus(neck_center, motor["diameter_m"] / 2 + clear + wall,
                                 motor["diameter_m"] / 2 + clear, spec["gear_motor_interface_gap_m"] + .0002)
            frames[parent].append(neck)
            out_sign = -input_sign
            flange_y = gc[1] + out_sign * mirror * (length / 2 + spec["output_flange"]["gap_m"] + spec["output_flange"]["width_m"] / 2)
            flange_center = np.array([origin[0], flange_y, origin[2]])
            flange = helper.annulus(flange_center, spec["output_flange"]["radius_m"], spec["output_flange"]["bore_radius_m"],
                                   spec["output_flange"]["width_m"])
            d = direction(child, origin)
            end_out = flange_center + d * spec["output_bridge"]["radial_station_m"]
            bridge = slab(flange_center + d * spec["output_flange"]["bore_radius_m"], end_out,
                          spec["output_bridge"]["width_xz_m"], spec["output_bridge"]["thickness_y_m"])
            end_in = origin + d * spec["output_bridge"]["radial_station_m"]
            cross = helper.box_tube(end_out, end_in, .060, .060, .006)
            frames[child].extend([flange, bridge, cross])
            # The brake/driver/encoder/input-connection allowance is explicit,
            # not disguised as validated contents of the motor or gear.
            reserve_center = mc + input_sign * axis * (motor["height_m"] / 2 + .028)
            reserve_mesh = trimesh.creation.box(extents=spec["auxiliary_installation_reserve"]["dimensions_xyz_m"])
            reserve_mesh.apply_translation(reserve_center)
            added.append(native(identifier + "_auxiliary_installation_reserve", parent, reserve_mesh,
                                "unqualified_installation_reserve", [.48, .35, .22, 1],
                                {"mass_range_kg": spec["auxiliary_installation_reserve"]["mass_range_kg"],
                                 "includes": ["brake", "driver", "encoder", "input connection", "fittings/fastening"],
                                 "scope": "Coarse complete remainder reservation, neither sourced SKU nor proven sufficiency. Full leads/assembly access and cooling remain open."}))
            constituent_rows.append({"id": identifier + "_auxiliary_installation_reserve", "body": parent,
                                     "centroid_hypothesis_world_m": reserve_center.tolist(),
                                     "mass_range_kg": spec["auxiliary_installation_reserve"]["mass_range_kg"],
                                     "mass_distribution_status": "Unqualified whole remainder mass and centroid hypotheses."})
            metadata.append({"id": side + "_" + key, "center_world_m": origin.tolist(), "axis_world": axis.tolist(),
                             "parent_body": parent, "output_body": child, "gear_center_world_m": gc.tolist(),
                             "motor_center_world_m": mc.tolist(), "gear_family": family["gear"], "motor_family": family["motor"],
                             "ratio": family["ratio"], "catalogue_gear_rated_Nm": gear["rated_Nm"],
                             "catalogue_motor_Ts_Nm": motor["Ts_Nm"], "catalogue_motor_Tc_Nm": motor["Tc_Nm"],
                             "nmax_at_Tc_and_Umax_rpm": motor["nmax_at_Tc_and_Umax_rpm"],
                             "OEM_integrated_output_bearing_counted_once": True,
                             "scope": "Eight sagittal constituent layouts, not complete 47-axis mechanism. Fixed/output housing attachment, gear interfaces, preload, seal, brake and thermal qualification remain open."})

    removed = []
    parts = []
    leg_prefixes = tuple(side + "_" + key + "_" for side in ("left", "right") for key in ("hip", "knee", "fold", "ankle"))
    # Preserve original armor, contacts, hand visuals and unrelated visual parts.
    # Old sagittal decorative motors are physically replaced, not hidden later.
    for p in base["parts"]:
        if p["role"].startswith("primary_structure") or (p["role"] == "visible_mechanism" and p["name"].startswith(leg_prefixes)):
            removed.append(p["name"])
        else:
            parts.append(copy.deepcopy(p))
    net_rows = []
    for body, meshes in frames.items():
        net = helper.united(meshes)
        components = net.split(only_watertight=False)
        details = {"density_kg_m3": density, "net_union_volume_m3": net.volume,
                   "positive_material_surface_components": int(sum(c.volume > 1e-10 for c in components)),
                   "negative_void_surface_components": int(sum(c.volume < -1e-10 for c in components)),
                   "source_members": source_members.get(body, []),
                   "connection_scope": "Nominal material only; disconnected islands, mounting/load transfer, strength/fatigue remain red-line unknown."}
        parts.append(native("isc_" + body + "_net_frame", body, net, "net_primary_structure_candidate", [.12, .14, .16, 1], details))
        net_rows.append({"body": body, "volume_m3": net.volume, "mass_kg": net.volume * density,
                         "COM_world_m": net.center_mass.tolist(), "inertia_at_COM_kg_m2": (net.moment_inertia * density).tolist(),
                         "connected_material_components": details["positive_material_surface_components"]})
    parts.extend(added)
    layout = json.loads(paths["budget_layout"].read_text())
    context = []
    for row in layout["modules"]:
        # Single rotary route. Its six non-sagittal leg and upper/waist/hand
        # allocations are still unresolved; no hydraulic system is retained.
        if row["route"] not in ("common", "rotary_electric") or row["role"] == "service_space":
            continue
        if row["route"] == "rotary_electric" and row["family"] == "high_load_rotary":
            continue
        m = trimesh.creation.box(extents=row["dimensions_m"]) if row["geometry"] == "box" else trimesh.creation.cylinder(radius=row["diameter_m"] / 2, height=row["length_m"], sections=64)
        if row["geometry"] == "cylinder":
            m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], row["axis_world"]))
        m.apply_translation(row["center_world_m"])
        name = "isc_context_" + row["id"]
        parts.append(native(name, "unresolved_module_allocation", m, "complete_module_packaging_probe", row["rgba"], {"A_module": row}))
        context.append({"id": name, "source_module": row})
    armor = [p for p in base["parts"] if p["role"] in ("armor_cover", "armor_surface")]
    if armor != [p for p in parts if p["role"] in ("armor_cover", "armor_surface")]:
        raise ValueError("Original armor changed")
    report = {"schema": "gorilla_internal_structure_candidate_v1", "robot_id": "gorilla_v0_1", "candidate": "internal_structure_c",
              "base_scene": spec["base_scene"], "base_scene_sha256": sha(paths["base_scene"]),
              "spec_path": str(args.spec.relative_to(ROOT)), "spec_sha256": sha(args.spec),
              "builder_path": str(Path(__file__).relative_to(ROOT)), "builder_sha256": sha(Path(__file__)),
              "helper_path": str(HELPER.relative_to(ROOT)), "helper_sha256": sha(HELPER),
              "previous_scene": spec["previous_scene"], "previous_scene_sha256": sha(paths["previous_scene"]),
              "budget_layout_sha256": sha(paths["budget_layout"]), "coordinate_frame": "SI; +X front, +Y left, +Z up",
              "parts": parts, "joint_supports": metadata, "net_frame_rows": net_rows,
              "catalogue_constituent_and_auxiliary_rows": constituent_rows, "context_module_probes": context,
              "removed_original_part_names": removed, "armor_exact_copy_count": len(armor),
              "steel_net_frame_mass_kg": sum(r["mass_kg"] for r in net_rows), "selected_route": None,
              "explored_route": "rotary_electric_constituent_layout_probe",
              "stable_physical_contract": False, "geometry_accepted": False, "physics_accepted": False,
              "scope": "Actual finite C housing/bridge material and eight separate OEM gear/motor component layouts. Other axes/core retain explicit unqualified A reserves. No complete fit, continuous output, dynamic or physical approval."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"scene": str(args.output), "parts": len(parts), "net_steel_kg": report["steel_net_frame_mass_kg"],
                      "frame_material_components": {r["body"]: r["connected_material_components"] for r in net_rows}}))


if __name__ == "__main__":
    main()
