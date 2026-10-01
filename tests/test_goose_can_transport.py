"""Primary PDF packet vectors and real local serial fragmentation, no motors."""
import os
import threading
import time

import pytest

from sai_agent.goose.can_transport import (CanFrame, FixedFrameStream, WaveshareCan,
                                           decode_fixed, encode_fixed, fixed_configuration)

STANDARD = bytes.fromhex("aa 55 01 01 01 23 01 00 00 08 11 22 33 44 55 66 77 88 00 93")
EXTENDED = bytes.fromhex("aa 55 01 02 01 78 56 34 12 08 01 02 03 04 05 06 07 08 00 44")


@pytest.mark.parametrize("packet,identifier,payload,extended", [
    (STANDARD, 0x123, bytes.fromhex("11 22 33 44 55 66 77 88"), False),
    (EXTENDED, 0x12345678, bytes(range(1, 9)), True),
])
def test_primary_pdf_golden_vectors(packet, identifier, payload, extended):
    expected = CanFrame(identifier, payload, extended)
    assert decode_fixed(packet) == expected
    assert encode_fixed(expected) == packet


@pytest.mark.parametrize("cut", range(1, 20))
def test_every_serial_packet_split_and_multiple_packets(cut):
    stream = FixedFrameStream()
    assert stream.feed(EXTENDED[:cut]) == []
    assert stream.feed(EXTENDED[cut:] + STANDARD) == [decode_fixed(EXTENDED), decode_fixed(STANDARD)]
    assert not stream.buffer


def test_corruption_recovery_retains_trailing_header_and_bounds_junk():
    stream = FixedFrameStream()
    bad = bytearray(EXTENDED); bad[11] ^= 128
    assert stream.feed(b"z" * 150000 + bad + b"\xaa") == []
    assert stream.invalid_packets == 1 and len(stream.buffer) == 1
    assert stream.feed(EXTENDED[1:]) == [decode_fixed(EXTENDED)]
    assert len(stream.buffer) <= 19


@pytest.mark.parametrize("index,value", [(2, 2), (3, 3), (4, 0), (9, 9), (18, 1)])
def test_malformed_fields_rejected_even_with_valid_checksum(index, value):
    packet = bytearray(EXTENDED); packet[index] = value
    packet[19] = sum(packet[2:19]) & 255
    with pytest.raises(ValueError): decode_fixed(bytes(packet))


def test_identifier_limits_remote_and_receive_padding():
    with pytest.raises(ValueError): CanFrame(0x800, b"", extended=False)
    with pytest.raises(ValueError): CanFrame(0x20000000, b"")
    with pytest.raises(ValueError): CanFrame(True, b"")
    with pytest.raises(ValueError): CanFrame(1, b"data", remote=True)
    remote = CanFrame(1, b"", remote=True, dlc=8)
    assert decode_fixed(encode_fixed(remote)) == remote
    packet = bytearray(encode_fixed(CanFrame(2, b"hi")))
    packet[12:18] = b"unused"; packet[19] = sum(packet[2:19]) & 255
    assert decode_fixed(bytes(packet)).data == b"hi"


def test_configuration_matches_manufacturer_demo_layout():
    normal = bytes.fromhex("aa 55 02 01 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 05")
    assert fixed_configuration() == normal
    silent = bytearray(normal); silent[13] = 1; silent[19] = 6
    assert fixed_configuration(silent=True) == bytes(silent)
    with pytest.raises(ValueError): fixed_configuration(bitrate=1234)


class PartialPort:
    def __init__(self, count=3): self.output = bytearray(); self.count = count
    def write(self, data):
        size = min(self.count, len(data)); self.output.extend(data[:size]); return size
    def read(self, size): return b""
    def close(self): pass


def test_partial_write_completion_and_no_progress_failure():
    port = PartialPort(); bus = WaveshareCan(port)
    with pytest.raises(RuntimeError): bus.send_many([decode_fixed(EXTENDED)])
    bus.configure(silent=True)
    with pytest.raises(RuntimeError): bus.send_many([decode_fixed(EXTENDED)])
    bus.configure(silent=False); bus.send_many([decode_fixed(EXTENDED), decode_fixed(STANDARD)])
    assert port.output[-40:] == EXTENDED + STANDARD
    port.count = 0
    with pytest.raises(TimeoutError): bus.send_many([decode_fixed(EXTENDED)])


@pytest.mark.skipif(os.name != "posix", reason="POSIX PTY integration")
def test_real_pyserial_endpoint_over_pty():
    pytest.importorskip("serial")
    master, slave = os.openpty()
    bus = WaveshareCan.open(os.ttyname(slave), io_timeout_s=.02)
    try:
        bus.configure(silent=True)
        assert os.read(master, 20) == fixed_configuration(silent=True)
        os.write(master, EXTENDED[:7])
        deadline = time.monotonic() + .1
        while len(bus.stream.buffer) < 7 and time.monotonic() < deadline:
            assert bus.receive() == []
            time.sleep(.001)
        os.write(master, EXTENDED[7:] + STANDARD)
        frames = []
        while len(frames) < 2 and time.monotonic() < deadline:
            frames.extend(bus.receive()); time.sleep(.001)
        assert frames == [decode_fixed(EXTENDED), decode_fixed(STANDARD)]
    finally:
        bus.close(); os.close(master); os.close(slave)
