"""Read-only old/new AR source and free/locked inertia comparison; zero steps."""
from pathlib import Path
import argparse,hashlib,json,math,xml.etree.ElementTree as ET
import numpy as np
import mujoco as mj


def identity(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def tensor(m,b):
    R=np.zeros(9);mj.mju_quat2Mat(R,m.body_iquat[b]);R=R.reshape(3,3);return R@np.diag(m.body_inertia[b])@R.T
def query(m,q,kp,kd):
    d=mj.MjData(m);d.qpos[:]=q;mj.mj_forward(m,d);M=np.empty((m.nv,m.nv));mj.mj_fullM(m,d,M);inverse=np.linalg.inv(M);rows={}
    for side in ['right','left']:
        name=side+'_ankle_roll';j=m.joint(name).id;i=int(m.jnt_dofadr[j]);b=int(m.jnt_bodyid[j]);locked=float(M[i,i]);free=float(1/inverse[i,i]);D=kd+float(m.dof_damping[i]);rows[side]=dict(foot_body=m.body(b).name,distal_foot_mass_kg=float(m.body_mass[b]),foot_body_COM_local_m=m.body_ipos[b].tolist(),foot_body_fullI_atCOM_kg_m2=tensor(m,b).tolist(),principal_I_kg_m2=m.body_inertia[b].tolist(),reflected_armature_kg_m2=float(m.dof_armature[i]),passive_damping=float(m.dof_damping[i]),frictionloss=float(m.dof_frictionloss[i]),I_all_other_accelerations_ideal_locked_kg_m2=locked,I_all_other_forces_zero_instantaneously_free_kg_m2=free,kp=kp,kd=kd,isolated_damping_ratio_heuristic_with_passive=dict(locked=D/(2*math.sqrt(kp*locked)),free=D/(2*math.sqrt(kp*free))),not_contact_mode_or_closed_loop_effective_inertia=True)
    return rows


def main(oldxml,newmjb,actual,out):
    assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);mj.mj_step=lambda*a,**k:(_ for _ in()).throw(AssertionError('NO INTEGRATION'))
    # The historic patched engine's 'discrete' keyword is not supported here.
    # In-memory integrator selection changes no rigid-body mass matrix. This
    # model is never stepped or used to inherit policy/physical qualification.
    xml=ET.fromstring(oldxml.read_text());original_integrator=xml.find('option').get('integrator');xml.find('option').set('integrator','implicitfast');xml.find('compiler').set('meshdir',str(oldxml.parent))
    old=mj.MjModel.from_xml_string(ET.tostring(xml,encoding='unicode'));new=mj.MjModel.from_binary_path(str(newmjb));a=json.loads(actual.read_text());rows=[]
    for r in a['rows']:
        if not any(abs(r['time_s']-t)<1e-7 for t in [6.265,6.433]):continue
        q=np.array(r['qpos']);qo=old.qpos0.copy();qo[:7]=q[:7];copied=[]
        for j in range(old.njnt):
            name=old.joint(j).name
            if old.jnt_type[j]!=int(mj.mjtJoint.mjJNT_HINGE):continue
            jn=new.joint(name).id;qo[int(old.jnt_qposadr[j])]=q[int(new.jnt_qposadr[jn])];copied.append(name)
        rows.append(dict(actual12_time_s=r['time_s'],old_pose_scope='Same shared logical/native hinge angles and root pose mapped into old source geometry; not old policy actual or an asserted ground-contact state.',mapped_hinges=copied,old_source_Kp20=query(old,qo,20.,.175),old_named_calibration_Kp10_heuristic_only=query(old,qo,10.,.175),current08=query(new,q,20.,.175)))
    out.write_text(json.dumps(dict(source=identity(Path(__file__)),inputs=[identity(oldxml),identity(newmjb),identity(actual)],physics_steps=0,LP_calls=0,in_memory_algebra_compiler_only_changes=dict(integrator_before=original_integrator,integrator_after='implicitfast',meshdir_absolute=str(oldxml.parent),no_input_file_written=True),queries=rows,limitations=['M algebra only, no contacts/equalities/actuator clipping/digital delay in the inertia bounds or isolated damping ratio.','Old source XML compiled only for algebra using current MuJoCo; old accepted binary is version-incompatible and was not successfully loaded.','Kp10 is a separately named calibration-development source, not established as the accepted444 actuator gain.','No proposed replacement gains or source mutation.']),indent=2)+'\n');print(identity(out));print(rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--oldxml',type=Path,required=True);p.add_argument('--newmjb',type=Path,required=True);p.add_argument('--actual',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.oldxml,a.newmjb,a.actual,a.output)
