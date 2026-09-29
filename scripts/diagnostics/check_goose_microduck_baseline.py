"""Measure MicroDuck's published standing model against Goose's visual screen.

This is a morphology comparison, not a transfer or stability test. Requires
MuJoCo and the original MicroDuck scene plus its referenced meshes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id(model: mujoco.MjModel, obj: mujoco.mjtObj, name: str) -> int:
    result = mujoco.mj_name2id(model, obj, name)
    if result < 0:
        raise ValueError(f"missing {obj}: {name}")
    return result


def _foot_extent(model: mujoco.MjModel, data: mujoco.MjData, side: str) -> dict:
    geom_id = _id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{side}_foot_collision")
    mesh_id = int(model.geom_dataid[geom_id])
    start = int(model.mesh_vertadr[mesh_id])
    count = int(model.mesh_vertnum[mesh_id])
    vertices = model.mesh_vert[start : start + count]
    rotation = data.geom_xmat[geom_id].reshape(3, 3)
    world = vertices @ rotation.T + data.geom_xpos[geom_id]
    low = world[:, 2].min()
    contact = world[world[:, 2] <= low + 0.002]
    ankle_id = _id(model, mujoco.mjtObj.mjOBJ_JOINT, f"{side}_ankle")
    ankle_x = float(data.xanchor[ankle_id, 0])
    return {
        "ankle_x_m": round(ankle_x, 6),
        "near_sole_min_x_m": round(float(contact[:, 0].min()), 6),
        "near_sole_max_x_m": round(float(contact[:, 0].max()), 6),
        "ankle_to_rear_m": round(ankle_x - float(contact[:, 0].min()), 6),
        "ankle_to_front_m": round(float(contact[:, 0].max()) - ankle_x, 6),
        "near_sole_min_z_m": round(float(low), 6),
        "vertex_band_m": 0.002,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--microduck-scene", type=Path, required=True)
    parser.add_argument("--goose-mass-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model = mujoco.MjModel.from_xml_path(str(args.microduck_scene))
    data = mujoco.MjData(model)
    stand_id = _id(model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
    data.qpos[:] = model.key_qpos[stand_id]
    mujoco.mj_forward(model, data)

    mass = float(model.body_mass.sum())
    com = (model.body_mass[:, None] * data.xipos).sum(axis=0) / mass
    mouth_id = _id(model, mujoco.mjtObj.mjOBJ_SITE, "mouth_tip")
    goose = json.loads(args.goose_mass_evidence.read_text())
    goose_standing = goose["cases_by_assumed_uniform_wall_mm"]["1.6"]["standing"]
    goose_mass = goose_standing["mass_kg"]
    goose_com_z = goose_standing["projected_com_mm"][2] / 1000.0
    result = {
        "status": "morphology_comparison_not_transfer_validation",
        "microduck_scene_sha256": _sha256(args.microduck_scene),
        "goose_evidence_sha256": _sha256(args.goose_mass_evidence),
        "microduck_stand": {
            "model_mass_kg": round(mass, 6),
            "com_m": [round(float(x), 6) for x in com],
            "mouth_tip_m": [round(float(x), 6) for x in data.site_xpos[mouth_id]],
            "actuator_count_in_mjcf": model.nu,
            "left_foot": _foot_extent(model, data, "left"),
            "right_foot": _foot_extent(model, data, "right"),
        },
        "goose_visual_study": {
            "assumed_uniform_wall_mm": 1.6,
            "conditional_mass_kg": goose_mass,
            "conditional_com_height_m": goose_com_z,
            "mass_ratio_to_microduck": round(goose_mass / mass, 2),
            "com_height_ratio_to_microduck": round(goose_com_z / float(com[2]), 2),
        },
        "limitations": [
            "MicroDuck scene STAND is a keyframe, not a settled physical equilibrium.",
            "Foot extents use the lowest 2 mm of collision-mesh vertices, not measured contact pressure.",
            "Goose mass depends on an assumed uniform 1.6 mm PETG wall and incomplete packaging.",
            "Ratios do not prove or disprove walking, lifting, gripping, or dragging.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
