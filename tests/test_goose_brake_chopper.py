import copy
import json
from pathlib import Path

import numpy as np
import pytest

from sai_agent.goose.brake_chopper import compare, threshold_voltage, validate_circuit

ROBOT = Path(__file__).resolve().parents[1] / "robots/Goose_V0.1"


def candidate():
    return json.loads((ROBOT / "configs/absolute_brake_chopper_candidate.json").read_text())


def test_threshold_kcl_independently_solved_as_two_node_network():
    # Unknowns are bus voltage and sense voltage; equations use conductances.
    for rt, rb, rf, ref, output, bias in [(100e3, 10700, 1.65e6, 2.5, 0, 0),
                                         (103e3, 10200, 1.7e6, 2.49, 4.8, 5e-9)]:
        matrix = np.array([[-1/rt, 1/rt + 1/rb + 1/rf], [0, 1]])
        solution = np.linalg.solve(matrix, [output/rf - bias, ref])
        assert threshold_voltage(rt, rb, rf, ref, output, bias) == pytest.approx(solution[0], rel=1e-14)
        assert solution[1] == ref


@pytest.mark.parametrize("fault", ["upstream_bias", "fixed_ldo_dnc_grounded", "wrong_reference_grade",
    "reference_output_pin", "driver_inverted", "driver_pinout_other_variant", "fet_reversed",
    "cap_reversed", "wrong_cap_voltage_sku", "feedback_wrong_node", "threshold_wrong_value",
    "duplicate_ref", "pretend_release"])
def test_pin_and_domain_faults_rejected(fault):
    x = copy.deepcopy(candidate())
    parts = {c["ref"]: c for c in x["components"]}
    if fault == "upstream_bias":
        parts["U1"]["pins"]["8"]["net"] = "UPSTREAM_BATTERY"
    elif fault == "fixed_ldo_dnc_grounded":
        parts["U1"]["pins"]["2"]["net"] = "GND"
    elif fault == "wrong_reference_grade":
        parts["U2"]["sku"] = "REF5025AIDR"
    elif fault == "reference_output_pin":
        parts["U2"]["pins"]["5"]["net"] = "REF_2V5"
    elif fault == "driver_inverted":
        parts["U4"]["pins"]["5"]["net"] = "BRAKE_REQUEST"
    elif fault == "driver_pinout_other_variant":
        parts["U4"]["pins"]["1"]["net"] = "GND"
    elif fault == "fet_reversed":
        parts["Q1"]["pins"]["1"]["net"] = "SW_RETURN"
    elif fault == "cap_reversed":
        parts["C1"]["pins"]["1"]["net"] = "GND"
    elif fault == "wrong_cap_voltage_sku":
        parts["C1"]["sku"] = "16SVPF1000M"
    elif fault == "feedback_wrong_node":
        parts["R3"]["pins"]["1"]["net"] = "GND"
    elif fault == "threshold_wrong_value":
        parts["R2"]["value"] = "12000 ohm"
    elif fault == "duplicate_ref":
        x["components"].append(copy.deepcopy(parts["U1"]))
    elif fault == "pretend_release":
        x["hardware_enable_release"] = True
    with pytest.raises(ValueError):
        validate_circuit(x)


def test_comparison_keeps_assumptions_and_mass_gap_explicit():
    contract = json.loads((ROBOT / "configs/mechanical_physics_contract.json").read_text())
    result = compare(candidate(), contract)
    assert result["response"]["qualified_delay_s"] is None
    assert result["response"]["conditional_delayed_peak_v"] < 28
    assert result["full_6s_false_trigger_margin_v"] > 0
    assert result["dump_stage"]["ideal_peak_equilibrium_v_one_open"] < 28
    assert result["capacitors"]["derated_total_rating_a_10_to_100khz_equal_sharing"] == pytest.approx(30.8)
    assert result["mass"]["existing_total_protection_and_brake_reservation_kg"] == pytest.approx(.213)
    assert result["mass"]["remaining_before_pcb_capacitors_mounts_wires_kg"] == pytest.approx(.02948)
    assert result["mass"]["installed_complete_mass_kg"] is None
    assert result["hardware_enable_release"] is False


@pytest.mark.parametrize("delay", [50e-6, 100e-6])
def test_delayed_response_does_not_inherit_ideal_pass(delay):
    x = candidate()
    x["threshold"]["full_path_response_budget_s_assumed"] = delay
    contract = json.loads((ROBOT / "configs/mechanical_physics_contract.json").read_text())
    assert compare(x, contract)["response"]["conditional_delayed_peak_v"] > 28
