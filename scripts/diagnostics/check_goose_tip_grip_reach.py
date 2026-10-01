"""Finite IK/static/floor rejection screen of the detached tip grip candidate."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time

import mujoco
import numpy as np
from build123d import import_brep
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull

from sai_agent.goose.native_linkage import set_passive_linkage

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/models'), str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'evidence/body_bay_mechanical_parameters.json',
             R/'configs/tip_grip_physics_contract.json', R/'models/tip_grip_physics/robot.xml',
             R/'cad/exports/tip_grip_candidate/manifest.json']
    ledger, contract, kit = [json.loads(paths[i].read_text()) for i in [0, 1, 3]]
    for data in [contract, kit]:
        for relative, digest in data['source_hashes'].items():
            if sha(ROOT/relative) != digest:
                raise ValueError(('stale source', relative))
    if sha(paths[2]) != contract['model_sha256']:
        raise ValueError('tip model identity')
    s = candidate()
    s.pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    s.grip = np.array(kit['front_contact_native_world_m'])+lift
    s.tip = np.array(ledger['tip_world_at_zero_m'])
    s.items = copy.deepcopy(ledger['items'])
    parts = {p['name']: p for p in kit['parts']}
    for item in s.items:
        if item['name'] in parts:
            part = parts[item['name']]
            item.update(mass_kg=part['mass_kg'], center_m=(np.array(part['center_of_mass_world_m'])+lift).tolist(),
                        inertia_at_com_kg_m2=part['inertia_at_com_world_kg_m2'])
        elif item['name'] == 'specified_payload_50g':
            item['center_m'] = s.grip.tolist()
    s.contact_hulls = {n: ConvexHull(np.array(v)) for n, v in ledger['contact_hulls'].items()}
    s.contact_center_y_m = ledger['contact_center_y_m']
    static_models = {v: s.model(v)[0] for v in [-1, 0, 1]}
    model = mujoco.MjModel.from_xml_path(str(paths[2]))
    data = mujoco.MjData(model)
    order = contract['joint_order']
    qadr = [model.joint(n).qposadr[0] for n in order]
    joints = {j['name']: j for j in contract['joints']}
    lookup = {g['name']: g['part'] for g in contract['collision_geometries']}
    neck = ['neck_pitch', 'neck_mid_pitch', 'head_pitch']
    bounds = np.array([joints[n]['range_rad'] for n in neck])
    started = time.monotonic()
    records = []
    for drop in [60, 70, 80, 90]:
        for target_x in [.22, .26]:
            for pitch in [1.1, 1.3, 1.45]:
                q, root, rotation = s.pose(drop)
                target = np.array([target_x, 0., .016])

                def grip_at(angles):
                    pose = dict(q)
                    pose.update(zip(neck, angles))
                    fk, _ = s.fk(pose, root_p=root, root_r=rotation)
                    return s.point(fk, 'head_roll', s.grip)

                def residual(angles):
                    return np.r_[(grip_at(angles)-target)[[0, 2]], .1*(sum(angles)-pitch)]

                sol = least_squares(residual, [2.17, .08, -.95],
                                    bounds=(bounds[:, 0], bounds[:, 1]), max_nfev=80)
                q.update(zip(neck, sol.x.tolist()))
                grip = grip_at(sol.x)
                error = float(np.linalg.norm(grip-target))
                pitch_error = float(abs(sum(sol.x)-pitch))
                limits = [n for n in order if not joints[n]['range_rad'][0] <= q[n] <= joints[n]['range_rad'][1]]
                ik = not limits and error < .001 and pitch_error < .01
                static, endpoints = [], []
                if ik:
                    fk, axes = s.fk(q, root_p=root, root_r=rotation)
                    normal = fk['head_roll'][1]@np.array([0., 0., 1.])
                    # Existing static checker validates a50N opposed pair.
                    # Reduce ONLY that pair to the declared20N tip test load;
                    # all head ancestors see equal/cancelling pair forces.
                    correction = 30.*float(axes['beak_hinge']@np.cross(grip-fk['beak_hinge'][0], normal))
                    for variant, sm in static_models.items():
                        for drag in [-2., 0., 2.]:
                            result = s.evaluate('tip_grip_floor_candidate', q, root, rotation,
                                                ['right', 'left'], variant, drag, sm)
                            torque = dict(result['joint_torque_nm'])
                            torque['beak_hinge'] -= correction
                            overload = [n for n in order if abs(torque[n]) > joints[n]['continuous_design_limit_nm']]
                            static.append(dict(mass_variant=variant, drag_x_n=drag, tip_opposed_clamp_n=20.,
                                joint_torque_nm=torque, beak_50_to_20n_correction_nm=correction,
                                overloaded_axes=overload, contact_wrench_feasible=result['static_contact_feasible'],
                                minimum_foot_edge_margin_m=min(c['edge_margin_m'] for c in result['contacts']),
                                static_screen_pass=result['static_contact_feasible'] and not overload))
                    for angle in [0., .26, .55]:
                        mujoco.mj_resetData(model, data)
                        data.qpos[:3] = root
                        data.qpos[3:7] = [1, 0, 0, 0]
                        data.qpos[qadr] = [q[n] for n in order]
                        data.qpos[model.joint('beak_hinge').qposadr[0]] = angle
                        set_passive_linkage(model, data, contract)
                        mujoco.mj_forward(model, data)
                        hits = []
                        for cc in data.contact:
                            if cc.dist >= -.0002:
                                continue
                            a, b = [model.geom(int(g)).name for g in cc.geom]
                            if 'ground' in (a, b):
                                other = b if a == 'ground' else a
                                if 'sole_pad' in other or lookup.get(other, '').endswith('_flexible_sole'):
                                    continue
                            hits.append(dict(part_a=lookup.get(a, a), part_b=lookup.get(b, b), depth_m=float(-cc.dist)))
                        endpoints.append(dict(jaw_angle_rad=angle, contacts=hits, approximate_geometry_pass=not hits))
                passed = bool(ik and static and all(c['static_screen_pass'] for c in static)
                              and endpoints and all(c['approximate_geometry_pass'] for c in endpoints))
                record = dict(index=len(records), crouch_drop_mm=drop, target_front_contact_world_m=target.tolist(),
                              head_pitch_target_rad=pitch, q_rad=q, root_position_m=root.tolist(),
                              actual_front_contact_world_m=grip.tolist(), ik_position_error_m=error,
                              ik_pitch_error_rad=pitch_error, limit_violations=limits, ik_pass=ik,
                              static_cases=static, jaw_endpoints=endpoints, finite_screen_pass=passed)
                records.append(record)
                print('TIP REACH', record['index'], 'IK', ik, 'finite', passed, flush=True)
    passed = [r for r in records if r['finite_screen_pass']]
    native = []
    if passed:
        best = min(passed, key=lambda r: (r['crouch_drop_mm'], abs(r['head_pitch_target_rad']-1.3), abs(r['target_front_contact_world_m'][0]-.22)))
        native_shapes = {}
        for name, part in parts.items():
            info = part['files']['brep']
            file = R/info['path']
            if sha(file) != info['sha256']:
                raise ValueError(('native BREP identity', name))
            native_shapes[name] = import_brep(file)
            paths.append(file)
        ground = box([2000., 2000., 500.], [0., 0., -250.])
        for angle in [0., .26, .55]:
            q = dict(best['q_rad'])
            q['beak_hinge'] = angle
            fk, _ = s.fk(q, root_p=np.array(best['root_position_m']))
            results = []
            for name, shape in native_shapes.items():
                owner = parts[name]['body']
                position, rotation = fk[owner]
                moved = transform(shape, rotation, (position+rotation@(lift-s.pivots[owner]))*1000)
                result = bounded_common(moved, ground, 3.)
                results.append(dict(part=name, native_common=result,
                                    native_floor_clear='error' not in result and result['volume_mm3'] <= .01))
            native.append(dict(screen_index=best['index'], jaw_q_rad=angle, parts=results,
                               native_floor_pass=all(r['native_floor_clear'] for r in results)))
        selected = best
    else:
        selected = None
    report = dict(schema='goose_tip_grip_finite_reach_v1', requested_candidates=24,
                  completed_candidates=len(records), records=records,
                  finite_screen_pass_indices=[r['index'] for r in passed], selected_candidate=selected,
                  selected_native_floor_cases=native,
                  selected_native_floor_pass=bool(native and all(c['native_floor_pass'] for c in native)),
                  nominal_conditional_robot_mass_kg=contract['nominal_robot_mass_kg'],
                  wall_seconds_after_model_load=time.monotonic()-started,
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
                  installed=False, actual_object_pickup_pass=False, training_release=False,
                  limitations=['Finite24pose local IK/static/three-jaw-endpoint screen; not a global morphology optimum.',
                    'Front contact reference is inside an actual backed TPU surface atX255mm, not a moved proxy.',
                    '20N tip clamp screened; middle50N target is a distinct contact region. No measured force/friction.',
                    'Native below-floor commons only cover the selected pose at three angles; no continuous swept CAD.',
                    'No floor object, approach, lift, return, walking or terrain success is inferred.'])
    (R/'evidence/tip_grip_finite_reach.json').write_text(json.dumps(report, indent=2)+'\n')
    print('TIP REACH DONE', len(passed), 'native floor pass', report['selected_native_floor_pass'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
