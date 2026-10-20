"""Finite read-only mechanical attribution of actual002; never step or solve LP."""
from pathlib import Path
import argparse,gzip,hashlib,json,math
import numpy as np
import mujoco as mj
from scipy.spatial.transform import Rotation


def identity(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def bernstein(c,u):
    n=len(c)-1;return sum(math.comb(n,k)*u**k*(1-u)**(n-k)*c[k]for k in range(n+1))
def segment_qdd(meta,time):
    p=meta['trajectory_packet'];segs=p['segments'];s=next((x for x in segs if x['start_s']-1e-8<=time<=x['end_s']+1e-8),segs[-1]);T=s['end_s']-s['start_s'];u=np.clip((time-s['start_s'])/T,0,1);c=np.array(s['bernstein_q18']);return bernstein(20*np.diff(c,n=2,axis=0)/T**2,u)
def pose(m,q,v=None):
    d=mj.MjData(m);d.qpos[:]=q
    if v is not None:d.qvel[:]=v
    mj.mj_forward(m,d);return d


def main(run,out):
    assert not out.exists();out.mkdir(parents=True);s=run/'attempt_002';m=mj.MjModel.from_binary_path(str(s/'actual_scene.mjb'));mj.mj_step=lambda*a,**k:(_ for _ in()).throw(AssertionError('NO INTEGRATION'))
    names=[m.joint(int(m.actuator_trnid[i,0])).name for i in range(18)];qidx=np.array([int(m.jnt_qposadr[m.actuator_trnid[i,0]])for i in range(18)]);vidx=np.array([int(m.jnt_dofadr[m.actuator_trnid[i,0]])for i in range(18)]);times=[6.240,6.260,6.265,6.290,6.355,6.433,6.644];chosen=[];stats={}
    with gzip.open(s/'substeps.jsonl.gz','rt')as f:
        for line in f:
            r=json.loads(line);t=r['pre_time_s']
            if any(abs(t-x)<1e-7 for x in times):chosen.append(r)
            if t>=5.8 and t<=6.433+1e-8:
                motor=r['motor_profile_details'];request=np.array(motor.get('combined_requested_tau18_Nm',r['actual_torque18']));actual=np.array(r['actual_torque18'])
                for axis in ['left_ankle_roll','right_ankle_roll','left_hip_roll','right_knee_pitch']:
                    i=names.index(axis);x=stats.setdefault(axis,dict(maximum_abs_raw_request=0.,maximum_abs_actual=0.,first_clip=None))
                    if abs(request[i])>x['maximum_abs_raw_request']:x.update(maximum_abs_raw_request=float(abs(request[i])),raw_peak_time=t,raw_peak_signed=float(request[i]))
                    x['maximum_abs_actual']=max(x['maximum_abs_actual'],float(abs(actual[i])))
                    if abs(request[i]-actual[i])>1e-7 and x['first_clip']is None:x['first_clip']=t
    assert len(chosen)==7
    rows=[]
    for r in chosen:
        d=pose(m,r['pre_qpos'],r['pre_qvel']);g=pose(m,r['pre_qpos']);M=np.empty((m.nv,m.nv));mj.mj_fullM(m,d,M);acc=np.array(r['pre_qacc']);inertial=M@acc;meta=r['command_metadata'];soft=meta['soft_phase'];qd2=segment_qdd(meta,r['motion_elapsed_s']);axes={}
        for side in ['left','right']:
            joint=m.joint(side+'_ankle_roll').id;i=names.index(side+'_ankle_roll');dof=vidx[i];anchor=d.xanchor[joint];axis=d.xaxis[joint];normal=0.;pweighted=np.zeros(3);Fsum=np.zeros(3);torqueN=0.;torqueT=0.;couple=0.;points=[]
            for c in r['contacts']:
                fnames=[c['geom1'],c['geom2']]
                if side+'_actual_sole'not in fnames or not any(n in fnames for n in['ground','sole_ground_box']):continue
                sign=1 if c['geom2']==side+'_actual_sole'else-1;F=sign*np.array(c['force_on_geom2_world']);T=sign*np.array(c['world_torque_on_geom2_at_contact_Nm']);p=np.array(c['pos_world']);z=np.array([0,0,F[2]]);normal+=max(0,F[2]);pweighted+=max(0,F[2])*p;Fsum+=F;torqueN+=axis@np.cross(p-anchor,z);torqueT+=axis@np.cross(p-anchor,F-z);couple+=axis@T;points.append(dict(world_m=p.tolist(),force_world_N=F.tolist(),contact_material_velocity=c.get('stance_material_point_velocity_world')))
            cop=pweighted/normal if normal>0 else np.full(3,np.nan);taucontact=torqueN+torqueT+couple;actual=float(r['actual_torque18'][i]);friction_inferred=float(inertial[dof]+d.qfrc_bias[dof]-d.qfrc_passive[dof]-taucontact-m.actuator_gear[i,0]*actual)
            motor=r['motor_profile_details'];body=m.body(side+'_ankle_roll').id;Rfoot=d.geom_xmat[m.geom(side+'_actual_sole').id].reshape(3,3);tilt=np.degrees(np.arccos(np.clip(Rfoot[2]@np.array([0,0,1.]),-1,1)))
            planeNormal=Rfoot@np.array([0,0,1.]);axes[side]=dict(actual_q_rad=float(d.qpos[qidx[i]]),actual_qd_rad_s=float(d.qvel[dof]),actual_qdd_rad_s2=float(acc[dof]),target_slewed_q_rad=float(r['actual_slew_target18'][i]),target_qd_rad_s=float(motor['qd_ref18_rad_s'][i]),segment_exact_target_qdd_rad_s2=float(qd2[i]),planned_native_reference_qdd=float(meta['reference_qdd'][dof]),LP_task_goal_qdd=float(soft['task_acceleration_goal'][dof]),LP_predicted_qdd=float(soft['predicted_full_qacc'][dof]),actual_tau_Nm=actual,raw_requested_tau_Nm=float(motor['combined_requested_tau18_Nm'][i]),PD_tau_Nm=float(motor['PD18_Nm'][i]),held_FF_Nm=float(motor['tau_ff18_Nm'][i]),source_cap_Nm=float(soft['source_caps18'][i]),normal_N=normal,force_world_N=Fsum.tolist(),CoP_world_m=cop.tolist(),anchor_world_m=anchor.tolist(),axis_world=axis.tolist(),CoP_minus_anchor_m=(cop-anchor).tolist(),vertical_force_generalized_moment_Nm=float(torqueN),tangent_force_generalized_moment_Nm=float(torqueT),contact_couple_generalized_Nm=float(couple),all_ground_generalized_moment_Nm=float(taucontact),gravity_generalized_Nm=float(g.qfrc_bias[dof]),coriolis_generalized_Nm=float(d.qfrc_bias[dof]-g.qfrc_bias[dof]),mass_times_actual_qacc_Nm=float(inertial[dof]),source_passive_generalized_Nm=float(d.qfrc_passive[dof]),inferred_friction_or_unrecorded_eq_generalized_Nm=friction_inferred,source_frictionloss_bound_Nm=float(m.dof_frictionloss[dof]),foot_normal_world=planeNormal.tolist(),whole_sole_min_z_m=float(r['foot_geometry_min_z_m'][0 if side=='right'else 1]),actual_contact_points=points)
        actual_hips={}
        for side in ['right','left']:
            P=d.xanchor[m.joint(side+'_hip_pitch').id];Q=d.xanchor[m.joint(side+'_knee_pitch').id];A=d.xanchor[m.joint(side+'_ankle_pitch').id];v=A-P;deltaY=.04*(1 if side=='left'else-1);newv=v.copy();newv[1]+=deltaY;new_vertical=np.sqrt(max(0.,v[2]**2+v[1]**2-newv[1]**2));dz=float(new_vertical-abs(v[2]));newv[2]=-new_vertical
            rotvec=np.cross(v,newv);dot=float(np.clip(v@newv/(np.linalg.norm(v)*np.linalg.norm(newv)),-1,1));angle=float(np.arccos(dot));R=Rotation.from_rotvec(rotvec/(np.linalg.norm(rotvec)+1e-30)*angle).as_matrix();Pnew=P+[0,0,dz];Qnew=Pnew+R@(Q-P)
            actual_hips[side]=dict(hip_pitch_axis_world_m=P.tolist(),knee_axis_world_m=Q.tolist(),ankle_pitch_axis_world_m=A.tolist(),hip_to_ankle_vector_m=v.tolist(),hip_to_ankle_length_m=float(np.linalg.norm(v)),upper_link_m=float(np.linalg.norm(Q-P)),lower_link_m=float(np.linalg.norm(A-Q)),actual_knee_q_rad=float(d.qpos[m.joint(side+'_knee_pitch').qposadr[0]]),one_analytic_outward_ankle_shift_m=deltaY,constant_triangle_length_required_bodyZ_increase_m=dz,minimal_triangle_rotation_rad=angle,coarse_knee_anchor_after_constant_flex_lateral_rotation_m=Qnew.tolist(),not_an_IK_or_dynamics_certificate=True)
        row=dict(time_s=r['pre_time_s'],motion_elapsed_s=r['motion_elapsed_s'],phase=meta['phase'],active_swing=meta.get('active_swing'),planned_swing=meta.get('planned_swing'),FF_C2_entry_blend=meta['FF_C2_entry_blend'],unload_soft_weight=soft['left_normal_soft_weight'],unload_target_N=soft['left_normal_target_N'],LP_raw_predicted_left_normal_N=soft['left_normal_predicted_N'],LP_success=soft['success'],LP_held_command_age_s=float(r['motion_elapsed_s']-meta['trajectory_packet']['command_time_s']),actual_root_pose=r['root_pose'],actual_root_velocity6=r['root_velocity6'],reference_root_pose=meta['reference_qpos'][:7],reference_root_velocity6=meta['reference_qvel'][:6],COM_world=r['COM_world'],COM_reference=meta['COM_reference_world'],COM_velocity=r['COM_velocity_world_m_s'],mouth_wrench6=r['mouth_wrench6_world_on_robot_about_COM'],foot_normals_R_L=r['foot_normal_N'],foot_material_path_m=r['foot_material_slip_integral_m'],AR=axes,leg_geometry=actual_hips,qpos=r['pre_qpos'],qvel=r['pre_qvel'],qacc=r['pre_qacc'],contact_and_internal_closure_limitations=dict(max_penetration_m=r['max_penetration_m'],equalities=r['equalities']))
        rows.append(row);print('STATE',r['pre_time_s'],'N',r['foot_normal_N'],'LAR',[(k,round(axes['left'][k],6))for k in['actual_tau_Nm','vertical_force_generalized_moment_Nm','tangent_force_generalized_moment_Nm','mass_times_actual_qacc_Nm','inferred_friction_or_unrecorded_eq_generalized_Nm']],'weight',row['unload_soft_weight'],flush=True)
    terminal=json.loads((s/'true_terminal_poststate.json').read_text())
    result=dict(physics_steps=0,LP_calls=0,selected_actual_PRE_states=7,selected_true_terminal_POST=terminal['time_s'],source=identity(Path(__file__)),inputs=[identity(s/x)for x in ['actual_scene.mjb','substeps.jsonl.gz','commands50hz.json','manifest.json','actual_event_analysis.json','true_terminal_poststate.npz']],actuator_order=names,before_sticky_failure_raw_request_stats=stats,rows=rows,terminal_summary=dict(time_s=terminal['time_s'],qpos=terminal['qpos'],qvel=terminal['qvel']),scope='Actual-state moment decomposition only. No alternate rigid-contact acceleration, arbitrary mouth force, native repair, cap change, control change, rollout or pose family. Contact loads are from synchronized source trace, not scratch-solver contact forces.')
    (out/'readback.json').write_text(json.dumps(result,indent=2)+'\n');print('FINAL',identity(out/'readback.json'),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.run,a.output)
