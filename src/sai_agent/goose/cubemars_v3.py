"""AK V3 primary-document wire formats, without invented motor profiles.

The generic MIT demo ranges are deliberately not defaults for AK40/45 V3.
Telemetry is initially kept in documented wire units: ERPM and board degrees C.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct

from .can_transport import CanFrame


def _frame(node_id: int, function: int, data: bytes) -> CanFrame:
    if type(node_id) is not int or not 1 <= node_id <= 255:
        raise ValueError("AK node ID must be 1..255; no broadcast")
    return CanFrame((function << 8) | node_id, data)


def disable(node_id: int) -> CanFrame:
    return _frame(node_id, 15, b"")


def current_command(node_id: int, current_a: float, *, limit_a: float) -> CanFrame:
    if not math.isfinite(limit_a) or limit_a <= 0 or not math.isfinite(current_a):
        raise ValueError("Invalid commissioned current")
    if abs(current_a) > limit_a:
        raise ValueError("Current exceeds commissioned limit; no silent clipping")
    milliamps = math.trunc(current_a * 1000)
    if not -(2**31) <= milliamps < 2**31:
        raise ValueError("Current overflows AK wire format")
    return _frame(node_id, 1, struct.pack(">i", milliamps))


@dataclass(frozen=True)
class MitRanges:
    position: tuple[float, float]
    velocity: tuple[float, float]
    kp: tuple[float, float]
    kd: tuple[float, float]
    feedforward: tuple[float, float]


def _quantize(value: float, bounds: tuple[float, float], bits: int) -> int:
    low, high = bounds
    if not all(math.isfinite(v) for v in (value, low, high)) or low >= high:
        raise ValueError("Invalid explicit MIT range")
    if not low <= value <= high:
        raise ValueError("MIT field outside explicit range")
    # Official Arduino demo uses (2**bits-1). The manual's 2**bits expression
    # overflows at the upper endpoint; do not copy that defect or silently wrap.
    return min((1 << bits) - 1, int((value - low) * ((1 << bits) - 1) / (high - low)))


def mit_command(node_id: int, *, position: float, velocity: float, kp: float,
                kd: float, feedforward: float, ranges: MitRanges) -> CanFrame:
    p = _quantize(position, ranges.position, 16)
    v = _quantize(velocity, ranges.velocity, 12)
    k = _quantize(kp, ranges.kp, 12)
    d = _quantize(kd, ranges.kd, 12)
    f = _quantize(feedforward, ranges.feedforward, 12)
    return _frame(node_id, 8, bytes((k >> 4, ((k & 15) << 4) | (d >> 8),
                                    d & 255, p >> 8, p & 255, v >> 4,
                                    ((v & 15) << 4) | (f >> 8), f & 255)))


@dataclass(frozen=True)
class AkStatus:
    node_id: int
    position_deg: float
    electrical_rpm: float
    current_a: float
    driver_temperature_c: int
    error_code: int


@dataclass(frozen=True)
class DisableAcknowledgement:
    node_id: int


def decode_status(frame: CanFrame) -> AkStatus | DisableAcknowledgement:
    if not frame.extended or frame.remote or frame.arbitration_id >> 8 != 0x29:
        raise ValueError("Not AK V3 status feedback")
    if len(frame.data) != 8 or not 1 <= frame.arbitration_id & 255 <= 255:
        raise ValueError("Invalid AK feedback DLC/node")
    node = frame.arbitration_id & 255
    if frame.data[7] == 0x77:
        return DisableAcknowledgement(node)
    position, speed, current, temp, error = struct.unpack(">hhhbB", frame.data)
    if abs(position) > 32000 or abs(speed) > 32000 or abs(current) > 6000 or temp < -20:
        raise ValueError("AK status outside documented wire range")
    return AkStatus(node, position * .1, speed * 10., current * .01, temp, error)


@dataclass(frozen=True)
class CommissionedAkProfile:
    """Physical device/firmware-specific calibration; never supplied by demo."""
    model: str
    firmware: str
    device_identity: str
    evidence_ref: str
    verified: bool
    current_control_verified: bool
    disable_verified: bool
    feedback_verified: bool
    hardware_watchdog_verified: bool
    hardware_watchdog_timeout_s: float
    nm_per_a: float
    current_limit_a: float
    position_output_rad_per_degree: float
    pole_pairs: int
    reduction_ratio: float
    zero_output_rad: float
    sign: int
    max_driver_temperature_c: float

    def validate(self):
        if not all(isinstance(v, str) and v.strip() for v in (
            self.model, self.firmware, self.device_identity, self.evidence_ref
        )):
            raise ValueError("Physical identity, firmware and evidence required")
        if not all(v is True for v in (self.verified, self.current_control_verified,
                                       self.disable_verified, self.feedback_verified,
                                       self.hardware_watchdog_verified)):
            raise ValueError("AK physical commissioning incomplete")
        if not math.isfinite(self.hardware_watchdog_timeout_s) or not 0 < self.hardware_watchdog_timeout_s <= .08:
            raise ValueError("Verified drive watchdog must expire within 80 ms")
        if type(self.sign) is not int or self.sign not in (-1, 1):
            raise ValueError("Invalid joint direction")
        if type(self.pole_pairs) is not int or self.pole_pairs <= 0:
            raise ValueError("Verified pole-pair count required")
        positive = (self.nm_per_a, self.current_limit_a,
                    self.position_output_rad_per_degree, self.reduction_ratio,
                    self.max_driver_temperature_c)
        if not all(math.isfinite(v) and v > 0 for v in positive) or not math.isfinite(self.zero_output_rad):
            raise ValueError("Invalid AK physical conversion/limits")

    def output(self, status: AkStatus) -> tuple[float, float, float]:
        self.validate()
        return (self.sign * (status.position_deg * self.position_output_rad_per_degree
                             - self.zero_output_rad),
                self.sign * status.electrical_rpm * 2 * math.pi / (
                    60 * self.pole_pairs * self.reduction_ratio),
                self.sign * status.current_a)
