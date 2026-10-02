#!/usr/bin/env python3
"""Finite split-foot and long-lever telescoping compression-brace diagnostic.

No component rating, lock qualification, or physical contract is implied.
The forefoot and heel rotate independently when unloaded and pins withdrawn.
"""
from pathlib import Path
import json, hashlib, importlib.util, math, copy
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'robots/gorilla_v0_1/cad/source'
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_scene.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(BASE)=='7a1e49f45838303ca5fd86265dc9980c10cde85ed7626424136afd3863aa5886'
definition=importlib.util.spec_from_file_location('helpers',ROOT/'scripts/models/build_gorilla_internal_structure.py')
h=importlib.util.module_from_spec(definition);definition.loader.exec_module(h)
STEEL=[.20,.24,.27,1.]; MOVING=[.36,.40,.43,1.]

def emit(name,body,m,role,**meta):
 assert m.is_watertight and m.is_winding_consistent and m.volume>0,name
 return {'name':'isd_'+name,'body':body,'role':role,'vertices_world_m':m.vertices.tolist(),'faces':m.faces.tolist(),'color_rgba':MOVING if 'moving' in role else STEEL,'edge_bevel_m':0,'hardware':True,'D_metadata':meta}
def spin(J,q,p):
 a=math.radians(q);R=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
 return np.array(J)+R@(np.array(p)-J)
def tube(a,b,w,d,t):return h.box_tube(np.array(a),np.array(b),w,d,t)
def solid(a,b,w,d):return h.solid_along(np.array(a),np.array(b),w,d)

