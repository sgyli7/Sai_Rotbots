"""Targeted native bill-backbone assembly sweep, without physics exclusions."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import import_step
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import transform
from sai_agent.native_cad import common_solid_volume_mm3


def main():
    paths = [R/'cad/exports'/folder/'manifest.json' for folder in
             ['bill_backbones', 'head_load_path', 'head_linkage_clearance_skins', 'beak_native_linkage']]
    manifests = [json.loads(p.read_text()) for p in paths]
    shapes = {}
    for manifest in manifests:
        for part in manifest['parts']:
            item = R/part['files']['step']['path']
            assert hashlib.sha256(item.read_bytes()).hexdigest() == part['files']['step']['sha256']
            shapes[part['name']] = import_step(item).solids()[0]
    fixed_names = ['head_frame_with_bill_mounts', 'upper_bill_metal_backbone',
                   'upper_bill_backbone_shell', 'beak_motor_catalog_case',
                   'jaw_front_bearing', 'jaw_rear_bearing',
                   'head_bill_access_shell_left', 'head_bill_access_shell_right']
    moving_names = ['lower_bill_keyed_backbone', 'lower_bill_backbone_shell']
    motor = np.array(manifests[-1]['motor_axis_world_mm'])
    jaw = np.array(manifests[-1]['jaw_axis_world_mm'])
    rows = []
    for q in np.linspace(0, .55, 23):
        rotation = Rotation.from_rotvec([0, q, 0]).as_matrix()
        moved = {name: transform(shapes[name], rotation, jaw-rotation@jaw) for name in moving_names}
        # Also check the input/output cranks against the added fixed backbone
        # and frame bosses; the old linkage report predates those additions.
        moved['beak_native_input_flange'] = transform(shapes['beak_native_input_flange'], rotation, motor-rotation@motor)
        moved['beak_native_output_arm'] = transform(shapes['beak_native_output_arm'], rotation, jaw-rotation@jaw)
        records = []
        for a, shape in moved.items():
            for b in fixed_names:
                if a.startswith('beak_native') and b not in fixed_names[:2]:
                    continue
                volume = common_solid_volume_mm3(shape, shapes[b])
                if volume > .01:
                    records.append(dict(a=a, b=b, common_volume_mm3=volume))
        rows.append(dict(q_rad=float(q), hits=records, sampled_geometry_pass=not records))
        print('BILL BACKBONE SWEEP', round(q, 3), 'hits', len(records), flush=True)
    report = dict(schema='goose_native_bill_backbone_sweep_v1', cases=rows,
                  sample_count=len(rows), passed_samples=sum(r['sampled_geometry_pass'] for r in rows),
                  installed=False, manufacturing_release=False, whole_head_release=False,
                  source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in paths+[Path(__file__)]},
                  limitations=['Only listed native bill/backbone/frame/skin/crank pairs, 23 jaw angles.',
                               'No continuous clearance proof, fastener/head/cable sweeps, minimum walls, strength, thermal or task release.',
                               'Independent candidate; current 292-part running model and its mass have not changed.'])
    (R/'evidence/native_bill_backbone_sweep.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['passed_samples'] == len(rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
