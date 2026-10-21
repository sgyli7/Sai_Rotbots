"""Bounded CPU physical-I/O smoke; no learning, reward or task-success claim."""
from __future__ import annotations
import os
os.environ.setdefault('MUJOCO_GL', 'egl')
os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = os.environ['MKL_NUM_THREADS'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import argparse, hashlib, json, time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
import numpy as np
from sai_agent.goose_training_io import GooseTrainingIO


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--zip', type=Path, required=True); ap.add_argument('--out', type=Path, required=True); ap.add_argument('--evidence', type=Path, required=True)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=False); args.evidence.mkdir(parents=True, exist_ok=True)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    started = time.monotonic(); env = None; rows = []; failure = None; checks = {}; reset_states = []
    expected = '41ee30e7eeb004986daa9ee55d67c4ae74b638615bb2c29f6dcc3c314197df89'
    try:
        env = GooseTrainingIO(args.zip, expected_manifest_sha256=expected)
        contract = env.contract(); (args.evidence / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')
        # Pure bad-input checks must not advance the live environment.
        t0 = env.physics.data.time
        rejected = 0
        for bad in [np.zeros(17), np.full(18, np.nan)]:
            try: env.step(bad)
            except ValueError: rejected += 1
        checks['invalid_actions_rejected_without_step'] = rejected == 2 and env.physics.data.time == t0
        for episode in range(2):
            obs, state = env.reset(); reset_states.append(env.physics.data.qpos.copy())
            assert obs.shape == (65,) and obs.dtype == np.float32 and np.isfinite(obs).all()
            initial = env.physics.data.qpos.copy()
            for i in range(50):
                if time.monotonic() - started > 175: raise TimeoutError('Bounded wall time reached')
                def small_action(index):
                    a = np.zeros(18); a[0] = .002 * np.sin((index + 1) * .1); a[6] = .001 * np.cos(index * .1)
                    return a
                action = small_action(i)
                previous = float(env.physics.data.time)
                before_obs = env.observe().copy(); before_q = env.physics.data.qpos.copy(); before_v = env.physics.data.qvel.copy()
                if episode == 1 and i == 46:
                    chunk = np.array([small_action(k) for k in range(46, 50)])
                    meta = env.write_sample(args.out / 'language_rgb_chunk', language='Hold the current posture with the following four diagnostic motor actions.', action_chunk=chunk)
                    assert np.array_equal(before_q, env.physics.data.qpos) and np.array_equal(before_v, env.physics.data.qvel) and env.physics.data.time == previous
                obs, state = env.step(action)
                assert abs(env.physics.data.time - previous - .02) < 1e-10
                assert np.isfinite(obs).all() and obs.shape == (65,)
                assert np.max(abs(env.physics.data.actuator_force) - env.physics.cont) <= 1e-9
                assert not np.any(env.physics.data.xfrc_applied) and not np.any(env.physics.data.qfrc_applied)
                assert env.physics.internal_pin_residual() <= 25e-6
                rows.append(dict(episode=episode, time=env.physics.data.time, time_before=previous, time_after=env.physics.data.time, action=action.copy(), observation=obs.copy(), observation_before=before_obs, observation_after=obs.copy(), qpos_before=before_q, qvel_before=before_v, qpos=env.physics.data.qpos.copy(), qvel=env.physics.data.qvel.copy(), torque=env.physics.data.actuator_force.copy(), loop=env.physics.internal_pin_residual()))
            assert np.max(abs(env.physics.data.qpos - initial)) > 1e-8
        checks['two_resets_identical_qpos'] = bool(np.array_equal(*reset_states))
        checks['100_actions_exact_clock_finite_caps_loop_hidden0'] = len(rows) == 100
        z = np.load(args.out / 'language_rgb_chunk/sample.npz'); image = z['rgb']
        executed = rows[-4:]
        checks['same_state_rgb_and_sample_readback'] = bool(image.shape == (240,320,3) and image.dtype == np.uint8 and np.ptp(image) > 0 and np.array_equal(z['proprio'],executed[0]['observation_before']) and np.array_equal(z['qpos'],executed[0]['qpos_before']) and np.array_equal(z['qvel'],executed[0]['qvel_before']))
        checks['proposed_chunk_actually_executed_exactly'] = bool(np.array_equal(z['action_chunk'],np.array([r['action']for r in executed])))
        checks['preaction_and_poststate_time_alignment'] = bool(np.max(abs(z['action_time_s']-np.array([r['time_before']for r in executed])))<1e-12 and np.max(abs(z['action_time_s']-[.92,.94,.96,.98]))<1e-12 and np.max(abs(np.array([r['time_after']for r in executed])-[.94,.96,.98,1.]))<1e-12)
        assert all(checks.values())
        execution_receipt={'status':'EXECUTED_CHUNK_EXACT_ACTION_AND_TIME_ALIGNMENT','sample_npz_sha256':hashlib.sha256((args.out/'language_rgb_chunk/sample.npz').read_bytes()).hexdigest(),'language':json.load(open(args.out/'language_rgb_chunk/sample.json'))['language'],'sample_state_time_s':meta['actual_state_time_s'],'command_time_s':[r['time_before']for r in executed],'post_state_time_s':[r['time_after']for r in executed],'action_chunk_matches_actual_actions':True,'preaction_RGB_proprio_q_qvel_matches_first_execution_row':True,'actual_actions':z['action_chunk'].tolist(),'not_task_success_or_human_demonstration':True}
        (args.evidence/'execution_receipt.json').write_text(json.dumps(execution_receipt,indent=2)+'\n')
        from PIL import Image
        Image.fromarray(image).save(args.evidence / 'debug_rgb.png')
    except Exception as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if rows:
            np.savez_compressed(args.out / 'state_action_trajectory.npz', **{k:np.asarray([r[k] for r in rows]) for k in rows[0]})
            reloaded = np.load(args.out / 'state_action_trajectory.npz'); checks['trajectory_roundtrip'] = bool(np.array_equal(reloaded['action'],np.asarray([r['action']for r in rows])))
        if env is not None:
            np.savez_compressed(args.out / 'final_actual_state.npz', qpos=env.physics.data.qpos, qvel=env.physics.data.qvel, ctrl=env.physics.data.ctrl, time=env.physics.data.time)
        receipt = {'status':'PASS_PHYSICAL_TRAINING_IO_ONLY' if failure is None and all(checks.values()) else 'NOT_PASSED', 'checks':checks,'failure':failure,'completed_actions':len(rows),'actual_simulated_s':len(rows)*.02,'explicit_resets':len(reset_states),'wall_s':time.monotonic()-started,'physics_operator':'F only','PPO_updates':0,'GPU_training':False,'task_or_reward_changes':False,'model_manifest_sha256':expected,'zip_sha256':hashlib.sha256(args.zip.read_bytes()).hexdigest(),'raw_artifacts':str(args.out.resolve()),'source_bindings':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__).resolve(),Path(__file__).resolve().parents[2]/'src/sai_agent/goose_training_io.py']},'limitations':['No standing/task success or learning convergence claim','Debug camera is uncalibrated simulator viewpoint','Legacy08 policy actions are incompatible; motor input axis5 is explicit']}
        (args.evidence / 'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if env is not None: env.close()
        print(json.dumps(receipt,indent=2))
    return 0 if failure is None and all(checks.values()) else 1
if __name__ == '__main__': raise SystemExit(main())
