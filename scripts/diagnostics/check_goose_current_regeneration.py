"""Current-model conditional braking envelope; no unproven DC/thermal release."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    contract_path = ROBOT / "configs/mechanical_physics_contract.json"
    contract = json.loads(contract_path.read_text())
    rows = []
    for joint in contract["joints"]:
        rows.append({"axis": joint["name"], "branch": "ttl_5v" if joint["name"] == "head_roll" else "main_motor_bus",
                     "continuous_limit_nm": joint["continuous_design_limit_nm"],
                     "peak_limit_nm": joint["torque_peak_limit_nm"], "speed_limit_rad_s": joint["speed_limit_rad_s"],
                     "continuous_absolute_mechanical_w": joint["continuous_design_limit_nm"] * joint["speed_limit_rad_s"],
                     "peak_absolute_mechanical_w": joint["torque_peak_limit_nm"] * joint["speed_limit_rad_s"]})
    continuous = sum(r["continuous_absolute_mechanical_w"] for r in rows if r["branch"] == "main_motor_bus")
    peak = sum(r["peak_absolute_mechanical_w"] for r in rows if r["branch"] == "main_motor_bus")
    # Retained stage-two loaded-voltage assumption, not a confirmed A2 range.
    v_low, v_high = 20., 25.2 + 2.5
    intervals = []
    for kind, power in (("continuous_axis_limits", continuous), ("peak_axis_limits", peak)):
        for cooling, current in (("free_air_at_25c", 20.), ("heatspreader", 40.), ("at_most_3_second_peak", 80.)):
            lower = v_high/current
            upper = v_low**2/power
            intervals.append({"axis_envelope": kind, "cooling_condition": cooling,
                "brake_current_condition_a": current, "ideal_resistance_min_ohm": lower,
                "ideal_resistance_max_ohm": upper, "nonempty_ideal_interval": lower <= upper,
                "component_or_installed_thermal_release": False})
    evidence_path = ROBOT / "evidence/supported_manipulation_cycle_contract_constant_pitch.json"
    evidence = json.loads(evidence_path.read_text())
    trajectory_path = ROOT / "artifacts/Goose_V0.1/supported_manipulation_cycle_contract_constant_pitch/sampled_qpos.npz"
    task_path = trajectory_path.parent / "task.xml"
    if sha(trajectory_path) != evidence["sampled_qpos_sha256"] or sha(task_path) != evidence["task_xml_sha256"]:
        raise ValueError("Recorded motion identity mismatch")
    model = mujoco.MjModel.from_xml_path(str(task_path)); data = mujoco.MjData(model)
    recorded = np.load(trajectory_path)
    energies = []
    for time_s, qpos in zip(recorded["time_s"], recorded["qpos"], strict=True):
        data.qpos[:] = qpos
        mujoco.mj_forward(model, data)
        # This is gravitational potential from recorded geometry only; sampled
        # qpos contains neither control torques nor adequately sampled qvel.
        potential = -float(np.sum(model.body_mass[:, None] * data.xipos * model.opt.gravity))
        energies.append({"time_s": float(time_s), "gravity_potential_j": potential})
    values = np.array([r["gravity_potential_j"] for r in energies])
    report = {"schema": "goose_current_conditional_regeneration_envelope_v1",
        "status": "CONDITIONAL_MECHANICAL_REQUIREMENTS_NOT_BRAKE_RELEASE",
        "main_motor_bus_continuous_mechanical_envelope_w": continuous,
        "main_motor_bus_peak_mechanical_envelope_w": peak,
        "ttl_5v_continuous_mechanical_envelope_w": next(r["continuous_absolute_mechanical_w"] for r in rows if r["branch"] == "ttl_5v"),
        "positive_contract_limit_w": contract["positive_mechanical_power_limit_w"],
        "positive_limit_does_not_limit_negative_power": True, "axis_envelopes": rows,
        "resistor_voltage_scenario_v": [v_low, v_high], "voltage_scenario_confirmed_for_A2": False,
        "ideal_resistor_intervals": intervals,
        "scenario_80mm_whole_robot_drop_energy_j": contract["nominal_robot_mass_kg"] * 9.81 * .08,
        "scenario_2200uf_cap_24v_to_25_2v_energy_j": .5 * .0022 * (25.2**2 - 24.**2),
        "legacy_12j_reserve_is_complete_stop_energy_bound": False,
        "recorded_task_gravity": {"poses": len(energies), "minimum_j": float(values.min()),
            "maximum_j": float(values.max()), "range_j": float(np.ptp(values)),
            "sampled_cumulative_decrease_j": float(np.maximum(-np.diff(values), 0).sum()),
            "measured_electrical_regeneration": False, "complete_braking_energy_bound": False,
            "records": energies},
        "controller_envelope_physically_verified": False,
        "standstill_copper_loss_bounded": False, "uncontrolled_drive_disable_braking_bounded": False,
        "total_stop_kinetic_and_magnetic_energy_bounded": False,
        "battery_direct_connection_released": False, "regen_clamp_and_resistor_selected": False,
        "hardware_freeze": False, "stage_three_four_complete": False,
        "primary_clamp_source": "https://docs.odriverobotics.com/v/latest/hardware/regen-clamp-datasheet.html",
        "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in
            (contract_path, evidence_path, trajectory_path, task_path, Path(__file__))},
        "limits": ["Sum |torque limit|*|speed limit| bounds controlled shaft power only while both limits remain enforced; it is not a verified motor DC input/regen bound.",
            "Peak and continuous model limits are engineering candidates, not confirmed enclosed static thermal performance.",
            "Resistance intervals assume 20..27.7V and ideal lossless absorption; include resistor tolerance, pulse energy, duty and actual housing temperature before selection.",
            "80A brake condition is peak-only, at most three seconds; do not substitute it for continuous heatspreader/free-air limits.",
            "Full battery/disconnected input, overshoot and thermal protection disabling the clamp require separate failure analysis.",
            "TTL 5V regeneration cannot be assumed to flow through a non-bidirectional buck to the main clamp.",
            "199 recorded qpos samples permit gravity-energy inspection, not torque/velocity peaks or electrical braking measurement."]}
    (ROBOT / "evidence/current_regeneration_envelope.json").write_text(json.dumps(report, indent=2) + "\n")
    print("CURRENT REGEN", round(continuous, 3), "W continuous envelope;", round(peak, 3), "W peak envelope;",
          len(energies), "recorded gravity poses; no electrical release")


if __name__ == "__main__":
    main()
