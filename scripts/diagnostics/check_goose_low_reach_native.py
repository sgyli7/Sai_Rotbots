"""Confirm the previously colliding head bracket/torso pair in native CAD.

This checks the same discrete path as the full convex-model screen. It is a
targeted native-solid rejection, not a continuous sweep or a task execution.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/models')]
from build_goose_cad import transform
from build_goose_stage_two import candidate
from sai_agent.native_cad import common_solid_volume_mm3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'cad/exports/head_load_path/manifest.json',
             R/'cad/exports/neck_access_skins/manifest.json',
             R/'evidence/body_bay_mechanical_parameters.json',
             R/'evidence/mechanical_ground_reach_path.json']
    head, torso, ledger, path = [json.loads(p.read_text()) for p in paths]
    for source, digest in path['source_hashes'].items():
        assert sha(ROOT/source) == digest, ('stale path', source)
    names = {'head_pitch_to_roll_stator_bracket',
             'torso_shell_right_fore', 'torso_shell_left_fore'}
    shapes, owners = {}, {}
    for manifest in [head, torso]:
        for part in manifest['parts']:
            if part['name'] not in names:
                continue
            info = part['files']['step']
            step = R/info['path']
            assert sha(step) == info['sha256']
            shape = import_step(step).solids()[0]
            local = part.get('world_from_local_mm')
            if local:
                shape = transform(shape, np.array(local['rotation']), local['translation'])
            shapes[part['name']], owners[part['name']] = shape, part['body']
    assert set(shapes) == names
    skeleton = candidate()
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    skeleton.pivots = {n: np.array(p)-(lift if n != 'torso' else 0)
                       for n, p in ledger['pivots_world_at_zero_m'].items()}
    records = []
    for sample in path['samples']:
        poses, _ = skeleton.fk(sample['joint_q_rad'],
                               root_p=np.array(sample['root_position_m'])-lift)
        moved = {}
        bounds = {}
        for name, shape in shapes.items():
            position, rotation = poses[owners[name]]
            moved[name] = transform(shape, rotation,
                                    (position-rotation@skeleton.pivots[owners[name]])*1000)
            box = moved[name].bounding_box()
            bounds[name] = np.array(tuple(box.min)), np.array(tuple(box.max))
        bracket = 'head_pitch_to_roll_stator_bracket'
        intersections = {}
        for shell in ['torso_shell_right_fore', 'torso_shell_left_fore']:
            bbox_overlap = np.all(np.minimum(bounds[bracket][1], bounds[shell][1])
                                  > np.maximum(bounds[bracket][0], bounds[shell][0])+1e-6)
            intersections[shell] = (common_solid_volume_mm3(moved[bracket], moved[shell])
                                    if bbox_overlap else 0.)
        passed = all(v <= .01 for v in intersections.values())
        records.append(dict(index=sample['index'], phase=sample['phase'],
                            parameter=sample['parameter'],
                            common_volume_mm3=intersections, native_pair_screen_pass=passed))
        if not passed:
            print('NATIVE LOW REACH FAIL', records[-1], flush=True)
    report = dict(schema='goose_low_reach_native_pair_v1', checked_parts=sorted(names),
                  sample_count=len(records), passed_samples=sum(x['native_pair_screen_pass'] for x in records),
                  maximum_common_volume_mm3=max(v for x in records for v in x['common_volume_mm3'].values()),
                  samples=records, manufacturing_release=False, actual_pickup_pass=False,
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
                  limitations=['Only the previously colliding head bracket and two fore torso shells are covered.',
                               'Discrete native solid intersections do not prove continuous swept clearance, cables, strength or physical pickup.'])
    (R/'evidence/mechanical_low_reach_native_pair.json').write_text(json.dumps(report, indent=2)+'\n')
    print('NATIVE LOW REACH', report['passed_samples'], '/', len(records), flush=True)
    return 0 if report['passed_samples'] == len(records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
