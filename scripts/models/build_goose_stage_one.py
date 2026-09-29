"""Build a separate 18-axis, SI, first-stage candidate from preserved quad sources.

The inertias integrate actual source volumes where available and explicit box/
cylinder estimates elsewhere. This is a training candidate, not manufacturing CAD.
"""
from __future__ import annotations
import sys,json,hashlib,copy
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/diagnostics'))
from screen_goose_system_loads import System,vec,R,SCENE,BASIS,FOOT
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_r2_reference_rebuild import link,rounded_box
OUT=R/'models/stage_one';CONFIG=R/'configs/stage_one_contract.json'

CATALOG={
 'ak45_36_v3':dict(model='AK45-36 V3.0 KV80',mass=.349,diameter=.055,length=.0565,rated=8.,peak=24.,rpm=40.,no_load_rpm=52.,rotor_gcm2=181.9,ratio=36,backdrive=.8,usd=185.9,url='https://www.cubemars.com/product/ak45-36-v3-0-kv80-robotic-actuator.html'),
 'ak45_10_v3':dict(model='AK45-10 V3.0 KV75',mass=.262,diameter=.053,length=.0452,rated=2.5,peak=7.,rpm=120.,no_load_rpm=180.,rotor_gcm2=157.33,ratio=10,backdrive=.1,usd=155.9,url='https://www.cubemars.com/product/ak45-10-v3-0-kv75-robotic-actuator.html'),
 'ak40_10_v3':dict(model='AK40-10 V3.0 KV170',mass=.190,diameter=.053,length=.0402,rated=1.3,peak=4.1,rpm=370.,no_load_rpm=435.,rotor_gcm2=97.35,ratio=10,backdrive=.06,usd=135.9,url='https://www.cubemars.com/product/ak40-10-v3-0-kv170-robotic-actuator.html'),
}
def mesh(part):
 f=np.asarray(part['faces']);return trimesh.Trimesh(part['vertices'],np.vstack((f[:,[0,1,2]],f[:,[0,2,3]])),process=False)
def box_inertia(m,size):
 x,y,z=size;return m/12*np.diag([y*y+z*z,x*x+z*z,x*x+y*y])
def cylinder_inertia(m,r,length,axis):
 a=np.asarray(axis);a=a/np.linalg.norm(a);parallel=m*r*r/2;perp=m*(3*r*r+length*length)/12
 return perp*np.eye(3)+(parallel-perp)*np.outer(a,a)

