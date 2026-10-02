"""Explicit entry for the frozen18-axis experimental training checkpoint."""
from pathlib import Path
import argparse,copy,hashlib,json,shutil,time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--iterations',type=int,default=100);ap.add_argument('--envs',type=int,default=2);ap.add_argument('--horizon',type=int,default=32);ap.add_argument('--device',default='cpu');ap.add_argument('--seed',type=int,default=29);ap.add_argument('--commands',action='store_true');ap.add_argument('--randomize',action='store_true');a=ap.parse_args()
    if min(a.iterations,a.envs,a.horizon)<1 or a.envs*a.horizon<4:raise ValueError('positive budget and at least4 rollout samples required')
    cp=R/'configs/training_checkpoint_contract.json';c=json.loads(cp.read_text());entry=json.loads((R/'evidence/training_checkpoint_entry.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if entry['model_sha256']!=c['model_sha256'] or entry['contract_sha256']!=sha(cp):raise ValueError('stale checkpoint smoke')
    if not entry['stance_smoke_pass']:raise ValueError('checkpoint has not passed nominal stance smoke; resolve collision/dynamics before PPO')
    import torch
    from rsl_rl.runners import OnPolicyRunner
    from sai_agent.goose.stage_one import StageOneEnv,rsl_environment
    from sai_agent.goose.rsl import runner_config
    a.output.mkdir(parents=True,exist_ok=False);inputs=a.output/'inputs';inputs.mkdir()
    for folder in ['training_checkpoint','training_reference']:shutil.copytree(R/'models'/folder,inputs/folder)
    shutil.copyfile(cp,inputs/'contract.json')
    torch.set_num_threads(2);torch.manual_seed(a.seed);np.random.seed(a.seed)
    base=StageOneEnv(inputs/'training_checkpoint/robot.xml',inputs/'contract.json',a.envs,a.seed,a.randomize,a.commands);env=rsl_environment(base);cfg=runner_config(a.horizon,.045);cfg['algorithm']['num_mini_batches']=min(4,a.envs*a.horizon)
    runner=OnPolicyRunner(env,copy.deepcopy(cfg),log_dir=None,device=a.device);head=runner.alg.actor.mlp[-1];torch.nn.init.zeros_(head.weight);torch.nn.init.zeros_(head.bias)
    start=time.monotonic();runner.learn(a.iterations,init_at_random_ep_len=False);runner.save(str(a.output/'checkpoint.pt'),infos=dict(contract=c,seed=a.seed,status='experimental_no_walking_acceptance'))
    result=dict(status='EXPERIMENTAL_POLICY_NOT_HARDWARE_RELEASE',model_sha256=c['model_sha256'],contract_sha256=sha(cp),iterations=a.iterations,environment_steps=env.steps,failures=env.failures,device=a.device,elapsed_s=time.monotonic()-start,runner_config=cfg)
    (a.output/'metadata.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
