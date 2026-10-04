"""Finite flat-foot IK and ideal static load screening for all six samples.

No integration, task policy, material calibration or object attachment. Source
SI is retained; gravity loads use exact source Jacobians and reduced four-bar
coordinates. Ground supports are ideal rigid points, not TPU qualification.
"""
from pathlib import Path
import json,math
import mujoco,numpy as np
from scipy.optimize import least_squares,linprog
from sai_agent.goose.convex_support import compiled_body_vertices
from sai_agent.goose.task_samples import primitives,aggregate_si

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
c=json.loads((R/'configs/task_proxy_11_v1_contract.json').read_text())
m=mujoco.MjModel.from_xml_path(str((R/'models/task_proxy_11_v1/robot.xml').resolve()));d=mujoco.MjData(m)
qidx=np.array([int(m.joint(n).qposadr[0]) for n in c['joint_order']]);vidx=np.array([int(m.joint(n).dofadr[0]) for n in c['joint_order']])
def sync():
 for j in c['passive_linkage_joints']:d.qpos[int(m.joint(j['name']).qposadr[0])]=j['mimic_multiplier']*d.qpos[int(m.joint(j['mimic_joint']).qposadr[0])]
 mujoco.mj_forward(m,d)

d.qpos[2]=-.0005;sync();feet=[m.body(s+'_ankle_roll').id for s in ['right','left']];neutral_feet=[d.xpos[b].copy() for b in feet]
locals={g:compiled_body_vertices(m,g) for g in range(m.ngeom) if g!=m.geom('ground').id}
T=np.zeros((m.nv,24));T[:6,:6]=np.eye(6)
for i,v in enumerate(vidx):T[v,6+i]=1
T[int(m.joint('beak_input_rotor').dofadr[0]),11]=1;T[int(m.joint('beak_coupler_link').dofadr[0]),11]=-1

def grip_point(offset):
 return d.site("grip").xpos + d.xmat[m.body("head_roll").id].reshape(3,3) @ np.array([offset,0.,0.])

def gravity_demand(payload_m,com):
 jacp=np.zeros((3,m.nv));jacr=jacp.copy();mujoco.mj_jac(m,d,jacp,jacr,np.array(com),m.body('head_roll').id)
 return T.T@(d.qfrc_bias-jacp.T@np.array([0.,0.,-9.81*payload_m]))

def gravity_static(payload_m,com):
 demand=gravity_demand(payload_m,com)
 points=[];J=[]
 for patch in c['contact_mapping']['ground_contact_quadrature']:
  b=m.body(patch['body']).id
  for local in patch['bottom_corners_body_m']:
   p=d.xmat[b].reshape(3,3)@np.array(local)+d.xpos[b];points.append(p)
   jp=np.zeros((3,m.nv));jr=jp.copy();mujoco.mj_jac(m,d,jp,jr,p,b);J.append(T.T@jp.T)
 JT=np.concatenate(J,axis=1);n=JT.shape[1];caps=np.array([j['continuous_design_limit_nm'] for j in c['joints']]);ub=[];rhs=[]
 for i in range(18):
  a=np.zeros(n+1);a[:n]=-JT[6+i];a[-1]=-caps[i];ub.append(a);rhs.append(-demand[6+i])
  a=np.zeros(n+1);a[:n]=JT[6+i];a[-1]=-caps[i];ub.append(a);rhs.append(demand[6+i])
 for i in range(8):
  for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
   a=np.zeros(n+1);a[3*i:3*i+3]=[sx,sy,-.65];ub.append(a);rhs.append(0.)
 objective=np.zeros(n+1);objective[-1]=1.;eq=np.c_[JT[:6],np.zeros(6)]
 bounds=[(None,None) if i%3<2 else (0,None) for i in range(n)]+[(0,None)]
 sol=linprog(objective,A_ub=np.array(ub),b_ub=np.array(rhs),A_eq=eq,b_eq=demand[:6],bounds=bounds,method='highs')
 if not sol.success:return {'feasible':False,'status':sol.message}
 tau=demand[6:]-JT[6:]@sol.x[:n]
 return {'feasible':True,'minimum_continuous_utilization':float(sol.x[-1]),'continuous_ok':bool(sol.x[-1]<=1+1e-8),'torques_nm':dict(zip(c['joint_order'],tau.tolist())),'forces_world_n':sol.x[:n].reshape(-1,3).tolist(),'root_balance_max_residual':float(np.max(np.abs(JT[:6]@sol.x[:n]-demand[:6]))),'foot_z_max_m':float(np.max(np.abs(np.array(points)[:,2])))}

