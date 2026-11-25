"""Bounded actual 20ms closeout integration probes, with no policy or optimizer.

Run only after the Owner supplies a same-version source/contact candidate and
assigns a resource slot. A finite probe is development evidence, not release.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import traceback

import mujoco
import numpy as np

from .artifacts import DT, sha256
from .closeout_drive import gravity_estimator_readback
from .closeout_precision import cpu_post_contacts,gpu_post_contacts,evaluate_comparison,load_acceptance


def run_cpu(model_path, contract_path, steps, rows, counters, *, reference_inputs=None, precision_acceptance=None):
    from .closeout_native50 import make_source_runtime, cold_birth_contact_check
    from .mjlab_baseline import make_entity_cfg
    # This is the real entity construction path, not a schema-only surrogate.
    reference = None
    if reference_inputs is not None:
        from .closeout_reference import load_reference,evaluate_reference
        reference=load_reference(model_path,contract_path,reference_inputs)
    entity = make_entity_cfg(model_path, contract_path, reference_inputs=reference_inputs)
    entity_model = entity.spec_fn().compile()
    if entity_model.nu != 18:
        raise ValueError('CPU entity does not retain 18 native motors')
    if reference is not None and entity.spec_fn.external_reference_readback != reference['identity']:
        raise RuntimeError('Actual make_entity reference readback mismatch')
    runtime = make_source_runtime(model_path, contract_path)
    m, d = runtime.model, runtime.data
    contact_probe=mujoco.MjData(m) if precision_acceptance is not None else None
    patches = runtime.contract['rigid_native']['foot_sensor_sites']
    sole_ids = [{m.geom(name).id for name in patch['geoms']} for patch in patches]
    ground = m.geom('ground').id
    contact_manifest = json.loads(Path(runtime.contract['closeout_native50']['source_refs']['contact']['path']).read_text())
    for case in ('standing', 'drop_50mm', 'reinitialize'):
        observation = runtime.reset()
        if observation.shape != (65,) or not np.isfinite(observation).all():
            raise ValueError('CPU cold observation invalid')
        if case == 'drop_50mm':
            d.qpos[2] += .05  # Explicit initial condition, before any integration.
            mujoco.mj_forward(m, d)
        if runtime.physics_integrations != 0 or float(d.time) != 0:
            raise RuntimeError('CPU reinitialization did not clear the declared clock')
        rows.append({'case':case,'initial':True,'qpos':d.qpos.tolist(),'qvel':d.qvel.tolist(),
                     'action':(reference['action'].tolist() if reference is not None else [0.]*18),'time_s':float(d.time)})
        if case in ('standing','reinitialize'):
            cold = cold_birth_contact_check(m,d,contact_manifest)
            rows[-1]['cold_birth_contacts'] = cold
            if not cold['passed']:
                raise RuntimeError('Cold birth self-contact rejected before any physical Tick')
        for tick in range(steps):
            action,controller_state = (evaluate_reference(reference,d.qpos,d.qvel)
                                       if reference is not None else (np.zeros(18),{}))
            before = float(d.time)
            step_start_qpos = d.qpos.copy()
            step_start_body_xpos,step_start_body_xmat = d.xpos.copy(),d.xmat.copy()
            started = time.perf_counter()
            try:
                observation, info = runtime.step(action)
            except BaseException:
                rows.append({'case':case, 'failed_tick':tick+1, 'time_s':float(d.time),
                    'qpos':d.qpos.tolist(), 'qvel':d.qvel.tolist(), 'qacc':d.qacc.tolist(),
                    'ctrl':d.ctrl.tolist(), 'actuator_force':d.actuator_force.tolist(),
                    'warnings':[int(w.number) for w in d.warning],
                    'pending_controller_preparation':runtime.drive._pending_action is not None})
                raise
            finally:
                counters['CPU_integrations'] += int(float(d.time) > before)
                step_elapsed = time.perf_counter()-started
            if (abs(float(d.time)-before-DT) > 1e-12
                    or runtime.drive.completed_ticks.item() != tick+1
                    or observation.shape != (65,) or not np.isfinite(observation).all()):
                rows.append({'case':case, 'failed_tick':tick+1, 'time_s':float(d.time),
                             'qpos':d.qpos.tolist(), 'qvel':d.qvel.tolist()})
                raise RuntimeError('CPU Tick/observation/history mismatch')
            forces = np.zeros((2, 3))
            found = np.zeros(2, dtype=int)
            self_contacts = []
            for index in range(d.ncon):
                contact = d.contact[index]
                pair = {int(contact.geom1), int(contact.geom2)}
                if ground not in pair:
                    a,b=int(contact.geom1),int(contact.geom2)
                    ba,bb=int(m.geom_bodyid[a]),int(m.geom_bodyid[b])
                    wrench=np.zeros(6);mujoco.mj_contactForce(m,d,index,wrench)
                    self_contacts.append({'geoms':[m.geom(a).name,m.geom(b).name],
                        'owners':[m.body(ba).name,m.body(bb).name],
                        'distance_m':float(contact.dist),'world_point_m':contact.pos.tolist(),
                        'contact_frame_world_axes':contact.frame.reshape(3,3).tolist(),
                        'actual_contact_frame_force_torque':wrench.tolist(),
                        'step_start_body_xpos':[step_start_body_xpos[ba].tolist(),step_start_body_xpos[bb].tolist()],
                        'step_start_body_xmat':[step_start_body_xmat[ba].reshape(3,3).tolist(),step_start_body_xmat[bb].reshape(3,3).tolist()]})
                    continue
                for side, ids in enumerate(sole_ids):
                    if pair & ids:
                        wrench = np.zeros(6)
                        mujoco.mj_contactForce(m, d, index, wrench)
                        forces[side] += contact.frame.reshape(3,3).T @ wrench[:3]
                        found[side] += 1
            rows.append({'case': case, 'tick': tick+1, 'time_s': float(d.time),
                'qpos': d.qpos.tolist(), 'qvel': d.qvel.tolist(), 'action':action.tolist(),'controller_state':controller_state,
                'gravity_estimator':gravity_estimator_readback(runtime.drive.gravity),
                'motor_force_nm': d.actuator_force.tolist(),
                'ctrl':d.ctrl.tolist(),'target':runtime.drive.target[0].tolist(),
                'thermal':runtime.drive.thermal[0].tolist(),'wall_s':step_elapsed,
                'step_start_qpos':step_start_qpos.tolist(),
                'actual_cached_self_contacts':self_contacts,
                **({'post_state_contacts':cpu_post_contacts(m,contact_probe,d.qpos)} if contact_probe is not None else {}),
                'contact_geometry_clock':'solver contacts from step-start state; qpos/upright/height below are post-integration',
                'sole_found': found.tolist(), 'sole_force_world_n': forces.tolist(),
                'closure_residual_m': float(np.max(np.abs(d.efc_pos[:3]))) if d.nefc else None,
                'height_m': info['height_m'], 'upright': info['upright'],
                'standing_failure': info['failure']})
            if info['failure']:
                raise RuntimeError('CPU bounded standing/drop posture failed; preserve actual state')
        if steps >= 25 and not bool(found.any()):
            raise RuntimeError('CPU bounded probe finished without a named sole contact')
        print('EVENT '+json.dumps({'case':case, 'ticks':steps, 'time_s':float(d.time)}), flush=True)
    return {'entity_compiled': True, 'declared_reinitialization_checked': True,
            'physics_dt_s':DT,'zero_action_standing':reference is None,
            'standing_with_bound_reference':reference is not None,
            'external_reference':reference['identity'] if reference is not None else None,
            'case_integrations':{key:steps for key in ('standing','drop_50mm','reinitialize')}}


def run_gpu(model_path, contract_path, steps, rows, counters, *, reference_inputs=None, cpu_replay=None, precision_acceptance=None):
    import torch
    from .closeout_native50 import make_source_runtime, cold_birth_contact_check
    from .mjlab_env import GooseDevelopmentEnv, make_development_env_cfg
    from .foot_curriculum import add_foot_sensors, CONTACT_SENSOR
    preflight=make_source_runtime(model_path,contract_path)
    manifest=json.loads(Path(preflight.contract['closeout_native50']['source_refs']['contact']['path']).read_text())
    cold=cold_birth_contact_check(preflight.model,preflight.data,manifest)
    rows.append({'case':'gpu_preflight_cold','initial':True,'cold_birth_contacts':cold})
    if not cold['passed']:
        raise RuntimeError('GPU cold birth self-contact rejected before upload/integration')
    reference=None
    if reference_inputs is not None:
        from .closeout_reference import load_reference,evaluate_reference
        reference=load_reference(model_path,contract_path,reference_inputs)
    replay=None
    if reference is not None and reference['identity']['reference_kind']=='ap_pitch_feedback_v1':
        if cpu_replay is None or sha256(Path(cpu_replay['path'])) != cpu_replay['sha256']:
            raise ValueError('Dynamic-reference GPU qualification requires exact CPU trace replay')
        trace=json.loads(Path(cpu_replay['path']).read_text())
        replay=np.array([row['action'] for row in trace if row.get('case')=='standing' and 'tick' in row])
        if replay.shape != (steps,18):
            raise ValueError('Incomplete CPU standing replay sequence')
    cfg = make_development_env_cfg(model_path, contract_path, num_envs=2,reference_inputs=reference_inputs)
    entity_spec_fn=cfg.scene.entities['robot'].spec_fn
    add_foot_sensors(cfg, contract_path)
    env = None
    try:
        env = GooseDevelopmentEnv(cfg, 'cuda:0')
        if reference is not None and entity_spec_fn.external_reference_readback != reference['identity']:
            raise RuntimeError('Actual GPU make_entity reference readback mismatch')
        observation, _ = env.reset()
        term = env.action_manager.get_term('goose')
        graph_available = bool(env.sim.use_cuda_graph)
        if not graph_available:
            raise RuntimeError('Requested GPU graph/noncaptured comparison is unavailable in this environment')
        passes = {}
        for captured in (False,True):
            env.sim.use_cuda_graph = captured
            observation, _ = env.reset()
            label = 'gpu_standing_graph' if captured else 'gpu_standing_uncaptured'
            samples = []
            rows.append({'case':label,'initial':True,'qpos':env.sim.data.qpos.cpu().tolist(),
                         'qvel':env.sim.data.qvel.cpu().tolist(),'action':(reference['action'].tolist() if reference is not None else [0.]*18)})
            for tick in range(steps):
                action = (torch.as_tensor(replay[tick] if replay is not None else reference['action'],
                          dtype=torch.float64,device='cuda:0').repeat(2,1)
                          if reference is not None else torch.zeros((2,18), device='cuda:0'))
                if replay is not None and not np.array_equal(action.cpu().numpy(),np.repeat(replay[tick][None,:],2,axis=0)):
                    raise ValueError('GPU replay input differs from the frozen CPU action')
                before = env.sim.data.time.clone()
                started = time.perf_counter()
                try:
                    observation, *_ = env.step(action)
                finally:
                    counters['GPU_integrations'] += int((env.sim.data.time > before).sum())
                if (observation['actor'].shape != (2,65)
                        or not bool(torch.isfinite(observation['actor']).all())
                        or term.drive.completed_ticks.tolist() != [tick+1,tick+1]
                        or bool(((env.sim.data.time-before-DT).abs() > 2e-6).any())
                        or int(env.sim.data.overflow.max()) != 0):
                    raise RuntimeError('GPU actual Tick/observation/capacity mismatch')
                feet = env.scene.sensors[CONTACT_SENSOR].data
                if feet.force.shape != (2,2,3) or feet.found.shape != (2,2):
                    raise RuntimeError('GPU sole leaves were not aggregated to two feet')
                sample = {'case':label, 'tick':tick+1,'wall_s':time.perf_counter()-started,
                    'time_s':env.sim.data.time.cpu().tolist(), 'action':action.cpu().tolist(),
                    'actual_drive_action':term.drive.actions.cpu().tolist(),
                    'gravity_estimator':gravity_estimator_readback(term.drive.gravity),
                    **({'post_state_contacts':gpu_post_contacts(env)}if precision_acceptance is not None else {}),
                    'qpos':env.sim.data.qpos.cpu().tolist(),
                    'qvel':env.sim.data.qvel.cpu().tolist(),
                    'observation':observation['actor'].cpu().tolist(),
                    'motor_force_nm':term._solver_force.cpu().tolist(),
                    'sole_found':feet.found.cpu().tolist(),
                    'sole_force_world_n':feet.force.cpu().tolist()}
                samples.append(sample);rows.append(sample)
            passes[captured] = samples
        state = {name:getattr(env.sim.data,name)[1].clone() for name in ('qpos','qvel','time','ctrl')}
        history = {name:getattr(term.drive,name)[1].clone() for name in
                   ('target','thermal','actions','last_tau','completed_ticks')}
        env.reset(env_ids=torch.tensor([0],device='cuda:0'))
        if (not all(torch.equal(getattr(env.sim.data,name)[1],value) for name,value in state.items())
                or not all(torch.equal(getattr(term.drive,name)[1],value) for name,value in history.items())
                or term.drive.completed_ticks.tolist() != [0,steps]):
            raise RuntimeError('Selective reset changed the running world/history')
        precision = {}
        cpu = [row for row in rows if row.get('case') == 'standing' and 'tick' in row]
        if len(cpu) == steps:
            for field in ('qpos','qvel'):
                cpu_values = np.array([row[field] for row in cpu])[:,None,:]
                actual = np.array([row[field] for row in passes[False]])
                precision['CPU_GPU_'+field+'_max_abs_by_coordinate'] = np.abs(actual-cpu_values).max(axis=(0,1)).tolist()
        graph_equal = None
        if graph_available:
            graph_equal = True
            for field in ('qpos','qvel','motor_force_nm','observation'):
                direct = np.array([row[field] for row in passes[False]])
                graph = np.array([row[field] for row in passes[True]])
                precision['graph_'+field+'_max_abs'] = float(np.max(np.abs(graph-direct)))
                graph_equal = graph_equal and np.array_equal(graph,direct)
        comparison=(evaluate_comparison(preflight.model,cpu,passes,precision_acceptance)
                    if precision_acceptance is not None else None)
        import importlib.util
        engine_origin=importlib.util.find_spec('mujoco_warp._src.collision_primitive').origin
        return {'selected_engine_origin':engine_origin,'selected_engine_source_sha256':sha256(Path(engine_origin)),
                'numerical_comparison':comparison,
                'selective_reset_preserves_running_world':True, 'two_foot_sensor_checked':True,
                'physics_dt_s':DT,'zero_action_standing':reference is None,
                'external_reference':reference['identity'] if reference is not None else None,'graph_capture_available':graph_available,
                'graph_capture_control_comparison_exact':graph_equal,'measured_error_bounds':precision,
                'precision_acceptance':'Owner review required; observed errors never silently accepted',
                'reference_mode':'exact_CPU_standing_action_trace_replay' if replay is not None else 'constant_action',
                'cpu_action_trace':cpu_replay,'same_input_verified_each_tick':replay is not None}
    except BaseException:
        if env is not None:
            state = {name:getattr(env.sim.data,name).cpu().tolist()
                     for name in ('time','qpos','qvel','qacc','ctrl','actuator_force')}
            if 'term' in locals():
                state['actual_solver_force_captured_by_tick_guard'] = term._solver_force.cpu().tolist()
                state['controller_target'] = term.drive.target.cpu().tolist()
                state['controller_thermal'] = term.drive.thermal.cpu().tolist()
                for bound in ('force_lower','force_upper'):
                    if hasattr(term.drive,bound):
                        state[bound] = getattr(term.drive,bound).cpu().tolist()
            rows.append({'case':'gpu_failed_state', **state})
        raise
    finally:
        if env is not None:
            env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--contract', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--backend', choices=('cpu','gpu','both'), required=True)
    parser.add_argument('--portable', action='store_true',
                        help='Export, relocate and load byte-preserving source bundle before probing')
    parser.add_argument('--steps', type=int, default=100)
    for name in ('reference-action','validation-protocol'):
        parser.add_argument('--'+name,type=Path)
        parser.add_argument('--'+name+'-sha256')
    parser.add_argument('--precision-acceptance',type=Path)
    parser.add_argument('--precision-acceptance-sha256')
    args = parser.parse_args()
    if bool(args.precision_acceptance)!=bool(args.precision_acceptance_sha256):
        parser.error('Numerical acceptance requires explicit path and hash')
    reference_inputs={key:getattr(args,key) for key in ('reference_action','reference_action_sha256',
        'validation_protocol','validation_protocol_sha256')}
    if any(value is not None for value in reference_inputs.values()):
        if not all(value is not None for value in reference_inputs.values()):
            parser.error('External reference requires both explicit paths and both hashes')
    else:
        reference_inputs=None
    if not 1 <= args.steps <= 100:
        parser.error('--steps must be bounded to 1..100')
    if args.output.exists():
        raise FileExistsError('Preserve the previous admission attempt')
    args.output.mkdir(parents=True)
    rows, counters = [], {'CPU_integrations':0,'GPU_integrations':0,'optimizer_updates':0}
    started, failure, checks = time.monotonic(), None, {}
    reference_identity=None
    cpu_replay=None
    precision_acceptance=None
    try:
        model_path, contract_path = args.model, args.contract
        if args.precision_acceptance is not None:
            precision_acceptance=load_acceptance(args.precision_acceptance,args.precision_acceptance_sha256,model_path)
        if reference_inputs is not None:
            from .closeout_reference import load_reference
            reference_identity=load_reference(model_path,contract_path,reference_inputs)['identity']
        if args.portable:
            from .closeout_bundle import export_bundle
            portable = args.output/'portable'
            staging = args.output/'portable_staging'
            export_bundle(model_path, contract_path, staging,reference_inputs=reference_inputs,precision_acceptance=precision_acceptance)
            staging.rename(portable)
            model_path, contract_path = portable/'robot.xml', portable/'contract.json'
            if reference_inputs is not None:
                reference_inputs={**reference_inputs,'reference_action':portable/'reference_inputs/reference_action.json',
                    'validation_protocol':portable/'reference_inputs/validation_protocol.json'}
            if precision_acceptance is not None:
                precision_acceptance=load_acceptance(portable/'validation/gpu_precision_acceptance_001.json',args.precision_acceptance_sha256,model_path)
            checks['portable_source_exported'] = True
            checks['portable_relocated_before_load'] = True
        for backend in (('cpu','gpu') if args.backend == 'both' else (args.backend,)):
            checks[backend] = (run_cpu if backend == 'cpu' else run_gpu)(
                model_path, contract_path, args.steps, rows, counters,
                **({'reference_inputs':reference_inputs,**({'cpu_replay':cpu_replay} if backend=='gpu' else {})}
                   if reference_inputs is not None else {}),
                **({'precision_acceptance':precision_acceptance}if precision_acceptance is not None else {}))
            if backend=='gpu' and precision_acceptance is not None:
                if not checks[backend]['numerical_comparison']['precision_passed']:
                    raise RuntimeError('Predeclared CPU/GPU numerical acceptance failed; preserve actual measurements')
            if backend=='cpu' and reference_inputs is not None:
                trace_path=args.output/'cpu_trace.json'
                trace_path.write_text(json.dumps(rows,indent=2)+'\n')
                cpu_replay={'path':str(trace_path),'sha256':sha256(trace_path)}
    except BaseException:
        failure = traceback.format_exc()
    finally:
        (args.output/'trace.json').write_text(json.dumps(rows, indent=2)+'\n')
        receipt = {'schema':'goose_closeout_actual20ms_probe_v1',
            'model_sha256':sha256(args.model), 'contract_sha256':sha256(args.contract),
            'actual_tested_model_sha256':sha256(model_path),
            'actual_tested_contract_sha256':sha256(contract_path),
            'precision_acceptance':({k:v for k,v in precision_acceptance.items()if k!='document'}if precision_acceptance is not None else None),
            'external_reference':reference_identity,'backend':args.backend, 'steps_per_case':args.steps, **counters,
            'checks':checks, 'completed_cpu_case_integrations':{case:sum(row.get('case') == case and 'tick' in row for row in rows)
                for case in ('standing','drop_50mm','reinitialize')}, 'failure':failure, 'elapsed_s':time.monotonic()-started,
            'training_ready':False, 'qualification':'none',
            'status':'FAILED_PRESERVED' if failure else 'BOUNDED_DYNAMIC_PROBE_ONLY'}
        (args.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        print('STATUS '+json.dumps(receipt), flush=True)
    if failure:
        raise RuntimeError(failure)


if __name__ == '__main__':
    main()
