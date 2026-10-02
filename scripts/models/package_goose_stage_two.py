"""Package an independently versioned conditional engineering baseline.

The first-stage ZIP is never rewritten. Historical first-stage physics is
included only for the parameter comparator and backward-compatibility tests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/Goose_V0.1/goose_stage_two_20260930.zip')
    args = parser.parse_args()
    cp = R / 'configs/stage_two_contract.json'
    contract = read(cp)
    assert digest(R / 'models/stage_two/robot.xml') == contract['model_sha256']
    files = set()
    for stage in ('stage_one', 'stage_two'):
        model = R / 'models' / stage
        c = read(R / 'configs' / f'{stage}_contract.json')
        assets = set(c['asset_sha256'])
        assets.update(m.attrib['filename'] for m in ET.parse(model / 'robot.urdf').findall('.//mesh'))
        for relative, expected in c['asset_sha256'].items():
            if digest(model / relative) != expected:
                raise ValueError('Asset hash mismatch: ' + relative)
        files.update([model / 'robot.xml', model / 'robot.urdf'])
        files.update(model / a for a in assets)
    files.update((R / 'configs').glob('stage_two_*'))
    files.add(R / 'configs/stage_one_contract.json')
    files.add(R / 'evidence/stage_one_system_gate.json')
    files.update((R / 'hardware').glob('stage_two_*'))
    files.add(R / 'design/stage_two_parameter_handoff.md')
    files.update((R / 'images').glob('stage_two_*.png'))
    files.update((R / 'cad/source/stage_two_architecture').glob('*'))
    files.update(ROOT / p for p in (
        'src/sai_agent/__init__.py', 'src/sai_agent/paths.py',
        'scripts/training/train_goose_stage_one.py',
        'scripts/diagnostics/validate_goose_stage_one_entry.py',
        'scripts/diagnostics/compare_goose_parameter_versions.py',
        'scripts/diagnostics/check_goose_power_budget.py',
        'scripts/evaluation/evaluate_goose_supported_reach.py',
        'scripts/models/render_goose_supported_reach.py',
        'tests/test_goose_stage_one.py', 'tests/test_goose_stage_two.py',
        'LICENSE', 'THIRD_PARTY_NOTICES.md',
    ))
    files.update(ROOT / 'src/sai_agent/goose' / name for name in (
        '__init__.py', 'stage_one.py', 'stage_one_gravity.py', 'rsl.py',
        'control.py', 'spec.py', 'low_reach.py',
    ))
    files.update(p for p in (ROOT / 'licenses').rglob('*') if p.is_file())
    # Reject stale model/source evidence instead of packaging a convenient pass.
    for name in ('system_gate', 'mechanism_gate', 'supported_reach', 'trainer_entry'):
        record = read(R / 'evidence' / f'stage_two_{name}.json')
        assert record['model_sha256'] == contract['model_sha256'], name
        assert record['contract_sha256'] == digest(cp), name
        for field in ('source_hashes', 'source_sha256'):
            for relative, expected in record.get(field, {}).items():
                assert digest(ROOT / relative) == expected, (name, relative)
    assert read(R / 'evidence/stage_two_supported_reach.json')['all_passed']
    assert read(R / 'evidence/stage_two_mechanism_gate.json')['all_checks_passed']
    system = read(R / 'evidence/stage_two_system_gate.json')
    assert system['static_cases'] == system['contact_feasible'] == 63
    assert all(j['below_continuous_design_limit'] for j in system['joint_summary'].values())
    power = read(R / 'evidence/stage_two_power_gate.json')
    assert power['contract_sha256'] == digest(cp)
    assert power['source_sha256'] == digest(R / 'hardware/stage_two_power_architecture.json')
    assert not power['hardware_freeze_passed']
    delta = read(R / 'evidence/stage_two_parameter_delta.json')
    assert delta['candidate_sha256'] == digest(cp)
    assert delta['base_sha256'] == digest(R / 'configs/stage_one_contract.json')
    assert delta['requires_new_training_version']
    tests = read(R / 'evidence/stage_two_test_gate.json')
    assert tests['failures'] == tests['errors'] == 0 and tests['tests'] >= 64
    for relative, expected in tests['source_sha256'].items():
        assert digest(ROOT / relative) == expected, relative
    scene_path = R / 'cad/source/stage_two_architecture/scene.json'
    scene = read(scene_path)
    geometry = []
    for part in scene['parts']:
        faces = np.asarray(part['faces'])
        assert faces.ndim == 2 and faces.shape[1] == 4, part['name']
        mesh = trimesh.Trimesh(part['vertices'], np.vstack((faces[:, [0, 1, 2]], faces[:, [0, 2, 3]])), process=False)
        ok = mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
        assert ok, part['name']
        geometry.append(dict(name=part['name'],quad_faces=len(faces),watertight=bool(mesh.is_watertight),consistent_winding=bool(mesh.is_winding_consistent),volume_m3=float(mesh.volume),passed=bool(ok)))
    geometry_path = R / 'evidence/stage_two_geometry_gate.json'
    geometry_path.write_text(json.dumps(dict(status='EDITABLE_SOURCE_QUAD_GEOMETRY_PASS',part_count=len(geometry),quad_faces=sum(p['quad_faces'] for p in geometry),all_quads_closed_positive=True,scene_sha256=digest(scene_path),blend_sha256=digest(R / 'cad/source/stage_two_architecture/goose_stage_two_quad.blend'),parts=geometry),indent=2)+'\n')
    files.update((R / 'evidence').glob('stage_two_*.json'))
    manifest_path = R / 'evidence/stage_two_delivery_manifest.json'
    files.discard(manifest_path)
    # Post-package audit contains the ZIP hash and cannot be embedded in itself.
    files.discard(R / 'evidence/stage_two_bundle_check.json')
    assert all(p.is_file() for p in files)
    readme = '''# Goose stage-two parameter handoff

Start with robots/Goose_V0.1/design/stage_two_parameter_handoff.md (Chinese).
Current candidate: goose_stage_two_si_v2,18 axes,8.854kg nominal.
Conditional architecture/initial-training baseline, NOT hardware freeze or manufacturing release.
No walking, object-pickup or measured continuous-grasp acceptance; no policy included.

Python3.12. Reuse the tested MuJoCo/PyTorch environment on DGX Spark when available.
Core dependencies: requirements.txt. Training extras: requirements_train.txt.

From the package root:

    PYTHONPATH=src python scripts/diagnostics/validate_goose_stage_one_entry.py --stage stage_two --device cuda --output artifacts/entry.json
    PYTHONPATH=src python scripts/evaluation/evaluate_goose_supported_reach.py --stage stage_two --output artifacts/reach.json
    PYTHONPATH=src python -m pytest -q tests/test_goose_stage_one.py tests/test_goose_stage_two.py

Use --device cpu without CUDA. Optional initial training, explicitly selecting the new version:

    PYTHONPATH=src python scripts/training/train_goose_stage_one.py --stage stage_two --output artifacts/new_run --iterations 2 --envs 4 --horizon 16 --device cuda

Training output must be a new directory. This delivery itself made zero optimizer updates.
The stage_one model is historical comparison/test input, NOT the new training candidate.
Source generation and full historical investigations use the Git repository; this is a compact runtime/parameter/editable-source handoff.
The original first-stage ZIP remains unchanged.

Integrity: robots/Goose_V0.1/evidence/stage_two_delivery_manifest.json contains per-file SHA-256.
'''
    generated = {'README.md':readme,'requirements.txt':'mujoco==3.10.0\nnumpy>=2.0,<3\nscipy>=1.14,<2\nonnxruntime==1.24.4\npytest>=8,<10\n','requirements_train.txt':'torch==2.9.1\nrsl-rl-lib==5.0.1\nonnx==1.22.0\n'}
    manifest = dict(schema='goose_stage_two_handoff_v2',status='CONDITIONAL_ARCHITECTURE_INITIAL_TRAINING_BASELINE',model_sha256=contract['model_sha256'],contract_sha256=digest(cp),nominal_mass_kg=contract['nominal_robot_mass_kg'],joint_count=18,physical_hard_freeze=False,manufacturing_release=False,walking_acceptance=False,object_pickup_acceptance=False,policy_included=False,optimizer_updates=0,repository_tests=tests['tests'],open_items=['exact AK48 bus voltage and regeneration hardware','enclosed-head stationary thermal force validation','shaft/clamp/fastener manufacturing interfaces','closed-loop object acquisition and dragging'],files={str(p.relative_to(ROOT)):digest(p) for p in sorted(files)},generated_files_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in generated.items()})
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(files | {manifest_path}):
            archive.write(path,str(path.relative_to(ROOT)))
        for name,value in generated.items():
            archive.writestr(name,value)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
    sha = digest(args.output)
    args.output.with_suffix('.zip.sha256').write_text(sha+'  '+args.output.name+'\n')
    print(json.dumps(dict(path=str(args.output),sha256=sha,size_bytes=args.output.stat().st_size,files=len(files)),indent=2))


if __name__ == '__main__':
    main()
