"""Same-version mass, axes and contacts for the unreleased hip carrier candidate.

This creates a separate SI ledger. It does not overwrite the published stage
two contract, prior native increment ledger or training model.
"""
from pathlib import Path
import argparse, copy, csv, hashlib, json, math, sys
import numpy as np
from scipy.spatial import ConvexHull
from scipy.linalg import eigvalsh

ROOT = Path(__file__).resolve().parents[2]; R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/models'), str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from compare_goose_native_skin_parameters import aggregate
from check_goose_native_fastener_stacks import stack


def fastener_rows(manifest, lift):
    rows = []
    # Length, washer, count, pierced plate thickness, permitted insertion,
    # minimum engagement; the stack uses the native nominal plate dimensions.
    specifications = [
        ('output_to_motor', 'hip_roll_output_adapter', 8., .5, 6, 4., 4.5, 3.),
        ('arm_to_adapter', 'hip_roll_carrier_arm', 10., 1., 3, 5.5, 4., 3.),
        ('arm_to_block', 'hip_roll_carrier_arm', 12., .5, 2, 5.5, 8., 5.),
        ('case_plate_to_block', 'hip_pitch_static_front_carrier', 10., .5, 2, 4., 6., 5.),
        ('case_plate_to_stator', 'hip_pitch_static_front_carrier', 8., 1., 6, 4., 4., 3.),
    ]
    parts = {p['name']: p for p in manifest['parts']}
    for a in manifest['assemblies']:
        side = a['side']
        for role, suffix, length, washer, count, plate, maximum, minimum in specifications:
            p = parts[side+'_'+suffix]
            engagement, ok = stack(length, [plate, washer], maximum, minimum)
            # Full solid shaft and oversized6x4mm head,7mmOD3.2mmID washer.
            volume = math.pi/4*(9*length+36*4+(49-3.2**2)*washer)
            rows.append(dict(assembly=side+'_hip_roll_to_pitch', role=role, body=side+'_hip_roll',
                thread='M3', length_mm=length, washer_mm=washer, count=count,
                clearance_stack_mm=[plate, washer], effective_engagement_mm=engagement,
                minimum_engagement_mm=minimum, maximum_insertion_mm=maximum, length_pass=ok,
                anchor_part=p['name'], center_world_m=(np.array(p['center_of_mass_world_m'])+[0, 0, lift]).tolist(),
                mass_upper_estimate_kg=volume*7850e-9*count, released=False))
    return rows


