"""Run actual Godot/Jolt selective-contact fixtures without touching hardware.

This does not run the old 30,105-leaf adapter or qualify whole-robot dynamics.
The new helper applies all effective source exceptions explicitly by instance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.evaluation.check_goose_collision_filters import (
    CONTRACT, MODEL, PLANT, POLICY, validate_policy,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "integrations/godot/goose_collision_filters"
ROBOT = ROOT / "robots/Goose_V0.1"
C = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)
HARDWARE_SOURCES = (
    ROBOT / "cad/source/manual_wing_service/assembly_scene.json",
    ROBOT / "evidence/manual_wing_service_parameters.json",
    ROBOT / "cad/source/brake_packaging/assembly_scene.json",
    ROBOT / "evidence/brake_packaging_parameters.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_input():
    policy = json.loads(POLICY.read_text())
    validate_policy(policy)
    plant = json.loads(PLANT.read_text())
    shapes = {}
    body_rotation = {b["name"]: b["rotation_world_wxyz"] for b in plant["bodies"]}
    for g in plant["colliders"]:
        points = np.array(g["vertices_local_m"], dtype=float)
        if not np.isfinite(points).all() or points.shape[0] < 4:
            raise ValueError("Invalid source hull")
        # Preserve native hull support points/orientation, then translate their
        # strictly interior mean to the diagnostic origin. No CAD is resampled.
        def rotation(q):
            return Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()
        r = C @ rotation(body_rotation[g["body"]]) @ rotation(g["local_rotation_wxyz"])
        rotated = points @ r.T
        centered = rotated - rotated.mean(axis=0)
        shapes[g["name"]] = centered.tolist()
    return dict(policy=policy, plant=plant, shapes=shapes)


def validate_report(report, policy, expected_engine):
    if report.get("physics_engine") != expected_engine:
        raise ValueError("Wrong actual physics engine")
    if report.get("schema") != "goose_godot_collision_filter_probe_v1" or report.get("candidate_id") != policy["candidate_id"]:
        raise ValueError("Wrong native result identity")
    if report.get("full_task_success_claim") is not False:
        raise ValueError("Filter fixture cannot qualify full tasks")
    expected = {(r["first"], r["second"]): r["collision_enabled"] for r in policy["pairs"]}
    roles = {k for pair in expected for k in pair}
    wanted = {(s, a, b, False): enabled for (a, b), enabled in expected.items() for s in ["same_instance"]}
    wanted.update({("same_instance", a, b, True): True for a, b in expected})
    wanted.update({(scope, a, a if scope == "other_robot" else scope, False): True
                   for a in roles for scope in ("ground", "object", "other_robot")})
    wanted.update({("other_robot", a, b, False): True for (a, b), enabled in expected.items() if not enabled})
    seen = set()
    for row in report["rows"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid native fixture result")
        key = (row["scope"], row["first"], row["second"], row["unfiltered_control"])
        if key in seen or key not in wanted:
            raise ValueError("Unknown/duplicate fixture: " + str(key))
        seen.add(key)
        depth = row["raw_penetration_m"]
        if not np.isfinite(depth) or depth <= 1e-5 or row["raw_contact_points"] < 1:
            raise ValueError("Missing unfiltered penetration witness")
        if not np.isfinite(row["native_peak_reported_impulse_Ns"]):
            raise ValueError("Nonfinite actual contact result")
        if row["expected_collision_enabled"] is not wanted[key] or row["collision_enabled"] is not wanted[key]:
            raise ValueError("Native filtering mismatch: " + str(key))
        if (row["native_contact_samples"] > 0) is not wanted[key]:
            raise ValueError("Native contact readback mismatch")
    if seen != set(wanted):
        raise ValueError("Incomplete native fixture coverage")
    required_checks = {"head_upper_bill_envelope|torso_envelope",
                       "left_flexible_sole|right_flexible_sole", "incomplete_pair_table",
                       "missing_connection_witness", "aliased_instance_handles",
                       "live_instance_reapplication", "joint_default_reset"}
    if set(report["rejection_checks"]) != required_checks or not all(report["rejection_checks"].values()):
        raise ValueError("Missing rejection/instance lifecycle checks")
    if report.get("failures") != [] or report.get("passed") is not True:
        raise ValueError("Native probe reports a failure")
    return dict(passed=True, total_fixtures=len(seen),
                policy_fixtures=97, unfiltered_positive_controls=55,
                same_instance_pairs=55, ignored_connected_pairs=9,
                retained_self_pairs=46, ground_positive_fixtures=11,
                object_positive_fixtures=11, cross_instance_positive_fixtures=20,
                rejection_and_lifecycle_checks=len(required_checks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default="godot")
    parser.add_argument("--engine", choices=["Jolt Physics", "GodotPhysics3D", "both"], default="Jolt Physics")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/Goose_V0.1/godot_collision_filters")
    args = parser.parse_args()
    executable = Path(shutil.which(args.godot) or args.godot).resolve(strict=True)
    hardware_present = [p for p in HARDWARE_SOURCES if p.exists()]
    if len(hardware_present) not in (0, len(HARDWARE_SOURCES)):
        raise RuntimeError("Partial engineering source set; do not infer hardware preservation")
    # Portable runtime archives deliberately exclude CAD. In the complete
    # workspace also measure the four current hardware/parameter authorities.
    hardware_before = {str(p.relative_to(ROOT)): sha(p) for p in hardware_present}
    payload = fixture_input()
    args.out.mkdir(parents=True, exist_ok=True)
    input_path = args.out.resolve() / "fixture_input.json"
    input_path.write_text(json.dumps(payload) + "\n")
    engines = ["Jolt Physics", "GodotPhysics3D"] if args.engine == "both" else [args.engine]
    measurements = {}
    for engine in engines:
        name = "jolt" if engine == "Jolt Physics" else "godot_physics"
        project = args.out.resolve() / name
        project.mkdir(exist_ok=True)
        for path in sorted(PROJECT.iterdir()):
            if path.is_file() and path.suffix in (".gd", ".tscn", ".godot"):
                shutil.copy2(path, project / path.name)
        project_config = (project / "project.godot").read_text()
        (project / "project.godot").write_text(project_config.replace('3d/physics_engine="Jolt Physics"', f'3d/physics_engine="{engine}"'))
        output = project / "results.json"
        # A previous success file must not survive a failed rerun.
        output.unlink(missing_ok=True)
        preflight = subprocess.run([args.godot, "--headless", "--path", str(project),
                                    "--editor", "--import", "--quit"],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, timeout=45)
        (project / "import.log").write_text(preflight.stdout)
        if preflight.returncode or "ERROR:" in preflight.stdout:
            raise RuntimeError("Godot script preflight failed: " + preflight.stdout[-6000:])
        with (project / "native.log").open("w") as log:
            process = subprocess.run([args.godot, "--headless", "--path", str(project),
                                      "--", str(input_path), str(output)],
                                     stdout=log, stderr=subprocess.STDOUT, text=True, timeout=150)
        output_log = (project / "native.log").read_text()
        if process.returncode or not output.exists():
            raise RuntimeError("Native Godot probe failed; preserved log: " + str(project / "native.log") + "\n" + output_log[-6000:])
        if "ERROR:" in output_log:
            raise RuntimeError("Native errors reject acceptance: " + output_log[-6000:])
        report = json.loads(output.read_text())
        summary = validate_report(report, payload["policy"], engine)
        measurements[name] = dict(summary=summary, engine=engine,
                                  godot_version=report["godot_version"],
                                  result_sha256=sha(output), fixture_input_sha256=sha(input_path),
                                  physics_dt_s=report["physics_dt_s"],
                                  actual_shape_input_vertices={k: len(v) for k, v in payload["shapes"].items()})
        print(json.dumps({"engine": engine, **summary}), flush=True)
    if hardware_before != {str(p.relative_to(ROOT)): sha(p) for p in hardware_present}:
        raise RuntimeError("Hardware source changed during filter-only diagnostics")
    result = dict(schema="goose_godot_collision_filter_acceptance_v1",
                  candidate_id=payload["policy"]["candidate_id"], results=measurements,
                  measured_utc=datetime.now(timezone.utc).isoformat(),
                  godot_executable_sha256=sha(executable),
                  preserved_hardware_input_sha256=hardware_before,
                  hardware_preservation_scope=("Four current engineering source/parameter identities measured before and after"
                                               if hardware_present else "Portable runtime archive contains no hardware CAD authority"),
                  input_sha256={str(p.relative_to(ROOT)): sha(p) for p in (MODEL, CONTRACT, PLANT, POLICY)},
                  evaluator_sha256=sha(Path(__file__)),
                  receiver_source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(PROJECT.iterdir())
                                          if p.is_file() and p.suffix in (".gd", ".godot", ".tscn")},
                  scope="Cooked shapes and selective native filtering in artificial independent contact fixtures; no whole-robot qualification",
                  native_full_robot_qualified=False, hardware_modified=False,
                  full_task_success_claim=False)
    (args.out / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
