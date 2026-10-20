"""Finite actual12 native mechanical audit; no integration or geometry edits.

Use the MuJoCo environment for --stage poses and the pinned CAD environment
for --stage native. All outputs are new audit artifacts, never runtime assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")


def identity(path):
    path = Path(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def poses(args):
    import numpy as np
    import mujoco as mj

    def forbidden(*a, **k):
        raise RuntimeError("No mj_step permitted in finite native audit")

    mj.mj_step = mj.mj_step1 = mj.mj_step2 = forbidden
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/"pose_contract.json").exists()
    r = args.workspace / "robots/goose_v0_2"
    index_path = r / "cad/source/drag_hardware_integration_009_08/assembly_index.json"
    binding_path = r / "evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json"
    selected_path = args.attempt / "selected_actual_native_states.json"
    selected = json.loads(selected_path.read_text())
    index = json.loads(index_path.read_text())
    binding = json.loads(binding_path.read_text())
    model_path = args.attempt / selected["source_scene"]
    assert identity(model_path)["sha256"] == selected["source_scene_sha256"]
    m = mj.MjModel.from_binary_path(str(model_path))
    d = mj.MjData(m)
    all_origins = binding["physical_body_origin_world_zero_m"]
    robot_ids = {m.body(n).id for n in all_origins}
    d.qpos[:] = m.qpos0
    for j in range(m.njnt):
        if int(m.jnt_bodyid[j]) not in robot_ids:
            continue
        q = int(m.jnt_qposadr[j])
        if m.jnt_type[j] == mj.mjtJoint.mjJNT_FREE:
            d.qpos[q:q+7] = [0, 0, 0, 1, 0, 0, 0]
        elif m.jnt_type[j] == mj.mjtJoint.mjJNT_HINGE:
            d.qpos[q] = 0
        else:
            raise ValueError((j, "Unexpected native-zero joint type"))
    mj.mj_fwdPosition(m, d)
    names = ["front_main_shell", "rear_service_cap"]
    roles = {"front_main_shell": "front", "rear_service_cap": "rear"}
    for side in ["left", "right"]:
        for suffix, role in [
            ("visible_structural_shin_primary_shell", "shin"),
            ("visible_structural_shin_inner_C45_cover", "C45"),
            ("ankle_pitch_7075_load_body_009_c02", "Al"),
            ("ankle_pitch_qt_steel_collector_009_c02", "steel"),
            ("visible_AP_outboard_coaxial_service_shell_clearance_009_c09", "AP"),
            ("integrated_AR_shoe_crown_continuous_009_c03", "AR"),
        ]:
            name = side + "_" + suffix
            names.append(name)
            roles[name] = side + "_" + role
    parts = []
    zero = {}
    for row in index["parts"]:
        if row["name"] not in names:
            continue
        source = row.get("native") or row["native_source"]
        source_path = Path(source["path"])
        if not source_path.is_absolute():
            source_path = args.workspace / source_path
        assert identity(source_path)["sha256"] == source["sha256"]
        assert np.max(abs(np.array(row["source_to_target_world_zero_4x4"]) - np.eye(4))) == 0
        owner = row["body"]
        bid = m.body(owner).id
        t = np.eye(4)
        t[:3, :3] = d.xmat[bid].reshape(3, 3)
        t[:3, 3] = 1000*d.xpos[bid]
        error = max(abs(t[:3, 3]-1000*np.array(all_origins[owner])))
        assert error < 1e-8 and max(abs(t[:3, :3]-np.eye(3)).flat) < 1e-12
        zero[owner] = t
        parts.append(dict(name=row["name"], role=roles[row["name"]], owner=owner,
                          native_index=row["native_part_index"], source=identity(source_path),
                          zero_origin_error_mm=float(error)))
    assert len(parts) == 14, len(parts)
    rows = list(selected["states"])
    # The distinct terminal POST is optional fifth state; never relabel a PRE.
    post_path = args.attempt / "true_terminal_poststate.npz"
    post_json = args.attempt / "true_terminal_poststate.json"
    if post_path.is_file() and len(rows) < 5:
        z = np.load(post_path)
        pj = json.loads(post_json.read_text())
        rows.append(dict(label="terminal_POST", state_semantics="saved true terminal POST",
                         time_s=pj["time_s"], qpos=z["qpos"].tolist(), qvel=z["qvel"].tolist(),
                         pre_bodies={n:dict(xpos=z["xpos"][m.body(n).id].tolist(),
                                           xmat=z["xmat"][m.body(n).id].tolist()) for n in zero}))
    result = dict(physics_steps=0, LP_calls=0, geometry_edits=0,
                  inputs={"script":identity(Path(__file__)), "selected":identity(selected_path),
                          "index":identity(index_path), "binding":identity(binding_path),
                          "model":identity(model_path), "terminal_post":identity(post_path)},
                  source_zero_T_mm={n:t.tolist() for n,t in zero.items()}, parts=parts, states=[])
    for row in rows:
        q = np.array(row["qpos"])
        d.qpos[:] = q
        d.qvel[:] = row["qvel"]
        d.time = row["time_s"]
        mj.mj_fwdPosition(m, d)
        transforms = {}
        comparisons = []
        for owner, original in zero.items():
            b = m.body(owner).id
            t = np.eye(4)
            t[:3,:3] = d.xmat[b].reshape(3,3)
            t[:3,3] = 1000*d.xpos[b]
            transforms[owner] = (t @ np.linalg.inv(original)).tolist()
        # PRE logs save torso/head/mouth/cart, not all leg bodies. Reconstruct
        # the leg bodies by exact FK from the complete actual52 qpos and exact
        # saved model; crosscheck every body matrix that the logger did save.
        for owner, saved in row["pre_bodies"].items():
            b=m.body(owner).id
            pe=max(abs(d.xpos[b]-saved["xpos"]))
            re=max(abs(d.xmat[b]-saved["xmat"]))
            assert pe<1e-11 and re<1e-11,(owner,pe,re)
            comparisons.append(dict(owner=owner,saved_position_error_m=float(pe),
                                    saved_rotation_error=float(re)))
        angles = {}
        for side in ["left","right"]:
            for axis in ["ankle_pitch", "ankle_roll", "knee_pitch"]:
                name = side + "_" + axis
                angles[name] = float(d.qpos[m.jnt_qposadr[m.joint(name).id]])
        result["states"].append(dict(label=row["label"], time_s=row["time_s"],
            semantics=row["state_semantics"], qpos_full=row["qpos"], qvel_full=row["qvel"],
            named_joint_angles_rad=angles, source_saved_body_crosschecks=comparisons,
            CAD_zero_to_world_mm=transforms))
    save(args.output/"pose_contract.json",result)
    print(json.dumps({"pose_contract":str(args.output/"pose_contract.json"), "states":len(rows),
                      "parts":len(parts),"physics_steps":0}),flush=True)


def native(args):
    import time
    import numpy as np
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    contract = json.loads((args.output/"pose_contract.json").read_text())
    shapes = {}
    source_by_role = {}
    for part in contract["parts"]:
        source = part["source"]
        assert identity(source["path"])["sha256"] == source["sha256"]
        s = TopoDS_Shape()
        assert BRepTools.Read_s(s,source["path"],BRep_Builder())
        shapes[part["role"]] = s
        source_by_role[part["role"]] = part
    pairs = []
    for side in ["left","right"]:
        pairs += [(shell,side+"_"+leg) for shell in ["front","rear"] for leg in ["C45","shin"]]
    # AR/metal and optional AP/shin exact queries use the separate priority
    # process. Do not duplicate them while native shell distances are running.
    cache_path=args.output/"native_pair_results.partial.json"
    previous=json.loads(cache_path.read_text()) if cache_path.exists() else {"rows":[]}
    cache={(r['label'],tuple(r['role_pair'])):r for r in previous['rows']}
    out = dict(inputs=contract["inputs"],pose_contract=identity(args.output/"pose_contract.json"),
               parts=contract["parts"],scope="Five finite actual states; not continuous-motion/full-ROM/manufacturing qualification.",
               numerical_policy="Common exact native boolean, no fuzzy tolerance/healing; report positive volumes separately from zero distance.",
               physics_steps=0,LP_calls=0,geometry_edits=0,
               native_execution_script=identity(Path(__file__)),rows=[])
    for state in contract["states"]:
        world = {}
        for role,shape in shapes.items():
            part = source_by_role[role]
            a = np.array(state["CAD_zero_to_world_mm"][part["owner"]])
            tr = gp_Trsf();tr.SetValues(*a[:3,:].ravel().tolist())
            world[role] = BRepBuilderAPI_Transform(shape,tr,True).Shape()
        for rolea,roleb in pairs:
            cached=cache.get((state['label'],(rolea,roleb)))
            if cached is not None:
                out['rows'].append(cached)
                save(args.output/'native_shell_pair_results.partial.json',out)
                print('CACHED '+json.dumps(cached),flush=True)
                continue
            begin=time.monotonic();a,b=world[rolea],world[roleb]
            optional_shin=roleb.endswith('_shin')
            bounds=[]
            for shape in [a,b]:
                box=Bnd_Box();BRepBndLib.Add_s(shape,box);bounds.append(np.array(box.Get()))
            low=np.maximum(bounds[0][:3],bounds[1][:3]);high=np.minimum(bounds[0][3:],bounds[1][3:])
            bbox_lower=float(np.linalg.norm(np.maximum(low-high,0)))
            value=None;pa=None;pb=None
            if not optional_shin:
                dist=BRepExtrema_DistShapeShape(a,b);dist.Perform();assert dist.IsDone()
                value=float(dist.Value());pa=list(dist.PointOnShape1(1).Coord());pb=list(dist.PointOnShape2(1).Coord())
            common_volume=0.;common_bbox=None;common_source=None
            if (optional_shin and bbox_lower<=0) or (value is not None and value<1e-6):
                op=BRepAlgoAPI_Common(a,b);op.SetRunParallel(False);op.Build();assert op.IsDone()
                props=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),props)
                common_volume=float(props.Mass())
                if common_volume>1e-9:
                    bb=Bnd_Box();BRepBndLib.Add_s(op.Shape(),bb)
                    if not bb.IsVoid():common_bbox=list(bb.Get())
                    fn=args.output/(state["label"]+"_"+rolea+"_"+roleb+"_Common.brep")
                    BRepTools.Write_s(op.Shape(),str(fn));common_source=identity(fn)
            row=dict(label=state["label"],time_s=state["time_s"],state_semantics=state["semantics"],
                     role_pair=[rolea,roleb],native_distance_mm=value,Common_mm3=common_volume,
                     native_AABB_distance_lower_bound_mm=bbox_lower,
                     distance_method='native_AABB_lower_bound_only' if optional_shin else 'exact_native_Extrema',
                     common_bbox_world_mm=common_bbox,Common_shape=common_source,
                     nearest_points_world_mm=[pa,pb],elapsed_s=time.monotonic()-begin)
            out["rows"].append(row);save(args.output/"native_shell_pair_results.partial.json",out)
            print(json.dumps(row),flush=True)
    save(args.output/"native_shell_pair_results.json",out)
    print("FINAL "+str(args.output/"native_shell_pair_results.json"),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",choices=["poses","native"],required=True)
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--attempt",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    os.sched_setaffinity(0,{6})
    (poses if a.stage=="poses" else native)(a)
