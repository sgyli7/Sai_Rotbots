"""Six short-span TPU leaves per foot, retaining the real aluminium plate."""
from pathlib import Path
import json,sys,numpy as np
from build123d import import_step,Face,Solid,Vector,Pos
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,holes
from goose_candidate_export import CandidateExport


def main():
    path=R/'cad/exports/body_bay_ankle_assembly/manifest.json';data=json.loads(path.read_text())
    export=CandidateExport(R,'short_span_soles');feet=[]
    for side,sign in [('right',-1),('left',1)]:
        p=next(p for p in data['parts'] if p['name']==side+'_ankle_tapped_load_plate')
        plate=import_step(R/p['files']['step']['path'])
        f=[f for f in plate.faces() if abs(f.center().Z-3.5)<1e-6 and abs(f.normal_at().Z)>.99]
        assert len(f)==1
        carrier=Solid.extrude(Face(f[0].outer_wire()),Vector(0,0,1)).moved(Pos(0,0,-1))
        centers=[(x,sign*76+dy) for x in [-47,33,106] for dy in [-18,18]]
        for x,y in centers:
            leaf=box([2,24,4.2],[x-4.75,y,-2.1])+box([2,24,4.2],[x+4.75,y,-2.1])
            leaf+=box([7.5,24,2.7],[x,y,-3.15]);leaf+=box([5,24,1.5],[x,y,-5.25])
            carrier+=leaf.moved(Pos(0,0,2.5))
        fasteners=[[x,sign*76+dy,3] for x in [-42,98] for dy in [-30,30]]
        carrier=holes(carrier,fasteners,3.2,12,'z')
        export.emit(side+'_flexible_sole',carrier,side+'_ankle_roll',rho=1240,material='rubber',notes=['Short span7.5mm, thickness2.7mm, width24mm; six independent open leaves.','Undeformed contactZ-3.5mm; every rigid part must use common4.0mm lift.','1.5mm nominal compression before the pad meets the carrier; spring estimate is not measured TPU calibration.','Existing four sole screws M3x6+1mmspacer+0.5mmwasher,3.5mm aluminium engagement retained.'])
        # Conservative pinned-end rectangular beam with a central force:48EI/L^3.
        # The actual printed integral end walls are neither an ideal pin nor a
        # measured fixed boundary. Also store192EI/L^3 as the fixed-end ideal.
        stiffness=[4*E*24*2.7**3/7.5**3 for E in [3.8,4.4,5.0]]
        feet.append(dict(side=side,pad_centers_world_xy_mm=[list(p) for p in centers],contact_size_mm=[5,24],leaf_span_mm=7.5,leaf_thickness_mm=2.7,compression_range_mm=1.5,
            assumed_E_mpa=[3.8,4.4,5.0],linear_pinned_end_stiffness_n_per_mm=stiffness,
            linear_fixed_end_stiffness_n_per_mm=[4*k for k in stiffness],
            six_leaf_force_at_1_5mm_n=[6*k*1.5 for k in stiffness],material='Bambu TPU90A',stiffness_is_measured=False))
    value=export.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py',path],replaces=[p['name'] for p in export.parts],
        extra=dict(feet=feet,robot_rigid_coordinate_lift_m=.004,contact_release=False,material_source='https://store.bblcdn.eu/s8/default/8140c9d50a6049a3b634fa1387518d8d/Bambu_TPU_90A_Technical_Data_Sheet_582bf8f6-1f0a-474c-aeda-9e72af3689dc.pdf'))
    print('sole kg',value['native_mass_kg'],'nominal pinned leaf N/mm',feet[0]['linear_pinned_end_stiffness_n_per_mm'][1],flush=True)

if __name__=='__main__':main()
