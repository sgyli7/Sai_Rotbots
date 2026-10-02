"""Repose both legs in the Goose visual low-pickup mass/support screen.

The earlier screen rotated the upper body but kept both legs at their standing
mass locations. This checks whether that shortcut changed the whole-body COM
conclusion for the v95/v96 pointed-beak exterior. It remains a conditional
surface-mass estimate, not a force, stability, or gait certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from check_goose_exterior_mass_screen import (motor_and_component_items,
                                               placed, printed_parts, summary)
from check_goose_exterior_reach import pitch_matrix, pivots_from_manifest


CASES = {
    "v95_torso20": (
        "exterior_study_r2_swept_mechanism_v95b_closed",
        "exterior_study_r2_swept_mechanism_v95b_open",
        "r2_swept_head_v95_support_geometry.json",
        "r2_swept_head_v95_sit90_x300_z25_open.json",
    ),
    "v95_torso15": (
        "exterior_study_r2_swept_mechanism_v95b_closed",
        "exterior_study_r2_swept_mechanism_v95b_open",
        "r2_swept_head_v95_support_geometry.json",
        "r2_swept_head_v95_sit90_torso15_x300_z25_open.json",
    ),
    "v96_torso20": (
        "exterior_study_r2_centered_foot_v96_closed",
        "exterior_study_r2_centered_foot_v96_open",
        "r2_centered_foot_v96_support_geometry.json",
        "r2_centered_foot_v96_sit90_x300_z25_open.json",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def leg_attachment(name: str) -> str:
    if name.startswith(("leg_hip_", "hip_")):
        return "hip"
    if name.startswith(("leg_knee_", "thigh_", "knee_")):
        return "thigh"
    if name.startswith(("leg_ankle_", "shin_", "ankle_")):
        return "shin"
    if name.startswith("foot_"):
        return "foot"
    raise ValueError(f"Unknown visual leg-mass attachment: {name}")


def seated_items(items, pivots, pose):
    """Match the hierarchy in check_goose_exterior_reach.make_posed_xml."""
    upper = pose["pose_pitch_down_deg"]
    leg = pose["seated_leg_pitch_deg"]
    drop = float(pose["sit_drop_mm"])
    if leg is None or drop <= 0:
        raise ValueError("Expected a seated pose with planar leg angles")
    hip_world = pivots["hip"] - np.array([0.0, 0.0, drop])
    thigh_pitch = upper["torso"] + leg["hip"]
    shin_pitch = thigh_pitch + leg["knee"]
    foot_pitch = shin_pitch + leg["ankle"]
    knee_world = hip_world + pitch_matrix(thigh_pitch) @ (
        pivots["knee"] - pivots["hip"])
    ankle_world = knee_world + pitch_matrix(shin_pitch) @ (
        pivots["ankle"] - pivots["knee"])
    ankle_drift = float(np.linalg.norm(ankle_world - pivots["ankle"]))
    if ankle_drift > .01 or abs(foot_pitch) > .01:
        raise ValueError("The seated pose does not retain a fixed, flat visual foot")

    upper_placed = placed(items, pivots, upper["torso"],
                          upper["neck_lower_relative"],
                          upper["neck_upper_relative"],
                          upper["head_relative"])
    result = []
    counts = {"hip": 0, "thigh": 0, "shin": 0, "foot": 0}
    for (name, group, mass, original), (_, _, _, prior) in zip(items, upper_placed):
        if group != "legs":
            center = prior - np.array([0.0, 0.0, drop])
        else:
            attachment = leg_attachment(name)
            counts[attachment] += 1
            pivot, world, pitch = {
                "hip": (pivots["hip"], hip_world, upper["torso"]),
                "thigh": (pivots["hip"], hip_world, thigh_pitch),
                "shin": (pivots["knee"], knee_world, shin_pitch),
                "foot": (pivots["ankle"], ankle_world, foot_pitch),
            }[attachment]
            center = world + pitch_matrix(pitch) @ (original - pivot)
        result.append((name, group, mass, center))
    return result, counts, ankle_drift


def inspect(root: Path, label: str, paths: tuple[str, str, str, str]) -> dict:
    artifacts = root / "artifacts/Goose_V0.1"
    evidence = root / "robots/Goose_V0.1/evidence"
    closed, opened, support_name, pose_name = paths
    closed_dir, open_dir = artifacts / closed, artifacts / opened
    support_path, pose_path = evidence / support_name, evidence / pose_name
    support = json.loads(support_path.read_text())
    pose = json.loads(pose_path.read_text())
    if support["source_manifest_sha256"] != sha256(closed_dir / "manifest.json"):
        raise ValueError(f"{label}: support is not from its stated visual candidate")
    if pose["source_appearance_xml_sha256"] != sha256(open_dir / "appearance.xml"):
        raise ValueError(f"{label}: pose is not from its stated visual candidate")
    if not pose["sampled_stand_to_target_sweep"]["necessary_clearance_pass"]:
        raise ValueError(f"{label}: the sampled reach path already failed")
    pivots = pivots_from_manifest(closed_dir)
    manifest = json.loads((closed_dir / "manifest.json").read_text())
    items = (printed_parts(closed_dir, 1.6)
             + motor_and_component_items(root, pivots, manifest))
    upper = pose["pose_pitch_down_deg"]
    frozen = placed(items, pivots, upper["torso"],
                    upper["neck_lower_relative"],
                    upper["neck_upper_relative"], upper["head_relative"])
    reposed, counts, ankle_drift = seated_items(items, pivots, pose)
    before = summary(frozen, support, pivots["hip"])
    after = summary(reposed, support, pivots["hip"])
    target_x, _, target_z = pose["target_bill_tip_visual_datum_mm"]
    total = after["mass_kg"]
    load_x = (total * after["projected_com_mm"][0] + .05 * target_x) / (total + .05)
    load_z = (total * after["projected_com_mm"][2] + .05 * target_z) / (total + .05)
    x_min, x_max = support["double_support_necessary_x_com_interval_mm"]
    return {
        "input_sha256": {
            "closed_manifest": sha256(closed_dir / "manifest.json"),
            "open_appearance_xml": sha256(open_dir / "appearance.xml"),
            "support": sha256(support_path),
            "pose": sha256(pose_path),
        },
        "source_paths": {
            "closed": str(closed_dir.relative_to(root)),
            "opened": str(open_dir.relative_to(root)),
            "support": str(support_path.relative_to(root)),
            "pose": str(pose_path.relative_to(root)),
        },
        "conditional_wall_mm": 1.6,
        "visual_leg_attachment_counts": counts,
        "visual_ankle_fixpoint_drift_mm": round(ankle_drift, 6),
        "standing_leg_mass_shortcut": before,
        "reposed_leg_and_lowered_torso_mass": after,
        "reposed_plus_50g_at_visual_tip": {
            "projected_com_xz_mm": [round(load_x, 2), round(load_z, 2)],
            "double_support_nearest_sagittal_margin_mm": round(
                min(load_x - x_min, x_max - load_x), 2),
            "equal_share_hip_gravity_moment_Nm": round(
                after["equal_share_per_hip_Nm"]
                + .05 * 9.81 * (target_x - pivots["hip"][0]) / 2000, 3),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    cases = {label: inspect(root, label, paths)
             for label, paths in CASES.items()}
    v95 = cases["v95_torso20"]["reposed_leg_and_lowered_torso_mass"]
    v96 = cases["v96_torso20"]["reposed_leg_and_lowered_torso_mass"]
    result = {
        "status": "conditional_whole_body_seated_mass_screen_no_balance_release",
        "source_script_sha256": sha256(Path(__file__)),
        "cases": cases,
        "v96_minus_v95_same_pose": {
            "nearest_sagittal_margin_mm": round(
                v96["double_support_x_margin_to_nearest_end_mm"]
                - v95["double_support_x_margin_to_nearest_end_mm"], 2),
            "projected_com_x_mm": round(
                v96["projected_com_mm"][0] - v95["projected_com_mm"][0], 2),
        },
        "decision": "Reposing visual leg mass does not remove the low-pickup margin trade or hip-load warning; do not freeze v96 shoes or release pickup.",
        "limitations": [
            "Same visual STL skin-area × 1.6 mm PETG proxy and inherited component reserves; the shells overlap and lack real structural masses.",
            "Planar posterior-knee IK keeps ideal visual feet fixed and flat; it does not check leg/door/foot self-collision, joint stops or contact pressure.",
            "The support polygon is a visual sole bound, not a measured contact patch, dynamic balance, or single-foot capability.",
            "The 50 g point mass assumes a completed lift; there is no real object, grip force, drag, powered squat, or continuous motor thermal test.",
            "The 0.82 Nm per-hip warning threshold is a screening estimate, not verified continuous actuator capacity.",
            "The pointed exterior has not passed appearance review; the RC2 motor/BOM/model mismatch remains.",
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "v96_minus_v95_same_pose": result["v96_minus_v95_same_pose"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
