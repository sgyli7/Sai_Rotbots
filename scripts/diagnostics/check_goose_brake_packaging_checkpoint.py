"""Same-source packaging packet audit; no upgrade to manufacturing release."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen003-archive', type=Path, required=True)
    args = parser.parse_args()
    paths = [R/p for p in ['cad/exports/brake_packaging/manifest.json', 'evidence/brake_packaging_parameters.json',
        'evidence/brake_packaging_checks.json', 'evidence/brake_motion_clearance.json',
        'evidence/brake_packaging_render.json', 'evidence/brake_packaging_socket_head_rejection.json',
        'evidence/brake_motion_rejection.json', 'evidence/brake_pcb_shell_rejection.json']]
    kit, params, fit, motion, render, *rejected = [json.loads(p.read_text()) for p in paths]
    for data in [kit, params, fit, motion, render]+rejected:
        for relative,digest in data['source_hashes'].items():
            if sha(ROOT/relative) != digest:
                raise ValueError(('Stale packet source', relative))
    quad = []
    for part in kit['parts']:
        for file in part['files'].values():
            if sha(R/file['path']) != file['sha256']:
                raise ValueError(('Changed export', part['name']))
        arrays = np.load(R/part['files']['npz']['path'])
        v,f = arrays['vertices'], arrays['faces']
        if f.shape[1]!=4:
            raise ValueError('Nonquad source')
        mesh = trimesh.Trimesh(v, np.concatenate([f[:,[0,1,2]], f[:,[0,2,3]]]), process=False)
        error = abs(mesh.volume*1e9/part['volume_mm3']-1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or error>.005:
            raise ValueError(('Quad exchange mismatch', part['name']))
        quad.append(dict(name=part['name'], all_quad=True, closed=True, volume_relative_error=error))
    for name,digest in render['images'].items():
        if sha(R/'images/brake_packaging'/name) != digest:
            raise ValueError('Changed actual render')
    frozen = args.frozen003_archive
    expected = 'dbed165c552e3a44e8279ce6da6d31e3230ccb4c46223aa74e35275df84595a0'
    if not frozen.exists() or sha(frozen)!=expected:
        raise ValueError('Frozen003 archive not verified')
    documents = [ROOT/'README.md', R/'README.md', R/'design/hardware_milestones.md',
                 R/'hardware/brake_packaging_checkpoint.md', R/'hardware/absolute_brake_chopper_checkpoint.md']
    link_count = 0
    for document in documents:
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',document.read_text()):
            link = match.group(1).split('#')[0].split(' "')[0]
            if not link or '://' in link or link.startswith('mailto:'):
                continue
            target = document.parent/link
            if not target.exists():
                raise ValueError(('Broken local link',document,link))
            link_count += 1
    junit = ROOT/'artifacts/Goose_V0.1/brake_packaging_review_20261004/targeted_tests.xml'
    suites = ET.parse(junit).getroot().iter('testsuite')
    totals = {k:0 for k in ['tests','failures','errors','skipped']}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib.get(key,0))
    if totals['tests']<68 or any(totals[k] for k in ['failures','errors','skipped']):
        raise ValueError(('Targeted tests incomplete',totals))
    if not fit['limited_candidate_pass'] or not motion['finite_pose_pass']:
        raise ValueError('Finite installation checks failed')
    preserved = R/'cad/source/manual_wing_service/assembly_scene.json'
    if sha(preserved)!='0eb5468d86792ccad23503c96b54ec4c8c54a4cef134998db4555e0d7c651cfe':
        raise ValueError('Preserved478 source changed')
    result = dict(schema='goose_brake_packaging_delivery_audit_v1', status='LOCAL_INSTALLATION_CHECKPOINT_ONLY',
        candidate_parts=48, scene_objects=params['parts'], active_axes=18, closed_pose_si_bodies=len(params['bodies']),
        quad_exchange=quad, targeted_tests=totals, checked_local_links=link_count,
        limited_native_fit_pass=True, finite_motion_samples=motion['sampled_poses'], same_source_static_pass=fit['static_screen_pass'],
        actual_render_images=len(render['images']), preserved478_source_sha256=sha(preserved),
        frozen003_zip_sha256=sha(frozen), nominal_conditional_mass_kg=params['nominal_conditional_mass_kg'],
        electrical_release=False, thermal_release=False, manufacturing_release=False, full_assembly_pass=False,
        continuous_sweep_pass=False, runtime_or_training_default_changed=False, full_engineering_goal_complete=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+documents+[Path(__file__)]},
        junit_sha256=sha(junit))
    (R/'evidence/brake_packaging_delivery_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PACKET AUDIT',totals,'links',link_count,'mass',params['nominal_conditional_mass_kg'],flush=True)


if __name__=='__main__':
    main()
