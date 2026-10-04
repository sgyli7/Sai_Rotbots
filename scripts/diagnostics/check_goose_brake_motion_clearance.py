"""Finite combined poses of moving hardware against the new fixed brake kit."""
from pathlib import Path
import hashlib
import itertools
import json
import sys
import time

import numpy as np
from build123d import import_brep

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/models'), str(ROOT/'scripts/diagnostics')]
from build_goose_cad import box, transform
from build_goose_stage_two import candidate
from check_goose_brake_packaging import aabb_gap, bounds, native_pair


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/p for p in ['configs/brake_packaging_candidate.json', 'cad/exports/brake_packaging/manifest.json',
        'evidence/brake_packaging_parameters.json', 'evidence/manual_wing_service_native_inventory.json',
        'cad/source/manual_wing_service/assembly_scene.json', 'evidence/integrated_hardware_parameters.json',
        'configs/mechanical_physics_contract.json']]
    cfg, kit, params, inventory, scene, poses, contract = [json.loads(p.read_text()) for p in paths]
    ledger_owner = {p['name']:p['body'] for p in params['items']}
    owners = {p['name']:(p['body'] if 'body' in p else ledger_owner[p['name']]) for p in scene['parts']}
    fixed = {}
    for part in kit['parts']:
        if part['name']=='brake_chassis_plate':
            continue
        file = part['files']['brep']
        if sha(R/file['path']) != file['sha256']:
            raise ValueError('Changed new kit')
        fixed[part['name']] = import_brep(R/file['path'])
    fixed['brake_pcb_draft'] = box(cfg['pcb']['draft_envelope_size_mm'], cfg['pcb']['draft_envelope_center_mm'])
    moving, moving_owner = {}, {}
    for rec in inventory['results']:
        body = owners[rec['name']]
        if body=='torso':
            continue
        path = R/rec['source']
        if sha(path) != rec['sha256']:
            raise ValueError('Changed retained moving part')
        moving[rec['name']] = import_brep(path)
        moving_owner[rec['name']] = body
        paths.append(path)
    # Mesh-only catalogue cases are explicit conservative native convex hulls
    # of retained displayed samples; never rewritten into manufactured CAD.
    from build123d import Solid
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    from build123d import Face, Wire, Vector
    from scipy.spatial import ConvexHull
    for part in scene['parts']:
        if part['name'] not in inventory['unmapped_display_names'] or owners[part['name']]=='torso':
            continue
        v = np.asarray(part['vertices']) if 'vertices' in part else np.load(R/part['geometry_npz'])['vertices']
        v = v*1000
        hull = ConvexHull(v)
        sewing = BRepBuilderAPI_Sewing(1e-6)
        for indices, equation in zip(hull.simplices, hull.equations):
            p = v[indices]
            if np.dot(np.cross(p[1]-p[0], p[2]-p[0]), equation[:3])<0:
                p = p[::-1]
            face = Face(Wire.make_polygon([Vector(*row) for row in p], close=True))
            sewing.Add(face.wrapped)
        sewing.Perform()
        from OCP.TopoDS import TopoDS
        shape = Solid(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid())
        if not shape.is_valid or shape.volume<=0:
            raise ValueError(('Invalid retained display hull',part['name']))
        moving[part['name']] = shape
        moving_owner[part['name']] = owners[part['name']]
    system = candidate()
    system.pivots = {k:np.asarray(v) for k,v in params['pivots_world_at_zero_m'].items()}
    for joint in contract['joints']:
        if not np.allclose(system.pivots[joint['name']], joint['pivot_world_at_zero_m'], atol=1e-12):
            raise ValueError(('Incompatible retained runtime pivot', joint['name']))
    for joint in contract.get('passive_linkage_joints', []):
        system.parents[joint['name']] = joint['parent']
        system.pivots[joint['name']] = np.asarray(joint['pivot_world_at_zero_m'])
        system.axes[joint['name']] = np.asarray(joint['axis_parent'])
    lift = np.array([0,0,params['rigid_coordinate_lift_m']])
    samples, seen = [], set()
    def add(name, q):
        if any(not np.isfinite(x) for x in q.values()):
            raise ValueError('Nonfinite pose')
        key = tuple(sorted((n,float(v)) for n,v in q.items() if abs(v)>1e-12))
        if key not in seen:
            samples.append((name, q));seen.add(key)
    add('raw_zero', {})
    for row in poses['static_results']:
        if row['mass_variant']==0:
            add(row['name'], row['joint_q_rad'])
    for side in ['right','left','both']:
        for yaw in [-np.pi/12,np.pi/12]:
            add(f'{side}_yaw_{yaw:.6f}', {s+'_hip_yaw':yaw for s in (['right','left'] if side=='both' else [side])})
    ranges = {j['name']:j['range_rad'] for j in contract['joints']}
    for side in ['right','left']:
        for yaw, roll in itertools.product(ranges[side+'_hip_yaw'], ranges[side+'_hip_roll']):
            add(f'{side}_yaw_roll_corner_{yaw}_{roll}', {side+'_hip_yaw':yaw,side+'_hip_roll':roll})
    reports = []
    fixed_bounds = {n:bounds(s) for n,s in fixed.items()}
    started = time.monotonic()
    for name,q in samples:
        articulated = dict(q)
        for joint in contract.get('passive_linkage_joints', []):
            articulated[joint['name']] = joint['mimic_multiplier']*q.get(joint['mimic_joint'], 0.)+joint['mimic_offset_rad']
        frames,_ = system.fk(articulated,root_p=system.pivots['torso'])
        transforms = {}
        for body in set(moving_owner.values()):
            p,rot = frames[body]
            # Native zero coordinates omit the one global lift. Rotate that
            # lift with the body before cancelling it in the fixed torso frame.
            offset = (p-rot@system.pivots[body]+rot@lift-lift)*1000
            if name=='raw_zero' and (not np.allclose(rot,np.eye(3),atol=1e-12) or not np.allclose(offset,0,atol=1e-8)):
                raise ValueError(('Zero-frame mismatch',body))
            transforms[body] = rot, offset
        near, clear = [], 0
        for other,source in moving.items():
            rot,offset = transforms[moving_owner[other]]
            shape = transform(source,rot,offset)
            ab = bounds(shape)
            for key, installed in fixed.items():
                if aabb_gap(ab,fixed_bounds[key])>=cfg['minimum_envelope_gap_mm']+1e-6:
                    clear += 1
                    continue
                near.append(native_pair(installed,shape,cfg['minimum_envelope_gap_mm'],key,other))
        passed = all(row['pair_pass'] for row in near)
        reports.append(dict(name=name,joint_q_rad=q,native_bounding_pairs_clear=clear,near_pairs=near,finite_pose_pass=passed))
        print('BRAKE MOTION',name,'near',len(near),'pass',passed,flush=True)
    result = dict(schema='goose_brake_motion_clearance_v1', fixed_shapes=len(fixed), moving_shapes=len(moving),
        sampled_poses=len(reports), cases=reports, finite_pose_pass=all(r['finite_pose_pass'] for r in reports),
        zero_fk_raw_coordinate_identity_pass=True, minimum_gap_mm=cfg['minimum_envelope_gap_mm'],
        wall_seconds=time.monotonic()-started, full_assembly_pass=False, continuous_sweep_pass=False,
        pcb_is_only_draft_envelope=True, simulation_collision_filters_used=False,
        unmapped_display_basis='Own closed convex hulls for clearance analysis only; not modified CAD or delivered runtime colliders.',
        passive_linkage_mimic_used=True,
        limitations=['Finite samples only; whole continuous coupled sweep, cable deformation and task trajectory remain separate.',
            'Passive input/coupler use the retained mechanical contract mimic and fixed pivot compatibility; real cable deformation and full local linkage fit remain separate.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__),
            ROOT/'scripts/cad/build_goose_cad.py', ROOT/'scripts/diagnostics/check_goose_brake_packaging.py',
            ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py', ROOT/'scripts/models/build_goose_stage_two.py',
            ROOT/'scripts/models/build_goose_stage_one.py', ROOT/'scripts/diagnostics/screen_goose_system_loads.py']})
    (R/'evidence/brake_motion_clearance.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['finite_pose_pass']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
