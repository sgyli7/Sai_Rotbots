"""True native neck opening for the real pitch case and yawing front cradle."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build123d import import_step
from build_goose_cad import cylinder
from goose_candidate_export import CandidateExport


def main():
    prior=R/'cad/exports/body_bay_skins/manifest.json';data=json.loads(prior.read_text());export=CandidateExport(R,'neck_access_skins')
    for p in data['parts']:
        if not p['name'].endswith('_fore'):continue
        shape=import_step(R/p['files']['step']['path']).solids()[0]
        # Native circular cutter makes a smooth opening; no voxel staircase or
        # filled-shell convex approximation is used to repair an interference.
        shape-=cylinder(44,120,[43,0,430])
        export.emit(p['name'],shape,'torso',rho=1270,notes=['Replaces only the body-bay forward half-shell.','Actual circular neck passage R44mm, X43/Y0; cutter spansZ370..490mm.','Opening sized for pitch stator/front cradle under neck yaw; same outer body profile.','Edge trim, shell fasteners and print fit are separate assembly gates.'])
    value=export.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py',prior],replaces=[p['name'] for p in export.parts],
        extra=dict(neck_access=dict(center_xy_mm=[43,0],radius_mm=44,cutter_z_mm=[370,490]),final_appearance_pass=False))
    print('neck-access skins',len(value['parts']),'kg',value['native_mass_kg'],flush=True)

if __name__=='__main__':main()
