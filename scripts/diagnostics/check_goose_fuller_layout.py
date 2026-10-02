"""Screen fuller Goose geometry: declared service boxes and contact-outline changes.

No claim about electronics completeness, printability, balance or dynamic motion.
"""
from pathlib import Path
import argparse,sys,json,itertools,hashlib
import numpy as np
from scipy.spatial import ConvexHull
from scipy.integrate import trapezoid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cad'))
import build_goose_fuller_exterior as current
import build_goose_hinged_exterior as previous

p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('--previous',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
d=json.loads(a.scene.read_text());old=json.loads(a.previous.read_text())
parts={p['name']:p for p in d['parts']}
def v(part):return np.asarray(part['vertices'])*1000
boxes=[]
for part in d['parts']:
 if part.get('role')=='provisional_electronics_service_envelope' or part['name'].endswith('_case') and not part['name'].endswith('_front_case'):
  vv=v(part)
  if part.get('role')=='provisional_electronics_service_envelope':
   lo,hi=vv.min(0),vv.max(0);c=(lo+hi)/2;rot=np.eye(3);h=(hi-lo)/2
  else:
   basis=json.loads((a.scene.parent/'hardware_basis.json').read_text())
   m=next(m for m in basis['actuators'] if m['joint']+'_case'==part['name'])
   yy=np.array(m['axis_world'],float);yy/=np.linalg.norm(yy);zz=np.array(m['up_world'],float);rot=np.column_stack((np.cross(yy,zz),yy,zz));w,hh,dep=m['case_whd_mm'];top=13.75 if '540' in m['model'] else 11.25 if '430' in m['model'] else 9.5;c=np.array(m['shaft_world_mm'])+zz*(top-hh/2);h=np.array([w,dep,hh])/2
  boxes.append((part['name'],c,rot,h,part.get('role')))
issues=[]
for (na,ca,ra,ha,rolea),(nb,cb,rb,hb,roleb) in itertools.combinations(boxes,2):
 if 'provisional_electronics_service_envelope' not in (rolea,roleb):continue
 overlap=[]
 for ax in [*ra.T,*rb.T,*[np.cross(x,y) for x in ra.T for y in rb.T]]:
  if np.linalg.norm(ax)<1e-8:continue
  ax=ax/np.linalg.norm(ax);overlap.append(float(np.sum(ha*np.abs(ra.T@ax))+np.sum(hb*np.abs(rb.T@ax))-abs((cb-ca)@ax)))
 if min(overlap)>.05:issues.append(dict(a=na,b=nb,min_overlap_mm=min(overlap)))
fits=[]
for name,c,r,h,role in boxes:
 if role!='provisional_electronics_service_envelope':continue
 pts=np.array(list(itertools.product(*[np.linspace(c[i]-h[i],c[i]+h[i],7) for i in range(3)])))
 cz,ry,rz=current.PROFILE(pts[:,0]).T
 # Conservative algebraic ellipse inset; not exact signed distance to curved shell.
 level=(pts[:,1]/(ry-4))**2+((pts[:,2]-cz)/(rz-4))**2
 fits.append(dict(name=name,bounds_mm=[(c-h).tolist(),(c+h).tolist()],inside_inset_profile_sampled=bool(np.all(level<1)),max_inset_level=float(level.max()),basis=parts[name]['envelope_basis']))
def contact(payload):
 vv=v(next(p for p in payload['parts'] if p['name']=='right_foot_sole'))
 pts=vv[np.isclose(vv[:,2],vv[:,2].min()),:2];h=ConvexHull(pts);return pts,h
oldp,oh=contact(old);newp,nh=contact(d)
# halfspaces of new hull applied to every old contact point
outside=oldp@nh.equations[:,:2].T+nh.equations[:,2]
body=[]
for module in (previous,current):
 xx=np.linspace(module.BODY[0,0],module.BODY[-1,0],2001);cz,ry,rz=module.PROFILE(xx).T
 body.append(dict(gross_outer_volume_l=float(trapezoid(np.pi*ry*rz,xx)/1e6),profile_dimensions_mm=[float(np.ptp(xx)),float(2*ry.max()),float((cz+rz).max()-(cz-rz).min())]))
report=dict(scope='Static nominal service-envelope, body profile and ideal sole contact hull only. Not physical/manufacturing acceptance.',scene_sha256=hashlib.sha256(a.scene.read_bytes()).hexdigest(),previous_scene_sha256=hashlib.sha256(a.previous.read_bytes()).hexdigest(),electronics_boxes=fits,box_overlaps=issues,all_declared_service_boxes_fit=not issues and all(f['inside_inset_profile_sampled'] for f in fits),body_before_after=body,gross_outer_volume_gain_percent=100*(body[1]['gross_outer_volume_l']/body[0]['gross_outer_volume_l']-1),contact_hull=dict(old_area_mm2=float(oh.volume),new_area_mm2=float(nh.volume),old_points_inside_new_hull=bool(outside.max()<1e-6),max_old_point_outside_new_hull_mm=float(outside.max()),old_x_limits_mm=[float(oldp[:,0].min()),float(oldp[:,0].max())],new_x_limits_mm=[float(newp[:,0].min()),float(newp[:,0].max())],note='Original heel retained; forefoot extended while including the old contact hull. Full flat sole assumed. Increased hull does not prove balance or friction.'),unresolved=['Exact BOM and enclosure of all additional electronics, IMU and speaker','Connector sweeps, cooling, service/removal paths and fasteners','Hip/neck full motion sweep against larger shell','Mass, inertia, seated reach, balance, ground friction and gait'])
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