def left_foot(qf=0,qh=0):
 parts=[]; frames=[];arch_clearances=[]
 # A raised arch and separate journals; no sole or beam crosses a pad hinge.
 arch=[tube([-.075,.50,.285],[-.075,.50,.220],.090,.120,.008),tube([-.055,.34,.230],[-.055,.78,.230],.060,.060,.006)]
 joints=[]
 for kind,x,q in [('forefoot',-.077,qf),('heel',-.131,qh)]:
  J=np.array([x,.50,.124]);body='left_'+('forefoot_display' if kind=='forefoot' else 'heel_display')
  for sy in (.37,.67):
   c=np.array([x,sy,.124]);arch.append(h.annulus(c,.047,.026,.026))
   arch.append(solid([-.055,sy,.230],c+[0,0,.032],.050,.018))
   # Bearing is a reference envelope, not solid steel at catalogue mass.
   parts.append(emit(kind+'_support_bearing_'+str(sy),'left_foot',h.annulus(c,.0255,.020,.024),'bearing_design_envelope',mass_range_kg=[.35,.5,.8],source='Custom 40mm-ID bearing space; rolling rating/fits/preload unknown'))
  moving=[h.annulus(J,.0198,.010,.560 if kind=='forefoot' else .368)]
  end=.430 if kind=='forefoot' else -.360
  yvals=(.59,.75) if kind=='forefoot' else (.40,.60)
  for sy in yvals:
   A=np.array([x,sy,.124]);B=np.array([end,sy,.063])
   start=.060 if kind=='forefoot' else -.215
   moving.extend([tube(A,B if kind=='heel' else [start,sy,.063],.050,.045,.006),tube([start,sy,.063],B,.060,.045,.006)])
   attach=np.array([.365 if kind=='forefoot' else -.345,sy,.078])
   for sg in (-1,1):
    cheek=attach+[0,sg*.026,0]
    moving.extend([h.annulus(cheek,.035,.0125,.012),solid(cheek+[0,0,-.025],[cheek[0],cheek[1],.063],.038,.012)])
  crossx=.280 if kind=='forefoot' else -.310
  moving.append(tube([crossx,.565 if kind=='forefoot' else .335,.060],[crossx,.780 if kind=='forefoot' else .640,.060],.054,.044,.006))
  tray=h.united(moving)
  for sy in yvals:
   attach=np.array([.365 if kind=='forefoot' else -.345,sy,.078])
   tray=trimesh.boolean.difference([tray,h.cylinder(attach,.030,.038),h.cylinder(attach,.0125,.090)],engine='manifold')
  T=np.eye(4);a=math.radians(q);T[:3,:3]=[[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]];T[:3,3]=J-T[:3,:3]@J
  tray.apply_transform(T)
  parts.append(emit(kind+'_continuous_tray',body,tray,'moving_load_tray',density_kg_m3=7850.,independent_hinge={'pivot_world_m':J.tolist(),'axis':[0,1,0],'unloaded_q_deg':q},connection_qualified=False))
  joints.append({'id':'left_'+kind,'parent':'left_foot','child':body,'pivot_world_m':J.tolist(),'axis':[0,1,0],'q_deg':q,'support_range_m':[-.163,.163],'shaft_and_bearing_rating_known':False})
  # Long axial brace divides pad moment through a 0.18/0.12m vertical offset,
  # not the old 30mm local stop. Each brace has two independent locks.
  for index,sy in enumerate(yvals):
   a0=np.array([-.055 if kind=='forefoot' else -.110,sy,.255 if kind=='forefoot' else .230])
   b0=np.array([.365 if kind=='forefoot' else -.345,sy,.078]);b=spin(J,q,b0)
   u=(b-a0)/np.linalg.norm(b-a0);L=float(np.linalg.norm(b-a0));L0=float(np.linalg.norm(b0-a0));Lbar=.260 if kind=='forefoot' else .145
   axis=np.array([0.,1.,0.]);pinr=.012;eyew=.030
   fixed_eye=h.annulus(a0,.028,pinr+.0005,eyew)
   root=solid(a0+u*.019,a0+u*.037,.046,.034)
   cap=solid(a0+u*.025,a0+u*.041,.064,.060)
   barrel=tube(a0+u*.035,a0+u*(.035+Lbar),.064,.060,.006)
   # Real positive overlap with eye; fixed end is supported by arch below.
   fixed=h.united([fixed_eye,root,cap,barrel])
   rodstart=a0+u*(L-.035-(.300 if kind=='forefoot' else .160))
   moving_neck=solid(b-u*.035,b-u*.019,.046,.034)
   rod=tube(rodstart,b-u*.035,.050,.044,.008)
   moving_eye=h.annulus(b,.028,pinr+.0005,eyew)
   plunger=h.united([rod,moving_neck,moving_eye])
   stations=(.210,.260) if kind=='forefoot' else (.105,.155)
   fixed_holes=[h.cylinder(a0+u*s,.0085,.084) for s in stations]
   moving_holes=[h.cylinder(a0+u*(s+L-L0),.0085,.084) for s in stations]
   fixed=trimesh.boolean.difference([fixed,*fixed_holes],engine='manifold')
   plunger=trimesh.boolean.difference([plunger,*moving_holes],engine='manifold')
   overlap_interval=[max(.035,float((rodstart-a0)@u)),min(.035+Lbar,L-.035)]
   if q==0:assert all(overlap_interval[0]+.0085<s<overlap_interval[1]-.0085 for s in stations)
   assert (rodstart-a0)@u>=.035-1e-8,'plunger penetrates fixed rear end'
   parts.append(emit(f'{kind}_brace{index}_fixed','left_foot',fixed,'endpoint_driven_brace_fixed',density_kg_m3=7850.,endpoint_A=a0.tolist(),endpoint_B=b.tolist(),mechanism='Pivoted telescoping box brace, does not follow one rigid body transform',motion_rule='Rebuild from transformed A/B endpoints',supplier_known=False,actual_lock_holes=True,overlap_interval_m=overlap_interval))
   parts.append(emit(f'{kind}_brace{index}_plunger',body,plunger,'endpoint_driven_brace_moving',density_kg_m3=7850.,endpoint_A=a0.tolist(),endpoint_B=b.tolist(),mechanism='Plunger endpoint at independent tray',motion_rule='Rebuild from transformed A/B endpoints',supplier_known=False,actual_lock_holes=True,overlap_interval_m=overlap_interval))
   for target,owner in [(a0,'left_foot'),(b,body)]:
    if owner=='left_foot':
     for sg in (-1,1):
      cheek=target+[0,sg*.026,0]
      arch.extend([h.annulus(cheek,.035,.0125,.012),solid([-.055,cheek[1],.215],cheek+[0,0,-.020],.038,.012)])
     arch_clearances.extend([h.cylinder(target,.030,.038),h.cylinder(target,.0125,.090)])
    parts.append(emit(f'{kind}_brace{index}_{"fixed" if owner=="left_foot" else "moving"}_pin',owner,h.cylinder(target,.012,.080),'steel_pin_design',density_kg_m3=7850.,interface_qualified=False))
   locks=[]
   # Two 16mm pins at 50mm spacing pass actual 17mm holes in both telescoping
   # members. Pins withdraw before folding; clearances do not qualify a lock.
   for station in stations:
    c=a0+u*station
    if q==0:
     parts.append(emit(f'{kind}_brace{index}_lock_{station}','left_foot',h.cylinder(c,.008,.082),'lock_pin_design',density_kg_m3=7850.,diameter_m=.016,shear_planes=2,locks_per_brace=2,lock_rating_known=False,hole_and_bearing_strength_unqualified=True))
    locks.append({'center_world_m':c.tolist(),'diameter_m':.016,'withdrawn_for_fold':q!=0})
   cap=math.pi*(.016/2)**2*2*2*(355e6/math.sqrt(3))/2
   direction=b-a0
   joints[-1].setdefault('brace_load_paths',[]).append({'brace':index,'A_world_m':a0.tolist(),'B_world_m':b.tolist(),'eye_length_m':L,'vertical_direction_fraction':abs(direction[2])/L,'moment_arm_about_hinge_m':float(np.cross(b-J,direction/L)[1]),'locks':locks,'ideal_two_pin_double_shear_force_at_yield_FS2_N':cap,'bearing_hole_ligament_and_connections_not_qualified':True})
 archmesh=h.united(arch)
 archmesh=trimesh.boolean.difference([archmesh,*arch_clearances],engine='manifold')
 parts.append(emit('continuous_main_arch','left_foot',archmesh,'fixed_load_arch',density_kg_m3=7850.,connection_qualified=False,no_continuous_sole=True))
 return parts,joints

