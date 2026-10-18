"""Read-only frozen04 FK and CAD render. No simulation integrations."""
from pathlib import Path
import os,json,hashlib,xml.etree.ElementTree as ET
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
import mujoco as mj
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

W=Path(__file__).resolve().parents[2];PKG=W/'robots/goose_v0_2/models/physics_v0_2_20261018_04';IMG=W/'robots/goose_v0_2/images/low_profile_stock_cart_01';E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01'
C=json.loads((PKG/'physical_contract.json').read_text());p=json.loads((W/'robots/goose_v0_2/cad/source/low_profile_stock_cart_01/parameters.json').read_text())
m=mj.MjModel.from_xml_path(str(PKG/'robot.xml'));d=mj.MjData(m);d.qpos[:]=m.qpos0
for n,q in zip(['neck_pitch','neck_mid_pitch','head_pitch'],p['robot_04_preferred_neck_pitch_mid_head_rad']):d.qpos[int(m.joint(n).qposadr[0])]=q
d.qpos[int(m.joint('beak_hinge').qposadr[0])]=.19682523003160665
for j in C['passive_linkage_joints']:d.qpos[int(m.joint(j['name']).qposadr[0])]=j['mimic_multiplier']*d.qpos[int(m.joint(j['mimic_joint']).qposadr[0])]+j['mimic_offset_rad']
mj.mj_forward(m,d)
robot=[]
for g in range(m.ngeom):
 if m.geom_type[g]!=mj.mjtGeom.mjGEOM_MESH:continue
 mid=int(m.geom_dataid[g]);v=m.mesh_vert[int(m.mesh_vertadr[mid]):int(m.mesh_vertadr[mid]+m.mesh_vertnum[mid])];f=m.mesh_face[int(m.mesh_faceadr[mid]):int(m.mesh_faceadr[mid]+m.mesh_facenum[mid])];vv=(v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g])*1000
 robot.append({'name':m.geom(g).name,'v':vv,'f':f.copy(),'color':m.geom_rgba[g,:3].copy()})
