"""A prior CAD pass is reusable only for the exact source and passed poses."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

pytest.importorskip('build123d')
ROOT=Path(__file__).resolve().parents[1]
ROBOT=ROOT/'robots/Goose_V0.1'


@pytest.fixture
def inherited_fit(tmp_path,monkeypatch):
    file=ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py'
    spec=importlib.util.spec_from_file_location('goose_fit_inheritance_fixture',file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=ROBOT/'evidence/jaw_retention_native_fit.json'
    report=json.loads(source.read_text())
    for relative in report['source_hashes']:
        target=tmp_path/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)
    robot=tmp_path/'robots/Goose_V0.1'
    output=robot/'evidence/jaw_retention_native_fit.json'
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(source.read_text())
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'R',robot)
    folders=['head_load_path','beak_native_linkage','bill_backbones','jaw_retention','grip_cassettes']
    paths=[ROBOT/'cad/exports'/folder/'manifest.json' for folder in folders]
    manifests=[json.loads(p.read_text()) for p in paths]
    additional=json.loads((ROBOT/'configs/mechanical_native_replacements.json').read_text())['additional_replaces_by_folder']
    return module,paths,manifests,additional,output


def test_source_change_cannot_reuse_a_previous_native_pass(inherited_fit):
    module,paths,manifests,additional,_=inherited_fit
    records,pairs,angles,_=module.baseline_pair_coverage(paths,manifests,additional)
    assert len(records)==47 and len(pairs)==937 and len(angles)==23
    changed=module.ROOT/'robots/Goose_V0.1/cad/exports/jaw_retention/manifest.json'
    changed.write_text(changed.read_text()+'\n')
    with pytest.raises(ValueError,match='Stale inherited'):
        module.baseline_pair_coverage(paths,manifests,additional)


def test_one_failed_prior_pose_rejects_inheritance(inherited_fit):
    module,paths,manifests,additional,output=inherited_fit
    report=json.loads(output.read_text());report['cases'][9]['sampled_geometry_pass']=False
    output.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='not a passed'):
        module.baseline_pair_coverage(paths,manifests,additional)
