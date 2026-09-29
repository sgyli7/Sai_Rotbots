"""Screen a prescribed Goose pose for static equilibrium on its two feet.

This linear program balances full-body gravity with forces at eight sole
corners and joint torques. It is a necessary static check, not a controller,
continuous motor rating, gait, or grasp validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
from scipy.optimize import linprog

from check_goose_exterior_reach import pivots_from_manifest, tip_datum_from_mesh
from simulate_goose_r2_stance_trial import pose_data


def corner_jacobians(model, data):
    """One X/Y/Z force at each sole corner, left four then right four."""
    matrix = np.zeros((model.nv, 24))
    points = []
    for side in ('left', 'right'):
        geom = model.geom(f'{side}_sole_contact')
        rotation = data.geom_xmat[geom.id].reshape(3, 3)
        for x in (-geom.size[0], geom.size[0]):
            for y in (-geom.size[1], geom.size[1]):
                point = data.geom_xpos[geom.id] + rotation @ np.array([x, y, -geom.size[2]])
                jacp = np.zeros((3, model.nv))
                jacr = np.zeros((3, model.nv))
                mujoco.mj_jac(model, data, jacp, jacr, point,
                              model.geom_bodyid[geom.id])
                index = len(points)
                matrix[:, 3*index:3*index+3] = jacp.T
                points.append((side, point))
    return matrix, points


def torque_caps(model):
    caps = np.zeros(model.nv)
    names = {}
    for index in range(model.nu):
        joint_id = model.actuator_trnid[index, 0]
        dof_index = model.jnt_dofadr[joint_id]
        caps[dof_index] = model.actuator_ctrlrange[index, 1]
        names[dof_index] = model.joint(joint_id).name
    if np.any(caps[6:] <= 0):
        raise ValueError('Static screen requires a torque actuator on every non-root DoF')
    return caps, names


def balance_case(model, data, mu, mirror_force_slack_n, tip_force_n):
    jacobian, corners = corner_jacobians(model, data)
    heights = [float(point[2]) for _, point in corners]
    if max(heights) - min(heights) > .001 or not -.001 <= min(heights) <= .003:
        raise ValueError('The candidate feet are not flat near the floor')
    bias = data.qfrc_bias.copy()
    tip_site = model.site('beak_tip_visual_datum')
    tip_jacp = np.zeros((3, model.nv))
    tip_jacr = np.zeros((3, model.nv))
    mujoco.mj_jac(model, data, tip_jacp, tip_jacr,
                  data.site_xpos[tip_site.id], model.site_bodyid[tip_site.id])
    # An object pulls on the beak; transfer that generalized force to the
    # right-hand side of static force balance.
    bias -= tip_jacp.T @ tip_force_n
    caps, names = torque_caps(model)
    # First six DoF are the free root. The remaining joint torques obey
    # |bias - J^T f| <= scale * trial actuator cap.
    equalities = []
    targets = []
    for dof in range(6):
        row = np.zeros(25)
        row[:24] = jacobian[dof]
        equalities.append(row)
        targets.append(bias[dof])
    inequalities = []
    limits = []
    # Keep the solution close to mirror symmetry. Exact symmetry can be
    # infeasible because the reserved electronics have a small lateral offset.
    for local_index in range(4):
        mirror_index = 4 + (local_index ^ 1)
        for axis, sign in ((0, 1), (1, -1), (2, 1)):
            row = np.zeros(25)
            row[3*local_index+axis] = 1
            row[3*mirror_index+axis] = -sign
            inequalities.append(row)
            limits.append(mirror_force_slack_n)
            inequalities.append(-row)
            limits.append(mirror_force_slack_n)
    for dof in range(6, model.nv):
        for sign in (-1, 1):
            row = np.zeros(25)
            row[:24] = sign * jacobian[dof]
            row[24] = -caps[dof]
            inequalities.append(row)
            limits.append(sign * bias[dof])
    for corner in range(8):
        for axis in (0, 1):
            for sign in (-1, 1):
                row = np.zeros(25)
                row[3*corner+axis] = sign
                row[3*corner+2] = -mu
                inequalities.append(row)
                limits.append(0.0)
    bounds = [(None, None) if index % 3 != 2 else (0, None)
              for index in range(24)] + [(0, None)]
    objective = np.zeros(25)
    objective[24] = 1
    result = linprog(objective, A_ub=np.array(inequalities), b_ub=np.array(limits),
                     A_eq=np.array(equalities), b_eq=np.array(targets),
                     bounds=bounds, method='highs')
    if not result.success:
        return {'solver_status': result.message, 'static_equilibrium_found': False}
    force = result.x[:24]
    torque = bias - jacobian @ force
    demands = [{'joint': names[index],
                'torque_Nm': round(float(torque[index]), 4),
                'trial_limit_Nm': round(float(caps[index]), 4),
                'fraction_of_trial_limit': round(float(abs(torque[index])/caps[index]), 4)}
               for index in range(6, model.nv)]
    demands.sort(key=lambda item: item['fraction_of_trial_limit'], reverse=True)
    torque_by_joint = {names[index]: round(float(torque[index]), 8)
                       for index in range(6, model.nv)}
    normals = [float(force[3*index+2]) for index in range(8)]
    return {
        'solver_status': result.message,
        'static_equilibrium_found': True,
        'minimum_normalized_torque_scale': round(float(result.x[24]), 4),
        'within_trial_torque_caps': bool(result.x[24] <= 1 + 1e-6),
        'root_force_balance_residual_N': round(float(np.linalg.norm(
            jacobian[:3] @ force - bias[:3])), 8),
        'normal_force_by_foot_N': {'left': round(sum(normals[:4]), 3),
                                   'right': round(sum(normals[4:]), 3)},
        'normal_force_total_N': round(sum(normals), 3),
        'corner_normal_forces_N': [round(value, 3) for value in normals],
        'highest_joint_demands': demands[:8],
        'foot_only_equilibrium_torque_Nm_by_joint': torque_by_joint,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--trial-xml', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--target-x-mm', type=float, nargs='+', required=True)
    parser.add_argument('--target-tip-z-mm', type=float, default=40)
    parser.add_argument('--sit-drop-mm', type=float, default=90)
    parser.add_argument('--sit-torso-deg', type=float, default=20)
    parser.add_argument('--sit-head-global-deg', type=float, default=60)
    parser.add_argument('--friction-mu', type=float, default=.8)
    parser.add_argument('--mirror-force-slack-N', type=float, default=2.0)
    parser.add_argument('--tip-downward-load-N', type=float, default=0.0)
    parser.add_argument('--tip-horizontal-load-N', type=float, default=0.0)
    args = parser.parse_args()
    if args.tip_downward_load_N < 0:
        parser.error('--tip-downward-load-N must be nonnegative')
    model = mujoco.MjModel.from_xml_path(str(args.trial_xml))
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT
    layout = pivots_from_manifest(args.appearance_dir)
    tip = tip_datum_from_mesh(args.appearance_dir)
    cases = {}
    for target_x in args.target_x_mm:
        data = pose_data(model, 'seated_ground_reach', tip, layout,
                         sit_drop_mm=args.sit_drop_mm,
                         sit_torso_deg=args.sit_torso_deg,
                         sit_head_global_deg=args.sit_head_global_deg,
                         target_tip_z_mm=args.target_tip_z_mm,
                         target_tip_x_mm=target_x)
        cases[str(target_x)] = balance_case(
            model, data, args.friction_mu, args.mirror_force_slack_N,
            np.array([args.tip_horizontal_load_N, 0.0,
                      -args.tip_downward_load_N]))
    evidence = {
        'status': 'necessary_foot_only_static_balance_screen_not_dynamic_or_thermal_validation',
        'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'trial_xml_sha256': hashlib.sha256(args.trial_xml.read_bytes()).hexdigest(),
        'appearance_manifest_sha256': hashlib.sha256((args.appearance_dir/'manifest.json').read_bytes()).hexdigest(),
        'model_mass_kg': round(float(model.body_mass.sum()), 4),
        'contact_hypothesis': 'Eight normal/tangential forces at two flat rectangular sole corners, near mirror-symmetric; no beak/body support.',
        'friction_coefficient': args.friction_mu,
        'mirror_force_slack_N_per_corner_axis': args.mirror_force_slack_N,
        'beak_tip_external_force_N': [args.tip_horizontal_load_N, 0.0,
                                       -args.tip_downward_load_N],
        'pose': {'sit_drop_mm': args.sit_drop_mm,
                 'torso_pitch_down_deg': args.sit_torso_deg,
                 'head_global_pitch_down_deg': args.sit_head_global_deg,
                 'target_tip_z_mm': args.target_tip_z_mm},
        'cases_by_target_tip_x_mm': cases,
        'limitations': [
            'Each case is a prescribed zero-velocity pose, not a sit-down, stand-up, walking or grasp trajectory.',
            'Actuator caps are initial short-duration trial limits, not continuous thermal torque ratings.',
            'The program does not verify whole-body self-collision, contact pressure distribution, slip margins, beak/object forces or controller tracking.',
            'A scale below one is only necessary static feasibility; it is not physical delivery approval.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({target: {'scale': case.get('minimum_normalized_torque_scale'),
                               'feasible': case['static_equilibrium_found']}
                      for target, case in cases.items()}))


if __name__ == '__main__':
    main()
