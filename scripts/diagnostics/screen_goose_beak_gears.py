"""Compare jaw torque with primary catalog references; never a release decision."""
from pathlib import Path
import hashlib,json,math
R=Path(__file__).resolve().parents[2]/'robots/Goose_V0.1'
def main():
    path=R/'hardware/beak_gear_catalog_screen.json'; cfg=json.loads(path.read_text()); t=cfg['target']
    output=t['contact_force_n']*t['contact_lever_mm']/1000
    trials=[]
    for p in cfg['pairs']:
        ratio=p['output_teeth']/p['pinion_teeth']; required=output/ratio/t['assumed_total_efficiency']
        pinion_radius=p['module_mm']*p['pinion_teeth']/2000
        force_bound=required/pinion_radius/math.cos(math.radians(t['pressure_angle_deg']))
        loads={'pinion':required,'output':output}
        margins={k:{mode:p[k][mode+'_reference_nm']/loads[k] for mode in ('bending','surface')} for k in loads}
        trials.append(dict(name=p['name'],output_torque_nm=output,motor_torque_nm=required,
            center_distance_mm=p['module_mm']*(p['pinion_teeth']+p['output_teeth'])/2,
            gear_pair_catalog_mass_kg=p['pinion']['mass_kg']+p['output']['mass_kg'],
            conservative_tooth_normal_force_n=force_bound,catalog_reference_margins=margins,
            exceeds_any_reference=any(x<1 for d in margins.values() for x in d.values()),
            disposition='REFERENCE_SCREEN_ONLY_NOT_SELECTED'))
    report=dict(status='CATALOG_COMPARISON_NOT_RELEASE',input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pairs=trials,
        limitations=['Catalog numbers refer to intact standard gears, not custom cut sectors or thin hubs',
            'Efficiency is a total-drive assumption; attributing all losses to tooth force gives a conservative load bound',
            'No actual thermal motor rating, packaging, coupling, shaft, key, bearing, lubrication or tooth fatigue test is certified',
            'The existing 24 mm center distance envelope has no selected gear SKU; this table neither proves nor disproves every possible custom gear at that size'])
    (R/'evidence/beak_gear_catalog_screen.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(trials,indent=2))
if __name__=='__main__':main()
