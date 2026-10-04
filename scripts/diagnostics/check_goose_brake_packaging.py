"""Native finite-pose packaging and same-candidate static comparison.

No application collision filters participate in CAD queries. Unknown/timeouts
fail a local check. PCB draft and existing electronic boxes are reserves only.
"""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import sys

import numpy as np
from build123d import import_brep
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/models'), str(ROOT/'scripts/diagnostics')]
from build_goose_cad import box
from check_goose_grip_cassettes import bounded_common
from build_goose_stage_two import candidate
from build_goose_integrated_hardware_candidate import opposed_clamp_result
from sai_agent.native_cad_query import native_solid_integrity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(shape):
    bb = shape.bounding_box(optimal=False)
    return np.array(tuple(bb.min)), np.array(tuple(bb.max))


def aabb_gap(a, b):
    # A conservative lower bound on the actual distance, not an optimal box.
    return float(np.linalg.norm(np.maximum(0., np.maximum(a[0]-b[1], b[0]-a[1]))))


def native_pair(a, b, minimum, first, second, mating=False):
    lower = aabb_gap(bounds(a), bounds(b))
    if lower >= minimum+1e-6 and lower > 1e-6:
        return dict(first=first, second=second, gap_lower_bound_mm=lower,
                    method='conservative native AABB distance', pair_pass=True, mating=mating)
    common = bounded_common(a, b, 10)
    gap = float(a.distance_to(b)) if 'error' not in common else None
    passed = 'error' not in common and common['volume_mm3'] < .01 and gap+1e-6 >= minimum
    return dict(first=first, second=second, gap_mm=gap, common=common,
                minimum_gap_mm=minimum, pair_pass=passed, mating=mating)


def static_comparison(params):
    ps = R/'evidence/integrated_hardware_parameters.json'
    dp = R/'evidence/body_bay_mechanical_parameters.json'
    cp = R/'configs/mechanical_physics_contract.json'
    poses, default, contract = [json.loads(p.read_text()) for p in [ps, dp, cp]]
    system = candidate()
    system.pivots = {k:np.array(v) for k,v in params['pivots_world_at_zero_m'].items()}
    system.items = copy.deepcopy(params['items'])
    system.contact_hulls = {k:ConvexHull(np.array(v)) for k,v in default['contact_hulls'].items()}
    system.contact_center_y_m = default['contact_center_y_m']
    system.tip = np.array(default['tip_world_at_zero_m'])
    payload = copy.deepcopy(next(p for p in default['items'] if p['name']=='specified_payload_50g'))
    system.items.append(payload)
    result = {}
    for station, point, force in [('front20n', poses['front_grip_reference_world_m'], 20.),
                                  ('middle50n', poses['middle_grip_reference_world_m'], 50.)]:
        system.grip = np.array(point)
        payload['center_m'] = (system.grip+np.array(default['native_grip_reference']['payload_reference_offset_m'])).tolist()
        rows = []
        for variant in [-1,0,1]:
            model, _ = system.model(variant)
            for pose in poses['static_results']:
                if pose['mass_variant'] != variant:
                    continue
                w,x,y,z = pose['root_quaternion_wxyz']
                support = ['right'] if pose['name']=='right_single_support' else ['left'] if pose['name']=='left_single_support' else ['right','left']
                row = system.evaluate(pose['name'], pose['joint_q_rad'], np.array(pose['root_position_m']),
                    Rotation.from_quat([x,y,z,w]).as_matrix(), support, variant, pose['drag_x_n'], model)
                if force != 50:
                    row = opposed_clamp_result(system, model, row, force)
                rows.append(row)
        joints = []
        for joint in contract['joints']:
            worst = max(abs(row['joint_torque_nm'][joint['name']]) for row in rows)
            limit = joint['continuous_design_limit_nm']
            joints.append(dict(joint=joint['name'], worst_nm=worst, limit_nm=limit,
                               margin_nm=limit-worst, pass_torque=worst<=limit))
        result[station] = dict(cases=len(rows), results=rows, joint_summary=joints,
            contact_feasible=sum(row['static_contact_feasible'] for row in rows),
            all_static_torques_pass=all(row['pass_torque'] for row in joints))
    return result, [ps, dp, cp, ROOT/'scripts/models/build_goose_stage_two.py',
                   ROOT/'scripts/models/build_goose_integrated_hardware_candidate.py']