def candidate():
 s=System();s.catalog=CATALOG;s.selected={};s.actuators={}
 for n in s.names:
  if n in ('head_roll','beak_hinge'):continue
  key='ak40_10_v3' if n.endswith('yaw') else ('ak45_10_v3' if n in ('neck_mid_pitch','head_pitch') or n.endswith('ankle_roll') else 'ak45_36_v3')
  s.selected[n]=key;s.actuators[n]=CATALOG[key]
 for side in ('right','left'):s.pivots[side+'_hip_yaw'][2]=.292
 s.pivots['head_roll'][0]=.081;s.pivots['head_roll'][2]=.5855
 # The neutral visual coordinates remain world referenced. Only the free root
 # frame is moved to the body; q=0 remains the accepted standing configuration.
 s.pivots['torso']=np.array([0.,0.,.29])
 replacements={p['name']:p for p in json.loads(FOOT.read_text())['parts']}
 s.parts.update(replacements)
 for p in s.parts.values():
  if '_fork_' in p['name']:
   v=np.array(p['vertices']);center_y=0. if 'neck' in p['name'] else (-.089 if p['name'].startswith('right') else .089)
   original_span=.058 if 'lower_neck' in p['name'] or 'thigh' in p['name'] else (.053 if 'upper_neck' in p['name'] else .057)
   if p['name'].endswith(('rear','front')):v[:,1]+=(-1 if p['name'].endswith('rear') else 1)*(.0665-original_span)/2
   else:v[:,1]=center_y+(v[:,1]-center_y)*(.0695/(original_span+.003))
   if p['name'].endswith(('rear','front')):
    yc=v[:,1].mean();v[:,1]=yc+(v[:,1]-yc)*(5.5/3.5)
   # Crossbars sit between motors, never through an output shaft/case.
   if p['name'].endswith('bridge'):
    group=p['group'];pair={'lower_neck_fork':('neck_pitch','neck_mid_pitch'),'upper_neck_fork':('neck_mid_pitch','head_pitch')}
    for side in ('right','left'):pair.update({side+'_thigh_fork':(side+'_hip_pitch',side+'_knee_pitch'),side+'_shin_fork':(side+'_knee_pitch',side+'_ankle_pitch')})
    a,b=pair[group];v+=(s.pivots[a]-s.pivots[b])/2
   p['vertices']=v.tolist()
  elif p['group']=='head_roll_bridge':
   if p['name'].endswith('bridge'):new=rounded_box((81,0,599.5),(16,63,7),2,8)
   else:
    y=-30 if p['name'].endswith('rear') else 30;new=link((42,y,605),(81,y,599.5),13,3.5)
   p['vertices']=(new.vertices/1000).tolist();p['faces']=np.asarray(new.faces).tolist()
  elif p['group']=='head_roll':
   v=np.array(p['vertices']);v[:,0]+=.005;v[:,2]-=.0015;p['vertices']=v.tolist()

 s.items=[i for i in s.items if i['name'] not in ('specified_payload_50g','left_power_hub','right_power_hub')]
 for i in s.items:
  n=i['name'];m=i['mass_kg'];size=None
  if n in s.selected:
   c=CATALOG[s.selected[n]];i.update(mass_kg=c['mass'],center_m=s.pivots[n].tolist(),relative_uncertainty=.03,basis='manufacturer mass; uniform cylinder inertia; output plane centered provisionally')
   I=cylinder_inertia(c['mass'],c['diameter']/2,c['length'],s.axes[n])
  elif n=='battery_service':
   i.update(mass_kg=.4,center_m=[-.070,0,.280],relative_uncertainty=.125,basis='CNHL 220406BK 6S 2200mAh catalog 372g plus 28g retention/lead allocation; total400g; supplier tolerance and lead layout remain');size=[.120,.065,.050]
  elif n=='compute_stack':i['center_m']=[-.060,0,.345];size=[.080,.048,.032]
  elif n=='interfaces_audio':i['center_m']=[.025,0,.250];size=[.044,.052,.032]
  elif n in ('logic_buck','servo_buck'):
   i.update(mass_kg=.025 if n=='logic_buck' else .04,relative_uncertainty=.25,basis='5V logic /12V servo converter and heatsink allocation; exact SKU pending');size=[.049,.029,.022]
  elif n=='head_roll':i['center_m'][0]+=.005;i['center_m'][2]-=.0015;size=[.026,.020,.034]
  elif n=='beak_drive':size=[.0585,.044,.0335]
  elif n.endswith('_mount_reserve') or n=='head_internal_frame_reserve':size=[.025,.025,.012]
  elif n=='camera_module':size=[.013,.030,.030]
  elif n in s.parts:
   mm=mesh(s.parts[n])
   if ('_fork_' in n or 'head_roll_bridge' in n) and n.endswith(('rear','front')):
    m=float(mm.volume*2700);i.update(mass_kg=m,relative_uncertainty=.1,basis='5.5mm aluminium paired plate; assumed density 2700kg/m3; painted ivory')
   I=mm.moment_inertia*(m/mm.mass)
   if '_fork_' in n or 'head_roll_bridge' in n:i['center_m']=mm.center_mass.tolist()
   # Original hollow-shell masses can be surface estimates; retain their mass
   # and volume-derived radius of gyration, flag uncertainty instead of epsilon.
   if np.linalg.eigvalsh(I).min()<=0:raise ValueError(('invalid source inertia',n))
  else:raise ValueError(('unassigned inertia',n))
  if size is not None:I=box_inertia(i['mass_kg'],size)
  i['inertia_at_com_kg_m2']=I.tolist()
 # Distributed additions allow widened load-bearing fork adapters, harness and
 # dual CAN interfaces. They are allocations, not detailed selected assemblies.
 for n in s.names:
  if n=='beak_hinge':continue
  amount=.020 if n not in ('head_pitch','head_roll') else .010
  s.items.append(dict(name=n+'_structure_allocation',body=n,mass_kg=amount,center_m=s.pivots[n].tolist(),relative_uncertainty=.3,
   basis='additional adapter/harness allowance above previous mount reserve',inertia_at_com_kg_m2=box_inertia(amount,[.040,.040,.016]).tolist()))
 s.items.append(dict(name='dual_can_interface_allocation',body='torso',mass_kg=.06,center_m=[-.04,0,.32],relative_uncertainty=.3,
  basis='dual CAN + harness allocation replacing two TTL hubs',inertia_at_com_kg_m2=box_inertia(.06,[.07,.04,.016]).tolist()))
 return s

