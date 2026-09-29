"""Bounded PPO candidate training with model/contract snapshot and ONNX parity."""
from pathlib import Path
import argparse,json,time,copy,hashlib,shutil,platform
import numpy as np
import torch,onnx,onnxruntime as ort
from rsl_rl.runners import OnPolicyRunner
from sai_agent.goose.stage_one import StageOneEnv,rsl_environment
from sai_agent.goose.rsl import runner_config
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--iterations',type=int,default=100);p.add_argument('--envs',type=int,default=8);p.add_argument('--horizon',type=int,default=32);p.add_argument('--device',default='cpu');p.add_argument('--seed',type=int,default=29);p.add_argument('--standing',action='store_true');p.add_argument('--nominal',action='store_true');a=p.parse_args()
 if min(a.iterations,a.envs,a.horizon)<1:raise ValueError('positive budgets required')
 a.output.mkdir(parents=True,exist_ok=False);inputs=a.output/'inputs';shutil.copytree(ROOT/'robots/Goose_V0.1/models/stage_one',inputs/'model');shutil.copy2(ROOT/'robots/Goose_V0.1/configs/stage_one_contract.json',inputs/'contract.json')
 torch.set_num_threads(2);torch.manual_seed(a.seed);np.random.seed(a.seed)
 base=StageOneEnv(inputs/'model/robot.xml',inputs/'contract.json',a.envs,a.seed,not a.nominal,not a.standing);env=rsl_environment(base);cfg=runner_config(a.horizon,.045);cfg['algorithm']['num_learning_epochs']=3
 runner=OnPolicyRunner(env,copy.deepcopy(cfg),log_dir=None,device=a.device);head=runner.alg.actor.mlp[-1];torch.nn.init.zeros_(head.weight);torch.nn.init.zeros_(head.bias)
 start=time.monotonic();runner.learn(a.iterations,init_at_random_ep_len=False);runner.save(str(a.output/'checkpoint.pt'),infos={'contract':base.contract,'seed':a.seed,'status':'experimental'})
 actor=runner.alg.actor.cpu().eval().as_onnx(verbose=False).eval();policy=a.output/'policy.onnx'
 torch.onnx.export(actor,torch.zeros(1,65),policy,input_names=['observation'],output_names=['action'],dynamic_axes={'observation':{0:'batch'},'action':{0:'batch'}},opset_version=18,dynamo=False)
 onnx.checker.check_model(onnx.load(policy));session=ort.InferenceSession(str(policy),providers=['CPUExecutionProvider']);samples=np.r_[base.observations(),np.random.default_rng(a.seed).normal(0,.2,(128,65)).astype(np.float32)]
 with torch.no_grad():expected=actor(torch.from_numpy(samples)).numpy()
 actual=session.run(None,{'observation':samples})[0];error=float(abs(expected-actual).max());assert error<1e-5 and np.isfinite(actual).all()
 result=dict(status='PPO_CHAIN_VERIFIED_POLICY_NOT_WALKING_ACCEPTED',model_sha256=base.source_hash,contract_sha256=hashlib.sha256((inputs/'contract.json').read_bytes()).hexdigest(),policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),seed=a.seed,iterations=a.iterations,envs=a.envs,horizon=a.horizon,environment_steps=env.steps,failures=env.failures,device=a.device,gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,torch=torch.__version__,platform=platform.platform(),elapsed_s=time.monotonic()-start,onnx_parity_error=error,randomized=not a.nominal,commands=not a.standing,root_free=True,external_root_support=False,observation_size=65,action_size=18,runner_config=cfg)
 (a.output/'metadata.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
