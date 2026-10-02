"""Conditional mass and neck gravity screen of the user-accepted fuller geometry.

Uses real proxy locations, catalog motor masses, explicitly assumed shell/mount
masses. Not a released inertia model, thermal rating or collision-free workspace.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import trimesh


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 scene=json.loads(a.scene.read_text());basis=json.loads((a.scene.parent/'hardware_basis.json').read_text());root=Path(__file__).resolve().parents[2]
 spec=json.loads((root/'robots/Goose_V0.1/configs/robot_spec.json').read_text())['servos']
 specs={s['model']:s for s in spec.values()};parts={x['name']:x for x in scene['parts']};motors={m['joint']:m for m in basis['actuators']};items=[]
 def chain(group):
  if group in ('neck_mid_pitch','lower_neck_fork'):return 'lower'
  if group in ('head_pitch','upper_neck_fork'):return 'upper'
  if group in ('head','head_internal','lower_beak','head_roll','head_roll_bridge','beak_drive','beak_transmission'):return 'head'
  return 'fixed'
 def add(name,group,mass,center,method,uncertainty):
  items.append(dict(name=name,chain=chain(group),mass_kg=float(mass),center_m=np.asarray(center).tolist(),basis=method,relative_uncertainty=uncertainty))
 for joint,m in motors.items():
  s=specs[m['model']];center=np.array(m['shaft_world_mm'])/1000+np.array(m['up_world'])*(s['shaft_from_top_m']-m['case_whd_mm'][1]/2000)
  add(joint,joint,s['mass_kg'],center,'catalog motor mass; uniform case center approximation',.03)
  add(joint+'_mount_reserve',joint,.012,np.array(m['shaft_world_mm'])/1000,'assumed horn/idler/fixing allowance, not a selected assembly',.50)
 electronic_mass={'battery_service':.145,'compute_stack':.054,'left_power_hub':.035,'right_power_hub':.035,'logic_buck':.009,'servo_buck':.009,'main_protection':.093,'interfaces_audio':.10235}
 for part in scene['parts']:
  name,group,role=part['name'],part['group'],part.get('role','');vv=np.asarray(part['vertices']);center=(vv.min(0)+vv.max(0))/2
  if group in motors or group=='head_internal':continue
  if group=='torso_electronics':add(name,group,electronic_mass[name],center,'component mass budget incl. assigned harness reserve; not measured assembly',.35);continue
  if group=='chassis':add(name,group,.150,center,'assumed machined/frame assembly budget, not solid visual block',.50);continue
  if group=='neck_cable':add(name,'lower_neck_fork' if name.endswith(('0','1','2')) else 'upper_neck_fork',.005,center,'assumed 5 g per visible cable segment; moving harness unmeasured',.50);continue
  q=np.asarray(part['faces']);tri=np.vstack((q[:,[0,1,2]],q[:,[0,2,3]]));mesh=trimesh.Trimesh(vv,tri,process=False)
  if mesh.volume<=0:raise ValueError('nonpositive source volume '+name)
  center=mesh.center_mass
  if role in ('hollow_shell_candidate','removable_cover_candidate'):
   mass=mesh.volume*1250;method='actual modeled hollow shell volume at assumed PETG 1250 kg/m3';unc=.20
  elif role=='shell_outer_surface_candidate' or name in ('fixed_upper_bill','hinged_lower_bill'):
   mass=min(mesh.volume,mesh.area*.0024)*1250;center=np.average(mesh.triangles_center,axis=0,weights=mesh.area_faces);method='conditional 2.4 mm shell area approximation; head/beak/foot are not hollow manufacturing CAD';unc=.35
  elif group=='beak_transmission':
   mass=mesh.volume*7850;method='steel-filled transmission envelope bound; includes solid gear discs, bearing annuli, shaft';unc=.40
  else:
   density={'ivory':1250,'orange':1250,'graphite':1250,'rubber':1200,'titanium':2700,'glass':2500,'lens':2500,'seam':1200}[part['material']]
   mass=mesh.volume*density;method=f'solid nominal mesh with assumed density {density} kg/m3; material not released';unc=.30
  add(name,group,mass,center,method,unc)
 add('camera_module','head',.025,[.166,0,.606],'assumed 25 g complete camera module; optical meshes excluded',.40)
 # Missing internal head bearing seats, spine and root fixing are deliberately budgeted.
 add('head_internal_frame_reserve','head',.080,[.139,0,.588],'unmodeled internal metal load-path reserve',.50)
 mass=sum(i['mass_kg'] for i in items);com=sum(i['mass_kg']*np.array(i['center_m']) for i in items)/mass
 uncertainty=sum(i['mass_kg']*i['relative_uncertainty'] for i in items)
 roots=[np.array(motors[n]['shaft_world_mm'])/1000 for n in ('neck_pitch','neck_mid_pitch','head_pitch')]
 def ry(t):
  c,s=np.cos(np.deg2rad(t)),np.sin(np.deg2rad(t));return np.array([[c,0,s],[0,1,0],[-s,0,c]])
 trials=[]
 for lower_delta in (0,45,75,105):
  for upper_delta in (0,-30,30):
   if lower_delta==0 and upper_delta!=0:continue
   rr,ee,hh=roots;E=rr+ry(lower_delta)@(ee-rr);H=E+ry(lower_delta+upper_delta)@(hh-ee)
   def place(item):
    c=np.array(item['center_m']);g=item['chain']
    if g=='lower':return rr+ry(lower_delta)@(c-rr)
    if g=='upper':return E+ry(lower_delta+upper_delta)@(c-ee)
    if g=='head':return H+(c-hh) # compensating head pitch keeps the head level
    return c
   tip=H+(np.array([.263,0,.556])-hh);loads={}
   for name,joint,groups in [('neck_pitch',rr,('lower','upper','head')),('neck_mid_pitch',E,('upper','head')),('head_pitch',H,('head',))]:
    gravity=sum(i['mass_kg']*9.81*(place(i)[0]-joint[0]) for i in items if i['chain'] in groups)
    payload=.05*9.81*(tip[0]-joint[0]);drag=2*abs(tip[2]-joint[2])
    uncertainty_moment=sum(i['mass_kg']*i['relative_uncertainty']*9.81*abs(place(i)[0]-joint[0]) for i in items if i['chain'] in groups)
    cap=specs[motors[name]['model']]['torque_screening_Nm']
    loads[name]=dict(gravity_nm=gravity,payload_50g_nm=payload,drag_2n_moment_bound_nm=drag,gravity_plus_payload_abs_nm=abs(gravity+payload),mass_uncertainty_torque_bound_nm=uncertainty_moment,with_uncertainty_and_drag_bound_nm=abs(gravity+payload)+uncertainty_moment+drag,manufacturer_20_percent_stall_screen_nm=cap)
   trials.append(dict(lower_delta_deg=lower_delta,upper_delta_deg=upper_delta,head_global_pitch_held=True,tip_world_m=tip.tolist(),loads=loads))
 report=dict(status='CONDITIONAL_MASS_AND_NECK_SCREEN_NOT_HARDWARE_RELEASE',scene_sha256=hashlib.sha256(a.scene.read_bytes()).hexdigest(),motor_count=len(motors),catalog_motor_mass_kg=sum(specs[m['model']]['mass_kg'] for m in motors.values()),conditional_total_mass_kg=mass,assumption_interval_kg=[mass-uncertainty,mass+uncertainty],interval_is_not_statistical=True,standing_com_m=com.tolist(),head_chain_mass_kg=sum(i['mass_kg'] for i in items if i['chain']=='head'),items=items,neck_trials=trials,limitations=['Requested masses and exact moments of inertia still require selected hardware and manufactured geometry','Head/foot/beak shell area approximation can over/underestimate cavity volume; inner ribs and seats are unresolved','Pose grid is algebraic, not joint-limit or collision validated, and excludes acceleration, shock, friction and thermal duty','Leg torque, support/contact dynamics, seated grasp and walking are not tested here','50 N opposed bite load is an internal jaw load path; only specified 50 g payload and 2 N external drag are added','Catalog screening torque is not a measured continuous thermal rating'])
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('conditional_total_mass_kg','assumption_interval_kg','standing_com_m','head_chain_mass_kg')}))
 for t in trials:print(t['lower_delta_deg'],t['upper_delta_deg'],{n:round(d['with_uncertainty_and_drag_bound_nm'],3) for n,d in t['loads'].items()})

if __name__=='__main__':main()
