"""Compare standing stability at the controller's actual torque update cadence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from sai_agent.goose.locomotion import LocomotionEnv


def probe(update_ms: int, leg_kd: float, duration_s: float) -> dict:
    env = LocomotionEnv(1, seed=20260928)
    env.reset(0, command=np.zeros(3), randomize=False)
    env.mapping.kd[:10] = leg_kd
    data = env.data[0]
    start = data.qpos[:3].copy()
    target = env.stance.copy()
    physics_s = float(env.model.opt.timestep)
    period = round(update_ms / 1000 / physics_s)
    assert period > 0 and abs(period * physics_s - update_ms / 1000) < 1e-9
    max_tilt = 0.0
    saturation = 0
    failed = False
    for step in range(round(duration_s / physics_s)):
        if step % period == 0:
            q = data.qpos[env.mapping.qpos]
            rotation = data.xmat[env.torso].reshape(3, 3)
            ff = env.rigid.gravity_torque(q, rotation)
            torque = env.mapping.torque(q, data.qvel[env.mapping.dof], target, ff)
        saturation += int(np.any(abs(torque) >= env.mapping.limits - 1e-6))
        data.ctrl[env.mapping.actuator] = torque
        mujoco.mj_step(env.model, data)
        rotation = data.xmat[env.torso].reshape(3, 3)
        tilt = float(np.arccos(np.clip(rotation[2, 2], -1, 1)))
        max_tilt = max(max_tilt, tilt)
        if tilt > .65 or data.qpos[2] < env.home_root_z - .08:
            failed = True
            break
    return {
        'torque_update_dt_s': update_ms / 1000,
        'leg_kd_Nm_s_rad': leg_kd,
        'elapsed_s': (step + 1) * physics_s,
        'failed': failed,
        'max_tilt_deg': float(np.degrees(max_tilt)),
        'root_displacement_m': float(np.linalg.norm(data.qpos[:3] - start)),
        'saturation_physics_steps': saturation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    env = LocomotionEnv(1, seed=20260928)
    cases = [probe(period, kd, 4.0) for period, kd in ((1, .30), (5, .30), (5, .10))]
    result = {
        'scope': 'MuJoCo free-base neutral standing cadence/damping diagnostic; no walking or hardware acceptance',
        'model_sha256': env.source_model_sha256,
        'transfer_sha256': hashlib.sha256((env.model_path.parent / 'rigid_transfer.json').read_bytes()).hexdigest(),
        'physics_dt_s': float(env.model.opt.timestep),
        'no_double_support': True,
        'leg_kp_Nm_rad': 15.0,
        'cases': cases,
        'pass': not cases[0]['failed'] and cases[1]['failed'] and not cases[2]['failed'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
