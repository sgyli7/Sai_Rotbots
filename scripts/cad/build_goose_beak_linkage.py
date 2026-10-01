"""Native equal-crank linkage candidate with real mounting holes and bushes.

Crank240deg avoids the AK45 outputM3 holes;225deg left only0.4mm web.
This kit is not integrated: upper/lower bill load paths and calibrated torque,
thread strength, exact bush tolerances and moving inertias remain release gates.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from build123d import Pos,Rot
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import box,cylinder,holes
from goose_candidate_export import CandidateExport

M=np.array([129.,0.,601.]);J=np.array([160.,0.,576.]);PHASE=np.deg2rad(240.);RAD=12.
D=RAD*np.array([np.cos(PHASE),0,np.sin(PHASE)]);A=M+D;B=J+D


def bar(a,b,width,depth,y):
    a=np.array(a);b=np.array(b);d=b-a;L=float(np.linalg.norm(d[[0,2]]));angle=float(-np.rad2deg(np.arctan2(d[2],d[0])))
    c=(a+b)/2;c[1]=y
    return Pos(*c)*Rot(0,angle,0)*box([L,depth,width])


def main():
    e=CandidateExport(R,'beak_native_linkage')
    flange=cylinder(18,6,[129,29.25,601],'y')
    mounts=[[129+13.5*np.cos(a),29.25,601+13.5*np.sin(a)] for a in np.deg2rad([30,90,150,210,270,330])]
    flange=holes(flange,mounts,3.2,9,'y')
    guides=[[129+12*np.cos(a),29.25,601+12*np.sin(a)] for a in np.deg2rad([60,180,300])]
    flange=holes(flange,guides,4.1,9,'y')
    flange-=cylinder(1.65,4.5,[A[0],30,A[2]],'y') #M4tap major overlap is an intended threaded interface
    e.emit('beak_native_input_flange',flange,'head_roll',notes=['AK45-36 output6M3PCD27,3guide holesPCD24;6mm flange Y26.25..32.25.','Crank12mm at240deg;M4tap drill3.3,4.5mm blind engagement. Pin moves with input rotor; rigid-body reduction not integrated.'])
    arm=bar(J,B,12,4.5,30)+cylinder(6,4.5,[B[0],30,B[2]],'y')+cylinder(8.5,4.5,[160,30,576],'y')
    hole=cylinder(4.05,8,[160,30,576],'y')-box([10,12,12],[152,30,576]) #Dflat atX157
    arm-=hole;arm-=cylinder(1.65,4.5,[B[0],30,B[2]],'y')
    e.emit('beak_native_output_arm',arm,'beak_hinge',notes=['8.1mm nominal D-flat bore X157,positive shaft key; fit and axial retention unreleased.','4.5mm CNC arm Y27.75..32.25;12mm crank240deg,4.5mm M4through engagement.'])
    coupler=bar(A,B,10,4,35)+cylinder(6,4,[A[0],35,A[2]],'y')+cylinder(6,4,[B[0],35,B[2]],'y')
    coupler=holes(coupler,[[A[0],35,A[2]],[B[0],35,B[2]]],6.05,8,'y')
    e.emit('beak_native_coupler',coupler,'head_roll',notes=['Pin centre distance39.824616mm;equal uncrossed cranks1:1ideal output.','OD6 bush seats6.05nominal,4mm plate Y33..37; actual press-fit drawing/vendor flange dimensions remain gates.','Coupler translates by D(q)-D(0); no body-tree approximation is released here.'])
    for name,p,owner in [('input',A,'head_roll'),('output',B,'beak_hinge')]:
        bush=(cylinder(3,4,[p[0],35,p[2]],'y')+cylinder(5,.5,[p[0],32.75,p[2]],'y'))-cylinder(2.51,9,[p[0],35,p[2]],'y')
        e.emit('beak_'+name+'_bush_candidate',bush,'head_roll',rho=1410,material='graphite',notes=['igusGFM0506-05 nominal5/6/5mm family;0.5mm flange here is explicit installation candidate,not a verified supplier dimension.'])
        sleeve=cylinder(2.5,5,[p[0],34.75,p[2]],'y')-cylinder(2.05,9,[p[0],34.75,p[2]],'y')
        e.emit('beak_'+name+'_steel_sleeve',sleeve,owner,rho=7850,material='titanium',notes=['Own steel sleeve5OD/4.1ID/5long; bolt clamps sleeve,plastic bush rotates outside.','C45/strength/finish and wear tolerance still require release.'])
        washer=cylinder(4,.5,[p[0],37.5,p[2]],'y')-cylinder(2.05,3,[p[0],37.5,p[2]],'y')
        e.emit('beak_'+name+'_washer',washer,owner,rho=7850,material='titanium',notes=['M4washer8OD/4.1ID/.5thick candidate,exact commoditySKU pending.'])
        screw=cylinder(2,10,[p[0],32.75,p[2]],'y')+cylinder(3.8,2.2,[p[0],38.85,p[2]],'y')
        e.emit('beak_'+name+'_button_screw',screw,owner,rho=7850,material='titanium',notes=['ISO7380-1 M4x10 property10.9 dimension envelope;driver socket/thread helices omitted.','HeadY37.75..39.95;thread engagements4.5mm input/output require preload/thread-pullout proof.'])
    shaft=cylinder(4,76,J,'y')
    # Preserve round journals atfront20.5..26.5,rear-29.5..-23.5.
    for lo,hi in [(-20.,19.),(27.75,38.)]:shaft-=box([6,hi-lo,12],[154,0.5*(lo+hi),576])
    e.emit('beak_native_d_shaft',shaft,'beak_hinge',rho=7850,material='titanium',notes=['8mm steel shaft76long;DflatX157 only in central keyed andfront output zones.','698journal bands remain circular. Axial retainers,heat-treatment specification and tolerances remain unclosed.'])
    nearest=min(float(np.linalg.norm((p-A)[[0,2]])) for p in mounts)
    transmission_angles=[float(abs(np.sin(PHASE-q-np.arctan2(J[2]-M[2],J[0]-M[0])))) for q in np.linspace(0,.55,56)]
    facts=dict(status='NATIVE_LINKAGE_CANDIDATE_NOT_INTEGRATED',motor_axis_world_mm=M.tolist(),jaw_axis_world_mm=J.tolist(),crank_radius_mm=12,closed_phase_rad=float(PHASE),coupler_spacing_mm=float(np.linalg.norm((J-M)[[0,2]])),
        maximum_output_candidate_nm=4.4,minimum_absolute_transmission_sine=min(transmission_angles),
        worst_ideal_pin_force_n=4.4/.012/min(transmission_angles),nearest_M3_to_M4_hole_web_mm=nearest-1.6-1.65,
        exact_bush_flange_verified=False,shaft_retention_released=False,moving_inertia_released=False,
        manufacturing_released=False,whole_head_release=False)
    replaces=['beak_input_crank','beak_output_crank','beak_output_hub','beak_coupler',
              'beak_input_pin','beak_output_pin','beak_supported_output_shaft',
              'beak_bush_fastener_allowance']
    e.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py',R/'hardware/stage_three_actuator_mounts.json',R/'cad/exports/head_load_path/manifest.json'],replaces=replaces,extra=facts)
    print('LINKAGE parts',len(e.parts),'kg',sum(p['mass_kg'] for p in e.parts),'hole web',facts['nearest_M3_to_M4_hole_web_mm'],'pin force',facts['worst_ideal_pin_force_n'],flush=True)

if __name__=='__main__':main()
