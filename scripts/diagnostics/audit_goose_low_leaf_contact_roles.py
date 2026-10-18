"""Independent task-role checks for a low-leaf collision derivative.

Never edits the model, hardware contract, masks, source meshes or producer's
files. Full convex-head and sole-support probes are source feasibility tests.
"""
from pathlib import Path
import argparse,hashlib,json,sys,importlib.util
import numpy as np
import mujoco
from scipy.spatial import ConvexHull
from scipy.optimize import linprog


def ref(p):
 p=Path(p);return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def world_vertices(m,d,g):
 if m.geom_type[g]!=mujoco.mjtGeom.mjGEOM_MESH:return None
 k=int(m.geom_dataid[g]);i=int(m.mesh_vertadr[k]);n=int(m.mesh_vertnum[k]);return np.asarray(m.mesh_vert[i:i+n],float)@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]


def box_intersection(hull,centre,size):
 # Positive Chebyshev radius proves an interior intersection. This is not a
 # nearest-surface distance or a claim about the complete source's cavities.
 A=np.vstack([hull.equations[:,:3],np.eye(3),-np.eye(3)]);b=np.r_[-hull.equations[:,3],centre+size,-centre+size]
 result=linprog([0,0,0,-1.],A_ub=np.c_[A,np.linalg.norm(A,axis=1)],b_ub=b,bounds=[(None,None)]*3+[(0,None)],method='highs')
 return dict(interior_intersection=bool(result.success and result.x[3]>1e-8),interior_witness_m=result.x[:3].tolist()if result.success else None,interior_radius_m=float(result.x[3])if result.success else None,LP_status=result.message)


def run(a):
 a.output.mkdir(exist_ok=False,parents=True);p=a.package.resolve();c=json.loads((p/'physical_contract.json').read_text());m=mujoco.MjModel.from_xml_path(str(p/'robot.xml'));d=mujoco.MjData(m)
 spec=importlib.util.spec_from_file_location('shipped_source_contact_helper',p/'verify_contacts.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);helper.pose(m,d,c,{},root_z=0.)
 by={}
 for g in range(m.ngeom):
  owner=helper.owner(m,g);v=world_vertices(m,d,g)
  if not m.geom_bodyid[g]or v is None:continue
  by.setdefault(owner,[]).append((g,v))
 groups=[]
 for owner,rows in by.items():
  v=np.vstack([v for _,v in rows]);groups.append(dict(owner=owner,source_geom_count=len(rows),source_geometries=[m.geom(g).name for g,_ in rows],world_zero_bounds_m=[v.min(0).tolist(),v.max(0).tolist()],raw_vertices=len(v)))
 soles=[]
 for side in ['left','right']:
  rows=[(g,v)for g,v in by[side+'_ankle_roll']if 'sole'in m.geom(g).name]
  if not rows:
   rows=by[side+'_ankle_roll']
  v=np.vstack([v for _,v in rows]);z=float(v[:,2].min());base=v[abs(v[:,2]-z)<2e-6];xy=np.unique(np.round(base[:,:2],10),axis=0);h=ConvexHull(xy);source=xy[h.vertices]
  angles=np.arange(32)*2*np.pi/32;directions=np.c_[np.cos(angles),np.sin(angles)];chosen=np.unique(np.argmax(source@directions.T,axis=0));kept=source[chosen];fine=np.arange(1440)*2*np.pi/1440;dirs=np.c_[np.cos(fine),np.sin(fine)];omission=np.max(source@dirs.T,axis=0)-np.max(kept@dirs.T,axis=0)
  soles.append(dict(side=side,source_geoms=[m.geom(g).name for g,_ in rows],true_bottom_z_m=z,true_bottom_max_planarity_error_m=float(np.ptp(base[:,2])),source_support_outline_vertices=len(source),selected_bottom_vertices=len(kept),selected_bottom_world_zero_m=np.c_[kept,np.full(len(kept),z)].tolist(),source_bounds_m=[v.min(0).tolist(),v.max(0).tolist()],dense1440_direction_max_support_loss_m=float(omission.max()),finite_support_probe_not_Hausdorff_or_terrain_qualification=True,remaining_64_vertex_budget_for_upper_crown=64-len(kept)))
 headpoints=np.vstack([v for _,v in by['head_roll']]);hh=ConvexHull(headpoints);plane=float(c['grip_reference_zero_m'][2]);centres=[np.array([.21,0,plane-.009]),np.array([.21,0,plane-.007])]
 mouth=[dict(name=label,box_dimensions_m=[.02,.02,.016],centre_world_zero_m=cc.tolist(),full_convex_head_and_upperjaw_source_hull=box_intersection(hh,cc,np.array([.01,.01,.008])))for label,cc in zip(['open_object_clearance_domain','upper_positive_contact_domain'],centres)]
 report=dict(schema='goose_independent_low_leaf_task_role_feasibility_v1',source_package=str(p),inputs=[ref(p/x)for x in ['robot.xml','physical_contract.json','collision_manifest.json']],mujoco_version=mujoco.__version__,loaded_source_robot_collision_geoms=sum(bool(m.geom_bodyid[g])for g in range(m.ngeom)),body_geometry_groups=groups,true_sole_support_reduction=soles,head_and_upperjaw_one_convex_leaf_feasibility=mouth,
 allowed_minimal_role_adjacency_candidates=[dict(pair=['torso','neck_pitch'],mechanism='Through internal neck_yaw without intervening exterior role; exterior root proxy may overlap adjacent torso.'),dict(pair=['torso','left_hip_roll'],mechanism='Through internal left_hip_yaw only.'),dict(pair=['torso','right_hip_roll'],mechanism='Through internal right_hip_yaw only.'),dict(pair=['neck_mid_pitch','head_roll'],mechanism='Through internal head_pitch; the headpitch knuckle may be approximated by an upperneck-end spherical envelope with explicit source bound.'),dict(pair=['left_knee_pitch','left_ankle_roll'],mechanism='Through internal AP only; one shoe proxy deliberately abstracts local shoe pivot opening.'),dict(pair=['right_knee_pitch','right_ankle_roll'],mechanism='Through internal AP only; no cross-leg exclusion.')],
 nonadjacent_pairs_that_must_remain_enabled=[['torso','neck_mid_pitch'],['torso','head_roll'],['torso','left_hip_pitch'],['torso','right_hip_pitch'],['torso','left_knee_pitch'],['torso','right_knee_pitch'],['left_ankle_roll','right_ankle_roll'],['left_hip_pitch','right_hip_pitch'],['left_knee_pitch','right_knee_pitch']],
 task_caveats=['One convex head+upperjaw must be evaluated against a20x20x16mm object; source cavity exactness is not an installation-hole criterion.', 'One foot hull must keep actual horizontal support plane and support polygon while abstracting upper shoe articulation gaps.', 'Absent neck_yaw/head_pitch/AP exterior leaves are allowed only with disclosed interior/knuckle abstraction; true MCI remains in every original body.', 'Manufacturing cavities and small installed holes need not survive; mouth object clearance and nonadjacent external collisions must survive.'],mass_or_inertia_or_actuator_modified=False,producer_model_written=False)
 rp=a.output/'source_contact_role_feasibility.json';rp.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(report=ref(rp),sole_losses_m=[q['dense1440_direction_max_support_loss_m']for q in soles],mouth=mouth)),flush=True)


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--package',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);run(ap.parse_args())
