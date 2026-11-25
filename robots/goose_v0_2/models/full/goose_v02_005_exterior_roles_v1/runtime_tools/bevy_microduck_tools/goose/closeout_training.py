"""Explicit source007 training entry; smoke mode never updates an optimizer."""
import argparse
import copy
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
import torch
from .artifacts import sha256
from .closeout_reference import load_reference,evaluate_reference
from .closeout_drive import gravity_estimator_readback
from .mjlab_env import GooseDevelopmentEnv
from .source_training import make_standing_cfg,make_runner_cfg,GooseRslEnv
from .foot_curriculum import add_foot_sensors
from .closeout_checkpoint import checkpoint_identity,write_binding,validate_resume,parameter_digest

PROTOCOL_SHA='71462e444b1b4d753922defb0317869ed54a10fdae7eb9c68f7805234cbb72ee'
REFERENCE_SHA='2d0a05b9667b9642f5087bdf3cd6c206101cb0fe358cadbbe5f88dd2f0ba4c20'


def reference_inputs(bundle):
    return {'reference_action':bundle/'reference_inputs/reference_action.json',
            'reference_action_sha256':REFERENCE_SHA,
            'validation_protocol':bundle/'reference_inputs/validation_protocol.json',
            'validation_protocol_sha256':PROTOCOL_SHA}


def selected_execution_mode(bundle,requested=None,*,training=False):
    contract=json.loads((bundle/'contract.json').read_text());qualified='captured'
    adoption=contract['closeout_native50'].get('production_adoption')
    from .closeout_native50 import CONTACT_LITE_CANDIDATE
    if contract['candidate'] == CONTACT_LITE_CANDIDATE:
        qualified = 'uncaptured'
    if adoption is not None:
        from .closeout_native50 import _source
        approval=json.loads(_source(adoption,'execution-mode Owner adoption',bundle).read_text())
        qualified=approval.get('runtime_backend',{}).get('execution_mode','captured')
    selected=requested or qualified
    if selected not in ('captured','uncaptured'):raise ValueError('Unsupported execution mode')
    if training and selected!=qualified:raise ValueError('Requested execution mode is not Owner-adopted for training')
    return selected


def make_training_environment(bundle, *, num_envs=2, device='cuda:0', use_reference=False, execution_mode=None):
    """Real SaiLab reward/termination/RSL environment; policy action stays18."""
    selected=selected_execution_mode(bundle,execution_mode)
    from .closeout_native50 import CONTACT_LITE_CANDIDATE
    if use_reference and json.loads((bundle / 'contract.json').read_text())['candidate'] == CONTACT_LITE_CANDIDATE:
        raise ValueError('Frozen reference is parent007-bound. Use the included A/B regression protocol.')
    inputs=reference_inputs(bundle) if use_reference else None
    cfg=make_standing_cfg(bundle/'robot.xml',bundle/'contract.json',num_envs=num_envs,
                          episode_length_s=8.,seed=41,reference_inputs=inputs)
    add_foot_sensors(cfg,bundle/'contract.json')
    env=GooseDevelopmentEnv(cfg,device)
    if selected=='captured' and not env.sim.use_cuda_graph:
        env.close();raise RuntimeError('Owner-selected CUDA capture is unavailable')
    env.sim.use_cuda_graph=(selected=='captured')
    env._closeout_execution_mode=selected
    return env,GooseRslEnv(env),cfg



