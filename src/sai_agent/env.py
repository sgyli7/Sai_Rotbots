"""GPU command-conditioned locomotion environment.

Flat terrain is the first curriculum stage. Height samples are explicit simulation
terrain observations, not a claim that an RGB camera already produces a height map.
"""
import math
from pathlib import Path
import torch
from tensordict import TensorDict

from .gpu_backend import WarpBackend
from .control import CONTROL_DT, CROUCH_DROP, STAND_HEIGHT, LEG_INDICES, SIDES, FRONTS, SCAN_XY


def rotate_inverse(quat, vector):
    xyz = quat[:, 1:]
    t = 2 * torch.cross(xyz, vector, dim=-1)
    return vector - quat[:, :1]*t + torch.cross(xyz, t, dim=-1)


class LocomotionEnv:
    def __init__(self, model_path: Path, worlds=64, seed=47, random_commands=True):
        torch.manual_seed(seed)
        self.backend = WarpBackend(model_path, worlds)
        self.device = self.backend.device
        self.num_envs, self.num_actions = worlds, 16
        self.cfg = {}
        self.dt = CONTROL_DT
        self.gait_period = 2.4
        self.max_episode_length = 600
        self.episode_length_buf = torch.zeros(worlds, dtype=torch.long, device=self.device)
        self.command = torch.zeros((worlds, 3), device=self.device)
        self.crouch = torch.zeros(worlds, device=self.device)
        self.previous = torch.zeros((worlds, 16), device=self.device)
        self.random_commands = random_commands
        self.sides = torch.tensor(SIDES, dtype=torch.float32, device=self.device)
        self.fronts = torch.tensor(FRONTS, dtype=torch.float32, device=self.device)
        self.leg_indices = torch.tensor(LEG_INDICES, device=self.device)
        self.scan_xy = torch.tensor(SCAN_XY, dtype=torch.float32, device=self.device)
        self.up = torch.zeros((worlds, 3), device=self.device)
        self.up[:, 2] = 1
        self.reset(torch.ones(worlds, dtype=torch.bool, device=self.device))

    def sample_commands(self, mask):
        # Include exact stop, reverse, turn-in-place and height transitions.
        n = self.num_envs
        samples = torch.rand((n, 3), device=self.device)
        commands = torch.stack([(samples[:, 0]*2-1)*.20,
                                (samples[:, 1]*2-1)*.60,
                                (samples[:, 2] > .5).float()], dim=-1)
        bucket = torch.randint(0, 6, (n,), device=self.device)
        commands[:, 0] = torch.where(bucket <= 1, 0., commands[:, 0])
        commands[:, 1] = torch.where((bucket == 0) | (bucket == 2), 0., commands[:, 1])
        self.command[mask] = commands[mask]

    def reset(self, mask):
        self.backend.reset(mask)
        self.episode_length_buf[mask] = 0
        self.previous[mask] = 0
        self.crouch[mask] = 0
        if self.random_commands:
            self.sample_commands(mask)

    def terrain_heights(self):
        return torch.zeros((self.num_envs, 24), device=self.device)

    def ground_reference(self):
        return torch.zeros(self.num_envs, device=self.device)

    def task_failures(self):
        return torch.zeros(self.num_envs,dtype=torch.bool,device=self.device)

    def task_metrics(self):
        return {}

    def task_reward(self, height_error):
        return torch.zeros(self.num_envs,device=self.device)

    def state(self):
        q, v = self.backend.q, self.backend.v
        up = rotate_inverse(q[:, 3:7], self.up)
        lin = rotate_inverse(q[:, 3:7], v[:, :3])
        return up, lin, v[:, 3:6]

    def get_observations(self):
        q, v = self.backend.q, self.backend.v
        up, lin, ang = self.state()
        phase = self.episode_length_buf * self.dt * (2*math.pi/self.gait_period)
        scan = torch.clamp((self.terrain_heights()-(q[:, 2:3]-STAND_HEIGHT))*5, -2., 2.)
        obs = torch.cat([up, lin, ang, self.command[:, :2], self.crouch[:, None],
            q[:, 7:][:, self.leg_indices], v[:, 6:][:, self.leg_indices]*.1,
            v[:, 9::4]*self.sides*.1, self.previous,
            torch.sin(phase)[:, None], torch.cos(phase)[:, None], scan], dim=-1)
        return TensorDict({'policy': obs}, batch_size=[self.num_envs])

    def targets(self, action):
        down = .172812737 - CROUCH_DROP*self.crouch[:, None]
        beta = -self.fronts*torch.acos(torch.clamp((down**2-.09**2-.11**2)/(2*.09*.11), -1., 1.))
        theta = -torch.atan2(.11*torch.sin(beta), .09+.11*torch.cos(beta))
        theta0 = self.fronts*math.atan2(.05, .074833147)
        beta0 = -self.fronts*(math.atan2(.05, .09797959)+math.atan2(.05, .074833147))
        target = .18*action.clone()
        target[:, 1::4] += self.sides*(theta0-theta)
        target[:, 2::4] += self.sides*(beta0-beta)
        target[:, 3::4] = self.sides*((self.command[:, :1]-self.command[:, 1:2]*self.sides*.146)/.048
                                     +6*action[:, 3::4])
        return target

    def step(self, actions):
        actions = actions.clamp(-1., 1.)
        actions = actions*(torch.linalg.vector_norm(self.command[:,:2],dim=-1)>1e-5)[:,None]
        self.crouch += torch.clamp(self.command[:, 2]-self.crouch, -self.dt*2, self.dt*2)
        self.backend.step(self.targets(actions))
        self.episode_length_buf += 1
        up, lin, ang = self.state()
        ground = self.ground_reference()
        height_error = self.backend.q[:, 2] - (ground+STAND_HEIGHT-CROUCH_DROP*self.crouch)
        dv, dw = lin[:, 0]-self.command[:, 0], ang[:, 2]-self.command[:, 1]
        reward = (1.5*torch.exp(-(dv.square()+4*lin[:,1].square())/.015) + 1.*torch.exp(-dw.square()/.09)
            +.5-2.*height_error.square()/.0004 + .3*up[:, 2]
            -.1*lin[:, 1].square()-.08*ang[:, :2].square().sum(-1)
            -.15*actions.square().mean(-1)-.10*(actions-self.previous).square().mean(-1)
            -.002*(self.backend.ctrl*self.backend.v[:, 6:]).abs().sum(-1))
        reward += self.task_reward(height_error)
        fallen = (up[:, 2] < .6) | (self.backend.q[:, 2] < ground+.10)
        failed = fallen | self.task_failures()
        timeouts = self.episode_length_buf >= self.max_episode_length
        done = failed | timeouts
        reward -= failed.float()*8
        self.previous.copy_(actions)
        # Keep terminal/reset observations out of reported tracking diagnostics.
        extras = {'time_outs': timeouts, 'log': {
            'velocity_mae': dv.abs().mean(), 'yaw_mae': dw.abs().mean(),
            'lateral_mae': lin[:,1].abs().mean(),
            'height_mae': height_error.abs().mean(), 'falls': fallen.sum(),
            'task_failures':failed.sum(), 'upright': up[:, 2].mean(), **self.task_metrics()}}
        self.reset(done)
        if self.random_commands:
            self.sample_commands((self.episode_length_buf % 150 == 0) & ~done)
        return self.get_observations(), reward, done, extras
