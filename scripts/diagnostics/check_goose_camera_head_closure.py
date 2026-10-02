"""Bounded new head contacts and fresh same-source static screening.

Keep all vendor groups, all failures and positive legacy contacts. Thread
envelopes require individually checked overlap volumes; timeout is unknown.
"""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import sys
import time

import mujoco
import numpy as np
import trimesh
from build123d import import_brep, import_step
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad'), str(ROOT / 'scripts/models'), str(ROOT / 'scripts/diagnostics')]
from build_goose_cad import box, transform
from build_goose_stage_two import candidate
from build_goose_integrated_hardware_candidate import opposed_clamp_result
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(shape):
    bb = shape.bounding_box(optimal=False)
    return np.array(tuple(bb.min)), np.array(tuple(bb.max))


def main():
    paths = [ROBOT / p for p in ['cad/exports/camera_head_closure/manifest.json',
        'evidence/camera_head_closure_parameters.json', 'evidence/integrated_hardware_parameters.json',
        'evidence/body_bay_mechanical_parameters.json', 'configs/mechanical_physics_contract.json',
        'evidence/camera_catalog_layout.json', 'cad/source/integrated_hardware_candidate/scene.json']]
    kit, parameters, old, default, contract, catalog, scene = [json.loads(p.read_text()) for p in paths]
    for rel, digest in kit['source_hashes'].items():
        if sha(ROOT / rel) != digest:
            raise ValueError(('Changed native source', rel))
    for rel, digest in parameters['source_hashes'].items():
        if sha(ROOT / rel) != digest:
            raise ValueError(('Changed parameter source', rel))
    own, quad_records = {}, []
    for p in kit['parts']:
        for rec in p['files'].values():
            if sha(ROBOT / rec['path']) != rec['sha256']:
                raise ValueError(('Changed native geometry', p['name']))
        own[p['name']] = import_brep(ROBOT / p['files']['brep']['path'])
        if not own[p['name']].is_valid or len(own[p['name']].solids()) != 1:
            raise ValueError(('Invalid native part', p['name']))
        data = np.load(ROBOT / p['files']['npz']['path'])
        v, f = data['vertices'], data['faces']
        if f.ndim != 2 or f.shape[1] != 4:
            raise ValueError('Non-quad source')
        mesh = trimesh.Trimesh(v, np.concatenate([f[:, [0, 1, 2]], f[:, [0, 2, 3]]]), process=False)
        err = abs(mesh.volume * 1e9 / p['volume_mm3'] - 1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or err > .005:
            raise ValueError(('Quad closure mismatch', p['name'], err))
        quad_records.append(dict(name=p['name'], quads=len(f), closed=True, winding_consistent=True, volume_relative_error=err))
    frame_name = 'head_frame_camera_fastened_carrier'
    old_frame_path = ROBOT / 'cad/source/camera_carrier/head_frame_camera_carrier.brep'
    old_frame = import_brep(old_frame_path)
    paths.append(old_frame_path)
    threads = {frozenset([t['screw'], t['frame']]): t for t in kit['nominal_thread_contacts']}
    supplier_threads = {(t['screw'],t['supplier_group']):t for t in kit['nominal_oem_thread_contacts']}
    queries, failures, unknown, thread_checks, supplier_thread_checks, retained_contacts = [], [], [], [], [], []
    cache = {}
    started = time.monotonic()
    def common(a, b, label):
        lo_a, hi_a = bounds(a)
        lo_b, hi_b = bounds(b)
        if np.any(np.minimum(hi_a, hi_b) - np.maximum(lo_a, lo_b) <= 1e-6):
            return dict(volume_mm3=0., method='disjoint or tangent conservative native AABBs')
        limit = 10. if len(label) == 2 and label[-1] == 'UC-A51_Rev_B' and label[0] == 'head_camera_nose_shroud' else 3.
        result = bounded_common(a, b, limit)
        queries.append(dict(pair=label, attempt_timebox_seconds=limit, **result))
        if result.get('error') == 'NATIVE_PAIR_TIMEBOX' and limit == 3.:
            result = bounded_common(a, b, 60.)
            queries.append(dict(pair=label, attempt_timebox_seconds=60., **result))
        return result
    for a, b in itertools.combinations(own, 2):
        result = common(own[a], own[b], [a, b])
        if 'error' in result:
            unknown.append(dict(a=a, b=b, **result))
        elif frozenset([a, b]) in threads:
            expected = threads[frozenset([a, b])]['expected_thread_overlap_mm3']
            passed = abs(result['volume_mm3'] - expected) < .03
            thread_checks.append(dict(a=a, b=b, expected_mm3=expected, actual_mm3=result['volume_mm3'], pass_contact=passed))
            if not passed:
                failures.append(dict(a=a, b=b, **result, reason='Nominal threaded contact differs from explicit stack'))
        elif result['volume_mm3'] > .01:
            failures.append(dict(a=a, b=b, **result))

    supplier_path = ROOT / 'artifacts/Goose_V0.1/camera_vendor_docs/b0471.step'
    if sha(supplier_path) != catalog['vendor_files']['step']['sha256']:
        raise ValueError('Vendor source changed')
    supplier = import_step(supplier_path)
    pose = catalog['selected']
    vendor_r, vendor_t = np.array(pose['vendor_to_native_rotation']), np.array(pose['vendor_to_native_translation_mm'])
    vendor_cases = []
    for child in supplier.children:
        valid = bool(child.is_valid and child.solids())
        if valid:
            obstacle = transform(child, vendor_r, vendor_t)
        else:
            lo, hi = bounds(child)
            obstacle = transform(box(hi - lo + 1.4, (lo + hi) / 2), vendor_r, vendor_t)
        cases = []
        for name, shape in own.items():
            result = common(shape, obstacle, [name, child.label])
            if 'error' in result and valid:
                # Exact union-zero proof using every retained valid OEM solid.
                # No display proxy, hull shrink or deleted vendor children.
                solid_results = []
                for index, solid in enumerate(child.solids()):
                    # Expanded native source-axis bounds enclose every face.
                    # A zero intersection with that larger box proves separation;
                    # a positive box intersection must refine to the real solid.
                    lo, hi = bounds(solid)
                    enclosing = transform(box(hi-lo+.02, (lo+hi)/2), vendor_r, vendor_t)
                    enclosure = common(shape, enclosing, [name, child.label, 'solid_bounds', index])
                    if 'error' not in enclosure and enclosure['volume_mm3'] <= 1e-8:
                        piece = dict(volume_mm3=enclosure['volume_mm3'],
                            method='complete native source-axis bounds expanded0.01mm; conservative zero proof',
                            enclosure_result=enclosure)
                    else:
                        posed_solid = transform(solid, vendor_r, vendor_t)
                        piece = common(shape, posed_solid, [name, child.label, 'solid', index])
                        piece = dict(piece, enclosure_result=enclosure)
                    solid_results.append(dict(index=index, **piece))
                if all('error' not in piece for piece in solid_results):
                    upper = sum(max(0., piece['volume_mm3']) for piece in solid_results)
                    result = dict(volume_mm3=upper,
                        method='all valid OEM solids retained; sum of exact/enclosing intersections is a conservative union-intersection upper bound',
                        solids_checked=len(solid_results), solid_results=solid_results)
                else:
                    result = dict(error='OEM_SOLID_DECOMPOSITION_UNRESOLVED', solids_checked=len(solid_results), solid_results=solid_results)
            cases.append(dict(name=name, **result))
            if 'error' in result:
                unknown.append(dict(a=name, b=child.label, **result))
            elif (name,child.label) in supplier_threads:
                expected=supplier_threads[(name,child.label)]['expected_thread_overlap_mm3']
                passed=abs(result['volume_mm3']-expected)<.03
                supplier_thread_checks.append(dict(a=name,b=child.label,expected_mm3=expected,actual_mm3=result['volume_mm3'],pass_contact=passed))
                if not passed:
                    failures.append(dict(a=name,b=child.label,**result,reason='OEM nominal threaded contact differs from explicit source stack'))
            elif result['volume_mm3'] > .01:
                failures.append(dict(a=name, b=child.label, **result, source_valid=valid))
        vendor_cases.append(dict(label=child.label, source_valid=valid, source_solid_count=len(child.solids()),
            method='exact valid OEM group' if valid else 'complete expanded OEM non-solid group; no omission', cases=cases))
    paths.append(supplier_path)

    system = candidate()
    system.pivots = {k: np.array(v) for k, v in parameters['pivots_world_at_zero_m'].items()}
    owners = {p['name']: p['body'] for p in old['items']}
    targets = {}
    for p in scene['parts']:
        name = p['name']
        if name in kit['replaces_existing_parts'] or not p.get('geometry_npz') or owners.get(name) not in ['head_roll','head_pitch','beak_hinge']:
            continue
        path = ROBOT / p['geometry_npz'].replace('_quad.npz', '.brep')
        if not path.exists():
            raise ValueError(('No native head input', name, path))
        targets[name] = import_brep(path)
        paths.append(path)
    poses = [('zero', {})] + [(row['name'], row['joint_q_rad']) for row in old['static_results']
        if row['mass_variant'] == 0 and row['drag_x_n'] == 0]
    poses += [('head_roll_' + str(q), {'head_roll': q}) for q in [-.6, .6]]
    finite_reports = []
    for case_name, q in poses:
        fk, _ = system.fk(q, root_p=system.pivots['torso'])
        def place(shape, owner):
            position, rotation = fk[owner]
            return transform(shape, rotation, (position - rotation @ system.pivots[owner]) * 1000)
        hits, unresolved = [], []
        for a, shape in own.items():
            for b, other in targets.items():
                key = (a, b, 'same' if owners[b] == 'head_roll' else case_name)
                if key not in cache:
                    result = common(place(shape, 'head_roll'), place(other, owners[b]), [case_name, a, b])
                    previous = None
                    if a == frame_name and 'error' not in result and result['volume_mm3'] > .01:
                        previous = common(place(old_frame, 'head_roll'), place(other, owners[b]), ['legacy', case_name, a, b])
                    cache[key] = result, previous
                result, previous = cache[key]
                if 'error' in result or previous is not None and 'error' in previous:
                    unresolved.append(dict(a=a, b=b, result=result, previous=previous))
                elif result['volume_mm3'] > .01:
                    if previous is not None and result['volume_mm3'] <= previous['volume_mm3'] + .01:
                        retained_contacts.append(dict(case=case_name, a=a, b=b, current_mm3=result['volume_mm3'], prior_mm3=previous['volume_mm3']))
                    else:
                        hits.append(dict(a=a, b=b, **result))
        finite_reports.append(dict(name=case_name, joint_q_rad=q, collisions=hits, unresolved=unresolved,
            incremental_head_fit_pass=not hits and not unresolved))
        print('HEAD CLOSURE FIT', case_name, len(hits), 'hits', len(unresolved), 'unknown', flush=True)

    # A fresh static screen, not inherited419 results. Grips/feet/joint axes
    # are unchanged, but all new mass, COM and full tensors enter this system.
    system.items = copy.deepcopy(parameters['items'])
    system.contact_hulls = {k: ConvexHull(np.array(v)) for k, v in default['contact_hulls'].items()}
    system.contact_center_y_m = default['contact_center_y_m']
    system.tip = np.array(default['tip_world_at_zero_m'])
    payload = copy.deepcopy(next(p for p in default['items'] if p['name'] == 'specified_payload_50g'))
    system.items.append(payload)
    static = {}
    for station, point, force in [('front20n', old['front_grip_reference_world_m'], 20.),
                                  ('middle50n', old['middle_grip_reference_world_m'], 50.)]:
        system.grip = np.array(point)
        payload['center_m'] = (system.grip + np.array(default['native_grip_reference']['payload_reference_offset_m'])).tolist()
        results = []
        for variant in [-1, 0, 1]:
            model, _ = system.model(variant)
            for row in old['static_results']:
                if row['mass_variant'] != variant:
                    continue
                q = row['joint_q_rad']
                w, x, y, z = row['root_quaternion_wxyz']
                support = ['right'] if row['name'] == 'right_single_support' else ['left'] if row['name'] == 'left_single_support' else ['right','left']
                value = system.evaluate(row['name'], q, np.array(row['root_position_m']),
                    Rotation.from_quat([x,y,z,w]).as_matrix(), support, variant, row['drag_x_n'], model)
                if force != 50.:
                    value = opposed_clamp_result(system, model, value, force)
                results.append(value)
        joint_summary = []
        for joint in contract['joints']:
            worst = max(results, key=lambda r: abs(r['joint_torque_nm'][joint['name']]))
            value = abs(worst['joint_torque_nm'][joint['name']])
            limit = joint['continuous_design_limit_nm']
            joint_summary.append(dict(joint=joint['name'], worst_nm=value, limit_nm=limit, margin_nm=limit-value, pass_torque=value<=limit))
        static[station] = dict(cases=len(results), results=results, joint_summary=joint_summary,
            contact_feasible=sum(r['static_contact_feasible'] for r in results), all_static_torques_pass=all(j['pass_torque'] for j in joint_summary))
    geometry_pass = not failures and not unknown and len(thread_checks) == 4 and len(supplier_thread_checks) == 4 and all(r['incremental_head_fit_pass'] for r in finite_reports)
    static_pass = all(r['contact_feasible'] == 63 and r['all_static_torques_pass'] for r in static.values())
    paths += [Path(__file__), ROOT / 'scripts/diagnostics/check_goose_grip_cassettes.py', ROOT / 'scripts/models/build_goose_integrated_hardware_candidate.py', ROOT / 'scripts/models/build_goose_stage_two.py']
    report = dict(schema='goose_camera_head_closure_fit_v1', own_parts=29, source_quads=quad_records,
        source_validity_and_quad_closure_pass=True, own_pair_failures=failures, unresolved=unknown,
        nominal_thread_contacts=thread_checks, nominal_oem_thread_contacts=supplier_thread_checks, full_supplier_children=vendor_cases,
        incremental_head_cases=finite_reports, existing_frame_contacts_explicitly_retained=retained_contacts,
        static_screens=static, incremental_geometry_pass=geometry_pass, same_source_static_pass=static_pass,
        full_assembly_pass=False, manufacturing_release=False, final_appearance_pass=False, training_release=False,
        original419_unchanged=sha(paths[6]) == 'bce7ee34419f7cb0898d4e5da14ceba5c6db4f4081f9b659ab00e4491d75d4ab',
        wall_seconds=time.monotonic()-started, actual_native_queries=queries,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in dict.fromkeys(paths)},
        limitations=['Finite head-only screen at ten closed-beak poses; full continuous assembly and moving linkage remain gates.',
            'Unchanged positive prior frame contacts recorded individually; not declared fully qualified hardware joints.',
            'One OEM rear group is non-solid, retained through complete expanded bounds; boughtSKU/revision/plug and wire service loop still unconfirmed.',
            'Inherited torque design bounds are screening assumptions, not verified actual AK-A2 driver thermal/current ratings.'])
    (ROBOT / 'evidence/camera_head_closure_fit.json').write_text(json.dumps(report, indent=2) + '\n')
    print('HEAD CLOSURE SUMMARY', geometry_pass, 'static', static_pass, 'queries', len(queries), flush=True)
    return 0 if geometry_pass and static_pass else 1


if __name__ == '__main__':
    raise SystemExit(main())
