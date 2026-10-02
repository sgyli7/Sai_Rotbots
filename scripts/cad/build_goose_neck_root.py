"""AK40 yaw output to AK45 pitch stator: actual monolithic front cradle."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path[:0]=[str(ROOT/'scripts/cad'),str(ROOT/'scripts/models')]
from build_goose_stage_two import candidate
from build_goose_cad import box,cylinder,holes
from goose_candidate_export import CandidateExport


def main():
    s=candidate();P=s.pivots['neck_yaw']*1000;Q=s.pivots['neck_pitch']*1000
    facts_path=R/'hardware/stage_three_actuator_mounts.json';facts=json.loads(facts_path.read_text())['catalog']
    export=CandidateExport(R,'neck_root_assembly');stacks=[]
    output_z=P[2]+20.1
    adapter=cylinder(22,4,[P[0],P[1],output_z+2])-cylinder(8,10,[P[0],P[1],output_z+2])
    motor=[[P[0]+13.5*np.cos(t),P[1]+13.5*np.sin(t),output_z+2] for t in np.deg2rad([30,150,270])]
    links=[[P[0]+17*np.cos(t),P[1]+17*np.sin(t),output_z+2] for t in np.deg2rad([0,120,240])]
    adapter=holes(adapter,motor,2.7,12,'z');adapter=holes(adapter,links,2.5,12,'z')
    export.emit('neck_yaw_output_adapter',adapter,'neck_yaw',notes=['AK40-10 V3 output3M2.5PCD27, no undocumented pilot depth.','Three M3 through taps PCD34 for front cradle.'])
    z=output_z+6.75;front_y=Q[1]+27.25
    base=cylinder(23,5.5,[P[0],P[1],z])+box([24,front_y+2-P[1],5.5],[P[0],(P[1]+front_y+2)/2,z])
    base=holes(base,[[p[0],p[1],z] for p in links],3.2,14,'z')
    base=holes(base,[[p[0],p[1],z] for p in motor],5.3,14,'z')
    ring=cylinder(30,4,[Q[0],front_y,Q[2]],'y')-cylinder(21,12,[Q[0],front_y,Q[2]],'y')
    low=z+2.75;high=Q[2]-22
    cradle=base+ring+box([24,4,high-low],[Q[0],front_y,(low+high)/2])
    case=[[Q[0]+24*np.cos(t),front_y,Q[2]+24*np.sin(t)] for t in np.deg2rad([30,90,150,210,270,330])]
    cradle=holes(cradle,case,3.2,12,'y')
    export.emit('neck_yaw_to_pitch_front_cradle',cradle,'neck_yaw',notes=['One CNC6061 billet:5.5mm base,4mm front wall; no unsupported bonded seam.','Pitch stator case front25.25mm,4mm ring ID42 clears the next output adapter R20.','Lower-neck independent rear spider remains neck_yaw-owned and uses the shared case bolts.','Rear case access, actual connectors and OEM yaw output bearing capacity remain gates.'])
    for role,anchor,d,L,count,washer,stack,maximum in [('yaw_output','neck_yaw_output_adapter',2.5,8,3,1.5,4,3),('cradle_base','neck_yaw_output_adapter',3,10,3,1,5.5,4),('pitch_case','neck_yaw_to_pitch_front_cradle',3,8,6,1,4,4)]:
        engagement=L-washer-stack;assert 2.5<=engagement<=maximum
        hd,hh=(5,3) if d==2.5 else (6,4)
        v=np.pi/4*(d*d*L+hd*hd*hh+((6 if d==2.5 else 7)**2-(d+.2)**2)*washer)
        stacks.append(dict(role=role,anchor_part=anchor,body='neck_yaw',thread='M2.5' if d==2.5 else 'M3',length_mm=L,count=count,washer_stack_mm=washer,clamped_stack_mm=stack,engagement_mm=engagement,max_engagement_mm=maximum,mass_upper_estimate_kg=v*7850e-9*count,released=False))
    value=export.save(ROOT,[Path(__file__),ROOT/'scripts/cad/goose_candidate_export.py',facts_path],
        replaces=['neck_yaw_mount','neck_pitch_mount_reserve','neck_yaw_structure_allocation'],
        extra=dict(fasteners=stacks,load_path='torso rear plate -> AK40 yaw stator/output ->4mm adapter -> CNC front cradle -> AK45 pitch stator -> lower-neck fork'))
    print('neck root parts',len(value['parts']),'kg',value['native_mass_kg'],'fasteners kg',sum(p['mass_upper_estimate_kg'] for p in stacks),flush=True)

if __name__=='__main__':main()
