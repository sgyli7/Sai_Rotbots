"""Project the actual recorded pickup trial through a catalog camera candidate.

This is offline geometry evidence. The original controller used no camera;
do not call the recorded manipulation a visually controlled autonomous task.
"""
from pathlib import Path
import hashlib
import json
import time

import mujoco
import numpy as np
from build123d import import_brep
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
from scipy.spatial.transform import Rotation
from sai_agent.goose.double_support import NominalDoubleSupport

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    layout_file = ROBOT/'evidence/camera_catalog_layout.json'
    frame_file = ROBOT/'cad/exports/camera_carrier/manifest.json'
    cycle_file = ROBOT/'evidence/supported_manipulation_cycle_contract_constant_pitch.json'
    contract_file = ROBOT/'configs/tip_grip_physics_contract.json'
    ledger_file = ROBOT/'evidence/body_bay_mechanical_parameters.json'
    layout, carrier, cycle, contract, ledger = [json.loads(p.read_text()) for p in
        [layout_file, frame_file, cycle_file, contract_file, ledger_file]]
    run = ROOT/'artifacts/Goose_V0.1/supported_manipulation_cycle_contract_constant_pitch'
    xml, trajectory = run/'task.xml', run/'sampled_qpos.npz'
    if sha(xml) != cycle['task_xml_sha256'] or sha(trajectory) != cycle['sampled_qpos_sha256']:
        raise ValueError('recorded trial identity mismatch')
    for record in [layout, carrier, cycle]:
        for rel, expected in record['source_hashes'].items():
            if sha(ROOT/rel) != expected:
                raise ValueError(('stale geometry or trial source', rel))
    if carrier['camera_layout'] != layout['selected']:
        raise ValueError('camera carrier and projected layout must be identical')
    optical_native = np.array(layout['selected']['optical_front_native_world_mm'])
    down_deg = layout['selected']['optical_pitch_down_in_head_deg']
    camera_r = Rotation.from_euler('y', down_deg, degrees=True).as_matrix()
    head_zero = np.array(next(j['pivot_world_at_zero_m'] for j in contract['joints'] if j['name']=='head_roll'))
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    native_pivot_mm = (head_zero-lift)*1000
    inputs = [ROBOT/'cad/source/tip_grip_candidate'/(n+'.brep') for n in
        ['upper_grip_shell', 'upper_grip_carrier', 'upper_grip_cassette_pad']]
    inputs += [ROBOT/'cad/source/bill_backbones/head_bill_access_shell_left.brep',
               ROBOT/'cad/source/jaw_retention/head_retention_access_shell_right.brep']
    inputs += [ROBOT/p['files']['brep']['path'] for p in carrier['parts']]
    intersectors = {}
    for path in inputs:
        shape = import_brep(path)
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(('invalid optical occluder', path))
        tester = IntCurvesFace_ShapeIntersector()
        tester.Load(shape.wrapped, 1e-7)
        intersectors[path.stem] = tester
    model = mujoco.MjModel.from_xml_path(str(xml))
    data = mujoco.MjData(model)
    head, obj = model.body('head_roll').id, model.body('floor_50g_object').id
    qadr = np.array([model.joint(n).qposadr[0] for n in contract['joint_order']])
    helper = NominalDoubleSupport(contract, ledger['contact_center_y_m'], ledger['contact_hulls'])
    limits = np.array([j['continuous_design_limit_nm'] for j in contract['joints']])
    native_part_by_geom = {g['name']:g['part'] for g in contract['collision_geometries']}
    size = np.array(cycle['object_size_m'])
    offsets = np.vstack([np.zeros(3), np.array([[x, y, z] for x in [-1,1] for y in [-1,1] for z in [-1,1]])*size/2])
    times = np.load(trajectory)
    hfov, vfov, minimum_focus_m = 65., 51., .10
    timer = time.monotonic()

    def project(label, time_s, qpos):
        data.qpos[:] = qpos
        mujoco.mj_forward(model, data)
        head_r = data.xmat[head].reshape(3,3)
        camera_world = data.xpos[head]+head_r@(optical_native/1000+lift-head_zero)
        camera_world_r = head_r@camera_r
        world_points = data.xpos[obj]+(data.xmat[obj].reshape(3,3)@offsets.T).T
        records = []
        for index, point in enumerate(world_points):
            delta = camera_world_r.T@(point-camera_world)
            distance = float(np.linalg.norm(delta))
            inside = bool(delta[0] > 0 and abs(delta[1]/delta[0]) <= np.tan(np.deg2rad(hfov/2)) and
                          abs(delta[2]/delta[0]) <= np.tan(np.deg2rad(vfov/2)))
            native_target = head_r.T@(point-data.xpos[head])*1000+native_pivot_mm
            segment = native_target-optical_native
            ray_length_mm = float(np.linalg.norm(segment))
            line = gp_Lin(gp_Pnt(*map(float, optical_native)), gp_Dir(*map(float, segment/ray_length_mm)))
            hits = []
            for name, tester in intersectors.items():
                tester.Perform(line, .001, ray_length_mm-.001)
                if not tester.IsDone():
                    raise ValueError(('native optical ray did not complete', label, index, name))
                if tester.NbPnt():
                    hits.append(dict(part=name, first_distance_mm=min(tester.WParameter(i+1) for i in range(tester.NbPnt()))))
            focus = distance >= minimum_focus_m
            records.append(dict(point='center' if index==0 else 'corner_'+str(index),
                camera_coordinates_m=delta.tolist(), range_m=distance, inside_catalog_fov=inside,
                meets_current_page_nominal_focus_distance=bool(focus), native_occluders=hits,
                geometric_visibility=bool(inside and focus and not hits)))
        phase = min(cycle['records'], key=lambda r:abs(r['time_s']-time_s))['phase'] if time_s is not None else label
        return dict(label=label, time_s=time_s, phase=phase, camera_world_m=camera_world.tolist(),
            actual_object_center_world_m=data.xpos[obj].tolist(), points=records,
            center_geometrically_visible=records[0]['geometric_visibility'],
            all_nine_points_geometrically_visible=all(p['geometric_visibility'] for p in records))

    # A separate geometric scan pose uses the unchanged head-pitch actuator;
    # its dynamics and complete whole-body swept clearances are not validated.
    scans = []
    for head_pitch in [.65, .85, 1.05]:
        scan_q = model.qpos0.copy()
        scan_q[model.joint('head_pitch').qposadr[0]] = head_pitch
        scan = project('candidate_head_pitch_scan_pose', None, scan_q)
        scan['head_pitch_rad'] = head_pitch
        collisions = []
        for contact in data.contact:
            geom_names = [model.geom(int(g)).name for g in contact.geom]
            if contact.dist < -.0002 and not any(n in ['ground', 'floor_50g_object'] for n in geom_names):
                collisions.append(dict(geoms=geom_names, parts=[native_part_by_geom.get(n,n) for n in geom_names],
                    signed_distance_m=float(contact.dist)))
        estimate = helper.estimate(data.qpos[qadr], data.qpos[3:7])
        torque = estimate['torque_nm']
        scan['unchanged_physics_model_self_contacts_below_minus_0p2mm'] = collisions
        scan['nominal_support_feasible'] = estimate['nominal_support_feasible']
        scan['unchanged_model_nominal_static_torque_nm'] = dict(zip(contract['joint_order'], torque.tolist()))
        scan['unchanged_model_nominal_static_continuous_limits_pass'] = bool(np.all(abs(torque) <= limits))
        scan['new_camera_geometry_in_physics_model'] = False
        scans.append(scan)
    passing_scans = [s for s in scans if s['all_nine_points_geometrically_visible'] and
        not s['unchanged_physics_model_self_contacts_below_minus_0p2mm'] and
        s['nominal_support_feasible'] and s['unchanged_model_nominal_static_continuous_limits_pass']]
    selected_scan = min(passing_scans, key=lambda s:s['head_pitch_rad']) if passing_scans else None
    rows = []
    for i, seconds in enumerate(times['time_s']):
        if time.monotonic()-timer > 120.:
            raise ValueError('native camera-view time bound; partial rays are not a passed task')
        rows.append(project('recorded_free_trial', float(seconds), times['qpos'][i]))
    approach = [r for r in rows if r['phase']=='approach']
    visible_approach = [r for r in approach if r['center_geometrically_visible']]
    last_visible = visible_approach[-1] if visible_approach else None
    clamp = [r for r in rows if r['phase']=='clamp']
    summary = dict(recorded_frames=len(rows), geometrically_visible_center_frames=sum(r['center_geometrically_visible'] for r in rows),
        approach_center_visible_frames=len(visible_approach), last_center_visible_approach_sample=last_visible,
        clamp_center_visible_frames=sum(r['center_geometrically_visible'] for r in clamp),
        clamp_sample_count=len(clamp), candidate_scan_count=len(scans),
        candidate_all_points_visible_scan_count=len(passing_scans),
        selected_scan_head_pitch_rad=selected_scan['head_pitch_rad'] if selected_scan else None)
    value = dict(schema='goose_camera_recorded_task_view_v1', status='COMPLETE_RECORDED_FINITE_VIEW_CHECK',
        summary=summary, finite_scan_poses=scans, selected_geometric_scan=selected_scan, records=rows,
        optical_front_native_world_mm=optical_native.tolist(), optical_axis_down_in_head_deg=down_deg,
        catalog_hfov_deg=hfov, catalog_vfov_deg=vfov, catalog_page_minimum_focus_m=minimum_focus_m,
        camera_procurement_candidate='B0471-1', camera_installed=False,
        camera_used_by_original_controller=False, ideal_pinhole_projection_only=True,
        complete_visual_autonomy_pass=False, manufacturing_pass=False, training_release=False,
        wall_seconds=time.monotonic()-timer,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in
            [Path(__file__), layout_file, frame_file, cycle_file, contract_file, ledger_file, xml, trajectory]+inputs},
        sources=layout['sources'], limitations=[
            'Offline projection uses actual recorded free-root/head/object poses; it does not rerun or alter dynamics or introduce camera feedback.',
            'Occlusion rays use eight named exact native head-owned solids. Moving lower-jaw/rotor, body, cables, module housing and scene occlusion are additional gates.',
            'Supplier65x51deg FoV and current-page10cm focus are nominal;2023 PDF focus discrepancy, active video crop, autofocus latency and calibration remain unresolved.',
            'Center plus eight bounding-box corner rays do not prove surface visibility or recognition under actual lighting.',
            'Scan checks unchanged full collision model and unchanged nominal support torques only. New camera geometry/mass is not in that physics model; scan dynamics and full native assembly swept clearances remain gates.',
            'During a close approach an invisible or out-of-focus object requires validated localization/tactile control; no arbitrary-object autonomy claim follows.'])
    (ROBOT/'evidence/camera_recorded_task_view.json').write_text(json.dumps(value,indent=2)+'\n')
    print('CAMERA VIEW SUMMARY', json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
