"""Two real local PTYs exercise the passive diagnostic's complete entry point."""
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import threading

import pytest

from sai_agent.goose.can_transport import CanFrame, encode_fixed, fixed_configuration

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "posix", reason="POSIX serial test")
@pytest.mark.parametrize("missing_last", [False, True])
def test_passive_entry_point_never_emits_motor_commands(tmp_path, missing_last):
    pytest.importorskip("serial")
    pairs = [os.openpty(), os.openpty()]
    outgoing = []; failures = []
    def device(index, master):
        try:
            if not select.select([master], [], [], 3)[0]:
                raise TimeoutError("No adapter configuration received")
            config = bytearray()
            while len(config) < 20:
                config.extend(os.read(master, 20 - len(config)))
            outgoing.append(bytes(config))
            count = 9 if index == 0 else (7 if missing_last else 8)
            packets = b"".join(encode_fixed(CanFrame(0x2900 | node,
                struct.pack(">hhhbB", 0, 0, 0, 25, 0))) for node in range(1, count + 1))
            os.write(master, packets[:11]); os.write(master, packets[11:])
            if select.select([master], [], [], .4)[0]:
                outgoing.append(os.read(master, 4096))
        except Exception as exc:
            failures.append(str(exc))
    threads = [threading.Thread(target=device, args=(i, pair[0])) for i, pair in enumerate(pairs)]
    output = tmp_path / "capture.json"
    try:
        for thread in threads: thread.start()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/diagnostics/inspect_goose_can.py"),
            "--can-a", os.ttyname(pairs[0][1]), "--can-b", os.ttyname(pairs[1][1]),
            "--configure-silent", "--seconds", ".15", "--output", str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=5)
        for thread in threads: thread.join(timeout=2)
        assert not failures
        assert outgoing == [fixed_configuration(silent=True)] * 2
        assert result.returncode == (2 if missing_last else 0), result.stderr
        report = json.loads(output.read_text())
        assert report["motor_commands_sent"] == 0
        assert not report["hardware_control_release"]
        assert report["all_17_status_endpoints_seen_without_recorded_fault"] == (not missing_last)
        assert report["missing_axes"] == (["left_ankle_roll"] if missing_last else [])
    finally:
        for thread in threads: thread.join(timeout=1)
        for master, slave in pairs: os.close(master); os.close(slave)
