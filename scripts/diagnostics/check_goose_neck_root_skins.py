"""Native neck-root yaw fit against the two current forebody skins."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from build123d import import_step
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder,transform
from sai_agent.native_cad import common_solid_volume_mm3 as overlap


def main():
    paths=[R/'cad/exports/neck_root_assembly/manifest.json',R/'cad/exports/neck_access_skins/manifest.json',R/'evidence/body_bay_mechanical_parameters.json']
    neck,skin,ledger=[json.loads(p.read_text()) for p in paths];moving={};fixed={}
    for m,destination in [(neck,moving),(skin,fixed)]:
        for p in m['parts']:
            for f in p['files'].values():assert hashlib.sha256((R/f['path']).read_bytes()).hexdigest()==f['sha256']
            destination[p['name']]=import_step(R/p['files']['step']['path']).solids()[0]
    moving['neck_pitch_stator']=cylinder(27.5,53.5,[43,-1.5,408],'y')
    pivot=np.array(ledger['pivots_world_at_zero_m']['neck_yaw'])*1000-[0,0,ledger['rigid_coordinate_lift_m']*1000]
    cases=[]
    for yaw in np.linspace(-.5,.5,15):
        rot=Rotation.from_rotvec([0,0,yaw]).as_matrix();hits=[]
        for n,s in moving.items():
            moved=transform(s,rot,pivot-rot@pivot)
            for name,other in fixed.items():
                v=overlap(moved,other)
                if v>.01:hits.append(dict(a=n,b=name,intersection_mm3=v))
        cases.append(dict(yaw_rad=float(yaw),collisions=hits,native_skin_fit_pass=not hits))
    report=dict(schema='goose_neck_root_native_skin_fit_v1',cases=cases,native_pair_checks=90,passed_samples=sum(c['native_skin_fit_pass'] for c in cases),sample_count=15,
        whole_neck_release=False,manufacturing_pass=False,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
        limitations=['Two root parts and pitch stator against two forebody skins;no lower-fork/cable/connector or full pitch sweep certification.','15yaw samples inside current[-.5,.5]candidate limits;not continuous clearance or shaft-bearing capacity proof.'])
    (R/'evidence/neck_root_skin_screen.json').write_text(json.dumps(report,indent=2)+'\n');print('NECK ROOT',report['passed_samples'],'/15',flush=True)
    return 0 if report['passed_samples']==15 else 1

if __name__=='__main__':raise SystemExit(main())
