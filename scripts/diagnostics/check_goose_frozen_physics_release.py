"""Independent-path package checks and bounded physical stepping, no training."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,time,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import mujoco


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mat(q):
 a=np.empty(9);mujoco.mju_quat2Mat(a,q);return a.reshape(3,3)
def check(package):
 package=Path(package).resolve();contract=json.loads((package/'physical_contract.json').read_text());drive=json.loads((package/'actuator_contract.json').read_text());m=mujoco.MjModel.from_xml_path(str(package/'robot.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d);fail=[];rows=[]
 for b in contract['bodies']:
  live=m.body(b['name']);R=mat(live.iquat);I=R@np.diag(live.inertia)@R.T;row=dict(body=b['name'],mass_error_kg=abs(float(live.mass[0])-b['mass_kg']),COM_max_error_m=float(abs(live.ipos-b['com_local_m']).max()),fullI_max_error_kg_m2=float(abs(I-b['inertia_at_com_body_kg_m2']).max()));rows.append(row)
  if row['mass_error_kg']>1e-10 or row['COM_max_error_m']>1e-10 or row['fullI_max_error_kg_m2']>1e-10:fail.append('MCI:'+b['name'])
 if abs(sum(m.body_mass)-contract['nominal_robot_mass_kg'])>1e-10:fail.append('totalmass')
 if (m.nbody-1,m.nu,m.njnt-1)!=(23,18,22):fail.append('topology')
 logical={j['name']:j for j in contract['joints']};spec={j['name']:j for j in contract['joints']+contract['passive_linkage_joints']};props={b['name']:b for b in contract['bodies']};axisrows=[]
 for nm,j in spec.items():
  q=m.joint(nm);body=m.body(nm);parent=props[j['parent']];p=np.array(props[nm]['origin_world_zero_m'])-parent['origin_world_zero_m'];bad=not(np.allclose(q.axis,j['axis_parent'],atol=1e-12,rtol=0)and np.allclose(body.pos,p,atol=1e-12,rtol=0));axisrows.append(dict(name=nm,axis_error=float(abs(q.axis-j['axis_parent']).max()),body_origin_error_m=float(abs(body.pos-p).max()),range_rad=q.range.tolist(),limited=bool(q.limited[0])))
  if bad:fail.append('axis:'+nm)
  if bool(q.limited[0]) and not np.allclose(q.range,j['range_rad'],atol=1e-12,rtol=0):fail.append('limit:'+nm)
  for field,key in [('armature','armature_kg_m2'),('frictionloss','frictionloss_nm'),('damping','damping_nm_s_rad')]:
   actual=getattr(m,'dof_'+field)[int(q.dofadr[0])];expected=j.get(key,0 if field!='damping'else .01)
   if abs(actual-expected)>1e-12:fail.append(field+':'+nm)
 for i,j in enumerate(contract['joints']):
  target=m.joint(j.get('actuation_joint',j['name']));cap=j['continuous_design_limit_nm']
  if m.actuator_trnid[i,0]!=target.id or not np.allclose(m.actuator_ctrlrange[i],[-cap,cap],rtol=0,atol=1e-12)or not np.allclose(m.actuator_forcerange[i],[-cap,cap],rtol=0,atol=1e-12):fail.append('drive:'+j['name'])
  if not(m.actuator_ctrllimited[i]and m.actuator_forcelimited[i]):fail.append('unbounded drive:'+j['name'])
 if abs(m.opt.timestep-contract['physics_dt_s'])>1e-12:fail.append('dt')
 tree=ET.parse(package/'robot.xml');uris=[]
 for e in tree.iter():
  for key in['file']:
   if key not in e.attrib:continue
   rel=Path(e.attrib[key]);path=(package/rel).resolve();uris.append(str(rel))
   if rel.is_absolute()or not path.is_relative_to(package)or not path.exists():fail.append('nonportableasset:'+str(rel))
 modulepath=package/'runtime_adapter.py';specmod=importlib.util.spec_from_file_location('packaged_goose_physics',modulepath);mod=importlib.util.module_from_spec(specmod);specmod.loader.exec_module(mod);env=mod.FrozenPhysics(package)
 # Same input at three battery voltages proves actual limit andslew code. No
 # state projection or mass randomization is used to make the check pass.
 voltage=[]
 for v in[20.,22.2,24.,25.2]:
  en=mod.FrozenPhysics(package,bus_voltage_v=v);vel=np.array([r['selected_speed_limit_rad_s']for r in drive['axes']])*1.15;request=np.full(18,1000.);tau=en.limit_torque(request,vel);voltage.append(dict(bus_voltage_v=v,velocity_rad_s=vel.tolist(),request_nm=request.tolist(),limited_torque_nm=tau.tolist(),target_slew_rad_per_drive_tick=(en.slew_speed*en.drive_dt).tolist(),power_w=float(np.maximum(tau*vel,0).sum())))
  if np.any(abs(tau)>en.cont+1e-12)or voltage[-1]['power_w']>drive['positive_mechanical_power_limit_w']+1e-10:fail.append('power/cont:'+str(v))
 before=float(env.data.time);start=time.perf_counter();warnings_before=[w.number for w in env.data.warning]
 for _ in range(5):env.step(np.zeros(18))
 elapsed=time.perf_counter()-start
 if abs(env.data.time-before-.1)>1e-10 or env.controller_updates!=20 or env.policy_updates!=5:fail.append('200Hz50Hztiming')
 if np.any(env.data.xfrc_applied)or np.any(env.data.qfrc_applied):fail.append('externalrootforce')
 obs=env.observations()
 if obs.shape!=(65,)or not np.isfinite(obs).all():fail.append('observation')
 report=dict(schema='goose_frozen_physical_package_readback_v1',package=str(package),mujoco_version=mujoco.__version__,model_sha256=sha(package/'robot.xml'),physical_contract_sha256=sha(package/'physical_contract.json'),body_readback=rows,axis_readback=axisrows,total_mass_kg=float(sum(m.body_mass)),robot_bodies=m.nbody-1,active_actuators=m.nu,hinge_coordinates=m.njnt-1,equality_objects=m.neq,loaded_contact_leaves=m.ngeom-1,loaded_mesh_support_vertices=int(m.mesh_vertnum.sum()),all_asset_URIs=uris,independent_runtime_copy_sha256=sha(modulepath),clock_check=dict(physics_dt_s=m.opt.timestep,elapsed_simulated_s=float(env.data.time-before),controller_updates=env.controller_updates,policy_calls=env.policy_updates,integrations=env.controller_updates*env.substeps),voltage_same_input_readback=voltage,bounded5policy_step_wall_s=elapsed,approx_mean_physics_step_ms=1000*elapsed/(env.controller_updates*env.substeps),warnings=[w.number for w in env.data.warning],finite_state=all(np.isfinite(getattr(env.data,k)).all()for k in['qpos','qvel','qacc']),observations_size=len(obs),no_task_reward_policy_or_training=True,no_external_forces_or_state_projection=True,failures=fail,passed=not fail)
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=check(a.package);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(report=str(a.output),passed=r['passed'],failures=r['failures'],mass=r['total_mass_kg'],leaves=r['loaded_contact_leaves'],step_ms=r['approx_mean_physics_step_ms'])));raise SystemExit(0 if r['passed']else 1)

if __name__=='__main__':main()
