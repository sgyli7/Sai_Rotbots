"""Source-bound native checks, separate from appearance or physics release."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from cadgen import build123d as b
from OCP.BRepAlgoAPI import BRepAlgoAPI_Check, BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopTools import TopTools_ListOfShape
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/cad"))
import assemble_goose_enclosure_refinement_056 as assembly


def quality(shape):
    return {"BRepCheck_strict": bool(BRepCheck_Analyzer(shape.wrapped, True, False, True).IsValid()),
            "BOP_including_self_intersection": bool(BRepAlgoAPI_Check(shape.wrapped, True, True).IsValid()),
            "solids": len(shape.solids()), "volume_mm3": float(shape.volume)}


def conservative_bounds(shape):
    # Add_s encloses the native surface/control representation. AddOptimal
    # can underestimate a trimmed periodic loft; it is unsuitable for pruning
    # a possible interference merely because a displayed bound is smaller.
    box = Bnd_Box()
    BRepBndLib.Add_s(shape.wrapped, box, False)
    values = box.Get()
    return np.asarray([values[:3], values[3:]])


def common(a, bshape):
    alo, ahi = conservative_bounds(a)
    blo, bhi = conservative_bounds(bshape)
    if np.any(np.minimum(ahi, bhi) - np.maximum(alo, blo) <= 1e-7):
        return {"method": "disjoint_native_bounds", "volume_mm3": 0.0, "valid": True}
    distance = BRepExtrema_DistShapeShape()
    distance.LoadS1(a.wrapped)
    distance.LoadS2(bshape.wrapped)
    distance.Perform()
    if distance.IsDone() and not distance.InnerSolution() and distance.Value() > 1e-5:
        return {"method": "native_positive_minimum_distance", "volume_mm3": 0.0,
                "native_minimum_distance_mm": distance.Value(), "valid": True}
    operation = BRepAlgoAPI_Common()
    arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    arguments.Append(a.wrapped)
    tools.Append(bshape.wrapped)
    operation.SetArguments(arguments)
    operation.SetTools(tools)
    operation.SetNonDestructive(True)
    operation.SetRunParallel(False)
    operation.SetFuzzyValue(1e-7)
    operation.Build()
    if not operation.IsDone():
        return {"method": "native_Common", "valid": False, "reason": "Boolean did not complete"}
    result = b.Compound(operation.Shape())
    solids = list(result.solids())
    volume = float(sum(s.volume for s in solids))
    return {"method": "native_Common", "valid": bool(result.is_valid and volume >= -1e-6),
            "volume_mm3": volume, "solids": len(solids)}


def original_neck():
    parts, inputs = assembly.load_original_upper()
    lower = {n: s for n, (_, s, _) in parts.items() if n.startswith("lower_neck_") and "fork" in n}
    upper = {n: s for n, (_, s, _) in parts.items() if n.startswith("upper_neck_") and "fork" in n}
    pivot = (-43.55, 0, 544.305)
    rows = []
    for angle in [-80.21409131831524, 0.0, 80.21409131831524]:
        for ln, ls in lower.items():
            for un, us in upper.items():
                moved = us.rotate(b.Axis(pivot, (0, 1, 0)), angle)
                row = {"mid_pitch_deg": angle, "lower": ln, "upper": un, **common(ls, moved)}
                rows.append(row)
                print(json.dumps(row), flush=True)
    return {"scope": "Original lower/upper fork plates only, three joint states; not a complete robot motion qualification",
            "inputs": inputs, "fork_quality": {n: quality(s) for n, s in {**lower, **upper}.items()},
            "checks": rows, "new_geometry_included": False}


def components():
    manifest = assembly.load(assembly.CAD / "assembly_manifest.json")
    rows = []
    for row in manifest["parts"]:
        source = ROOT / row["native"]["path"]
        assert assembly.sha(source) == row["native"]["sha256"]
        shape = b.import_brep(str(source))
        result = {"name": row["name"], "source": row["native"], **quality(shape)}
        result["pass"] = bool(result["BRepCheck_strict"] and result["BOP_including_self_intersection"]
                              and result["solids"] == 1 and result["volume_mm3"] > 0)
        rows.append(result)
        print(json.dumps(result), flush=True)
    return {"scope": "Saved new solids, strict native topology and self-intersection checks only",
            "assembly_manifest": assembly.ref(assembly.CAD / "assembly_manifest.json"),
            "checks": rows, "all_pass": all(r["pass"] for r in rows)}


def static_neck():
    manifest = assembly.load(assembly.CAD / "assembly_manifest.json")
    new = [r for r in manifest["parts"] if r["module"] == "neck"]
    assert new
    old_shapes, old_records = assembly.prepare_parent()
    retired = set(manifest["retired_previous_covers"])
    bounds = {r["name"]: conservative_bounds(old_shapes[r["name"]]) for r in old_records if r["name"] not in retired}
    checks = []
    for row in new:
        path = ROOT / row["native"]["path"]
        assert assembly.sha(path) == row["native"]["sha256"]
        shape = b.import_brep(str(path))
        box = conservative_bounds(shape)
        for name, other in bounds.items():
            if np.any(np.minimum(box[1], other[1]) - np.maximum(box[0], other[0]) <= 1e-6):
                continue
            result = {"cover": row["name"], "hardware": name, "cover_deformable": row.get("deformable", False),
                      **common(shape, old_shapes[name])}
            checks.append(result)
            if not result["valid"] or result.get("volume_mm3", 0) > .01:
                print(json.dumps(result), flush=True)
            assembly.write(assembly.RAW / "neck_native_static_checkpoint.json", {"checks": checks})
    return {"scope": "All saved new neck solids vs all retained native occurrences at actual zero pose; no motion or flexible deformation qualification",
            "assembly_manifest": assembly.ref(assembly.CAD / "assembly_manifest.json"),
            "checks": checks,
            "intersections": [r for r in checks if not r["valid"] or r.get("volume_mm3", 0) > .01]}


def interfaces():
    """Check actual independently produced modules in the saved assembly.

    These are zero-pose interfaces, not a replacement for the modules' motion
    checks or flexible-material qualification. Bolted component mates within
    one factory are left to their explicit interface receipts.
    """
    manifest = assembly.load(assembly.CAD / "assembly_manifest.json")
    rows = manifest["parts"]
    by_name = {r["name"]: r for r in rows}
    shapes = {}

    def native(row):
        name = row["name"]
        if name not in shapes:
            path = ROOT / row["native"]["path"]
            assert assembly.sha(path) == row["native"]["sha256"]
            shapes[name] = b.import_brep(str(path))
        return shapes[name]

    shells = [by_name[n] for n in ["front_main_shell_056", "rear_service_cap_056"]]
    exterior = [r for r in rows if r["module"] in ["neck", "limbs"]]
    ankle = [r for r in rows if r["module"] == "ankle"]
    limbs = [r for r in rows if r["module"] == "limbs"]
    service = [r for r in rows if r["module"] == "service"]
    pairs = [(a, c) for a in shells for c in exterior + service]
    pairs += [(a, c) for a in ankle for c in limbs]
    checks = []
    for left, right in pairs:
        result = {"a": left["name"], "b": right["name"],
                  "a_native": left["native"], "b_native": right["native"],
                  **common(native(left), native(right))}
        checks.append(result)
        if not result["valid"] or result.get("volume_mm3", 0) > .01:
            print(json.dumps(result), flush=True)
    return {"scope": "Saved final body vs new neck/limbs/service and modified ankle hardware vs limb covers at actual zero pose; no full-ROM or flexible-material qualification",
            "assembly_manifest": assembly.ref(assembly.CAD / "assembly_manifest.json"),
            "checks": checks,
            "intersections": [r for r in checks if not r["valid"] or r.get("volume_mm3", 0) > .01]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["original-neck", "components", "static-neck", "interfaces"], required=True)
    args = ap.parse_args()
    started = time.monotonic()
    report = {"original-neck": original_neck, "components": components, "static-neck": static_neck,
              "interfaces": interfaces}[args.scope]()
    if args.scope == "components":
        report["pass"] = report["all_pass"]
    elif args.scope in ["static-neck", "interfaces"]:
        report["pass"] = not report["intersections"]
    report["elapsed_s"] = time.monotonic() - started
    report["source"] = assembly.ref(Path(__file__))
    assembly.write(assembly.RAW / (args.scope.replace("-", "_") + "_strict_check.json"), report)
    if report.get("pass") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
