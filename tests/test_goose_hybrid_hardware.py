"""Current assembly bindings and injected fault recovery, not bench validation."""
from dataclasses import replace
import json
import math
from pathlib import Path
import struct
import time

import numpy as np
import pytest

from sai_agent.goose.can_transport import CanFrame, WaveshareCan, decode_fixed, encode_fixed
from sai_agent.goose.cubemars_v3 import CommissionedAkProfile
from sai_agent.goose.hybrid_hardware import HybridTorqueSession, bind_axes, xc330_axis_spec

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def axes():
    robot = ROOT / "robots/Goose_V0.1"
    contract = json.loads((robot / "configs/mechanical_physics_contract.json").read_text())
    layout = json.loads((robot / "hardware/stage_three_can_layout.json").read_text())
    return bind_axes(contract, layout)


class MemoryPort:
    def __init__(self):
        self.output = bytearray(); self.input = bytearray(); self.fail = False
    def read(self, size):
        result = bytes(self.input[:size]); del self.input[:size]; return result
    def write(self, data):
        if self.fail: raise OSError("injected disconnected serial link")
        self.output.extend(data); return len(data)
    def close(self): pass


class TtlFixture:
    def __init__(self): self.enabled = False; self.commands = []; self.stops = 0; self.failed = False
    def validate_ready(self):
        if self.failed: raise ValueError("injected TTL preflight fault")
        return [{"joint": "head_roll", "current_limit_ticks": 360, "output_Nm_per_A": .5}]
    def arm(self): self.enabled = True
    def disarm(self): self.enabled = False; self.stops += 1
    def read_encoders(self):
        return {k: np.array([v]) for k, v in (
            ("positions_rad", 0), ("velocities_rad_s", 0),
            ("motor_current_A", 0), ("temperature_C", 25))}
    def write_torques(self, value): self.commands.append(list(value))
    def close(self): self.enabled = False


@pytest.fixture
def session(axes):
    buses = {name: WaveshareCan(MemoryPort()) for name in ("can_a", "can_b")}
    for bus in buses.values(): bus.configure(silent=False); bus.port.output.clear()
    profiles = {a.name: CommissionedAkProfile(
        a.actuator, "synthetic_not_hardware", "test_" + a.name, "test_fixture_only", True,
        True, True, True, True, .05, 2., 4., math.pi/180, 7, 10., 0.,
        -1 if a.name == "left_knee_pitch" else 1, 60.)
        for a in axes if a.bus != "ttl_5v"}
    release = {k: True for k in ("power_protection_passed", "emergency_stop_passed",
        "mechanical_fixture_passed", "ttl_commissioning_passed", "bus_identity_passed", "latency_loss_passed")}
    release["evidence_ref"] = "synthetic_not_a_release"
    runtime = HybridTorqueSession(axes, buses, TtlFixture(), profiles, release=release,
                                 positive_power_limit_w=350., feedback_timeout_s=.08)
    healthy(runtime)
    yield runtime
    runtime.close()


def healthy(session, *, error_axis=None, current_axis=None):
    for axis in session.can_axes.values():
        current = 500 if axis.name == current_axis else 0
        error = 3 if axis.name == error_axis else 0
        payload = struct.pack(">hhhbB", 0, 0, current, 25, error)
        session.buses[axis.bus].port.input.extend(encode_fixed(CanFrame(0x2900 | axis.node_id, payload)))


def sent(session, bus):
    output = session.buses[bus].port.output
    return [decode_fixed(bytes(output[i:i+20])) for i in range(0, len(output), 20)]


def clear_sent(session):
    for bus in session.buses.values(): bus.port.output.clear()


def test_current_contract_partition_and_single_ttl_not_legacy(axes):
    assert len(axes) == 18
    assert sum(a.bus == "can_a" for a in axes) == 9
    assert sum(a.bus == "can_b" for a in axes) == 8
    head = next(a for a in axes if a.name == "head_roll")
    spec = xc330_axis_spec(head, motor_id=2, current_limit_a=.3)
    assert [a["name"] for a in spec["joints"]] == ["head_roll"]
    assert spec["joints"][0]["range_rad"] == [-.6, .6]
    assert set(spec["motor_bus"]) == {"5v"}


@pytest.mark.parametrize("fault", ["release", "profile", "ttl", "stale", "motor_fault"])
def test_whole_preflight_before_any_current_or_enable(session, fault):
    if fault == "release": session.release["power_protection_passed"] = False
    elif fault == "profile":
        session.profiles["left_ankle_roll"] = replace(session.profiles["left_ankle_roll"], verified=False)
    elif fault == "ttl": session.ttl.failed = True
    elif fault == "stale":
        for bus in session.buses.values(): bus.port.input.clear()
    else: healthy(session, error_axis="left_ankle_roll")
    with pytest.raises((ValueError, TimeoutError)): session.arm()
    assert not session.armed and not session.ttl.enabled
    assert all(not b.port.output for b in session.buses.values())