def main():
    paths = [R/p for p in ['configs/brake_packaging_candidate.json', 'cad/exports/brake_packaging/manifest.json',
        'evidence/brake_packaging_parameters.json', 'evidence/manual_wing_service_native_inventory.json',
        'cad/source/manual_wing_service/assembly_scene.json', 'configs/body_bay_layout_candidate.json']]
    cfg, kit, params, inventory, scene, layout = [json.loads(p.read_text()) for p in paths]
    for data in [kit, params]:
        for rel, expected in data['source_hashes'].items():
            if sha(ROOT/rel) != expected:
                raise ValueError(('Changed candidate input', rel))
    shapes, integrity = {}, []
    for part in kit['parts']:
        for file in part['files'].values():
            if sha(R/file['path']) != file['sha256']:
                raise ValueError(('Changed candidate export', part['name']))
        shape = import_brep(R/part['files']['brep']['path'])
        check = native_solid_integrity(shape)
        shapes[part['name']] = shape
        integrity.append(dict(name=part['name'], **check))
    print('Native parts checked', len(integrity), flush=True)
    retained = {}
    for row in inventory['results']:
        if row['name'] == cfg['chassis']['name']:
            continue
        path = R/row['source']
        if sha(path) != row['sha256']:
            raise ValueError(('Changed retained source', row['name']))
        retained[row['name']] = import_brep(path)
        paths.append(path)
    mating = {frozenset(pair) for pair in kit['nominal_mating_pairs']}
    cases, coarse_clear = [], 0
    new_bounds = {name:bounds(shape) for name,shape in shapes.items()}
    retained_bounds = {name:bounds(shape) for name,shape in retained.items()}
    # Retained chassis is separately shown to lose material only; do not claim
    # a whole preexisting chassis interface release from unchanged relations.
    for index, (name, shape) in enumerate(shapes.items()):
        if name == 'brake_chassis_plate':
            continue
        for other, fixed in retained.items():
            gap = aabb_gap(new_bounds[name], retained_bounds[other])
            if gap >= cfg['minimum_envelope_gap_mm']+1e-6:
                coarse_clear += 1
                continue
            row = native_pair(shape, fixed, cfg['minimum_envelope_gap_mm'], name, other)
            cases.append(row)
            if not row['pair_pass']:
                print('RETAINED FIT REJECT', name, other, row, flush=True)
        if index % 8 == 0:
            print('Retained-pair progress', index+1, '/', len(shapes), flush=True)
    for a, b in itertools.combinations(shapes, 2):
        intentional = frozenset([a,b]) in mating
        gap = aabb_gap(new_bounds[a], new_bounds[b])
        minimum = 0. if intentional else cfg['minimum_envelope_gap_mm']
        if gap >= minimum+1e-6:
            coarse_clear += 1
            continue
        row = native_pair(shapes[a], shapes[b], minimum, a, b, intentional)
        cases.append(row)
        if not row['pair_pass']:
            print('NEW FIT REJECT', a, b, row, flush=True)
    boxes = {name:box(rec['size'], rec['centre']) for name, rec in layout['electronics_allowance_boxes_mm'].items()}
    boxes['brake_pcb_draft'] = box(cfg['pcb']['draft_envelope_size_mm'], cfg['pcb']['draft_envelope_center_mm'])
    envelope_rows = []
    # A PCB reserve must also clear retained native hardware, including neck
    # fixtures. Checking only the new resistor kit would miss this occupancy.
    pcb_retained, pcb_clear = [], 0
    pcb_bounds = bounds(boxes['brake_pcb_draft'])
    for other, fixed in retained.items():
        if aabb_gap(pcb_bounds, retained_bounds[other]) >= cfg['minimum_envelope_gap_mm']+1e-6:
            pcb_clear += 1
            continue
        row = native_pair(boxes['brake_pcb_draft'], fixed, cfg['minimum_envelope_gap_mm'], 'brake_pcb_draft', other)
        pcb_retained.append(row)
        if not row['pair_pass']:
            print('PCB RETAINED REJECT', other, row, flush=True)
    envelope_rows.append(native_pair(boxes['brake_pcb_draft'], shapes['brake_chassis_plate'],
        cfg['minimum_envelope_gap_mm'], 'brake_pcb_draft', 'brake_chassis_plate'))
    for other, envelope in boxes.items():
        if other != 'brake_pcb_draft':
            envelope_rows.append(native_pair(boxes['brake_pcb_draft'], envelope,
                cfg['minimum_envelope_gap_mm'], 'brake_pcb_draft', other))
    for name, shape in shapes.items():
        # Existing plate cuts preserve its previous overlap with explicitly
        # reserved component mounts; new kit alone must clear electronics.
        if name == 'brake_chassis_plate':
            continue
        for other, envelope in boxes.items():
            row = native_pair(shape, envelope, cfg['minimum_envelope_gap_mm'], name, other)
            envelope_rows.append(row)
            if not row['pair_pass']:
                print('ELECTRONIC RESERVE REJECT', name, other, row, flush=True)
    display_bounds = []
    for part in scene['parts']:
        if part['name'] not in inventory['unmapped_display_names']:
            continue
        vertices = np.asarray(part['vertices']) if 'vertices' in part else np.load(R/part['geometry_npz'])['vertices']
        ab = vertices.min(0)*1000, vertices.max(0)*1000
        pcb_gap = aabb_gap(pcb_bounds, ab)
        display_bounds.append(dict(first='brake_pcb_draft', second=part['name'], conservative_display_gap_mm=pcb_gap,
                                   pair_pass=pcb_gap+1e-6>=cfg['minimum_envelope_gap_mm']))
        for name, shape in shapes.items():
            if name == 'brake_chassis_plate':
                continue
            gap = aabb_gap(new_bounds[name], ab)
            display_bounds.append(dict(first=name, second=part['name'], conservative_display_gap_mm=gap,
                                       pair_pass=gap+1e-6>=cfg['minimum_envelope_gap_mm']))
    original = import_brep(R/cfg['chassis']['source_brep'])
    chassis_subset = bounded_common(shapes['brake_chassis_plate'], original, 10)
    vol = shapes['brake_chassis_plate'].volume
    subset_pass = 'error' not in chassis_subset and abs(chassis_subset['volume_mm3']/vol-1)<1e-7
    hole_expected = 2*np.pi*1.6**2*3
    removed = kit['source_chassis_removed_volume_mm3']
    hole_pass = abs(removed/hole_expected-1)<1e-6
    positive = bounded_common(shapes['brake_thermal_plate'], shapes['brake_thermal_plate'], 10)
    positive_pass = 'error' not in positive and abs(positive['volume_mm3']/shapes['brake_thermal_plate'].volume-1)<1e-7
    wrong_offset = np.asarray(cfg['plate']['centre_mm'])-cfg['pcb']['draft_envelope_center_mm']
    fault = native_pair(shapes['brake_thermal_plate'], boxes['brake_pcb_draft'].translate(tuple(wrong_offset)), 2.,
                        'brake_thermal_plate', 'deliberately misplaced PCB')
    fault_pass = not fault['pair_pass'] and 'error' not in fault.get('common', {}) and fault['common']['volume_mm3']>.01
    static, extra = static_comparison(params)
    static_pass = all(x['cases']==63 and x['contact_feasible']==63 and x['all_static_torques_pass'] for x in static.values())
    fit_pass = all(x['pair_pass'] for x in cases+envelope_rows+display_bounds+pcb_retained)
    result = dict(schema='goose_brake_packaging_checks_v1', native_parts=integrity,
        native_bounding_pairs_clear=coarse_clear, exact_near_pairs=cases,
        electronics_allowance_pairs=envelope_rows, unmapped_display_aabb_pairs=display_bounds,
        pcb_retained_native_pairs=pcb_retained, pcb_native_bounding_pairs_clear=pcb_clear,
        raw_zero_pose_only=True, nominal_mating_does_not_ignore_positive_interference=True,
        source_chassis_subset=dict(common=chassis_subset, pass_subset=subset_pass,
            removed_volume_mm3=removed, expected_two_holes_volume_mm3=hole_expected, pass_holes=hole_pass),
        positive_common_control=dict(common=positive, pass_control=positive_pass),
        deliberate_misplacement=dict(pair=fault, pass_rejection=fault_pass),
        native_integrity_pass=all(x['boolean_input_integrity_pass'] for x in integrity),
        finite_packing_pass=fit_pass, static_screen_pass=static_pass, static=static,
        nominal_conditional_mass_kg=params['nominal_conditional_mass_kg'],
        delta_from_manual_wing_service_kg=params['delta_from_manual_wing_service_kg'],
        active_axes=18, electrical_release=False, thermal_release=False, manufacturing_release=False,
        continuous_sweep_pass=False, full_assembly_pass=False, frozen003_modified=False,
        limitations=['Raw zero-pose installation only; moving hip/neck, continuous service/tool/wire paths remain unqualified.',
            'Existing source integrity has two mouth timeouts and 29 unmapped display objects; the latter are screened by conservative mesh AABBs only.',
            'Main protection 93g remains an unclosed board/harness reserve. PCB envelope is not actual layout, mass or a manufactured board.',
            'Nominal purchased screw/nut envelopes omit thread preload and supplier tolerances; local no-overlap does not qualify fastening or heat flow.',
            'Static cases retain declared ideal contacts and existing actuator continuous limits; dynamics and actual actuator/thermal ratings remain separate.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+extra+[Path(__file__),
            ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py', ROOT/'src/sai_agent/native_cad_query.py']})
    result['limited_candidate_pass'] = fit_pass and static_pass and result['native_integrity_pass'] and subset_pass and hole_pass and positive_pass and fault_pass
    (R/'evidence/brake_packaging_checks.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PACKAGING', fit_pass, 'STATICS', static_pass, 'LIMITED CANDIDATE', result['limited_candidate_pass'], flush=True)
    for station, rows in static.items():
        print(station, sorted(rows['joint_summary'], key=lambda x:x['margin_nm'])[:2], flush=True)
    if not result['limited_candidate_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
