"""Same seven saved actual states: coordinate readback and wrench sensitivities.

No new kinematic pose is solved. Constant-link-length widening is analytic;
lowering an axis is only a frozen measured-wrench derivative, not a new model.
"""
from pathlib import Path
import argparse,gzip,hashlib,json
import numpy as np
import mujoco as mj
from scipy.spatial.transform import Rotation


def identity(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def data(m,q,v=None):
    d=mj.MjData(m);d.qpos[:]=q
    if v is not None:d.qvel[:]=v
    mj.mj_forward(m,d);return d


def main(run,readback,out):
    assert not out.exists();s=run/'attempt_002';m=mj.MjModel.from_binary_path(str(s/'actual_scene.mjb'));a=json.loads(readback.read_text());times=[r['time_s']for r in a['rows']];records=[]
    with gzip.open(s/'substeps.jsonl.gz','rt')as f:
        for line in f:
            r=json.loads(line)
            if any(abs(r['pre_time_s']-t)<1e-8 for t in times):records.append(r)
    cold=np.load(s/'cold_state.npz');d0=data(m,cold['qpos']);start=np.load(s/'actual_motion_start_state.npz');ds=data(m,start['qpos']);normals={side:d0.geom_xmat[m.geom(side+'_actual_sole').id].reshape(3,3).T@np.array([0.,0.,1.])for side in ['right','left']};rows=[]
    for source,r in zip(a['rows'],records):
        d=data(m,r['pre_qpos'],r['pre_qvel']);ref=data(m,r['command_metadata']['reference_qpos']);grav=data(m,r['pre_qpos']);M=np.empty((m.nv,m.nv));mj.mj_fullM(m,d,M);inertial=M@np.array(r['pre_qacc']);foot={};joints={};hypo={}
        ids=np.where(d.efc_type[:d.nefc]==int(mj.mjtConstraint.mjCNSTR_EQUALITY))[0];Je=d.efc_J.reshape(d.nefc,m.nv)[ids]
        for side in ['right','left']:
            g=m.geom(side+'_actual_sole').id;R=d.geom_xmat[g].reshape(3,3);RR=ref.geom_xmat[g].reshape(3,3);n=R@normals[side];nref=RR@normals[side];mesh=m.geom_dataid[g];v=m.mesh_vert[m.mesh_vertadr[mesh]:m.mesh_vertadr[mesh]+m.mesh_vertnum[mesh]]
            world=v@R.T+d.geom_xpos[g];refworld=v@RR.T+ref.geom_xpos[g]
            foot[side]=dict(actual_center_world_m=d.geom_xpos[g].tolist(),reference_center_world_m=ref.geom_xpos[g].tolist(),actual_minus_reference_m=(d.geom_xpos[g]-ref.geom_xpos[g]).tolist(),actual_center_motion_from_real_motionstart_m=(d.geom_xpos[g]-ds.geom_xpos[g]).tolist(),actual_normal_world=n.tolist(),reference_normal_world=nref.tolist(),actual_tilt_deg=float(np.degrees(np.arccos(np.clip(n[2],-1,1)))),reference_tilt_deg=float(np.degrees(np.arccos(np.clip(nref[2],-1,1)))),actual_whole_minZ_m=float(world[:,2].min()),reference_whole_minZ_m=float(refworld[:,2].min()),normal_basis='cold native floor normal transformed through actual/reference geom rotation; mesh principal local Z is not the sole normal')
            z=source['AR'][side];axis=np.array(z['axis_world']);F=np.array(z['force_world_N']);delta=float(.010*(-axis[0]*F[1]+axis[1]*F[0]));hypo[side]=dict(axis_height_current_m=z['anchor_world_m'][2],axis_height_if_lower10mm_m=z['anchor_world_m'][2]-.010,frozen_wrench_delta_contact_generalized_Nm=delta,frozen_wrench_delta_motor_demand_Nm=-delta,actual_motor_tau_Nm=z['actual_tau_Nm'],frozen_wrench_equivalent_motor_tau_Nm=z['actual_tau_Nm']-delta,geometry_mass_or_controller_changed=False,validity='Only a projection derivative at actual measured q/contact loads. Lowered native geometry, gravity/inertia, fitted source axes and real closed-loop response are not evaluated.')
            for suffix in ['hip_roll','knee_pitch','ankle_roll']:
                name=side+'_'+suffix;j=m.joint(name).id;di=int(m.jnt_dofadr[j]);i=a['actuator_order'].index(name);anchor=d.xanchor[j];axis=d.xaxis[j];tn=0.;tt=0.;tc=0.
                for c in z['actual_contact_points']:
                    p=np.array(c['world_m']);force=np.array(c['force_world_N']);vertical=np.array([0.,0.,force[2]]);tn+=axis@np.cross(p-anchor,vertical);tt+=axis@np.cross(p-anchor,force-vertical)
                tau=float(r['actual_torque18'][i]);fr=float(inertial[di]+d.qfrc_bias[di]-d.qfrc_passive[di]-tn-tt-tau)
                joints[name]=dict(axis_world=axis.tolist(),anchor_world_m=anchor.tolist(),actual_tau_Nm=tau,actual_q_rad=float(d.qpos[m.jnt_qposadr[j]]),actual_qd_rad_s=float(d.qvel[di]),actual_qdd_rad_s2=float(r['pre_qacc'][di]),target_q_rad=float(r['actual_slew_target18'][i]),target_qd_rad_s=float(r['motor_profile_details']['qd_ref18_rad_s'][i]),PD_Nm=float(r['motor_profile_details']['PD18_Nm'][i]),held_FF_Nm=float(r['motor_profile_details']['tau_ff18_Nm'][i]),target_native_reference_qdd=float(r['command_metadata']['reference_qdd'][di]),LP_goal_qdd=float(r['command_metadata']['soft_phase']['task_acceleration_goal'][di]),LP_predicted_qdd=float(r['command_metadata']['soft_phase']['predicted_full_qacc'][di]),ground_vertical_moment_Nm=float(tn),ground_tangent_moment_Nm=float(tt),gravity_Nm=float(grav.qfrc_bias[di]),Coriolis_Nm=float(d.qfrc_bias[di]-grav.qfrc_bias[di]),mass_actual_acceleration_Nm=float(inertial[di]),passive_Nm=float(d.qfrc_passive[di]),inferred_friction_Nm=fr,source_frictionloss_Nm=float(m.dof_frictionloss[di]),maximum_equality_J_coefficient=float(max(abs(Je[:,di]),default=0.)))
        row=dict(time_s=r['pre_time_s'],feet=foot,joints=joints,lower_AR_axis10mm=hypo)
        if abs(r['pre_time_s']-6.265)<1e-7:
            analytic={}
            for side in ['left','right']:
                x=source['leg_geometry'][side];P=np.array(x['hip_pitch_axis_world_m']);Q=np.array(x['knee_axis_world_m']);A=np.array(x['ankle_pitch_axis_world_m']);v=A-P;deltaY=x['one_analytic_outward_ankle_shift_m'];vnew=v.copy();vnew[1]+=deltaY;vnew[2]=-np.sqrt(v[2]**2+v[1]**2-vnew[1]**2);cross=np.cross(v,vnew);angle=np.arccos(np.clip(v@vnew/(np.linalg.norm(v)*np.linalg.norm(vnew)),-1,1));Rtri=Rotation.from_rotvec(cross/(np.linalg.norm(cross)+1e-30)*angle).as_matrix();Qnew=np.array(x['coarse_knee_anchor_after_constant_flex_lateral_rotation_m']);k=m.joint(side+'_knee_pitch').id;ax=d.xaxis[k];axnew=Rtri@ax;oldmoment=0.;newmoment=0.
                for c in source['AR'][side]['actual_contact_points']:
                    p=np.array(c['world_m']);force=np.array(c['force_world_N']);oldmoment+=ax@np.cross(p-Q,force);newmoment+=axnew@np.cross(p+[0,deltaY,0]-Qnew,force)
                analytic[side]=dict(actual_hip_to_ankle_lateral_m=float(v[1]),after_outward40mm_lateral_m=float(vnew[1]),actual_vertical_separation_m=float(abs(v[2])),constant_link_triangle_bodyZ_increase_m=x['constant_triangle_length_required_bodyZ_increase_m'],actual_knee_ground_moment_Nm=float(oldmoment),hypothetical_constant_flex_knee_ground_moment_Nm=float(newmoment),change_frozen_ground_knee_moment_Nm=float(newmoment-oldmoment),AR_ground_moment_change_if_foot_axis_and_contacts_translate_together_Nm=0.,assumptions='Rigid link triangle minimally rotated to the new equal-length chord; foot/cop translated outward40mm, world wrench frozen. Not six-axis IK, full ID, contact equilibrium or task validation.')
            row['one_analytic_constant_flex_widening']=analytic
        rows.append(row)
    result=dict(source=identity(Path(__file__)),inputs=[identity(readback),identity(s/'actual_scene.mjb'),identity(s/'substeps.jsonl.gz'),identity(s/'cold_state.npz'),identity(s/'actual_motion_start_state.npz')],physics_steps=0,LP_calls=0,unique_actual_states=7,foot_normal_correction='Initial raw readback AR.foot_normal_world used mesh principal local Z and is not a sole normal; superseded exclusively by this cold-native-plane-normal readback. Force/moment/axis/geometry calculations did not use the erroneous normal field.',rows=rows)
    out.write_text(json.dumps(result,indent=2)+'\n');print(identity(out))
    for r in rows:print('SENSITIVITY',r['time_s'],r['lower_AR_axis10mm'],'normal',[(s,x['actual_tilt_deg'])for s,x in r['feet'].items()],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--readback',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.run,a.readback,a.output)
