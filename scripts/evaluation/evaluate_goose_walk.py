"""Replay a Goose ONNX policy on free-base MuJoCo without training resets.

This is a gait diagnostic, not a claim of contact-task or cross-engine acceptance.
The policy sees only the production 53-value observation. World pose and contacts
are read only after each step for scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort

from sai_agent.goose.control import ACTION_SIZE, OBS_SIZE, metadata
from sai_agent.goose.locomotion import LocomotionEnv
from sai_agent.paths import resource_root


CASES = (
    ('idle', (0., 0., 0.)),
    ('forward', (.10, 0., 0.)),
    ('backward', (-.025, 0., 0.)),
    ('turn_left', (0., 0., .20)),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_case(session, env: LocomotionEnv, name: str, command, duration: float):
    env.reset(0, command=np.asarray(command), randomize=False)
    d = env.data[0]
    start = d.qpos[:3].copy()
    yaw_values = []
    trace = []
    contact = {'left': [], 'right': []}
    foot_height = {'left': [], 'right': []}
    max_tilt = 0.
    failures = 0
    steps = round(duration / .02)
    input_name = session.get_inputs()[0].name
    for k in range(steps):
        obs = env.observations()
        if obs.shape != (1, OBS_SIZE) or not np.isfinite(obs).all():
            raise ValueError('Invalid policy observation')
        action = session.run(None, {input_name: obs})[0]
        if action.shape != (1, ACTION_SIZE) or not np.isfinite(action).all():
            raise ValueError('Invalid policy action')
        _, _, done, info = env.step(action)
        if done[0]:
            failures += int(info[0]['failure'])
            break
        torso = d.xmat[env.torso].reshape(3, 3)
        yaw_values.append(float(np.arctan2(torso[1, 0], torso[0, 0])))
        max_tilt = max(max_tilt, float(np.arccos(np.clip(torso[2, 2], -1., 1.))))
        touching = {'left': False, 'right': False}
        for c in d.contact:
            pair = {env.model.geom(c.geom1).name, env.model.geom(c.geom2).name}
            for side in touching:
                if 'floor' in pair and f'{side}_ankle_pitch_foot' in pair:
                    touching[side] = True
        for side in touching:
            contact[side].append(touching[side])
            foot_height[side].append(float(d.site(env.model.site(f'{side}_foot').id).xpos[2]))
        if k % 20 == 0:
            trace.append({'t_s': round((k + 1) * .02, 3),
                          'root_xyz_m': d.qpos[:3].tolist(),
                          'contacts': touching})
    elapsed = (k + 1) * .02
    delta = (d.qpos[:3] - start).tolist() if failures == 0 else None
    yaw_change = float(np.unwrap(yaw_values)[-1] - np.unwrap(yaw_values)[0]) if len(yaw_values) > 1 else None
    contact_breaks = {side: sum(contact[side][j - 1] and not contact[side][j]
                                for j in range(1, len(contact[side]))) for side in contact}
    lifts = {side: max(foot_height[side], default=0.) for side in foot_height}
    completed = failures == 0 and elapsed >= duration - .01
    # Translation alone can come from continuous foot slip; require visible
    # alternating stance breaks for the forward/backward gait cases.
    gait = all(contact_breaks[s] >= 2 and lifts[s] > .008 for s in contact)
    if name == 'idle':
        passed = completed and abs(delta[0]) < .05 and abs(delta[1]) < .05
    elif name == 'forward':
        passed = completed and delta[0] >= .05 * duration and abs(delta[1]) < .20 and gait
    elif name == 'backward':
        passed = completed and delta[0] <= -.0125 * duration and gait
    else:
        passed = completed and yaw_change is not None and yaw_change >= .10 * duration
    passed = bool(passed and max_tilt < np.deg2rad(25))
    return {'name': name, 'command_vx_vy_yawrate': list(command), 'elapsed_s': elapsed,
            'completed': completed, 'failures': failures, 'root_delta_m': delta,
            'yaw_change_rad': yaw_change, 'max_tilt_deg': float(np.degrees(max_tilt)),
            'foot_contact_breaks': contact_breaks, 'foot_peak_height_m': lifts,
            'gait_observed': gait, 'pass': passed, 'trace': trace}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=8.)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not .1 <= args.duration <= 11.9:
        raise ValueError('Duration must be between 0.1 and 11.9 s')
    root = resource_root(); robot = root / 'robots/Goose_V0.1'
    model = robot / 'models/full/robot.xml'
    spec_path = robot / 'configs/robot_spec.json'
    spec = json.loads(spec_path.read_text())
    meta = json.loads(args.metadata.read_text())
    expected = metadata(spec)
    for key in ('version', 'units', 'frame', 'observation_size', 'action_size',
                'action_reference_pose', 'action_position_scale_rad', 'torque_feedforward',
                'action_joint_names', 'encoder_joint_names', 'control_dt_s'):
        if meta.get(key) != expected[key]:
            raise ValueError(f'Policy contract mismatch: {key}')
    for key, digest in (('model_sha256', sha(model)), ('spec_sha256', sha(spec_path)),
                        ('policy_sha256', sha(args.policy))):
        if meta.get(key) != digest:
            raise ValueError(f'Policy source hash mismatch: {key}')
    session = ort.InferenceSession(str(args.policy), providers=['CPUExecutionProvider'])
    env = LocomotionEnv(1, seed=20260928, model_path=model, spec=spec)
    results = [run_case(session, env, name, cmd, args.duration) for name, cmd in CASES]
    result = {'scope': 'MuJoCo free-base training-environment replay; no Godot or real-hardware acceptance',
              'model_sha256': sha(model), 'spec_sha256': sha(spec_path),
              'policy_sha256': sha(args.policy), 'duration_per_case_s': args.duration,
              'criteria': 'idle drift <5 cm; forward/backward >=50% commanded travel with two stance breaks and >8 mm foot lift per side; turn >=50% yaw; all survive and tilt <25 deg',
              'cases': results, 'pass': all(item['pass'] for item in results)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'cases'} | {
        'cases': [{key: value for key, value in item.items() if key != 'trace'} for item in results]}, indent=2))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
