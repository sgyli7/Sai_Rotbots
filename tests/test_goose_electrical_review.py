import copy
import json
import math
from pathlib import Path

import pytest
from scipy.integrate import solve_ivp

from sai_agent.goose.electrical_review import (capacitor_voltage, response_budget_s,
                                               validate_endpoint_map)

ROOT = Path(__file__).resolve().parents[1]
ROBOT = ROOT / "robots/Goose_V0.1"


def load(path):
    return json.loads((ROBOT / path).read_text())


def endpoints():
    return (load("hardware/current_actuator_endpoints.json"),
            load("configs/mechanical_physics_contract.json")["joints"],
            load("hardware/stage_three_can_layout.json"))


def test_offline_endpoint_map_covers_can_and_separate_ttl():
    mapping, joints, layout = endpoints()
    validate_endpoint_map(mapping, joints, layout)
    assert len(mapping["endpoints"]) == 18
    assert sum(r["bus"] == "can_a" for r in mapping["endpoints"]) == 9
    assert sum(r["bus"] == "can_b" for r in mapping["endpoints"]) == 8
    assert mapping["hardware_release"] is False


@pytest.mark.parametrize("fault", ["can_h_l_swapped", "power_polarity_swapped",
    "ttl_on_24v", "ttl_on_can", "wrong_motor", "wrong_node", "missing_axis",
    "repeated_axis", "whole_robot_power_chain", "three_terminations",
    "old_driver_voltage", "unqualified_fuse"])
def test_rejects_harness_faults_before_release(fault):
    original, joints, layout = endpoints()
    mapping = copy.deepcopy(original)
    ak = next(r for r in mapping["endpoints"] if r["axis"] == "neck_pitch")
    ttl = next(r for r in mapping["endpoints"] if r["axis"] == "head_roll")
    if fault == "can_h_l_swapped":
        ak["pin_nets"]["3"], ak["pin_nets"]["4"] = ak["pin_nets"]["4"], ak["pin_nets"]["3"]
    elif fault == "power_polarity_swapped":
        ak["pin_nets"]["1"], ak["pin_nets"]["2"] = ak["pin_nets"]["2"], ak["pin_nets"]["1"]
    elif fault == "ttl_on_24v":
        ttl["nominal_power_v"] = 24
    elif fault == "ttl_on_can":
        ttl["protocol"] = "cubemars_v3_can"
    elif fault == "wrong_motor":
        ak["actuator"] = "ak40_10_v3"
    elif fault == "wrong_node":
        ak["node_id"] = 9
    elif fault == "missing_axis":
        mapping["endpoints"].pop()
    elif fault == "repeated_axis":
        mapping["endpoints"][-1] = copy.deepcopy(mapping["endpoints"][0])
    elif fault == "whole_robot_power_chain":
        mapping["motor_power_topology"] = "daisy_chain"
    elif fault == "three_terminations":
        mapping["can_terminations_per_bus"] = 3
    elif fault == "old_driver_voltage":
        ak["allowed_operating_v"] = [18, 52]
    elif fault == "unqualified_fuse":
        ak["branch_fuse_a"] = 40
    with pytest.raises(ValueError):
        validate_endpoint_map(mapping, joints, layout)


def test_capacitor_energy_balance_without_brake():
    c, power, dt, start = .00176, 890.4291283123216, 50e-6, 27.7
    end = capacitor_voltage(start, power, c, dt)
    assert .5 * c * (end**2 - start**2) == pytest.approx(power * dt, abs=1e-15)
    assert end > 28  # this declared delay alone exceeds the exact AK48 operating window
    assert capacitor_voltage(start, 0, c, dt) == start


def test_brake_solution_matches_independent_numerical_integration_and_energy():
    c, power, r, start, dt = .00176, 890.4291283123216, .7575, 22.5, .01
    # Independently integrate voltage and resistor energy, rather than the closed form.
    solution = solve_ivp(lambda t, y: [(power - y[0]**2/r)/(c*y[0]), y[0]**2/r],
                         [0, dt], [start, 0.], rtol=1e-10, atol=1e-11)
    assert solution.success
    numeric_v, dump_energy_j = solution.y[:, -1]
    analytic = capacitor_voltage(start, power, c, dt, r)
    assert analytic == pytest.approx(numeric_v, rel=1e-9)
    assert .5*c*(analytic**2-start**2)+dump_energy_j == pytest.approx(power*dt, rel=1e-9)
    assert analytic < 28
    # Low-voltage complete absorption is sufficient, but is not required for a safe equilibrium.
    assert power > start**2/r
    assert math.sqrt(power*r) < 28


def test_zero_injected_power_discharge_and_response_budget():
    assert capacitor_voltage(26, 0, .0022, .001, .75) == pytest.approx(
        26 * math.exp(-.001/(.75*.0022)))
    c, p = .00176, 890.4291283123216
    budget = response_budget_s(27.7, 28, p, c)
    assert capacitor_voltage(27.7, p, c, budget) == pytest.approx(28)
    assert budget == pytest.approx(16.514284553865434e-6)
    # A separate conservative ESR reserve can exhaust this narrow headroom.
    assert response_budget_s(27.7, 28, p, c, .01) == 0
    assert response_budget_s(26, 28, p, c, .01) > 80e-6


@pytest.mark.parametrize("bad", [math.nan, math.inf, -1.])
def test_no_invalid_power_or_negative_resistance(bad):
    with pytest.raises(ValueError):
        capacitor_voltage(24, bad, .0022, .001)
    with pytest.raises(ValueError):
        response_budget_s(26, 28, 800, .0022, bad)
    with pytest.raises(ValueError):
        capacitor_voltage(24, 800, .0022, .001, bad)


def test_vendor_nominal_fields_cannot_become_a_physical_enable_profile():
    facts = load("hardware/ak48_v1_11_electrical_facts.json")
    assert facts["applicability"]["hardware_revision"] == "V1.11"
    assert facts["driver"]["allowed_operating_v"] == [15, 28]
    catalog = facts["nominal_protocol_catalog"]
    assert catalog["physical_commissioned_profiles_created"] is False
    assert catalog["hardware_watchdog_timeout_s"] is None
    # Selected KV variants, not legacy examples; torque field limits are not thermal ratings.
    assert {key: row["nominal_output_kt_nm_per_iq_a"] for key, row in catalog["models"].items()} == {
        "ak40_10_v3": .4894, "ak45_10_v3": 1.1286, "ak45_36_v3": 3.9790}
    assert facts["hardware_release"] is False


def test_current_hardware_endpoint_identity_preserves_physical_inputs():
    import hashlib
    mapping, _, _ = endpoints()
    for path, digest in mapping["source_hashes"].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    assert mapping["parts"] == 478
