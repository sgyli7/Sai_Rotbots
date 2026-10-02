"""Bounded PPO experiment on an explicitly provisional Goose R2 physics trial.

The actor sees simulated IMU and joint states only. This is a diagnostic of
whether leg-position residuals can improve standing under the selected torque
caps; it is not a walking policy or an engineering release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

import mujoco
import numpy as np
import torch
from tensordict import TensorDict
from rsl_rl.env import VecEnv
from rsl_rl.runners import OnPolicyRunner


LEG_NAMES = [f'{side}_{name}' for side in ('right','left')
             for name in ('hip_yaw','hip_roll','hip_pitch','knee_pitch','ankle_pitch')]
NECK_NAMES = ['neck_lower_pitch','neck_upper_pitch','head_pitch']
JOINT_NAMES = LEG_NAMES + NECK_NAMES
OBS_SIZE = 3 + 3 + 3 + 13 + 13 + 10
ACTION_SIZE = 10
CONTROL_STEPS = 20
EPISODE_STEPS = 200


def source_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runner_config(horizon, std):
    return {
        'num_steps_per_env':horizon,'save_interval':1000,
        'obs_groups':{'actor':['policy'],'critic':['policy']},
        'actor':{'class_name':'rsl_rl.models:MLPModel','hidden_dims':[128,128],
                 'activation':'tanh','obs_normalization':False,
                 'distribution_cfg':{'class_name':'rsl_rl.modules.distribution:GaussianDistribution',
                                     'init_std':std,'std_type':'log'}},
        'critic':{'class_name':'rsl_rl.models:MLPModel','hidden_dims':[128,128],
                  'activation':'tanh','obs_normalization':False},
        'algorithm':{'class_name':'rsl_rl.algorithms:PPO','num_learning_epochs':4,
                     'num_mini_batches':4,'learning_rate':.0003,'schedule':'fixed',
                     'entropy_coef':.002,'gamma':.99,'lam':.95,'clip_param':.2},
    }


class StanceTrialEnv(VecEnv):
    def __init__(self,model_path,num_envs,seed,device):
        self.model=mujoco.MjModel.from_xml_path(str(model_path))
        self.model_path=model_path
        self.model_sha256=source_hash(model_path)
        self.cfg={'model_sha256':self.model_sha256,'observation_size':OBS_SIZE,
                  'action_size':ACTION_SIZE,'episode_steps':EPISODE_STEPS,
                  'status':'experimental_stance_trial'}
        self.num_envs=num_envs
        self.num_actions=ACTION_SIZE
        self.device=device
        self.max_episode_length=EPISODE_STEPS
        self.rng=np.random.default_rng(seed)
        self.qadr=np.array([self.model.joint(n).qposadr[0] for n in JOINT_NAMES])
        self.vadr=np.array([self.model.joint(n).dofadr[0] for n in JOINT_NAMES])
        self.ctrl_limit=np.array([self.model.actuator(n+'_motor').ctrlrange[1]
                                  for n in JOINT_NAMES])
        if self.model.nu!=len(JOINT_NAMES) or not np.all(self.ctrl_limit>0):
            raise ValueError('Unexpected trial actuator contract')
        self.torso=self.model.body('torso').id
        self.data=[mujoco.MjData(self.model) for _ in range(num_envs)]
        self.age=np.zeros(num_envs,dtype=np.int64)
        self.previous=np.zeros((num_envs,ACTION_SIZE))
        self.episode_length_buf=torch.zeros(num_envs,dtype=torch.long,device=device)
        self.training_steps=0
        self.failure_count=0
        self.reward_sum=0.
        self.reward_count=0
        for i in range(num_envs):self.reset(i)

    def reset(self,i,perturb=True):
        d=self.data[i]
        mujoco.mj_resetData(self.model,d)
        d.qpos[:3]=[-.01,0,.35]
        d.qpos[3:7]=[1,0,0,0]
        if perturb:
            d.qpos[:2]+=self.rng.uniform(-.005,.005,2)
            roll,pitch=self.rng.uniform(-.035,.035,2)
            q_roll=np.array([math.cos(roll/2),math.sin(roll/2),0,0])
            q_pitch=np.array([math.cos(pitch/2),0,math.sin(pitch/2),0])
            q=np.empty(4);mujoco.mju_mulQuat(q,q_roll,q_pitch)
            d.qpos[3:7]=q
            d.qpos[self.qadr]+=self.rng.uniform(-.015,.015,len(JOINT_NAMES))
        mujoco.mj_forward(self.model,d)
        self.age[i]=0
        self.previous[i]=0

    def _obs(self,i):
        d=self.data[i]
        rot=d.xmat[self.torso].reshape(3,3)
        velocity=np.zeros(6)
        mujoco.mj_objectVelocity(self.model,d,mujoco.mjtObj.mjOBJ_BODY,
                                 self.torso,velocity,1)
        projected_gravity=rot.T@np.array([0,0,-1.])
        return np.concatenate([np.clip(velocity[:3],-10,10)*.25,
                               projected_gravity,
                               np.zeros(3),
                               d.qpos[self.qadr],
                               np.clip(d.qvel[self.vadr],-30,30)*.05,
                               self.previous[i]]).astype(np.float32)

    def get_observations(self):
        values=np.stack([self._obs(i) for i in range(self.num_envs)])
        if values.shape!=(self.num_envs,OBS_SIZE) or not np.isfinite(values).all():
            raise FloatingPointError('Invalid trial PPO observations')
        return TensorDict({'policy':torch.as_tensor(values,device=self.device)},
                          batch_size=[self.num_envs])

    def _advance(self,i,action):
        d=self.data[i]
        action=np.clip(np.asarray(action,dtype=float),-1,1)
        target=np.zeros(len(JOINT_NAMES))
        target[:ACTION_SIZE]=.18*action
        torque_cost=0.
        for _ in range(CONTROL_STEPS):
            q=d.qpos[self.qadr];qd=d.qvel[self.vadr]
            demand=40*(target-q)-2*qd
            torque=np.clip(demand,-self.ctrl_limit,self.ctrl_limit)
            d.ctrl[:]=torque
            torque_cost+=np.mean((torque/self.ctrl_limit)**2)
            mujoco.mj_step(self.model,d)
        rot=d.xmat[self.torso].reshape(3,3)
        tilt=math.acos(float(np.clip(rot[2,2],-1,1)))
        height_error=float(d.qpos[2]-.35)
        root_xy=float(np.linalg.norm(d.qpos[:2]-[-.01,0]))
        reward=(1.5*math.exp(-tilt**2/.15**2)
                +math.exp(-height_error**2/.04**2)
                +.3*math.exp(-root_xy**2/.12**2)
                -.03*torque_cost/CONTROL_STEPS
                -.02*np.mean(action**2)
                -.02*np.mean((action-self.previous[i])**2))
        self.previous[i]=action
        self.age[i]+=1
        failed=(tilt>.7 or d.qpos[2]<.24 or not np.isfinite(d.qpos).all())
        timeout=self.age[i]>=EPISODE_STEPS
        if failed:reward-=4
        return float(reward),bool(failed),bool(timeout),tilt,float(d.qpos[2])

    def step(self,actions):
        array=actions.detach().to('cpu').numpy()
        if array.shape!=(self.num_envs,ACTION_SIZE) or not np.isfinite(array).all():
            raise ValueError('Invalid trial PPO action batch')
        rewards=np.zeros(self.num_envs,dtype=np.float32)
        dones=np.zeros(self.num_envs,dtype=bool)
        timeouts=np.zeros(self.num_envs,dtype=bool)
        failures=0
        for i,action in enumerate(array):
            reward,failed,timeout,_,_=self._advance(i,action)
            rewards[i]=reward
            dones[i]=failed or timeout
            timeouts[i]=timeout and not failed
            failures+=failed
            if dones[i]:self.reset(i)
        self.episode_length_buf.copy_(torch.as_tensor(self.age,device=self.device))
        self.training_steps+=1
        self.failure_count+=failures
        self.reward_sum+=float(rewards.sum())
        self.reward_count+=self.num_envs
        return (self.get_observations(),
                torch.as_tensor(rewards,device=self.device),
                torch.as_tensor(dones,device=self.device),
                {'time_outs':torch.as_tensor(timeouts,device=self.device),
                 'log':{'/trial/failures':float(failures/self.num_envs)}})


def evaluate(model_path,policy,seed,episodes,device):
    env=StanceTrialEnv(model_path,1,seed,device)
    records=[]
    for episode in range(episodes):
        env.reset(0,perturb=True)
        max_tilt=0.
        min_z=1.
        for step in range(EPISODE_STEPS):
            obs=env.get_observations()
            with torch.no_grad():action=policy(obs)
            _,failed,timeout,tilt,z=env._advance(0,action.detach().to('cpu').numpy()[0])
            max_tilt=max(max_tilt,tilt)
            min_z=min(min_z,z)
            if failed or timeout:break
        records.append({'episode':episode,'survived_s':round((step+1)*.02,3),
                        'completed_4s':not failed and timeout,
                        'maximum_tilt_deg':round(math.degrees(max_tilt),2),
                        'minimum_root_height_m':round(min_z,4)})
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=2)
    parser.add_argument('--envs',type=int,default=2)
    parser.add_argument('--horizon',type=int,default=16)
    parser.add_argument('--device',default='cpu')
    parser.add_argument('--seed',type=int,default=20260928)
    parser.add_argument('--eval-episodes',type=int,default=4)
    args=parser.parse_args()
    if min(args.iterations,args.envs,args.horizon,args.eval_episodes)<1:
        raise ValueError('Invalid finite PPO budget')
    args.output.mkdir(parents=True,exist_ok=False)
    frozen_model=args.output/'trial.xml'
    shutil.copyfile(args.model,frozen_model)
    torch.manual_seed(args.seed);np.random.seed(args.seed)
    torch.set_num_threads(2)
    env=StanceTrialEnv(frozen_model,args.envs,args.seed,args.device)
    cfg=runner_config(args.horizon,.14)
    (args.output/'runner_config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    runner=OnPolicyRunner(env,cfg,log_dir=None,device=args.device)
    start=time.monotonic()
    runner.learn(num_learning_iterations=args.iterations,init_at_random_ep_len=False)
    elapsed=time.monotonic()-start
    checkpoint=args.output/'checkpoint.pt'
    runner.save(str(checkpoint),infos={'model_sha256':source_hash(frozen_model),
                                      'status':'experimental_unvalidated_stance_trial',
                                      'seed':args.seed})
    actor=runner.alg.actor.eval()
    learned=evaluate(frozen_model,actor,args.seed+1000,args.eval_episodes,args.device)
    class ZeroActor:
        def __call__(self,x):return torch.zeros((x.batch_size[0],ACTION_SIZE),device=device)
    device=args.device
    zero=evaluate(frozen_model,ZeroActor(),args.seed+1000,args.eval_episodes,args.device)
    result={'status':'experimental_ppo_stance_diagnostic_not_walking_acceptance',
            'model_sha256':source_hash(frozen_model),
            'source_script_sha256':source_hash(Path(__file__)),
            'algorithm':'RSL PPO','device':args.device,'seed':args.seed,
            'iterations':args.iterations,'envs':args.envs,'horizon':args.horizon,
            'environment_steps':args.iterations*args.envs*args.horizon,
            'elapsed_s':round(elapsed,2),
            'training_failures':env.failure_count,
            'training_mean_reward':round(env.reward_sum/max(env.reward_count,1),4),
            'observation_size':OBS_SIZE,'action_size':ACTION_SIZE,
            'actor_inputs':'body gyro, projected gravity, joint positions/velocities, previous leg action; no true root position',
            'learned_eval':learned,'zero_action_eval':zero,
            'limitations':['The trial model uses estimated print mass and unverified motor/collision packaging.',
                           'The actor is trained only for standing, never walking, picking or dragging.',
                           'A learned simulation result cannot certify physical hardware or cross-engine transfer.']}
    (args.output/'metadata.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
