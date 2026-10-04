"""Circuit comparison, not an authorization to energize a motor bus.

The candidate uses absolute-voltage hysteresis. Component limits with missing
guarantees remain assumptions, even when the ideal network passes simulation.
"""

from __future__ import annotations

import itertools
import math

from .electrical_review import capacitor_voltage, response_budget_s


def threshold_voltage(top: float, bottom: float, feedback: float,
                      sense: float, output: float, bias: float = 0.) -> float:
    """KCL at sense node, with positive bias current drawn from that node."""
    if any(not math.isfinite(x) or x <= 0 for x in (top, bottom, feedback, sense)):
        raise ValueError("resistances and sense voltage must be positive and finite")
    if not math.isfinite(output) or not math.isfinite(bias):
        raise ValueError("output and bias must be finite")
    return sense * (1 + top / bottom + top / feedback) - output * top / feedback + bias * top


def validate_circuit(config: dict) -> None:
    """Independently bind critical physical pins, including deliberate DNC pins."""
    parts = config["components"]
    by_ref = {c["ref"]: c for c in parts}
    if len(by_ref) != len(parts):
        raise ValueError("duplicate reference")
    expected = {
        "U1": ("TPS7A1650DGNR", {"1": "BIAS_5V", "2": None, "3": "BIAS_PG",
                                  "4": "GND", "5": "BUS", "6": None,
                                  "7": None, "8": "BUS", "9": "GND"}),
        "U2": ("REF5025IDR", {"1": None, "2": "BIAS_5V", "3": None,
                               "4": "GND", "5": None, "6": "REF_2V5",
                               "7": None, "8": None}),
        "U3": ("TLV3201DBVR", {"1": "BRAKE_REQUEST", "2": "GND",
                                "3": "SENSE", "4": "REF_2V5", "5": "BIAS_5V"}),
        "U4": ("UCC27511DBVR", {"1": "BIAS_5V", "2": "GATE_DRIVE",
                                 "3": "GATE_DRIVE", "4": "GND", "5": "GND",
                                 "6": "BRAKE_REQUEST"}),
    }
    for ref, (sku, pins) in expected.items():
        actual = by_ref.get(ref)
        if (actual is None or actual["sku"] != sku
                or {p: n["net"] for p, n in actual["pins"].items()} != pins):
            raise ValueError(f"{ref} exact SKU/pin/domain mismatch")
    for ref, nets, key in (("R1", ("BUS", "SENSE"), "top_ohm"),
                           ("R2", ("SENSE", "GND"), "bottom_ohm"),
                           ("R3", ("BRAKE_REQUEST", "SENSE"), "feedback_ohm")):
        part = by_ref[ref]
        if (tuple(part["pins"][str(i)]["net"] for i in (1, 2)) != nets
                or float(part["value"].split()[0]) != config["threshold"][key]):
            raise ValueError("threshold network value or feedback polarity mismatch")
    stage = config["power_stage"]
    for n in range(1, stage["mosfet_parallel_count"] + 1):
        q = by_ref[f"Q{n}"]
        pins = {p: n["net"] for p, n in q["pins"].items()}
        if (q["sku"] != "BSC027N06LS5" or pins != {
                **{str(p): "GND" for p in (1, 2, 3)}, "4": f"GATE{n}",
                **{str(p): "SW_RETURN" for p in (5, 6, 7, 8)}}):
            raise ValueError("MOSFET source/gate/drain mismatch")
    for n in range(1, stage["cap_count"] + 1):
        if (by_ref[f"C{n}"]["sku"] != "35SVPF120M"
                or by_ref[f"C{n}"]["pins"]["1"]["net"] != "BUS"
                or by_ref[f"C{n}"]["pins"]["2"]["net"] != "GND"):
            raise ValueError("bulk capacitor SKU/polarity mismatch")
    for n in range(1, stage["dump_resistors_parallel"] + 1):
        if (by_ref[f"RD{n}"]["sku"] != "LTO100F4R700FTE3"
                or {v["net"] for v in by_ref[f"RD{n}"]["pins"].values()}
                != {"BUS", "SW_RETURN"}):
            raise ValueError("dump resistor SKU or path mismatch")
    if any(config[k] for k in ("hardware_enable_release", "source_si_changed", "frozen_003_changed")):
        raise ValueError("comparison cannot authorize or mutate an assembly")


