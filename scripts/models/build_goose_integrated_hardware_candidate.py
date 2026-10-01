"""One traceable assembly/parameter candidate from four current increments.

Preserves default344-part assets and model. This supplies a common419-part
geometry and closed-pose19-body inertial/static ledger, NOT stale collisions
or a new dynamics/training release. Existing reserves remain explicit.
"""
from pathlib import Path
import copy
import csv
import hashlib
import json
import sys

import numpy as np
import mujoco
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/models'))
from build_goose_stage_two import candidate
from sai_agent.goose.mass_properties import aggregate_rigid_components


def opposed_clamp_result(system, model, result, force_n):
    """Re-evaluate only the declared opposed force from evaluator's fixed50N.

    Loads cancel above the jaw. Analytic virtual work is checked against a
    fresh MuJoCo generalized-force Jacobian, not by changing torque limits.
    Contact wrench/COM/FK do not change because this is an internal force pair.
    """
    row = copy.deepcopy(result)
    q, root = row['joint_q_rad'], np.array(row['root_position_m'])
    w,x,y,z = row['root_quaternion_wxyz']
    rotation = Rotation.from_quat([x,y,z,w]).as_matrix()
    poses, axes = system.fk(q, root, rotation)
    grip = system.point(poses, 'head_roll', system.grip)
    difference = poses['head_roll'][1] @ np.array([0.,0.,force_n-50.])
    data = mujoco.MjData(model)
    data.qpos[:3], data.qpos[3:7] = root, row['root_quaternion_wxyz']
    for name, value in q.items():
        data.qpos[model.joint(name).qposadr] = value
    mujoco.mj_forward(model, data)
    delta = np.zeros(model.nv)
    loads = [('head_roll',difference), ('beak_hinge',-difference)]
    for body, force in loads:
        mujoco.mj_applyFT(model,data,force,np.zeros(3),grip,model.body(body).id,delta)
    errors = []
    for name in system.names:
        moment = sum((np.cross(grip-poses[name][0], force) for body,force in loads
                      if body in system.desc[name]), start=np.zeros(3))
        manual_change = -float(axes[name] @ moment)
        mujoco_change = -delta[int(model.joint(name).dofadr[0])]
        errors.append(abs(manual_change-mujoco_change))
        row['joint_torque_nm'][name] += manual_change
    if max(errors)>1e-9 or max(abs(delta[:6]))>1e-9:
        raise ValueError(('Opposed-force cancellation/Jacobian mismatch',errors,delta[:6]))
    row.update(opposed_clamp_force_n=force_n, original_evaluator_force_n=50.,
               opposed_force_change_jacobian_error_nm=max(errors),
               opposed_force_change_floating_base_residual=float(max(abs(delta[:6]))))
    return row


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ledger_path = ROBOT / 'evidence/body_bay_mechanical_parameters.json'
    scene_path = ROBOT / 'cad/source/mechanical_preview/scene.json'
    contract_path = ROBOT / 'configs/mechanical_physics_contract.json'
    old, old_scene, old_contract = [json.loads(p.read_text()) for p in [ledger_path, scene_path, contract_path]]
    paths = [ledger_path, scene_path, contract_path, Path(__file__), ROOT / 'src/sai_agent/goose/mass_properties.py']
    before_hashes = {str(p.relative_to(ROOT)): sha(p) for p in [ledger_path, scene_path, contract_path]}
    items = {i['name']: copy.deepcopy(i) for i in old['items'] if i['name'] != 'specified_payload_50g'}
    parts = {p['name']: copy.deepcopy(p) for p in old_scene['parts']}
    lift = old['rigid_coordinate_lift_m']
    deltas, removed = [], []
    increments = {}
    for folder in ['tip_grip_candidate', 'camera_carrier', 'power_module_mounts', 'compute_module_mounts']:
        mp = ROBOT / 'cad/exports' / folder / 'manifest.json'
        sp = ROBOT / 'cad/source' / folder / 'quad_scene.json'
        manifest, scene = [json.loads(p.read_text()) for p in [mp, sp]]
        paths += [mp, sp]
        increments[folder] = manifest
        for rel, expected in manifest['source_hashes'].items():
            if sha(ROOT / rel) != expected:
                raise ValueError(('Stale native increment', folder, rel))
        before = sum(i['mass_kg'] for i in items.values())
        for name in manifest['replaces_existing_parts']:
            if name not in items or name not in parts:
                raise ValueError(('Replacement is absent from current assembly and ledger', folder, name))
            removed.append(dict(name=name, by=folder, item=items.pop(name)))
            parts.pop(name)
        by_name = {p['name']: p for p in scene['parts']}
        for part in manifest['parts']:
            name = part['name']
            if name in parts:
                raise ValueError(('Duplicate installed name', name))
            for record in part['files'].values():
                if sha(ROBOT / record['path']) != record['sha256']:
                    raise ValueError(('Changed output', name, record['path']))
            parts[name] = copy.deepcopy(by_name[name])
            # These16 nominal pieces replace the existing four conservative
            # frame-stack bounds. Their mass is not added a second time.
            if folder == 'power_module_mounts' and name.startswith('neck_power_frame_'):
                continue
            if name in items:
                raise ValueError(('Duplicate mass item', name))
            items[name] = dict(name=name, body=part['body'], mass_kg=part['mass_kg'],
                center_m=(np.array(part['center_of_mass_world_m']) + [0,0,lift]).tolist(),
                inertia_at_com_kg_m2=part['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
                basis='Same-source native density/nominal hardware estimate; tolerances/material/strength not released')
        if folder == 'power_module_mounts':
            # Keep each old full stack upper bound; add the actual2mm longer
            # shaft segment at its own center. This retains the prior margin.
            m = np.pi * 1.5**2 * 2 * 7850e-9
            for i, xy in enumerate([(x,y) for x in [34,52] for y in [-34,34]]):
                name = 'neck_power_m3x18_extra_shaft_bound_' + str(i)
                radius, length = .0015, .002
                tensor = np.diag([m*(3*radius**2+length**2)/12]*2 + [m*radius**2/2])
                items[name] = dict(name=name, body='torso', mass_kg=m,
                    center_m=[xy[0]/1000, xy[1]/1000, .3109+lift],
                    inertia_at_com_kg_m2=tensor.tolist(), relative_uncertainty=.1,
                    basis='Additional2mmM3shaft density7850; old four full-stack mass bounds retained for replacements')
            for name, item in items.items():
                if name.startswith('neck_frame_through_screw_'):
                    item['basis'] += '; retained upper mass/inertia bound for replacementM3x18 stack; separate extra2mmshaft included'
        deltas.append(dict(folder=folder, mass_before_kg=before,
                           mass_change_kg=sum(i['mass_kg'] for i in items.values())-before))

    # Relocate retained mass reservations, rather than counting OEM material a
    # second time. Whole-box inertia is an explicit installation approximation.
    compute_path = ROBOT / 'configs/compute_module_mounts.json'
    paths.append(compute_path)
    compute_cfg = json.loads(compute_path.read_text())
    allocation = compute_cfg['proposed_compute_allocation_mm']
    compute = items['compute_stack']
    size = np.array(allocation['size'])/1000
    compute['center_m'] = (np.array(allocation['centre'])/1000 + [0,0,lift]).tolist()
    compute['inertia_at_com_kg_m2'] = np.diag(compute['mass_kg']*(sum(size*size)-size*size)/12).tolist()
    compute['basis'] += '; existing54g preserved at proposed36mm-high box; PCB/plug/harness mass split not released'
    camera = items['camera_module']
    bounds = np.array(increments['camera_carrier']['camera_layout']['complete_expanded_bounds_mm'])/1000
    size = bounds[1]-bounds[0]
    camera['center_m'] = ((bounds[1]+bounds[0])/2 + [0,0,lift]).tolist()
    camera['inertia_at_com_kg_m2'] = np.diag(camera['mass_kg']*(sum(size*size)-size*size)/12).tolist()
    camera['basis'] += '; retained25g at new complete supplier enclosing-box center; actual camera mass distribution unmeasured'
    mass = sum(i['mass_kg'] for i in items.values())
    if not np.isclose(mass, old['nominal_conditional_mass_kg']+sum(d['mass_change_kg'] for d in deltas), atol=1e-12):
        raise ValueError('Mass delta conservation failed')
    system = candidate()
    system.pivots = {k:np.array(v) for k,v in old['pivots_world_at_zero_m'].items()}
    system.items = list(items.values())
    system.grip = np.array(increments['tip_grip_candidate']['front_contact_native_world_m']) + [0,0,lift]
    system.tip = np.array(old['tip_world_at_zero_m'])
    system.contact_hulls = {k:ConvexHull(np.array(v)) for k,v in old['contact_hulls'].items()}
    system.contact_center_y_m = old['contact_center_y_m']
    bodies = [dict(name=b['name'], **aggregate_rigid_components(
        [i for i in items.values() if i['body']==b['name']], system.pivots[b['name']])) for b in old['bodies']]
    np.testing.assert_allclose(sum(b['mass_kg'] for b in bodies), mass, atol=1e-12)
    payload = copy.deepcopy(next(i for i in old['items'] if i['name']=='specified_payload_50g'))
    offset = np.array(old['native_grip_reference']['payload_reference_offset_m'])
    payload['center_m'] = (system.grip+offset).tolist()
    payload['basis'] = '50g static lump at candidate front contact, not actual grip/contact/dynamics evidence'
    system.items.append(payload)
    results, overload_results = [], []
    for variant in [-1,0,1]:
        model, _ = system.model(variant)
        for row in old['results']:
            if row['mass_variant'] != variant:
                continue
            name = row['name']
            support = ['right'] if name=='right_single_support' else ['left'] if name=='left_single_support' else ['right','left']
            q = row['joint_q_rad']
            w,x,y,z = row['root_quaternion_wxyz']
            rotation = Rotation.from_quat([x,y,z,w]).as_matrix()
            result = system.evaluate(name,q,np.array(row['root_position_m']),rotation,support,
                                     variant,row['drag_x_n'],model)
            result['joint_limit_violations'] = [j['name'] for j in old_contract['joints'] if
                not j['range_rad'][0] <= q[j['name']] <= j['range_rad'][1]]
            overload_results.append(copy.deepcopy(result))
            results.append(opposed_clamp_result(system,model,result,
                           increments['tip_grip_candidate']['front_design_clamp_force_n']))
    summary = []
    for joint in old_contract['joints']:
        worst = max(results,key=lambda row:abs(row['joint_torque_nm'][joint['name']]))
        value = abs(worst['joint_torque_nm'][joint['name']])
        limit = joint['continuous_design_limit_nm']
        summary.append(dict(joint=joint['name'], worst_static_nm=value, inherited_continuous_design_limit_nm=limit,
            margin_nm=limit-value, pass_torque=value<=limit, case=worst['name'], mass_variant=worst['mass_variant'],
            drag_x_n=worst['drag_x_n']))
    overload_failed = [dict(name=row['name'],mass_variant=row['mass_variant'],drag_x_n=row['drag_x_n'],
        beak_torque_nm=row['joint_torque_nm']['beak_hinge']) for row in overload_results if
        abs(row['joint_torque_nm']['beak_hinge']) > next(j['continuous_design_limit_nm'] for j in old_contract['joints'] if j['name']=='beak_hinge')]
    # Independent middle-station50N screen retains the same specified50g/2N
    # payload/drag cases but moves their application to the actual middle pad.
    system.grip = np.array(increments['tip_grip_candidate']['middle_contact_native_world_m']) + [0,0,lift]
    payload['center_m'] = (system.grip+offset).tolist()
    middle_results = []
    for variant in [-1,0,1]:
        model,_ = system.model(variant)
        for row in old['results']:
            if row['mass_variant'] != variant:
                continue
            name,q = row['name'],row['joint_q_rad']
            supports = ['right'] if name=='right_single_support' else ['left'] if name=='left_single_support' else ['right','left']
            w,x,y,z = row['root_quaternion_wxyz']
            result = system.evaluate(name,q,np.array(row['root_position_m']),Rotation.from_quat([x,y,z,w]).as_matrix(),
                                     supports,variant,row['drag_x_n'],model)
            result['opposed_clamp_force_n'] = increments['tip_grip_candidate']['middle_design_clamp_force_n']
            result['joint_limit_violations'] = [j['name'] for j in old_contract['joints'] if not
                j['range_rad'][0]<=q[j['name']]<=j['range_rad'][1]]
            middle_results.append(result)
    middle_summary = []
    for joint in old_contract['joints']:
        worst = max(middle_results,key=lambda r:abs(r['joint_torque_nm'][joint['name']]))
        value,limit = abs(worst['joint_torque_nm'][joint['name']]),joint['continuous_design_limit_nm']
        middle_summary.append(dict(joint=joint['name'],worst_static_nm=value,continuous_design_limit_nm=limit,
            margin_nm=limit-value,pass_torque=value<=limit,case=worst['name'],mass_variant=worst['mass_variant'],drag_x_n=worst['drag_x_n']))
    expected_delta = .00167319791563938+.003761624326889451+.0101218485775+.028991090856709603
    np.testing.assert_allclose(mass-old['nominal_conditional_mass_kg'],expected_delta,atol=1e-11)
    for rel, expected in before_hashes.items():
        if sha(ROOT/rel)!=expected:
            raise ValueError(('Default assembly overwritten',rel))
    if len(parts)!=419 or len(bodies)!=19 or len(results)!=63:
        raise ValueError(('Unexpected integration scope',len(parts),len(bodies),len(results)))
    source_hashes = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    ledger = dict(schema='goose_integrated_hardware_static_candidate_v1', status='INTEGRATED_GEOMETRY_AND_CLOSED_POSE_PARAMETERS_NOT_TRAINING_RELEASE',
        nominal_conditional_mass_kg=mass, delta_from_default_kg=mass-old['nominal_conditional_mass_kg'],
        rigid_coordinate_lift_m=lift, pivots_world_at_zero_m=old['pivots_world_at_zero_m'],
        items=list(items.values()), bodies=bodies, applied_increments=deltas, removed_items=removed,
        static_cases=len(results), static_results=results, joint_summary=summary,
        static_contact_feasible=sum(r['static_contact_feasible'] and not r['joint_limit_violations'] for r in results),
        all_static_torques_pass=all(r['pass_torque'] for r in summary),
        front_design_clamp_force_n=increments['tip_grip_candidate']['front_design_clamp_force_n'],
        middle_design_clamp_force_n=increments['tip_grip_candidate']['middle_design_clamp_force_n'],
        middle_static_results=middle_results, middle_joint_summary=middle_summary,
        middle_static_contact_feasible=sum(r['static_contact_feasible'] and not r['joint_limit_violations'] for r in middle_results),
        middle_all_static_torques_pass=all(r['pass_torque'] for r in middle_summary),
        front_50n_overload_results=overload_results, front_50n_overload_failures=overload_failed,
        compute_allocation_mm=allocation, retained_camera_mass_reservation_kg=.025,
        retained_compute_mass_reservation_kg=.054, retained_power_mass_reservations_kg=.065,
        camera_optical_front_world_m=(np.array(increments['camera_carrier']['camera_layout']['optical_front_native_world_mm'])/1000+[0,0,lift]).tolist(),
        front_grip_reference_world_m=(np.array(increments['tip_grip_candidate']['front_contact_native_world_m'])+[0,0,lift]).tolist(),
        middle_grip_reference_world_m=system.grip.tolist(), active_axes=18,
        neutral_joint_order=old_contract['joint_order'], backend_neutral_SI=True,
        compatibility={n:'Same geometry/closed-pose SI data only; new dynamics validation pending' for n in ['mujoco','godot_jolt','unity','bevy']},
        default_assembly_unchanged=True, default_source_hashes=before_hashes,
        new_collision_model_generated=False, manufacturing_release=False, full_assembly_pass=False,
        training_release=False, hardware_freeze=False, final_appearance_pass=False,
        source_hashes=source_hashes,
        limitations=['19 static body tensors aggregate linkage at zero; runtime must resplit the two passive jaw bodies and12soft-sole contacts.',
            'No model or hull from default344 geometry is released for this419part assembly; new same-version collisions/dynamics remain required.',
            'Radxa invalid main source remains unresolved13pairs; USB-CAN actual78.52x18.36mm plan exceeds old reserve.',
            'Camera mounting fasteners/plug/calibration, interface/power protection mounts, wiring, shell anchoring and whole strength are incomplete.',
            'Camera25g/compute54g/power65g and old frame-stack bounds retained, not spent; relocation inertias are explicit enclosing-box assumptions.',
            'Front20N/middle50N each63static cases with50g and+/-2N test existing support/torque assumptions, not walking/turning/pickup/drag proof or actual AK-A2hardware acceptance.',
            'Front50N overload fails inherited4.4Nm continuous beak design bound; it is explicitly retained, not the declared20Nfront operating target.',
            'New combined419part scene is a physical packaging candidate; appearance/materials/manufacturing approval pending.'])
    ledger_out = ROBOT / 'evidence/integrated_hardware_parameters.json'
    ledger_out.write_text(json.dumps(ledger,indent=2)+'\n')
    directory = ROBOT / 'cad/source/integrated_hardware_candidate'
    directory.mkdir(exist_ok=True)
    scene = dict(unit='m', status=ledger['status'], parts=list(parts.values()),
        assembly_translation_m=[0,0,lift], nominal_conditional_mass_kg=mass,
        manufacturing_pass=False, final_appearance_pass=False, whole_assembly_clearance_pass=False,
        default_assembly_unchanged=True, source_hashes=dict(source_hashes, **{str(ledger_out.relative_to(ROOT)):sha(ledger_out)}),
        scope='Current344parts plus real tip/camera/power/compute native candidates,419parts. Vendor circuits/plugs/harness remain omitted from display; original-fit gaps are explicit.')
    (directory/'scene.json').write_text(json.dumps(scene,separators=(',',':'))+'\n')
    csv_path = ROBOT / 'hardware/integrated_hardware_body_parameters.csv'
    with csv_path.open('w',newline='') as file:
        columns = ['body','mass_kg','com_x_m','com_y_m','com_z_m','ixx','iyy','izz','ixy','ixz','iyz']
        writer = csv.DictWriter(file,fieldnames=columns,lineterminator='\n')
        writer.writeheader()
        for body in bodies:
            c,t = body['com_local_m'], body['inertia_at_com_body_kg_m2']
            writer.writerow(dict(body=body['name'],mass_kg=body['mass_kg'],com_x_m=c[0],com_y_m=c[1],com_z_m=c[2],
                                 ixx=t[0][0],iyy=t[1][1],izz=t[2][2],ixy=t[0][1],ixz=t[0][2],iyz=t[1][2]))
    print('INTEGRATED HARDWARE',len(parts),'parts',mass,'kg',ledger['static_contact_feasible'],'/',len(results),
          'front contact;torques',ledger['all_static_torques_pass'], 'middle',ledger['middle_static_contact_feasible'],
          'torques',ledger['middle_all_static_torques_pass'],'front50Nfailures',len(overload_failed),flush=True)
    return 0 if (ledger['static_contact_feasible']==63 and ledger['all_static_torques_pass'] and
                 ledger['middle_static_contact_feasible']==63 and ledger['middle_all_static_torques_pass']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
