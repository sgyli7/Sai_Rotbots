"""Sample a staged low-reach path on the current whole collision candidate.

No training, root forces or collision-tolerance changes. Uses the model's
documented mating-pin and adjacent-body collision filtering unchanged.
This geometry path cannot certify grasp contact, balance control or cables.
"""
from pathlib import Path
import hashlib,json,sys
import mujoco
import numpy as np
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate
from sai_agent.goose.native_linkage import set_passive_linkage


def main():
    paths=[R/'configs/mechanical_physics_contract.json',R/'models/mechanical_physics/robot.xml',R/'evidence/body_bay_mechanical_parameters.json',R/'configs/mechanical_task_poses.json']
    c,l=[json.loads(p.read_text()) for p in [paths[0],paths[2]]]
    for path,h in c['source_hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,('stale',path)
    m=mujoco.MjModel.from_xml_path(str(paths[1]));d=mujoco.MjData(m)
    s=candidate();s.pivots={k:np.array(v) for k,v in l['pivots_world_at_zero_m'].items()}
    s.grip=np.array(l['grip_world_at_zero_m']);s.tip=np.array(l['tip_world_at_zero_m'])
    names=c['joint_order'];qadr=[m.joint(n).qposadr[0] for n in names];lookup={g['name']:g['part'] for g in c['collision_geometries']}
    task=json.loads(paths[3].read_text())['low_reach'];drop=task['crouch_drop_mm']
    neck={n:task[n+'_rad'] for n in ['neck_pitch','neck_mid_pitch','head_pitch']}
    samples=[]
    # Lower neck and upper head prepare while high above the floor, then
    # crouch vertically. This is an explicit two-segment candidate task.
    for f in np.linspace(0,1,41):
        q,p,rot=s.pose(0);q.update({k:v*f for k,v in neck.items()});samples.append(('neck_prepare',float(f),q,p,rot))
    for f in np.linspace(0,1,31)[1:]:
        q,p,rot=s.pose(drop*f);q.update(neck);samples.append(('crouch',float(f),q,p,rot))
    for angle in np.linspace(0,.55,12)[1:]:
        q,p,rot=s.pose(drop);q.update(neck);q['beak_hinge']=float(angle);samples.append(('beak_open',float(angle),q,p,rot))
    records=[]
    for index,(phase,parameter,q,p,rot) in enumerate(samples):
        mujoco.mj_resetData(m,d);d.qpos[:3]=p;d.qpos[3:7]=[1,0,0,0];d.qpos[qadr]=[q.get(n,0) for n in names]
        set_passive_linkage(m,d,c);mujoco.mj_forward(m,d)
        violations=[j['name'] for j in c['joints'] if not j['range_rad'][0]<=q.get(j['name'],0)<=j['range_rad'][1]]
        hits=[]
        for contact in d.contact:
            a,b=[m.geom(int(g)).name for g in contact.geom]
            if contact.dist>=-.0002:continue
            if 'ground' in [a,b]:
                other=b if a=='ground' else a
                if 'sole_pad' in other or lookup.get(other,'').endswith('_flexible_sole'):continue
            hits.append(dict(part_a=lookup.get(a,a),part_b=lookup.get(b,b),depth_m=float(-contact.dist)))
        poses,_=s.fk(q,root_p=p,root_r=rot);hp,hr=poses['head_roll'];grip=hp+hr@(s.grip-s.pivots['head_roll'])
        record=dict(index=index,phase=phase,parameter=parameter,joint_q_rad=q,root_position_m=p.tolist(),
                    grip_world_m=grip.tolist(),limit_violations=violations,contact_candidates=hits,geometry_screen_pass=not hits and not violations)
        records.append(record)
        if hits:print('PATH FAIL',index,phase,'contacts',len(hits),flush=True)
    report=dict(schema='goose_ground_reach_path_candidate_v1',samples=records,passed_samples=sum(r['geometry_screen_pass'] for r in records),sample_count=len(records),
                closed_beak_ground_target_m=records[70]['grip_world_m'],full_beak_open_geometry_pass=all(r['geometry_screen_pass'] for r in records if r['phase']=='beak_open'),
                motion_control_pass=False,actual_grasp_pass=False,manufacturing_pass=False,training_release=False,
                source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
                limitations=['Discrete geometric samples, not continuous swept CAD or root balance control.',
                             '1mm CoACD concavity is approximate; every collision candidate needs native CAD confirmation.',
                             'Soft tread contacts excluded only from ground penetration rejection; all other floor and self contacts retained.',
                             'No actual object, cable, sensor tracking or task execution controller is demonstrated.'])
    (R/'evidence/mechanical_ground_reach_path.json').write_text(json.dumps(report,indent=2)+'\n')
    print('GROUND PATH',report['passed_samples'],'/',len(records),'grip',report['closed_beak_ground_target_m'],flush=True)
    return 0 if report['passed_samples']==len(records) else 1


if __name__=='__main__':raise SystemExit(main())