scene=trimesh.load(W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_01/goose_low_profile_stock_cart_01.glb');cart=[]
for node in scene.graph.nodes_geometry:
 T,key=scene.graph[node];geom=scene.geometry[key];vv=trimesh.transform_points(geom.vertices,T);vv=np.c_[vv[:,0],-vv[:,2],vv[:,1]]*1000;vv[:,0]+=650
 mat=geom.visual.material;rgba=getattr(mat,'baseColorFactor',None);col=np.array(rgba[:3])/255 if rgba is not None else [.75,.78,.8]
 cart.append({'name':node,'v':vv,'f':geom.faces,'color':col})

def side():
 fig,ax=plt.subplots(figsize=(15,7),layout='constrained');fig.patch.set_facecolor('#f7f8fa');ax.set_facecolor('#f7f8fa')
 for obj in cart+robot:
  tri=obj['v'][obj['f']];order=np.argsort(tri[:,:,1].mean(1))[::-1];poly=PolyCollection(tri[order][:,:,[0,2]],facecolor=obj['color'],edgecolor='none');ax.add_collection(poly)
 ax.axhline(0,color='#647381',lw=1);ax.set_xlim(-270,1370);ax.set_ylim(-35,745);ax.set_aspect('equal');ax.set_xlabel('World X / mm  (robot faces +X; backward towing moves -X)');ax.set_ylabel('Height / mm')
 ax.scatter([300],[480],s=45,c='#dd4c31',zorder=20);ax.annotate('Bite TCP / cart grip: (300, 0, 480) mm',xy=(300,480),xytext=(50,705),arrowprops={'arrowstyle':'->','color':'#b63f25'},fontsize=10,color='#a83c2b')
 ax.annotate('Deck 181.5 mm\nLow rim 290 mm',xy=(1000,182),xytext=(1040,425),arrowprops={'arrowstyle':'->'},fontsize=10)
 ax.annotate('',xy=(650,-15),xytext=(1300,-15),arrowprops={'arrowstyle':'<->'});ax.text(975,-25,'650 mm platform',ha='center',va='top',fontsize=9)
 ax.text(750,690,'20 kg cargo target + actual cart mass\nCAD concept; no whole-robot drag validation',fontsize=10,color='#334653',bbox={'facecolor':'white','edgecolor':'#bbc6ce','pad':8})
 ax.set_title('Goose 04 + low stock cart: actual FK + CAD context\nRobot shown as its 14 convex PHYSICS PROXIES, not original exterior CAD',fontsize=13)
 fig.savefig(IMG/'goose_cart_context_side.png',dpi=160);plt.close(fig)

def iso():
 fig=plt.figure(figsize=(13,8),layout='constrained');ax=fig.add_subplot(projection='3d');fig.patch.set_facecolor('#f7f8fa');ax.set_facecolor('#f7f8fa')
 for obj in robot+cart:
  coll=Poly3DCollection(obj['v'][obj['f']],facecolor=obj['color'],edgecolor='none',alpha=1);ax.add_collection3d(coll)
 ax.set_xlim(-250,1350);ax.set_ylim(-500,500);ax.set_zlim(0,750);ax.set_box_aspect([1600,1000,750]);ax.view_init(elev=22,azim=-65);ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm');ax.set_zlabel('Z / mm');ax.set_title('Actual 04 FK physics proxies + passive cart CAD\nNo robot geometry, mass, limits or drive changed; no dynamics run',fontsize=12)
 fig.savefig(IMG/'goose_cart_context_isometric.png',dpi=150);plt.close(fig)
side();iso()
bounds=[{'geom':o['name'],'min_mm':o['v'].min(0).tolist(),'max_mm':o['v'].max(0).tolist()} for o in robot]
negative=[{'a':m.geom(c.geom1).name,'b':m.geom(c.geom2).name,'distance_m':float(c.dist)} for c in d.contact if c.dist<-.0001]
foot=[b for b in bounds if 'actual_sole' in b['geom']];front_shoe=max(b['max_mm'][0] for b in foot)
out={'source_robot':'physics_v0_2_20261018_04','robot_xml_sha256':hashlib.sha256((PKG/'robot.xml').read_bytes()).hexdigest(),'cart_GLB_sha256':hashlib.sha256((W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_01/goose_low_profile_stock_cart_01.glb').read_bytes()).hexdigest(),'robot_geometry':'14 loaded convex physics meshes, not native exterior CAD','robot_named_joints_rad':dict(zip(['neck_pitch','neck_mid_pitch','head_pitch'],p['robot_04_preferred_neck_pitch_mid_head_rad'])),'cart_origin_robot_frame_mm':[650,0,0],'grip_TCP_robot_frame_mm':[300,0,480],'deck_world_x_range_mm':[650,1300],'basket_rim_z_mm':290,'shoes_to_cart_deck_front_horizontal_separation_mm':650-front_shoe,'loaded_robot_self_penetration_beyond0p1mm':negative,'robot_geom_bounds_mm':bounds,'physics_integrations':0,'training':0,'GPU':0,'qualifications':'Geometry context only. Shoe-to-platform X separation is a sufficient plane separation at this single FK pose; cart tow head and jaws require separate local clearance/contact checks. No swept gait or dynamic support qualification.'}
out['full_qpos']=d.qpos.tolist();out['joint_qpos_addresses']={m.joint(j).name:int(m.jnt_qposadr[j]) for j in range(m.njnt)}
np.savez_compressed(E/'selected_fk_state.npz',qpos=d.qpos.copy(),qvel=d.qvel.copy(),grip_center_robot_m=np.array([.3,0,.48]),cart_origin_robot_m=np.array([.65,0,0]))
(E/'goose_cart_context.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'geometry_bounds':bounds,'shoe_to_deck_X_mm':650-front_shoe,'self_penetrations':negative,'physics_integrations':0},indent=2))
