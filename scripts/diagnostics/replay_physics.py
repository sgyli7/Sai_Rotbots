"""Replay captured finite state/targets through actual GPU physics, with no policy."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import torch
import warp as wp
import mujoco
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from sai_agent.gpu_backend import WarpBackend
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--worlds',type=int,default=64);p.add_argument('--repeats',type=int,default=5);p.add_argument('--zero-warmstart',action='store_true');p.add_argument('--iterations',type=int);p.add_argument('--timestep',type=float);a=p.parse_args()
x=np.load(a.trial/'nonfinite-replay.npz')
source=a.trial/'stairs.xml'
if a.iterations or a.timestep:
 import xml.etree.ElementTree as ET
 root=ET.parse(source);option=root.getroot().find('option')
 if a.iterations:option.set('iterations',str(a.iterations))
 if a.timestep:option.set('timestep',str(a.timestep))
 source=a.trial/f'replay-{a.iterations}-{a.timestep}.xml';root.write(source,encoding='unicode')
b=WarpBackend(source,a.worlds,clear_warmstart=a.zero_warmstart);failed=0;rows=[]
for i in range(a.repeats):
 b.reset()
 b.q[:]=torch.as_tensor(x['q'][0],device=b.device)
 b.v[:]=torch.as_tensor(x['v'][0],device=b.device)
 wp.to_torch(b.data.mocap_pos)[:]=torch.as_tensor(x['mocap'][0],device=b.device)
 if not a.zero_warmstart:wp.to_torch(b.data.qacc_warmstart)[:]=torch.as_tensor(x['warmstart'][0],device=b.device)
 b.step(torch.as_tensor(x['target'][0],device=b.device).expand(a.worlds,-1));b.sync()
 q=b.q.cpu().numpy();v=b.v.cpu().numpy();n=int((~np.isfinite(q).all(1)|~np.isfinite(v).all(1)).sum());failed+=n
 rows.append(dict(repeat=i,nonfinite_worlds=n,max_abs_velocity=float(np.nanmax(abs(v)))))
print('REPLAY_RESULT',json.dumps(dict(worlds=a.worlds,repeats=a.repeats,nonfinite_worlds=failed,rows=rows)))
if failed:raise SystemExit(1)
