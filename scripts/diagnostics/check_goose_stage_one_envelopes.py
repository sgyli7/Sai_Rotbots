"""Motor-case intersections independent of simulation's adjacent-body exclusions."""
from pathlib import Path
import sys,json
import numpy as np
import trimesh
import mujoco
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_one import candidate,mesh,R

def main():
 s=candidate();s.pivots['torso']=np.zeros(3);cases=[];g=json.loads((R/'evidence/stage_one_system_gate.json').read_text());parts=[]
 for n,key in s.selected.items():
  cat=s.catalog[key];mm=trimesh.creation.cylinder(cat['diameter']/2,cat['length'],sections=64);T=trimesh.geometry.align_vectors([0,0,1],s.axes[n]);T[:3,3]=s.pivots[n];mm.apply_transform(T);parts.append((n,s.parents[n],mm))
 for n,b in [('head_roll','head_pitch'),('beak_drive','head_roll')]:parts.append((n,b,mesh(s.parts[n+'_case'])))
 from scipy.spatial.transform import Rotation
 for p in g['pose_geometry']:
  # The stored root is the torso-frame position. FK here keeps original zero origin.
  R0=Rotation.from_quat(np.array(p['root_qpos'][3:])[[1,2,3,0]]).as_matrix();root=np.array(p['root_qpos'][:3])-R0@np.array([0,0,.29]);poses,_=s.fk(p['joint_q_rad'],root,R0);world=[]
  for n,b,mm in parts:
   m=mm.copy();position,rot=poses[b];m.vertices=position+(m.vertices-s.pivots[b])@rot.T;world.append((n,m))
  hits=[];candidates=0
  for k,(a,ma) in enumerate(world):
   for b,mb in world[k+1:]:
    if np.any(np.minimum(ma.bounds[1],mb.bounds[1])-np.maximum(ma.bounds[0],mb.bounds[0])<=0):continue
    candidates+=1;inter=trimesh.boolean.intersection([ma,mb],engine='manifold');volume=0. if inter.is_empty else abs(float(inter.volume))
    if volume>1e-10:hits.append(dict(a=a,b=b,intersection_mm3=volume*1e9))
  cases.append(dict(pose=p['name'],case_count=18,broadphase_candidates=candidates,intersections=hits,pass_motor_cases=not hits))
 # Conservative paired-plate weak-axis section screen; not a joint/bolt/FEA check.
 plates=[]
 for name,width,torque in [('lower_neck',.019,12),('upper_neck',.016,4),('thigh',.020,12),('shin',.018,12)]:
  t=.0055;stress=3*torque/(width*t*t);plates.append(dict(part=name,width_m=width,thickness_m=t,total_pair_moment_nm=torque,equal_share_weak_axis_bending_pa=stress,provisional_allowable_pa=80e6,below_provisional_allowable=stress<80e6))
 model=mujoco.MjModel.from_xml_path(str(R/'models/stage_one/robot.xml'));paths=[]
 for pose in g['pose_geometry']:
  hits=[]
  for fraction in np.linspace(0,1,61):
   data=mujoco.MjData(model)
   for n,q in pose['joint_q_rad'].items():data.qpos[model.joint(n).qposadr]=q*fraction
   mujoco.mj_forward(model,data)
   for contact in data.contact:
    a,b=model.geom(int(contact.geom1)).name,model.geom(int(contact.geom2)).name
    if 'floor' not in (a,b) and contact.dist<-.0005:hits.append(dict(fraction=float(fraction),a=a,b=b,depth_m=-float(contact.dist)))
  paths.append(dict(target=pose['name'],samples=61,self_collision_hits=hits,pass_self_collision=not hits))
 report=dict(interpolated_joint_path_self_collision=paths,status='NOMINAL_CASE_AND_SECTION_SCREEN',cases=cases,paired_plate_screen=plates,limits=['Case envelopes exclude connector plugs, cabling and bolt heads','Rounded cylinder proxies are dimensions, not vendor STEP tolerances','Weak-axis screen assumes equal moment sharing between plates and a declared 80MPa allowable; no hole stress concentration, fatigue, bolted-joint or drop proof','Hollow shell openings and foot upper cavities still need manufacture-level definition'])
 (R/'evidence/stage_one_envelope_gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
