"""Waveshare USB-CAN-A fixed 20-byte serial protocol (not SocketCAN).

No ports open at import. Configuration is explicit; receive-only callers can
choose silent mode. A completed serial write is not a CAN delivery receipt.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol


@dataclass(frozen=True)
class CanFrame:
    arbitration_id: int
    data: bytes
    extended: bool = True
    remote: bool = False
    dlc: int | None = None

    def __post_init__(self):
        if type(self.extended) is not bool or type(self.remote) is not bool:
            raise ValueError("CAN flags must be boolean")
        if type(self.arbitration_id) is not int or not 0 <= self.arbitration_id <= (
            0x1FFFFFFF if self.extended else 0x7FF
        ):
            raise ValueError("CAN identifier outside frame range")
        if not isinstance(self.data, bytes):
            raise ValueError("CAN payload must be immutable bytes")
        dlc = len(self.data) if self.dlc is None else self.dlc
        if type(dlc) is not int or not 0 <= dlc <= 8:
            raise ValueError("CAN DLC must be 0..8")
        if (self.remote and self.data) or (not self.remote and len(self.data) != dlc):
            raise ValueError("CAN payload does not match frame format/DLC")
        object.__setattr__(self, "dlc", dlc)


def encode_fixed(frame: CanFrame) -> bytes:
    packet = bytearray((0xAA, 0x55, 1, 2 if frame.extended else 1,
                        2 if frame.remote else 1))
    packet.extend(frame.arbitration_id.to_bytes(4, "little"))
    packet.append(frame.dlc)
    packet.extend(frame.data.ljust(8, b"\0"))
    packet.append(0)
    packet.append(sum(packet[2:]) & 255)
    return bytes(packet)


def decode_fixed(packet: bytes) -> CanFrame:
    if len(packet) != 20 or packet[:3] != b"\xaa\x55\x01":
        raise ValueError("Invalid fixed-length CAN packet header")
    if packet[3] not in (1, 2) or packet[4] not in (1, 2) or packet[18] != 0:
        raise ValueError("Invalid CAN type/format/reserved byte")
    if sum(packet[2:19]) & 255 != packet[19]:
        raise ValueError("CAN serial checksum mismatch")
    dlc = packet[9]
    if dlc > 8:
        raise ValueError("CAN DLC exceeds eight")
    # Unused RX slots are not documented as zero-filled by the manufacturer.
    return CanFrame(int.from_bytes(packet[5:9], "little"),
                    b"" if packet[4] == 2 else packet[10:10 + dlc],
                    packet[3] == 2, packet[4] == 2, dlc)


def fixed_configuration(*, bitrate: int = 1_000_000, silent: bool = False) -> bytes:
    """Manufacturer demo configuration layout, fixed mode / extended frames.

    Persistence and configuration ACK behavior are not established. This does
    not write motor parameters, set encoder origins, or issue motor commands.
    """
    rates = (1_000_000, 800_000, 500_000, 400_000, 250_000, 200_000,
             125_000, 100_000, 50_000, 20_000, 10_000, 5_000)
    if type(bitrate) is not int or bitrate not in rates or type(silent) is not bool:
        raise ValueError("Unsupported CAN baud rate/mode")
    packet = bytearray((0xAA, 0x55, 0x02, rates.index(bitrate) + 1, 2))
    packet.extend(b"\0" * 8)  # accept all: filter and mask
    packet.extend((int(silent), 0, 0, 0, 0, 0))
    packet.append(sum(packet[2:]) & 255)
    return bytes(packet)


class FixedFrameStream:
    """Incremental parser; retain at most 19 incomplete bytes between calls."""

    def __init__(self):
        self.buffer = bytearray()
        self.invalid_packets = 0
        self.discarded_bytes = 0

    def feed(self, data: bytes) -> list[CanFrame]:
        frames = []
        # Process in bounded chunks, including when a caller supplies huge junk.
        for offset in range(0, len(data), 1024):
            self.buffer.extend(data[offset:offset + 1024])
            while self.buffer:
                start = self.buffer.find(b"\xaa\x55")
                if start < 0:
                    keep = int(self.buffer[-1] == 0xAA)
                    self.discarded_bytes += len(self.buffer) - keep
                    self.buffer[:] = self.buffer[-1:] if keep else b""
                    break
                if start:
                    self.discarded_bytes += start
                    del self.buffer[:start]
                if len(self.buffer) < 20:
                    break
                try:
                    frame = decode_fixed(bytes(self.buffer[:20]))
                except ValueError:
                    self.invalid_packets += 1
                    self.discarded_bytes += 1
                    del self.buffer[0]
                    continue
                frames.append(frame)
                del self.buffer[:20]
        return frames


class BytePort(Protocol):
    def write(self, data: bytes) -> int: ...
    def read(self, size: int) -> bytes: ...
    def close(self) -> None: ...


class WaveshareCan:
    """One bounded, explicitly configured serial endpoint; single owner only."""

    def __init__(self, port: BytePort, *, io_timeout_s: float = .005):
        if not 0 < io_timeout_s <= .05:
            raise ValueError("Serial IO timeout outside 0..50 ms")
        self.port = port
        self.io_timeout_s = io_timeout_s
        self.stream = FixedFrameStream()
        self.configured = False
        self.silent = True

    @classmethod
    def open(cls, path: str, *, io_timeout_s: float = .005):
        import serial
        port = serial.Serial(path, 2_000_000, timeout=0,
                             write_timeout=io_timeout_s, exclusive=True)
        return cls(port, io_timeout_s=io_timeout_s)

    def _write_all(self, payload: bytes):
        deadline = time.monotonic() + self.io_timeout_s
        offset = 0
        while offset < len(payload):
            if time.monotonic() >= deadline:
                raise TimeoutError("Incomplete USB-CAN serial write")
            count = self.port.write(payload[offset:])
            if type(count) is not int or not 0 <= count <= len(payload) - offset:
                raise OSError("Invalid serial write result")
            if not count:
                raise TimeoutError("USB-CAN serial write made no progress")
            offset += count
        if time.monotonic() > deadline:
            raise TimeoutError("USB-CAN serial write exceeded deadline")

    def configure(self, *, silent: bool, bitrate: int = 1_000_000):
        self.configured = False
        self.silent = True
        self._write_all(fixed_configuration(bitrate=bitrate, silent=silent))
        self.silent = silent
        self.configured = True  # host request sent, not a firmware ACK

    def send_many(self, frames: list[CanFrame]):
        if not self.configured or self.silent:
            raise RuntimeError("USB-CAN adapter is not configured for transmission")
        if not frames or len(frames) > 32:
            raise ValueError("CAN batch must contain 1..32 frames")
        self._write_all(b"".join(encode_fixed(frame) for frame in frames))

    def receive(self) -> list[CanFrame]:
        # Bound work per call. The real serial endpoint is nonblocking.
        return self.stream.feed(self.port.read(4096))

    def close(self):
        self.configured = False
        self.port.close()
