"""Fourteen task-role convex proxies; hardware SI and CAD stay unchanged.

No automatic convex decomposition, CAD-face partition, density-derived mass,
solver changes, or broad joint filtering. Ordinary installation openings are
omitted; the sole and mouth planes get dedicated support samples.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clip(mesh, normal, point):
    n = np.asarray(normal, dtype=float)
    n /= np.linalg.norm(n)
    v = np.asarray(mesh.vertices).copy()
    d = (v - point) @ n
    close = np.abs(d) <= 1e-8
    v[close] -= d[close, None] * n
    d[close] = 0
    vertices, faces, _ = trimesh.intersections.slice_faces_plane(
        v, mesh.faces, n, point, cached_dots=d)
    return trimesh.Trimesh(vertices, faces, process=False)


def main(a):
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "meshes").mkdir()
    parent = a.parent.resolve()
    contract = json.loads((parent / "physical_contract.json").read_text())
    old = json.loads((parent / "collision_manifest.json").read_text())
    origins = {b["name"]: np.array(b["origin_world_zero_m"]) for b in contract["bodies"]}
    source, named = {}, {}
    for r in old["collision_geometries"]:
        mesh = trimesh.load(parent / r["asset"], force="mesh", process=False)
        mesh.vertices += origins[r["body"]]
        source.setdefault(r["body"], []).append((r, mesh))
        named[r["name"]] = (r, mesh)
    directions = np.vstack((np.eye(3), -np.eye(3),
                            trimesh.creation.icosphere(subdivisions=1).vertices))
    rows = []

    def joined(bodies=(), names=()):
        chosen = [x for body in bodies for x in source.get(body, [])]
        chosen += [named[n] for n in names]
        return trimesh.util.concatenate([m for _, m in chosen]), [r["name"] for r, _ in chosen]

    def emit(mesh, name, body, roles, critical=None, note=""):
        vertices = np.asarray(mesh.vertices)
        if len(vertices) < 4:
            raise ValueError("Empty semantic role: " + name)
        picked = [] if critical is None else [p.copy() for p in critical]
        for direction in directions:
            p = vertices[int(np.argmax(vertices @ direction))]
            if not any(np.linalg.norm(p - oldp) < 1e-9 for oldp in picked):
                if len(picked) == 64:
                    break
                picked.append(p)
        hull = trimesh.convex.convex_hull(np.array(picked))
        if len(hull.vertices) > 64 or hull.volume <= 0:
            raise ValueError("Convex role exceeds budget: " + name)
        hull.vertices -= origins[body]
        path = a.output / "meshes" / (name + ".obj")
        hull.export(path, include_normals=False, digits=12)
        rows.append(dict(name=name, body=body, asset="meshes/" + path.name,
                         sha256=sha(path), vertices=len(hull.vertices), triangles=len(hull.faces),
                         source_parent_geometries=roles, source_parts=roles,
                         semantic_role=name, mass_contribution_kg=0.,
                         construction="One low-support convex task role; sampled actual parent contact references",
                         task_approximation=note, ordinary_CAD_detail_not_preserved=True))

    torso, roles = joined(["torso"])
    # One normal convex belly envelope, wider toward the actual front where
    # right HP+.7 must still meet the body. At X=0 the side gap stays70mm.
    # This fixes the measured missed contact without splitting another leaf.
    keel = clip(clip(torso, [.16, 1, 0], np.array([0, -.070, 0])),
                [.16, -1, 0], np.array([0, .070, 0]))
    emit(keel, "torso_central_keel", "torso", roles,
         note="Central belly contact envelope leaves side leg workspace; no installation-hole fidelity claim")
    upper = clip(torso, [0, 0, 1], np.array([0, 0, .300]))
    emit(upper, "torso_upper_envelope", "torso", roles,
         note="Upper mango envelope; root installation void abstracted only at explicit connected neck/hip roles")
    for body in ("neck_pitch", "neck_mid_pitch"):
        mesh, roles = joined([body])
        emit(mesh, body + "_envelope", body, roles,
             note="Single connected neck link; inner fastener holes omitted")
    upper, roles = joined(["head_roll", "head_pitch"])
    pad = named["upper_bill_envelope"][1]
    plane = float(pad.vertices[:, 2].min())
    upper = clip(upper, [0, 0, 1], np.array([0, 0, plane]))
    pv = np.asarray(pad.vertices)
    pv = pv[np.abs(pv[:, 2] - plane) < 2e-6]
    critical = [pv[np.argmax(pv @ np.array([np.cos(t), np.sin(t), 0]))]
                for t in np.arange(8) * np.pi / 4]
    emit(upper, "upper_bill_envelope", "head_roll", roles, critical,
         "Head+upper jaw share actual upper contact plane; rear pitch knuckle is a coarse head envelope, not exact pitch skin")
    lower, roles = joined(["beak_hinge"])
    v = np.asarray(lower.vertices)
    z = v[:, 2].max()
    lip = v[np.abs(v[:, 2] - z) < 2e-6]
    critical = [lip[np.argmax(lip @ np.array([np.cos(t), np.sin(t), 0]))]
                for t in np.arange(8) * np.pi / 4]
    emit(lower, "lower_bill_envelope", "beak_hinge", roles, critical,
         "Independent moving jaw and actual upper pad plane")
    for side, sign in (("left", 1), ("right", -1)):
        body = side + "_hip_roll"
        mesh, roles = joined([body])
        emit(mesh, side + "_hip_envelope", body, roles,
             note="One external hip motor role; connected torso installation overlap is separately declared")
        body = side + "_hip_pitch"
        mesh, roles = joined(names=[side + "_hip_pitch_outer0"])
        mesh = clip(mesh, [0, sign, 0], np.array([0, sign * .114, 0]))
        emit(mesh, side + "_thigh_envelope", body, roles,
             note="External lateral thigh link only; inner bearing cups are installation detail, mass retained")
        body = side + "_knee_pitch"
        mesh, roles = joined([body, side + "_ankle_pitch"], [side + "_hip_pitch_outer2"])
        emit(mesh, side + "_shin_envelope", body, roles,
             note="Shin and approximately rotation-invariant coaxial motor end caps; moving AP cavities omitted")
        body = side + "_ankle_roll"
        mesh, roles = joined([body])
        sole = named[side + "_actual_sole"][1]
        v = np.asarray(sole.vertices)
        bottom = v[np.abs(v[:, 2] - v[:, 2].min()) < 2e-6]
        critical = [bottom[np.argmax(bottom @ np.array([np.cos(t), np.sin(t), 0]))]
                    for t in np.arange(32) * 2 * np.pi / 32]
        critical = np.unique(np.round(critical, 12), axis=0)
        emit(mesh, side + "_actual_sole", body, roles, critical,
             "Single shoe contact envelope;32 sole support directions retained;not a resolved AP installation window")
    if len(rows) != 14:
        raise ValueError("Exactly fourteen convex leaves required")
    adjacency = [("torso", "neck_pitch"), ("torso", "left_hip_roll"),
                 ("torso", "right_hip_roll"), ("neck_mid_pitch", "head_roll"),
                 ("left_knee_pitch", "left_ankle_roll"),
                 ("right_knee_pitch", "right_ankle_roll")]
    result = dict(schema="goose_fourteen_low_support_task_contacts_v1",
                  status="FIRST_CANDIDATE_REQUIRES_INDEPENDENT_FUNCTIONAL_GATES",
                  hardware_parent="physics_v0_2_20261018_02",
                  parent_physical_contract_sha256=sha(parent / "physical_contract.json"),
                  parent_actuator_contract_sha256=sha(parent / "actuator_contract.json"),
                  parent_collision_manifest_sha256=sha(parent / "collision_manifest.json"),
                  producer_sha256=sha(__file__), collision_geometries=rows,
                  torso_keel_side_domain="abs(Y) <= .070 + .16*X (metres); upper envelope unchanged",
                  actual_leaf_count=14, maximum_source_convex_vertices=max(r["vertices"] for r in rows),
                  source_vertex_sum=sum(r["vertices"] for r in rows),
                  by_owner=dict(Counter(r["body"] for r in rows)),
                  explicit_exclusions=adjacency,
                  exclusion_basis="Only directly connected external roles, possibly through an internal axis carrier with no external collision role; same-instance only",
                  explicit_contact_pairs=old["source_collision_metadata"]["explicit_contact_pairs"],
                  collision_geometry_contributes_to_MCI=False,
                  omitted_contact_detail="Internal bearings, screw holes, electronics, installation cup cavities; actual component masses and all23 rigid bodies remain")
    (a.output / "collision_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"collision_geometries"}}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args())
