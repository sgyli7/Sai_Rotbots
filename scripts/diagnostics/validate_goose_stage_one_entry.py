"""Validate the final model's RSL/CUDA boundary without any optimizer updates."""
from pathlib import Path
import json,hashlib,argparse,platform
import numpy as np
import torch
from rsl_rl.runners import OnPolicyRunner
from sai_agent.goose.stage_one import StageOneEnv,rsl_environment
from sai_agent.goose.rsl import runner_config
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--device',default='cpu');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=ROOT/'robots/Goose_V0.1';torch.set_num_threads(2);torch.manual_seed(931)
 base=StageOneEnv(r/'models/stage_one/robot.xml',r/'configs/stage_one_contract.json',4,seed=931);env=rsl_environment(base);runner=OnPolicyRunner(env,runner_config(16,.045),log_dir=None,device=a.device)
 obs=env.get_observations().to(a.device)
 with torch.no_grad():action=runner.alg.actor(obs)
 assert action.shape==(4,18) and torch.isfinite(action).all();obs,reward,done,info=env.step(action)
 assert obs['policy'].shape==(4,65) and torch.isfinite(obs['policy']).all() and torch.isfinite(reward).all()
 files=[ROOT/'src/sai_agent/goose/stage_one.py',ROOT/'src/sai_agent/goose/stage_one_gravity.py',ROOT/'scripts/training/train_goose_stage_one.py']
 out=dict(status='FINAL_MODEL_TRAINER_ENTRY_PASS_NO_OPTIMIZER_UPDATES',optimizer_updates=0,model_sha256=base.source_hash,contract_sha256=hashlib.sha256((r/'configs/stage_one_contract.json').read_bytes()).hexdigest(),source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},observation_shape=[4,65],action_shape=[4,18],device=a.device,gpu=torch.cuda.get_device_name(0) if a.device.startswith('cuda') else None,torch=torch.__version__,platform=platform.platform(),finite=True)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
