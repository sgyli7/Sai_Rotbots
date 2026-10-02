"""Reproduce current transport software checks; explicitly not hardware release."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from sai_agent.goose.hybrid_hardware import bind_axes

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    contract_path = ROBOT / "configs/mechanical_physics_contract.json"
    layout_path = ROBOT / "hardware/stage_three_can_layout.json"
    template_path = ROBOT / "configs/hybrid_hardware_commissioning_template.json"
    template = json.loads(template_path.read_text())
    axes = bind_axes(json.loads(contract_path.read_text()), json.loads(layout_path.read_text()))
    if template["contract_sha256"] != sha(contract_path) or template["can_layout_sha256"] != sha(layout_path):
        raise ValueError("Commissioning template source identity mismatch")
    if template["joint_order"] != [a.name for a in axes] or template["hardware_control_release"]:
        raise ValueError("Incorrect current order or invented release")
    if template["positive_power_limit_w"] != json.loads(contract_path.read_text())["positive_mechanical_power_limit_w"]:
        raise ValueError("Current positive power limit mismatch")
    if any(value is not False for key, value in template["whole_release"].items() if key != "evidence_ref"):
        raise ValueError("Template cannot assert bench release")
    for axis, row in zip(axes, template["axes"], strict=True):
        if any(row[key] != (list(value) if isinstance(value, tuple) else value)
               for key, value in asdict(axis).items()):
            raise ValueError("Template binding mismatch")
        if axis.bus != "ttl_5v":
            profile = row["profile"]
            for key, value in profile.items():
                if key == "model":
                    if value != axis.actuator: raise ValueError("Template actuator mismatch")
                elif value is not None and value is not False:
                    raise ValueError("Unknown model profile must not acquire invented defaults")
    tests = ["tests/test_goose_can_transport.py", "tests/test_goose_cubemars_v3.py",
             "tests/test_goose_hybrid_hardware.py", "tests/test_goose_passive_can_capture.py",
             "tests/test_goose_interfaces.py"]
    output_dir = ROOT / "artifacts/Goose_V0.1/hybrid_transport_verification"
    output_dir.mkdir(parents=True, exist_ok=True)
    junit = output_dir / "junit.xml"
    command = [sys.executable, "-m", "pytest", "-q", *tests, "--junitxml", str(junit)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    (output_dir / "pytest.txt").write_text(result.stdout + result.stderr)
    suites = ET.parse(junit).getroot()
    counts = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    test_pass = result.returncode == 0 and counts["tests"] >= 65 and not any(
        counts[k] for k in ("failures", "errors", "skipped"))
    print(result.stdout, end="")
    baseline_commit = "6931ee3b"
    defaults = []
    for rel in ("cad/source/mechanical_preview/scene.json", "configs/mechanical_physics_contract.json",
                "models/mechanical_physics/robot.xml", "evidence/body_bay_mechanical_parameters.json"):
        path = ROBOT / rel
        previous = subprocess.run(["git", "show", baseline_commit + ":" + str(path.relative_to(ROOT))],
                                  cwd=ROOT, check=True, capture_output=True).stdout
        if sha(path) != hashlib.sha256(previous).hexdigest():
            raise ValueError("Unexpected physical baseline change")
        defaults.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path), "unchanged": True})
    docs = [ROBOT / "README.md", ROBOT / "hardware/current_hybrid_control_checkpoint.md",
            ROBOT / "hardware/power_release_checkpoint.md", ROBOT / "design/hardware_milestones.md",
            ROBOT / "design/mechanical_integration_checkpoint.md"]
    link_count = 0
    for path in docs:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link or link.startswith("#"): continue
            link_count += 1
            target = (path.parent / link.split("#", 1)[0]).resolve()
            if not target.exists() and target != ROBOT / "evidence/current_hybrid_transport_checkpoint.json":
                raise ValueError("Missing document target: " + str(target))
    sources = [contract_path, layout_path, template_path, Path(__file__), ROOT / "pyproject.toml",
               ROOT / "uv.lock", ROBOT / "hardware/current_hybrid_transport_sources.json", *docs]
    sources += [ROOT / name for name in tests]
    sources += [ROOT / "src/sai_agent/goose" / name for name in
                ("can_transport.py", "cubemars_v3.py", "hybrid_hardware.py", "hardware.py")]
    sources.append(ROOT / "scripts/diagnostics/inspect_goose_can.py")
    report = {"schema": "goose_current_hybrid_transport_checkpoint_v1",
              "software_verification_pass": test_pass, "test_counts": counts,
              "test_command_relative": ["python", "-m", "pytest", "-q", *tests],
              "active_axis_count": len(axes), "can_a_axis_count": 9, "can_b_axis_count": 8,
              "ttl_axis_count": 1, "axis_bindings": [asdict(a) for a in axes],
              "real_pyserial_library_tested_with_local_pty": True,
              "actual_waveshare_adapter_tested": False, "actual_motor_or_firmware_tested": False,
              "physical_device_specific_profile_confirmed": False,
              "measured_arm64_latency_loss_pass": False,
              "hardware_control_release": False, "power_release": False,
              "training_hard_freeze": False, "stage_three_four_complete": False,
              "default_baseline_commit": baseline_commit, "default_baseline": defaults,
              "local_doc_links_checked": link_count, "missing_local_doc_links": [],
              "source_hashes": {str(path.relative_to(ROOT)): sha(path) for path in sources},
              "limits": ["Synthetic test-only calibration cannot be used as a selected motor profile.",
                         "Protocol/PTY success does not establish drive mode, limits, power safety or physical torque-off.",
                         "Software watchdog cannot stop a drive through a failed host, process or bus.",
                         "Current hardware commissioning template remains deliberately uncommissioned."],
              "next_scope": "Whole-robot power protection selection/installation and assembly paths; no PPO expansion."}
    (ROBOT / "evidence/current_hybrid_transport_checkpoint.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if test_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
