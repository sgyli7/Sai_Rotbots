"""Six non-load-bearing open-inner link covers from native pitch-fork inputs.

This is a bounded aesthetic sample: attachment, moving sweep and thermal
behavior are deliberately unreleased. No existing structure or model is edited.
Engineering CAD is a thin NURBS solid; the render source is its structured
closed all-quad construction, not a repaired triangular STL.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh
from build123d import export_brep, export_step, import_step

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"
sys.path[:0] = [str(ROOT / "scripts/cad"), str(ROOT / "scripts/models")]
from goose_nurbs_skin import skin, surface, native_properties
from build_goose_cad import transform, cylinder
from build_goose_stage_two import candidate
from sai_agent.goose.morphology import apply_leg_layout
from sai_agent.native_cad import common_solid_volume_mm3, boundary_surface_distance_mm, sampled_skin_quads


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(t: np.ndarray, panel_y: float, open_y: float, corner: float,
            half_flat: float) -> np.ndarray:
    """U path: open at inner Y, two end returns, rounded outer-side panel.

    n,Y cross-plane coordinates; increasing path has outward normals under
    longitudinal-direction cross path-direction. Outer/inner share corner
    centers, producing exactly 1.4 mm nominal section thickness.
    """
    center_y = panel_y - 4.0
    output = []
    for a in t:
        if a < .20:
            y = open_y + (center_y - open_y) * a / .20
            n = -(half_flat + corner)
        elif a < .35:
            angle = (a - .20) / .15 * np.pi / 2
            n = -half_flat - corner * np.cos(angle)
            y = center_y + corner * np.sin(angle)
        elif a < .65:
            n = -half_flat + 2 * half_flat * (a - .35) / .30
            y = center_y + corner
        elif a < .80:
            angle = (a - .65) / .15 * np.pi / 2
            n = half_flat + corner * np.sin(angle)
            y = center_y + corner * np.cos(angle)
        else:
            n = half_flat + corner
            y = center_y + (open_y - center_y) * (a - .80) / .20
        output.append([n, y])
    return np.asarray(output)


def closed_quads(out: np.ndarray, inside: np.ndarray):
    nu, nv = out.shape[:2]
    vertices = np.concatenate([out.reshape(-1, 3), inside.reshape(-1, 3)])
    cells = []
    base = nu * nv
    for i in range(nu - 1):
        for j in range(nv - 1):
            a, b = i * nv + j, (i + 1) * nv + j
            cells.append([a, b, b + 1, a + 1])
            cells.append([a + base + 1, b + base + 1, b + base, a + base])
    boundary = ([j for j in range(nv)]
                + [i * nv + nv - 1 for i in range(1, nu)]
                + [(nu - 1) * nv + j for j in range(nv - 2, -1, -1)]
                + [i * nv for i in range(nu - 2, 0, -1)])
    for a, b in zip(boundary, boundary[1:] + boundary[:1]):
        cells.append([a, b, b + base, a + base])
    # The U traversal on the outward-Y panel has e cross tangent inward;
    # reverse the analytically constructed winding for the complete surface.
    faces = np.asarray(cells, dtype=np.int64)[:, ::-1]
    triangles = np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]])
    mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError(("structured quad construction is not a positive closed solid",
                          mesh.is_watertight, mesh.is_winding_consistent, mesh.volume))
    return vertices, faces, mesh


def main():
    source = ROBOT / "cad/source/link_cover_samples"
    exports = ROBOT / "cad/exports/link_cover_samples"
    source.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    layout_path = ROBOT / "configs/body_bay_layout_candidate.json"
    inputs = [layout_path]
    original = json.loads((ROBOT / "cad/exports/pitch_fork_assembly/manifest.json").read_text())
    legs = json.loads((ROBOT / "cad/exports/body_bay_pitch_forks/manifest.json").read_text())
    records_in = [p for p in original["parts"] if "neck" in p["name"]] + legs["parts"]
    assemblies = [a for a in original["assemblies"] if "neck" in a["name"]] + legs["assemblies"]
    for folder in ["pitch_fork_assembly", "body_bay_pitch_forks"]:
        inputs.extend([ROBOT / f"cad/exports/{folder}/manifest.json",
                       ROBOT / f"cad/source/{folder}/quad_scene.json"])
    structure = candidate()
    apply_leg_layout(structure, json.loads(layout_path.read_text()))
    native_parts = []
    for p in records_in:
        step_path = ROBOT / p["files"]["step"]["path"]
        local = import_step(step_path)
        tf = p["world_from_local_mm"]
        world = transform(local, np.array(tf["rotation"]), np.array(tf["translation"]))
        native_parts.append((p["name"], world))
    all_parts, scene, checks = [], [], []
    for a in assemblies:
        label, owner = a["name"], a["owner"]
        record = next(p for p in records_in if p["name"] == label + "_output_fork_plate")
        frame = record["world_from_local_mm"]
        rotation, origin = np.asarray(frame["rotation"]), np.asarray(frame["translation"])
        lower = a["lower_joint"]
        b = rotation.T @ (structure.pivots[lower] * 1000 - origin)
        direction = b / np.linalg.norm(b)
        length = float(np.linalg.norm(b))
        # Legs cover their outward output side. Neck covers the visible right
        # idler side; the opposite side remains fully open for inspection.
        side = -1 if "neck" in label else 1
        outward_y = np.array([0., float(side), 0.])
        n_axis = np.cross(direction, outward_y)
        near = a["near_plate_center_local_y_mm"] + 2.75
        far = a["far_plate_center_local_y_mm"] - 2.75
        panel_y = (near if side == 1 else -far) + 6.0
        center_y = (a["near_plate_center_local_y_mm"] + a["far_plate_center_local_y_mm"]) / 2
        open_y = side * center_y + 2.0
        # This end exclusion preserves full motor discs and mounting holes.
        start, end = 33.0, length - 33.0
        if end - start < 15:
            raise ValueError((label, "insufficient cover length", length))
        stations = np.linspace(start, end, 9)
        # Canonicalize construction parameters before interpolation. Almost
        # equal floating-point knot values must not create revisited points.
        across = np.unique(np.round(np.concatenate([np.linspace(0, 1, 41), [.2, .35, .65, .8]]), 12))
        out = np.zeros((len(stations), len(across), 3))
        inside = out.copy()
        for i, u in enumerate(stations):
            v = (u - start) / (end - start)
            # Gently tuck the ends rather than adding bulky ball-shaped caps.
            flat = 10.5 + 2.0 * np.sin(np.pi * v) ** 2
            inner_sec = section(across, panel_y, open_y, 4.0, flat)
            outer_sec = section(across, panel_y, open_y, 5.4, flat)
            inside[i] = direction * u + np.outer(inner_sec[:, 0], n_axis) + np.outer(inner_sec[:, 1], outward_y)
            out[i] = direction * u + np.outer(outer_sec[:, 0], n_axis) + np.outer(outer_sec[:, 1], outward_y)
        shape = skin(out, inside, np.ones((len(stations) - 1, len(across) - 1), dtype=bool))
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError((label, "invalid native cover"))
        volume, com, inertia, integration_error = native_properties(shape)
        vertices, quads = sampled_skin_quads(surface(out), surface(inside),
                                            np.ones((len(stations)-1,len(across)-1),bool), factor=4)
        triangles = np.concatenate([quads[:,[0,1,2]], quads[:,[0,2,3]]])
        mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise ValueError((label, "source quad topology"))
        volume_error = abs(mesh.volume - volume) / volume
        if volume_error > .005:
            raise ValueError((label, "structured quad volume differs from native CAD", volume_error))
        name = label + "_open_inner_cover"
        brep, step = source / (name + ".brep"), exports / (name + ".step")
        export_brep(shape, brep)
        export_step(shape, step)
        rt = import_step(step)
        rvol, *_ = native_properties(rt)
        if not rt.is_valid or len(rt.solids()) != 1 or abs(rvol - volume) / volume > 1e-5:
            raise ValueError((name, "STEP roundtrip"))
        world_vertices = vertices @ rotation.T + origin
        npz = source / (name + "_quad.npz")
        np.savez_compressed(npz, vertices=world_vertices / 1000, faces=quads)
        # ASCII STL is a distinct, triangulated exchange, not the editable quad source.
        stl = exports / (name + ".stl")
        stl.write_text(trimesh.exchange.stl.export_stl_ascii(mesh))
        exchange = trimesh.load(stl, force="mesh", process=True)
        if (not exchange.is_watertight or not exchange.is_winding_consistent
                or exchange.volume <= 0 or abs(exchange.volume-volume)/volume > .005):
            raise ValueError((name, "STL geometric topology or volume roundtrip"))
        world = transform(shape, rotation, origin)
        failures = []
        min_distance = float("inf")
        min_partner = ""
        screw_envelopes = []
        for u in [-4.0, 4.0]:
            for side_y in [near + 2.25, far - 2.25]:
                center = direction * (length/2 + u) + np.array([0.,side_y,0.])
                head = cylinder(3.1,4.5,center,'y')
                screw_envelopes.append((label + "_bridge_screw_head_envelope_" + str(len(screw_envelopes)),
                                        transform(head, rotation, origin)))
        wa = world.bounding_box()
        distances = []
        for other_name, other in native_parts + screw_envelopes:
            overlap = common_solid_volume_mm3(world, other)
            if overlap > 1e-3:
                failures.append({"part": other_name, "overlap_mm3": overlap})
            bb = other.bounding_box()
            gap = np.maximum(np.maximum(np.asarray(list(bb.min))-np.asarray(list(wa.max)),
                                        np.asarray(list(wa.min))-np.asarray(list(bb.max))), 0)
            distances.append((float(np.linalg.norm(gap)),other_name,other))
        for lower_bound,other_name,other in sorted(distances,key=lambda row:row[0]):
            if lower_bound >= min_distance:
                continue
            distance = boundary_surface_distance_mm(world,other)
            if distance < min_distance:
                min_distance, min_partner = distance, other_name
        density = 1270.
        part = dict(name=name, body=owner, material="petg_white_candidate", density_kg_m3=density,
                    volume_mm3=volume, mass_kg=volume * density * 1e-9,
                    center_of_mass_world_m=((rotation @ com + origin) / 1000).tolist(),
                    inertia_at_com_world_kg_m2=(rotation @ (inertia * density * 1e-15) @ rotation.T).tolist(),
                    world_from_local_mm=dict(rotation=rotation.tolist(), translation=origin.tolist()),
                    native_valid=True, closed_quad_source=True, quad_faces=len(quads),
                    nominal_wall_mm=1.4, wall_status="nominal constant section; longitudinal curvature and interpolation not metrologically qualified",
                    longitudinal_interval_from_proximal_mm=[start, end], link_length_mm=length,
                    side="right_idler" if side < 0 else "outward_output", inner_side_open=True,
                    native_to_quad_volume_relative_error=volume_error,
                    step_volume_relative_error=abs(rvol-volume)/volume,
                    native_integration_error=integration_error,
                    attachment_pass=False, manufacturing_released=False,
                    notes=["Non-load-bearing appearance sample; no screws, clips or adhesive are present.",
                           "Retention and service/removal path remain unreleased; do not install and operate from this sample alone.",
                           "Only static native forks plus conservative central bridge screw-head envelopes are screened; no complete robot, wire or moving clearance.",
                           "Each cover follows one rigid link. No existing carrier/fork holes have been modified."], files={})
        for p in [brep, step, stl, npz]:
            part["files"][p.suffix[1:]] = dict(path=str(p.relative_to(ROBOT)), sha256=sha(p))
        all_parts.append(part)
        scene.append(dict(name=name, body=owner, group="link_cover_samples", material="ivory",
                          role="non_load_bearing_cover_attachment_unreleased",
                          geometry_npz=str(npz.relative_to(ROBOT)), source_sha256=sha(npz)))
        checks.append(dict(name=name, native_fork_static_interference_pass=not failures,
                           minimum_native_fork_clearance_mm=min_distance, closest_part=min_partner,
                           interference=failures, coverage_scope="two neck and four leg native pitch assemblies plus four central bridge screw-head envelopes per cover at neutral candidate pivots"))
        print(name, "mass_g", round(part["mass_kg"] * 1000, 2), "min_gap_mm", round(min_distance, 3), "failures", len(failures), flush=True)
    manifest = dict(schema="goose_link_cover_samples_v1", status="AESTHETIC_SAMPLE_NOT_ATTACHMENT_OR_MANUFACTURING_RELEASE",
                    geometry_unit="mm", quad_geometry_unit="m", physical_rigid_lift_mm=0,
                    reference_note="unlifted CAD pivots; parent assembly must apply the same rigid lift as every other part",
                    manufacturing_pass=False, attachment_pass=False, moving_sweep_pass=False, thermal_pass=False,
                    static_native_fork_interference_pass=all(x["native_fork_static_interference_pass"] for x in checks),
                    total_shell_mass_kg=sum(x["mass_kg"] for x in all_parts),
                    neck_shell_mass_kg=sum(x["mass_kg"] for x in all_parts if "neck" in x["name"]),
                    mass_excludes=["attachment hardware", "paint", "wire management"],
                    source_quad_kind="structured NURBS construction, closed all quad; native BREP/STEP is authoritative",
                    source_hashes={str(p.relative_to(ROOT)): sha(p) for p in inputs + [Path(__file__)]},
                    parts=all_parts, static_checks=checks)
    (exports / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (source / "quad_scene.json").write_text(json.dumps(dict(unit="m", status=manifest["status"], parts=scene), indent=2) + "\n")
    print("cover total mass_g", round(manifest["total_shell_mass_kg"] * 1000, 2), flush=True)


if __name__ == "__main__":
    main()
