"""Strict policy/optimizer checkpoint identity for the independent source007 entry."""
import hashlib
import importlib.util
import json
from pathlib import Path
from .artifacts import sha256


def config_digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def binding_path(checkpoint):
    return Path(checkpoint).with_suffix('.binding.json')


def checkpoint_identity(bundle,config,execution_mode,*,num_envs=2):
    bundle=Path(bundle);contract=json.loads((bundle/'contract.json').read_text())
    engine=importlib.util.find_spec('mujoco_warp._src.collision_primitive')
    if engine is None or engine.origin is None:raise ValueError('Missing selected GPU collision module')
    return {'candidate':contract['candidate'],'model_sha256':sha256(bundle/'robot.xml'),
        'contract_sha256':sha256(bundle/'contract.json'),'joint_order':contract['joint_order'],
        'action_size':contract['action_size'],'observation_size':contract['observation_sizes']['locomotion'],
        'physics_dt_s':contract['physics_dt_s'],'num_envs':num_envs,'horizon_ticks':config['num_steps_per_env'],
        'runner_config_sha256':config_digest(config),'execution_mode':execution_mode,
        'engine_collision_module_sha256':sha256(Path(engine.origin)),
        'runtime_files_sha256':{p.relative_to(bundle).as_posix():sha256(p)
            for p in sorted((bundle/'runtime_tools').rglob('*.py'))}}


def write_binding(checkpoint,identity,runner_iteration_index,config,parameters_sha256=None):
    checkpoint=Path(checkpoint)
    value={'schema':'goose_source007_policy_checkpoint_binding_v1',**identity,
        'checkpoint_sha256':sha256(checkpoint),'policy_parameters_sha256':parameters_sha256,'last_completed_iteration_index':int(runner_iteration_index),
        'next_iteration_index':int(runner_iteration_index)+1,'runner_config':config,
        'policy_action_is_direct_normalized18':True,'external_reference_added_to_policy':False}
    target=binding_path(checkpoint);temporary=target.with_suffix(target.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(target)
    return {'path':str(checkpoint),'sha256':value['checkpoint_sha256'],
            'binding_path':str(target),'binding_sha256':sha256(target),
            'last_iteration_index':int(runner_iteration_index),'next_iteration_index':int(runner_iteration_index)+1}


def validate_resume(checkpoint,identity):
    checkpoint=Path(checkpoint).resolve(strict=True);sidecar=binding_path(checkpoint)
    if not sidecar.is_file():raise ValueError('A source007 binding sidecar is required; legacy weights cannot resume')
    value=json.loads(sidecar.read_text())
    if (value.get('schema')!='goose_source007_policy_checkpoint_binding_v1'
        or value.get('checkpoint_sha256')!=sha256(checkpoint)
        or not isinstance(value.get('policy_parameters_sha256'),str)or len(value['policy_parameters_sha256'])!=64
        or any(value.get(key)!=expected for key,expected in identity.items())
        or config_digest(value.get('runner_config'))!=identity['runner_config_sha256']
        or value.get('policy_action_is_direct_normalized18')is not True
        or value.get('external_reference_added_to_policy')is not False
        or type(value.get('last_completed_iteration_index'))is not int
        or value['last_completed_iteration_index']<0
        or value.get('next_iteration_index')!=value['last_completed_iteration_index']+1):
        raise ValueError('Checkpoint does not match this source007 model/contract/runtime/engine/config; old policies cannot resume')
    return value


def parameter_digest(parameters):
    value=hashlib.sha256()
    for tensor in parameters:value.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return value.hexdigest()
