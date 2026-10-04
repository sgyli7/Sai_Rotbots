"""Finite service mechanism checks and same-candidate whole-body statics.

Not a continuous swept-volume proof or whole robot assembly/dynamics release.
The pins/nuts remain; removable closure screw/washer are absent while opening.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import numpy as np
import trimesh
from build123d import Axis, import_brep
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/models'), str(ROOT/'scripts/diagnostics')]
from sai_agent.native_cad_query import native_solid_integrity
from check_goose_grip_cassettes import bounded_common
from build_goose_stage_two import candidate
from build_goose_integrated_hardware_candidate import opposed_clamp_result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/p for p in ['configs/manual_wing_service.json',
        'cad/exports/manual_wing_service/manifest.json', 'evidence/manual_wing_service_parameters.json',
        'evidence/integrated_hardware_parameters.json', 'evidence/body_bay_mechanical_parameters.json',
        'configs/mechanical_physics_contract.json', 'cad/exports/torso_shell_mounts/manifest.json']]
    cfg, kit, params, poses_source, default, contract, roof = [json.loads(p.read_text()) for p in paths]
    for data in [kit, params]:
        for rel, digest in data['source_hashes'].items():
            if sha(ROOT/rel) != digest:
                raise ValueError(('Stale candidate input', rel))
    shapes, integrity, quad = {}, [], []
    for rec in kit['parts']:
        for file in rec['files'].values():
            if sha(R/file['path']) != file['sha256']:
                raise ValueError('Changed candidate part')
        bp = R/rec['files']['brep']['path']
        paths.append(bp)
        shape = import_brep(bp)
        check = native_solid_integrity(shape)
        if not check['boolean_input_integrity_pass']:
            raise ValueError(('Unhealthy exported part', rec['name'], check))
        integrity.append(dict(name=rec['name'], **check))
        shapes[rec['name']] = shape
        qp = R/rec['files']['npz']['path']
        arrays = np.load(qp)
        v, f = arrays['vertices'], arrays['faces']
        if f.shape[1] != 4:
            raise ValueError('Non-quad editable sample')
        mesh = trimesh.Trimesh(v, np.concatenate([f[:, [0,1,2]], f[:, [0,2,3]]]), process=False)
        error = abs(mesh.volume*1e9/rec['volume_mm3']-1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or error > .005:
            raise ValueError(('Bad quad/native exchange', rec['name'], error))
        quad.append(dict(name=rec['name'], all_quad=True, closed=True, faces=len(f), volume_relative_error=error))
    service, controls = [], []
    for label, side in [('right', -1), ('left', 1)]:
        door = shapes['wing_manual_door_'+label]
        control = bounded_common(door, door, 12)
        native_volume = next(p['volume_mm3'] for p in kit['parts'] if p['name'] == 'wing_manual_door_'+label)
        passed = 'error' not in control and abs(control['volume_mm3']/native_volume-1) < .001
        controls.append(dict(side=label, common=control, native_volume_mm3=native_volume, positive_control_pass=passed))
        if not passed:
            raise ValueError(('Common positive control failed', label))
        y, z = cfg['axis_right_yz_mm']
        for angle in cfg['finite_service_angles_deg']:
            pose = door.rotate(Axis((0, -side*y, z), (1,0,0)), side*angle)
            for end in ['aft', 'fore']:
                fixed = shapes['torso_manual_shell_'+label+'_'+end]
                common = bounded_common(pose, fixed, 12)
                gap = float(pose.distance_to(fixed)) if 'error' not in common else None
                passed = 'error' not in common and common['volume_mm3'] < 1e-5 and gap >= cfg['minimum_finite_service_gap_mm']
                service.append(dict(side=label, angle_deg=angle, fixed=end, common=common,
                    gap_mm=gap, finite_pose_pass=passed))
                print('SERVICE FIT', label, angle, end, passed, gap, flush=True)
    # Retained metal roof carriers against the four actual new fixed skins;
    # torso-fixed relationships are invariant to active robot configuration.
    roof_fit = []
    for interface in roof['interfaces']:
        name = interface['roof_carrier']
        rec = next(p for p in roof['parts'] if p['name'] == name)
        file = rec['files']['brep'];bp = R/file['path']
        if sha(bp) != file['sha256']:
            raise ValueError('Changed retained roof carrier')
        paths.append(bp)
        carrier = import_brep(bp)
        for label in ['right', 'left']:
            for end in ['aft', 'fore']:
                fixed_name = 'torso_manual_shell_'+label+'_'+end
                fixed = shapes[fixed_name]
                a, b = carrier.bounding_box(optimal=False), fixed.bounding_box(optimal=False)
                disjoint = any(min(i,j)-max(k,l) <= 1e-7 for i,j,k,l in zip(a.max,b.max,a.min,b.min))
                common = dict(volume_mm3=0., method='Complete native bounds disjoint') if disjoint else bounded_common(carrier, fixed, 12)
                roof_fit.append(dict(carrier=name, shell=fixed_name, common=common,
                    limited_pair_pass='error' not in common and common['volume_mm3'] < .01))
    system = candidate()
    system.pivots = {k:np.array(v) for k,v in params['pivots_world_at_zero_m'].items()}
    system.items = copy.deepcopy(params['items'])
    system.contact_hulls = {k:ConvexHull(np.array(v)) for k,v in default['contact_hulls'].items()}
    system.contact_center_y_m = default['contact_center_y_m']
    system.tip = np.array(default['tip_world_at_zero_m'])
    payload = copy.deepcopy(next(p for p in default['items'] if p['name'] == 'specified_payload_50g'))
    system.items.append(payload)
    static = {}
    for station, point, force in [('front20n', poses_source['front_grip_reference_world_m'], 20.),
                                  ('middle50n', poses_source['middle_grip_reference_world_m'], 50.)]:
        system.grip = np.array(point)
        payload['center_m'] = (system.grip+np.array(default['native_grip_reference']['payload_reference_offset_m'])).tolist()
        results = []
        for variant in [-1,0,1]:
            model, _ = system.model(variant)
            for row in poses_source['static_results']:
                if row['mass_variant'] != variant:
                    continue
                w,x,y,z = row['root_quaternion_wxyz']
                support = ['right'] if row['name'] == 'right_single_support' else ['left'] if row['name'] == 'left_single_support' else ['right','left']
                result = system.evaluate(row['name'], row['joint_q_rad'], np.array(row['root_position_m']),
                    Rotation.from_quat([x,y,z,w]).as_matrix(), support, variant, row['drag_x_n'], model)
                if force != 50:
                    result = opposed_clamp_result(system, model, result, force)
                results.append(result)
        summary = []
        for joint in contract['joints']:
            worst = max(abs(row['joint_torque_nm'][joint['name']]) for row in results)
            limit = joint['continuous_design_limit_nm']
            summary.append(dict(joint=joint['name'], worst_nm=worst, limit_nm=limit,
                margin_nm=limit-worst, pass_torque=worst <= limit))
        static[station] = dict(cases=len(results), results=results, joint_summary=summary,
            contact_feasible=sum(row['static_contact_feasible'] for row in results),
            all_static_torques_pass=all(row['pass_torque'] for row in summary))
    service_pass = all(row['finite_pose_pass'] for row in service)
    roof_pass = all(row['limited_pair_pass'] for row in roof_fit)
    static_pass = all(row['contact_feasible'] == 63 and row['all_static_torques_pass'] for row in static.values())
    paths += [Path(__file__), ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py',
              ROOT/'scripts/models/build_goose_stage_two.py', ROOT/'scripts/models/build_goose_integrated_hardware_candidate.py',
              ROOT/'src/sai_agent/native_cad_query.py']
    result = dict(schema='goose_manual_wing_service_checks_v1', native_parts=integrity, quad_exchange=quad,
        positive_controls=controls, finite_service_pairs=service, roof_carrier_pairs=roof_fit, static=static,
        finite_service_pair_pass=service_pass, finite_roof_carrier_pair_pass=roof_pass, static_screen_pass=static_pass,
        nominal_conditional_mass_kg=params['nominal_conditional_mass_kg'], delta_from460_kg=params['delta_from460_kg'],
        active_axes=18, same_source_limited_checkpoint_pass=service_pass and roof_pass and static_pass,
        continuous_service_sweep_proved=False, full_assembly_pass=False, manufacturing_release=False,
        electrical_release=False, dynamics_release=False, frozen003_modified=False,
        limitations=['Seven sampled service angles per door, only against same-side aft/fore skins; continuous sweep and full frame/wiring/electronics service path not qualified.',
            'Roof carrier checks cover these named torso-fixed pairs only.',
            'Static screen inherits declared ideal contact/material/continuous limits; dynamic/thermal/real-material claims remain separate.',
            'Purchased fasteners use own nominal envelopes; as-printed insert pilots are not installed interference qualification.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths})
    out = R/'evidence/manual_wing_service_checks.json'
    out.write_text(json.dumps(result, indent=2)+'\n')
    print('LIMITED CHECKPOINT', result['same_source_limited_checkpoint_pass'], 'mass', result['nominal_conditional_mass_kg'], flush=True)
    if not result['same_source_limited_checkpoint_pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
