import math
import struct

import pytest

from sai_agent.goose.can_transport import CanFrame
from sai_agent.goose.cubemars_v3 import (AkStatus, CommissionedAkProfile,
    DisableAcknowledgement, MitRanges, current_command, decode_status, disable, mit_command)


def test_v3_order_endpoints_and_official_demo_midpoint():
    # Explicit generic demo values for testing the wire format only.
    bounds = MitRanges((-12.5, 12.5), (-45, 45), (0, 500), (0, 5), (-18, 18))
    mid = mit_command(104, position=0, velocity=0, kp=0, kd=0, feedforward=0, ranges=bounds)
    assert mid.arbitration_id == 0x868 and mid.extended
    assert mid.data == bytes.fromhex("00 00 00 7f ff 7f f7 ff")
    high = mit_command(1, position=12.5, velocity=45, kp=500, kd=5, feedforward=18, ranges=bounds)
    assert high.data == b"\xff" * 8  # no upper-endpoint wrap to zero
    low = mit_command(1, position=-12.5, velocity=-45, kp=0, kd=0, feedforward=-18, ranges=bounds)
    assert low.data == b"\0" * 8
    with pytest.raises(ValueError):
        mit_command(1, position=12.6, velocity=0, kp=0, kd=0, feedforward=0, ranges=bounds)


def test_signed_current_mode_and_disable_are_distinct_extended_functions():
    command = current_command(9, -1.234, limit_a=2)
    assert command.arbitration_id == 0x109 and command.data.hex() == "fffffb2e"
    stopped = disable(9)
    assert stopped.arbitration_id == 0xf09 and stopped.data == b""
    with pytest.raises(ValueError): current_command(9, 2.001, limit_a=2)
    with pytest.raises(ValueError): current_command(0, 0, limit_a=2)
    with pytest.raises(ValueError): current_command(1, math.nan, limit_a=2)


def test_signed_feedback_keeps_electrical_speed_and_board_temperature_units():
    frame = CanFrame(0x2903, bytes.fromhex("ff 9c ff ec ff 38 fb 00"))
    status = decode_status(frame)
    assert status == AkStatus(3, -10., -200., -2., -5, 0)
    assert decode_status(CanFrame(0x2903, b"\0" * 7 + b"\x77")) == DisableAcknowledgement(3)
    with pytest.raises(ValueError): decode_status(CanFrame(0x2903, b"\0" * 4))
    with pytest.raises(ValueError): decode_status(CanFrame(0x29, b"\0" * 8, extended=False))
    with pytest.raises(ValueError): decode_status(CanFrame(0x2900, b"\0" * 8))


def test_si_conversion_requires_physical_profile_not_generic_demo():
    profile = CommissionedAkProfile("synthetic_test_only", "test", "test1", "fixture", True,
        True, True, True, True, .05, 2., 3., math.pi/180, 7, 10., .2, -1, 60.)
    q, dq, current = profile.output(AkStatus(1, 90, 4200, 1.2, 25, 0))
    assert q == pytest.approx(.2 - math.pi/2)
    assert dq == pytest.approx(-2 * math.pi)
    assert current == -1.2
    from dataclasses import replace
    with pytest.raises(ValueError): replace(profile, feedback_verified=False).validate()
    with pytest.raises(ValueError): replace(profile, hardware_watchdog_timeout_s=.1).validate()
