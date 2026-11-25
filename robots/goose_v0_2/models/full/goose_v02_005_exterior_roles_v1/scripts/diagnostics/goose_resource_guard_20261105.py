#!/usr/bin/env python3
"""Run one Goose computation outside the desktop app cgroup, with hard limits.

All descendants share the service limit. Two cooperating runners can execute at
once; their parent slice also has a kernel-enforced aggregate memory limit.
No shell command interpolation, automatic retries, or changes to desktop units.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

GIB = 1024 ** 3
SLICE = "goose_closeout.slice"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/goose_v0_2/enclosure_closeout_20261105/resource_runs"


def ctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], text=True,
                          capture_output=True, timeout=15)


def properties(unit: str) -> dict[str, str]:
    p = ctl("show", unit, "--property=LoadState,ActiveState,SubState,ControlGroup,"
            "Result,MemoryCurrent,MemoryPeak,MemoryMax,MemoryHigh,MemorySwapMax,"
            "ExecMainCode,ExecMainStatus,CPUUsageNSec,TasksCurrent")
    return dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def available_memory() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("Cannot read physical memory availability")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True)
    ap.add_argument("--memory-gib", type=int, default=12, choices=range(1, 17))
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--cwd", type=Path, default=ROOT)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    command = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not command or not 1 <= a.timeout <= 7200:
        ap.error("An explicit command and timeout of 1..7200 seconds are required")
    name = re.sub("[^a-z0-9_-]", "_", a.name.lower())[:48]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    token = uuid.uuid4().hex[:8]
    unit = f"goose-{name}-{token}.service"
    run_dir = OUT / f"{stamp}_{name}_{token}"
    run_dir.mkdir(parents=True, exist_ok=False)
    report = {"unit": unit, "slice": SLICE, "status": "PREFLIGHT", "command": command,
              "cwd": str(a.cwd.resolve()), "memory_max_bytes": a.memory_gib * GIB,
              "aggregate_max_bytes": 32 * GIB, "timeout_s": a.timeout,
              "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "samples": []}
    receipt = run_dir / "receipt.json"
    atomic_json(receipt, report)
    lock_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "goose_closeout_guard"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = None
    for i in range(2):
        candidate = (lock_dir / f"slot_{i}.lock").open("a+")
        try:
            fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock = candidate
            break
        except BlockingIOError:
            candidate.close()
    if lock is None:
        report.update(status="REFUSED_TWO_COMPUTATIONS_ALREADY_RUNNING")
        atomic_json(receipt, report)
        print(f"EVENT RESOURCE_REFUSED {receipt}", flush=True)
        return 75
    if available_memory() < 32 * GIB:
        report.update(status="REFUSED_LOW_SYSTEM_MEMORY")
        atomic_json(receipt, report)
        return 75
    setup = ctl("set-property", "--runtime", SLICE, "MemoryHigh=24G", "MemoryMax=32G",
                "MemorySwapMax=0", "TasksMax=192")
    parent = properties(SLICE)
    if setup.returncode or parent.get("MemoryMax") != str(32 * GIB) or parent.get("MemorySwapMax") != "0":
        report.update(status="REFUSED_CGROUP_PROTECTION_UNAVAILABLE", protection=parent,
                      detail=setup.stderr[-2000:])
        atomic_json(receipt, report)
        return 78
    report["parent_protection"] = parent
    run = ["systemd-run", "--user", "--wait", "--pipe", f"--unit={unit}", f"--slice={SLICE}",
           f"--working-directory={a.cwd.resolve()}", f"--property=MemoryMax={a.memory_gib}G",
           f"--property=MemoryHigh={max(1, a.memory_gib - 2)}G", "--property=MemorySwapMax=0",
           "--property=OOMPolicy=kill", "--property=KillMode=control-group",
           "--property=TimeoutStopSec=5", f"--property=RuntimeMaxSec={a.timeout}",
           "--property=TasksMax=96", "--property=CPUQuota=600%", "--property=Nice=5",
           "--property=OOMScoreAdjust=500"]
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        run.append(f"--setenv={key}=2")
    if "MUJOCO_GL" in os.environ:
        run.append(f"--setenv=MUJOCO_GL={os.environ['MUJOCO_GL']}")
    run.extend(["--", *command])
    reason = None

    def stop(signum, _frame):
        nonlocal reason
        reason = f"CALLER_SIGNAL_{signum}"
        ctl("stop", unit)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    log_path = run_dir / "stdout.log"
    started = time.monotonic()
    print(f"EVENT GUARDED_START {unit} {a.memory_gib}GiB {receipt}", flush=True)
    with log_path.open("wb") as log:
        proc = subprocess.Popen(run, stdout=log, stderr=subprocess.STDOUT)
        report["systemd_run_pid"] = proc.pid
        report["status"] = "RUNNING"
        atomic_json(receipt, report)
        previous_sample = 0.0
        while proc.poll() is None:
            elapsed = time.monotonic() - started
            sample_interval = 1 if elapsed < 6 else 10
            if elapsed - previous_sample >= sample_interval or not report["samples"]:
                state = properties(unit)
                report["samples"].append({"elapsed_s": round(elapsed, 2), **state})
                previous_sample = elapsed
                atomic_json(receipt, report)
            if available_memory() < 24 * GIB:
                reason = "LOW_SYSTEM_MEMORY_SAFETY_STOP"
            if log_path.stat().st_size > 128 * 1024 ** 2:
                reason = "EXCESS_OUTPUT_SAFETY_STOP"
            if elapsed > a.timeout + 20:
                reason = "SUPERVISOR_WALL_TIMEOUT"
            if reason:
                ctl("stop", unit)
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()  # Exact systemd-run observer, never an unrelated process.
                    proc.wait()
                break
            time.sleep(1)
    final = properties(unit)
    peak = max((int(v.get("MemoryCurrent", "0")) for v in report["samples"]
                if v.get("MemoryCurrent", "").isdigit()), default=0)
    if final.get("MemoryPeak", "").isdigit():
        peak = max(peak, int(final["MemoryPeak"]))
    summary_lines = [line for line in log_path.read_text(errors="replace").splitlines()[-20:]
                     if line.startswith(("Memory peak:", "Memory swap peak:", "CPU time consumed:",
                                         "Service runtime:", "Finished with result:"))]
    report.update(status="PASS_PROCESS_EXIT" if not reason and proc.returncode == 0 else "TASK_FAILED_OR_STOPPED",
                  stop_reason=reason, exit_code=proc.returncode, final_service_state=final,
                  observed_peak_bytes=peak or None, service_resource_summary=summary_lines,
                  elapsed_s=round(time.monotonic() - started, 3),
                  finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    atomic_json(receipt, report)
    ctl("reset-failed", unit)
    peak_label = f"{peak/GIB:.3f}" if peak else "see_service_summary"
    print(f"EVENT GUARDED_FINISH {report['status']} peak_GiB={peak_label} {receipt}", flush=True)
    return 0 if report["status"] == "PASS_PROCESS_EXIT" else 1


if __name__ == "__main__":
    sys.exit(main())
