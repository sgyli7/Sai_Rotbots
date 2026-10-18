"""Independent finite task-contact review of a reduced Goose collision model.

Does not construct or modify collision assets. Hardware contract, compiled mass,
joint properties, exact mouth fixtures and non-adjacent participation are read
back from the candidate rather than inferred from a producer report.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
from scipy.spatial import ConvexHull


def identity(path):
    p = Path(path).resolve()
    return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def load_helper(package):
    spec = importlib.util.spec_from_file_location("fixed_source_contact_definitions", package / "verify_contacts.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def vertices(m, d, g):
    mid = int(m.geom_dataid[g])
    lo, count = int(m.mesh_vertadr[mid]), int(m.mesh_vertnum[mid])
    return m.mesh_vert[lo:lo+count].astype(float) @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]


def run(package, baseline, model_path):
    helper = load_helper(baseline)
    source_contract = json.loads((baseline / "physical_contract.json").read_text())
    contract_path = package / "physical_contract.json"
    contract = json.loads(contract_path.read_text()) if contract_path.exists() else source_contract
    m = mujoco.MjModel.from_xml_path(str(model_path))
    source = mujoco.MjModel.from_xml_path(str(baseline / "robot.xml"))
    d, sd = mujoco.MjData(m), mujoco.MjData(source)
    failures = []
    checks = []
    for field in ("body_mass", "body_ipos", "body_inertia", "body_iquat", "body_pos", "body_quat",
                  "jnt_axis", "jnt_pos", "jnt_range", "jnt_type", "dof_frictionloss", "dof_armature", "dof_damping",
                  "actuator_gear", "actuator_ctrlrange", "actuator_forcerange", "actuator_gainprm", "actuator_biasprm",
                  "actuator_trnid", "eq_data", "eq_obj1id", "eq_obj2id", "eq_type"):
        a, b = np.asarray(getattr(m, field)), np.asarray(getattr(source, field))
        delta = float(np.max(np.abs(a-b))) if a.shape == b.shape and a.size else (0.0 if a.shape == b.shape else None)
        passed = delta is not None and delta <= 1e-12
        checks.append(dict(field=field, candidate_shape=list(a.shape), baseline_shape=list(b.shape), max_abs_delta=delta, passed=passed))
        if not passed:
            failures.append("Compiled hardware change: " + field)
    contract_identities = []
    for filename in ("physical_contract.json","actuator_contract.json"):
        a, b = identity(package/filename), identity(baseline/filename)
        same = a["sha256"] == b["sha256"]
        contract_identities.append(dict(file=filename,candidate=a,baseline=b,byte_identical=same))
        if not same:
            failures.append("Hardware contract bytes changed: " + filename)
    xml = ET.parse(model_path).getroot()
    compiler = xml.find("compiler")
    meshdir = compiler.get("meshdir", ".") if compiler is not None else "."
    asset_identities = [dict(asset_name=e.get("name"),**identity(model_path.parent/meshdir/e.get("file"))) for e in xml.findall("asset/mesh") if e.get("file")]
    for field in ("joint_order", "joints", "passive_linkage_joints", "bodies"):
        if contract.get(field) != source_contract.get(field):
            failures.append("Physical contract changed: " + field)
    robot = [g for g in range(m.ngeom) if m.geom_bodyid[g] and (m.geom_contype[g] or m.geom_conaffinity[g])]
    if len(robot) != 14:
        failures.append(f"Expected14 active collision leaves, loaded{len(robot)}")
    leaves = []
    for g in robot:
        row = dict(name=m.geom(g).name, owner=helper.owner(m, g), type=int(m.geom_type[g]))
        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
            mid = int(m.geom_dataid[g])
            lo, count = int(m.mesh_vertadr[mid]), int(m.mesh_vertnum[mid])
            vv = m.mesh_vert[lo:lo+count].astype(float)
            row.update(raw_vertices=count, true_convex_support_vertices=len(ConvexHull(vv).vertices))
            if row["true_convex_support_vertices"] > 64:
                failures.append(row["name"] + ": exceeds64 support vertices")
        else:
            row["primitive_analytic_support"] = True
        leaves.append(row)
    expected_roles = {"torso": 2, "neck_pitch": 1, "neck_mid_pitch": 1, "head_roll": 1, "beak_hinge": 1}
    expected_roles.update({s+"_"+r: 1 for s in ("left", "right") for r in ("hip_roll", "hip_pitch", "knee_pitch", "ankle_roll")})
    actual_roles = {r: sum(x["owner"] == r for x in leaves) for r in {x["owner"] for x in leaves}}
    if actual_roles != expected_roles:
        failures.append("Actual fourteen role allocation differs from the agreed role map")
    critical = [("torso", "neck_mid_pitch"), ("torso", "head_roll")]
    critical += [("torso", s+"_"+segment) for s in ("left", "right") for segment in ("hip_pitch", "knee_pitch")]
    critical += [("left_"+segment, "right_"+segment) for segment in ("hip_pitch", "knee_pitch", "ankle_roll")]
    policy = []
    for a, b in critical:
        ga, gb = [g for g in robot if helper.owner(m, g) == a], [g for g in robot if helper.owner(m, g) == b]
        actual = [helper.pair_policy(m, x, y) for x in ga for y in gb]
        enabled = sum(x[0] for x in actual)
        policy.append(dict(owners=[a,b], pairs=len(actual), enabled=enabled, details=actual))
        if not actual or enabled != len(actual):
            failures.append("Nonadjacent role hidden/missing: " + a + "/" + b)
    # Exhaustive role participation, not merely same-level cross-leg probes.
    adjacent = [("torso","neck_pitch"),("neck_pitch","neck_mid_pitch"),("neck_mid_pitch","head_roll"),("head_roll","beak_hinge")]
    adjacent += [("torso",s+"_hip_roll") for s in ("left","right")]
    adjacent += [(s+"_"+a,s+"_"+b) for s in ("left","right") for a,b in (("hip_roll","hip_pitch"),("hip_pitch","knee_pitch"),("knee_pitch","ankle_roll"))]
    adjacent = {tuple(sorted(x)) for x in adjacent}
    role_pairs = []
    for i, ga in enumerate(robot):
        for gb in robot[i+1:]:
            owners = tuple(sorted((helper.owner(m,ga),helper.owner(m,gb))))
            if owners[0] == owners[1]:
                continue
            enabled, reason = helper.pair_policy(m,ga,gb)
            row = dict(geoms=[m.geom(ga).name,m.geom(gb).name],owners=owners,mechanical_adjacent=owners in adjacent,enabled=enabled,reason=reason)
            role_pairs.append(row)
            if not enabled and owners not in adjacent:
                failures.append("Unjustified nonadjacent filter: " + "/".join(owners))
    ground = [g for g in range(m.ngeom) if not m.geom_bodyid[g] and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
    if len(ground) != 1 or any(not helper.pair_policy(m, ground[0], g)[0] for g in robot):
        failures.append("An exterior role cannot contact the ground")
    cases = dict(zero={}, neck_015=dict(neck_pitch=.15,neck_mid_pitch=-.15),
                 neck_030=dict(neck_pitch=.3,neck_mid_pitch=-.3), neck_050=dict(neck_pitch=.5,neck_mid_pitch=-.5),
                 crossed_feet=dict(left_hip_roll=-.5,right_hip_roll=.5),
                 right_HP_070=dict(right_hip_pitch=.7), left_HP_070=dict(left_hip_pitch=.7))
    fixtures = []
    for label, q in cases.items():
        helper.pose(m,d,contract,q)
        cc = helper.contacts(m,d)
        penetrating = [x for x in cc if x["distance_m"] < -.00025]
        if label in ("zero", "neck_015", "neck_030", "neck_050"):
            false = [x for x in penetrating if tuple(sorted((x["owner_a"],x["owner_b"]))) in {tuple(sorted(p)) for p in critical}]
            passed = not false
        elif label == "crossed_feet":
            false = []
            passed = any(set((x["owner_a"],x["owner_b"])) == {"left_ankle_roll","right_ankle_roll"} for x in cc)
        else:
            false = []
            side = label.split("_")[0]
            passed = any(set((x["owner_a"],x["owner_b"])) == {"torso",side+"_knee_pitch"} and x["distance_m"] < 0 for x in cc)
        fixtures.append(dict(name=label,q=q,passed=passed,unexpected_nonadjacent_contacts=false,contacts=cc))
        if not passed:
            failures.append("Contact fixture: " + label)
    # Same real object and source reference plane used for02; no task policy.
    if model_path.name == "robot.xml":
        mouth = helper.mouth_object_fixtures(package, contract)
        for row in mouth:
            if not row["passed"]:
                failures.append("Mouth object fixture: " + row["name"])
    else:
        mouth = []
        failures.append("Mouth fixture requires candidate package robot.xml")
    # Compare real sole planes and footprint support directions, then exercise
    # ordinary plane contact. This is a kinematic fixture, no state projection.
    helper.pose(m,d,contract,{},root_z=0.)
    helper.pose(source,sd,source_contract,{},root_z=0.)
    support_probes = []
    all_candidate = np.vstack([vertices(m,d,g) for g in robot])
    all_source = np.vstack([vertices(source,sd,g) for g in range(source.ngeom) if source.geom_bodyid[g] and source.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH])
    candidate_torso = np.vstack([vertices(m,d,g) for g in robot if helper.owner(m,g)=="torso"])
    source_torso = np.vstack([vertices(source,sd,g) for g in range(source.ngeom) if helper.owner(source,g)=="torso" and source.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH])
    dirs = [np.array(v,dtype=float) for v in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))]
    dirs += [np.array([h*np.cos(a),h*np.sin(a),z],dtype=float) for a in np.linspace(0,2*np.pi,8,endpoint=False) for h,z in ((1,-.5),(1,-1),(1,-2),(1,.5),(1,1),(1,2))]
    for label, sv, cv in (("whole_robot",all_source,all_candidate),("torso_only",source_torso,candidate_torso)):
        for direction in dirs:
            direction /= np.linalg.norm(direction)
            si, ci = int(np.argmax(sv @ direction)), int(np.argmax(cv @ direction))
            sh, ch = float(sv[si] @ direction), float(cv[ci] @ direction)
            support_probes.append(dict(scope=label,outward_support_direction_zero=direction.tolist(),
                                       source_support_m=sh,candidate_support_m=ch,extent_delta_m=ch-sh,
                                       source_witness_world_zero_m=sv[si].tolist(),candidate_witness_world_zero_m=cv[ci].tolist()))
    feet = []
    directions = np.c_[np.cos(np.linspace(0,2*np.pi,1440,endpoint=False)), np.sin(np.linspace(0,2*np.pi,1440,endpoint=False))]
    for side in ("left","right"):
        vv = np.vstack([vertices(m,d,g) for g in robot if helper.owner(m,g) == side+"_ankle_roll"])
        actual_g = [g for g in range(source.ngeom) if helper.owner(source,g) == side+"_ankle_roll" and "actual_sole" in (source.geom(g).name or "")]
        actual = np.vstack([vertices(source,sd,g) for g in actual_g])
        z, actual_z = float(vv[:,2].min()), float(actual[:,2].min())
        bottom = vv[np.abs(vv[:,2]-z) < 1e-6]
        true_bottom = actual[np.abs(actual[:,2]-actual_z) < 1e-6]
        hs = np.max(true_bottom[:,:2] @ directions.T,axis=0)
        cs = np.max(bottom[:,:2] @ directions.T,axis=0)
        feet.append(dict(side=side,ground_plane_m=z,true_ground_plane_m=actual_z,plane_delta_m=z-actual_z,
                         bottom_vertices=len(bottom),max_support_loss_m=float(np.max(hs-cs)),max_support_excess_m=float(np.max(cs-hs)),
                         max_abs_support_error_m=float(np.max(np.abs(cs-hs))),bottom_world_zero_m=bottom.tolist()))
        if abs(z-actual_z)>1e-5:
            failures.append(side + ": true sole plane shifted by>0.01mm")
    helper.pose(m,d,contract,{},root_z=-.001-min(x["ground_plane_m"] for x in feet))
    cc = helper.contacts(m,d)
    ground_contacts = [x for x in cc if "world" in (x["owner_a"],x["owner_b"])]
    for side in ("left","right"):
        if not any(side+"_ankle_roll" in (x["owner_a"],x["owner_b"]) for x in ground_contacts):
            failures.append(side+": ground contact missing")
    excludes = [[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(x)>>16),mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(x)&65535)] for x in m.exclude_signature]
    return dict(schema="goose_independent_low_leaf_finite_contact_review_v1",candidate=identity(model_path),baseline=identity(baseline/"robot.xml"),
                status="PASS_FINITE_CONTACT_FIXTURES" if not failures else "REJECT_FINITE_CONTACT_FIXTURES",failures=failures,
                candidate_mesh_assets=asset_identities,hardware_contract_identities=contract_identities,
                candidate_collision_manifest=identity(package/"collision_manifest.json"),
                compiled_hardware_checks=checks,actual_active_collision_leaves=len(robot),leaves=leaves,
                total_mesh_convex_support_vertices=sum(x.get("true_convex_support_vertices",0) for x in leaves),
                explicit_body_exclusions=excludes,critical_nonadjacent_pair_policy=policy,finite_contact_fixtures=fixtures,
                exact_role_counts=actual_roles,exhaustive_role_pair_participation=role_pairs,
                actual_mouth_object_fixtures=mouth,actual_sole_support_comparison=feet,ground_contact_fixture=ground_contacts,
                cheap_front_back_side_lying_support_extent_probes=support_probes,
                limitations=["Finite contact fixtures do not establish learned task success or whole-ROM clearance.",
                             "Footprint errors are1440 directional samples, not a continuous Hausdorff certificate.",
                             "Mechanical adjacent-role proxy exceptions are explicit; CAD interference remains a separate test."])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package",type=Path,required=True)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--model",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    out=run(a.package.resolve(),a.baseline.resolve(),a.model.resolve() if a.model else a.package.resolve()/"robot.xml")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"failures":out["failures"],"leaves":out["actual_active_collision_leaves"],"supports":out["total_mesh_convex_support_vertices"],"output":str(a.output)}))
    raise SystemExit(bool(out["failures"]))


if __name__ == "__main__":
    main()
