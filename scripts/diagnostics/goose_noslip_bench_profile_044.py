"""Zero-step BENCH ONLY profile builder. Sole permitted change: noslip_iterations0->2or8.
No execution/step API. Existingbaseline remains immutable. F alone may run after Root authorization.
"""
from pathlib import Path
import argparse,hashlib,json,copy,xml.etree.ElementTree as ET
import numpy as np,mujoco as mj
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def model_array_diff(a,b):
 changes=[];checked=[]
 for name in dir(a):
  if name.startswith('_'):continue
  x=getattr(a,name);y=getattr(b,name)
  if isinstance(x,np.ndarray):
   checked.append(name)
   if x.shape!=y.shape or not np.array_equal(x,y):changes.append(name)
 return checked,changes
def prepare(base_scene,base_MJB,base_initial,out,iterations):
 if iterations not in (2,8):raise ValueError('Exactly two predefinedcases2or8, no search')
 if out.exists():raise ValueError('Refuseoverwrite')
 root=ET.parse(base_scene).getroot();op=root.find('option')
 if op is None:raise ValueError('Explicit frozenoption required')
 original=mj.MjModel.from_binary_path(str(base_MJB));assert original.opt.noslip_iterations==0
 changed=copy.deepcopy(root);changed.find('option').set('noslip_iterations',str(iterations));out.mkdir(parents=True);ET.ElementTree(changed).write(out/'scene.xml',encoding='utf-8',xml_declaration=True);m=mj.MjModel.from_xml_path(str(out/'scene.xml'));checked,diff=model_array_diff(original,m)
 if diff:raise ValueError('Forbidden compiledmodelarray changes '+str(diff))
 optdiff=[]
 for name in dir(original.opt):
  if name.startswith('_'):continue
  a=getattr(original.opt,name);b=getattr(m.opt,name)
  if isinstance(a,np.ndarray):same=np.array_equal(a,b)
  elif isinstance(a,(int,float,bool,np.number)):same=(a==b)
  else:continue
  if not same:optdiff.append(name)
 assert optdiff==['noslip_iterations'],optdiff
 mj.mj_saveModel(m,str(out/'actual_scene.mjb'),None);(out/'initial_state.npz').write_bytes(Path(base_initial).read_bytes());z=np.load(base_initial);d=mj.MjData(m);d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl'];mj.mj_forward(m,d)
 receipt=dict(status='BENCH_ONLY_NUMERICAL_PROFILE_ZERO_STEP_NOT_EXECUTION_AUTHORIZATION',mujoco_version=mj.__version__,physics_steps=0,iterations=iterations,noslip_tolerance=float(m.opt.noslip_tolerance),base_scene=dict(path=str(base_scene),sha256=sha(base_scene)),base_MJB=dict(path=str(base_MJB),sha256=sha(base_MJB)),initial=dict(path=str(base_initial),sha256=sha(base_initial)),source_sha256=sha(__file__),scene_sha256=sha(out/'scene.xml'),MJB_sha256=sha(out/'actual_scene.mjb'),compiled_model_arrays_checked=len(checked),compiled_model_array_changes=diff,option_changes=optdiff,geometry_MCI_mu_solref_solimp_condim_caps_armature_eq_limits_unchanged=True,all_original_numeric_options_except_noslip_unchanged=True,initial_q_qvel_ctrl_bitwise_preserved=all(np.array_equal(getattr(d,k),z[k])for k in ['qpos','qvel','ctrl']),initial_ncon=d.ncon,scope='Globalmodel NoSlippostprocessing, not mouth-onlyfrictioncorrection; table andotherfrictiondimensions remainpartofthis numericalprofile.',physical_hardware_qualification=False)
 (out/'zero_step_profile_receipt.json').write_text(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base-scene',type=Path,required=True);p.add_argument('--base-mjb',type=Path,required=True);p.add_argument('--base-initial',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--iterations',type=int,choices=[2,8],required=True);a=p.parse_args();r=prepare(a.base_scene,a.base_mjb,a.base_initial,a.out,a.iterations);print(json.dumps(r,indent=2))
