#!/usr/bin/env python3
"""One analytically sized external AP pitch feedback reference, unchanged007 plant."""
import argparse
import json
from pathlib import Path
import shutil
import time
import traceback
import mujoco
import numpy as np
from bevy_microduck_tools.goose.artifacts import sha256
from bevy_microduck_tools.goose.closeout_native50 import make_source_runtime,cold_birth_contact_check

BASELINE_ID='goose_source007_ap_pitch_feedback_v1'
CONSTANT_SHA='46b81967bf255b21cd1c221ee06aec2e3264c364504f5b496b791f0a20a61917'
MODEL_SHA='9f4687b5245bfb1c3d1103d8065f8371d10e6b1e6d7a087722e13a5759e1220c'
CONTRACT_SHA='25133749c65bd693e4d2d34e8855134bce338ee78c0a016b734d7080784da9fc'


def size_feedback(runtime,reference):
    m=runtime.model;d=mujoco.MjData(m)
    d.qpos[:]=reference['static_qpos']
    mujoco.mj_kinematics(m,d);mujoco.mj_comPos(m,d)
    mass=float(m.body_mass.sum());com=(m.body_mass[:,None]*d.xipos).sum(axis=0)/mass
    # Free static root equilibrium with gravity and ground forces implies CoP
    # directly below CoM; the prior reference has <1e-6N/Nm residual.
    cop=np.array([com[0],com[1],0.]);tensor=np.zeros((3,3));rows=[]
    for body in range(1,m.nbody):
        rotation=d.ximat[body].reshape(3,3)
        world=rotation@np.diag(m.body_inertia[body])@rotation.T
        offset=d.xipos[body]-cop
        translated=world+m.body_mass[body]*((offset@offset)*np.eye(3)-np.outer(offset,offset))
        tensor+=translated
        rows.append({'body':m.body(body).name,'mass_kg':float(m.body_mass[body]),
                     'world_COM_m':d.xipos[body].tolist(),'world_full_inertia_at_COM_kg_m2':world.tolist()})
    h=float(com[2]-cop[2]);ieff=float(tensor[1,1]);wn=3.;zeta=1.2
    gravity=float(-m.opt.gravity[2]);K=mass*gravity*h+ieff*wn**2;D=2*zeta*ieff*wn
    axes={name:d.xaxis[m.joint(name).id].tolist() for name in ('right_ankle_pitch','left_ankle_pitch')}
    if not np.allclose(axes['right_ankle_pitch'],[0,-1,0],atol=1e-10) or not np.allclose(axes['left_ankle_pitch'],[0,1,0],atol=1e-10):
        raise ValueError('Actual source AP axes do not match the approved torque split')
    return {'baseline_id':BASELINE_ID,'mass_kg':mass,'static_COM_world_m':com.tolist(),
        'static_equilibrium_CoP_world_m':cop.tolist(),'h_m':h,'full_I_about_CoP_world_kg_m2':tensor.tolist(),
        'Ieff_y_kg_m2':ieff,'gravity_m_s2':gravity,'omega_n_rad_s':wn,'zeta':zeta,
        'K_Nm_rad':K,'D_Nm_s_rad':D,'formula':'K=m*g*h+Ieff*wn^2; D=2*zeta*Ieff*wn; Mcorr=-K*pitch-D*world_omega_y',
        'AP_actual_q0_axes_world':axes,'body_MCI_readback':rows,
        'torque_split':'delta_tau_right_AP=+Mcorr/2; delta_tau_left_AP=-Mcorr/2',
        'external_policy_input':True,'plant_or_action_semantics_changed':False}


