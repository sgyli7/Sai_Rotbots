"""Electrical design budgets; never equates a mechanical-power cap to bus watts."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'

def main():
    src=R/'hardware/stage_two_power_architecture.json';p=json.loads(src.read_text());c=json.loads((R/'configs/stage_two_contract.json').read_text());a=p['system_power_assumptions'];pcb=p['pcb_design_requirements'];arch=p['architecture']
    power=[a['positive_mechanical_limit_w']/eta+a['electronics_and_5v_input_allowance_w'] for eta in a['electrical_conversion_efficiency_assumed']]
    current=[x/a['planned_battery_low_loaded_v'] for x in power];wh=arch['battery_nominal_v']*2.2*a['usable_battery_energy_fraction_assumed']
    cap=.5*a['main_capacitance_example_f']*(a['illustrative_regen_max_v']**2-a['illustrative_regen_initial_v']**2);drop=c['nominal_robot_mass_kg']*9.81*a['crouch_height_m']
    can=[(n*pcb['frames_per_axis_per_update']*pcb['update_hz']+pcb['transient_diagnostics_frames_per_s'])*pcb['worst_case_frame_bits_budget']/pcb['can_bitrate_bps'] for n in arch['axis_allocation']]
    fits=[dict(name=b['name'],body_fits_reservation=all(x<=y for x,y in zip(b['supplier_size_mm'],b['allocated_size_mm'])),bare_board_mass_fits_reservation=b['supplier_mass_g']<=b['allocated_mass_g'],connector_and_thermal_fit_verified=False) for b in p['branches']]
    report=dict(status='ELECTRICAL_BUDGET_WITH_EXPLICIT_SUPPLIER_BLOCKERS',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),contract_sha256=hashlib.sha256((R/'configs/stage_two_contract.json').read_bytes()).hexdigest(),estimated_input_w_at_350w_mechanical_assumed_efficiency=power,estimated_input_a_at_20v=current,main_40a_requirement_exceeds_estimate=max(current)<40,runtime_scenarios_minutes={str(w):wh/w*60 for w in a['average_electrical_power_scenarios_w']},runtime_is_not_measured=True,can_scheduled_utilization_per_bus=can,can_utilization_below_70pct=all(v<.7 for v in can),can_retries_and_firmware_latency_not_verified=True,converter_envelopes=fits,regen=dict(single_80mm_drop_potential_energy_j=drop,capacitor_energy_window_j=cap,drop_to_capacitor_energy_ratio=drop/cap,pulse_absorption_requirement_j=a['pulse_absorption_design_j'],component_rating_validated=False),battery_direct_connection_released=False,hardware_freeze_passed=False,unresolved_ids=[x['id'] for x in p['unresolved']],standstill_copper_losses_bounded=False,power_estimate_scope=a['power_estimate_scope'],scope='Sizing requirements and conditional energy scenarios; no electrical circuit, live battery, or thermal acceptance is implied')
    (R/'evidence/stage_two_power_gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
