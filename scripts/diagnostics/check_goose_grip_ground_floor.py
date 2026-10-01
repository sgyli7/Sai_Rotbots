"""Native CAD floor intersections for two otherwise clear finite reach poses.

Confirms a selected rejection; does not prove all ground pickup impossible.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import import_brep

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/models'), str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from build_goose_stage_two import candidate
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'evidence/mechanical_grip_ground_pose_screen.json',
             R/'evidence/body_bay_mechanical_parameters.json',
             R/'cad/exports/grip_cassettes/manifest.json',
             ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py',
             ROOT/'scripts/cad/build_goose_cad.py']
    screen, ledger, manifest = [json.loads(p.read_text()) for p in paths[:3]]
    for relative, digest in screen['source_hashes'].items():
        if sha(ROOT/relative) != digest:
            raise ValueError(('stale reach screen', relative))
    poses = [r for r in screen['records'] if r['ik_pass']
             and all(s['static_screen_pass'] for s in r['static_cases'])
             and all('ground' in (h['part_a'], h['part_b']) for h in r['jaw_endpoints'][0]['contacts'])]
    poses = sorted(poses, key=lambda r: (abs(r['target_grip_world_m'][0]-.22), r['crouch_drop_mm']))[:2]
    if len(poses) != 2:
        raise ValueError('expected two selected poses without non-floor closed-jaw hits')
    s = candidate()
    s.pivots = {n: np.array(v) for n, v in ledger['pivots_world_at_zero_m'].items()}
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    parts = {p['name']: p for p in manifest['parts'] if p['name'] in ('upper_grip_shell', 'lower_grip_shell')}
    shapes = {}
    for name, part in parts.items():
        info = part['files']['brep']
        file = R/info['path']
        if sha(file) != info['sha256']:
            raise ValueError(('native source identity', name))
        shapes[name] = import_brep(file)
        paths.append(file)
    # Broad finite below-floor solid: top at assembled worldZ=0mm.
    below_floor = box([2000., 2000., 500.], [0., 0., -250.])
    records = []
    for pose in poses:
        fk, _ = s.fk(pose['joint_q_rad'], root_p=np.array(pose['root_position_m']))
        results = []
        for name, shape in shapes.items():
            owner = parts[name]['body']
            position, rotation = fk[owner]
            moved = transform(shape, rotation, (position+rotation@(lift-s.pivots[owner]))*1000)
            result = bounded_common(moved, below_floor, 3.)
            results.append(dict(part=name, native_common=result,
                                floor_intersection_confirmed=result.get('volume_mm3', 0.) > .01 and 'error' not in result))
        records.append(dict(screen_candidate_index=pose['index'], crouch_drop_mm=pose['crouch_drop_mm'],
                            target_grip_world_m=pose['target_grip_world_m'], closed_jaw_angle_rad=0.,
                            parts=results, native_floor_rejection_confirmed=any(x['floor_intersection_confirmed'] for x in results)))
    report = dict(schema='goose_grip_ground_floor_native_rejection_v1', selected_pose_count=len(records),
                  cases=records, all_selected_rejections_confirmed=all(x['native_floor_rejection_confirmed'] for x in records),
                  unresolved_native_queries=sum('error' in p['native_common'] for r in records for p in r['parts']),
                  pair_timeout_s=3., coordinate_unit='mm', floor_world_z_mm=0.,
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
                  architecture_changed=False, global_ground_pickup_infeasibility_proved=False,
                  floor_pickup_pass=False, manufacturing_release=False,
                  limitations=['Two selected discrete closed-jaw poses only; neither all36poses nor a continuous reach path is checked natively.',
                               'Positive native solid volume belowZ0 confirms collision for this pose; bounding-box overlap alone is not used as proof.',
                               'Timeouts are unresolved and not zero; other poses, objects, approaches and alternative structures remain open.'])
    (R/'evidence/mechanical_grip_ground_floor_native.json').write_text(json.dumps(report, indent=2)+'\n')
    print('NATIVE FLOOR REJECTION', report['all_selected_rejections_confirmed'], records, flush=True)
    return 0 if report['all_selected_rejections_confirmed'] and not report['unresolved_native_queries'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
