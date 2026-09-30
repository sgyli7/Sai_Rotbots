"""Axis identity and CAN/USB-serial budgets, not measured link performance."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];ROBOT=ROOT/'robots/Goose_V0.1'

def main():
    path=ROBOT/'hardware/stage_three_can_layout.json';contract_path=ROBOT/'configs/stage_two_contract.json'
    layout=json.loads(path.read_text());contract=json.loads(contract_path.read_text());budget=layout['budget'];adapter=layout['adapter_candidate']
    expected={j['name'] for j in contract['joints'] if j['name']!='head_roll'};actual=[n for b in layout['motor_buses'] for n in b['axes']];rows=[]
    axis_pass=set(actual)==expected and len(actual)==len(set(actual))==17 and layout['ttl_branch']['axis']=='head_roll'
    for bus in layout['motor_buses']:
        n=len(bus['axes']);frames=n*budget['control_update_hz']*budget['frames_per_axis_per_update']+budget['diagnostic_frames_per_s']
        can_fraction=frames*budget['worst_case_can_frame_bits']/adapter['can_bitrate_bps']
        serial_fraction=frames*budget['fixed_host_frame_bytes']*budget['serial_bits_per_byte_8n1']/adapter['host_serial_baud']
        ids=bus['proposed_node_ids'];identity=len(ids)==n and len(set(ids))==n and all(1<=i<=127 for i in ids)
        rows.append(dict(name=bus['name'],axis_count=n,frames_per_second_budget=frames,can_fraction_budget=can_fraction,serial_8n1_fraction_budget=serial_fraction,identity_pass=identity,analytical_budget_pass=identity and can_fraction<.65 and serial_fraction<.65))
    report=dict(status='ANALYTICAL_CAN_HOST_BUDGET_NOT_MEASURED',axis_partition_pass=axis_pass,budget_pass=axis_pass and all(r['analytical_budget_pass'] for r in rows),hardware_wiring_released=False,checks=rows,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,contract_path,Path(__file__)]},limits=['Frame count, worst-bit estimate and fixed serial framing are assumptions; no ARM64 latency/loss test or motor compatibility test has been run.','A compact supplier candidate is not an installed CAD part; exact mating connector, polarity, grounding and USB current remain unreleased.'])
    (ROBOT/'evidence/manufacturing_can_budget.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    return 0 if report['budget_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
