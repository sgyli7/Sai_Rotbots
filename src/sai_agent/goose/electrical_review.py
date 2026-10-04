"""Offline electrical checks. These calculations cannot authorize hardware enabling."""

from __future__ import annotations

import math


def _positive(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")


def capacitor_voltage(initial_v: float, power_w: float, capacitance_f: float,
                      duration_s: float, resistance_ohm: float | None = None) -> float:
    """Exact constant injected-power solution; optional continuously enabled brake.

    C*V*dV/dt = P - V**2/R. No source absorption, parasitics, switching delay,
    current limits, or thermal limits are implicit in this ideal model.
    """
    _positive(initial_v=initial_v, capacitance_f=capacitance_f)
    if not math.isfinite(power_w) or power_w < 0:
        raise ValueError("power_w must be finite and nonnegative")
    if not math.isfinite(duration_s) or duration_s < 0:
        raise ValueError("duration_s must be finite and nonnegative")
    if resistance_ohm is None:
        square = initial_v**2 + 2 * power_w * duration_s / capacitance_f
    else:
        _positive(resistance_ohm=resistance_ohm)
        decay = math.exp(-2 * duration_s / (resistance_ohm * capacitance_f))
        square = power_w * resistance_ohm + (initial_v**2 - power_w * resistance_ohm) * decay
    return math.sqrt(max(0., square))


def response_budget_s(trigger_v: float, limit_v: float, power_w: float,
                      capacitance_f: float, esr_ohm: float = 0.) -> float:
    """Conservative delay budget with I<=P/trigger and ESR voltage allowance.

    Returns zero if this allowance already consumes the available headroom.
    This is a requirement on unverified hardware, not its response guarantee.
    """
    _positive(trigger_v=trigger_v, limit_v=limit_v, power_w=power_w,
              capacitance_f=capacitance_f)
    if not math.isfinite(esr_ohm) or esr_ohm < 0:
        raise ValueError("esr_ohm must be finite and nonnegative")
    capacitor_limit = limit_v - esr_ohm * power_w / trigger_v
    if capacitor_limit <= trigger_v:
        return 0.
    return capacitance_f * (capacitor_limit**2 - trigger_v**2) / (2 * power_w)


def validate_endpoint_map(mapping: dict, joints: list[dict], layout: dict) -> None:
    """Reject connector/domain/bus transcription faults before any harness release.

    Pin semantics here are fixed to the exact vendor mating-face pinout. Merely
    copying another JSON's pin table does not provide an independent check.
    """
    expected = {}
    for bus in layout["motor_buses"]:
        if len(bus["axes"]) != len(bus["proposed_node_ids"]):
            raise ValueError("bus axis/node count mismatch")
        if len(set(bus["proposed_node_ids"])) != len(bus["proposed_node_ids"]):
            raise ValueError("duplicate node on one bus")
        for axis, node in zip(bus["axes"], bus["proposed_node_ids"], strict=True):
            if axis in expected or not 1 <= node <= 255:
                raise ValueError("duplicate axis or invalid node")
            expected[axis] = (bus["name"], node)
    catalog = {j["name"]: j for j in joints}
    rows = mapping["endpoints"]
    if len(rows) != len(catalog) or {r["axis"] for r in rows} != set(catalog):
        raise ValueError("every active axis must occur exactly once")
    if mapping["motor_power_topology"] != "independent_star_branches":
        raise ValueError("signal chaining cannot carry whole-robot motor power")
    if mapping["can_termination_ohm_per_end"] != 120 or mapping["can_terminations_per_bus"] != 2:
        raise ValueError("each physical CAN line needs exactly two 120 ohm ends")
    for row in rows:
        name = row["axis"]
        if row["actuator"] != catalog[name]["actuator"]:
            raise ValueError("wrong actuator binding")
        if name == layout["ttl_branch"]["axis"]:
            if (row["protocol"] != "dynamixel_ttl_half_duplex"
                    or row["nominal_power_v"] != 5
                    or row["supply_domain"] != "head_5v"
                    or row["bus"] != "ttl_head" or row["node_id"] is not None
                    or row["cable_mate"] != "JST EHR-03"
                    or row["pin_nets"] != {"1": "ground", "2": "head_5v", "3": "ttl_data"}):
                raise ValueError("head TTL axis must use its separate 5V connector/domain")
        else:
            bus, node = expected[name]
            if (row["protocol"] != "cubemars_v3_can" or row["bus"] != bus
                    or row["node_id"] != node or row["supply_domain"] != "protected_motor_bus"
                    or row["allowed_operating_v"] != [15, 28]
                    or row["cable_mate"] != "AMASS XT30(2+2)-F"
                    or row["pin_nets"] != {"1": "protected_motor_bus", "2": "ground",
                                           "3": f"{bus}_l", "4": f"{bus}_h"}):
                raise ValueError("AK48 pin, domain, voltage, or CAN identity mismatch")
        if row["branch_fuse_a"] is not None or row["harness_length_m"] is not None:
            raise ValueError("endpoint review must not invent unqualified fuse/route values")
    if set(expected) != set(catalog) - {layout["ttl_branch"]["axis"]}:
        raise ValueError("CAN layout does not cover all non-TTL axes")
