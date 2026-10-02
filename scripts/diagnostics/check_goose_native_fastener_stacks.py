"""Dimensioned assembly bill for native links, without inventing preload release."""
from pathlib import Path
import json, hashlib, math, csv

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'

def stack(length, layers, maximum, minimum):
    engagement=length-sum(layers)
    return engagement, minimum-1e-8<=engagement<=maximum+1e-8

def main():
    path=R/'cad/exports/pitch_fork_assembly/manifest.json';m=json.loads(path.read_text())
    facts_path=R/'hardware/stage_three_actuator_mounts.json';facts=json.loads(facts_path.read_text())['catalog']
    contract_path=R/'configs/stage_two_contract.json';selected={j['name']:j['actuator'] for j in json.loads(contract_path.read_text())['joints']}
    rows=[]
    def add(a,role,thread,length,count,layers,maximum,minimum,anchor,shared=False):
        engagement,valid=stack(length,layers,maximum,minimum)
        d=3 if thread=='M3' else 2.5
        # Conservative solid screw envelope, not a catalog weighing. Threads
        # are full cylinders and head is larger than the intended socket head.
        head_d,head_h=(6,4) if d==3 else (5,3)
        volume=math.pi/4*(d*d*length+head_d*head_d*head_h)
        washer_t=layers[-1] if role not in ['bridge','output_to_motor','fork_to_adapter','outer_race_cover','shaft_end','root_spider'] else {'bridge':.5,'output_to_motor':.5 if length==8 else 1.5,'fork_to_adapter':1.,'outer_race_cover':.5,'shaft_end':0.,'root_spider':.5}[role]
        volume+=math.pi/4*((7 if d==3 else 6)**2-(3.2 if d==3 else 2.7)**2)*washer_t
        p=next(p for p in m['parts'] if p['name']==a['name']+'_'+anchor)
        rows.append(dict(assembly=a['name'],role=role,body=p['body'],thread=thread,length_mm=length,count=count,
            clearance_stack_mm=layers,effective_engagement_mm=engagement,minimum_engagement_mm=minimum,maximum_insertion_mm=maximum,
            length_pass=valid,shared_case_bolt=shared,mass_upper_estimate_kg=volume*7850e-9*count,
            center_world_m=p['center_of_mass_world_m'],anchor_part=p['name'],
            released=False))
    for a in m['assemblies']:
        level=a['axial_level'];head=a['name']=='upper_neck'
        output=facts[selected[a['upper_joint']]]['output_mount']
        add(a,'output_to_motor',output['thread'],8 if level==0 else 16,output['count'],[a['output_adapter_thickness_mm'],.5 if level==0 else 1.5],output['max_insertion'],3.,'output_adapter')
        add(a,'fork_to_adapter','M3',10,3,[5.5,1.],a['output_adapter_thickness_mm'],3.,'output_fork_plate')
        add(a,'bridge','M3',12,4,[5.5,.5],8,5,'bridge')
        add(a,'outer_race_cover','M2.5',5,3,[1.,.5],5.5,3,'bearing_outer_retainer')
        add(a,'shaft_end','M3',6,1,[.5],8,5,'stationary_idler_spider')
        if not level:add(a,'root_spider','M3',8,4,[2.,1.,.5],5,4,'stationary_idler_spider')
        if head:
            add(a,'distal_front_case','M2.5',25,6,[a['front_spacer_mm'],5.5,.5],5,3.,'output_fork_plate')
            add(a,'distal_rear_case','M2.5',30,4,[a['rear_spacer_mm'],5.5,.5],5,3.,'idler_fork_plate')
        elif level:
            add(a,'distal_front_case','M3',20,6,[a['front_spacer_mm'],5.5,0.],4,3.,'output_fork_plate')
            add(a,'distal_rear_case','M3',25,4,[a['rear_spacer_mm'],5.5,.5],5,4.,'idler_fork_plate')
        else:
            add(a,'distal_front_case','M3',16,6,[a['front_spacer_mm'],5.5,2.5],4,3.,'output_fork_plate')
            add(a,'distal_rear_case','M3',20,4,[a['rear_spacer_mm'],5.5,2.5],5,4.,'idler_fork_plate',True)
    report=dict(schema='goose_native_fastener_stack_v1',rows=rows,total_screws=sum(x['count'] for x in rows),
        mass_upper_estimate_kg=sum(x['mass_upper_estimate_kg'] for x in rows),length_pass=all(x['length_pass'] for x in rows),
        fastener_release=False,manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,facts_path,contract_path,Path(__file__)]},
        limitations=['Only six native parallel-axis assemblies; feet and cross-axis joints not included',
            'Minimum engagement is a geometry screen, not pullout, fatigue or preload proof',
            'Long standoff screws require local bending/preload verification; bare distal-front M3 heads require bearing-pressure check',
            'Spacer rings and steel shaft-end washer are already in native CAD mass; do not count those twice',
            'Screw/washer upper envelope is not a vendor mass; exact head/washer SKU, torque and lubrication remain unreleased',
            'Three shared distal rear case screws groups also retain the NEXT stationary spider: do not add another root screw group'])
    (R/'hardware/native_pitch_fastener_stacks.json').write_text(json.dumps(report,indent=2)+'\n')
    fields=['assembly','role','thread','length_mm','count','effective_engagement_mm','minimum_engagement_mm','maximum_insertion_mm','length_pass','shared_case_bolt','released']
    with (R/'hardware/native_pitch_fastener_bom.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
    print({k:report[k] for k in ['total_screws','mass_upper_estimate_kg','length_pass']})
    return 0 if report['length_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
