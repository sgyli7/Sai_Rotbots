"""Measure how untrained action noise affects free-base Goose stability."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from sai_agent.goose.locomotion import LocomotionEnv
from sai_agent.paths import resource_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    robot = resource_root() / 'robots/Goose_V0.1'
    command = np.array([.1, 0., 0.])
    cases = []
    for standard_deviation in (.03, .05, .10, .22):
        env = LocomotionEnv(1, seed=20260928)
        env.reset(0, command=command, randomize=False)
        rng = np.random.default_rng(7)
        for step in range(400):
            action = rng.normal(0., standard_deviation, (1, 10))
            _, _, done, info = env.step(action)
            if done[0]:
                break
        cases.append({
            'gaussian_action_std': standard_deviation,
            'elapsed_s': (step + 1) * .02,
            'failure': bool(info[0]['failure']),
            'command_vx_vy_yawrate': command.tolist(),
        })
    result = {
        'scope': 'One fixed-seed untrained-action probe, not a gait policy or proof of robust exploration limits',
        'model_sha256': hashlib.sha256((robot / 'models/full/robot.xml').read_bytes()).hexdigest(),
        'transfer_sha256': hashlib.sha256((robot / 'models/full/rigid_transfer.json').read_bytes()).hexdigest(),
        'initial_pose': 'standing',
        'policy_dt_s': .02,
        'torque_update_dt_s': .005,
        'duration_cap_s': 8.,
        'action_rng_seed': 7,
        'cases': cases,
        'pass': not cases[0]['failure'] and not cases[1]['failure'] and cases[-1]['failure'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