def test_signed_named_dispatch_with_repeated_ids_on_distinct_buses(session):
    session.arm(); clear_sent(session); healthy(session)
    torque = np.zeros(18); torque[0] = .5; torque[4] = .1; torque[15] = -.5
    session.write_torques(torque)
    assert len(sent(session, "can_a")) == 9 and len(sent(session, "can_b")) == 8
    assert sent(session, "can_a")[0].arbitration_id == 0x101
    assert sent(session, "can_a")[0].data == bytes.fromhex("00 00 00 fa")
    left_knee = next(a for a in session.axes if a.name == "left_knee_pitch")
    packet = next(f for f in sent(session, "can_b") if f.arbitration_id & 255 == left_knee.node_id)
    assert packet.data == bytes.fromhex("00 00 00 fa")  # negative joint torque, negative motor direction
    assert session.ttl.commands[-1] == [.1]
    reading = session.poll()
    assert reading["positions_rad"].shape == (18,)
    assert "supply_voltage_V" not in reading  # AK packet has no voltage


def test_invalid_last_axis_command_does_not_partially_command_first_bus(session):
    session.arm(); clear_sent(session); healthy(session)
    torque = np.zeros(18); torque[-1] = 2.01
    with pytest.raises(ValueError): session.write_torques(torque)
    assert not session.armed and session.fault
    assert all(f.arbitration_id >> 8 == 15 for bus in session.buses for f in sent(session, bus))
    assert not session.ttl.commands and not session.ttl.enabled


def test_bus_b_failure_still_attempts_bus_a_and_ttl_stop(session):
    session.arm(); clear_sent(session); healthy(session)
    session.buses["can_b"].port.fail = True
    with pytest.raises(OSError): session.write_torques(np.zeros(18))
    assert not session.armed and not session.ttl.enabled
    assert any(f.arbitration_id >> 8 == 15 for f in sent(session, "can_a"))
    assert any("can_b" in e for e in session.stop_errors)
    with pytest.raises(RuntimeError): session.arm()


@pytest.mark.parametrize("fault", ["checksum", "current", "disable_ack"])
def test_received_fault_stops_all_branches(session, fault):
    session.arm(); clear_sent(session)
    if fault == "checksum":
        packet = bytearray(encode_fixed(CanFrame(0x2901, b"\0" * 8))); packet[-1] ^= 1
        session.buses["can_a"].port.input.extend(packet)
    elif fault == "current": healthy(session, current_axis="left_ankle_roll")
    else: session.buses["can_a"].port.input.extend(encode_fixed(CanFrame(0x2901, b"\0" * 7 + b"\x77")))
    with pytest.raises((ValueError, OSError)): session.poll()
    assert not session.armed and not session.ttl.enabled
    assert all(f.arbitration_id >> 8 == 15 for bus in session.buses for f in sent(session, bus))


def test_independent_software_watchdog_expires_without_new_application_call(session):
    session.arm(); clear_sent(session)
    deadline = time.monotonic() + .3
    while session.armed and time.monotonic() < deadline: time.sleep(.005)
    assert not session.armed and not session.ttl.enabled and session.fault
    assert all(f.arbitration_id >> 8 == 15 for bus in session.buses for f in sent(session, bus))
    result = session.disarm()
    assert result["physical_torque_off_confirmed"] is False


def test_duplicate_physical_identity_rejected(session):
    session.profiles["left_ankle_roll"] = replace(session.profiles["left_ankle_roll"],
        device_identity=session.profiles["neck_yaw"].device_identity)
    with pytest.raises(ValueError): session.arm()
    assert not session.armed and all(not b.port.output for b in session.buses.values())


def test_current_contract_positive_power_limit_checked_before_transmission(session):
    session.arm(); clear_sent(session)
    for axis in session.can_axes.values():
        profile = session.profiles[axis.name]
        erpm_ticks = math.floor(axis.speed_limit_rad_s * 60 * profile.pole_pairs * profile.reduction_ratio / (2*math.pi*10))
        payload = struct.pack(">hhhbB", 0, profile.sign * erpm_ticks, 0, 25, 0)
        session.buses[axis.bus].port.input.extend(encode_fixed(CanFrame(0x2900 | axis.node_id, payload)))
    with pytest.raises(ValueError, match="Positive mechanical power"):
        session.write_torques([a.continuous_limit_nm for a in session.axes])
    assert not session.armed and not session.ttl.commands
    assert all(f.arbitration_id >> 8 == 15 for bus in session.buses for f in sent(session, bus))
