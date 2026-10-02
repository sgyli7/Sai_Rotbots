"""Whole candidate contact rejection and bounded free-root stance test.

Does not train a policy or certify walking/turning/manipulation. Reports every
contact candidate, solver warning, early stop and torque clipping explicitly.
"""
from pathlib import Path
import hashlib,json,time
import mujoco
import numpy as np
from sai_agent.goose.native_linkage import set_passive_linkage
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths=[R/'configs/mechanical_physics_contract.json',R/'evidence/body_bay_mechanical_parameters.json',R/'models/mechanical_physics/robot.xml']
    contract,ledger=[json.loads(p.read_text()) for p in paths[:2]]
    for p,h in contract['source_hashes'].items():assert sha(ROOT/p)==h,('stale input',p)
    assert sha(paths[2])==contract['model_sha256']
    for p,h in contract['asset_sha256'].items():assert sha(R/'models/mechanical_physics'/p)==h
    model=mujoco.MjModel.from_xml_path(str(paths[2]));data=mujoco.MjData(model)
    names=contract['joint_order'];qadr=np.array([model.joint(n).qposadr[0] for n in names]);vadr=np.array([model.joint(n).dofadr[0] for n in names])
    actuators=np.array([model.actuator(n+'_motor').id for n in names]);limits=np.array([j['continuous_design_limit_nm'] for j in contract['joints']])
    parts={g['name']:g['part'] for g in contract['collision_geometries']}
    cases=[r for r in ledger['results'] if r['mass_variant']==0 and r['drag_x_n']==0]
    reports=[]
    for case in cases:
        mujoco.mj_resetData(model,data);data.qpos[:3]=case['root_position_m'];data.qpos[3:7]=case['root_quaternion_wxyz']
        desired=np.array([case['joint_q_rad'].get(n,0) for n in names]);data.qpos[qadr]=desired
        set_passive_linkage(model,data,contract);mujoco.mj_forward(model,data)
        contacts=[]
        for c in data.contact:
            a,b=[model.geom(int(g)).name for g in c.geom]
            if 'ground' in [a,b] or c.dist>=-.0002:continue
            contacts.append(dict(geom_a=a,geom_b=b,part_a=parts.get(a,a),part_b=parts.get(b,b),penetration_m=float(-c.dist),position_m=c.pos.tolist()))
        record=dict(name=case['name'],contact_count=int(data.ncon),self_contact_candidates=contacts,
            maximum_self_penetration_m=max([c['penetration_m'] for c in contacts],default=0.),
            collision_candidate_screen_pass=not contacts)
        reports.append(record);print('CONTACT',case['name'],'self candidates',len(contacts),'max',record['maximum_self_penetration_m'],flush=True)
    # Keep this test bounded: the first neutral stance alone is a useful
    # dynamics rejection. Unsafe initial contacts prevent a meaningful stance.
    dynamics=dict(status='NOT_RUN_INITIAL_SELF_CONTACT',completed=False,stance_pass=False)
    if reports[0]['collision_candidate_screen_pass']:
        case=cases[0];mujoco.mj_resetData(model,data);data.qpos[:3]=case['root_position_m'];data.qpos[3:7]=case['root_quaternion_wxyz'];desired=np.array([case['joint_q_rad'].get(n,0) for n in names]);data.qpos[qadr]=desired
        set_passive_linkage(model,data,contract)
        started=time.monotonic();peak=np.zeros(18);clipped=np.zeros(18,int);max_tilt=0.;min_height=np.inf;reason='FULL_DURATION'
        for k in range(int(np.ceil(1.0/model.opt.timestep))):
            mujoco.mj_forward(model,data)
            torque=80*(desired-data.qpos[qadr])-4*data.qvel[vadr]+data.qfrc_bias[vadr]
            clipped+=(abs(torque)>limits);torque=np.clip(torque,-limits,limits);peak=np.maximum(peak,abs(torque));data.ctrl[actuators]=torque
            mujoco.mj_step(model,data)
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all() or any(int(w.number) for w in data.warning):reason='NONFINITE_OR_SOLVER_WARNING';break
            rot=data.xmat[model.body('torso').id].reshape(3,3);tilt=float(np.arccos(np.clip(rot[2,2],-1,1)));max_tilt=max(max_tilt,tilt)
            height=float(data.subtree_com[model.body('torso').id,2]);min_height=min(min_height,height)
            if tilt>np.deg2rad(30) or height<.15:reason='FALL_REJECTION';break
            if time.monotonic()-started>45:reason='WALL_TIME_BOUND_REACHED';break
        warnings=[int(w.number) for w in data.warning];complete=bool(data.time>=.999 and reason=='FULL_DURATION')
        pad_q=[float(data.qpos[model.joint(p['joint']).qposadr[0]]) for p in contract['passive_contacts']]
        final_errors=(data.qpos[qadr]-desired).tolist()
        dynamics=dict(status=reason,completed=complete,simulated_seconds=float(data.time),wall_seconds=time.monotonic()-started,
            max_root_tilt_rad=max_tilt,minimum_robot_com_height_m=min_height,final_joint_error_rad=dict(zip(names,final_errors)),
            peak_torque_nm=dict(zip(names,peak.tolist())),clipped_step_counts=dict(zip(names,clipped.tolist())),
            final_pad_compression_m=pad_q,bottom_out_pad_count=sum(q>=.00149 for q in pad_q),solver_warnings=warnings,
            stance_pass=bool(complete and not any(warnings) and max_tilt<np.deg2rad(10) and max(abs(np.array(final_errors)))<.08))
        print('DYNAMICS',dynamics['status'],'seconds',dynamics['simulated_seconds'],'pass',dynamics['stance_pass'],flush=True)
    report=dict(schema='goose_mechanical_physics_rejection_v1',bare_mass_kg=float(model.body_mass.sum()),active_axes=18,passive_axes=contract['passive_axes'],
        nq=int(model.nq),nv=int(model.nv),collision_hulls=len(contract['collision_geometries']),static_cases=reports,free_root_stance=dynamics,
        contact_candidate_cases_passed=sum(r['collision_candidate_screen_pass'] for r in reports),static_case_count=len(reports),
        dynamic_walking_pass=False,turning_pass=False,manipulation_pass=False,training_release=False,hardware_freeze=False,
        stage_three_complete=False,stage_four_complete=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths+[Path(__file__)]},
        limitations=['Convex hull penetration candidates require native CAD confirmation;1mm CoACD concavity is not a certified clearance bound.',
            'Adjacent bodies retain default MuJoCo filtering; native ankle/head load-path checks remain separate.',
            'Coupler-to-jaw collision filtering represents the second mating pin, equivalent to adjacent-body filtering at the first pin; native linkage fit is checked separately.',
            'One-second free-root joint PD stance uses assumed80Nm/rad stiffness,4Nm-s/rad damping and typical TPU springs; this does not prove gait or controller feasibility.',
            'No body pose clamp or root force is used. Active commands clip to continuous design limits, not catalog stall values.',
            'No PPO run or policy success is inferred.'])
    (R/'evidence/mechanical_physics_rejection.json').write_text(json.dumps(report,indent=2)+'\n')
    print('WHOLE CANDIDATE screen',report['contact_candidate_cases_passed'],'/',len(reports),flush=True)
    return 0 if report['contact_candidate_cases_passed']==len(reports) and dynamics['stance_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
