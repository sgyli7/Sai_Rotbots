"""Measure selective Goose collision filtering using deliberately overlapping hulls.

Collider placements in these fixtures are artificial; they do not qualify a
physical pose, trajectory, material or manufacturing interference clearance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / "robots/Goose_V0.1"
MODEL = ROBOT / "models/task_proxy_11_v1/robot.xml"
CONTRACT = ROBOT / "configs/task_proxy_11_v1_contract.json"
PLANT = MODEL.parent / "native_plant.json"
POLICY = ROBOT / "configs/task_proxy_11_v1_collision_filter.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collision_policy():
    """Document the existing compiled filters, including built-in parent filters."""
    plant = json.loads(PLANT.read_text())
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    assert not (model.opt.disableflags & mujoco.mjtDisableBit.mjDSBL_FILTERPARENT)
    parents = {b["name"]: b["parent"] for b in plant["bodies"]}
    owners = {g["body"]: g["name"] for g in plant["colliders"]}
    exclusions = {frozenset(p) for p in plant["exclusions"]}
    rows = []
    for first, second in itertools.combinations(plant["colliders"], 2):
        a, b = first["body"], second["body"]
        direct = parents[a] == b or parents[b] == a
        explicit = frozenset((a, b)) in exclusions
        allowed_mask = bool((first["contype"] & second["conaffinity"])
                            or (second["contype"] & first["conaffinity"]))
        assert allowed_mask, "This profile preserves all non-excluded self contact"
        enabled = not (direct or explicit)
        chain = []
        if not enabled:
            # A justified skip may cross small internal axis carriers, but never
            # another exterior collision role. Proximity at one pose is not adjacency.
            for start, end in ((a, b), (b, a)):
                path = [start]
                while path[-1] != end and parents.get(path[-1]) is not None:
                    path.append(parents[path[-1]])
                if path[-1] == end:
                    chain = path
                    break
            assert chain and not any(n in owners for n in chain[1:-1])
        rows.append(dict(first=first["name"], second=second["name"],
                         collision_enabled=enabled,
                         reason=("retained_self_contact" if enabled else
                                 "explicit_connected_role_exception" if explicit else
                                 "native_direct_joint_parent_filter"),
                         connected_body_chain=chain))
    assert len(rows) == 55 and sum(not r["collision_enabled"] for r in rows) == 9
    return dict(schema="goose_collision_filter_policy_v1",
                candidate_id="goose_task_proxy_11_v1",
                model_sha256=sha(MODEL), contract_sha256=sha(CONTRACT),
                native_plant_sha256=sha(PLANT),
                self_collision_default="enabled", exception_scope="one_robot_instance",
                ground_collision="enabled_for_every_role",
                object_collision="enabled_for_every_role",
                other_robot_collision="enabled_including_same_named_roles",
                rule="Only the listed mechanically connected adjacent role pairs may overlap without self-contact. Every unlisted pair remains enabled.",
                pairs=rows,
                external_geometry_kind="convex_hull",
                target_qualification="Source MuJoCo and standalone Rapier filter fixtures; this policy is not Unity/Godot runtime acceptance.")


def validate_policy(policy):
    if policy != collision_policy():
        raise ValueError("Collision policy differs from the bound selective source profile")


def source_filter_probe():
    tree = ET.parse(MODEL).getroot()
    plant = json.loads(PLANT.read_text())
    original = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(original)
    mujoco.mj_forward(original, data)
    geometries = {g.get("name"): g for g in tree.findall(".//geom")}
    mesh_assets = {m.get("name"): m for m in tree.findall("./asset/mesh")}
    vertex_means = {}
    for g in plant["colliders"]:
        mesh = mesh_assets[geometries[g["name"]].get("mesh")]
        assert mesh.get("scale", "1 1 1") == "1 1 1"
        path = MODEL.parent / mesh.get("file")
        points = [list(map(float, line.split()[1:4])) for line in path.read_text().splitlines()
                  if line.startswith("v ")]
        vertex_means[g["name"]] = np.mean(points, axis=0)

    def fixture(first, second=None, *, scope="same_instance", unfiltered=False):
        root = copy.deepcopy(tree)
        world = root.find("worldbody")
        selected = [first] + ([second] if second else [])
        names = {g["name"] for g in selected}
        center = np.array([2., 2., 0. if scope == "ground" else 3.])
        for parent in root.iter():
            for child in list(parent):
                if child.tag == "geom" and child.get("name") not in names:
                    if not (scope == "ground" and child.get("name") == "ground"):
                        parent.remove(child)
        for index, g in enumerate(selected):
            geom = next(gx for gx in root.iter("geom") if gx.get("name") == g["name"])
            bid = original.body(g["body"]).id
            quat = np.array(list(map(float, geom.get("quat", "1 0 0 0").split())))
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, quat)
            target = center + (np.array([.003, -.002, .001])
                               if index and scope != "other_robot" else 0)
            target_local = data.xmat[bid].reshape(3, 3).T @ (target - data.xpos[bid])
            position = target_local - rotation.reshape(3, 3) @ vertex_means[g["name"]]
            geom.set("pos", " ".join(format(v, ".17g") for v in position))
        second_name = second["name"] if second else scope
        if scope == "object":
            body = ET.SubElement(world, "body", name="fixture_object", pos=" ".join(map(str, center)))
            ET.SubElement(body, "geom", name="object", type="sphere", size=".005",
                          contype="1", conaffinity="1")
        if scope == "other_robot":
            peer = copy.deepcopy(world.find("body"))
            for node in peer.iter():
                if "name" in node.attrib:
                    node.set("name", node.get("name") + "_peer")
            peer.set("pos", ".003 -.002 .001")
            peer_role = second["name"] if second else first["name"]
            for body, keep in ((world.find("body"), first["name"]), (peer, peer_role + "_peer")):
                for parent in body.iter():
                    for child in list(parent):
                        if child.tag == "geom" and child.get("name") != keep:
                            parent.remove(child)
            world.append(peer)
            second_name = peer_role + "_peer"
        # Resolve assets explicitly; only the selected original hulls are loaded.
        used = {g.get("mesh") for g in root.iter("geom") if g.get("mesh")}
        for mesh in list(root.find("asset")):
            if mesh.tag == "mesh" and mesh.get("name") not in used:
                root.find("asset").remove(mesh)
            elif mesh.tag == "mesh":
                mesh.set("file", str((MODEL.parent / mesh.get("file")).resolve()))
        root.find("compiler").set("meshdir", ".")
        if unfiltered:
            root.find("option/flag").set("filterparent", "disable")
            for exclude in list(root.find("contact")):
                root.find("contact").remove(exclude)
        model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
        state = mujoco.MjData(model)
        mujoco.mj_forward(model, state)
        a, b = model.geom(first["name"]).id, model.geom(second_name).id
        raw = float(mujoco.mj_geomDistance(model, state, a, b, 1., None))
        assert np.isfinite(raw) and raw < -1e-5, "Fixture lacks unfiltered penetration witness"
        contacts = [c for c in state.contact if set(c.geom) == {a, b}]
        solver_rows = sum(int(c.efc_address >= 0) for c in contacts)
        return dict(raw_unfiltered_distance_m=raw, source_contact_points=len(contacts),
                    source_solver_contacts=solver_rows,
                    minimum_filtered_distance_m=min((float(c.dist) for c in contacts), default=None),
                    collision_enabled=bool(contacts and solver_rows))

    rows = []
    for first, second in itertools.combinations(plant["colliders"], 2):
        measurement = fixture(first, second)
        # In addition to a distance query, exercise native contact generation
        # with the same hulls/topology and just the filtering disabled.
        control = fixture(first, second, unfiltered=True)
        assert control["collision_enabled"], (first["name"], second["name"], control)
        rows.append(dict(scope="same_instance", first=first["name"], second=second["name"],
                         measurement=measurement, unfiltered_positive_control=control))
    for first in plant["colliders"]:
        for scope in ("ground", "object", "other_robot"):
            rows.append(dict(scope=scope, first=first["name"],
                             second=first["name"] if scope == "other_robot" else scope,
                             measurement=fixture(first, scope=scope)))
    roles = {g["name"]: g for g in plant["colliders"]}
    for pair in collision_policy()["pairs"]:
        if not pair["collision_enabled"]:
            first, second = (roles[pair[k]] for k in ("first", "second"))
            rows.append(dict(scope="other_robot", first=first["name"], second=second["name"],
                             measurement=fixture(first, second, scope="other_robot")))
    return rows


def check_rows(rows, policy):
    expected = {(r["first"], r["second"]): r["collision_enabled"] for r in policy["pairs"]}
    seen = set()
    for row in rows:
        key = (row["scope"], row["first"], row["second"])
        assert key not in seen
        seen.add(key)
        wanted = expected[(row["first"], row["second"])] if row["scope"] == "same_instance" else True
        actual = row["measurement"]
        assert actual["raw_unfiltered_distance_m"] < -1e-5
        assert actual["collision_enabled"] is wanted, key
        prefix = "source" if "source_contact_points" in actual else "native"
        if wanted:
            assert actual[prefix + "_contact_points"] > 0
            assert actual[prefix + "_solver_contacts"] > 0
            assert actual["minimum_filtered_distance_m"] < 0
        else:
            assert actual[prefix + "_contact_points"] == 0
            assert actual[prefix + "_solver_contacts"] == 0
            assert actual["minimum_filtered_distance_m"] is None
    roles = {r["first"] for r in policy["pairs"]} | {r["second"] for r in policy["pairs"]}
    required = {("same_instance", a, b) for a, b in expected}
    required.update((s, a, a if s == "other_robot" else s)
                    for s in ("ground", "object", "other_robot") for a in roles)
    required.update(("other_robot", a, b) for (a, b), enabled in expected.items() if not enabled)
    assert seen == required
    return dict(total_fixtures=len(rows), same_instance_pairs=55,
                ignored_connected_pairs=9, retained_self_pairs=46,
                ground_positive_fixtures=11, object_positive_fixtures=11,
                cross_instance_positive_fixtures=20, passed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-policy", action="store_true")
    parser.add_argument("--native-probe", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/Goose_V0.1/collision_filters")
    args = parser.parse_args()
    policy = collision_policy()
    if args.write_policy:
        POLICY.write_text(json.dumps(policy, indent=2) + "\n")
    validate_policy(json.loads(POLICY.read_text()))
    args.out.mkdir(parents=True, exist_ok=True)
    source = source_filter_probe()
    results = {"source": check_rows(source, policy)}
    (args.out / "source.json").write_text(json.dumps(source, indent=2) + "\n")
    if args.native_probe:
        native_path = args.out / "native.json"
        subprocess.run([str(args.native_probe.resolve()), str(PLANT), str(CONTRACT),
                        str(native_path), "collision_filters"], check=True)
        native = json.loads(native_path.read_text())
        results["standalone_rapier"] = check_rows(native["rows"], policy)
    report = dict(schema="goose_collision_filter_acceptance_v1",
                  candidate_id=policy["candidate_id"], model_sha256=sha(MODEL),
                  contract_sha256=sha(CONTRACT), native_plant_sha256=sha(PLANT),
                  collision_policy_sha256=sha(POLICY), results=results,
                  mujoco=mujoco.__version__, native_binary_sha256=sha(args.native_probe) if args.native_probe else None,
                  diagnostic="Injected collider placements, 97 fixtures per backend. Source has zero integrations; Rapier has one pipeline integration per fixture. These are filter tests, not physical trajectory or CAD clearance acceptance.",
                  full_task_success_claim=False,
                  unity_runtime_qualified=False, godot_runtime_qualified=False,
                  source_report_sha256=sha(args.out / "source.json"),
                  native_report_sha256=sha(args.out / "native.json") if args.native_probe else None,
                  evaluator_sha256=sha(Path(__file__)),
                  receiver_source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                                         (ROOT / "integrations/bevy/goose_task_proxy/src").glob("*.rs")})
    (args.out / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
