"""Verify a frozen Goose package and optionally load it without advancing time.

Supports both historical list manifests and candidate path-to-SHA manifests.
Does not change a package, call mj_step, or grant motion/hardware qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def verify(package: Path, zero_step_load: bool = False) -> dict:
    package = package.resolve()
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    files = manifest["files"]
    rows = (
        [{"path": name, "sha256": digest} for name, digest in files.items()]
        if isinstance(files, dict)
        else files
    )
    errors = []
    for row in rows:
        path = (package / row["path"]).resolve()
        if not path.is_relative_to(package) or not path.is_file():
            errors.append("Missing or nonlocal: " + row["path"])
            continue
        if "bytes" in row and path.stat().st_size != row["bytes"]:
            errors.append("Wrong size: " + row["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            errors.append("Wrong hash: " + row["path"])
    result = {
        "package": str(package),
        "release_id": manifest.get("release_id"),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "verified_files": len(rows),
        "passed": not errors,
        "errors": errors,
        "physics_steps": 0,
        "scope": "File integrity and optional zero-step loading only; no dynamics or hardware qualification.",
    }
    if zero_step_load and not errors:
        import numpy as np

        spec = importlib.util.spec_from_file_location(
            "goose_frozen_package_040", package / "runtime_adapter.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load the package adapter")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        physics = module.FrozenPhysics(package)
        model, data = physics.model, physics.data
        load = {
            "time_s": float(data.time),
            "mass_kg": float(np.sum(model.body_mass)),
            "public_axes": len(physics.names),
            "actuators": int(model.nu),
            "bodies_including_world": int(model.nbody),
            "internal_equalities": int(model.neq),
            "hidden_body_force_max": float(np.max(np.abs(data.xfrc_applied))),
            "hidden_generalized_force_max": float(np.max(np.abs(data.qfrc_applied))),
            "input_continuous_cap_Nm": float(physics.cont[5]),
            "noslip_iterations": int(model.opt.noslip_iterations),
            "physics_dt_s": float(model.opt.timestep),
            "drive_dt_s": float(physics.drive_dt),
            "public_dt_s": float(physics.policy_dt),
        }
        result["zero_step_load"] = load
        if (
            load["time_s"] != 0.0
            or load["hidden_body_force_max"] != 0.0
            or load["hidden_generalized_force_max"] != 0.0
            or not np.isfinite(load["mass_kg"])
            or load["mass_kg"] <= 0
        ):
            errors.append("Invalid zero-step state")
            result["passed"] = False
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--zero-step-load", action="store_true")
    parser.add_argument("--receipt", type=Path)
    arguments = parser.parse_args()
    receipt = verify(arguments.package, arguments.zero_step_load)
    output = json.dumps(receipt, indent=2) + "\n"
    if arguments.receipt:
        arguments.receipt.write_text(output)
    print(output, end="")
    raise SystemExit(0 if receipt["passed"] else 1)
