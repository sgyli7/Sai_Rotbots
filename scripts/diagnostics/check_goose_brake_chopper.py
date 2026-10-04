#!/usr/bin/env python3
"""Inspect real NGSPICE output, preserve negative controls and plot waveforms."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(path, config, resistor_count):
    log = path.with_suffix(".log").read_text()
    if "Error:" in log or "ngspice-42 done" not in log:
        raise ValueError("NGSPICE did not finish a valid trace")
    x = np.loadtxt(path, skiprows=1)
    if not np.isfinite(x).all() or x[-1, 0] < .004 or np.any(np.diff(x[:, 0]) <= 0):
        raise ValueError("non-finite, incomplete or non-monotonic integration")
    p, threshold = config["power_stage"], config["threshold"]
    steady = x[x[:, 0] >= .0015]
    elapsed = steady[-1, 0] - steady[0, 0]
    cap_current = (steady[:, 1] - steady[:, 2]) / (p["cap_esr_max_ohm_at_100khz"] / p["cap_count"])
    rms_each = np.sqrt(np.trapezoid((cap_current / p["cap_count"])**2, steady[:, 0]) / elapsed)
    high = steady[:, 3] > 2.5
    rising_times = steady[1:, 0][high[1:] & ~high[:-1]]
    frequency = 1 / np.median(np.diff(rising_times)) if len(rising_times) > 2 else None
    # Energy balance on the bus, including resistor, Ron-only switch, ESR and divider draw.
    segment = x[x[:, 0] >= .001]
    time, bus, store = segment[:, 0], segment[:, 1], segment[:, 2]
    regen, resistor_current = segment[:, 6], segment[:, 7]
    current = resistor_current * resistor_count
    ron = p["mosfet_rds_at_4_5v_max_ohm"] * p["mosfet_hot_resistance_multiplier_assumed"] / p["mosfet_parallel_count"]
    dump_power = resistor_count * resistor_current**2 * p["dump_resistance_each_ohm"]
    switch_power = current**2 * ron
    esr_power = (bus-store)**2 / (p["cap_esr_max_ohm_at_100khz"] / p["cap_count"])
    divider_draw = bus * (bus-segment[:, 5]) / threshold["top_ohm"]
    injected_energy = np.trapezoid(bus * regen, time)
    dissipated = np.trapezoid(dump_power + switch_power + esr_power + divider_draw, time)
    c = p["cap_count"] * p["cap_each_f"] * (1-p["cap_tolerance_fraction"])
    stored_delta = .5*c*(store[-1]**2-store[0]**2)
    relative_error = abs(injected_energy-dissipated-stored_delta)/injected_energy
    if relative_error > .005:
        raise ValueError(f"bus energy balance error {relative_error}")
    crossed = x[x[:, 1] > 28]
    return {"samples": len(x), "duration_s": float(x[-1, 0]),
        "all_values_finite": True, "maximum_bus_voltage_v": float(x[:, 1].max()),
        "first_exceed_28v_s": float(crossed[0, 0]) if len(crossed) else None,
        "measured_median_switching_frequency_hz": float(frequency) if frequency else None,
        "ideal_equal_share_cap_rms_each_a": float(rms_each),
        "energy_window_s": [float(time[0]), float(time[-1])],
        "injected_energy_j": float(injected_energy), "dissipated_energy_j": float(dissipated),
        "stored_energy_delta_j": float(stored_delta), "relative_bus_energy_error": float(relative_error),
        "trace_sha256": sha(path), "log_sha256": sha(path.with_suffix(".log"))}, x


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    config_path = ROBOT / "configs/absolute_brake_chopper_candidate.json"
    config = json.loads(config_path.read_text())
    reports, traces, sources = {}, {}, {}
    for name in ("nominal", "one_resistor_open", "brake_disabled"):
        count = config["power_stage"]["dump_resistors_parallel"] - (name == "one_resistor_open")
        reports[name], traces[name] = inspect(args.directory / f"{name}.tsv", config, count)
        sources[f"{name}.cir"] = sha(args.directory / f"{name}.cir")
    if (reports["nominal"]["maximum_bus_voltage_v"] >= 28
            or reports["one_resistor_open"]["maximum_bus_voltage_v"] >= 28
            or reports["brake_disabled"]["maximum_bus_voltage_v"] <= 28):
        raise ValueError("positive comparison or disabled-brake negative control failed")
    evidence = {"schema": "goose_absolute_brake_behavioral_spice_v1",
        "status": "BEHAVIORAL_TRANSIENT_AND_NEGATIVE_CONTROL_PASS_NOT_HARDWARE_RELEASE",
        "simulator": "NGSPICE 42", "input_config_sha256": sha(config_path),
        "source_generator_sha256": sha(ROOT / "scripts/models/build_goose_brake_chopper.py"),
        "analysis_script_sha256": sha(Path(__file__)), "model_hashes": sources,
        "upstream_source_open_at_s": .0005, "regen_start_s": .00075,
        "scenarios": reports, "model_limits": ["pre-established ideal 5V bias/reference",
          "nominal threshold resistors; corners calculated separately", "Ron-only FET switches with approximated gate charge",
          "initial minimum capacitance and 100kHz ESR used at all frequencies", "no wire inductance or physical temperature solver",
          "no device damage model after overvoltage; disabled-brake trace only proves rejection"],
        "pcb_thermal_fault_or_hardware_release": False, "assembly_si_or_frozen_003_changed": False}
    (ROBOT / "evidence/absolute_brake_chopper_spice.json").write_text(json.dumps(evidence, indent=2)+"\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
    for name, x in traces.items():
        axes[0].plot(x[::20, 0]*1000, x[::20, 1], label=name.replace("_", " "))
    axes[0].axhline(28, color="red", ls="--", label="AK48 operating upper limit")
    axes[0].set(xlabel="Time (ms)", ylabel="Bus voltage (V)")
    axes[0].legend(loc="upper left")
    x = traces["nominal"]
    zoom = x[(x[:, 0] > .002) & (x[:, 0] < .00215)]
    axes[1].plot(zoom[:, 0]*1e6, zoom[:, 1], color="C0", label="bus")
    axes[1].set(xlabel="Time (µs)", ylabel="Nominal bus (V)")
    other = axes[1].twinx()
    other.plot(zoom[:, 0]*1e6, zoom[:, 4], color="C1", alpha=.6)
    other.set_ylabel("Behavioral gate (V)", color="C1")
    fig.suptitle("Absolute brake comparison: controlled regeneration after source disconnect\nBehavioral circuit only; PCB, timing, thermal and cold-start qualification outstanding")
    fig.savefig(ROBOT / "images/absolute_brake_chopper_waveforms.png", dpi=150)
    print(json.dumps({n: {"maximum_v": r["maximum_bus_voltage_v"],
                           "cap_rms_each_a": r["ideal_equal_share_cap_rms_each_a"],
                           "energy_error": r["relative_bus_energy_error"]}
                      for n, r in reports.items()}))


if __name__ == "__main__":
    main()