def make_contract(s):
 joints=[]
 for n in s.names:
  if n=='beak_hinge':lim=[0.,.55];peak=4.7;cont=3.5;speed=1.;arm=.0003;friction=.05;kp=12.;kd=.6;scale=.25
  elif n=='head_roll':lim=[-.6,.6];peak=.18;cont=.14;speed=3.;arm=.00002;friction=.006;kp=2.;kd=.1;scale=.25
  else:
   c=s.actuators[n];peak={'ak45_36_v3':12.,'ak45_10_v3':4.,'ak40_10_v3':2.}[s.selected[n]]
   cont=c['rated']*.8;speed=c['rpm']*np.pi/30;arm=c['rotor_gcm2']*1e-7*c['ratio']**2;friction=c['backdrive']*.5
   kp=100. if c['rated']==8 else (20. if c['rated']==2.5 else 12.);kd=3.5 if c['rated']==8 else .7;scale=.4 if 'pitch' in n else .25
   if n=='neck_pitch':lim=[-.6,2.6];scale=.3
   elif n=='neck_mid_pitch':lim=[-1.4,1.4];scale=.3
   elif n=='head_pitch':lim=[-1.6,1.6];scale=.3
   elif n.endswith('hip_yaw'):lim=[-.6,.6]
   elif n.endswith('hip_roll'):lim=[-.5,.5]
   elif n.endswith('hip_pitch'):lim=[-1.1,1.1]
   elif n.endswith('knee_pitch'):lim=([-.2,1.8] if n.startswith('right') else [-1.8,.2])
   elif n.endswith('ankle_pitch'):lim=[-1.1,1.1]
   else:lim=[-.5,.5]
  scale=max(abs(lim[0]),abs(lim[1])) # every declared operational pose must be reachable by the action map
  joints.append(dict(name=n,parent=s.parents[n],pivot_world_at_zero_m=s.pivots[n].tolist(),axis_parent=s.axes[n].tolist(),range_rad=lim,
   q_neutral_rad=0.,action_scale_rad=scale,kp_nm_rad=kp,kd_nm_s_rad=kd,torque_peak_limit_nm=peak,continuous_design_limit_nm=cont,
   speed_limit_rad_s=speed,armature_kg_m2=arm,frictionloss_nm=friction,damping_nm_s_rad=.01,
   actuator=s.selected.get(n,'xm540_3_to_1_unselected_gears' if n=='beak_hinge' else 'xc330_m288_t'),
   limits_status='candidate conservative operational limits, not certified mechanical stops'))
 bodies=[]
 for b in ['torso']+s.names:
  items=[i for i in s.items if i['body']==b];mass=sum(i['mass_kg'] for i in items);center=sum(i['mass_kg']*np.array(i['center_m']) for i in items)/mass;I=np.zeros((3,3))
  for i in items:
   d=np.array(i['center_m'])-center;I+=np.array(i['inertia_at_com_kg_m2'])+i['mass_kg']*((d@d)*np.eye(3)-np.outer(d,d))
  uncertainty=sum(i['mass_kg']*i['relative_uncertainty'] for i in items)/mass
  bodies.append(dict(name=b,mass_kg=mass,com_local_m=(center-s.pivots[b]).tolist(),inertia_at_com_body_kg_m2=I.tolist(),
   mass_relative_design_uncertainty=uncertainty,com_randomization_m=.005 if b=='torso' else .003,inertia_multiplier_range=[.8,1.2]))
 return dict(schema='goose_stage_one_si_v1',status='TRAINING_CANDIDATE_NOT_HARDWARE_FREEZE',robot='Goose_V0.1',
  coordinates='right-handed X forward Y left Z up; radians, metres, seconds, kilograms, newton-metres; quaternion wxyz',
  root_origin_at_zero_m=s.pivots['torso'].tolist(),joint_order=s.names,joints=joints,bodies=bodies,
  nominal_robot_mass_kg=sum(i['mass_kg'] for i in s.items),actuator_catalog=CATALOG,
  physics_dt_s=.001,torque_dt_s=.005,policy_dt_s=.02,observation_size=65,action_size=18,
  observation_layout=[dict(name='body_angular_velocity_rad_s',start=0,length=3,scale=.25),dict(name='projected_gravity_unit',start=3,length=3,scale=1),
   dict(name='command_vx_vy_yaw_rate',start=6,length=3,scale=1),dict(name='joint_q_minus_neutral_rad',start=9,length=18,scale=1),
   dict(name='joint_velocity_rad_s',start=27,length=18,scale=.1),dict(name='previous_clipped_action',start=45,length=18,scale=1),dict(name='phase_sin_cos',start=63,length=2,scale=1)],
  action_semantics='clip to [-1,1]; target=q_neutral+scale*action; clamp to range; slew at speed_limit; PD at 200Hz; speed-envelope torque clipping; 2s squared-torque budget derates to continuous limit; nominal-model gravity feedforward for five neck/head joints from encoder q and IMU orientation only; no root support, no actual randomized-mass input',
  gravity_feedforward_joints=s.names[:5],positive_mechanical_power_limit_w=350.,phase_frequency_hz=1.2,foot_friction_range=[.45,.9],latency_policy_steps=[0,1],strength_multiplier_range=[.85,1.0],
  engineering_change_rule='Joint order/axes/frames/contact mesh/limits/actuator family changes require a new model+contract version. Allocated masses/COM/inertias may only vary within documented randomization; no guarantee of transfer without holdout and real calibration.',
  compatibility=dict(mujoco='implemented',godot_jolt='neutral SI data only; adapter validation pending',unity='neutral SI data only; adapter validation pending',bevy='neutral SI data only; adapter validation pending'),
  source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SCENE,BASIS,FOOT)},items=s.items)

