"""Read back the delivered native STEP and the untouched training baseline."""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
from cadgen import build123d as b
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/cad"))
import assemble_goose_enclosure_refinement_056 as assembly


def volume_mm3(shape):
    # Adaptive integration is necessary for the thin BSpline enclosures.
    # The default fixed-order integral can under-estimate their volume.
    props = GProp_GProps()
    error = BRepGProp.VolumeProperties_s(shape.wrapped, props, 1e-7, True, False)
    return float(props.Mass()), float(error)


def main():
    start = time.monotonic()
    manifest_path = assembly.CAD / "assembly_manifest.json"
    manifest = assembly.load(manifest_path)
    saved = manifest["complete_native_STEP"]
    compressed = manifest["complete_native_STEP_gzip"]
    archive = ROOT / compressed["path"]
    assert assembly.sha(archive) == compressed["sha256"]
    destination = ROOT / saved["path"]
    if not destination.exists():
        with gzip.open(archive, "rb") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)
    assert assembly.sha(destination) == saved["sha256"]

    old_shapes, _ = assembly.prepare_parent()
    retired = set(manifest["retired_previous_covers"])
    expected = [s for n, s in old_shapes.items() if n not in retired]
    for row in manifest["parts"]:
        path = ROOT / row["native"]["path"]
        assert assembly.sha(path) == row["native"]["sha256"], row["name"]
        expected.append(b.import_brep(str(path)))
    expected_solids = sum(len(s.solids()) for s in expected)
    expected_volume = sum(volume_mm3(s)[0] for s in expected)
    expected_bounds = np.asarray([assembly.bounds(s) for s in expected])
    expected_bounds = np.array([expected_bounds[:, 0].min(0), expected_bounds[:, 1].max(0)])
    actual = b.import_step(str(destination))
    actual_solids = len(actual.solids())
    actual_volume, actual_integration_error = volume_mm3(actual)
    volume_error = abs(actual_volume - expected_volume)
    bound_error = float(np.abs(assembly.bounds(actual) - expected_bounds).max())
    assert actual_solids == expected_solids, (actual_solids, expected_solids)
    assert volume_error <= max(.1, abs(expected_volume) * 1e-6), volume_error
    assert bound_error <= .002, bound_error
    result = {
        "schema": "goose_native_exchange_readback_056/1",
        "source": assembly.ref(Path(__file__)),
        "assembly_manifest": assembly.ref(manifest_path),
        "compressed_STEP": compressed, "saved_STEP": saved,
        "expected_native_occurrences": len(expected),
        "expected_solids": expected_solids, "actual_solids": actual_solids,
        "expected_volume_mm3": expected_volume, "actual_volume_mm3": actual_volume,
        "absolute_volume_error_mm3": volume_error,
        "native_volume_method": "adaptive BRepGProp aggregate transfer diagnostic; epsilon 1e-7; not the per-component mass authority",
        "actual_volume_integration_error": actual_integration_error,
        "maximum_bound_error_mm": bound_error,
        "volume_tolerance": "max(0.1 mm3, 1e-6 of expected aggregate volume)",
        "bound_tolerance_mm": .002,
        "pass": True,
        "scope": "Native STEP transfer identity/count/aggregate geometry only; not motion, material, strength or manufacture qualification.",
        "elapsed_s": time.monotonic() - start,
    }
    assembly.write(assembly.RAW / "native_exchange_readback.json", result)
    frozen = assembly.load(assembly.FROZEN)
    assert assembly.sha(assembly.FROZEN) == assembly.FROZEN_SHA
    checked = []
    for relative, digest in frozen["files"].items():
        path = assembly.FROZEN.parent / relative
        assert assembly.sha(path) == digest, relative
        checked.append(relative)
    assembly.write(assembly.RAW / "frozen15_integrity.json", {
        "source": assembly.ref(Path(__file__)),
        "frozen_manifest": assembly.ref(assembly.FROZEN),
        "files_checked": checked, "file_count": len(checked), "all_hashes_match": True,
        "runtime_replaced_or_retrained": False,
    })
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
