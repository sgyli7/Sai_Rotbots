"""Read derived actual C/O reactions. Never integrate or modify state/physics.
Caller must already run mj_forward after each actual step; RNE only populates
post-constraint derived spatial forces. cfrc_int torque/force axes are world.
"""
import numpy as np
import mujoco as mj

def screen_actual_axial_reactions(model, data, config):
    if mj.__version__ != config['mujoco_version']:
        raise ValueError('Axial reaction screen MuJoCo version mismatch')
    mj.mj_rnePostConstraint(model, data)
    eid=model.equality('beak_distal_pin').id
    rows=np.flatnonzero((data.efc_type==mj.mjtConstraint.mjCNSTR_EQUALITY)&(data.efc_id==eid))
    if len(rows)!=3: raise ValueError('Expected three actual world Cartesian connect reaction rows')
    jid=model.joint('beak_hinge').id
    axis=np.asarray(data.xaxis[jid],float).copy()
    if abs(np.linalg.norm(axis)-1)>1e-8: raise ValueError('Nonunit actual O/C axis')
    Cforce=np.asarray(data.efc_force[rows],float).copy()
    # The C force sign depends on connect ordering; symmetric engineering bound.
    Oforce=np.asarray(data.cfrc_int[model.body('beak_hinge').id,3:],float).copy()
    Cax=float(Cforce@axis);Oax=float(Oforce@axis)
    values=np.r_[Cforce,Oforce,axis,Cax,Oax]
    reasons=[]
    if not np.isfinite(values).all(): reasons.append('nonfinite_actual_axial_reaction')
    if abs(Cax)>config['C_pin_axial_limit_N']:reasons.append('actual_C_pin_axial_engineering_domain_exited')
    if abs(Oax)>config['O_thrust_symmetric_limit_N']:reasons.append('actual_O_thrust_conditional_strength_domain_exited')
    return dict(status='actual_derived_reaction_no_integration',time_s=float(data.time),axis_world=axis.tolist(),C_connect_force_world_N=Cforce.tolist(),O_parent_reaction_world_N=Oforce.tolist(),C_axial_N=Cax,O_axial_N=Oax,C_limit_N=config['C_pin_axial_limit_N'],O_limit_N=config['O_thrust_symmetric_limit_N'],reasons=reasons,legacy_per_mouth_Fy_2N_is_not_failure=True,material_procurement_condition=config['material_procurement_condition'])
