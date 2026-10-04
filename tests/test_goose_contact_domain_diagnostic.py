"""Validate the diagnostic against an untouched native source replay."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import copy

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location('contact_domain', ROOT / 'scripts/evaluation/check_goose_contact_domain.py')
diagnostic = module_from_spec(spec)
spec.loader.exec_module(diagnostic)
MODEL = ROOT / 'robots/Goose_V0.1/models/task_proxy_11_v1/robot.xml'
CONTRACT = ROOT / 'robots/Goose_V0.1/configs/task_proxy_11_v1_contract.json'


@pytest.fixture(scope='module')
def falling_case():
    hashes = {p: diagnostic.sha(p) for p in [MODEL, CONTRACT]}
    result, trace = diagnostic.scenario('pitch', 45, 20, MODEL, CONTRACT)
    assert {p: diagnostic.sha(p) for p in hashes} == hashes
    return result, trace


def test_observation_wrapper_keeps_untouched_source_trajectory(falling_case):
    result, trace = falling_case
    replay = diagnostic.verify_uninstrumented_replay(result, trace, MODEL, CONTRACT)
    assert replay['exact_qpos_qvel_match']
    assert result['completed_ticks'] == 20
    assert result['all_retained_native_contacts_identical']
    assert not result['full_recovery_qualification']
    assert result['initial_geometry_clearance_m'] == pytest.approx(.002, abs=1e-10)


def test_known_first_head_impact_is_visible_after_integration(falling_case):
    result, trace = falling_case
    step = trace[result['worst_tick'] - 1]
    head = 'head_upper_bill_envelope'
    assert result['worst_tick'] == 15 and result['worst_geom'] == head
    assert step['contacts']['pre_geom_minimum_height_m'][head] > 0.
    assert step['post_geom_minimum_height_m'][head] < -.03
    assert step['contacts']['quadrature_geoms'] == []
    assert step['contacts']['native_before'] == step['contacts']['after_quadrature']
    assert all(head not in c['geoms'] for c in step['contacts']['native_before'])


def test_tampered_record_is_rejected_by_native_replay(falling_case):
    result, trace = falling_case
    altered = copy.deepcopy(trace)
    altered[2]['qpos'][0] += 1e-6
    with pytest.raises(ValueError, match='tick 3: qpos'):
        diagnostic.verify_uninstrumented_replay(result, altered, MODEL, CONTRACT)
