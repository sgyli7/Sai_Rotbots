#!/usr/bin/env python3
"""Derive the current harness endpoints and conditional brake requirements offline."""

import csv
import hashlib
import json
from pathlib import Path

from sai_agent.goose.electrical_review import (capacitor_voltage, response_budget_s,
                                               validate_endpoint_map)

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"


def read(relative):
    return json.loads((ROOT / relative).read_text())


def sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def build():
    paths = ["robots/Goose_V0.1/configs/mechanical_physics_contract.json",
             "robots/Goose_V0.1/hardware/stage_three_can_layout.json",
             "robots/Goose_V0.1/hardware/ak48_v1_11_electrical_facts.json",
             "robots/Goose_V0.1/evidence/manual_wing_service_parameters.json",
             "robots/Goose_V0.1/cad/source/manual_wing_service/assembly_scene.json"]
    contract, layout, facts, parameters = map(read, paths[:4])
    if parameters["neutral_joint_order"] != contract["joint_order"]:
        raise ValueError("current hardware and historical joint order differ")
    for joint in contract["joints"]:
        if parameters["pivots_world_at_zero_m"][joint["name"]] != joint["pivot_world_at_zero_m"]:
            raise ValueError("current hardware changed a joint pivot")
    identity = {p: sha(p) for p in paths}
    identity["src/sai_agent/goose/electrical_review.py"] = sha("src/sai_agent/goose/electrical_review.py")
    identity["scripts/diagnostics/check_goose_electrical_endpoints.py"] = sha(
        "scripts/diagnostics/check_goose_electrical_endpoints.py")
    by_axis = {axis: (bus["name"], node) for bus in layout["motor_buses"]
               for axis, node in zip(bus["axes"], bus["proposed_node_ids"], strict=True)}
    mapping = {"schema": "goose_current_hardware_endpoint_map_v1",
               "status": "PIN_AND_DOMAIN_REVIEW_NOT_MANUFACTURING_HARNESS_RELEASE",
               "parts": parameters["parts"], "active_axes": parameters["active_axes"],
               "source_hashes": identity,
               "motor_power_topology": "independent_star_branches",
               "can_termination_ohm_per_end": 120, "can_terminations_per_bus": 2,
               "pin_view": facts["motor_connector"]["pin_view"],
               "hardware_release": False, "endpoints": []}
    requirements = []
    for joint in contract["joints"]:
        axis = joint["name"]
        common = {"axis": axis, "actuator": joint["actuator"],
                  "branch_fuse_a": None, "harness_length_m": None}
        if axis == "head_roll":
            row = {**common, "protocol": "dynamixel_ttl_half_duplex", "bus": "ttl_head",
                   "node_id": None, "supply_domain": "head_5v", "nominal_power_v": 5,
                   "cable_mate": facts["head_ttl"]["cable_mate"],
                   "pin_nets": {"1": "ground", "2": "head_5v", "3": "ttl_data"}}
        else:
            bus, node = by_axis[axis]
            row = {**common, "protocol": "cubemars_v3_can", "bus": bus, "node_id": node,
                   "supply_domain": "protected_motor_bus",
                   "allowed_operating_v": facts["driver"]["allowed_operating_v"],
                   "cable_mate": facts["motor_connector"]["cable_mate"],
                   "pin_nets": {"1": "protected_motor_bus", "2": "ground",
                                "3": f"{bus}_l", "4": f"{bus}_h"}}
            key = joint["actuator"].removesuffix("_parallel_crank_1_to_1")
            nominal = facts["nominal_protocol_catalog"]["models"][key]
            bounds = facts["nominal_protocol_catalog"]["position_rad"]
            within = (max(abs(v) for v in joint["range_rad"]) <= max(bounds)
                      and joint["speed_limit_rad_s"] <= nominal["velocity_rad_s"][1]
                      and joint["torque_peak_limit_nm"] <= nominal["torque_nm"][1])
            if not within:
                raise ValueError(f"{axis} exceeds exact nominal protocol field range")
            requirements.append({"axis": axis, "model": nominal["model"],
                "nominal_catalog_current_for_continuous_design_torque_a":
                    joint["continuous_design_limit_nm"] / nominal["nominal_output_kt_nm_per_iq_a"],
                "nominal_catalog_current_for_peak_design_torque_a":
                    joint["torque_peak_limit_nm"] / nominal["nominal_output_kt_nm_per_iq_a"],
                "within_documented_protocol_ranges": within,
                "physical_calibration_or_thermal_capacity_proven": False})
        mapping["endpoints"].append(row)
    validate_endpoint_map(mapping, contract["joints"], layout)
    power = {kind: sum(j[key] * j["speed_limit_rad_s"] for j in contract["joints"]
                      if j["name"] != "head_roll")
             for kind, key in [("continuous", "continuous_design_limit_nm"),
                               ("peak", "torque_peak_limit_nm")]}
    # Deliberately declared comparisons, not newly purchased protection devices.
    capacitance = .0022 * .8
    r_min, r_max = .75 * .99, .75 * 1.01
    scenarios = []
    for name, trigger in [("full_6s_relative_clamp", 25.2 + 2.5),
                          ("23v_source_relative_clamp", 23 + 2.5),
                          ("absolute_26v_chopper_requirement", 26.)]:
        for delay in [0., .00005, .0001]:
            voltage = capacitor_voltage(trigger, power["peak"], capacitance, delay)
            esr_allowance = .01 * power["peak"] / trigger
            scenarios.append({"name": name, "trigger_v": trigger,
                "assumed_response_delay_s": delay, "ideal_capacitor_peak_v": voltage,
                "conservative_esr_voltage_allowance_v": esr_allowance,
                "terminal_voltage_bound_v": voltage + esr_allowance,
                "voltage_bound_below_28v": voltage + esr_allowance < 28,
                "delay_budget_without_esr_s": response_budget_s(trigger, 28, power["peak"], capacitance),
                "delay_budget_with_10_milliohm_esr_s": response_budget_s(
                    trigger, 28, power["peak"], capacitance, .01),
                "hardware_qualified": False})
    steady = {"resistance_ohm_nominal": .75, "resistance_tolerance_fraction_assumed": .01,
              "worst_equilibrium_v_at_peak_power": (power["peak"] * r_max)**.5,
              "worst_brake_a_at_27_7v": 27.7 / r_min,
              "peak_power_w": power["peak"], "continuous_power_w": power["continuous"],
              "average_thermal_dissipation_w": None,
              "dump_resistor_sku": None, "hardware_qualified": False,
              "meaning": "ideal steady electrical comparison; R<=Vlimit^2/P, not R<=Vlow^2/P, is the equilibrium voltage criterion"}
    evidence = {"schema": "goose_electrical_endpoint_and_brake_review_v1",
        "status": "DOCUMENT_APPLICABILITY_AND_ENDPOINT_CHECKS_PASS_PROTECTION_UNRELEASED",
        "source_hashes": identity, "active_axes": len(mapping["endpoints"]),
        "can_axes": len(requirements), "ttl_axes": 1,
        "nominal_conditional_hardware_mass_kg": parameters["nominal_conditional_mass_kg"],
        "geometry_or_si_changed": False, "endpoint_validation_pass": True,
        "protocol_field_range_review": requirements,
        "controlled_shaft_power_envelope_w": power,
        "scope": "sum of enforced torque-times-speed limits, assumed 100% converted to DC for comparison; not measured bus power or a bound on uncontrolled kinetic/magnetic energy",
        "declared_assumptions": {"external_capacitance_f_nominal": .0022,
            "capacitance_tolerance_fraction": .2, "minimum_capacitance_f": capacitance,
            "esr_ohm": .01, "source_absorption_w": 0,
            "stray_inductance_and_switching_overshoot_modelled": False,
            "clamp_onboard_capacitance_counted": False,
            "component_skus_or_response_guarantees_selected": False},
        "steady_comparison": steady, "response_scenarios": scenarios,
        "manufacturer_maximum_response_delay_s": None,
        "hardware_enable_or_training_release": False}
    return mapping, evidence


def main():
    mapping, evidence = build()
    for target, data in [(ROBOT / "hardware/current_actuator_endpoints.json", mapping),
                         (ROBOT / "evidence/electrical_endpoint_and_brake_review.json", evidence)]:
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    with (ROBOT / "hardware/current_actuator_endpoints.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["axis", "actuator", "bus", "node_id", "supply_domain", "cable_mate",
                         "pin_1_net", "pin_2_net", "pin_3_net", "pin_4_net",
                         "branch_fuse_a_unqualified", "harness_length_m_unqualified"])
        for row in mapping["endpoints"]:
            writer.writerow([row[k] for k in ["axis", "actuator", "bus", "node_id",
                                             "supply_domain", "cable_mate"]]
                            + [row["pin_nets"].get(str(n), "") for n in range(1, 5)] + ["", ""])
    print(json.dumps({"endpoint_review_pass": True, "can_axes": 17, "ttl_axes": 1,
                      "hardware_release": False, "steady": evidence["steady_comparison"],
                      "full_6s_delay_budget_s": evidence["response_scenarios"][0]["delay_budget_without_esr_s"]}))


if __name__ == "__main__":
    main()
