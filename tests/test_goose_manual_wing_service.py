"""Regression of real manual-service CAD, retained physics and collision scope."""
from pathlib import Path
import hashlib, importlib.util, json, sys
import numpy as np
import pytest
cad=pytest.importorskip('build123d')
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/diagnostics')]
from sai_agent.native_cad_query import native_solid_integrity
from check_goose_grip_cassettes import bounded_common

def test_hinge_profile_has_real_area_and_correct_3d_extent():
    spec=importlib.util.spec_from_file_location('manual_wing_builder',ROOT/'scripts/cad/build_goose_manual_wing_service.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    solid=module.strip([(0,0),(0,20)],4,7,2.5)
    assert native_solid_integrity(solid)['boolean_input_integrity_pass']
    assert solid.volume==pytest.approx(200)
    bounds=solid.bounding_box()
    assert tuple(bounds.min)==pytest.approx((5.75,-2,0),abs=1e-6)
    assert tuple(bounds.max)==pytest.approx((8.25,2,20),abs=1e-6)

def test_actual_feature_bearing_left_and_right_doors_clear_closed_and45():
    kit=json.loads((R/'cad/exports/manual_wing_service/manifest.json').read_text())
    by_name={p['name']:p for p in kit['parts']}
    for side,label in [(-1,'right'),(1,'left')]:
        shapes=[]
        for name in ['wing_manual_door_'+label,'torso_manual_shell_'+label+'_fore']:
            rec=by_name[name]['files']['brep'];path=R/rec['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256']
            shape=cad.import_brep(path)
            assert native_solid_integrity(shape)['boolean_input_integrity_pass']
            shapes.append(shape)
        door,fixed=shapes
        for angle in [0,45]:
            pose=door.rotate(cad.Axis((0,side*109,371),(1,0,0)),side*angle)
            common=bounded_common(pose,fixed,12)
            assert 'error' not in common and common['volume_mm3']==0
            assert pose.distance_to(fixed)>=.2

def test_replacement_ledger_conserves_mass_and_preserves_active_contract():
    old=json.loads((R/'evidence/one_piece_head_service_parameters.json').read_text())
    new=json.loads((R/'evidence/manual_wing_service_parameters.json').read_text())
    kit=json.loads((R/'cad/exports/manual_wing_service/manifest.json').read_text())
    assert new['parts']==478 and new['active_axes']==old['active_axes']==18
    assert new['neutral_joint_order']==old['neutral_joint_order']
    assert new['pivots_world_at_zero_m']==old['pivots_world_at_zero_m']
    assert len(kit['parts'])==24 and len(kit['replaces_existing_parts'])==6
    assert len(new['items'])==len({p['name'] for p in new['items']})
    assert new['nominal_conditional_mass_kg']==pytest.approx(sum(p['mass_kg'] for p in new['items']))
    assert new['nominal_conditional_mass_kg']==pytest.approx(sum(b['mass_kg'] for b in new['bodies']))
    assert len(new['bodies'])==19
    for b in new['bodies']:
        assert np.linalg.eigvalsh(b['inertia_at_com_body_kg_m2']).min()>0
    assert not new['manufacturing_release'] and not new['training_release']

def test_finite_evidence_remains_bound_and_does_not_claim_full_release():
    report=json.loads((R/'evidence/manual_wing_service_checks.json').read_text())
    for relative,digest in report['source_hashes'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    assert len(report['finite_service_pairs'])==28
    assert len(report['roof_carrier_pairs'])==16
    assert report['same_source_limited_checkpoint_pass']
    assert not report['continuous_service_sweep_proved']
    assert not report['full_assembly_pass'] and not report['manufacturing_release']
    for scenario in report['static'].values():
        assert scenario['cases']==scenario['contact_feasible']==63
        assert scenario['all_static_torques_pass']

def test_rejected_same_domain_merge_is_not_waived_by_topology_validity():
    path=R/'cad/source/manual_wing_service_rejections/merged_left_aft.brep'
    result=native_solid_integrity(cad.import_brep(path))
    assert result['topology_valid'] and result['solid_count']==1
    assert not result['boolean_input_integrity_pass']
    assert any('SelfIntersect' in row['status'] for row in result['faults'])

def test_real_long_arm_rejection_is_detected_at45_degrees():
    base=R/'cad/source/manual_wing_service_rejections'
    moving=cad.import_brep(base/'arm_right_door.brep').rotate(cad.Axis((0,-109,371),(1,0,0)),-45)
    fixed=cad.import_brep(base/'arm_right_fore.brep')
    result=bounded_common(moving,fixed,12)
    assert 'error' not in result and result['volume_mm3']>4
    assert moving.distance_to(fixed)==pytest.approx(0,abs=1e-6)
