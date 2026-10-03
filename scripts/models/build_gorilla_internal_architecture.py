#!/usr/bin/env python3
"""Place complete-module sizing envelopes against the saved Gorilla C15 stage.

These are competing packaging probes, not selected actuators or a physical ABI.
OEM meshes, when locally available, replace spatial calibrators only.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/gorilla_v0_1"
BASE = ROOT / "experiments/gorilla_v0_1/appearance_c_round_fifteen"
# Optional local OEM geometry is explicitly versioned even when it is absent.
# Default envelopes must rebuild identically on a clean checkout without OEM CAD.
OEM_REFS = {
    "battery": {
        "path": "artifacts/gorilla_v0_1/internal_module_sources/imported_geometry/victron_ng_25_6v100ah_local_m.obj",
        "sha256": "0c0c599e9de3330ef3a469c4133f09538eec595513e8f4bbfa2c7d1f30ccaebe",
    },
    "wrist": {
        "path": "artifacts/gorilla_v0_1/internal_module_sources/imported_geometry/cubemars_ak80_64_local_m.obj",
        "sha256": "20558642a5536e6ec8c70320ba406fe3d97190557c1efec5c8e8a4ec9caae50a",
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec_path = ROBOT / "configs/internal_architecture_a_spec.json"
    spec = json.loads(spec_path.read_text())
    scene_path = ROOT / spec["base_scene"]
    scene = json.loads(scene_path.read_text())
    geometry_path = ROOT / spec["base_geometry_spec"]
    if sha(scene_path) != spec["base_scene_sha256"] or sha(geometry_path) != scene["spec_sha256"]:
        raise ValueError("C15 source binding changed")
    points = json.loads(geometry_path.read_text())["points_world_m"]
    modules = []
    palette = {
        "drive": [.67, .40, .14, 1], "energy": [.20, .57, .34, 1],
        "thermal": [.18, .56, .68, 1], "compute": [.48, .35, .62, 1],
        "connections": [.40, .42, .46, 1], "service": [.85, .60, .25, .3],
    }

    def add(identifier, family, category, center, *, route="common", dimensions=None,
            diameter=None, length=None, axis=(0, 0, 1), units=1, role="complete_module_envelope",
            basis="Sizing assumption; no complete product, fit or continuous capability acceptance."):
        masses = np.asarray(spec["module_classes"][family]["mass_range_kg"]) * units if family else np.zeros(3)
        row = {"id": "ia_" + identifier, "label": identifier.replace("_", " "),
               "family": family, "category": category, "route": route,
               "role": role, "budget_units": units, "mass_range_kg": masses.tolist(),
               "center_world_m": list(center), "rgba": palette[category], "basis": basis,
               "physical_mass_assigned": False, "inside_shell_verified": False}
        if dimensions is not None:
            row.update(geometry="box", dimensions_m=list(dimensions))
        else:
            vector = np.asarray(axis, float)
            row.update(geometry="cylinder", diameter_m=diameter, length_m=length,
                       axis_world=(vector / np.linalg.norm(vector)).tolist())
        modules.append(row)
        return row

    # Four vertical battery envelopes occupy the rear torso, leaving the center
    # spine and both front intake paths identifiable. Dimensions are the actual
    # imported benchmark bounds, not an invented smaller battery.
    for side, sign in (("left", 1), ("right", -1)):
        for level, z in (("lower", 1.965), ("upper", 2.325)):
            battery = add(side + "_" + level + "_battery_volume", "energy_system", "energy",
                          (-.29, sign * .16, z), dimensions=(.160260794060, .235795325916, .341202481542), units=.225,
                          basis="Generic HV energy-volume allocation, benchmarked against Victron NG CAD. Its SKU, 25.6 V wiring and mass are not selected. Four benchmark units cannot be wired in four-series.")
            battery.update(source_geometry_local_path=OEM_REFS["battery"]["path"],
                           source_geometry_sha256=OEM_REFS["battery"]["sha256"],
                           source_geometry_rotation_euler_rad=[-math.pi / 2, -math.pi / 2, 0])
        add(side + "_battery_removal_space", None, "service", (-.59, sign * .16, 2.145),
            dimensions=(.30, .255, .72), units=0, role="service_space",
            basis="Rear removal workspace only. Door aperture and the full extraction path are not proven.")
        # Separate core, fan and bend space. A fan box is not a rated flow curve.
        add(side + "_heat_exchanger", "thermal_system", "thermal", (.13, sign * .32, 2.17),
            dimensions=(.12, .14, .27), units=.25,
            basis="Liquid-to-air core volume behind the AA3 intake; heat rejection and pressure drop unqualified.")
        add(side + "_radiator_fan", "thermal_system", "thermal", (.025, sign * .32, 2.17),
            dimensions=(.07, .14, .14), units=.08)
        duct = add(side + "_rear_exhaust_duct", "thermal_system", "thermal", (-.195, sign * .345, 2.17),
                   dimensions=(.37, .09, .14), units=.06, role="connection_route",
                   basis="Air-path reservation from fan to rear-side outlet; not an actual sealed duct or CFD solution.")
        duct["path_world_m"] = [[.32, sign * .32, 2.17], [.13, sign * .32, 2.17],
                                [.025, sign * .32, 2.17], [-.38, sign * .345, 2.17]]

    add("power_protection_precharge_regeneration", "energy_system", "energy", (.02, 0, 1.89),
        dimensions=(.18, .23, .15), units=.10,
        basis="HV protection, BMS, contactors/precharge and braking-energy interface included in energy mass budget; not a circuit or selected voltage.")
    add("coolant_pump", "thermal_system", "thermal", (.055, -.12, 2.435),
        dimensions=(.13, .13, .10), units=.12)
    add("coolant_reservoir_and_manifold", "thermal_system", "thermal", (.06, .13, 2.435),
        dimensions=(.12, .12, .10), units=.10)
    add("task_compute_and_storage", "compute_sensing", "compute", (-.27, 0, 2.545),
        dimensions=(.18, .23, .07), units=.40)
    add("real_time_network_and_dc_conversion", "compute_sensing", "compute", (.065, 0, 2.13),
        dimensions=(.13, .16, .10), units=.10)
    add("back_control_screen_electronics", "compute_sensing", "compute", (-.429, 0, 2.19),
        dimensions=(.025, .135, .20), units=.04,
        basis="Screen electronics behind the existing AA3 blue panel. No functional UI/control or environmental qualification.")
    add("trunk_imu", "compute_sensing", "compute", (-.025, 0, 2.27),
        dimensions=(.045, .045, .025), units=.02)
    add("front_depth_camera", "compute_sensing", "compute", (.408, 0, 2.43),
        dimensions=(.026, .124, .029), units=.04,
        basis="D455 dimensional benchmark 124 x 29 x 26 mm, 116 g. Lens window, optical axis, occlusion and range not closed.")
    add("hand_depth_camera_pair_reserve", "compute_sensing", "compute", (.07, 0, 2.03),
        dimensions=(.026, .124, .058), units=.08, role="route_reserve",
        basis="Two camera volumes reserved centrally pending actual wrist optics and wiring design.")
    add("joint_and_contact_feedback_reserve", "compute_sensing", "compute", (.05, 0, 2.33),
        dimensions=(.13, .15, .06), units=.32, role="route_reserve",
        basis="Distributed encoders, load/contact feedback and interfaces reserved in aggregate; placement and mass distribution unresolved.")
    add("power_data_harness_trunk", "harness_and_mounts", "connections", (-.02, 0, 2.05),
        dimensions=(.07, .10, .48), role="connection_route",
        basis="Aggregate harness/mount allowance. This central route does not establish every joint loop, bend radius or port.")
    add("fasteners_guards_mount_reserve", "assembly_fasteners_and_covers", "connections", (.06, 0, 1.79),
        dimensions=(.18, .46, .07), role="route_reserve",
        basis="Aggregate mass/volume reserve to be replaced with actual nonduplicated part rows.")
    # Three waist axes are architecture allocations, not a change to the old
    # experimental 47-joint observation/action contract.
    for name, center, axis in (("yaw", (0, 0, 1.77), (0, 0, 1)),
                               ("roll", (-.055, 0, 1.86), (1, 0, 0)),
                               ("pitch", (.055, 0, 1.99), (0, 1, 0))):
        add("waist_" + name, "waist_rotary", "drive", center, diameter=.26, length=.24, axis=axis)

    for side, sign in (("left", 1), ("right", -1)):
        shoulder = np.asarray(points[side + "_shoulder"])
        elbow = np.asarray(points[side + "_elbow"])
        wrist = np.asarray(points[side + "_wrist"])
        arm_axis = elbow - shoulder
        for label, center, axis in (
            ("shoulder_pitch", shoulder, (0, 1, 0)),
            ("shoulder_roll", shoulder + [.11, sign * .03, -.04], (1, 0, 0)),
            ("upper_arm_yaw", shoulder * .55 + elbow * .45, arm_axis)):
            add(side + "_" + label, "upper_arm_rotary", "drive", center,
                diameter=.26, length=.245, axis=axis,
                basis="CSG65 260 x 115 mm reducer plus provisional motor/brake/drive/support stack; interface geometry remains unverified.")
        add(side + "_elbow", "elbow_rotary", "drive", elbow, diameter=.22, length=.25, axis=(0, 1, 0))
        for label, center, axis in (("pitch", wrist + [-.015, 0, .035], (0, 1, 0)),
                                    ("roll", wrist + [.045, 0, -.02], (1, 0, 0)),
                                    ("yaw", wrist + [.015, 0, -.085], (0, 0, 1))):
            unit = add(side + "_wrist_" + label, "wrist_rotary", "drive", center,
                       diameter=.098, length=.0619, axis=axis,
                       basis="AK80-64 exact size calibrator only; 48 Nm nominal/120 Nm peak is not a selected load or thermal rating for this wrist.")
            unit.update(source_geometry_local_path=OEM_REFS["wrist"]["path"],
                        source_geometry_sha256=OEM_REFS["wrist"]["sha256"],
                        source_geometry_rotation_euler_rad=[0, -math.pi / 2, 0])
        add(side + "_hand_mechanisms", "hand_assembly", "drive", points[side + "_palm"],
            dimensions=(.13, .17, .19),
            basis="Mechanism/drive/feedback/support allocation in palm; full fingers/thumb and force distribution not represented by this box.")
        for segment, x in (("forefoot", -.077), ("heel", -.131)):
            add(side + "_" + segment + "_lock_and_feedback", "foot_lock", "drive", (x, sign * .50, .155),
                dimensions=(.045, .08, .05),
                basis="Lock-actuation/feedback allowance. C15 fixed-side support gap remains open; lock holding load and fail-safe behavior unproved.")

        hip, knee, fold, ankle = [np.asarray(points[side + "_" + key]) for key in ("hip", "knee", "fold", "ankle")]
        for route in spec["routes"]:
            # Six transverse/vertical balancing allocations common to all leg
            # routes. High-load sagittal allocations are the four Z-leg levels.
            for label, center, axis in (("hip_yaw", hip + [0, 0, .16], (0, 0, 1)),
                                       ("hip_roll", hip + [-.10, 0, .07], (1, 0, 0)),
                                       ("ankle_roll", ankle + [-.02, 0, .015], (1, 0, 0))):
                add(route + "_" + side + "_" + label, "secondary_rotary", "drive", center,
                    route=route, diameter=.26, length=.245, axis=axis)
            if route == "rotary_electric":
                for label, center in (("hip_pitch", hip), ("knee_pitch", knee), ("fold_pitch", fold), ("ankle_pitch", ankle)):
                    add(route + "_" + side + "_" + label, "high_load_rotary", "drive", center,
                        route=route, diameter=.325, length=.285, axis=(0, 1, 0),
                        basis="RV320E 325 x 125 mm/44.3 kg reducer plus assumed motor, brake, drive and support stack. Its 3136 Nm catalogue rating does not meet all coarse demands.")
            else:
                family = {"linear_electric": "high_force_electric_linear", "central_hydraulic": "hydraulic_cylinder_assembly",
                          "distributed_eha": "eha_complete"}[route]
                diameter, length = {"linear_electric": (.15, .58), "central_hydraulic": (.115 * math.sqrt(2), .603),
                                    "distributed_eha": (.19, .68)}[route]
                probes = (("hip_pitch", (hip + knee) / 2 + [-.16, 0, .06], knee - hip),
                          ("knee_pitch", (hip + knee) / 2 + [.17, 0, -.10], knee - hip),
                          ("fold_pitch", (knee + fold) / 2 + [.12, 0, 0], fold - knee),
                          ("ankle_pitch", (fold + ankle) / 2 + [-.12, 0, 0], ankle - fold))
                for label, center, axis in probes:
                    row = add(route + "_" + side + "_" + label, family, "drive", center, route=route,
                              diameter=diameter, length=length, axis=axis,
                              basis="Rejected until mounts/linkage, effective moment arm throughout sweep, retracted length and complete continuous capacity are closed. Linear/EHA dimensions are assumptions; hydraulic uses HMI80/36/200 493mm bare budget plus 110mm mounting allowance.")
                    row["stroke_m_assumption"] = .20
                    if route == "central_hydraulic":
                        row["manufacturer_bare_body_width_m"] = .115
                        row["manufacturer_bare_retracted_budget_m"] = .493
                        row["mount_length_allowance_m"] = .110
                        row["manufacturer_rectangle_corner_scope"] = "Round envelope circumscribes the 115 mm square body: diameter = 115 mm * sqrt(2). It is conservative corner space, not the OEM cylinder mesh."

    add("hydraulic_motor_pump_and_drive", "central_motor_pump", "drive", (.025, 0, 2.385),
        route="central_hydraulic", dimensions=(.28, .30, .24))
    add("hydraulic_valves_protection_filter", "central_valves", "connections", (.035, 0, 2.065),
        route="central_hydraulic", dimensions=(.19, .27, .15))
    add("hydraulic_fluid_compensation_hoses", "central_wet_system", "connections", (-.12, 0, 1.815),
        route="central_hydraulic", dimensions=(.25, .30, .20), role="route_reserve")
    add("eha_fill_service_connections", "distributed_wet_connections", "connections", (.06, 0, 2.02),
        route="distributed_eha", dimensions=(.10, .18, .12), role="route_reserve")

    # Every complete module budget is represented exactly once in each route.
    budgets = {}
    for route, expected in [("common", spec["common_modules"]), *[(k, v["modules"]) for k, v in spec["routes"].items()]]:
        actual = {}
        for row in modules:
            if row["route"] == route and row["family"]:
                actual[row["family"]] = actual.get(row["family"], 0) + row["budget_units"]
        if set(actual) != set(expected) or any(not math.isclose(actual[k], expected[k], abs_tol=1e-12) for k in actual):
            raise ValueError(f"Module count mismatch: {route}: {actual} vs {expected}")
        budgets[route] = actual
    layout = {"schema": "gorilla_internal_architecture_layout_v1", "robot_id": "gorilla_v0_1",
              "base_stage_commit": spec["base_stage_commit"], "base_scene": spec["base_scene"], "base_scene_sha256": sha(scene_path),
              "base_blend": str((BASE / "appearance_c.blend").relative_to(ROOT)), "base_blend_sha256": sha(BASE / "appearance_c.blend"),
              "geometry_spec_sha256": sha(geometry_path), "budget_spec": str(spec_path.relative_to(ROOT)), "budget_spec_sha256": sha(spec_path),
              "builder_script": str(Path(__file__).relative_to(ROOT)), "builder_script_sha256": sha(Path(__file__)),
              "coordinate_frame": "SI metres; +X front, +Y robot left, +Z up", "modules": modules, "budget_units_by_route": budgets,
              "scope": "Full-route neutral packaging probes, with gross stock retained. Collisions and capability conflicts deliberately remain visible. Aggregate reserves are not local mechanisms. Not a selected actuation architecture, net assembly, service proof or stable SI contract.",
              "selected_route": None, "geometry_accepted": False, "physics_accepted": False,
              "OEM_scope": "Local optional source CAD used as dimensional calibration, not selected wiring/capacity/mass. Raw and derived OEM polygons stay in ignored artifacts until redistribution permission is resolved."}
    output = ROBOT / "configs/internal_architecture_a_layout.json"
    output.write_text(json.dumps(layout, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output), "envelopes": len(modules), "budget_units_by_route": budgets}))


if __name__ == "__main__":
    main()
