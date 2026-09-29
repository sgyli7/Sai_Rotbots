"""Train an experimental Goose policy with a standalone, finite PPO run.

No Sai_Lab monkey patches, non-finite masking, welded root or object assistance.
The produced policy is a candidate until independent task evaluation passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import shutil

import numpy as np
import torch
from torch import nn

from sai_agent.goose.control import ACTION_SIZE, OBS_SIZE, metadata
from sai_agent.goose.locomotion import LocomotionEnv


class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()
        self.actor=nn.Sequential(nn.Linear(OBS_SIZE,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh(),nn.Linear(128,ACTION_SIZE))
        self.critic=nn.Sequential(nn.Linear(OBS_SIZE,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh(),nn.Linear(128,1))
        self.log_std=nn.Parameter(torch.full((ACTION_SIZE,),-1.5))
        for layer in (self.actor[-1],):nn.init.orthogonal_(layer.weight,.01);nn.init.zeros_(layer.bias)

    def distribution(self,obs):
        return torch.distributions.Normal(self.actor(obs),self.log_std.exp().expand(obs.shape[0],-1))

    def value(self,obs):return self.critic(obs).squeeze(-1)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iterations',type=int,default=300)
    p.add_argument('--envs',type=int,default=8);p.add_argument('--horizon',type=int,default=32)
    p.add_argument('--seed',type=int,default=20260928);p.add_argument('--device',default='cpu')
    p.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/ppo_rc1'))
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    torch.manual_seed(args.seed);np.random.seed(args.seed);torch.set_num_threads(2)
    env=LocomotionEnv(args.envs,args.seed);net=ActorCritic().to(args.device);optimizer=torch.optim.Adam(net.parameters(),lr=3e-4)
    training_metadata=metadata(env.mapping.spec)
    snapshot=args.output/'model_snapshot';snapshot.mkdir(exist_ok=True)
    shutil.copyfile(env.model_path,snapshot/'robot.xml')
    if (env.model_path.parent/'visuals').exists():shutil.copytree(env.model_path.parent/'visuals',snapshot/'visuals',dirs_exist_ok=True)
    obs=env.observations();start=time.monotonic();history=[]
    for iteration in range(args.iterations):
        observations=[];actions=[];logprobs=[];values=[];rewards=[];dones=[];failures=0
        for _ in range(args.horizon):
            t=torch.as_tensor(obs,device=args.device)
            with torch.no_grad():
                dist=net.distribution(t);action=dist.sample();lp=dist.log_prob(action).sum(-1);value=net.value(t)
            next_obs,reward,done,info=env.step(action.cpu().numpy())
            observations.append(t);actions.append(action);logprobs.append(lp);values.append(value)
            rewards.append(torch.as_tensor(reward,device=args.device));dones.append(torch.as_tensor(done,device=args.device))
            failures+=sum(x['failure'] for x in info);obs=next_obs
        with torch.no_grad():last=net.value(torch.as_tensor(obs,device=args.device))
        advantages=[];gae=torch.zeros(args.envs,device=args.device)
        for k in reversed(range(args.horizon)):
            mask=(~dones[k]).float();delta=rewards[k]+.99*last*mask-values[k]
            gae=delta+.99*.95*mask*gae;advantages.insert(0,gae);last=values[k]
        o=torch.stack(observations).reshape(-1,OBS_SIZE);a=torch.stack(actions).reshape(-1,ACTION_SIZE)
        old_lp=torch.stack(logprobs).flatten();v=torch.stack(values).flatten()
        adv=torch.stack(advantages).flatten();returns=adv+v;adv=(adv-adv.mean())/(adv.std()+1e-8)
        n=len(o)
        for _ in range(4):
            order=torch.randperm(n,device=args.device)
            for indices in order.split(min(256,n)):
                dist=net.distribution(o[indices]);lp=dist.log_prob(a[indices]).sum(-1)
                ratio=(lp-old_lp[indices]).exp();policy_loss=-torch.minimum(ratio*adv[indices],ratio.clamp(.8,1.2)*adv[indices]).mean()
                loss=policy_loss+.5*(net.value(o[indices])-returns[indices]).square().mean()-.003*dist.entropy().sum(-1).mean()
                if not torch.isfinite(loss):raise FloatingPointError('Non-finite PPO loss; run aborted')
                optimizer.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),1.);optimizer.step()
        record={'iteration':iteration+1,'mean_step_reward':float(torch.stack(rewards).mean()),
                'failures':failures,'elapsed_s':time.monotonic()-start,'loss':float(loss.detach()),'std':float(net.log_std.exp().mean().detach())}
        history.append(record)
        if iteration%10==0 or iteration==args.iterations-1:
            print(json.dumps(record),flush=True)
            torch.save({'state_dict':net.state_dict(),'iteration':iteration+1,'seed':args.seed},args.output/'checkpoint.pt')
    net.cpu().eval()
    torch.onnx.export(net.actor,torch.zeros(1,OBS_SIZE),args.output/'policy.onnx',input_names=['observation'],output_names=['action'],opset_version=18,dynamo=False)
    meta=training_metadata;meta.update(policy_status='experimental_requires_independent_evaluation',algorithm='PPO',
        seed=args.seed,iterations=args.iterations,envs=args.envs,horizon=args.horizon,action_target_scale_rad=.3,
        model_sha256=env.source_model_sha256,
        policy_sha256=hashlib.sha256((args.output/'policy.onnx').read_bytes()).hexdigest(),
        physics_support={'root_free':True,'external_root_force':False,'reward_privileged_state':True,
                         'policy_privileged_state':False,'gravity_compensation':'measured model joint/root state bias'},
        last_training_record=history[-1],full_acceptance=False)
    (args.output/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    (args.output/'history.json').write_text(json.dumps(history,indent=2)+'\n')
    print(json.dumps(meta,indent=2))


if __name__=='__main__':main()
