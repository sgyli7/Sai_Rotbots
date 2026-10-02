"""Current 18-axis binding and torque dispatch: 17 AK CAN + one XC330 TTL.

An injectable TTL endpoint implements the same five operations as a one-axis
DynamixelRobot. Unknown A2 profiles prevent arming; raw passive capture remains
available in can_transport. Software stopping is best effort, not an E-stop.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import threading
import time
from typing import Protocol

import numpy as np

from .can_transport import WaveshareCan
from .cubemars_v3 import (AkStatus, CommissionedAkProfile, DisableAcknowledgement,
                         current_command, decode_status, disable)


@dataclass(frozen=True)
class AxisBinding:
    name: str
    actuator: str
    bus: str
    node_id: int | None
    range_rad: tuple[float, float]
    continuous_limit_nm: float
    speed_limit_rad_s: float


def bind_axes(contract: dict, layout: dict) -> tuple[AxisBinding, ...]:
    if contract.get("active_axes") != 18 or contract.get("robot") != "Goose_V0.1":
        raise ValueError("Expected current Goose 18-axis contract")
    names = contract["joint_order"]
    if len(names) != 18 or len(set(names)) != 18:
        raise ValueError("Duplicate/missing active axes")
    indexed = {j["name"]: j for j in contract["joints"]}
    if len(indexed) != 18 or set(indexed) != set(names):
        raise ValueError("Joint definitions do not match order")
    mapping = {}
    buses = layout["motor_buses"]
    if {b["name"] for b in buses} != {"can_a", "can_b"} or len(buses) != 2:
        raise ValueError("Two explicitly named CAN buses required")
    for bus in buses:
        ids = bus["proposed_node_ids"]
        if len(ids) != len(bus["axes"]) or len(set(ids)) != len(ids):
            raise ValueError("CAN IDs missing or duplicated within bus")
        for name, node in zip(bus["axes"], ids):
            if name in mapping or type(node) is not int or not 1 <= node <= 255:
                raise ValueError("Duplicate axis/invalid CAN ID")
            mapping[name] = (bus["name"], node)
    if layout["ttl_branch"]["axis"] != "head_roll" or "head_roll" in mapping:
        raise ValueError("head_roll requires its own TTL branch")
    mapping["head_roll"] = ("ttl_5v", None)
    if set(mapping) != set(names):
        raise ValueError("Every active axis must have exactly one hardware endpoint")
    bindings = []
    for name in names:
        joint = indexed[name]
        actuator = joint["actuator"]
        if actuator not in ("ak40_10_v3", "ak45_10_v3", "ak45_36_v3",
                            "ak45_36_v3_parallel_crank_1_to_1", "xc330_m288_t"):
            raise ValueError("Unexpected selected actuator")
        bus, node = mapping[name]
        if (bus == "ttl_5v") != (actuator == "xc330_m288_t"):
            raise ValueError("Actuator and electrical bus do not match")
        low, high = joint["range_rad"]
        limit = joint["continuous_design_limit_nm"]
        speed = joint["speed_limit_rad_s"]
        if not all(math.isfinite(v) for v in (low, high, limit, speed)) or low >= high or min(limit, speed) <= 0:
            raise ValueError("Invalid physical joint limits")
        bindings.append(AxisBinding(name, actuator, bus, node, (low, high), limit, speed))
    return tuple(bindings)


class TtlAxis(Protocol):
    def validate_ready(self) -> list[dict]: ...
    def arm(self) -> None: ...
    def disarm(self) -> None: ...
    def read_encoders(self) -> dict: ...
    def write_torques(self, torque_nm) -> None: ...
    def close(self) -> None: ...


def xc330_axis_spec(binding: AxisBinding, *, motor_id: int, current_limit_a: float) -> dict:
    """Adapt the existing verified DYNAMIXEL driver to the current single axis.

    Hardware current limits and Nm/A still require physical commissioning.
    No historical beak_drive or 12V joint is copied into this specification.
    """
    if binding.name != "head_roll" or binding.actuator != "xc330_m288_t":
        raise ValueError("Only the current head_roll XC330 belongs on this branch")
    if type(motor_id) is not int or not 1 <= motor_id <= 252:
        raise ValueError("Invalid TTL device ID")
    if not math.isfinite(current_limit_a) or not 0 < current_limit_a <= .36:
        raise ValueError("TTL commissioning current must stay within initial 0.36A cap")
    return {"joints": [{"name": binding.name, "servo": "xc330", "bus": "5v",
                        "motor_id": motor_id, "range_rad": list(binding.range_rad),
                        "motor_sign": 1, "motor_zero_ticks": 2048}],
            "servos": {"xc330": {"current_limit_initial_A": current_limit_a}},
            "motor_bus": {"5v": {"baud": 1_000_000}}}


def open_current_head_roll(binding: AxisBinding, path: str, *, motor_id: int,
                           current_limit_a: float, calibration: dict):
    from .hardware import DynamixelRobot
    if calibration.get("joint_names") != ["head_roll"] or calibration.get("commissioning_passed") is not True:
        raise ValueError("Current single-axis TTL commissioning required")
    gains = calibration.get("Nm_per_A", [])
    if len(gains) != 1 or not math.isfinite(gains[0]) or gains[0] <= 0:
        raise ValueError("Physical XC330 torque/current calibration required")
    if binding.continuous_limit_nm > math.floor(current_limit_a / .001) * .001 * gains[0]:
        raise ValueError("TTL continuous torque exceeds commissioned current")
    return DynamixelRobot({"5v": path}, calibration=calibration,
                          spec=xc330_axis_spec(binding, motor_id=motor_id,
                                              current_limit_a=current_limit_a))


class HybridTorqueSession:
    def __init__(self, axes: tuple[AxisBinding, ...], buses: dict[str, WaveshareCan],
                 ttl: TtlAxis, profiles: dict[str, CommissionedAkProfile], *,
                 release: dict, positive_power_limit_w: float, command_timeout_s: float = .08,
                 feedback_timeout_s: float = .04):
        if not math.isfinite(positive_power_limit_w) or positive_power_limit_w <= 0:
            raise ValueError("Explicit contract positive mechanical power limit required")
        if not 0 < feedback_timeout_s <= command_timeout_s <= .08:
            raise ValueError("Invalid watchdog intervals")
        if len(axes) != 18 or len({a.name for a in axes}) != 18 or sum(a.bus == "ttl_5v" for a in axes) != 1:
            raise ValueError("Session requires all 18 distinct axes")
        if set(buses) != {"can_a", "can_b"} or len({id(b) for b in buses.values()}) != 2:
            raise ValueError("Two distinct CAN endpoints required")
        self.axes, self.buses, self.ttl = axes, buses, ttl
        self.profiles, self.release = profiles, release
        self.positive_power_limit_w = positive_power_limit_w
        self.command_timeout_s, self.feedback_timeout_s = command_timeout_s, feedback_timeout_s
        self.can_axes = {a.name: a for a in axes if a.bus != "ttl_5v"}
        self.by_endpoint = {(a.bus, a.node_id): a for a in self.can_axes.values()}
        if len(self.by_endpoint) != 17:
            raise ValueError("Duplicate CAN endpoints")
        self.status: dict[str, tuple[AkStatus, float]] = {}
        self.disable_acks: set[tuple[str, int]] = set()
        self.stop_errors: list[str] = []
        self.fault: str | None = None
        self.armed = False
        self.closed = False
        self.last_command_s = 0.
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.watchdog: threading.Thread | None = None

    def _preflight(self):
        if self.closed:
            raise RuntimeError("Session is closed")
        required = ("power_protection_passed", "emergency_stop_passed", "mechanical_fixture_passed",
                    "ttl_commissioning_passed", "bus_identity_passed", "latency_loss_passed")
        if not all(self.release.get(k) is True for k in required):
            raise ValueError("Current whole-hardware release is incomplete")
        if not isinstance(self.release.get("evidence_ref"), str) or not self.release["evidence_ref"].strip():
            raise ValueError("Whole-hardware commissioning evidence required")
        if set(self.profiles) != set(self.can_axes):
            raise ValueError("17 physical device-specific AK profiles required")
        identities = set()
        for name, axis in self.can_axes.items():
            profile = self.profiles[name]
            profile.validate()
            if profile.model != axis.actuator:
                raise ValueError("Calibrated model/actuation chain mismatch: " + name)
            if profile.device_identity in identities:
                raise ValueError("Repeated physical actuator identity")
            identities.add(profile.device_identity)
            if axis.continuous_limit_nm / profile.nm_per_a > profile.current_limit_a:
                raise ValueError("Joint torque envelope exceeds commissioned current: " + name)
        if any(not bus.configured or bus.silent for bus in self.buses.values()):
            raise ValueError("CAN adapters not explicitly configured for transmission")
        ttl_status = self.ttl.validate_ready()
        if len(ttl_status) != 1 or ttl_status[0].get("joint") != "head_roll":
            raise ValueError("TTL endpoint must contain only current head_roll")
        available = ttl_status[0]["current_limit_ticks"] * .001 * ttl_status[0]["output_Nm_per_A"]
        head_limit = next(a.continuous_limit_nm for a in self.axes if a.bus == "ttl_5v")
        if not math.isfinite(available) or available < head_limit:
            raise ValueError("Actual TTL current limit cannot deliver the contract torque envelope")

    def _receive(self):
        for bus_name, bus in self.buses.items():
            now = time.monotonic()
            before = bus.stream.invalid_packets
            frames = bus.receive()
            if bus.stream.invalid_packets != before:
                raise OSError("Corrupt CAN serial packet on " + bus_name)
            for frame in frames:
                if frame.arbitration_id >> 8 != 0x29:
                    continue  # other documented feedback IDs are not fresh status
                value = decode_status(frame)
                endpoint = (bus_name, value.node_id)
                if endpoint not in self.by_endpoint:
                    raise ValueError("Uncommissioned actuator endpoint on " + bus_name)
                if isinstance(value, DisableAcknowledgement):
                    if self.armed:
                        raise ValueError("Unexpected actuator disable acknowledgement")
                    self.disable_acks.add(endpoint)
                else:
                    self.status[self.by_endpoint[endpoint].name] = (value, now)

    def _validate_status(self, now: float):
        for name, axis in self.can_axes.items():
            if name not in self.status or now - self.status[name][1] > self.feedback_timeout_s:
                raise TimeoutError("Missing/stale actuator feedback: " + name)
            status = self.status[name][0]
            profile = self.profiles[name]
            q, dq, current = profile.output(status)
            if status.error_code or status.driver_temperature_c >= profile.max_driver_temperature_c:
                raise ValueError("Actuator fault/driver temperature: " + name)
            if not axis.range_rad[0] <= q <= axis.range_rad[1] or abs(dq) > axis.speed_limit_rad_s:
                raise ValueError("Joint position/speed stop: " + name)
            if abs(current) > profile.current_limit_a:
                raise ValueError("Actuator current stop: " + name)

    def poll(self) -> dict:
        """Return current contract order in SI; voltage remains unavailable on AK."""
        with self.lock:
            try:
                self._receive()
                self._validate_status(time.monotonic())
                ttl = self.ttl.read_encoders()
                fields = {k: [] for k in ("positions_rad", "velocities_rad_s", "motor_current_A", "temperature_C")}
                for axis in self.axes:
                    if axis.bus == "ttl_5v":
                        arrays = [np.asarray(ttl[k], float) for k in
                                  ("positions_rad", "velocities_rad_s", "motor_current_A", "temperature_C")]
                        if any(v.shape != (1,) for v in arrays):
                            raise ValueError("TTL feedback must contain exactly one axis")
                        values = tuple(float(v[0]) for v in arrays)
                        if not all(math.isfinite(v) for v in values) or not axis.range_rad[0] <= values[0] <= axis.range_rad[1] or abs(values[1]) > axis.speed_limit_rad_s:
                            raise ValueError("TTL joint feedback stop")
                    else:
                        status = self.status[axis.name][0]
                        values = (*self.profiles[axis.name].output(status), status.driver_temperature_c)
                    for key, value in zip(fields, values):
                        fields[key].append(value)
                result = {key: np.asarray(value) for key, value in fields.items()}
                result["temperature_sensor_scope"] = [
                    "XC330 present-temperature register" if a.bus == "ttl_5v" else "AK driver board"
                    for a in self.axes]
                return result
            except Exception as exc:
                if self.armed:
                    self._stop(str(exc))
                raise

    def arm(self):
        with self.lock:
            if self.armed or self.fault is not None:
                raise RuntimeError("Already armed or fault latched; explicit reset required")
            self._preflight()  # no motor commands before every profile/release check
            self.poll()
            self.last_command_s = time.monotonic()
            self.armed = True
            try:
                for bus_name, bus in self.buses.items():
                    bus.send_many([current_command(a.node_id, 0., limit_a=self.profiles[a.name].current_limit_a)
                                   for a in self.can_axes.values() if a.bus == bus_name])
                self.ttl.arm()
            except Exception as exc:
                self._stop(str(exc))
                raise
            if self.watchdog is None:
                self.watchdog = threading.Thread(target=self._watch, name="goose_hardware_watchdog", daemon=True)
                self.watchdog.start()

    def write_torques(self, torque_nm):
        with self.lock:
            if not self.armed:
                raise RuntimeError("Robot is not armed")
            try:
                torque = np.asarray(torque_nm, dtype=float)
                if torque.shape != (18,) or not np.isfinite(torque).all():
                    raise ValueError("Invalid 18-axis torque command")
                now = time.monotonic()
                if now - self.last_command_s > self.command_timeout_s:
                    raise TimeoutError("Control stream expired")
                snapshot = self.poll()
                # Recheck after TTL IO; a blocked read must not refresh a stale
                # CAN sample or extend the command stream's lease.
                now = time.monotonic()
                self._validate_status(now)
                if now - self.last_command_s > self.command_timeout_s:
                    raise TimeoutError("Control stream expired during telemetry IO")
                positive_power = float(np.maximum(torque * snapshot["velocities_rad_s"], 0).sum())
                if positive_power > self.positive_power_limit_w:
                    raise ValueError("Positive mechanical power exceeds contract limit")
                batches = {name: [] for name in self.buses}
                ttl_torque = None
                # Validate and encode every axis before transmitting any command.
                for axis, value in zip(self.axes, torque):
                    if abs(value) > axis.continuous_limit_nm:
                        raise ValueError("Torque exceeds continuous design envelope: " + axis.name)
                    if axis.bus == "ttl_5v":
                        ttl_torque = value
                    else:
                        profile = self.profiles[axis.name]
                        batches[axis.bus].append(current_command(axis.node_id, profile.sign * value / profile.nm_per_a,
                                                                 limit_a=profile.current_limit_a))
                for name, bus in self.buses.items():
                    bus.send_many(batches[name])
                self.ttl.write_torques([ttl_torque])
                self.last_command_s = time.monotonic()
            except Exception as exc:
                if self.armed:
                    self._stop(str(exc))
                raise

    def _stop(self, reason: str | None):
        self.armed = False
        if reason is not None:
            self.fault = reason
        self.stop_errors = []
        self.disable_acks.clear()
        for name, bus in self.buses.items():
            try:
                bus.send_many([disable(a.node_id) for a in self.can_axes.values() if a.bus == name])
            except Exception as exc:
                self.stop_errors.append(name + ": " + str(exc))
        try:
            self.ttl.disarm()
        except Exception as exc:
            self.stop_errors.append("ttl_5v: " + str(exc))
        # Serial writes and any observed ACKs cannot prove torque-off after an
        # interrupted bus. A physical independent E-stop remains mandatory.

    def disarm(self):
        with self.lock:
            self._stop(None)
            return {"disable_commands_attempted": 17, "errors": list(self.stop_errors),
                    "physical_torque_off_confirmed": False}

    def reset_fault(self):
        with self.lock:
            if self.armed or self.closed:
                raise RuntimeError("Fault reset requires an open, disarmed session")
            self._preflight()
            self.status.clear()
            self.poll()
            self.fault = None

    def _watch(self):
        while not self.stop_event.wait(.005):
            with self.lock:
                if self.armed:
                    now = time.monotonic()
                    if now - self.last_command_s > self.command_timeout_s:
                        self._stop("Control stream expired in watchdog")
                    elif any(now - received > self.feedback_timeout_s for _, received in self.status.values()):
                        self._stop("Actuator feedback expired in watchdog")

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.stop_event.set()
            self._stop(None)
            self.closed = True
            for name, bus in self.buses.items():
                try:
                    bus.close()
                except Exception as exc:
                    self.stop_errors.append(name + " close: " + str(exc))
            try:
                self.ttl.close()
            except Exception as exc:
                self.stop_errors.append("ttl close: " + str(exc))
        if self.watchdog is not None:
            self.watchdog.join(timeout=.2)
