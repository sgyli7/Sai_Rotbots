"""Differential control and physics check through a held-crouch transition."""
import json
import math
from pathlib import Path
import sys
import mujoco
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sai_agent.env import LocomotionEnv
from sai_agent.control import observation_numpy, targets_numpy, torque_numpy

env=LocomotionEnv(ROOT/'models/locomotion.xml',64,random_commands=False)
cpu=mujoco.MjData(env.backend.cpu_model)
mujoco.mj_forward(env.backend.cpu_model,cpu)
action=torch.zeros((64,16),device='cuda')
previous=np.zeros(16)
errors={'target':0.,'observation':0.,'height':0.}
samples=[]
for k in range(450):
    env.command[:,2]=float(100<=k<300)
    # Compare the same pre-step sensor state, independent of simulator drift.
    q=env.backend.q[0].cpu().numpy().copy();v=env.backend.v[0].cpu().numpy().copy()
    crouch=float(env.crouch[0])
    expected=observation_numpy(q,v,[0,0],crouch,previous,k*.02*2*math.pi/2.4,np.zeros(24))
    got=env.get_observations()['policy'][0].cpu().numpy()
    errors['observation']=max(errors['observation'],float(abs(expected-got).max()))
    env.step(action)
    crouch=float(env.crouch[0])
    cpu_target=targets_numpy(previous,[0,0],crouch)
    gpu_target=env.backend.target[0].cpu().numpy()
    errors['target']=max(errors['target'],float(abs(cpu_target-gpu_target).max()))
    for _ in range(10):
        cpu.ctrl[:]=torque_numpy(cpu.qpos,cpu.qvel,cpu_target)
        mujoco.mj_step(env.backend.cpu_model,cpu)
    z=float(env.backend.q[0,2])
    errors['height']=max(errors['height'],float(abs(z-cpu.qpos[2])))
    if k in [90,150,290,400]:
        samples.append({'step':k,'crouch':crouch,'gpu_z':z,'cpu_z':float(cpu.qpos[2]),
                        'target_hip_knee':gpu_target[1:3].tolist()})
result={'errors':errors,'samples':samples,
        'passed':errors['target']<1e-5 and errors['observation']<1e-4 and errors['height']<.003}
(ROOT/'artifacts/backend-parity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert result['passed'],result
