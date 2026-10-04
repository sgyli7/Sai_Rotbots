"""Bounded fixed-head, free-object contact bench on the frozen jaw geometry.

This is deliberately not an 18-axis training environment or a pickup policy.
The local rate-limited jaw PD is capped below the declared source continuous
torque, with the source speed derating and thermal law. No object attachment.
"""
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from sai_agent.goose.task_samples import isolated_jaw_fixture

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'


def bench(sample, *, friction=.65, torque_cap=4.4, out=None):
    source = ROBOT / 'models/task_proxy_11_v1/robot.xml'
    tree, parts, si = isolated_jaw_fixture(source, sample['object_id'], sample['family'], sample['SI']['mass_kg'], friction)
    text = ET.tostring(tree, encoding='unicode')
    m = mujoco.MjModel.from_xml_string(text); d = mujoco.MjData(m)
    m.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_AUTORESET)
    ids = {name: m.joint(name).id for name in ['beak_hinge', 'beak_input_rotor', 'beak_coupler_link']}
    qidx = {name: int(m.jnt_qposadr[j]) for name,j in ids.items()}
    jawv = int(m.jnt_dofadr[ids['beak_hinge']]); obj = m.body(sample['object_id']).id
    for name, multiplier in [('beak_hinge',1), ('beak_input_rotor',1), ('beak_coupler_link',-1)]:
        d.qpos[qidx[name]] = .22*multiplier
    mujoco.mj_forward(m,d)
    geoms = {g for g in range(m.ngeom) if m.geom_bodyid[g] == obj}
    jaws = {m.geom(name).id for name in ['head_upper_bill_envelope','lower_bill_envelope']}
    initial_distances = {f'{m.geom(j).name}/{m.geom(g).name}':float(mujoco.mj_geomDistance(m,d,j,g,1,None)) for j in jaws for g in geoms}
    if min(initial_distances.values()) < -2e-7:
        raise ValueError('Sample starts inside actual jaw hull')
    trace = []; target = .22; thermal = 0.; error = None
    for tick in range(375):
        target = max(0.,target-.02)
        speedcap = 4.5*np.clip(1-abs(d.qvel[jawv])/1.3,0,1)
        thermcap = 4.4 if thermal > 4.4**2 else 4.5
        cap = min(torque_cap,speedcap,thermcap)
        torque = float(np.clip(12*(target-d.qpos[qidx['beak_hinge']])-.15*d.qvel[jawv],-cap,cap))
        thermal += .01*(torque*torque-thermal)
        d.ctrl[:] = torque; mujoco.mj_step(m,d)
        if any(w.number for w in d.warning) or not all(np.isfinite(getattr(d,n)).all() for n in ['qpos','qvel','qacc']):
            error = 'Native warning or nonfinite state; autoreset disabled'; break
        force_by_geom = {}; depth_by_geom = {}
        for ci,contact in enumerate(d.contact):
            if not any(int(g) in geoms for g in contact.geom):
                continue
            other = next(int(g) for g in contact.geom if int(g) not in geoms)
            name = m.geom(other).name
            force = np.zeros(6); mujoco.mj_contactForce(m,d,ci,force)
            force_by_geom[name] = force_by_geom.get(name,0.) + float(force[0])
            depth_by_geom[name] = max(depth_by_geom.get(name,0.),-float(contact.dist))
        # Keep last integration's contact forces; refresh pose only.
        mujoco.mj_kinematics(m,d); mujoco.mj_comPos(m,d)
        trace.append({'tick':tick+1,'time_s':float(d.time),'target_rad':target,'motor_torque_nm':torque,
            'jaw_rad':float(d.qpos[qidx['beak_hinge']]),'jaw_speed_rad_s':float(d.qvel[jawv]),
            'object_origin_m':d.xpos[obj].tolist(),'object_quat_wxyz':d.xquat[obj].tolist(),
            'normal_force_n':force_by_geom,'pre_contact_depth_m':depth_by_geom,
            'connect_coordinate_residual_max_m':float(np.max(np.abs(d.efc_pos[:3])))})
    hold = trace[125:375]
    both = sum(all(row['normal_force_n'].get(m.geom(j).name,0.)>1e-7 for j in jaws) for row in hold)
    # Dynamics minima are not substituted for the sampled native contact gaps.
    result = {'object_id':sample['object_id'],'family':sample['family'],'mass_kg':si['mass_kg'],
        'friction':friction,'torque_cap_nm':torque_cap,'initial_jaw_distances_m':initial_distances,
        'integrations':len(trace),'error':error,'hold_interval_s':[2.5,7.5], 'hold_ticks':len(hold),
        'both_jaws_positive_normal_ticks':both,'dual_contact_hold':len(hold)==250 and both==250,
        'max_jaw_speed_rad_s':max((abs(x['jaw_speed_rad_s']) for x in trace),default=0.),
        'max_jaw_contact_depth_m':max((v for x in trace for k,v in x['pre_contact_depth_m'].items() if k in [m.geom(j).name for j in jaws]),default=0.),
        'max_connect_coordinate_residual_m':max((x['connect_coordinate_residual_max_m'] for x in trace),default=0.),
        'object_origin_range_in_hold_m':np.ptp([x['object_origin_m'] for x in hold],axis=0).tolist() if hold else None,
        'last_state':trace[-1] if trace else None,'native_warning_counts':[int(w.number) for w in d.warning],
        'object_attachment_constraints':0,'fixed_head_bench':True,'full_pickup_qualification':False,
        'contact_quality_qualification':False,'source_18_axis_controller_or_GPU_qualification':False,
        'fixture_sha256':hashlib.sha256(text.encode()).hexdigest()}
    if out:
        stem=f'{sample["object_id"]}_mu{friction:g}_tau{torque_cap:g}'
        (out/f'{stem}.xml').write_text(text+'\n')
        (out/f'{stem}_trace.json').write_text(json.dumps(trace,separators=(',',':'))+'\n')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    catalog_path=ROBOT/'models/task_samples_v1/object_catalog.json';catalog=json.loads(catalog_path.read_text())
    formal=[x for x in catalog['objects'] if not x['development_only']]
    results=[bench(x,out=args.out) for x in formal]
    negative=[]
    for family in ['cylinder_weight','handle_weight']:
        sample=next(x for x in formal if x['family']==family and abs(x['SI']['mass_kg']-.1)<1e-12)
        negative.extend([bench(sample,friction=0.,out=args.out),bench(sample,torque_cap=0.,out=args.out)])
    report={'schema':'goose_task_sample_contact_bench_v1','robot_model_sha256':catalog['robot_model_sha256'],
        'object_catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        'evaluator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'physics_dt_s':.02,'hold_steps':250,'formal_samples':results,'negative_controls':negative,
        'PPO_updates':0,'full_pickup_qualification':False,'contact_quality_qualification':False,
        'scope':'Preplaced free object, fixed head, native actual two jaw hulls and four-bar; no object attachment or full robot balance. Contact and material quality remain unqualified.'}
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'formal':[(r['object_id'],r['dual_contact_hold'],r['max_jaw_contact_depth_m']) for r in results],
        'negative':[(r['object_id'],r['friction'],r['torque_cap_nm'],r['dual_contact_hold']) for r in negative],
        'qualification':False}))


if __name__=='__main__':main()
