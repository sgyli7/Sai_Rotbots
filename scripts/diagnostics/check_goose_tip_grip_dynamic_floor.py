"""Resolve observed shell/floor collision candidates with the native solid.

Uses captured actual body poses from the same fixed-controller trial. Stops
after a confirmed rejection, or after a60s bounded set of native queries.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
from build123d import import_brep

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'evidence/tip_grip_floor_pickup_80mm_contact_probe.json',
             R/'cad/exports/tip_grip_candidate/manifest.json',
             R/'evidence/body_bay_mechanical_parameters.json',
             ROOT/'scripts/cad/build_goose_cad.py', ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py']
    trial, kit, ledger = [json.loads(p.read_text()) for p in paths[:3]]
    for relative, expected in trial['source_hashes'].items():
        if sha(ROOT/relative) != expected:
            raise ValueError(('stale captured trial', relative))
    parts = {p['name']: p for p in kit['parts']}
    shapes = {}
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    ground = box([2000., 2000., 500.], [0., 0., -250.])
    samples = sorted(trial['nonobject_contact_native_pose_samples'],
                     key=lambda s: -s['convex_penetration_m'])
    results, unsupported = [], []
    started = time.monotonic()
    confirmed = False
    stopped = 'ALL_CAPTURED_SAMPLES_QUERIED'
    for sample in samples:
        if time.monotonic()-started > 60.:
            stopped = 'NATIVE_TOTAL_TIME_BOUND'
            break
        names = sample['parts']
        if 'ground' not in names:
            unsupported.append(dict(sample=sample, reason='Only native part/ground pairs in this bounded probe'))
            continue
        name = next(n for n in names if n != 'ground')
        if name not in parts:
            unsupported.append(dict(sample=sample, reason='Part is not in detached native replacement kit'))
            continue
        part = parts[name]
        if name not in shapes:
            file = R/part['files']['brep']['path']
            if sha(file) != part['files']['brep']['sha256']:
                raise ValueError(('native identity mismatch', name))
            shapes[name] = import_brep(file)
            paths.append(file)
        owner = part['body']
        captured = sample['native_body_poses'][owner]
        rotation = np.array(captured['rotation_world'])
        position = np.array(captured['position_world_m'])
        pivot = np.array(ledger['pivots_world_at_zero_m'][owner])
        moved = transform(shapes[name], rotation, (position+rotation@(lift-pivot))*1000)
        common = bounded_common(moved, ground, 3.)
        hit = 'error' not in common and common['volume_mm3'] > .01
        results.append(dict(part=name, captured_state_time_s=sample['state_time_s'],
            convex_penetration_m=sample['convex_penetration_m'], native_body_pose=captured,
            native_common=common, genuine_floor_intrusion_confirmed=hit))
        print('TIP DYNAMIC NATIVE', name, sample['state_time_s'], common, flush=True)
        if hit:
            confirmed = True
            stopped = 'NATIVE_FLOOR_REJECTION_CONFIRMED'
            break
    clear = bool(samples and len(results) == len(samples) and not unsupported
                 and not any('error' in c['native_common'] for c in results)
                 and all(not c['genuine_floor_intrusion_confirmed'] for c in results))
    report = dict(schema='goose_tip_grip_dynamic_native_floor_v1', status=stopped,
        captured_contact_sample_count=len(samples), tested_native_cases=len(results), cases=results,
        unsupported_samples=unsupported, unresolved_native_queries=sum('error' in c['native_common'] for c in results),
        genuine_dynamic_floor_intrusion_confirmed=confirmed,
        all_captured_convex_candidates_native_clear=clear,
        wall_seconds=time.monotonic()-started, total_wall_bound_s=60., pair_timeout_s=3.,
        native_coordinate_unit='mm', installed=False, whole_pickup_release=False,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
        limitations=['Checks observed10ms-sampled contact poses; not a certified continuous swept-volume bound.',
          'One positive exact native solid volume belowfloor rejects this trial; remaining samples are unnecessary for that rejection.',
          'Zero or timeout at one sample cannot prove all poses clear. Unknown queries stay unresolved.',
          'Does not change geometry, hulls, controller, joint limits, collision filters or physical gate.'])
    (R/'evidence/tip_grip_dynamic_native_floor.json').write_text(json.dumps(report, indent=2)+'\n')
    print('TIP DYNAMIC FLOOR', stopped, 'confirmed', confirmed, 'all captured clear', clear, flush=True)


if __name__ == '__main__':
    main()
