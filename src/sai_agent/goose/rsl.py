"""RSL 5 VecEnv boundary; the existing SI observation/action contract is kept."""
from __future__ import annotations

import numpy as np
import torch
from tensordict import TensorDict
from rsl_rl.env import VecEnv

from .control import ACTION_SIZE, OBS_SIZE, metadata


def runner_config(horizon=32, init_std=.22):
    if not 0 < init_std <= 1:
        raise ValueError('Initial exploration standard deviation must be in (0, 1]')
    return {
        'num_steps_per_env':horizon,'save_interval':10,
        'obs_groups':{'actor':['policy'],'critic':['policy']},
        'actor':{'class_name':'rsl_rl.models:MLPModel','hidden_dims':[128,128],
                 'activation':'tanh','obs_normalization':False,
                 'distribution_cfg':{'class_name':'rsl_rl.modules.distribution:GaussianDistribution',
                                     'init_std':init_std,'std_type':'log'}},
        'critic':{'class_name':'rsl_rl.models:MLPModel','hidden_dims':[128,128],
                  'activation':'tanh','obs_normalization':False},
        'algorithm':{'class_name':'rsl_rl.algorithms:PPO','num_learning_epochs':4,
                     'num_mini_batches':4,'learning_rate':.0003,'schedule':'fixed',
                     'entropy_coef':.003,'gamma':.99,'lam':.95,'clip_param':.2},
    }


class GooseRslVecEnv(VecEnv):
    def __init__(self,base):
        self.base=base;self.num_envs=base.num_envs;self.num_actions=ACTION_SIZE
        self.device='cpu';self.max_episode_length=600
        self.episode_length_buf=torch.as_tensor(base.age.copy(),dtype=torch.long)
        self.cfg={**metadata(base.mapping.spec),'model_sha256':base.source_model_sha256,
                  'episode_length_steps':self.max_episode_length}
        self.step_count=0;self.failure_count=0;self.reward_sum=0.;self.reward_count=0

    def _pack(self,array):
        tensor=torch.as_tensor(array,dtype=torch.float32)
        if tensor.shape!=(self.num_envs,OBS_SIZE) or not torch.isfinite(tensor).all():
            raise FloatingPointError('Invalid Goose observation batch')
        return TensorDict({'policy':tensor},batch_size=[self.num_envs])

    def get_observations(self):return self._pack(self.base.observations())

    def step(self,actions):
        actions=actions.detach().to('cpu')
        if actions.shape!=(self.num_envs,ACTION_SIZE) or not torch.isfinite(actions).all():
            raise FloatingPointError('Invalid Goose action batch')
        obs,rewards,dones,rows=self.base.step(actions.numpy())
        rewards=torch.as_tensor(rewards,dtype=torch.float32)
        if not torch.isfinite(rewards).all():raise FloatingPointError('Non-finite reward')
        self.episode_length_buf.copy_(torch.as_tensor(self.base.age,dtype=torch.long))
        self.step_count+=1;self.failure_count+=sum(r['failure'] for r in rows)
        self.reward_sum+=float(rewards.sum());self.reward_count+=self.num_envs
        extras={'time_outs':torch.tensor([r['timeout'] and not r['failure'] for r in rows],dtype=torch.bool),
                'log':{'/goose/failure_rate':float(np.mean([r['failure'] for r in rows]))}}
        return self._pack(obs),rewards,torch.as_tensor(dones,dtype=torch.bool),extras