def reference_action(qpos,qvel,constant,contract,parameters):
    matrix=np.empty(9);mujoco.mju_quat2Mat(matrix,qpos[3:7]);rotation=matrix.reshape(3,3)
    pitch=float(np.arctan2(-rotation[2,0],np.hypot(rotation[0,0],rotation[1,0])))
    omega=rotation@qvel[3:6]  # Free-joint angular qvel is body-local.
    moment=-parameters['K_Nm_rad']*pitch-parameters['D_Nm_s_rad']*float(omega[1])
    delta=np.zeros(18);delta[10]=moment/2;delta[16]=-moment/2
    gains=np.array([j['kp_nm_rad']*j['action_scale_rad'] for j in contract['joints']])
    requested=constant+delta/gains
    action=np.clip(requested,-1.,1.)
    return action,{'root_pitch_rad':pitch,'root_world_omega_rad_s':omega.tolist(),
        'requested_body_correction_Nm':moment,'requested_delta_motor_tau_Nm':delta.tolist(),
        'unclipped_action':requested.tolist(),'external_action_saturated':bool(np.any(action!=requested))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('model','contract','constant-reference','output'):parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    if 'goose_closeout.slice' not in Path('/proc/self/cgroup').read_text():raise RuntimeError('Resource guard required')
    if sha256(args.model)!=MODEL_SHA or sha256(args.contract)!=CONTRACT_SHA or sha256(args.constant_reference)!=CONSTANT_SHA:
        raise ValueError('Explicit007 plant/reference identity changed')
    args.output.mkdir(parents=True);shutil.copy2(__file__,args.output/'controller_source.py')
    shutil.copy2(args.constant_reference,args.output/'constant_reference.json')
    receipt={'baseline_id':BASELINE_ID,'model_sha256':MODEL_SHA,'contract_sha256':CONTRACT_SHA,
        'constant_reference_sha256':CONSTANT_SHA,'controller_source_sha256':sha256(Path(__file__)),
        'CPU_integrations':0,'GPU_integrations':0,'PPO_updates':0,'case_results':{},'failure':None,
        'old_zero_and_constant_drop_failures_preserved':True,'plant_or_action_semantics_changed':False,
        'training_ready':False,'qualification':'none'}
    rows=[];runtime=None
    try:
        runtime=make_source_runtime(args.model,args.contract);m,d=runtime.model,runtime.data
        reference=json.loads(args.constant_reference.read_text());constant=np.array(reference['constant_normalized_action'])
        parameters=size_feedback(runtime,reference)
        (args.output/'feedback_parameters.json').write_text(json.dumps(parameters,indent=2)+'\n')
        receipt['feedback_parameters_sha256']=sha256(args.output/'feedback_parameters.json')
        contact=json.loads(Path(runtime.contract['closeout_native50']['source_refs']['contact']['path']).read_text())
        print('EVENT FEEDBACK_PARAMETERS '+json.dumps({k:v for k,v in parameters.items() if k!='body_MCI_readback'}),flush=True)
        for case in ('standing','drop_50mm','reinitialize'):
            runtime.reset()
            if case=='drop_50mm':d.qpos[2]+=.05;mujoco.mj_forward(m,d)
            cold=cold_birth_contact_check(m,d,contact)
            rows.append({'case':case,'initial':True,'qpos':d.qpos.tolist(),'qvel':d.qvel.tolist(),'cold_birth_contacts':cold})
            if not cold['passed']:raise RuntimeError('Initial selfcontact rejected')
            case_failure=None
            for tick in range(100):
                action,control=reference_action(d.qpos,d.qvel,constant,runtime.contract,parameters)
                pre_q=d.qpos.copy();pre_v=d.qvel.copy();pre_x=d.xpos.copy();pre_r=d.xmat.copy();before=float(d.time)
                started=time.perf_counter()
                try:observation,info=runtime.step(action)
                finally:receipt['CPU_integrations']+=int(float(d.time)>before)
                contacts=[]
                for index in range(d.ncon):
                    hit=d.contact[index];wrench=np.zeros(6);mujoco.mj_contactForce(m,d,index,wrench)
                    a,b=int(hit.geom1),int(hit.geom2);ba,bb=int(m.geom_bodyid[a]),int(m.geom_bodyid[b])
                    contacts.append({'geoms':[m.geom(a).name,m.geom(b).name],'owners':[m.body(ba).name,m.body(bb).name],
                        'distance_m':float(hit.dist),'world_point_m':hit.pos.tolist(),'world_axes':hit.frame.reshape(3,3).tolist(),
                        'contact_frame_force_torque':wrench.tolist(),
                        'step_start_body_xpos':[pre_x[ba].tolist(),pre_x[bb].tolist()],
                        'step_start_body_xmat':[pre_r[ba].reshape(3,3).tolist(),pre_r[bb].reshape(3,3).tolist()]})
                collision=cold_birth_contact_check(m,d,contact)
                row={'case':case,'tick':tick+1,'time_s':float(d.time),'wall_s':time.perf_counter()-started,
                    'action':action.tolist(),'controller_state':control,'step_start_qpos':pre_q.tolist(),
                    'step_start_qvel':pre_v.tolist(),'qpos':d.qpos.tolist(),'qvel':d.qvel.tolist(),
                    'ctrl':d.ctrl.tolist(),'target':runtime.drive.target[0].tolist(),'actual_motor_force_Nm':d.actuator_force.tolist(),
                    'thermal':runtime.drive.thermal[0].tolist(),'force_lower_Nm':runtime.drive.force_lower[0].tolist(),
                    'force_upper_Nm':runtime.drive.force_upper[0].tolist(),'actual_cached_contacts':contacts,
                    'blocked_self_contacts':collision['blocked_self_contacts'],'info':info}
                rows.append(row)
                if abs(float(d.time)-before-.02)>1e-12 or observation.shape!=(65,) or not np.isfinite(observation).all():
                    raise RuntimeError('Actual20ms finite clock/observation failed')
                if info['failure'] or not collision['passed']:
                    case_failure='Posture or selfcontact failed; independent case terminated preserving actual state'
                    break
            receipt['case_results'][case]={'passed':case_failure is None and tick==99,'integrations':tick+1,
                'time_s':float(d.time),'last_info':info,'failure':case_failure}
            print('EVENT CPU_CASE '+json.dumps({'case':case,**receipt['case_results'][case]}),flush=True)
    except BaseException:
        receipt['failure']=traceback.format_exc()
        if runtime is not None:receipt['failed_state']={'qpos':runtime.data.qpos.tolist(),'qvel':runtime.data.qvel.tolist(),'time_s':float(runtime.data.time)}
    finally:
        receipt['all_three_cases_passed']=len(receipt['case_results'])==3 and all(x['passed'] for x in receipt['case_results'].values()) and receipt['failure'] is None
        receipt['status']='EXTERNAL_PITCH_REFERENCE_CPU300_PASS_ONLY' if receipt['all_three_cases_passed'] else 'EXTERNAL_PITCH_REFERENCE_FAILED_PRESERVED'
        (args.output/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');(args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('STATUS '+json.dumps(receipt),flush=True)
    if not receipt['all_three_cases_passed']:raise RuntimeError('One or more independent CPU cases failed; see preserved receipt')

if __name__=='__main__':main()
