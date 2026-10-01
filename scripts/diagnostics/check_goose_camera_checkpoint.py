"""Record camera candidate integrity without modifying the default assembly."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    reports = [ROBOT/'evidence'/n for n in ['camera_catalog_layout.json',
        'camera_supplier_native_mount_fit.json', 'camera_recorded_task_view.json']]
    carrier_path = ROBOT/'cad/exports/camera_carrier/manifest.json'
    records = [json.loads(p.read_text()) for p in reports+[carrier_path]]
    for record in records:
        for rel, expected in record['source_hashes'].items():
            if sha(ROOT/rel) != expected:
                raise ValueError(('stale source chain', rel))
    layout, native, view, carrier = records
    if layout['finite_candidate_count'] != 16 or layout['status'] != 'ALL_FINITE_CANDIDATES_TESTED':
        raise ValueError('incomplete finite camera layout')
    if not carrier['native_current_part_clearance_pass'] or not native['all_named_parts_nominal_no_intrusion']:
        raise ValueError('native camera installation screen failed')
    if carrier['replaces_existing_parts'][0] != 'head_frame_with_jaw_retention':
        raise ValueError('camera frame must preserve the current344-part jaw-retention predecessor')
    quads = []
    for part in carrier['parts']:
        for file in part['files'].values():
            if sha(ROBOT/file['path']) != file['sha256']:
                raise ValueError(('changed candidate output', part['name']))
        data = np.load(ROBOT/part['files']['npz']['path'])
        vertices, faces = data['vertices'], data['faces']
        if faces.ndim != 2 or faces.shape[1] != 4 or not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
            raise ValueError(('invalid quad source', part['name']))
        triangles = np.concatenate([faces[:,[0,1,2]], faces[:,[0,2,3]]])
        mesh = trimesh.Trimesh(vertices, triangles, process=False)
        error = abs(mesh.volume*1e9/part['volume_mm3']-1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or error >= .005:
            raise ValueError(('quad source closure/volume mismatch', part['name']))
        quads.append(dict(part=part['name'], all_quad=True, faces=len(faces),
            source_closed=True, source_winding_consistent=True, native_volume_relative_error=float(error)))
    # Pin the previous completed checkpoint, rather than whichever HEAD later
    # happens to contain this new camera diagnostic and its documentation.
    baseline_commit = '623f0f80'
    baseline = []
    for rel in ['cad/source/mechanical_preview/scene.json', 'configs/mechanical_physics_contract.json',
                'models/mechanical_physics/robot.xml', 'evidence/body_bay_mechanical_parameters.json']:
        path = ROBOT/rel
        git_path = str(path.relative_to(ROOT))
        previous = subprocess.run(['git', 'show', baseline_commit+':'+git_path], cwd=ROOT,
                                  check=True, capture_output=True).stdout
        expected = hashlib.sha256(previous).hexdigest()
        if sha(path) != expected:
            raise ValueError(('default assembly changed during detached camera work', git_path))
        baseline.append(dict(path=git_path, sha256=expected, unchanged=True))
    scene = json.loads((ROBOT/'cad/source/mechanical_preview/scene.json').read_text())
    ledger = json.loads((ROBOT/'evidence/body_bay_mechanical_parameters.json').read_text())
    items = {p['name']:p for p in ledger['items']}
    optics_com_differences = []
    for name in ['flush_camera_window', 'camera_glass', 'camera_inner_lens', 'camera_eye_bezel']:
        part = next(p for p in scene['parts'] if p['name']==name)
        vertices, faces = np.asarray(part['vertices']), np.asarray(part['faces'])
        mesh = trimesh.Trimesh(vertices, np.concatenate([faces[:,[0,1,2]], faces[:,[0,2,3]]]), process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError(('default display optic is not closed', name))
        actual = mesh.center_mass+np.asarray(scene['assembly_translation_m'])
        recorded = np.asarray(items[name]['center_m'])
        optics_com_differences.append(dict(part=name, actual_source_com_world_m=actual.tolist(),
            recorded_ledger_com_world_m=recorded.tolist(), ledger_minus_source_m=(recorded-actual).tolist(),
            resolved=False, disposition='Replace by geometry-derived own optical parts in next integrated version; do not inherit obsolete COM.'))
    docs = [ROBOT/'README.md']+[ROBOT/'design'/n for n in ['camera_installation_checkpoint.md',
        'mechanical_integration_checkpoint.md', 'hardware_milestones.md']]
    link_count = 0
    for path in docs:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            link_count += 1
            if not (path.parent/target.split('#',1)[0]).exists():
                raise ValueError(('missing document link', path, target))
    value = dict(schema='goose_detached_camera_checkpoint_v1',
        integrity_pass=True, native_candidate_parts=len(carrier['parts']), quad_sources=quads,
        finite_catalog_installation_candidates=layout['finite_candidate_count'],
        finite_passing_catalog_candidates=layout['finite_passing_count'],
        current_native_named_clearance_pass=True, supplier_four_groups_retained=True,
        nominal_supplier_mount_fit_pass=True, net_candidate_parts_mass_change_kg=carrier['net_candidate_parts_mass_change_kg'],
        recorded_task_view_summary=view['summary'],
        default_baseline_commit=baseline_commit, default_baseline=baseline,
        default_display_optics_com_discrepancies=optics_com_differences,
        checked_document_links=link_count, missing_document_links=[],
        installed=False, complete_camera_mount_pass=False, complete_visual_autonomy_pass=False,
        stage_three_four_complete=False, manufacturing_release=False, training_hard_freeze=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in reports+[carrier_path, Path(__file__)]+docs},
        next_scope='Whole assembly and power/actuator release. Do not extend this into camera polish, PPO or more local trial tuning.')
    (ROBOT/'evidence/camera_checkpoint.json').write_text(json.dumps(value,indent=2)+'\n')
    print('CAMERA CHECKPOINT', value['native_candidate_parts'], sum(p['faces'] for p in quads),
          'quads', link_count, 'local links', 'default unchanged', flush=True)


if __name__ == '__main__':
    main()
