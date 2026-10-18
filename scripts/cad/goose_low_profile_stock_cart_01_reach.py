from pathlib import Path
import os,json,hashlib
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
import mujoco as mj
from scipy.optimize import least_squares
W=Path(__file__).resolve().parents[2]
PKG=W/'robots/goose_v0_2/models/physics_v0_2_20261018_04'
OUT=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01'
C=json.loads((PKG/'physical_contract.json').read_text());m=mj.MjModel.from_xml_path(str(PKG/'robot.xml'));d=mj.MjData(m);d.qpos[:]=m.qpos0
head=m.body('head_roll').id
def fk():mj.mj_kinematics(m,d);mj.mj_comPos(m,d);mj.mj_comVel(m,d);mj.mj_subtreeVel(m,d)
fk();ref=np.array(C['grip_reference_zero_m'])+np.array([0,0,m.qpos0[2]])
local=d.xmat[head].reshape(3,3).T@(ref-d.xpos[head])+np.array([0,0,-.006])
names=['neck_pitch','neck_mid_pitch','head_pitch'];idx=np.array([int(m.joint(n).qposadr[0]) for n in names]);bounds=np.array([m.jnt_range[m.joint(n).id] for n in names]);rows=[]
for z in [.32,.36,.40,.42,.44,.48,.50]:
 for x in [.22,.26,.30]:
  goal=np.array([x,0,z]);best=None
  for start in [[1.2,-.4,-.8],[1.7,-.7,-1],[.8,.3,-1.1]]:
   def f(q):
    d.qpos[idx]=q;fk();R=d.xmat[head].reshape(3,3);p=d.xpos[head]+R@local;a=np.arctan2(R[0,2],R[0,0]);return np.r_[(p-goal)[[0,2]],.1*a]
   s=least_squares(f,np.clip(start,bounds[:,0]+1e-6,bounds[:,1]-1e-6),bounds=(bounds[:,0]+1e-6,bounds[:,1]-1e-6),max_nfev=100,gtol=1e-11,ftol=1e-11,xtol=1e-11)
   err=np.linalg.norm(f(s.x))
   if best is None or err<best[0]:best=(err,s.x.copy())
  d.qpos[idx]=best[1];d.qpos[int(m.joint('beak_hinge').qposadr[0])]=.19682523003160665
  for j in C['passive_linkage_joints']:d.qpos[int(m.joint(j['name']).qposadr[0])]=j['mimic_multiplier']*d.qpos[int(m.joint(j['mimic_joint']).qposadr[0])]+j['mimic_offset_rad']
  mj.mj_forward(m,d)
  contacts=[{'a':m.geom(c.geom1).name,'b':m.geom(c.geom2).name,'distance_m':float(c.dist)} for c in d.contact if c.dist<-.0001]
  soles=[]
  for n in ['right_actual_sole','left_actual_sole']:
   g=m.geom(n).id;mid=int(m.geom_dataid[g]);v=m.mesh_vert[int(m.mesh_vertadr[mid]):int(m.mesh_vertadr[mid]+m.mesh_vertnum[mid])];w=v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g];soles.append({'min':w.min(0).tolist(),'max':w.max(0).tolist()})
  com=d.subtree_com[m.body('torso').id].copy();xmin=min(s['min'][0] for s in soles);xmax=max(s['max'][0] for s in soles)
  rows.append({'target_m':goal.tolist(),'joints_rad':dict(zip(names,best[1].tolist())),'error_m_equiv':float(best[0]),'negative_contacts':contacts,'COM_world_m':com.tolist(),'sole_bounds':soles,'unloaded_support_projection_x_margin_m':float(min(com[0]-xmin,xmax-com[0])),'upper_bound_horizontal_pull_forward_before_pitching_N':float(16.97020392883353*9.81*(xmax-com[0])/z),'scope':'Kinematic/COM projection only, not static drive or gait qualification'})
out={'baseline':'physics_v0_2_20261018_04','robot_xml_sha256':hashlib.sha256((PKG/'robot.xml').read_bytes()).hexdigest(),'physics_integrations':0,'training_updates':0,'GPU':0,'grip_head_local_m':local.tolist(),'head_pitch_goal_rad':0,'cold_jaw_angle_for_12mm_prior_handle_rad':.19682523003160665,'rows':rows,'limitations':'Zero-pose leg stance; true sole bounds are an outer envelope, not sampled pressure support. mj_forward computes instantaneous contacts, never integrates. No controller or dynamic balance qualification.'}
(OUT/'reach_check.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['target_m','joints_rad','error_m_equiv','negative_contacts','unloaded_support_projection_x_margin_m','upper_bound_horizontal_pull_forward_before_pitching_N']} for r in rows],indent=2))
