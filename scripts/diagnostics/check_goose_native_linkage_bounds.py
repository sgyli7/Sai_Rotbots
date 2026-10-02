"""Bound the moving native linkage's effect on the closed-pose static ledger.

Compare nominal mass configurations without running a controller or PPO. This
does not certify the motor's stationary thermal capacity or the jaw structure.
"""
from pathlib import Path
import hashlib
import json

import mujoco
import numpy as np

from sai_agent.goose.native_linkage import set_passive_linkage

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'


def main():
    paths = [R/'configs/mechanical_reference_contract.json',
             R/'models/mechanical_reference/robot.xml',
             R/'evidence/body_bay_mechanical_parameters.json']
    contract, ledger = [json.loads(p.read_text()) for p in [paths[0], paths[2]]]
    model = mujoco.MjModel.from_xml_path(str(paths[1]))
    data = mujoco.MjData(model)
    names = contract['joint_order']
    qadr = [model.joint(n).qposadr[0] for n in names]
    vadr = [model.joint(n).dofadr[0] for n in names]
    passive = contract['passive_linkage_joints']
    samples = []
    poses = [r for r in ledger['results'] if r['mass_variant'] == 0 and r['drag_x_n'] == 0]
    for pose in poses:
        for angle in np.linspace(0., .55, 23):
            mujoco.mj_resetData(model, data)
            data.qpos[:3] = pose['root_position_m']
            data.qpos[3:7] = pose['root_quaternion_wxyz']
            data.qpos[qadr] = [pose['joint_q_rad'].get(n, 0.) for n in names]
            data.qpos[qadr[names.index('beak_hinge')]] = angle
            set_passive_linkage(model, data, contract)
            mujoco.mj_forward(model, data)
            moving_com = data.subtree_com[model.body('torso').id].copy()
            moving_bias = data.qfrc_bias[vadr].copy()
            # Virtual work: a unit jaw rotation rotates the input by +1 and
            # the coupler's relative coordinate by -1. The drive is 1:1.
            jaw_gravity = moving_bias[names.index('beak_hinge')]
            for joint in passive:
                jaw_gravity += joint['mimic_multiplier']*data.qfrc_bias[model.joint(joint['name']).dofadr[0]]
                data.qpos[model.joint(joint['name']).qposadr[0]] = 0.
            mujoco.mj_forward(model, data)
            delta = moving_bias[:5]-data.qfrc_bias[vadr[:5]]
            samples.append(dict(pose=pose['name'], jaw_angle_rad=float(angle),
                                robot_com_shift_m=(moving_com-data.subtree_com[model.body('torso').id]).tolist(),
                                neck_gravity_delta_nm=dict(zip(names[:5], delta.tolist())),
                                jaw_drive_nominal_gravity_nm=float(jaw_gravity)))
    maximum = {n: max(abs(s['neck_gravity_delta_nm'][n]) for s in samples) for n in names[:5]}
    margins = {j['joint']: j['margin_nm'] for j in ledger['joint_summary']}
    # Actual native density items use a 10% uncertainty. This conservative
    # extra bound is compared against the ledger's already perturbed margin.
    bound = {n: 1.1*v for n, v in maximum.items()}
    pass_margin = all(bound[n] < margins[n] for n in names[:5])
    report = dict(schema='goose_native_linkage_static_reduction_bound_v1',
                  sample_count=len(samples), poses=len(poses), samples=samples,
                  maximum_robot_com_shift_m=max(np.linalg.norm(s['robot_com_shift_m']) for s in samples),
                  maximum_nominal_neck_gravity_correction_nm=maximum,
                  native_mass_uncertainty_multiplier=1.1,
                  conservative_extra_neck_gravity_bound_nm=bound,
                  existing_perturbed_static_margin_nm={n: margins[n] for n in names[:5]},
                  existing_neck_static_margins_cover_linkage_motion=pass_margin,
                  maximum_nominal_jaw_drive_gravity_nm=max(abs(s['jaw_drive_nominal_gravity_nm']) for s in samples),
                  manufacturing_release=False, gait_release=False, thermal_release=False,
                  source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
                  limitations=['23 angles at each of seven nominal task poses, not a continuous interval proof.',
                               'Only moving crank/coupler correction is bounded; other assembly gaps and contact/gait remain separate.',
                               '1.1 factor covers the declared native density uncertainty, not arbitrary unmodeled hardware.'])
    (R/'evidence/mechanical_native_linkage_static_bound.json').write_text(json.dumps(report, indent=2)+'\n')
    print('LINKAGE STATIC BOUND', pass_margin, 'COM shift m', report['maximum_robot_com_shift_m'],
          'neck correction Nm', maximum, flush=True)
    return 0 if pass_margin else 1


if __name__ == '__main__':
    raise SystemExit(main())
