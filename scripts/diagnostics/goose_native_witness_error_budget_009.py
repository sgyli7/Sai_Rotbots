"""Frozen candidate native-forward numerical audit. No step, LP, or mutations."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import mujoco as mj

def ident(p):
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def main(root,out):
    assert not out.exists()
    out.mkdir(parents=True)
    mj.mj_step=lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO STEP'))
    statepath=root/'attempt_001/true_terminal_poststate.json'
    modelpath=root/'attempt_001/actual_scene.mjb'
    j=json.loads(statepath.read_text()); rec=j['metadata']['drive_FF_refresh']; original=rec['actual_blended_native_witness']
    m=mj.MjModel.from_binary_path(str(modelpath)); d=mj.MjData(m)
    d.qpos[:]=j['qpos'];d.qvel[:]=j['qvel'];d.ctrl[:]=original['total_tau18']
    mj.mj_forward(m,d)
    M=np.zeros((m.nv,m.nv));mj.mj_fullM(m,d,M)
    J=d.efc_J.reshape(d.nefc,m.nv).copy(); lam=d.efc_force[:d.nefc].copy()
    B=np.zeros((m.nv,m.nu))
    for a in range(m.nu): B[m.jnt_dofadr[m.actuator_trnid[a,0]],a]=m.actuator_gear[a,0]
    r=M@d.qacc+d.qfrc_bias-d.qfrc_passive-B@d.actuator_force-J.T@lam
    native_r=M@d.qacc-d.qfrc_smooth-d.qfrc_constraint
    delta=np.linalg.solve(M,r); inverse=np.linalg.inv(M)
    energy_dual_norm=float(np.sqrt(max(0.,r@delta)))
    dofs=[]
    for k in range(m.nv):
        jid=int(m.dof_jntid[k]); typ=int(m.jnt_type[jid]); off=k-int(m.jnt_dofadr[jid])
        suffix=('/'+['tx','ty','tz','rx','ry','rz'][off]) if typ==int(mj.mjtJoint.mjJNT_FREE) else ''
        dofs.append(m.joint(jid).name+suffix)
    rows=[]
    for k in np.argsort(abs(r))[::-1]:
        rows.append(dict(dof=int(k),name=dofs[k],residual=float(r[k]),unit='N' if int(m.jnt_type[m.dof_jntid[k]])==0 and k-int(m.jnt_dofadr[m.dof_jntid[k]])<3 else 'Nm',M_inv_r_acceleration=float(delta[k]),M_qacc=float((M@d.qacc)[k]),qfrc_smooth=float(d.qfrc_smooth[k]),qfrc_constraint=float(d.qfrc_constraint[k])))
    pointsets=[]
    def project(label,body,points):
        entries=[]
        for p in points:
            jp=np.zeros((3,m.nv));jr=np.zeros_like(jp);mj.mj_jac(m,d,jp,jr,np.array(p),body)
            a=jp@delta;ang=jr@delta
            # Independent of force-frozen direction: if the native fixed-q/v
            # convex acceleration objective is M-strongly convex, ||e||_M is
            # bounded by ||gradient||_(M^-1). This is an explicit conditional
            # local solver-error bound, never a trajectory/contact certificate.
            strong_bound=energy_dual_norm*np.sqrt(max(0.,float(np.linalg.eigvalsh(jp@inverse@jp.T)[-1])))
            entries.append(dict(point_world_m=np.asarray(p).tolist(),acceleration_error_world_m_s2=a.tolist(),acceleration_error_norm_m_s2=float(np.linalg.norm(a)),absolute_component_sum_bound_m_s2=float(np.linalg.norm(np.abs(jp)@np.abs(delta))),angular_acceleration_error_rad_s2=ang.tolist(),conditional_convex_solver_acceleration_bound_m_s2=float(strong_bound)))
        exact=max(e['acceleration_error_norm_m_s2'] for e in entries)
        conservative=max(e['absolute_component_sum_bound_m_s2'] for e in entries)
        strong=max(e['conditional_convex_solver_acceleration_bound_m_s2'] for e in entries)
        pointsets.append(dict(label=label,body=m.body(body).name,point_count=len(points),max_linear_acceleration_error_m_s2=exact,componentwise_triangle_bound_m_s2=conservative,displacement_bound_1ms_m=.5*1e-6*conservative,displacement_bound_5ms_m=.5*25e-6*conservative,conditional_convex_solver_acceleration_bound_m_s2=strong,conditional_convex_solver_displacement_1ms_m=.5e-6*strong,conditional_convex_solver_displacement_5ms_m=.5*25e-6*strong,representative_max_exact=max(entries,key=lambda e:e['acceleration_error_norm_m_s2'])))
    for side in ['left','right']:
        g=m.geom(side+'_actual_sole').id;mid=int(m.geom_dataid[g]);adr=int(m.mesh_vertadr[mid]);n=int(m.mesh_vertnum[mid]);verts=m.mesh_vert[adr:adr+n].astype(float)
        pts=verts@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]
        project(side+'_all_sole_vertices',int(m.geom_bodyid[g]),pts)
    b=m.body('head_roll').id
    tcp=d.xpos[b]+d.xmat[b].reshape(3,3)@np.array([.13750001972253326,0,-.03849996489687674])
    project('true_mouth_TCP',b,[tcp])
    stats={}
    for name in ['gradient','improvement','lineslope','nactive','nchange','neval','nupdate']:
        try:
            val=np.asarray(getattr(d.solver,name)); n=int(max(d.solver_niter)); stats[name]=dict(flat_array_shape=list(val.shape),first_active_island=val.reshape(-1)[:max(n,1)].tolist())
        except Exception as exc:stats[name]=str(exc)
    capfields={k:getattr(m.opt,k) for k in ['solver','integrator','tolerance','iterations','ls_tolerance','ls_iterations','noslip_iterations','noslip_tolerance','disableflags','enableflags','cone','timestep']}
    capfields={k:float(v) if isinstance(v,(float,np.floating)) else int(v) for k,v in capfields.items()}
    normM=float(np.linalg.norm(M,ord=np.inf)); normq=float(np.linalg.norm(d.qacc,ord=np.inf)); normJ=float(np.linalg.norm(J.T,ord=np.inf)); normlam=float(np.linalg.norm(lam,ord=np.inf))
    report=dict(inputs=[ident(statepath),ident(modelpath),ident(root/'native_dispatch_witness.py'),ident(root/'drive_ff200.py')],source=ident(Path(__file__)),physics_steps=0,LP_calls=0,pure_forward_calls=1,state_time_s=j['time_s'],witness_scope='UNdispatched candidate total_tau18 at exact failingPRE q/v, new MjData zero warmstart; not held-ctrl actual POST accelerations',nv=m.nv,nq=m.nq,nefc=d.nefc,ncon=d.ncon,original_witness=original,reconstruction=dict(qacc_max_difference=float(max(abs(d.qacc-np.array(original['qacc'])))),native_lambda_max_difference=float(max(abs(lam-np.array(original['native_force'])))),force_balance_max=float(max(abs(r))),force_balance_rows=rows,native_Mqacc_minus_smooth_minus_constraint_max=float(max(abs(native_r))),formula_vs_native_residual_difference_max=float(max(abs(r-native_r))),B_tau_vs_qfrc_actuator_max=float(max(abs(B@d.actuator_force-d.qfrc_actuator))),JT_lambda_vs_qfrc_constraint_max=float(max(abs(J.T@lam-d.qfrc_constraint))),qfrc_applied_max=float(max(abs(d.qfrc_applied))),xfrc_applied_max=float(np.max(abs(d.xfrc_applied)))),solver=dict(options=capfields,solver_niter=d.solver_niter.tolist(),solver_nnz=d.solver_nnz.tolist(),statistics=stats,model_meaninertia=float(m.stat.meaninertia),residual_mass_dual_norm=energy_dual_norm),projection=dict(M_inv_r=delta.tolist(),generalized_acceleration_inf=float(max(abs(delta))),M_condition_number=float(np.linalg.cond(M)),pointsets=pointsets,joint_angle_bound_1ms_rad=float(.5e-6*max(abs(delta[6:28]))),joint_angle_bound_5ms_rad=float(.5*25e-6*max(abs(delta[6:28]))),conditional_convex_joint_angle_bound_5ms_rad=float(.5*25e-6*energy_dual_norm*max(np.sqrt(np.diag(inverse))[6:28])),limits='Instantaneous frozen-M/J residual-only acceleration discrepancy; local zero-initial-error Taylor bound over stated horizon. Conditional convex bounds additionally require the fixed-q/v native acceleration objective to have Hessian >= M. None is an accumulated closed-loop trajectory/contact guarantee or evidence of physical slip.'),floating_point=dict(dtype=str(M.dtype),epsilon=float(np.finfo(float).eps),norm_M_inf=normM,norm_qacc_inf=normq,norm_Jtranspose_inf=normJ,norm_lambda_inf=normlam,conservative_plain_dot_roundoff_order=float(np.finfo(float).eps*(m.nv*normM*normq+d.nefc*normJ*normlam))),units='Root/free translations N, root/free rotations and hinges Nm. These mixed-unit residuals must not be interpreted as one physical force without row identity.')
    (out/'readback.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez(out/'native_candidate_arrays.npz',qpos=d.qpos,qvel=d.qvel,qacc=d.qacc,ctrl=d.ctrl,M=M,J=J,lambda_native=lam,residual=r,native_residual=native_r,delta_qacc=delta,qfrc_smooth=d.qfrc_smooth,qfrc_constraint=d.qfrc_constraint,qfrc_bias=d.qfrc_bias,qfrc_passive=d.qfrc_passive,qfrc_actuator=d.qfrc_actuator,efc_R=d.efc_R[:d.nefc],efc_aref=d.efc_aref[:d.nefc])
    print(json.dumps(dict(readback=ident(out/'readback.json'),rows=rows[:3],solver=report['solver'],projection=report['projection'],floating_point=report['floating_point']),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.root,a.output)
