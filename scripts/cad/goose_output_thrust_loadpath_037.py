"""Single source-bound radial thrust path candidate; no public model mutation."""
import pathlib,json,hashlib,math,importlib.util
import build123d as b
W=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('parent',W/'scripts/cad/goose_output_thrust_upgrade_033.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
O=W/'robots/goose_v0_2/cad/exports/output_thrust_loadpath_037/c01';E=W/'experiments/goose_v0_2/output_thrust_loadpath_037/c01'
O.mkdir(parents=True,exist_ok=True);E.mkdir(parents=True,exist_ok=True)
plan=json.load(open(W/'experiments/goose_v0_2/output_thrust_upgrade_033/c01/merge_plan_11_identity_r02.json'));old={x['name']:x for x in plan['new_parts']}
read=lambda n:b.import_step(str(W/old[n]['source']['path']))
frame=read('thrust033_head_frame_needle_seats_7075')
front=p.ann(7,11.18,27.1,.65)
rear=p.ann(7,9.8,-35.25,1.25).fuse(p.ann(9.7,12.25,-34.2,.2),p.ann(12.02,12.25,-34,.50))
sols=list(read('thrust033_rear_jam_nuts_m6').solids());far=min(sols,key=lambda s:s.center(b.CenterOf.MASS).Y).translate((0,-.05,0))
near=max(sols,key=lambda s:s.center(b.CenterOf.MASS).Y).translate((0,-.05,0));near=near.cut(p.cy(3.05,-38.4,3.2));near=near.fuse(p.ann(3.05,8.5,-35.8,.5))
shapes=[('front_centered_thrust_washer',front,7800,'certified_steel_sy200_e200_required','thrust033_front_thrust_washer'),('rear_piloted_thrust_washer',rear,7800,'certified_steel_sy200_e200_required','thrust033_rear_thrust_washer'),('rear_integral_flanged_m6_nut_h900',near,7800,'wrought_17_4ph_h900_sy1170_required',None),('rear_original_lock_nut_m6_shifted',far,7800,'original_steel_procurement_pending',None)]
rows=[]
for n,s,rho,mat,ret in shapes:
 f=O/(n+'.step');b.export_step(s,str(f));rows.append(dict(name=n,body='beak_hinge',frame='oldnative_mm',source=p.ident(f),material=mat,**p.props(s,rho),replaces=ret))
retired=[old['thrust033_'+x]for x in ['front_thrust_washer','rear_thrust_washer','rear_jam_nuts_m6']]
delta=sum(x['mass_kg']for x in rows)-sum(x['mci']['mass_kg']for x in retired)
# Native positive-contact material checks; actual rings, not a bounding box.
proof=[]
for name,tool,s in [('front_flat_load_ring',p.ann(7.05,7.65,27.75,.02),None),('front_fixed_backing_ring',p.ann(9.55,11.10,27.08,.02),frame),('rear_fixed_backing_ring',p.ann(9.55,9.75,-34,.02),frame)]:
 if s is not None:proof.append(dict(name=name,volume_mm3=tool.volume,common_mm3=p.common(s,tool)))
fork=b.import_step(str(W/'robots/goose_v0_2/cad/exports/variable_gain_drive_029/fork_c02_headed_pin/output_onepiece_keyed_fork.step'))
tool=p.ann(7.05,7.65,27.75,.02);proof.append(dict(name='actual_fork_rear_flat_load_ring',volume_mm3=tool.volume,common_mm3=p.common(fork,tool)))
ctx=[(x['name'],x['body'],b.import_step(str(W/x['source']['path'])))for x in plan['new_parts']if x['name']not in {v['name']for v in retired}]
def linkage(q):
 C=(160+29.87*math.cos(2.4531-q),576+29.87*math.sin(2.4531-q));dx,dz=C[0]-129,C[1]-601;rr=math.hypot(dx,dz);th=math.atan2(dz,dx)-math.acos((7.73**2+rr**2-15**2)/(2*7.73*rr));D=(129+7.73*math.cos(th),601+7.73*math.sin(th));return th,D,math.atan2(C[1]-D[1],C[0]-D[0])
t0,D0,a0=linkage(0)
def pose(s,body,q):
 t,D,a=linkage(q)
 if body=='beak_hinge':return s.rotate(b.Axis((160,0,576),(0,1,0)),math.degrees(q))
 if body=='beak_input_rotor':return s.rotate(b.Axis((129,0,601),(0,1,0)),-math.degrees(t-t0))
 if body=='beak_coupler_link':return s.rotate(b.Axis((D0[0],0,D0[1]),(0,1,0)),-math.degrees(a-a0)).translate((D[0]-D0[0],0,D[1]-D0[1]))
 return s
def bb(a,z):
 aa=a.bounding_box();zz=z.bounding_box();return all(min(list(aa.max)[i],list(zz.max)[i])-max(list(aa.min)[i],list(zz.min)[i])>1e-7 for i in range(3))
checks=[]
for q in [0,.14,.16,.3,.55]:
 for n,s,*_ in shapes:
  ss=pose(s,'beak_hinge',q)
  for cn,cb,cs in ctx:
   cc=pose(cs,cb,q)
   if not bb(ss,cc):continue
   v=p.common(ss,cc)
   if v>1e-6:checks.append(dict(q=q,part=n,other=cn,common_mm3=v,thread_envelope=('nut' in n and 'shaft' in cn.lower())))
 print('q_done',q,flush=True)
(E/'five_pose_fit.json').write_text(json.dumps(checks,indent=2))
# Same factor6 and unchanged minimum material; worst allowed .05 radial eccentricity.
a=6.95
cap=lambda sy,t,L:sy*2*math.pi*a*t*t/(36*L)
limits=dict(front_washer_N=cap(200,.65,9.5-a),rear_washer_N=cap(200,1.25,9.5-a),front_frame_lip_N=cap(420.58,.5,9.5-a),rear_frame_lip_N=cap(420.58,.5,9.5-a),flange_N=1170*2*math.pi*5*.5**2/(36*(8.5-5)))
d=dict(candidate_id='output_thrust_loadpath_037_c01',status='AUTHOR_CANDIDATE_REQUIRES_F_ROOT_REVIEW',source=p.ident(pathlib.Path(__file__)),parent_plan=p.ident(W/'experiments/goose_v0_2/output_thrust_upgrade_033/c01/merge_plan_11_identity_r02.json'),parts=rows,retired=retired,delta_mass_kg=delta,proof=proof,positive_common=checks,conditional_capacity_N=limits,target_bidirectional_O_N=40,centering=dict(front_pocket_radius=11.2,front_washer_radius=11.18,rear_frame_radius=12,rear_pilot_inner_radius=12.02,nominal_max_radial_offset=.05,worst_load_radius=6.95),assembly=dict(front_y=[27.1,27.75],rear_y=[-35.25,-34],rear_pilot_y=[-34,-33.5],near_nut_y=[-38.3,-35.3],far_nut_y=[-41.3,-38.3],shaft_end=-42,rear_endplay=.05,thread_end_margin=.7,near_thread='M6x1; 3mm nominal axial engagement, >=2mm full threads after edge breaks required; engineering bore envelope 6.10mm, not rendered helical teeth',jam_lock='Set .05mm rear running clearance with gauge; lock two nuts against each other, never preload fixed frame/needle'),unchanged=['frame and both needle positions','shaft/journals/DD','fork/drive/motor/caps','full bill and TPU/general workface','all frozen11 inputs'],limitations=['Conditional radial-strip screen, not full contact/plate FEA or fatigue certification','Centering nominal .05mm radial gap requires measured machining tolerances/runout; no arbitrary free washer eccentricity','H900 flanged nut certified material required, not already procured','S355 steel washers minimum Sy200 E200 procurement condition; no increased allowable','Thread preload/jam locking and surface flatness/runout require manufacture test','No physics and no self-admission'])
(E/'module_handoff.json').write_text(json.dumps(d,indent=2));print(json.dumps(dict(delta_kg=delta,capacities=limits,checks=checks),indent=2),flush=True)
