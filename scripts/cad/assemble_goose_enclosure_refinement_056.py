"""Integrate real enclosure solids with retained Goose hardware, in world mm.

Component factories own their surfaces. This entry point owns retirement,
assembly identity, native exports, render bindings and the incremental mass table.
It never writes the immutable Frozen15 runtime package.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
from cadgen import build123d as b, read_step
from OCP.gp import gp_Trsf
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.TopLoc import TopLoc_Location
from OCP.TopAbs import TopAbs_REVERSED
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/cad"))

RAW = ROOT / "artifacts/goose_v0_2/enclosure_refinement_056"
CAD = ROOT / "robots/goose_v0_2/cad/source/enclosure_refinement_056"
OUT = ROOT / "robots/goose_v0_2/cad/exports/enclosure_refinement_056"
INDEX = ROOT / "robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json"
DISPLAY_IDENTITY = CAD / "retained_display_identity.json"
SERVICE_RETIREMENT = CAD / "service_access_retirement.json"
LEGACY_GEOMETRY = ROOT / "artifacts/goose_v0_2/design_cleanup_052/render_geometry_native.json"
HEAD = ROOT / "robots/goose_v0_2/cad/exports/full_native_head_integration_026/r12_preload048_review/merged_native_manifest.json"
CONTRACT = ROOT / "robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json"
FROZEN = ROOT / "robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/manifest.json"
FROZEN_SHA = "41ee30e7eeb004986daa9ee55d67c4ae74b638615bb2c29f6dcc3c314197df89"
MODULES = {
    "body": "goose_enclosure_body_056",
    "neck": "goose_enclosure_neck_056",
    "limbs": "goose_enclosure_limbs_056",
    "ankle": "goose_ankle_interface_056",
    "service": "goose_enclosure_service_056",
}
# Superseded illustrative curves, explicitly retired by the electrical source.
# Actual native wire components and the harness mass reserve remain unchanged.
OBSOLETE_CABLE_DISPLAY = {f"neck_cable_{i}" for i in range(5)}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def bind_render():
    write(RAW / "render_binding.json", {
        "schema": "native_assembly_display_binding/1",
        "assembly_manifest": ref(CAD / "assembly_manifest.json"),
        "geometry": ref(RAW / "render_geometry.json"),
        "retained_native_input": ref(CAD / "retained_hardware_input.json"),
        "mesh_content_hashes_required": True,
    })


def bounds(shape):
    box = shape.bounding_box()
    return np.array([list(box.min), list(box.max)])


def conservative_bounds(shape):
    box = Bnd_Box()
    BRepBndLib.Add_s(shape.wrapped, box, False)
    values = box.Get()
    return np.asarray([values[:3], values[3:]])


def valid_face_triangulation(face, poly):
    if poly is None or poly.NbTriangles() == 0:
        return False
    # OCCT can report success for a narrow face while inserting a used,
    # uninitialised origin vertex. Remesh that face from native geometry.
    location = TopLoc_Location()
    BRep_Tool.Triangulation_s(face.wrapped, location)
    for index in range(1, poly.NbNodes()+1):
        point = np.asarray(poly.Node(index).Transformed(location.Transformation()).Coord())
        if not np.isfinite(point).all():
            return False
        if np.linalg.norm(point) < 1e-12:
            box = face.bounding_box()
            if min(box.min.Z, box.min.X) > 1 or max(box.max.Z, box.max.X) < -1:
                return False
    return True


def triangulate(shape):
    """Tessellate every actual native face at fixed absolute tolerance."""
    BRepTools.Clean_s(shape.wrapped)
    mesher = BRepMesh_IncrementalMesh(shape.wrapped, .04, False, .08, False)
    assert mesher.IsDone()
    vertices, normals, triangles = [], [], []
    offset = 0
    faces = list(shape.faces())
    for face in faces:
        location = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, location)
        assert valid_face_triangulation(face, poly)
        poly.ComputeNormals()
        transform = location.Transformation()
        reverse = face.wrapped.Orientation() == TopAbs_REVERSED
        for index in range(1, poly.NbNodes() + 1):
            point = poly.Node(index).Transformed(transform)
            normal = poly.Normal(index).Transformed(transform)
            vertices.append([point.X(), point.Y(), point.Z()])
            normals.append(np.asarray([normal.X(), normal.Y(), normal.Z()]) * (-1 if reverse else 1))
        for triangle in poly.Triangles():
            order = (1, 3, 2) if reverse else (1, 2, 3)
            triangles.append([triangle.Value(i) - 1 + offset for i in order])
        offset += poly.NbNodes()
    return np.asarray(vertices), np.asarray(normals), np.asarray(triangles, dtype=np.int32), len(faces)


def load_original_upper():
    """Use the frozen native manifests' rigid placements, without mesh conversion.

    This is the native-loading branch of build_goose_segmented_neck_covers,
    isolated from that legacy renderer's unrelated scipy/trimesh dependencies.
    """
    frozen = ROOT / "robots/Goose_V0.1"
    parameter_path = ROOT / "robots/goose_v0_2/design/concepts/tangpa_mango_ankle_integration_34.json"
    parameters = load(parameter_path)
    datum_path = ROOT / parameters["datum_source"]
    datum = load(datum_path)
    inputs = [ref(parameter_path), ref(datum_path)]
    catalog = {}
    folders = {Path(p["source_npz"]).parent.name for p in datum["physical_parts"]
               if p.get("source_npz") and p["body"] != "torso"
               and not p["body"].startswith(("left_", "right_"))}
    for folder in sorted(folders):
        path = frozen / "cad/exports" / folder / "manifest.json"
        if path.is_file():
            inputs.append(ref(path))
            for part in load(path)["parts"]:
                catalog[part["name"]] = part
    delta = np.asarray(parameters["neck_root_candidate_translation_mm"])
    parts = {}
    for original in datum["physical_parts"]:
        name, body = original["name"], original["body"]
        if body == "torso" or body.startswith(("left_", "right_")):
            continue
        row = catalog.get(name)
        if row and row.get("files", {}).get("brep"):
            source = frozen / row["files"]["brep"]["path"]
            assert sha(source) == row["files"]["brep"]["sha256"]
            tf = row.get("world_from_local_mm", {"rotation": np.eye(3).tolist(), "translation": [0, 0, 0]})
            matrix = np.eye(4)
            matrix[:3, :3] = tf["rotation"]
            matrix[:3, 3] = np.asarray(tf["translation"]) + [0, 0, 3.7] + delta
            transform = gp_Trsf()
            transform.SetValues(*map(float, matrix[:3].ravel()))
            shape = b.import_brep(str(source)).moved(b.Location(transform))
            residual = float(np.abs(bounds(shape) - (np.asarray(original["baseline_bounds_mm"]) + delta)).max())
            assert residual < .08, (name, "Frozen native placement differs", residual)
            provenance = {"source": ref(source), "world_from_local_mm": matrix.tolist(),
                          "representation": "actual_original_native"}
        elif name.endswith("_catalog_case"):
            box = np.asarray(original["baseline_bounds_mm"]) + delta
            size = box[1] - box[0]
            shape = b.Cylinder(float(size[0] / 2), float(size[1])).rotate(b.Axis.X, 90).translate(tuple(box.mean(0)))
            provenance = {"representation": "inherited_explicit_procurement_case_envelope",
                          "source": ref(datum_path), "baseline_bounds_mm": original["baseline_bounds_mm"],
                          "translation_mm": delta.tolist()}
        else:
            continue
        parts[name] = (body, shape, provenance)
    return parts, inputs


def mesh(shape, name, output):
    try:
        vertices, normals, faces, face_count = triangulate(shape)
        tessellation_patches = []
    except AssertionError:
        vertices, normals, faces, face_count, tessellation_patches = mesh_face_patches(shape)
    dest = output / (name.lower() + ".npz")
    dest.parent.mkdir(parents=True, exist_ok=True)
    np.savez(dest, vertices=(vertices / 1000).astype(np.float32),
             normals=normals.astype(np.float32), faces=faces, native_faces=face_count)
    return {"name": name, "path": str(dest), "vertices": len(vertices),
            "mesh_sha256": sha(dest),
            "triangles": len(faces), "native_faces": face_count,
            "tessellation_only_face_partitions": tessellation_patches,
            "original_material": "uncoloured_native_enclosure"}


def mesh_face_patches(shape):
    """Partition a failed *display face*, preserving its native analytic surface.

    A legacy cylindrical bore crosses the UV seam and fails OCCT's direct
    mesher. Native geometry is untouched. Area conservation and tessellation
    success are required for every partition; no face may silently disappear.
    """
    vertices, normals, triangles, witnesses = [], [], [], []
    original_faces = list(shape.faces())
    offset = 0
    for index, original in enumerate(original_faces):
        poly = BRep_Tool.Triangulation_s(original.wrapped, TopLoc_Location())
        pieces = [original]
        if not valid_face_triangulation(original, poly):
            if original.area <= 1e-9:
                witnesses.append({"native_face_index": index, "source_area_mm2": original.area,
                                  "display_triangles": 0, "reason": "zero-area native degeneracy has no visible material surface",
                                  "native_geometry_modified": False})
                continue
            # A valid narrow planar Boolean face can be thinner than the
            # global display tolerance. Tessellate that exact face locally;
            # never remove its positive area to silence the exporter.
            for local_tolerance in [.01, .005, .001, .0001]:
                BRepTools.Clean_s(original.wrapped)
                mesher = BRepMesh_IncrementalMesh(original.wrapped, local_tolerance, False, .04, False)
                poly = BRep_Tool.Triangulation_s(original.wrapped, TopLoc_Location())
                if valid_face_triangulation(original, poly):
                    witnesses.append({"native_face_index": index, "source_area_mm2": original.area,
                                      "local_linear_deflection_mm": local_tolerance,
                                      "display_patches": 1, "patch_mesher_status": int(mesher.GetStatusFlags()),
                                      "native_geometry_modified": False})
                    break
            if valid_face_triangulation(original, poly):
                pieces = [original]
            else:
                pieces = None
        if pieces is None:
            box = bounds(original)
            center = box.mean(0)
            candidates = []
            for direction in [(1, 0, 0), (0, 0, 1), (0, 1, 0)]:
                divided = b.split(original, bisect_by=b.Plane(origin=tuple(center), z_dir=direction), keep=b.Keep.BOTH)
                patches = list(divided.faces())
                error = abs(sum(p.area for p in patches) - original.area)
                if len(patches) <= 1 or error > max(.002, original.area * 2e-6):
                    continue
                valid = True
                statuses = []
                for patch in patches:
                    mesher = BRepMesh_IncrementalMesh(patch.wrapped, .04, False, .08, False)
                    p = BRep_Tool.Triangulation_s(patch.wrapped, TopLoc_Location())
                    statuses.append(int(mesher.GetStatusFlags()))
                    valid &= valid_face_triangulation(patch, p)
                if valid:
                    candidates.append((patches, error, direction, statuses))
                    break
            assert candidates, ("Native face cannot be faithfully tessellated", index, original.area)
            pieces, error, direction, statuses = candidates[0]
            witnesses.append({"native_face_index": index, "source_area_mm2": original.area,
                              "display_patches": len(pieces), "partition_plane_normal": direction,
                              "area_conservation_error_mm2": error, "patch_mesher_status": statuses,
                              "native_geometry_modified": False})
        reverse = original.wrapped.Orientation() == TopAbs_REVERSED
        for piece in pieces:
            location = TopLoc_Location()
            poly = BRep_Tool.Triangulation_s(piece.wrapped, location)
            assert valid_face_triangulation(piece, poly)
            poly.ComputeNormals()
            transform = location.Transformation()
            for i in range(1, poly.NbNodes() + 1):
                p = poly.Node(i).Transformed(transform)
                n = poly.Normal(i).Transformed(transform)
                vertices.append([p.X(), p.Y(), p.Z()])
                normals.append(np.asarray([n.X(), n.Y(), n.Z()]) * (-1 if reverse else 1))
            for triangle in poly.Triangles():
                order = (1, 3, 2) if reverse else (1, 2, 3)
                triangles.append([triangle.Value(k) - 1 + offset for k in order])
            offset += poly.NbNodes()
    return np.asarray(vertices), np.asarray(normals), np.asarray(triangles, dtype=np.int32), len(original_faces), witnesses


def design_properties(shape, row):
    props = GProp_GProps()
    if row.get("module") in ["neck", "limbs"] or row["name"] in ["front_main_shell_056", "rear_service_cap_056"]:
        error = BRepGProp.VolumePropertiesGK_s(shape.wrapped, props, 1e-9, True, True, True, True, False)
        method = "Gauss-Kronrod BRepGProp with BSpline spans; requested relative epsilon 1e-9"
    else:
        error = BRepGProp.VolumeProperties_s(shape.wrapped, props, 1e-7, True, False)
        method = "adaptive BRepGProp; requested relative epsilon 1e-7"
    return props, float(error), method


def physical_delta(shape, row, original):
    """Geometry mass estimates, never writes the immutable runtime contract."""
    if row.get("rigid_displacement_mm") is not None:
        displacement = np.asarray(row["rigid_displacement_mm"]) / 1000
        assert abs(shape.volume - original["native_volume_mm3"]) < max(.01, 1e-6 * shape.volume)
        old_center = original.get("center_of_mass_world_m")
        return {"mass_basis": "unchanged original hardware under rigid translation",
                "mass_kg": original.get("mass_kg"), "mass_delta_kg": 0.0,
                "center_of_mass_world_m": None if old_center is None else (np.asarray(old_center) + displacement).tolist(),
                "inertia_at_com_world_kg_m2": original.get("inertia_at_com_world_kg_m2"),
                "separate_unit_mass_allocation_must_remain": original.get("mass_kg") is None}
    density = row.get("density_kg_m3", row.get("mass_density_assumption_kg_m3"))
    if density is None and row.get("material_candidate", "").startswith("PA12"):
        density = 1010.0
    if density is None:
        return {"mass_basis": "material density not yet selected", "mass_kg": None}
    props, error, method = design_properties(shape, row)
    mass = float(props.Mass()) * density * 1e-9
    inertia = props.MatrixOfInertia()
    original_mass = 0.0 if original is None else original.get("mass_kg")
    return {"mass_basis": "unmeasured homogeneous design material, not purchased or measured mass",
            "density_kg_m3": density, "mass_kg": mass,
            "mass_delta_kg": None if original_mass is None else mass - original_mass,
            "separate_original_unit_allocation_unresolved": original is not None and original_mass is None,
            "center_of_mass_world_m": (np.asarray(props.CentreOfMass().Coord()) / 1000).tolist(),
            "inertia_at_com_world_kg_m2": [[inertia.Value(i+1, j+1) * density * 1e-15 for j in range(3)] for i in range(3)],
            "integration_method": method,
            "integration_error": float(error)}


def build_components(selected):
    entry_identity = ref(Path(__file__))
    assert (RAW / "retained_geometry_manifest.json").is_file(), "Create the native display cache with --phase parent-mesh first"
    index, geometry, contract = load(INDEX), load(DISPLAY_IDENTITY)["parts"], load(CONTRACT)
    pivots = {j["name"]: np.array(j["pivot_world_at_zero_m"]) * 1000 for j in contract["joints"]}
    records = []
    retired = set()
    if "body" in selected:
        retirement = load(SERVICE_RETIREMENT)
        for group in retirement["groups"]:
            assert group["status"] == "owner_approved_access_transferred_to_removable_full_shell"
            retired.update(part["name"] for part in group["parts"])
    shapes = []
    # Native08 contains both the original flat representation and the later
    # nested homogeneous property schema. Preserve explicit None allocations.
    old_by_name = {p["name"]: {**p.get("homogeneous_mass_properties", {}), **p}
                   for p in index["parts"]}
    for key in selected:
        module = importlib.import_module(MODULES[key])
        module_identity = ref(Path(module.__file__))
        context = dict(root=ROOT, pivots=pivots, artifacts=RAW,
                       native_index=index, native_geometry=geometry)
        if key == "body":
            context["artifacts"] = RAW / "body"
        if key == "limbs":
            context["nominal_wall_mm"] = 1.8
        if key == "ankle":
            context["artifacts"] = RAW / "ankle"
        if key == "service":
            context["artifacts"] = RAW / "service/integration_build"
        parts = module.build(context)
        assert ref(Path(module.__file__)) == module_identity, "Factory changed while building; rebuild a stable revision"
        retired.update(getattr(module, "RETIRED_NAMES", []))
        for part in parts:
            shape = part["shape"]
            name = part["name"]
            assert shape.is_valid and len(shape.solids()) == 1 and shape.volume > 0, name
            shape.label = name
            dest = CAD / (name.lower() + ".brep")
            b.export_brep(shape, str(dest))
            row = {k: v for k, v in part.items() if k != "shape"}
            for field in ("replaces", "retire_display_names", "retire_previous_cosmetic"):
                retired.update(row.get(field, []))
            if row.get("rigid_displacement_mm") is not None:
                native_volume, volume_error = float(shape.volume), None
                volume_method = "unchanged original native geometry under rigid translation; original mass and inertia preserved"
            else:
                volume_properties, volume_error, volume_method = design_properties(shape, {**row, "module": key})
                native_volume = float(volume_properties.Mass())
            row.update(native=ref(dest), volume_mm3=native_volume,
                       fixed_order_volume_mm3_diagnostic=float(shape.volume),
                       volume_method=volume_method,
                       volume_integration_error=volume_error,
                       bounds_mm=conservative_bounds(shape).tolist(),
                       optimized_kernel_bounds_mm=bounds(shape).tolist(),
                       bounds_method="OCCT Add_s without triangulation; conservative surface/control bounds, not a tight size measurement",
                       optimized_kernel_bounds_unsafe_for_collision_pruning=True,
                       native_valid=True,
                       source=module_identity, module=key)
            original = old_by_name.get(row.get("replacement_for"))
            row["physical_estimate"] = physical_delta(shape, row, original)
            if not row.get("replacement_for") and key in ["neck", "limbs"]:
                # Alternative polymer densities, not a measured assembly mass.
                row["mass_range_kg_density_1010_to_1270"] = [row["volume_mm3"] * d * 1e-9 for d in (1010, 1270)]
            # Display the saved native object, avoiding stale child objects in
            # transformed build123d wrappers.
            row.update(mesh(b.import_brep(str(dest)), name, RAW / "geometry"))
            records.append(row)
            shapes.append(shape)
            print(json.dumps({"native_component": name, "volume_mm3": shape.volume}), flush=True)
    names = [r["name"] for r in records]
    assert ref(Path(__file__)) == entry_identity, "Assembly entry changed while building; rebuild a stable revision"
    assert len(names) == len(set(names)), "Duplicate component names"
    previous_names = {r["name"] for r in geometry} | set(old_by_name)
    assert retired <= previous_names, sorted(retired - previous_names)
    structural_retirement = [n for n in retired if "visible_structural_" in n]
    assert not structural_retirement, structural_retirement
    native_display = RAW / "retained_geometry_manifest.json"
    if native_display.is_file():
        display = load(native_display)
        assert display["native_parent"] == ref(CAD / "retained_hardware_input.json")
        geometry = display["parts"]
    for row in geometry:
        actual_hash = sha(row["path"])
        assert row.get("mesh_sha256", actual_hash) == actual_hash, row["name"]
        row["mesh_sha256"] = actual_hash
        if "native_source" not in row:
            row["native_source"] = {"input": ref(CAD / "retained_hardware_input.brep.gz"),
                                    "solid_start": row["source_native_solid_start"],
                                    "solid_count": row["source_native_solid_count"]}
    compose = [r for r in geometry if r["name"] not in retired | OBSOLETE_CABLE_DISPLAY] + [
        {**{k: r[k] for k in ("name", "path", "mesh_sha256", "vertices", "triangles", "original_material")},
         "native_source": r["native"]}
        for r in records]
    write(RAW / "render_geometry.json", compose)
    b.export_step(b.Compound(children=shapes), str(OUT / "enclosures_056.step"))
    report = {
        "schema": "goose_enclosure_refinement_056/1",
        "status": "NATIVE_ASSEMBLY_CANDIDATE_UNDER_REVIEW",
        "modules": selected, "source": entry_identity,
        "parts": records, "retired_previous_covers": sorted(retired),
        "retired_known_mass_kg": sum(float(old_by_name.get(n, {}).get("mass_kg") or 0) for n in retired),
        "retired_names_without_mass": [n for n in retired if not old_by_name.get(n, {}).get("mass_kg")],
        "new_cover_mass_range_kg": np.sum([r["mass_range_kg_density_1010_to_1270"] for r in records if "mass_range_kg_density_1010_to_1270" in r], axis=0).tolist(),
        "new_cover_mass_range_scope": "Density sensitivity of the new neck/limb pieces without an original replacement allocation only; excludes body and hardware. It is not the selected-material bill of materials or a whole-robot mass.",
        "native_hardware_replacements": [{"old": r["replacement_for"], "new": r["name"]} for r in records if r.get("replacement_for")],
        "physical_estimates_are_not_runtime_contract": True,
        "parent_display_identity": ref(DISPLAY_IDENTITY), "parent_native_index": ref(INDEX),
        "obsolete_service_doors_retirement": ref(SERVICE_RETIREMENT) if "body" in selected else None,
        "parent_native_input": ref(CAD / "retained_hardware_input.json"),
        "head15_binding": ref(HEAD), "axes": ref(CONTRACT),
        "frozen15": ref(FROZEN), "runtime_files_modified": False,
        "structural_members_retired": [], "enclosures_STEP": ref(OUT / "enclosures_056.step"),
        "display_composition": ref(RAW / "render_geometry.json"),
        "unresolved": ["Complete motion sweep", "All retained-hardware static intersections",
                       "Mounting and service assembly details", "Material/process validation",
                       "Final same-version mass, COM and inertia before a physical release"],
    }
    write(CAD / "assembly_manifest.json", report)
    bind_render()
    return shapes, records, retired, report


def prepare_parent():
    """Restore retained native originals; do not turn display meshes into CAD."""
    cache_file = CAD / "retained_hardware_input.brep.gz"
    cache_manifest = CAD / "retained_hardware_input.json"
    unpacked = RAW / "retained_hardware_readback.brep"
    if cache_manifest.is_file() and cache_file.is_file():
        receipt = load(cache_manifest)
        assert sha(cache_file) == receipt["compressed_native"]["sha256"]
        assert ref(INDEX) == receipt["native08_index"] and ref(HEAD) == receipt["head15_manifest"]
        if not unpacked.is_file() or sha(unpacked) != receipt["uncompressed_native_sha256"]:
            with gzip.open(cache_file, "rb") as source, unpacked.open("wb") as target:
                while block := source.read(1024 * 1024):
                    target.write(block)
        assert sha(unpacked) == receipt["uncompressed_native_sha256"]
        solids = list(b.import_brep(str(unpacked)).solids())
        assert len(solids) == receipt["native_solids"]
        shapes = {}
        for row in receipt["parts"]:
            group = solids[row["solid_start"]:row["solid_start"] + row["solid_count"]]
            shape = group[0] if len(group) == 1 else b.Compound(children=group)
            assert float(np.abs(bounds(shape) - np.asarray(row["bounds_mm"])).max()) < .02, (row["name"], "Cached native occurrence placement differs")
            shape.label = row["name"]
            shapes[row["name"]] = shape
        return shapes, receipt["parts"]
    # Bootstrap only: normal builds use the self-contained native input above.
    # Legacy mesh bounds verify placements while reconstructing that input;
    # they are never converted into CAD.
    index, geometry, head = load(INDEX), load(LEGACY_GEOMETRY), load(HEAD)
    native_file = ROOT / "artifacts/goose_v0_2/design_cleanup_052/native08_readback.brep"
    assert sha(native_file) == index["uncompressed_native_sha256"]
    native = list(b.import_brep(str(native_file)).solids())
    assert len(native) == len(index["parts"])
    by_name = {p["name"]: p for p in index["parts"]}
    retained_head = {p["name"]: p for p in head["retained_parts"]}
    # The original fork STEP files are joint-local. Reuse the existing native
    # loader, including its documented world_from_local transforms, rather than
    # guessing an installation from an image or a bounding-box centre.
    actual_upper, upper_inputs = load_original_upper()
    source_files = {}
    for p in (ROOT / "robots/Goose_V0.1/cad/exports").rglob("*.step"):
        source_files.setdefault(p.stem, []).append(p)
    shapes, records, missing = {}, [], []
    for part in geometry:
        name = part["name"]
        if name.startswith("native15_") or name in OBSOLETE_CABLE_DISPLAY:
            continue
        if name in by_name:
            old = by_name[name]
            shape = native[old["native_part_index"]]
            provenance = {"source": ref(INDEX), "native_part_index": old["native_part_index"]}
            body = old["body"]
        elif name in retained_head:
            old = retained_head[name]
            src = ROOT / old["source"]["path"]
            assert sha(src) == old["source"]["sha256"]
            shape = read_step(str(src)).translate((-13.55, 0, 32.305))
            provenance = {"source": old["source"], "translation_mm": [-13.55, 0, 32.305],
                          "authority": "Frozen15 retained native head manifest"}
            body = old["body"]
        elif name in actual_upper:
            body, shape, original_provenance = actual_upper[name]
            with np.load(part["path"]) as data:
                expected = np.array([data["vertices"].min(0), data["vertices"].max(0)]) * 1000
            residual = float(np.max(np.abs(bounds(shape) - expected)))
            assert residual < .40, (name, "Original installation differs", residual)
            provenance = {**original_provenance,
                          "placement_authority": ref(ROOT / "scripts/cad/build_goose_segmented_neck_covers.py"),
                          "source_inputs": upper_inputs,
                          "bounds_residual_to_bound_display_mm": residual}
        else:
            with np.load(part["path"]) as data:
                expected = np.array([data["vertices"].min(0), data["vertices"].max(0)]) * 1000
            matches = []
            for src in source_files.get(name, []):
                candidate = read_step(str(src))
                for delta in [(-13.55, 0, 32.305), (0, 0, 0)]:
                    placed = candidate.translate(delta)
                    error = float(np.max(np.abs(bounds(placed) - expected)))
                    if error <= .40:
                        matches.append((error, placed, src, delta))
            if not matches:
                missing.append({"name": name, "candidate_sources": [str(p) for p in source_files.get(name, [])],
                                "expected_bounds_mm": expected.tolist()})
                continue
            matches.sort(key=lambda q: q[0])
            error, shape, src, delta = matches[0]
            provenance = {"source": ref(src), "translation_mm": list(delta),
                          "bounds_residual_to_bound_display_mm": error,
                          "authority": "Retained original native source; placement checked against bound display"}
            body = None
        shape.label = name
        shapes[name] = shape
        records.append({"name": name, "body": body, **provenance, "bounds_mm": bounds(shape).tolist()})
    # The native index also retains a few internal components absent from the
    # old display export. Include them rather than silently dropping hardware.
    for old in index["parts"]:
        name = old["name"]
        if name in shapes or name in head["retired"]:
            continue
        shape = native[old["native_part_index"]]
        shape.label = name
        shapes[name] = shape
        records.append({"name": name, "body": old["body"], "source": ref(INDEX),
                        "native_part_index": old["native_part_index"],
                        "restored_internal_component_absent_from_display": True,
                        "bounds_mm": bounds(shape).tolist()})
    for old in head["new_parts"]:
        src = ROOT / old["source"]["path"]
        assert sha(src) == old["source"]["sha256"]
        assert old["rotation_xyz_deg"] == [0, 0, 0]
        shape = read_step(str(src)).translate(tuple(old["translation_to_zero_mm"]))
        shape.label = old["name"]
        assert old["name"] not in shapes
        shapes[old["name"]] = shape
        records.append({"name": old["name"], "body": old["body"], "source": old["source"],
                        "translation_mm": old["translation_to_zero_mm"], "bounds_mm": bounds(shape).tolist()})
    write(RAW / "parent_native_readback.json", {"parts": records, "missing_native_sources": missing,
                                               "retired_obsolete_illustrative_cable_curves": sorted(OBSOLETE_CABLE_DISPLAY),
                                               "cable_retirement_authority": [ref(ROOT / "scripts/diagnostics/prepare_goose_electrical_harness.py"),
                                                                              ref(ROOT / "scripts/diagnostics/check_goose_clocked_jst_local_installation.py")],
                                               "cable_mass_credit_kg": 0,
                                               "native_source_reconstruction_from_mesh": False})
    assert not missing, "Original native sources unresolved; see parent_native_readback.json"
    # A self-contained native input for reproducibility. Preserve compound
    # occurrences by indexing their actual solid ranges; never fuse hardware.
    position = 0
    for row in records:
        count = len(shapes[row["name"]].solids())
        assert count > 0, row["name"]
        row.update(solid_start=position, solid_count=count)
        position += count
    b.export_brep(b.Compound(children=list(shapes.values())), str(unpacked))
    with unpacked.open("rb") as source, gzip.open(cache_file, "wb", compresslevel=6) as target:
        while block := source.read(1024 * 1024):
            target.write(block)
    write(cache_manifest, {"schema": "source_bound_retained_native_hardware_input/1",
                           "native08_index": ref(INDEX), "head15_manifest": ref(HEAD),
                           "compressed_native": ref(cache_file), "uncompressed_native_sha256": sha(unpacked),
                           "native_solids": position, "parts": records,
                           "mesh_to_native_conversion": False, "cable_mass_credit_kg": 0,
                           "obsolete_illustrative_cable_curves_retired": sorted(OBSOLETE_CABLE_DISPLAY),
                           "COTS_case_envelopes_are_inherited_not_supplier_CAD": True})
    return shapes, records


def mesh_parent(shapes, records):
    output = RAW / "retained_geometry"
    output.mkdir(parents=True, exist_ok=True)
    old_display = {p["name"]: p for p in load(DISPLAY_IDENTITY)["parts"]}
    rows = []
    for i, part in enumerate(records):
        name = part["name"]
        row = mesh(shapes[name], name, output)
        row["original_material"] = old_display.get(name, {}).get("original_material", "retained_actual_hardware")
        row["source_native_solid_start"] = part["solid_start"]
        row["source_native_solid_count"] = part["solid_count"]
        row["native_source"] = {"input": ref(CAD / "retained_hardware_input.brep.gz"),
                                "solid_start": part["solid_start"], "solid_count": part["solid_count"]}
        rows.append(row)
        if i % 100 == 0:
            print(json.dumps({"native_parent_meshed": i, "total": len(records)}), flush=True)
    write(RAW / "retained_geometry_manifest.json", {"native_parent": ref(CAD / "retained_hardware_input.json"),
                                                   "all_native_occurrences_meshed": len(rows),
                                                   "linear_deflection_mm": .04, "angular_deflection_rad": .08,
                                                   "parts": rows, "omitted_occurrences": []})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["components", "parent", "parent-mesh", "assembly"], default="components")
    ap.add_argument("--modules", nargs="+", choices=list(MODULES), default=list(MODULES))
    args = ap.parse_args()
    start = time.monotonic()
    assert sha(FROZEN) == FROZEN_SHA
    for folder in [RAW, RAW / "geometry", CAD, OUT]:
        folder.mkdir(parents=True, exist_ok=True)
    if args.phase in ["parent", "parent-mesh"]:
        shapes, records = prepare_parent()
        if args.phase == "parent-mesh":
            mesh_parent(shapes, records)
        print(json.dumps({"native_parent_parts": len(shapes), "elapsed_s": time.monotonic() - start}), flush=True)
        return
    shapes, records, retired, report = build_components(args.modules)
    if args.phase == "assembly":
        old_shapes, old_records = prepare_parent()
        for name in retired:
            assert name in old_shapes, name
            del old_shapes[name]
        combined = list(old_shapes.values()) + shapes
        step = OUT / "goose_enclosure_refinement_056.step"
        b.export_step(b.Compound(children=combined), str(step))
        report["complete_native_STEP"] = ref(step)
        compressed_step = step.with_suffix(step.suffix + ".gz")
        with step.open("rb") as source, compressed_step.open("wb") as output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=6) as target:
                shutil.copyfileobj(source, target)
        report["complete_native_STEP_gzip"] = ref(compressed_step)
        report["complete_native_STEP_distribution"] = "Git contains the gzip; decompress to the declared STEP path before opening. No native geometry is reconstructed from display meshes."
        report["complete_native_occurrences"] = len(combined)
        report["parent_retained_occurrences"] = len(old_shapes)
        write(CAD / "assembly_manifest.json", report)
        bind_render()
    assert sha(FROZEN) == FROZEN_SHA
    print(json.dumps({"component_count": len(records), "elapsed_s": time.monotonic() - start,
                      "runtime_modified": False}), flush=True)


if __name__ == "__main__":
    main()