def main():
 rows=[]
 for drop in [0.,.04,.07,.09]:
  d.qpos[:]=m.qpos0;d.qpos[2]=-.0005-drop
  for k,b in enumerate(feet):
   indices=qidx[8:11] if k==0 else qidx[14:17]
   signs=-1 if k==0 else 1;seed=signs*np.array([.3,-.7,.4])
   lo=np.array([c['joints'][i]['range_rad'][0] for i in ([8,9,10] if k==0 else [14,15,16])]);hi=np.array([c['joints'][i]['range_rad'][1] for i in ([8,9,10] if k==0 else [14,15,16])])
   def legfun(q):
    d.qpos[indices]=q;sync();rot=d.xmat[b].reshape(3,3);return np.r_[d.xpos[b][[0,2]]-neutral_feet[k][[0,2]],np.arctan2(rot[0,2],rot[2,2])*.1]
   leg=least_squares(legfun,np.clip(seed,lo,hi),bounds=(lo,hi),max_nfev=100,gtol=1e-11,ftol=1e-11,xtol=1e-11);legfun(leg.x)
   if np.max(np.abs(legfun(leg.x)))>1e-6:raise ValueError('grounded leg IK failed')
  stance=d.qpos.copy()
  for object_family in ['cylinder_weight','handle_weight']:
   si=aggregate_si(primitives(object_family,.1));z=-si['bounds_body_m'][0][2]
   for offset in [0.,.030]:
    for x in [.22,.26,.30,.34]:
     for pitch in [0.,.35,.7,1.05,1.4]:
      d.qpos[:]=stance;d.qpos[qidx[5]]=.22
      normal=np.array([np.sin(pitch),0,np.cos(pitch)]);target=np.array([x,0,z])+.006*normal
      def fun(q):
       d.qpos[qidx[1:4]]=q;sync();head=d.xmat[m.body('head_roll').id].reshape(3,3);actualpitch=np.arctan2(head[0,2],head[2,2]);return np.r_[10*(grip_point(offset)[[0,2]]-target[[0,2]]),actualpitch-pitch]
      lo=np.array([j['range_rad'][0] for j in c['joints'][1:4]]);hi=np.array([j['range_rad'][1] for j in c['joints'][1:4]])
      best=None
      for seed in [[2.2,-.6,pitch-1.6],[2.5,.2,pitch-2.7]]:
       s=least_squares(fun,np.clip(seed,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=50,gtol=1e-10)
       err=float(np.max(np.abs(fun(s.x))))
       if best is None or err<best[0]:best=(err,s.x.copy())
      err=best[0];fun(best[1]);gap=float(np.linalg.norm(grip_point(offset)-target))
      floor=[]
      for g,vertices in locals.items():
       b=m.geom_bodyid[g];wv=vertices@d.xmat[b].reshape(3,3).T+d.xpos[b];zg=float(wv[:,2].min())
       if zg<-.0002:floor.append([m.geom(g).name,zg])
      self_contacts=[]
      for cc in d.contact:
       if m.geom('ground').id not in cc.geom and cc.dist<-.0002:self_contacts.append([*[m.geom(int(g)).name for g in cc.geom],float(cc.dist)])
      row={'family':object_family,'grip_offset_body_m':[offset,0.,0.],'crouch_drop_m':drop,'object_grip_origin_world_m':[x,0,z],'head_pitch_rad':pitch,'ik_max_residual':err,'grip_error_m':gap,'floor_penetration':floor,'self_penetration':self_contacts,'geometry_possible':bool(err<.001 and gap<.0002 and not floor and not self_contacts),'qpos':d.qpos.tolist()}
      if row['geometry_possible']:row['load_static']={str(mass):gravity_static(mass,np.array([x,0,z])+aggregate_si(primitives(object_family,mass))['com_body_m']) for mass in [.1,.2,.3]}
      rows.append(row)
 out=ROOT/'artifacts/Goose_V0.1/task_samples_v1_domain/ground_static.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2)+'\n')
 good=[r for r in rows if r['geometry_possible']]
 print(json.dumps({'cases':len(rows),'geometry_possible':len(good),'best_geometric_residual':min(r['ik_max_residual'] for r in rows),'ground_probe_only':True}))

if __name__ == "__main__":
 main()