base=json.loads(BASE.read_text());poses=[]
for label,qf,qh in [('neutral_locked',0,0),('unloaded_fold',-25,25)]:
 parts,joints=left_foot(qf,qh);right=[]
 for p in parts:
  m=h.native_mesh(p);m.apply_transform(np.diag([1,-1,1,1]));q=copy.deepcopy({k:v for k,v in p.items() if k not in ['vertices_world_m','faces']});q['name']=q['name'].replace('isd_','isd_right_',1);q['body']=q['body'].replace('left_','right_',1)
  md=q.get('D_metadata',{})
  for key in ('endpoint_A','endpoint_B'):
   if key in md:md[key][1]*=-1
  if 'independent_hinge' in md:md['independent_hinge']['pivot_world_m'][1]*=-1
  q['vertices_world_m']=m.vertices.tolist();q['faces']=m.faces.tolist();right.append(q)
 poses.append({'id':label,'left_forefoot_q_deg':qf,'left_heel_q_deg':qh,'parts':parts+right,'joint_paths_left':joints})
foot_parts=[p for p in base['parts'] if p['body'] in ['left_foot','left_forefoot_display','left_heel_display','right_foot','right_forefoot_display','right_heel_display']]
report={'robot_id':'gorilla_v0_1','candidate':'internal_structure_d_foot','base_scene_sha256':sha(BASE),'builder_sha256':sha(__file__),'pose_scenes':poses,'retained_ground_pad_names':[p['name'] for p in foot_parts if p['role'] in ('ground_pad','contact_surface_candidate')],'removed_old_physical_foot_part_names':[p['name'] for p in foot_parts if p['role'] not in ['armor_cover','armor_surface','ground_pad','contact_surface_candidate']],'scope':'Finite custom brace/arch/tray diagnostic with unchanged independent pads. Contact/lock pin holes, shear/bearing, mounting and folding sweeps not accepted. No longer uses 30mm contact stop as main pressure path. Full arch-to-leg attachment pending leg output.','physics_accepted':False,'geometry_accepted':False}
(OUT/'internal_structure_d_foot_scene.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'poses':len(poses),'native_parts_neutral':len(poses[0]['parts']),'scene_sha256':sha(OUT/'internal_structure_d_foot_scene.json')},indent=2))
