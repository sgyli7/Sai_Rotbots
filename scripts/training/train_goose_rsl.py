"""Bounded RSL training with frozen inputs and independently checked ONNX export."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import time

import numpy as np
import onnx
import onnxruntime as ort
import torch
from rsl_rl.runners import OnPolicyRunner

from sai_agent.goose.control import OBS_SIZE, metadata
from sai_agent.goose.locomotion import LocomotionEnv
from sai_agent.goose.rsl import GooseRslVecEnv,runner_config
from sai_agent.paths import resource_root


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--iterations',type=int,default=2);p.add_argument('--envs',type=int,default=2)
    p.add_argument('--horizon',type=int,default=16);p.add_argument('--seed',type=int,default=20260928)
    p.add_argument('--device',default='cpu');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--init-std',type=float,default=.22)
    p.add_argument('--zero-actor-head',action='store_true')
    a=p.parse_args()
    if min(a.iterations,a.envs,a.horizon)<1 or a.envs*a.horizon<4:raise ValueError('Invalid finite training budget')
    root=resource_root();robot=root/'robots/Goose_V0.1'
    a.output.mkdir(parents=True,exist_ok=False)
    snapshot=a.output/'inputs';snapshot.mkdir()
    shutil.copytree(robot/'models/full',snapshot/'model')
    shutil.copyfile(robot/'configs/robot_spec.json',snapshot/'robot_spec.json')
    spec=json.loads((snapshot/'robot_spec.json').read_text());cfg=runner_config(a.horizon,a.init_std)
    source_hashes={str(path.relative_to(root)):sha(path) for path in
        [Path(__file__),*(root/'src/sai_agent/goose').glob('*.py')]}
    (snapshot/'runner_config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    torch.manual_seed(a.seed);np.random.seed(a.seed);torch.set_num_threads(2)
    base=LocomotionEnv(a.envs,a.seed,snapshot/'model/robot.xml',spec);env=GooseRslVecEnv(base)
    runner=OnPolicyRunner(env,copy.deepcopy(cfg),log_dir=None,device=a.device)
    if a.zero_actor_head:
        head=runner.alg.actor.mlp[-1]
        if not isinstance(head,torch.nn.Linear) or head.out_features!=10:
            raise TypeError('Unexpected actor output layer for zero-action initialization')
        torch.nn.init.zeros_(head.weight);torch.nn.init.zeros_(head.bias)
    start=time.monotonic();runner.learn(num_learning_iterations=a.iterations,init_at_random_ep_len=False)
    infos={'environment':env.cfg,'runner_config':cfg,'source_hashes':source_hashes,'seed':a.seed,
           'status':'experimental_unvalidated','torch_rng':torch.get_rng_state(),
           'numpy_rng':base.rng.bit_generator.state,'env_actions':base.actions.copy(),
           'env_commands':base.commands.copy(),'env_phase':base.phase.copy(),'env_age':base.age.copy(),
           'env_qpos':np.array([d.qpos.copy() for d in base.data]),
           'env_qvel':np.array([d.qvel.copy() for d in base.data]),
           'checkpoint_resume_scope':'optimizer/network/RNG captured; exact contact warm-start resume not certified'}
    runner.save(str(a.output/'checkpoint.pt'),infos=infos)
    actor=runner.alg.actor.to('cpu').eval();wrapper=actor.as_onnx(verbose=False).eval()
    policy=a.output/'policy.onnx'
    torch.onnx.export(wrapper,torch.zeros(1,OBS_SIZE),policy,input_names=['observation'],
        output_names=['action'],dynamic_axes={'observation':{0:'batch'},'action':{0:'batch'}},
        opset_version=18,dynamo=False)
    onnx.checker.check_model(onnx.load(policy));session=ort.InferenceSession(str(policy),providers=['CPUExecutionProvider'])
    samples=np.vstack([base.observations(),np.random.default_rng(a.seed).normal(0,.3,(101,OBS_SIZE))]).astype(np.float32)
    with torch.no_grad():expected=wrapper(torch.from_numpy(samples)).numpy()
    actual=session.run(None,{'observation':samples})[0];error=float(np.max(abs(expected-actual)))
    if not np.isfinite(actual).all() or error>1e-5:raise RuntimeError('ONNX inference differs from trained actor')
    result={**metadata(spec),'algorithm':'RSL PPO','rsl_version':importlib.metadata.version('rsl-rl-lib'),
        'seed':a.seed,'iterations':a.iterations,'envs':a.envs,'horizon':a.horizon,'device':a.device,
        'initial_exploration_std':a.init_std,'zero_actor_head':a.zero_actor_head,
        'elapsed_s':time.monotonic()-start,'environment_steps':env.step_count*env.num_envs,
        'failures_during_training':env.failure_count,'mean_training_reward':env.reward_sum/env.reward_count,
        'model_sha256':base.source_model_sha256,'spec_sha256':sha(snapshot/'robot_spec.json'),
        'policy_sha256':sha(policy),'source_hashes':source_hashes,'onnx_parity_max_absolute_error':error,
        'finite_training_and_export_pass':True,'policy_status':'experimental_no_walking_acceptance',
        'full_engineering_acceptance':False,'root_free':True,'external_root_support':False,
        'policy_privileged_state':False,'reward_privileged_state':True}
    (a.output/'metadata.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
