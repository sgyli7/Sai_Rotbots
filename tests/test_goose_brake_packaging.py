"""Reject CAD overlaps independently of runtime pair filtering and conserve SI."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pytest

cad = pytest.importorskip('build123d')
ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from check_goose_brake_packaging import aabb_gap, native_pair


def read(relative):
    return json.loads((R/relative).read_text())


def test_nominal_mating_cannot_hide_real_hardware_overlap():
    cube = cad.Box(10, 10, 10)
    result = native_pair(cube, cube.translate((5, 0, 0)), 0, 'bracket', 'frame', mating=True)
    assert not result['pair_pass']
    assert result['common']['volume_mm3'] == pytest.approx(500)


def test_face_mating_and_free_clearance_have_different_requirements():
    cube = cad.Box(10, 10, 10)
    touching = cube.translate((10, 0, 0))
    assert native_pair(cube, touching, 0, 'plate', 'bracket', mating=True)['pair_pass']
    assert not native_pair(cube, touching, 2, 'plate', 'PCB')['pair_pass']
    assert aabb_gap((np.zeros(3), np.ones(3)), (np.array([4,5,1]), np.array([5,6,2]))) == pytest.approx(5)


def test_failed_native_boolean_is_unknown_and_cannot_pass(monkeypatch):
    import check_goose_brake_packaging as module
    monkeypatch.setattr(module, 'bounded_common', lambda *args: {'error': 'NATIVE_PAIR_TIMEBOX'})
    result = module.native_pair(cad.Box(10,10,10), cad.Box(10,10,10), 0, 'a', 'b', True)
    assert not result['pair_pass'] and result['gap_mm'] is None


def test_preserved_socket_head_rejection_and_low_head_clearance():
    rejected = read('evidence/brake_packaging_socket_head_rejection.json')
    for relative,digest in rejected['source_hashes'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest
    frame = cad.import_brep(R/rejected['retained_frame'])
    old = cad.import_brep(R/rejected['failed_part'])
    assert not native_pair(old, frame, 2, 'old screw', 'neck base')['pair_pass']
    kit = read('cad/exports/brake_packaging/manifest.json')
    rec = next(p for p in kit['parts'] if p['name']=='brake_bracket_1_chassis_m3x12')
    new = cad.import_brep(R/rec['files']['brep']['path'])
    assert new.distance_to(frame)==pytest.approx(2.35, abs=1e-6)
    assert native_pair(new, frame, 2, 'low head screw', 'neck base')['pair_pass']


def test_replacement_keeps_all_unrelated_mass_and_kinematics():
    old = read('evidence/manual_wing_service_parameters.json')
    new = read('evidence/brake_packaging_parameters.json')
    kit = read('cad/exports/brake_packaging/manifest.json')
    before = {p['name']:p for p in old['items']}
    after = {p['name']:p for p in new['items']}
    replaced = set(kit['replaces_existing_parts'])
    assert replaced == {'torso_compute_mount_chassis_plate', 'brake_hardware_extra_allocation'}
    assert after['main_protection'] == before['main_protection']
    assert new['remaining_protection_reserve_kg'] == pytest.approx(.093)
    for name in before.keys()-replaced:
        assert before[name] == after[name], name
    expected = old['nominal_conditional_mass_kg']-sum(before[n]['mass_kg'] for n in replaced)+sum(p['mass_kg'] for p in kit['parts'])
    assert new['nominal_conditional_mass_kg'] == pytest.approx(expected)
    assert new['nominal_conditional_mass_kg'] == pytest.approx(sum(p['mass_kg'] for p in after.values()))
    assert new['nominal_conditional_mass_kg'] == pytest.approx(sum(b['mass_kg'] for b in new['bodies']))
    assert new['pivots_world_at_zero_m'] == old['pivots_world_at_zero_m']
    assert new['neutral_joint_order'] == old['neutral_joint_order'] and new['active_axes'] == 18
    assert len(new['bodies']) == len(old['bodies']) == 19
    for body in new['bodies']:
        assert np.linalg.eigvalsh(body['inertia_at_com_body_kg_m2']).min()>0
    assert not new['training_release'] and not new['manufacturing_release']


def test_catalog_resistor_mass_includes_leads_and_lift_is_applied_once():
    cfg = read('configs/brake_packaging_candidate.json')
    kit = read('cad/exports/brake_packaging/manifest.json')
    params = read('evidence/brake_packaging_parameters.json')
    items = {p['name']:p for p in params['items']}
    packages = [p for p in kit['parts'] if p['name'].startswith('brake_rd_') and p['name'].count('_')==3]
    assert len(packages)==8
    assert sum(p['mass_kg'] for p in packages)==pytest.approx(8*cfg['resistor']['mass_upper_kg'])
    for part in kit['parts']:
        expected = np.asarray(part['center_of_mass_world_m'])+[0,0,params['rigid_coordinate_lift_m']]
        assert items[part['name']]['center_m']==pytest.approx(expected)
    assert not any('lead_mass' in p['name'] for p in params['items'])


def test_passed_local_evidence_is_same_source_and_not_full_release():
    report = read('evidence/brake_packaging_checks.json')
    for relative, digest in report['source_hashes'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest, relative
    assert report['limited_candidate_pass']
    assert report['positive_common_control']['pass_control']
    assert report['deliberate_misplacement']['pass_rejection']
    assert report['source_chassis_subset']['pass_subset'] and report['source_chassis_subset']['pass_holes']
    for scenario in report['static'].values():
        assert scenario['cases']==scenario['contact_feasible']==63 and scenario['all_static_torques_pass']
    assert report['raw_zero_pose_only']
    assert not any(report[k] for k in ['electrical_release', 'thermal_release', 'manufacturing_release',
                                     'continuous_sweep_pass', 'full_assembly_pass', 'frozen003_modified'])


def test_finite_motion_preserves_yaw_roll_range_and_passive_linkage():
    report = read('evidence/brake_motion_clearance.json')
    for relative,digest in report['source_hashes'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    assert report['finite_pose_pass'] and report['sampled_poses']==21
    assert report['zero_fk_raw_coordinate_identity_pass'] and report['passive_linkage_mimic_used']
    contract = read('configs/mechanical_physics_contract.json')
    ranges = {j['name']:j['range_rad'] for j in contract['joints']}
    corners = [c['joint_q_rad'] for c in report['cases'] if 'yaw_roll_corner' in c['name']]
    assert len(corners)==8
    for side in ['right','left']:
        values = {(q[side+'_hip_yaw'],q[side+'_hip_roll']) for q in corners if side+'_hip_yaw' in q}
        assert values=={(yaw,roll) for yaw in ranges[side+'_hip_yaw'] for roll in ranges[side+'_hip_roll']}
    assert not report['simulation_collision_filters_used']
    assert not report['full_assembly_pass'] and not report['continuous_sweep_pass']
    rejection = read('evidence/brake_motion_rejection.json')
    assert any(r['common']['volume_mm3']>1 for c in rejection['failed_cases'] for r in c['failed_pairs'])
    for relative,digest in rejection['source_hashes'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest
