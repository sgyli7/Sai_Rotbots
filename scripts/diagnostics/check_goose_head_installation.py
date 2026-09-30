"""Actual native half-shell vs named hardware envelopes, including roll sweep.

This bounded assembly probe does not certify the complete head or connector.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
from build123d import import_step
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,cylinder,transform
ROBOT=ROOT/'robots/Goose_V0.1'

def main():
    layout_path=ROBOT/'configs/manufacturing_head_layout.json'
    layout=json.loads(layout_path.read_text());shift=np.array(layout['optical_module_translation_from_stage_two_m'])*1000
    pivot=np.array([81.,0.,585.5]);lo,hi=np.array(layout['head_roll_case_world_bounds_m'])*1000
    roll=box(hi-lo,(hi+lo)/2)
    hardware={'beak_motor_case_envelope':cylinder(27.5,56.5,(129,0,601),'y'),'camera_pcb_envelope':box(np.array(layout['camera_pcb_envelope_size_m'])*1000,np.array([160.3,0,606])+shift),'camera_lens_envelope':cylinder(9,19.69,np.array([170.155,0,606])+shift,'x')}
    fixed={'head_roll_case':roll}
    for name,bb in layout['head_pitch_fixed_envelopes_world_m'].items():
        b=np.array(bb)*1000;fixed[name]=box(b[1]-b[0],b.mean(axis=0))
    records=[]
    for side in ('left','right'):
        file=ROBOT/('cad/exports/manufacturing_skins/goose_head_shell_'+side+'.step');shell=import_step(file)
        for name,solid in hardware.items():
            distance=float(shell.distance_to(solid));common=shell&solid if distance<1e-7 else None
            volume=float(sum(s.volume for s in common.solids())) if common is not None else 0.
            records.append(dict(shell=side,hardware=name,min_distance_mm=distance,intersection_volume_mm3=volume,pass_check=distance>0.1))
        for name,solid in fixed.items():
            rows=[]
            for q in np.linspace(*layout['head_roll_aperture_range_rad'],49):
                r=Rotation.from_rotvec([-q,0,0]).as_matrix();moving=transform(solid,r,pivot-r@pivot)
                distance=float(shell.distance_to(moving));common=shell&moving if distance<1e-7 else None
                volume=float(sum(s.volume for s in common.solids())) if common is not None else 0.
                rows.append(dict(q_rad=float(q),min_distance_mm=distance,intersection_volume_mm3=volume))
            minimum=min(rows,key=lambda r:r['min_distance_mm']);maximum=max(rows,key=lambda r:r['intersection_volume_mm3'])
            records.append(dict(shell=side,hardware=name+'_sweep',sample_count=len(rows),range_rad=layout['head_roll_aperture_range_rad'],worst_gap=minimum,worst_intersection=maximum,pass_check=minimum['min_distance_mm']>0.1,samples=rows))
    manifest=ROBOT/'cad/exports/manufacturing_skins/manifest.json'
    report=dict(status='PARTIAL_NATIVE_HEAD_INSTALLATION_PROBE',partial_installation_pass=all(r['pass_check'] for r in records),manufacturing_pass=False,unit='mm',layout_sha256=hashlib.sha256(layout_path.read_bytes()).hexdigest(),skin_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),checks=records,limitations=layout['remaining_gates']+['sampled roll sweep; case box only, no horn/cable','motor cylinder excludes actual plug, motor thermal limit unvalidated'])
    dest=ROBOT/'evidence/manufacturing_head_installation.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','partial_installation_pass','manufacturing_pass')},indent=2))
    for r in records:print(r['shell'],r['hardware'],r.get('min_distance_mm',r.get('worst_gap')),r['pass_check'])
    return 0 if report['partial_installation_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
