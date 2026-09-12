"""Bounded, reproducible GPU PPO experiment; never silently use the CPU."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import numpy as np
import torch
import warp as wp
from rsl_rl.algorithms import PPO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from sai_agent.env import LocomotionEnv

p = argparse.ArgumentParser()
p.add_argument('--worlds', type=int, default=256)
p.add_argument('--seconds', type=float, default=300)
p.add_argument('--iterations', type=int, default=100000)
p.add_argument('--seed', type=int, default=47)
p.add_argument('--name', default='flat-001')
p.add_argument('--resume', type=Path)
p.add_argument('--stage', choices=['flat','stairs'],default='flat')
p.add_argument('--max-riser',type=float,default=.02)
p.add_argument('--reset-std',type=float,help='Explicit exploration reset when changing terrain curriculum')
p.add_argument('--lift-height',type=float,default=.055)
p.add_argument('--heading-control',action='store_true')
p.add_argument('--ascent-only',action='store_true')
p.add_argument('--min-riser',type=float,default=.006)
p.add_argument('--speed',type=float)
p.add_argument('--leg-scale',type=float,default=.18)
args = p.parse_args()
out = ROOT/'artifacts'/args.name
out.mkdir(parents=True, exist_ok=False)
cfg = json.loads((ROOT/'configs/flat.json').read_text())
source_sha256={str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
    for f in list((ROOT/'src/sai_agent').glob('*.py'))+[Path(__file__)]}
(out/'source').mkdir()
for relative in source_sha256:
    snapshot=out/'source'/relative
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    snapshot.write_bytes((ROOT/relative).read_bytes())
if args.stage=='stairs':
    from sai_agent.stair_env import StairEnv
    env=StairEnv(ROOT/'models/locomotion.xml',args.worlds,args.seed,args.max_riser,out,
                lift_height=args.lift_height,heading_control=args.heading_control,
                ascent_only=args.ascent_only,min_riser=args.min_riser,speed=args.speed,leg_scale=args.leg_scale)
else:
    env = LocomotionEnv(ROOT/'models/locomotion.xml', args.worlds, args.seed)
obs = env.get_observations()
alg = PPO.construct_algorithm(obs, env, copy.deepcopy(cfg), env.device)
if args.resume:
    previous = torch.load(args.resume, map_location=env.device, weights_only=True)
    alg.load(previous, None, True)
else:
    # Start near the verified analytical controller instead of a large random
    # residual. The distribution still explores every controlled joint.
    with torch.no_grad():
        linear = [m for m in alg.actor.modules() if isinstance(m, torch.nn.Linear)][-1]
        linear.weight.mul_(.01)
        linear.bias.zero_()
if args.reset_std is not None:
    with torch.no_grad():
        alg.actor.distribution.log_std_param.fill_(float(__import__('math').log(args.reset_std)))
alg.train_mode()
env.backend.sync()
start = time.monotonic()
cpu_start = time.process_time()
step_count = 0
last_checkpoint=0.


def save_checkpoint(iterations,status,filename):
    metadata = dict(schema_version=1,cfg=cfg,seed=args.seed,steps=step_count,
        stage=args.stage,max_riser=args.max_riser if args.stage=='stairs' else None,
        lift_height=args.lift_height,heading_control=args.heading_control,
        ascent_only=args.ascent_only,min_riser=args.min_riser,speed=args.speed,
        leg_scale=args.leg_scale,
        reset_std=args.reset_std,status=status,iterations=iterations,
        device=torch.cuda.get_device_name(),cpu_threads=torch.get_num_threads(),
        training_wall_seconds=time.monotonic()-start,process_cpu_seconds=time.process_time()-cpu_start,
        model_sha256=hashlib.sha256((ROOT/'models/locomotion.xml').read_bytes()).hexdigest(),
        training_scene_sha256=hashlib.sha256((out/'stairs.xml').read_bytes()).hexdigest() if args.stage=='stairs' else None,
        observation_size=82,action_size=16,control_hz=50,source_sha256=source_sha256,
        resume=str(args.resume) if args.resume else None)
    torch.save(dict(**alg.save(),metadata=metadata,rng_state=torch.get_rng_state(),
                    cuda_rng_state=torch.cuda.get_rng_state()),out/filename)
    (out/'run.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


print('TRAINING_STARTED', torch.cuda.get_device_name(), flush=True)
log = (out/'iterations.jsonl').open('w')
for iteration in range(args.iterations):
    metrics = {}
    reward_sum = 0
    with torch.inference_mode():
        for _ in range(cfg['num_steps_per_env']):
            actions = alg.act(obs)
            if not torch.isfinite(actions).all():
                save_checkpoint(iteration,'failed-policy-nonfinite','failed-policy.pt')
                raise RuntimeError('Non-finite policy action before physics')
            before={'q':env.backend.q.clone(),'v':env.backend.v.clone(),
                    'warmstart':wp.to_torch(env.backend.data.qacc_warmstart).clone(),
                    'mocap':wp.to_torch(env.backend.data.mocap_pos).clone(),
                    'episode_step':env.episode_length_buf.clone(),'command':env.command.clone(),
                    'obs':obs['policy'].clone()}
            obs, rewards, dones, extras = env.step(actions)
            if not torch.isfinite(obs['policy']).all() or not torch.isfinite(rewards).all():
                bad=(~torch.isfinite(obs['policy']).all(-1)) | (~torch.isfinite(rewards))
                np.savez_compressed(out/'nonfinite-replay.npz',
                    **{k:v[bad].cpu().numpy() for k,v in before.items()},
                    action=actions[bad].cpu().numpy(),target=env.backend.target[bad].cpu().numpy(),
                    post_q=env.backend.q[bad].cpu().numpy(),post_v=env.backend.v[bad].cpu().numpy(),
                    post_obs=obs['policy'][bad].cpu().numpy(),reward=rewards[bad].cpu().numpy())
                save_checkpoint(iteration,'failed-physics-nonfinite','failed-candidate.pt')
                raise RuntimeError('Non-finite physics state; experiment failed')
            alg.process_env_step(obs, rewards, dones, extras)
            reward_sum += rewards.mean().item()
            for k, v in extras['log'].items():
                metrics[k] = metrics.get(k, 0.)+v.item()
        alg.compute_returns(obs)
    losses = alg.update()
    step_count += args.worlds*cfg['num_steps_per_env']
    row = dict(iteration=iteration+1, steps=step_count, seconds=time.monotonic()-start,
        reward=reward_sum/cfg['num_steps_per_env'], losses=losses,
        **{k: v/cfg['num_steps_per_env'] for k, v in metrics.items()})
    log.write(json.dumps(row)+'\n'); log.flush()
    if iteration % 10 == 0:
        print(json.dumps(row), flush=True)
    if row['seconds']-last_checkpoint>=60:
        save_checkpoint(iteration+1,'unvalidated-checkpoint',f'checkpoint_{iteration+1:06d}.pt')
        last_checkpoint=row['seconds']
    if row['seconds'] >= args.seconds:
        break
env.backend.sync()
metadata=save_checkpoint(iteration+1,'training-complete-unvalidated','policy.pt')
print('TRAINING_COMPLETE', json.dumps(metadata), flush=True)
