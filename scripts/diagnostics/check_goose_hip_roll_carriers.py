"""Installed native roll/pitch candidate screen; never a whole-robot release.

Vendor STEP is a surface assembly, not a closed solid. Its zero common volume
would NOT prove clearance. Exact surface distances are recorded separately;
conservative closed stator envelopes screen solid interference.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, sys
import numpy as np
from build123d import import_step
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/models'), str(ROOT/'scripts/diagnostics')]
from build_goose_cad import transform, cylinder, box
from build_goose_stage_two import candidate
from sai_agent.native_cad import common_solid_volume_mm3 as overlap

SHIFT = np.array([.008, 0., 0.])
ROLL_ROTATION = np.array([[0., 1., 0.], [1., 0., 0.], [0., 0., -1.]])


def boolean_regression():
    rows = []
    for offset, expected in [(0., 1000.), (5., 500.), (10., 0.)]:
        for angle in [0., -.6, .6]:
            rot = Rotation.from_rotvec([.17, -.29, angle]).as_matrix()
            a = transform(box([10, 10, 10]), rot, [23, -15, 90])
            b = transform(box([10, 10, 10], [offset, 0, 0]), rot, [23, -15, 90])
            result = overlap(a, b)
            if abs(result-expected) > 1e-6:
                raise ValueError(('independent analytical common-volume regression', expected, result))
            rows.append(dict(offset_mm=offset, common_rigid_rotation_rad=angle,
                analytical_volume_mm3=expected, computed_volume_mm3=result))
    return rows


def load_native(manifest, shift_distal=False):
    shapes, owners = {}, {}
    for p in manifest['parts']:
        for f in p['files'].values():
            assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest() == f['sha256']
        shape = import_step(R/p['files']['step']['path'])
        assert shape.is_valid and len(shape.solids()) == 1, p['name']
        shape = shape.solids()[0]
        t = p.get('world_from_local_mm')
        if t:
            shape = transform(shape, np.array(t['rotation']), np.array(t['translation']))
        if shift_distal and any(p['name'].startswith(side+'_'+segment) for side in ['right', 'left'] for segment in ['thigh_', 'shin_']):
            shape = transform(shape, np.eye(3), SHIFT*1000)
        shapes[p['name']] = shape
        owners[p['name']] = p.get('body', 'head_roll' if p['name'].startswith('goose_head_shell') else 'torso')
    return shapes, owners


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skin-manifest', type=Path)
    args = parser.parse_args()
    regression = boolean_regression()
    paths = [R/('cad/exports/'+folder+'/manifest.json') for folder in
             ['hip_roll_carriers', 'pitch_fork_assembly', 'compliant_foot', 'manufacturing_skins']]
    manifests = [json.loads(p.read_text()) for p in paths]
    if args.skin_manifest:
        paths.append(args.skin_manifest.resolve())
        manifests.append(json.loads(paths[-1].read_text()))
    s = candidate()
    old_pivots = {n: p.copy() for n, p in s.pivots.items()}
    for side in ['right', 'left']:
        for n in s.desc[side+'_hip_pitch']:
            s.pivots[n] += SHIFT
    native, owners = {}, {}
    for index, manifest in enumerate(manifests):
        shapes, own = load_native(manifest, shift_distal=index == 1)
        if index == 2:
            shapes = {n: transform(shape, np.eye(3), SHIFT*1000) for n, shape in shapes.items()}
        native.update(shapes); owners.update(own)
    carrier_names = {p['name'] for p in manifests[0]['parts']}
    for side in ['right', 'left']:
        for suffix in ['hip_roll', 'hip_pitch', 'knee_pitch', 'ankle_pitch']:
            n = side+'_'+suffix
            rot = ROLL_ROTATION if suffix == 'hip_roll' else (np.eye(3) if side == 'left' else np.diag([1., -1., -1.]))
            # Conservative stator is only rear -28.25..front25.25. Treating
            # the entire 56.5mm tip envelope as stator falsely blocks rings.
            local = cylinder(27.5, 53.5, [0., -1.5, 0.], 'y')
            # Official output pilot socket18mm,1.5mm deep from26.25mm.
            # Part of the socket extends0.5mm into the conservative stator
            # cylinder; retain this real seating recess rather than treating
            # an intentionally installed adapter pilot as a collision.
            local -= cylinder(9., 1.5, [0., 25.5, 0.], 'y')
            native[n+'_stator_envelope'] = transform(local, rot, s.pivots[n]*1000)
            owners[n+'_stator_envelope'] = s.parents[n]
    cases = [('zero', {})]
    for side in ['right', 'left']:
        for suffix, extent in [('hip_yaw', .6), ('hip_roll', .5), ('hip_pitch', 1.1)]:
            for value in [-extent, extent]:
                n = side+'_'+suffix; cases.append((n+'_'+str(value), {n: value}))
        for yaw, roll, pitch in itertools.product([-.6, .6], [-.5, .5], [-1.1, 1.1]):
            q = {side+'_hip_yaw':yaw, side+'_hip_roll':roll, side+'_hip_pitch':pitch}
            cases.append((side+'_combined_'+str((yaw, roll, pitch)), q))
    reports = []
    for name, q in cases:
        poses, _ = s.fk(q, root_p=s.pivots['torso'])
        installed = {}
        for n, shape in native.items():
            body = owners[n]; pos, rot = poses[body]
            installed[n] = transform(shape, rot, (pos-rot@s.pivots[body])*1000)
        collisions = []; tested = 0
        # These pairs test the NEW carriers against the full available native
        # assembly, including opposite limb. Old-old pairs are outside scope.
        for a, b in itertools.combinations(installed, 2):
            if a not in carrier_names and b not in carrier_names:
                continue
            tested += 1; volume = overlap(installed[a], installed[b])
            if volume > .01:
                collisions.append(dict(a=a, b=b, intersection_mm3=volume,
                    basis='conservative_stator_envelope' if 'stator_envelope' in (a+b) else 'native_solid'))
        reports.append(dict(name=name, q_rad=q, tested_pairs=tested, collisions=collisions,
                            pass_no_screened_interference=not collisions))
        print(name, 'interferences', len(collisions), flush=True)
    vendor_path = ROOT/'.scratch/stage_three/ak45_36/AK45-36 V3.0 KV80.STEP'
    vendor_checks = []; old_gap = None
    if vendor_path.exists():
        raw = import_step(vendor_path)
        # Official drawing/CAD bbox normalization, not geometry repair.
        raw = transform(raw, np.eye(3), [0., -8.75, 0.])
        for side in ['right', 'left']:
            rot = np.eye(3) if side == 'left' else np.diag([1., -1., -1.])
            child = transform(raw, rot, s.pivots[side+'_hip_pitch']*1000)
            for suffix in ['hip_roll_output_adapter', 'hip_roll_carrier_arm', 'hip_roll_corner_block']:
                n = side+'_'+suffix
                gap = float(native[n].distance_to(child))
                vendor_checks.append(dict(part=n, motor=side+'_hip_pitch', exact_surface_gap_mm=gap,
                    pass_gap=gap >= 1., vendor_is_closed_solid=bool(raw.solids())))
            old_child = transform(raw, rot, old_pivots[side+'_hip_pitch']*1000)
            gap = float(native[side+'_hip_roll_output_adapter'].distance_to(old_child))
            if side == 'right': old_gap = gap
    report = dict(schema='goose_hip_roll_carrier_screen_v1', distal_leg_x_shift_m=SHIFT.tolist(),
        parts=len(carrier_names), assembly_native_parts=len(native)-8,
        screened_pose_count=len(reports), cases=reports, vendor_surface_checks=vendor_checks,
        analytical_boolean_regression=regression,
        old_adapter_to_child_vendor_gap_mm=old_gap,
        partial_native_interference_pass=all(p['pass_no_screened_interference'] for p in reports),
        selected_vendor_gap_pass=bool(vendor_checks) and all(p['pass_gap'] for p in vendor_checks),
        full_assembly_pass=False, manufacturing_pass=False, new_training_release=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__), ROOT/'src/sai_agent/native_cad.py', R/'hardware/stage_three_actuator_mounts.json', R/'configs/stage_two_contract.json']},
        vendor_file_sha256=hashlib.sha256(vendor_path.read_bytes()).hexdigest() if vendor_path.exists() else None,
        limitations=['29 sampled individual and combined extreme joint poses are not a continuous sweep',
            'No fastener heads, cables, torso frame, hip yaw-to-roll bracket or ankle cross-axis brackets',
            'Only new-old and new-new part pairs checked; old-old pair interference remains a separate gate',
            'Uniform stator envelope can flag false interference; actual vendor shell distances do not test strength or connector clearance',
            'A new same-version SI mass/axis/contact ledger is required; old stage-two models remain unchanged'])
    output = ('hip_clearance_wide_carrier_screen.json' if args.skin_manifest.parent.name=='hip_clearance_skins_wide' else 'hip_clearance_carrier_screen.json') if args.skin_manifest else 'hip_roll_carrier_screen.json'
    (R/'evidence'/output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['partial_native_interference_pass', 'selected_vendor_gap_pass', 'old_adapter_to_child_vendor_gap_mm']}, indent=2))
    return 0 if report['partial_native_interference_pass'] and report['selected_vendor_gap_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
