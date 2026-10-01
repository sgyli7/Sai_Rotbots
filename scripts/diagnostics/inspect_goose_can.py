"""Finite passive capture of the selected two USB-CAN-A serial adapters.

No current/position/enable/disable commands are emitted. Optional explicit
adapter configuration uses SILENT mode; never changes motor flash or origins.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from sai_agent.goose.can_transport import WaveshareCan
from sai_agent.goose.cubemars_v3 import DisableAcknowledgement, decode_status
from sai_agent.goose.hybrid_hardware import bind_axes

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--can-a", required=True, help="Explicit serial device, preferably /dev/serial/by-id/...")
    parser.add_argument("--can-b", required=True)
    parser.add_argument("--seconds", type=float, default=5.)
    parser.add_argument("--configure-silent", action="store_true", help="Send ONLY the adapter's fixed/extended/1Mbps SILENT configuration")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0 < args.seconds <= 60 or Path(args.can_a).resolve() == Path(args.can_b).resolve():
        parser.error("Capture must be 0..60 seconds with two distinct named serial devices")
    if args.output.exists():
        parser.error("Use a fresh capture path; previous evidence will not be overwritten")
    contract_path = ROBOT / "configs/mechanical_physics_contract.json"
    layout_path = ROBOT / "hardware/stage_three_can_layout.json"
    axes = bind_axes(json.loads(contract_path.read_text()), json.loads(layout_path.read_text()))
    expected = {(a.bus, a.node_id): a.name for a in axes if a.bus != "ttl_5v"}
    buses = {}; rows = []; seen = set(); errors = []
    start = time.monotonic()
    try:
        for name, path in (("can_a", args.can_a), ("can_b", args.can_b)):
            buses[name] = WaveshareCan.open(path)
            if args.configure_silent:
                buses[name].configure(silent=True)
        start = time.monotonic()
        while time.monotonic() - start < args.seconds:
            for name, bus in buses.items():
                for frame in bus.receive():
                    row = {"bus": name, "host_receive_elapsed_s": time.monotonic() - start,
                           "arbitration_id": frame.arbitration_id, "extended": frame.extended,
                           "remote": frame.remote, "dlc": frame.dlc, "data_hex": frame.data.hex()}
                    if frame.arbitration_id >> 8 == 0x29:
                        try:
                            status = decode_status(frame)
                            row["decoded_type"] = type(status).__name__
                            row["wire_units_status"] = asdict(status)
                            endpoint = (name, status.node_id)
                            row["axis"] = expected.get(endpoint)
                            if row["axis"] is None:
                                errors.append("Unknown endpoint " + str(endpoint))
                            elif not isinstance(status, DisableAcknowledgement):
                                seen.add(endpoint)
                                if status.error_code:
                                    errors.append("Fault code " + str(status.error_code) + " on " + row["axis"])
                        except ValueError as exc:
                            row["decode_error"] = str(exc); errors.append(str(exc))
                    rows.append(row)
            time.sleep(.001)
    except Exception as exc:
        errors.append(type(exc).__name__ + ": " + str(exc))
    finally:
        for name, bus in buses.items():
            try: bus.close()
            except Exception as exc: errors.append(name + " close: " + str(exc))
    parser_stats = {name: {"invalid_packets": bus.stream.invalid_packets,
                          "discarded_bytes": bus.stream.discarded_bytes,
                          "incomplete_tail_bytes": len(bus.stream.buffer)} for name, bus in buses.items()}
    complete = len(seen) == 17 and not errors and all(
        not s["invalid_packets"] and not s["incomplete_tail_bytes"] for s in parser_stats.values())
    report = {"schema": "goose_passive_can_capture_v1", "status": "PASSIVE_CAPTURE_ONLY",
              "all_17_status_endpoints_seen_without_recorded_fault": complete,
              "axis_identity_physically_confirmed": False, "hardware_control_release": False,
              "motor_commands_sent": 0, "adapter_silent_configuration_requested": args.configure_silent,
              "elapsed_s": time.monotonic() - start, "errors": sorted(set(errors)),
              "parser": parser_stats, "missing_axes": [name for endpoint, name in expected.items() if endpoint not in seen],
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (contract_path, layout_path, Path(__file__))},
              "limitations": ["Host receipt time is not actuator sample time or measured end-to-end latency.",
                              "CAN IDs do not prove device model/firmware/physical identity.",
                              "Wire feedback does not include supply voltage or winding temperature.",
                              "Capture cannot establish drive watchdog, current/torque calibration or torque-off."],
              "frames": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "all_17_status_endpoints_seen_without_recorded_fault", "errors", "missing_axes", "motor_commands_sent")}, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
