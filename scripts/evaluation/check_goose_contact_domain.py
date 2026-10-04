"""Bounded source contact-domain diagnostic on the frozen 004 physical inputs.

This observes recovery initial states; it does not train a policy or grant
recovery qualification. Recording wraps the contact hook without changing its
inputs, outputs or integration. Full per-tick records stay in artifacts.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import mujoco
import numpy as np

from sai_agent.goose.convex_support import compiled_body_vertices
from sai_agent.goose.task_proxy_runtime import TaskProxyRuntime

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contacts(runtime):
    result = []
    for c in runtime.data.contact:
        result.append({'geom_ids': [int(v) for v in c.geom],
            'geoms': [mujoco.mj_id2name(runtime.model, mujoco.mjtObj.mjOBJ_GEOM, int(g)) for g in c.geom],
            'distance_m': float(c.dist), 'position_m': c.pos.tolist(),
            'frame': c.frame.tolist(), 'friction': c.friction.tolist()})
    return result


def minimum_height(runtime, local_vertices):
    heights = {}
    for gid, vertices in local_vertices.items():
        bid = runtime.model.geom_bodyid[gid]
        world = vertices @ runtime.data.xmat[bid].reshape(3, 3).T + runtime.data.xpos[bid]
        heights[runtime.model.geom(gid).name] = float(world[:, 2].min())
    name = min(heights, key=heights.get)
    return heights[name], name, heights


def scenario(axis, degrees, ticks, model, contract):
    r = TaskProxyRuntime(model, contract, skill='recovery')
    local_vertices = {g: compiled_body_vertices(r.model, g)
        for g in range(r.model.ngeom) if g != r.ground}
    radians = math.radians(degrees)
    r.data.qpos[3:7] = [math.cos(radians / 2),
        math.sin(radians / 2) if axis == 'roll' else 0,
        math.sin(radians / 2) if axis == 'pitch' else 0, 0]
    mujoco.mj_forward(r.model, r.data)
    r.data.qpos[2] += .002 - minimum_height(r, local_vertices)[0]
    mujoco.mj_forward(r.model, r.data)
    initial_qpos = r.data.qpos.tolist()
    initial_gap = minimum_height(r, local_vertices)[0]
    if abs(initial_gap - .002) > 1e-10:
        raise ValueError('source geometry did not produce the requested clear initial state')
    # The wrapper calls the original exactly once. It only copies observations.
    original = r._planar_sole_quadrature
    contact_record = {}

    def observe_quadrature():
        before = contacts(r)
        replacements = {r.model.geom(p['geom']).id
            for p in r.contract['contact_mapping']['ground_contact_quadrature']
            if r.data.xmat[r.model.body(p['body']).id].reshape(3, 3)[2, 2] > .7}
        pre_gap, pre_geom, pre_heights = minimum_height(r, local_vertices)
        original()
        after = contacts(r)
        # All other native geometry contacts must remain unchanged. Constraint
        # addresses aren't compared because rebuilding constraints changes them.
        def retained(rows):
            return [x for x in rows if not (r.ground in x['geom_ids'] and
                any(g in replacements for g in x['geom_ids']))]
        if retained(before) != retained(after):
            raise ValueError('contact instrumentation found altered non-quadrature geometry contacts')
        contact_record.clear()
        contact_record.update(native_before=before, after_quadrature=after,
            quadrature_geoms=[r.model.geom(g).name for g in sorted(replacements)],
            pre_minimum_height_m=pre_gap, pre_lowest_geom=pre_geom,
            pre_geom_minimum_height_m=pre_heights,
            retained_native_geometry_identical=True)

    r._planar_sole_quadrature = observe_quadrature
    trace = []
    error = None
    for tick in range(ticks):
        try:
            obs, info = r.step(np.zeros(18))
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            error = repr(exc)
            break
        if info['auto_reset'] or r.physics_integrations != tick + 1 or r.controller_updates != tick + 1:
            raise ValueError('unexpected reset or physical/controller integration count')
        gap, geom, heights = minimum_height(r, local_vertices)
        trace.append({'tick': tick + 1, 'time_s': float(r.data.time),
            'physics_integrations': r.physics_integrations, 'controller_updates': r.controller_updates,
            'auto_reset': info['auto_reset'], 'upright': info['upright'],
            'qpos': r.data.qpos.tolist(), 'qvel': r.data.qvel.tolist(),
            'post_minimum_height_m': gap, 'post_lowest_geom': geom,
            'post_geom_minimum_height_m': heights,
            'contacts': dict(contact_record)})
    worst = min(trace, key=lambda x: x['post_minimum_height_m']) if trace else None
    result = {'axis': axis, 'degrees': degrees, 'requested_ticks': ticks,
        'completed_ticks': len(trace), 'initial_qpos': initial_qpos,
        'initial_geometry_clearance_m': initial_gap, 'error': error,
        'native_warning_counts': [int(w.number) for w in r.data.warning],
        'integrations': r.physics_integrations, 'controller_updates': r.controller_updates,
        'minimum_upright': min((x['upright'] for x in trace), default=None),
        'maximum_post_geometry_penetration_m': max(0., -worst['post_minimum_height_m']) if worst else None,
        'worst_tick': worst['tick'] if worst else None,
        'worst_geom': worst['post_lowest_geom'] if worst else None,
        'pre_minimum_height_at_worst_tick_m': worst['contacts']['pre_minimum_height_m'] if worst else None,
        'quadrature_changes': sum(a['contacts']['quadrature_geoms'] != b['contacts']['quadrature_geoms']
            for a, b in zip(trace, trace[1:])),
        'all_retained_native_contacts_identical': bool(trace) and not error and all(x['contacts']['retained_native_geometry_identical'] for x in trace),
        'full_recovery_qualification': False}
    return result, trace


def verify_uninstrumented_replay(result, trace, model, contract):
    """Replay the exact saved input without the contact observation wrapper.

    This deliberately checks the full trajectory, not only the lowest vertex.
    A mismatch rejects the diagnostic record; it does not change the plant.
    """
    r = TaskProxyRuntime(model, contract, skill='recovery')
    r.data.qpos[:] = result['initial_qpos']
    r.data.qvel[:] = 0.
    mujoco.mj_forward(r.model, r.data)
    maxima = {'qpos': 0., 'qvel': 0.}
    for row in trace:
        r.step(np.zeros(18))
        for field in maxima:
            delta = float(np.max(np.abs(getattr(r.data, field) - np.array(row[field]))))
            if not math.isfinite(delta) or delta != 0.:
                raise ValueError(f'Uninstrumented replay differs at tick {row["tick"]}: {field} delta={delta}')
            maxima[field] = max(maxima[field], delta)
    if not trace or r.physics_integrations != result['completed_ticks']:
        raise ValueError('Replay did not cover the recorded diagnostic')
    return {'scenario': f'{result["axis"]}_{result["degrees"]}',
        'ticks': len(trace), 'exact_qpos_qvel_match': True,
        'maximum_absolute_deltas': maxima,
        'native_warning_counts': [int(w.number) for w in r.data.warning]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ticks', type=int, default=100)
    parser.add_argument('--axis', choices=['roll', 'pitch'])
    parser.add_argument('--degrees', type=int, nargs='+', default=[0, 45, 46, 90, -90, 135, 180])
    args = parser.parse_args()
    if not 1 <= args.ticks <= 200:
        parser.error('bounded diagnostic requires 1..200 ticks per scenario')
    args.out.mkdir(parents=True, exist_ok=True)
    model = (ROBOT / 'models/task_proxy_11_v1/robot.xml').resolve()
    contract = (ROBOT / 'configs/task_proxy_11_v1_contract.json').resolve()
    runtime = ROOT / 'src/sai_agent/goose/task_proxy_runtime.py'
    bindings = {str(p.relative_to(ROOT)): sha(p) for p in [model, contract, runtime]}
    results = []
    for axis in ([args.axis] if args.axis else ['roll', 'pitch']):
        for degrees in args.degrees:
            result, trace = scenario(axis, degrees, args.ticks, model, contract)
            file = args.out / f'{axis}_{degrees}_trace.json'
            file.write_text(json.dumps(trace, separators=(',', ':')) + '\n')
            result['trace_path'] = file.name
            result['trace_sha256'] = sha(file)
            results.append(result)
    worst_case = max(results, key=lambda x: x['maximum_post_geometry_penetration_m'] or 0.)
    worst_trace = json.loads((args.out / worst_case['trace_path']).read_text())
    replay = verify_uninstrumented_replay(worst_case, worst_trace, model, contract)
    worst_row = worst_trace[worst_case['worst_tick'] - 1]
    if any(sha(ROOT / p) != digest for p, digest in bindings.items()):
        raise ValueError('frozen source changed during diagnostic')
    report = {'schema': 'goose_source_contact_domain_diagnostic_v1',
        'candidate_id': 'goose_task_proxy_11_v1', 'mujoco': mujoco.__version__,
        'source_bindings_sha256': bindings, 'source_evaluator_sha256': sha(Path(__file__)),
        'physics_dt_s': .02, 'initial_pose_basis': 'Rotate the unchanged full robot, align all native hull vertices to plane +2mm; keep neutral joint/mimic values and zero action.',
        'scenarios': results, 'source_inputs_changed': False,
        'all_scenarios_completed': all(x['completed_ticks'] == args.ticks and x['error'] is None for x in results),
        'worst_case_uninstrumented_replay': replay,
        'worst_step_witness': {'axis': worst_case['axis'], 'degrees': worst_case['degrees'],
            'initial_qpos': worst_case['initial_qpos'], 'step': worst_row},
        'PPO_updates': 0, 'full_recovery_qualification': False,
        'scope': 'Finite neutral-action falling/settling diagnostic, not a recovery policy, material or GPU qualification. Pre-contact and post-step geometry are recorded separately.'}
    (args.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