def build():
 s=candidate();c=make_contract(s);OUT.mkdir(parents=True,exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
 mj=ET.Element('mujoco',model='goose_stage_one_18axis');ET.SubElement(mj,'compiler',angle='radian',inertiafromgeom='false',meshdir='assets')
 ET.SubElement(mj,'option',timestep='.001',gravity='0 0 -9.81',integrator='implicitfast',iterations='50',cone='elliptic')
 default=ET.SubElement(mj,'default');ET.SubElement(default,'geom',friction='.65 .01 .002',solref='.008 1',solimp='.95 .99 .001')
 ET.SubElement(mj,'visual');assets=ET.SubElement(mj,'asset');world=ET.SubElement(mj,'worldbody')
 ET.SubElement(world,'light',pos='0 -2 3',dir='0 0 -1',diffuse='.8 .8 .8');ET.SubElement(world,'geom',name='floor',type='plane',size='3 3 .1',rgba='.24 .27 .28 1',contype='1',conaffinity='3')
 nodes={};geom_manifest=[]
 for b in c['bodies']:
  n=b['name'];parent=s.parents.get(n);node=ET.SubElement(world if parent is None else nodes[parent],'body',name=n,pos=vec(s.pivots[n]-(s.pivots[parent] if parent else 0)));nodes[n]=node
  I=np.array(b['inertia_at_com_body_kg_m2']);ET.SubElement(node,'inertial',mass=str(b['mass_kg']),pos=vec(b['com_local_m']),fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
  if parent is None:ET.SubElement(node,'freejoint',name='root')
  else:
   j=c['joints'][s.names.index(n)];ET.SubElement(node,'joint',name=n,type='hinge',axis=vec(s.axes[n]),range=vec(j['range_rad']),armature=str(j['armature_kg_m2']),frictionloss=str(j['frictionloss_nm']),damping=str(j['damping_nm_s_rad']))
 def geom(body,name,kind,**kw):
  attrs=dict(name=name,type=kind,**{k:str(v) for k,v in kw.items()});ET.SubElement(nodes[body],'geom',**attrs);geom_manifest.append(dict(body=body,**attrs))
 # Preserve editable quad source; triangulate only the physics/render interchange.
 # Group by body and source material colour to avoid hundreds of runtime geoms.
 groups={}
 for p in s.parts.values():
  if p['group'] in s.selected:continue
  if p['name'] in ('battery_service','compute_stack','left_power_hub','right_power_hub','logic_buck','servo_buck','main_protection','interfaces_audio'):continue
  owner=('head_roll' if p['group']=='beak_drive' else s.parents['head_roll']) if p['group'] in ('head_roll','beak_drive') else s.owner(p['name']);mm=mesh(p);mm.vertices-=s.pivots[owner]
  palette={'ivory':(.78,.78,.74,1),'orange':(.95,.19,.002,1),'graphite':(.045,.055,.065,1),'rubber':(.025,.03,.035,1),'seam':(.065,.068,.068,1),'titanium':(.45,.49,.51,1),'glass':(.01,.025,.04,1),'lens':(.003,.009,.016,1)}
  color=palette[p['material']]
  if len(color)==3:color=(*color,1.)
  groups.setdefault((owner,color),[]).append(mm)
 for k,((body,color),meshes) in enumerate(groups.items()):
  name=f'visual_{k:02d}';combined=trimesh.util.concatenate(meshes);combined.export(OUT/'assets'/f'{name}.obj')
  ET.SubElement(assets,'mesh',name=name,file=f'{name}.obj');geom(body,name,'mesh',mesh=name,rgba=vec(color),contype='0',conaffinity='0',group='1')
 # Catalog envelopes visible so changed hardware is not hidden behind old servos.
 for n,key in s.selected.items():
  cat=CATALOG[key];body=s.parents[n];a=s.axes[n];center=s.pivots[n]-s.pivots[body];half=cat['length']/2
  geom(body,n+'_case','cylinder',fromto=vec(np.r_[center-a*half,center+a*half]),size=str(cat['diameter']/2),rgba='.10 .12 .13 1',contype='2',conaffinity='3',group='2')
 # Jaw contact geometry follows the actual outer surfaces; closing collision
 # between the adjacent jaws is handled by the joint stop, not a false solid skull.
 for name in ('fixed_upper_bill','hinged_lower_bill'):
  part=s.parts[name];body=s.owner(name);mm=mesh(part);mm.vertices-=s.pivots[body];asset=name+'_contact';mm.convex_hull.export(OUT/'assets'/f'{asset}.obj')
  ET.SubElement(assets,'mesh',name=asset,file=f'{asset}.obj');geom(body,asset,'mesh',mesh=asset,rgba='.9 .6 .1 .2',contype='2',conaffinity='3',group='3')
 # Additional collision hulls are deliberately coarse and separately identified.
 for body,name,pos,size in [('torso','torso_collision',[-.015,0,.301],[.147,.109,.085]),('head_roll','head_collision',[.128,0,.603],[.054,.039,.042])]:
  geom(body,name,'ellipsoid',pos=vec(np.array(pos)-s.pivots[body]),size=vec(size),rgba='.8 .4 .1 .15',contype='2',conaffinity='3',group='3')
 # Paired forks have an open centre; a solid central capsule would invent
 # collisions and erase the motor clearance. Use each real plate's convex hull.
 for p in s.parts.values():
  if not ('_fork_' in p['name'] or p['group']=='head_roll_bridge'):continue
  body=s.owner(p['name']);mm=mesh(p);mm.vertices-=s.pivots[body];name=p['name']+'_collision'
  mm.convex_hull.export(OUT/'assets'/f'{name}.obj');ET.SubElement(assets,'mesh',name=name,file=f'{name}.obj')
  geom(body,name,'mesh',mesh=name,rgba='.9 .6 .1 .2',contype='2',conaffinity='3',group='3')
 for side in ('right','left'):
  body=side+'_ankle_roll';h=s.contact_hulls[side];xy=h.points[h.vertices];v=np.vstack([np.c_[xy,np.full(len(xy),z)] for z in (.0005,.014)])-s.pivots[body]
  mm=trimesh.convex.convex_hull(v);name=side+'_foot_contact';mm.export(OUT/'assets'/f'{name}.obj');ET.SubElement(assets,'mesh',name=name,file=f'{name}.obj')
  geom(body,name,'mesh',mesh=name,rgba='.3 .5 .2 .3',contype='2',conaffinity='3',condim='6',group='3')
 # The body is hollow around the in-body serial hip joints and neck yaw mount.
 # These exclusions are intentional internal assembly relationships, listed in SI.
 excludes=set()
 for n,p in s.parents.items():excludes.add(tuple(sorted((n,p))))
 for n in ('neck_pitch','neck_mid_pitch','right_hip_roll','left_hip_roll','right_hip_pitch','left_hip_pitch'):
  if n!='neck_mid_pitch':excludes.add(tuple(sorted(('torso',n))))
 contact=ET.SubElement(mj,'contact')
 for a,b in sorted(excludes):ET.SubElement(contact,'exclude',body1=a,body2=b)
 actuators=ET.SubElement(mj,'actuator')
 for j in c['joints']:ET.SubElement(actuators,'motor',name=j['name']+'_motor',joint=j['name'],gear='1',ctrllimited='true',ctrlrange=vec([-j['torque_peak_limit_nm'],j['torque_peak_limit_nm']]))
 ET.indent(mj);xml=ET.tostring(mj,encoding='unicode');(OUT/'robot.xml').write_text(xml+'\n')
 c['collision_geometries']=geom_manifest;c['collision_exclusions']=[list(x) for x in sorted(excludes)]
 c['asset_sha256']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT/'assets'/a.attrib['file'] for a in assets.findall('mesh'))}
 c['model_sha256']=hashlib.sha256((OUT/'robot.xml').read_bytes()).hexdigest();CONFIG.write_text(json.dumps(c,indent=2)+'\n')
 import mujoco
 model=mujoco.MjModel.from_xml_path(str(OUT/'robot.xml'));d=mujoco.MjData(model);mujoco.mj_forward(model,d)
 collisions=[dict(a=model.geom(int(x.geom1)).name,b=model.geom(int(x.geom2)).name,distance_m=float(x.dist)) for x in d.contact if x.dist<-.0001]
 print(json.dumps(dict(mass=c['nominal_robot_mass_kg'],nq=model.nq,nv=model.nv,nu=model.nu,neutral_penetrations=collisions),indent=2))
 if model.nu!=18:raise ValueError('contract mismatch')
 return s,c
if __name__=='__main__':build()
