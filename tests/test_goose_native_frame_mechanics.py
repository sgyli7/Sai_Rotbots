"""Analytical checks independent of the robot's selected frame dimensions."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import json

ROOT=Path(__file__).resolve().parents[1]

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

frame=load('goose_frame_screen','scripts/diagnostics/screen_goose_fork_frames.py')
stacks=load('goose_stacks','scripts/diagnostics/check_goose_native_fastener_stacks.py')

@pytest.mark.parametrize('dof,force,expected',[
    (0,25.,25.*100/(69000*80)),
    (1,10.,10.*100**3/(3*69000*500)),
    (2,12.,12.*100**3/(3*69000*1000)),
    (3,200.,200.*100/(26538*100)),
])
def test_rotated_frame_matches_axial_bending_and_torsion(dof,force,expected):
    a=np.array([23.,-15.,18.]);direction=np.array([2.,3.,4.]);direction/=np.linalg.norm(direction)
    K,local,T,_=frame.beam(a,a+direction*100,69000,26538,80,1000,500,100,[0,1,0])
    f=np.zeros(12);f[dof+6]=force;world=T.T@f
    u=np.zeros(12);u[6:]=np.linalg.solve(K[6:,6:],world[6:]);ul=T@u
    assert ul[dof+6]==pytest.approx(expected,rel=1e-11)
    assert np.allclose(K,K.T,rtol=1e-12,atol=1e-9)
    reaction=T@(K@u-world)
    assert reaction[dof]==pytest.approx(-force,rel=1e-10)

def test_beam_has_six_rigid_body_modes():
    K,*_=frame.beam(np.zeros(3),[100.,0,0],69000,26538,80,1000,500,100,[0,1,0])
    values=np.linalg.eigvalsh(K)
    assert sum(abs(values)<1e-6)==6
    assert min(values)>-1e-6

@pytest.mark.parametrize('length,layers,maximum,minimum,ok',[
    (16,[11.5,5.5],4,3,False), # standard short screw never reaches the case
    (25,[11.5,5.5],4,3,False), # too long can hit motor internals
    (20,[11.5,5.5],4,3,True),
    (25,[15.15,5.5,.5],5,3,True),
    (10,[5.5,1],4,3,True),
])
def test_screw_insertion_rejects_short_and_bottoming(length,layers,maximum,minimum,ok):
    _,valid=stacks.stack(length,layers,maximum,minimum)
    assert valid is ok

def test_all_vendor_output_mount_holes_have_a_bom_screw():
    r=ROOT/'robots/Goose_V0.1'
    facts=json.loads((r/'hardware/stage_three_actuator_mounts.json').read_text())['catalog']
    selected={p['name']:p['actuator'] for p in json.loads((r/'configs/stage_two_contract.json').read_text())['joints']}
    assemblies={p['name']:p for p in json.loads((r/'cad/exports/pitch_fork_assembly/manifest.json').read_text())['assemblies']}
    rows=json.loads((r/'hardware/native_pitch_fastener_stacks.json').read_text())['rows']
    for row in [p for p in rows if p['role']=='output_to_motor']:
        joint=assemblies[row['assembly']]['upper_joint']
        assert row['count']==facts[selected[joint]]['output_mount']['count']
        assert row['thread']==facts[selected[joint]]['output_mount']['thread']