def make_closeout_runner_cfg():
    """Bridge unused mjlab model options to the installed RSL MLP signature."""
    cfg=make_runner_cfg(seed=41)
    cfg['num_steps_per_env']=32
    cfg['save_interval']=1
    for name in ('actor','critic'):
        if cfg[name]['class_name']!='MLPModel':raise ValueError('Closeout entry requires explicit MLP model')
        for key,default in (('cnn_cfg',None),('rnn_type',None),('rnn_hidden_dim',256),('rnn_num_layers',1)):
            if key in cfg[name]:
                if cfg[name][key]!=default:raise ValueError('Cannot discard an active non-MLP option: '+key)
                del cfg[name][key]
    return cfg

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--mode',choices=('smoke','train'),default='smoke')
    parser.add_argument('--num-envs',type=int,default=2)
    parser.add_argument('--steps',type=int,default=32)
    parser.add_argument('--iterations',type=int)
    parser.add_argument('--use-reference',action='store_true',help='Explicit external reference input for smoke rollout only')
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--segment-seconds',type=float)
    parser.add_argument('--execution-mode',choices=('captured','uncaptured'))
    args=parser.parse_args()
    if args.mode!='train' and (args.resume is not None or args.segment_seconds is not None):
        parser.error('Resume and graceful segmentation are train-only')
    if args.mode=='train' and args.segment_seconds is None:args.segment_seconds=120.
    if args.segment_seconds is not None and not 0<args.segment_seconds<=570:
        parser.error('Segment duration must be0..570seconds with resource-guard margin')
    if args.mode=='train' and (args.use_reference or not args.iterations or args.iterations<1):
        parser.error('Training needs --iterations and uses the policy public18-action output directly')
    contract=json.loads((args.bundle/'contract.json').read_text())
    from .closeout_native50 import CONTACT_LITE_CANDIDATE
    allowed = (2, 32) if contract['candidate']==CONTACT_LITE_CANDIDATE else (2,)
    if args.num_envs not in allowed:parser.error(f'Qualified world counts are {allowed}')
    if not 1<=args.steps<=100:parser.error('Bounded rollout must be1..100ticks')
    if args.mode=='train':
        from .closeout_native50 import TRAINING_CANDIDATES
        if contract.get('candidate') not in TRAINING_CANDIDATES or contract.get('training_ready')is not True:
            parser.error('Policy training requires an independently qualified bundle')
        if args.steps!=32:parser.error('The validated training horizon is32ticks')
        if 'goose_closeout.slice'not in Path('/proc/self/cgroup').read_text():
            parser.error('Training must use the supplied resource-guarded launcher')
    if args.output.exists():raise FileExistsError('Preserve the previous run')
    args.output.mkdir(parents=True)
    from .upstream_discrete_mjlab import VERSIONS
    versions={name:importlib.metadata.version(name) for name in (*VERSIONS,'torch','numpy','scipy','gymnasium','tensordict')}
    if any(versions[name]!=version for name,version in VERSIONS.items()):
        raise RuntimeError('Wrong engine overlay; use the supplied pinned local launcher')
    receipt={'schema':'goose_source007_training_entry_probe_v1','mode':args.mode,
        'python_executable':sys.executable,'versions':versions,'num_envs':args.num_envs,
        'model_sha256':sha256(args.bundle/'robot.xml'),'contract_sha256':sha256(args.bundle/'contract.json'),
        'PPO_updates':0,'optimizer_steps':0,'actual_world_integrations':0,'failure':None,
        'explicit_external_reference':args.use_reference,'policy_action_semantics_changed':False,
        'scope':'training_environment_and_bounded_rollout_only','source_module_sha256':sha256(Path(__file__))}
    execution_mode=selected_execution_mode(args.bundle,args.execution_mode,training=args.mode=='train')
    receipt['execution_mode']=execution_mode
    env=wrapped=None;rows=[];started=time.monotonic()
    try:
        env,wrapped,cfg=make_training_environment(args.bundle,num_envs=args.num_envs,use_reference=args.use_reference,execution_mode=execution_mode)
        obs,_=wrapped.reset()
        if obs['actor'].shape!=(args.num_envs,65) or wrapped.num_actions!=18:
            raise ValueError('Training observation/action contract changed')
        from rsl_rl.runners import OnPolicyRunner
        runner_cfg=make_closeout_runner_cfg()
        runner=OnPolicyRunner(wrapped,copy.deepcopy(runner_cfg),log_dir=str(args.output/'runner'),device='cuda:0')
        receipt.update(runner_initialized=True,observation_shape=list(obs['actor'].shape),action_size=wrapped.num_actions,
            reward_terms=list(cfg.rewards),termination_terms=list(cfg.terminations),
            algorithm_class=runner.alg.__class__.__name__,initial_learning_iteration=runner.current_learning_iteration)
        (args.output/'training_config.json').write_text(json.dumps(runner_cfg,indent=2)+'\n')
        if args.mode=='train':
            identity=checkpoint_identity(args.bundle,runner_cfg,execution_mode,num_envs=args.num_envs)
            parameters=list(runner.alg.actor.parameters())+list(runner.alg.critic.parameters())
            if args.resume is not None:
                binding=validate_resume(args.resume,identity)
                runner.load(str(args.resume.resolve()),strict=True,map_location='cuda:0')
                if runner.current_learning_iteration!=binding['last_completed_iteration_index']:
                    raise ValueError('RSL loaded iteration differs from bound checkpoint')
                if parameter_digest(parameters)!=binding.get('policy_parameters_sha256'):
                    raise ValueError('Actually loaded policy parameters differ from checkpoint binding')
                runner.current_learning_iteration=binding['next_iteration_index']
                receipt['resumed_checkpoint']={'path':str(args.resume.resolve()),'sha256':sha256(args.resume)}
                receipt['resume_next_iteration_index']=runner.current_learning_iteration
            receipt['initial_parameters_sha256']=parameter_digest(parameters)
            receipt['starting_iteration_index']=runner.current_learning_iteration
            receipt['requested_outer_iterations']=args.iterations
            receipt['segment_seconds']=args.segment_seconds
            receipt['losses_by_iteration']=[]
            original_step=wrapped.step
            if contract['candidate']==CONTACT_LITE_CANDIDATE:
                capacity=receipt['contact_capacity']={
                    'active_contacts_all_worlds_limit':int(env.sim.wp_data.naconmax),
                    'constraint_rows_per_world_limit':int(env.sim.wp_data.njmax),
                    'peak_active_contacts_all_worlds':0,
                    'peak_constraint_rows_per_world':0,
                    'steps_checked':0,
                }

                def check_contacts():
                    data=env.sim.data
                    contacts=int(data.nacon[0])
                    constraints=int(data.nefc.max())
                    capacity['peak_active_contacts_all_worlds']=max(capacity['peak_active_contacts_all_worlds'],contacts)
                    capacity['peak_constraint_rows_per_world']=max(capacity['peak_constraint_rows_per_world'],constraints)
                    capacity['steps_checked']+=1
                    if (contacts>capacity['active_contacts_all_worlds_limit']
                            or constraints>capacity['constraint_rows_per_world_limit']
                            or bool(data.overflow.any())):
                        raise RuntimeError(f'GPU contact capacity exceeded: {contacts} contacts, {constraints} rows')

                # The wrapper calls this before the reset mutates terminal worlds.
                wrapped.on_terminal=lambda *_: check_contacts()

            def recorded_policy_step(action):
                sampled=action.detach().clone()
                obs,reward,done,extras=original_step(action)
                if contract['candidate']==CONTACT_LITE_CANDIDATE and not bool(done.any()):
                    check_contacts()
                term=env.action_manager.get_term('goose')
                rows.append({'tick':len(rows)+1,'actor_sampled_action':sampled.cpu().tolist(),
                    'actual_drive_action':term.drive.actions.cpu().tolist(),'reward':reward.cpu().tolist(),
                    'done':done.cpu().tolist(),'time_s':env.sim.data.time.cpu().tolist()})
                receipt['actual_world_integrations']=wrapped.real_integrations
                return obs,reward,done,extras
            wrapped.step=recorded_policy_step
            def check_gradients(optimizer,arguments,keywords):
                gradients=[p.grad for p in parameters if p.grad is not None]
                if not gradients or not all(bool(torch.isfinite(value).all())for value in gradients):
                    raise FloatingPointError('Nonfinite or missing training gradient')
            def count_optimizer_step(optimizer,arguments,keywords):
                if not all(bool(torch.isfinite(value).all())for value in parameters):
                    raise FloatingPointError('Nonfinite training parameter')
                receipt['optimizer_steps']+=1
            pre_hook=runner.alg.optimizer.register_step_pre_hook(check_gradients)
            post_hook=runner.alg.optimizer.register_step_post_hook(count_optimizer_step)
            original_update=runner.alg.update
            def count_iteration():
                losses=original_update()
                if not all(np.isfinite(float(value))for value in losses.values()):
                    raise FloatingPointError('Nonfinite policy learning loss')
                receipt['PPO_updates']+=1
                receipt['losses_by_iteration'].append({k:float(v)for k,v in losses.items()})
                return losses
            runner.alg.update=count_iteration
            original_save=runner.save
            checkpoints={}
            class SegmentFinished(Exception):pass
            def bound_save(path,infos=None):
                target=Path(path);temporary=target.with_suffix(target.suffix+'.tmp')
                original_save(str(temporary),infos)
                temporary.replace(target)
                record=write_binding(target,identity,runner.current_learning_iteration,runner_cfg,parameter_digest(parameters))
                checkpoints[str(target)]=record
                receipt['last_checkpoint']=record
                if time.monotonic()-started>=args.segment_seconds:raise SegmentFinished()
            runner.save=bound_save
            try:
                runner.learn(num_learning_iterations=args.iterations,init_at_random_ep_len=False)
                receipt['segment_end_reason']='requested_iterations_completed'
            except SegmentFinished:
                runner.logger.stop_logging_writer()
                receipt['segment_end_reason']='graceful_saved_iteration_boundary'
            finally:
                pre_hook.remove();post_hook.remove()
            receipt['checkpoints']=list(checkpoints.values())
            receipt['actual_world_integrations']=wrapped.real_integrations
            receipt['final_learning_iteration_index']=runner.current_learning_iteration
            receipt['next_learning_iteration_index']=runner.current_learning_iteration+1
            receipt['final_parameters_sha256']=parameter_digest(parameters)
            receipt['parameters_changed']=receipt['initial_parameters_sha256']!=receipt['final_parameters_sha256']
            receipt['terminal_episodes']=wrapped.terminal_episodes
            if receipt['PPO_updates']<1 or not checkpoints:raise RuntimeError('No actual saved learning iteration completed')
        else:
            loaded=load_reference(args.bundle/'robot.xml',args.bundle/'contract.json',reference_inputs(args.bundle)) if args.use_reference else None
            if loaded is not None:receipt['external_reference']=loaded['identity']
            for tick in range(args.steps):
                term=env.action_manager.get_term('goose')
                before=env.sim.data.time.clone()
                if loaded is not None:
                    q=env.sim.data.qpos.cpu().numpy();v=env.sim.data.qvel.cpu().numpy()
                    actions=np.array([evaluate_reference(loaded,q[i],v[i])[0] for i in range(args.num_envs)])
                    action=torch.as_tensor(actions,dtype=torch.float64,device='cuda:0')
                else:action=torch.zeros((args.num_envs,18),device='cuda:0')
                obs,reward,done,extras=wrapped.step(action)
                receipt['actual_world_integrations']=wrapped.real_integrations
                if not bool(torch.isfinite(obs['actor']).all()) or not bool(torch.isfinite(reward).all()):
                    raise FloatingPointError('Training rollout nonfinite observation/reward')
                rows.append({'tick':tick+1,'time_s':env.sim.data.time.cpu().tolist(),'action':action.cpu().tolist(),
                    'actual_drive_action':term.drive.actions.cpu().tolist(),'gravity_estimator':gravity_estimator_readback(term.drive.gravity),'reward':reward.cpu().tolist(),
                    'done':done.cpu().tolist(),'qpos':env.sim.data.qpos.cpu().tolist(),'qvel':env.sim.data.qvel.cpu().tolist(),
                    'actual_motor_force_Nm':term._solver_force.cpu().tolist(),'thermal':term.drive.thermal.cpu().tolist()})
            receipt.update(bounded_rollout_ticks=args.steps,terminal_episodes=wrapped.terminal_episodes,
                final_learning_iteration=runner.current_learning_iteration,runner_optimizer_state_entries=len(runner.alg.optimizer.state))
            if runner.current_learning_iteration!=0 or runner.alg.optimizer.state:
                raise RuntimeError('Smoke mode unexpectedly updated an optimizer')
    except BaseException:receipt['failure']=traceback.format_exc()
    finally:
        if env is not None:env.close()
        receipt['elapsed_s']=time.monotonic()-started
        receipt['passed']=receipt['failure'] is None
        (args.output/'trace.json').write_text(json.dumps(rows,indent=2)+'\n')
        (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('STATUS '+json.dumps(receipt),flush=True)
    if receipt['failure']:raise RuntimeError(receipt['failure'])

if __name__=='__main__':main()