def compare(config: dict, contract: dict) -> dict:
    validate_circuit(config)
    t, p, m = (config[k] for k in ("threshold", "power_stage", "mechanical_candidate"))
    shaft_power = {name: sum(j[key] * j["speed_limit_rad_s"]
                             for j in contract["joints"] if j["name"] != "head_roll")
                   for name, key in (("continuous", "continuous_design_limit_nm"),
                                     ("peak", "torque_peak_limit_nm"))}
    resistor_error = t["resistor_initial_tolerance_fraction"] + t["resistor_tcr_per_k"] * t["temperature_delta_max_k"]
    ref_error = (t["reference_initial_error_fraction"] + t["reference_tcr_per_k"] * t["temperature_delta_max_k"]
                 + t["reference_post_reflow_allowance_fraction"])
    sense_error = t["comparator_offset_max_v"] + t["comparator_intrinsic_hysteresis_allowance_v"]
    ranges = []
    for key in ("top_ohm", "bottom_ohm", "feedback_ohm"):
        ranges.append([t[key] * (1 - resistor_error), t[key] * (1 + resistor_error)])
    ranges += [[t["reference_v"] * (1 - ref_error) - sense_error,
                t["reference_v"] * (1 + ref_error) + sense_error],
               [-t["comparator_bias_max_a"], t["comparator_bias_max_a"]]]
    corners = list(itertools.product(*ranges))
    on = [threshold_voltage(a, b, f, s, o, i) for a, b, f, s, i in corners
          for o in (0., t["output_low_max_v"])]
    off = [threshold_voltage(a, b, f, s, o, i) for a, b, f, s, i in corners
           for o in (t["logic_v_range"][0] - t["output_high_drop_max_v"], t["logic_v_range"][1])]
    gain_max = max(1 + a / b + a / f for a, b, f, _, _ in corners)
    overdrive = t["switching_delay_data"]["comparator_required_input_overdrive_v"] * gain_max
    trigger = max(on) + overdrive
    cmin = p["cap_count"] * p["cap_each_f"] * (1 - p["cap_tolerance_fraction"])
    esr = p["cap_esr_max_ohm_at_100khz"] / p["cap_count"]
    peak = shaft_power["peak"]
    delayed_v = capacitor_voltage(trigger, peak, cmin, t["full_path_response_budget_s_assumed"])
    delayed_v += peak / trigger * esr
    rmin = p["dump_resistance_each_ohm"] * (1 - p["dump_resistance_tolerance_fraction"])
    rmax = p["dump_resistance_each_ohm"] * (1 + p["dump_resistance_tolerance_fraction"]
             + p["dump_resistor_tcr_per_k"] * p["dump_resistor_element_delta_max_k"])
    fet_r = p["mosfet_rds_at_4_5v_max_ohm"] * p["mosfet_hot_resistance_multiplier_assumed"]
    parallel = p["dump_resistors_parallel"]
    worst_on_current = 28 / (rmin / parallel)  # neglect FET resistance conservatively
    ripple_bound = worst_on_current / 2  # any duty cycle, ideal rectangular current
    ripple_derated = p["cap_count"] * p["cap_ripple_a_at_100khz_105c"] * p["cap_ripple_factor_10_to_100khz"]
    resistor_each_cont_w = shaft_power["continuous"] / parallel
    plate_mass = math.prod(m["flat_heat_spreader_candidate_xyz_mm"]) * 1e-9 * m["heat_spreader_density_kg_m3"]
    return {
        "status": "CONDITIONAL_CIRCUIT_COMPARISON_NOT_HARDWARE_RELEASE",
        "shaft_power_envelope_w": shaft_power,
        "power_scope": "controlled sum(torque_limit*speed_limit), not measured DC power or uncontrolled energy",
        "corner_count_each_transition": len(on),
        "threshold_nominal_v": {
            "on": threshold_voltage(t["top_ohm"], t["bottom_ohm"], t["feedback_ohm"], t["reference_v"], 0),
            "off": threshold_voltage(t["top_ohm"], t["bottom_ohm"], t["feedback_ohm"], t["reference_v"], 5)},
        "threshold_conditional_corners_v": {"on": [min(on), max(on)], "off": [min(off), max(off)]},
        "unverified_corner_allowances": ["soldered reference shift", "intrinsic comparator hysteresis", "precision resistor SKUs"],
        "full_6s_false_trigger_margin_v": min(off) - 25.2,
        "comparator_overdrive_extra_bus_v": overdrive,
        "response": {"qualified_delay_s": None,
            "assumed_whole_path_s": t["full_path_response_budget_s_assumed"],
            "trigger_plus_required_overdrive_v": trigger, "minimum_capacitance_f": cmin,
            "esr_allowance_ohm_at_100khz_only": esr, "conditional_delayed_peak_v": delayed_v,
            "budget_s_with_separate_esr_reserve": response_budget_s(trigger, 28, peak, cmin, esr),
            "condition": "no wire inductance, no uncontrolled energy, reference/bias pre-established, ESR at stated frequency"},
        "dump_stage": {
            "worst_hot_bank_resistance_ohm": rmax / parallel,
            "worst_hot_one_resistor_open_ohm": rmax / (parallel - 1),
            "ideal_peak_equilibrium_v_one_open": math.sqrt(peak * (rmax / (parallel - 1) + fet_r / p["mosfet_parallel_count"])),
            "on_current_upper_bound_at_28v_a": worst_on_current,
            "continuous_resistor_average_each_w_assumed_equal": resistor_each_cont_w,
            "maximum_case_temperature_c_for_that_average": p["dump_resistor_max_element_c"] - resistor_each_cont_w * p["dump_resistor_rth_jc_k_per_w"],
            "single_cold_0_1s_pulse_each_j": peak * .1 / parallel,
            "pulse_curve_and_repetitive_heat_qualified": False,
            "fet_each_on_loss_w_at_current_bound": (worst_on_current / p["mosfet_parallel_count"])**2 * fet_r,
            "fet_copper_geometry_and_switching_loss_qualified": False},
        "capacitors": {"rectangular_current_rms_upper_bound_total_a": ripple_bound,
            "derated_total_rating_a_10_to_100khz_equal_sharing": ripple_derated,
            "ideal_equal_sharing_bound_below_derated_rating": ripple_bound <= ripple_derated,
            "frequency_spectrum_sharing_and_thermal_qualified": False},
        "mass": {"flat_plate_kg": plate_mass,
            "dump_resistor_bank_upper_kg": parallel * p["dump_resistor_each_mass_upper_kg"],
            "plate_plus_resistor_upper_comparison_kg": plate_mass + parallel * p["dump_resistor_each_mass_upper_kg"],
            "installed_complete_mass_kg": None,
            "existing_reserved_mass_items_kg": m["existing_reserved_mass_items_kg"],
            "existing_total_protection_and_brake_reservation_kg": sum(m["existing_reserved_mass_items_kg"].values()),
            "remaining_before_pcb_capacitors_mounts_wires_kg": sum(m["existing_reserved_mass_items_kg"].values()) - plate_mass - parallel * p["dump_resistor_each_mass_upper_kg"],
            "assembly_si_changed": False},
        "hardware_enable_release": False,
    }
