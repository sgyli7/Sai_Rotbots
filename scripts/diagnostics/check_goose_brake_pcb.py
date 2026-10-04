"""Fresh-copy native PCB, schematic association and deliberately broken boards.

Run with the same pcbnew/kicad-cli runtime used by the builder. No ERC, current
capacity, manufacture or cold-start qualification is inferred from these checks.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET

import pcbnew as pcb
from sai_agent.goose.brake_pcb import require_clean_drc, validate_pcb_candidate

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kicad-cli', required=True, type=Path)
    args = parser.parse_args()
    config = ROBOT / 'configs/brake_pcb_candidate.json'
    cfg = json.loads(config.read_text())
    validate_pcb_candidate(cfg)
    source = ROBOT / 'hardware/brake_pcb_candidate'
    work = ROOT / 'artifacts/Goose_V0.1/brake_pcb_review_20261004/native_reload'
    work.mkdir(parents=True, exist_ok=True)
    copied = work / 'copied_project'
    shutil.copytree(source, copied, dirs_exist_ok=True)
    filename = copied / 'brake_pcb_candidate.kicad_pcb'
    board = pcb.LoadBoard(str(filename))
    report_path = work / 'copied_drc.txt'
    report_path.unlink(missing_ok=True)
    if not pcb.WriteDRCReport(board, str(report_path), pcb.EDA_UNITS_MILLIMETRES, True):
        raise ValueError('copied native DRC generation failed')
    clean = require_clean_drc(report_path.read_text())
    # Native schematic export, not a comparison to a second generated netlist.
    netlist = work / 'native_netlist.xml'
    netlist.unlink(missing_ok=True)
    proc = subprocess.run([str(args.kicad_cli.resolve()), 'sch', 'export', 'netlist',
        '--format', 'kicadxml', '-o', str(netlist),
        str(copied / 'brake_pcb_candidate.kicad_sch')],
        text=True, capture_output=True, check=True)
    if 'error' in (proc.stdout + proc.stderr).lower():
        raise ValueError('native schematic export diagnostics')
    tree = ET.parse(netlist)
    expected = {}
    for p in cfg['components']:
        for n, pin in p['pins'].items():
            if pin['net'] is not None:
                expected.setdefault(pin['net'], set()).add((p['ref'], n))
    actual = {n.attrib['name'].removeprefix('/'):
        {(i.attrib['ref'], i.attrib['pin']) for i in n.findall('node')}
        for n in tree.findall('.//nets/net')
        if not n.attrib['name'].startswith('unconnected-')}
    if actual != expected:
        raise ValueError('native schematic pin-to-net mismatch')
    components = {c.attrib['ref']: c for c in tree.findall('.//components/comp')}
    fps = {p.GetReference(): p for p in board.GetFootprints()}
    associated = 0
    root_id = re.search(r'\(uuid ([0-9a-f-]+)\)',
        (copied / 'brake_pcb_candidate.kicad_sch').read_text()).group(1)
    for p in cfg['components']:
        if p['kind'] == 'external_resistor':
            continue
        ref = p['ref']
        expected_fp = 'GooseBrake:' + cfg['footprints'][p['footprint']]['name']
        if components[ref].findtext('footprint') != expected_fp:
            raise ValueError('native schematic footprint field mismatch')
        part_id = components[ref].findtext('tstamps')
        if part_id != str(uuid.uuid5(uuid.NAMESPACE_URL, 'sai-robots/goose/brake-v1/' + ref)):
            raise ValueError('native schematic instance identity changed')
        if fps[ref].GetPath().AsString() != '/' + root_id + '/' + part_id:
            raise ValueError('PCB schematic instance path mismatch')
        associated += 1
    # Two failures observed in this implementation must remain detectable:
    # collapsing pads during serialize/reload, and signal routing left open.
    faults = {}
    for name in ['collapsed_u1_pads', 'open_feedback_mid']:
        faulty = pcb.LoadBoard(str(filename))
        if name == 'collapsed_u1_pads':
            fp = next(f for f in faulty.GetFootprints() if f.GetReference() == 'U1')
            for pad in fp.Pads():
                if pad.GetNumber():
                    pad.SetPos0(pcb.VECTOR2I(0, 0))
                    pad.SetPosition(fp.GetPosition())
        else:
            removed = 0
            for track in list(faulty.GetTracks()):
                if track.GetNetname() == 'FEEDBACK_MID':
                    faulty.Remove(track)
                    removed += 1
            if not removed:
                raise ValueError('negative control did not alter routing')
        # Keep the same project/library context: an unrelated missing-library
        # warning must never stand in for detecting the injected physical fault.
        faultfile = copied / (name + '.kicad_pcb')
        pcb.SaveBoard(str(faultfile), faulty)
        if sha(faultfile) == sha(filename):
            raise ValueError('negative control mutation did not serialize')
        faulty = pcb.LoadBoard(str(faultfile))
        drc = work / (name + '_drc.txt')
        drc.unlink(missing_ok=True)
        if not pcb.WriteDRCReport(faulty, str(drc), pcb.EDA_UNITS_MILLIMETRES, True):
            raise ValueError('negative native DRC generation failed')
        counts = {key: int(re.search(pattern, drc.read_text()).group(1)) for key, pattern in {
            'violations': r'\*\* Found (\d+) DRC violations',
            'unconnected': r'\*\* Found (\d+) unconnected pads',
            'footprint_errors': r'\*\* Found (\d+) Footprint errors'}.items()}
        if 'does not include the library' in drc.read_text():
            raise ValueError('negative control lost its project library context')
        if name == 'collapsed_u1_pads':
            fp = next(f for f in faulty.GetFootprints() if f.GetReference() == 'U1')
            lands = [p for p in fp.Pads() if p.GetNumber()]
            if len(lands) != 9 or any(p.GetPosition() != fp.GetPosition() for p in lands):
                raise ValueError('negative control did not reload collapsed lands')
            if '[clearance]' not in drc.read_text() or 'actual 0.0000 mm' not in drc.read_text():
                raise ValueError('native checker did not detect collapsed electrical lands')
        try:
            require_clean_drc(drc.read_text())
        except ValueError:
            pass
        else:
            raise ValueError('broken board unexpectedly accepted')
        if name == 'open_feedback_mid' and counts['unconnected'] == 0:
            raise ValueError('native connectivity did not detect missing feedback route')
        faults[name] = {'rejected': True, 'counts': counts, 'board_sha256': sha(faultfile),
            'native_report_sha256': sha(drc)}
    result = {'schema': 'goose_brake_pcb_native_reload_v1', 'native_version': pcb.Version(),
        'source_config_sha256': sha(config), 'source_board_sha256': sha(filename),
        'fresh_copy_drc_counts': clean, 'native_schematic_nets': len(actual),
        'native_schematic_connected_pins': sum(map(len, actual.values())),
        'schematic_pcb_instance_associations': associated,
        'native_netlist_sha256': sha(netlist), 'negative_controls': faults,
        'passed': True, 'erc_qualified': False, 'system_release': False,
        'si_or_runtime_changed': False}
    (ROBOT / 'evidence/brake_pcb_native_reload.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