def configure_candidate(data):
    """Reconstruct the explicit SI geometry and ledger for bounded checks."""
    s = candidate()
    for n in s.pivots:
        s.pivots[n] = np.array(data['pivots_world_at_zero_m'][n])
    s.pivots['torso'] = np.zeros(3)  # static solver uses the world-origin root
    s.items = copy.deepcopy(data['items'])
    s.grip = np.array(data['grip_world_at_zero_m']); s.tip = np.array(data['tip_world_at_zero_m'])
    for side in ['right', 'left']:
        s.contact_hulls[side] = ConvexHull(data['contact_hulls'][side])
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skin-manifest', type=Path)
    args = parser.parse_args()
    paths = [R/'evidence/manufacturing_component_parameters.json',
             R/'cad/exports/hip_roll_carriers/manifest.json', R/'configs/stage_two_contract.json']
    old, carriers, contract = [json.loads(p.read_text()) for p in paths]
    replacement_skins = None
    if args.skin_manifest:
        paths.append(args.skin_manifest.resolve())
        replacement_skins = json.loads(paths[-1].read_text())
    s = candidate(); lift = old['rigid_coordinate_lift_m']
    for n in s.pivots:
        s.pivots[n] += [0, 0, lift]
    s.grip += [0, 0, lift]; s.tip += [0, 0, lift]
    s.items = copy.deepcopy(old['items'])
    if replacement_skins:
        names = {p['name'] for p in replacement_skins['parts']}
        assert len(names) == 6 and names <= {i['name'] for i in s.items}
        s.items = [i for i in s.items if i['name'] not in names]
        for p in replacement_skins['parts']:
            s.items.append(dict(name=p['name'], body='torso', mass_kg=p['mass_kg'],
                center_m=(np.array(p['center_of_mass_world_m'])+[0, 0, lift]).tolist(),
                inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
                basis='native lower hip arch skin candidate at1270kg/m3; original outerNURBS retained outside port'))
    for a in carriers['assemblies']:
        side = a['side']; shift = np.array(a['descendants_translation_world_mm'])/1000
        descendants = s.desc[side+'_hip_pitch']
        for n in descendants:
            s.pivots[n] += shift
        # The motor stator, root idler spider and rear root hardware belong to
        # hip_roll but are anchored at the moved hip_pitch axis. Body-only
        # selection would silently leave them behind.
        for i in s.items:
            anchored = i['name'] in [side+'_hip_pitch', side+'_hip_pitch_mount_reserve'] or i['name'].startswith(side+'_thigh_')
            if i['body'] in descendants or anchored:
                i['center_m'] = (np.array(i['center_m'])+shift).tolist()
        s.contact_hulls[side] = ConvexHull(np.array(old['contact_hulls'][side])+shift[:2])
    removed = [i for i in s.items if i['name'] in [side+'_hip_pitch_mount_reserve' for side in ['right', 'left']]]
    s.items = [i for i in s.items if i not in removed]
    consumed = []
    for i in s.items:
        if i['name'] in [side+'_hip_roll_structure_allocation' for side in ['right', 'left']]:
            amount = .01; ratio = (i['mass_kg']-amount)/i['mass_kg']
            i['mass_kg'] -= amount; i['inertia_at_com_kg_m2'] = (np.array(i['inertia_at_com_kg_m2'])*ratio).tolist()
            i['basis'] = 'retained10g harness/small hardware allowance after native roll-to-pitch adapter replacement'
            consumed.append(dict(name=i['name'], consumed_kg=amount, retained_kg=i['mass_kg']))
    for p in carriers['parts']:
        s.items.append(dict(name=p['name'], body=p['body'], mass_kg=p['mass_kg'],
            center_m=(np.array(p['center_of_mass_world_m'])+[0, 0, lift]).tolist(),
            inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
            basis='same-version native6061-T6 candidate volume at2700kg/m3; selected geometry, not measured mass'))
    rows = fastener_rows(carriers, lift)
    for row in rows:
        mass = row['mass_upper_estimate_kg']
        s.items.append(dict(name=row['assembly']+'_'+row['role']+'_fastener_bound', body=row['body'],
            mass_kg=mass, center_m=row['center_world_m'], inertia_at_com_kg_m2=(np.eye(3)*mass*.03**2/3).tolist(),
            relative_uncertainty=.1, basis='full screw/head/washer steel envelope; anchor COM and30mm isotropic gyration approximation'))
    hardware = dict(schema='goose_hip_carrier_fasteners_v1', rows=rows, total_screws=sum(r['count'] for r in rows),
        mass_upper_estimate_kg=sum(r['mass_upper_estimate_kg'] for r in rows), length_pass=all(r['length_pass'] for r in rows),
        manufacturing_pass=False, fastener_release=False,
        limitations=['19new screws per hip carrier; existing posterior hip-pitch idler screws are retained only once',
            'Engagement is a geometry check; screw grade, preload, material lot, fatigue and thread pullout remain unreleased'])
    hardware_path = R/'hardware/hip_roll_carrier_fasteners.json'
    hardware_path.write_text(json.dumps(hardware, indent=2)+'\n')
    fields = ['assembly', 'role', 'thread', 'length_mm', 'washer_mm', 'count', 'effective_engagement_mm', 'length_pass', 'released']
    with (R/'hardware/hip_roll_carrier_fasteners.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
    bodies = []
    for b in contract['bodies']:
        new = aggregate([i for i in s.items if i['body'] == b['name'] and i['name'] != 'specified_payload_50g'], s.pivots[b['name']])
        ir = eigvalsh(np.array(new['inertia_at_com_body_kg_m2']), np.array(b['inertia_at_com_body_kg_m2']))
        bodies.append(dict(name=b['name'], **new, relative_inertia_to_stage_two=ir.tolist()))
    pivots = {n: p.tolist() for n, p in s.pivots.items()}
    s.pivots['torso'] = np.zeros(3)
    cases = []
    for drop in [0, 40, 60, 80]:
        q, root, rot = s.pose(drop); cases.append(('crouch_'+str(drop), q, root, rot, ['right', 'left']))
    q, root, rot = s.pose(60, neck=True); cases.append(('low_reach', q, root, rot, ['right', 'left']))
    for side in ['right', 'left']:
        q, root, rot = s.pose(); q, root, rot = s.bank(side, q, root)
        cases.append((side+'_single_support', q, root, rot, [side]))
    results = []
    for scale in [-1, 0, 1]:
        model, _ = s.model(scale)
        for name, q, root, rot, supports in cases:
            for drag in [-2, 0, 2]:
                value = s.evaluate(name, q, root, rot, supports, scale, drag, model)
                value['joint_limit_violations'] = [j['name'] for j in contract['joints'] if not j['range_rad'][0] <= q[j['name']] <= j['range_rad'][1]]
                results.append(value)
    summary = []
    for j in contract['joints']:
        worst = max(results, key=lambda x: abs(x['joint_torque_nm'][j['name']]))
        torque = abs(worst['joint_torque_nm'][j['name']]); limit = j['continuous_design_limit_nm']
        summary.append(dict(joint=j['name'], worst_static_nm=torque, continuous_design_limit_nm=limit,
            margin_nm=limit-torque, case=worst['name'], mass_variant=worst['mass_variant'], drag_n=worst['drag_x_n'], pass_torque=torque <= limit))
    mass = sum(i['mass_kg'] for i in s.items if i['name'] != 'specified_payload_50g')
    joints = copy.deepcopy(contract['joints'])
    for j in joints:
        j['pivot_world_at_zero_m'] = pivots[j['name']]
    report = dict(schema='goose_hip_carrier_si_candidate_v1', hardware_freeze=False, new_training_release=False,
        old_model_modified=False, nominal_conditional_mass_kg=mass, previous_native_increment_mass_kg=old['nominal_conditional_mass_kg'],
        change_kg=mass-old['nominal_conditional_mass_kg'], rigid_coordinate_lift_m=lift,
        lower_hip_arch_skin_replacements=6 if replacement_skins else 0,
        pivots_world_at_zero_m=pivots, joints=joints, bodies=bodies, items=s.items,
        grip_world_at_zero_m=s.grip.tolist(), tip_world_at_zero_m=s.tip.tolist(),
        removed_allowance_items=removed, consumed_allocations=consumed, new_fastener_count=hardware['total_screws'],
        new_fastener_mass_bound_kg=hardware['mass_upper_estimate_kg'], native_carrier_mass_kg=sum(p['mass_kg'] for p in carriers['parts']),
        contact_hulls={side:s.contact_hulls[side].points[s.contact_hulls[side].vertices].tolist() for side in ['right', 'left']},
        static_cases=len(results), static_contact_feasible=sum(p['static_contact_feasible'] for p in results),
        all_static_within_continuous_limits=all(p['pass_torque'] for p in summary), joint_summary=summary, results=results,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[hardware_path, Path(__file__)]},
        limitations=['Conditional estimate with conservative screw bounds and retained reserves; not final hardware weight',
            '8mm distal leg translation changes both foot contact datum and SI axes; stage-two trained policies cannot be assumed compatible',
            'Static63case check does not release assembly clearances, local structure or demonstrate turning gait',
            'No new full simulation model/contract, electrical or hardware acceptance is inferred'])
    output = ('hip_clearance_wide_component_parameters.json' if args.skin_manifest.parent.name=='hip_clearance_skins_wide' else 'hip_clearance_component_parameters.json') if args.skin_manifest else 'hip_carrier_component_parameters.json'
    (R/'evidence'/output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['nominal_conditional_mass_kg', 'change_kg', 'static_cases', 'static_contact_feasible', 'all_static_within_continuous_limits']}, indent=2))
    print([p for p in summary if not p['pass_torque']])
    return 0 if report['all_static_within_continuous_limits'] and report['static_contact_feasible'] == len(results) and hardware['length_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
