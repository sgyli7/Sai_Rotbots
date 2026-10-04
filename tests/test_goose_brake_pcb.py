import copy
import json
from pathlib import Path

import pytest

from sai_agent.goose.brake_pcb import require_clean_drc, validate_pcb_candidate

ROBOT = Path(__file__).resolve().parents[1] / 'robots/Goose_V0.1'


def candidate():
    return json.loads((ROBOT / 'configs/brake_pcb_candidate.json').read_text())


def test_series_feedback_preserves_parent_threshold_circuit():
    equivalent = validate_pcb_candidate(candidate())
    parts = {p['ref']: p for p in equivalent['components']}
    assert len(parts) == 46
    assert parts['R3']['value'] == '1650000 ohm'
    assert parts['R3']['pins']['2']['net'] == 'SENSE'
    assert parts['U1']['pins']['7']['net'] is None


@pytest.mark.parametrize('fault', ['feedback_node', 'feedback_value', 'loaded_midpoint',
    'wrong_delay_pin', 'wrong_ldo_package', 'wrong_comparator_package',
    'cap_height', 'copper_edge', 'pretend_release'])
def test_candidate_rejects_wiring_package_and_release_faults(fault):
    cfg = copy.deepcopy(candidate())
    parts = {p['ref']: p for p in cfg['components']}
    if fault == 'feedback_node':
        parts['R31']['pins']['1']['net'] = 'GND'
    elif fault == 'feedback_value':
        parts['R31']['value'] = '820000 ohm'
    elif fault == 'loaded_midpoint':
        parts['J3']['pins']['2']['net'] = 'FEEDBACK_MID'
    elif fault == 'wrong_delay_pin':
        parts['U1']['pins']['7']['net'] = 'GND'
    elif fault == 'wrong_ldo_package':
        cfg['footprints']['dgn8']['pads'][-1]['size_mm'] = [1.6, 2.0]
    elif fault == 'wrong_comparator_package':
        cfg['footprints']['dbv5']['pads'][0]['at_mm'] = [-1.1, -.65]
    elif fault == 'cap_height':
        cfg['footprints']['f12']['max_height_mm'] = 12.6
    elif fault == 'copper_edge':
        cfg['placements_mm']['R31'] = [0, 0]
    else:
        cfg['hardware_enable_release'] = True
    with pytest.raises(ValueError):
        validate_pcb_candidate(cfg)


def test_committed_native_drc_is_complete_and_clean():
    counts = require_clean_drc((ROBOT / 'evidence/brake_pcb_native_drc.txt').read_text())
    assert counts == {'violations': 0, 'unconnected': 0, 'footprint_errors': 0}


@pytest.mark.parametrize('fault', ['short', 'open', 'library', 'truncated', 'duplicate', 'stray_error'])
def test_native_drc_acceptance_rejects_partial_or_failed_reports(fault):
    text = (ROBOT / 'evidence/brake_pcb_native_drc.txt').read_text()
    if fault in ['short', 'open', 'library']:
        token = {'short': '0 DRC violations', 'open': '0 unconnected pads',
            'library': '0 Footprint errors'}[fault]
        text = text.replace(token, token.replace('0', '1', 1))
    elif fault == 'truncated':
        text = text.replace('** End of Report **', '')
    elif fault == 'duplicate':
        text += '\n** Found 0 unconnected pads **\n'
    else:
        text += '\n[shorting_items]: hidden diagnostic\n'
    with pytest.raises(ValueError):
        require_clean_drc(text)
