#!/usr/bin/env python3
"""D whole-body mass, finite material fit and hydraulic/foot-lock screening.

Normal-only gravity/contact LP witnesses are conditional existence evidence.
No friction, dynamics, full serial hierarchy, hardware thermal or strength
acceptance is supplied by this macro diagnostic.
"""
from pathlib import Path
import argparse,hashlib,json,importlib.util
import numpy as np
import trimesh
from scipy.optimize import linprog
from sai_agent.structural_statics import resultant,normal_contacts

ROOT=Path(__file__).resolve().parents[2];ROBOT=ROOT/'robots/gorilla_v0_1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def mesh(p):return trimesh.Trimesh(p['vertices_world_m'],[[f[0],f[i],f[i+1]] for f in p['faces'] for i in range(1,len(f)-1)],process=False)
def meta(p):return p.get('D_metadata',{})
def overlap(a,b):return np.all(a.bounds[0]<b.bounds[1]) and np.all(b.bounds[0]<a.bounds[1])

def asymmetric_contact_lp(vertices,loads,models):
 vertices=np.asarray(vertices,dtype=float)
 if vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or not np.isfinite(vertices).all():raise ValueError('Invalid contact vertices')
 f,m=resultant(loads,np.zeros(3))
 if abs(vertices[:,2]).max()>1e-8 or max(abs(f[0]),abs(f[1]),abs(m[2]))>1e-7:raise ValueError('Normal-only coplanar gravity/contact scope exceeded')
 target=np.array([-f[2],m[1],-m[0]])
 eq=np.vstack([np.ones(len(vertices)),vertices[:,0],vertices[:,1]])
 A=[];b=[]
 for j in models:
  k=np.array(j['force_contact_coefficients']);c=j['force_gravity_N']
  pos,neg=j['positive_force_hypothesis_N'],j['negative_force_hypothesis_N']
  if min(pos,neg)<=0:raise ValueError('Nonpositive force hypothesis')
  A.extend([np.r_[k/pos,-1],np.r_[-k/neg,-1]]);b.extend([-c/pos,c/neg])
 A=np.array(A);b=np.array(b)
 r=linprog(np.r_[np.zeros(len(vertices)),1.],A_ub=A,b_ub=b,A_eq=np.column_stack([eq,np.zeros(3)]),b_eq=target,bounds=[(0,None)]*(len(vertices)+1),method='highs')
 out={'solver_success':bool(r.success),'message':r.message,'conditional_normal_force_and_mapped_capacity_feasible':None,'physics_accepted':False}
 if r.success:
  residual=float(abs(eq@r.x[:-1]-target).max());violation=float(max(0,(A@r.x-b).max()));bound_violation=float(max(0,-r.x.min()))
  if residual>1e-5 or violation>1e-7 or bound_violation>1e-7:raise ValueError('Primal violation')
  objective=np.r_[np.zeros(len(vertices)),1.];E=np.column_stack([eq,np.zeros(3)])
  lam=np.asarray(r.ineqlin.marginals);y=np.asarray(r.eqlin.marginals)
  reduced=objective-A.T@lam-E.T@y;dual=float(b@lam+target@y)
  dual_violation=float(max(0,lam.max(),-reduced.min()));gap=float(r.fun-dual)
  dual_valid=dual_violation<1e-7 and abs(gap)<1e-6
  feasible=True if r.x[-1]<=1+1e-7 else (False if dual_valid and dual>1+1e-7 else None)
  out.update({'minimum_peak_force_hypothesis_use':float(r.x[-1]),'normal_reactions_N':r.x[:-1].tolist(),'equilibrium_residual_N_or_Nm':residual,'maximum_normalized_inequality_violation':violation,'maximum_nonnegative_variable_bound_violation':bound_violation,'conditional_normal_force_and_mapped_capacity_feasible':feasible,'numerical_dual_certificate':{'inequality_multipliers':lam.tolist(),'equality_multipliers':y.tolist(),'nonnegative_variable_reduced_costs':reduced.tolist(),'lower_bound_on_peak_use':dual,'maximum_dual_feasibility_violation':dual_violation,'primal_dual_gap':gap,'valid_with_declared_float_tolerances':dual_valid,'scope':'Floating-point certificate for the stated restricted LP, not rigorous interval proof or physical qualification'},'force_models':[{**j,'force_N_at_witness':float(j['force_gravity_N']+np.array(j['force_contact_coefficients'])@r.x[:-1])} for j in models]})
 return out

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--scene',type=Path,default=ROBOT/'cad/source/internal_structure_d_scene.json');ap.add_argument('--output',type=Path,default=ROBOT/'evidence/internal_structure_d_screen.json');ap.add_argument('--no-space',action='store_true');args=ap.parse_args()
 scene=json.loads(args.scene.read_text());specpath=ROOT/scene['spec_path'];assert sha(specpath)==scene['spec_sha256'];spec=json.loads(specpath.read_text())
 for p,v in scene['input_hashes'].items():assert sha(ROOT/p)==v,p
 definition=importlib.util.spec_from_file_location('pose_math',ROOT/'scripts/evaluation/evaluate_gorilla_internal_structure.py');h=importlib.util.module_from_spec(definition);definition.loader.exec_module(h)
 points=json.loads((ROOT/spec['geometry_spec']).read_text())['points_world_m'];leg=json.loads((ROOT/spec['leg_scene']).read_text());foot=json.loads((ROOT/spec['foot_scene']).read_text())
 parts={p['name']:p for p in scene['parts']};meshes={k:mesh(v) for k,v in parts.items()};modules={r['id']:r for r in scene['system_module_rows']};rows=[];unknown=[];density_groups={};counted_aliases=[]
 # Frame/shaft rows in the leg have already been unioned by rigid structural
 # material group by its builder. Independent bearings, pins and articulated
 # actuator constituents stay separate. Foot parent/trays are likewise unioned.
 for name,p in parts.items():
  role=p['role'];m=meshes[name];md=meta(p);scope=None;mass=None
  if name in modules and modules[name].get('mass_counted_elsewhere'):
   owner=modules[name]['mass_counted_elsewhere'];assert owner in modules
   counted_aliases.append({'id':name,'mass_owner':owner});continue
  lm=p.get('D_leg_metadata',{})
  rigid_material=role=='D_finite_primary_material' or role in ('fixed_load_arch','moving_load_tray') or (role=='primary_structure_candidate' and not lm.get('excluded_from_rigid_material_union') and lm.get('component')!='bearing_pack_reserve')
  if rigid_material:
   density_groups.setdefault('isd_net_rigid_'+p['body'],[]).append(name);continue
  if role=='finite_actuator_material_design_probe':
   density_groups.setdefault('isd_net_actuator_'+p['actuator_side']+'_'+p['actuator_family']+'_'+p['motion_group'],[]).append(name);continue
  if name in modules:mass=modules[name]['mass_range_kg'];scope='D distributed module: '+modules[name].get('mass_basis','source/own allowance; homogeneous inertia proxy')
  elif role in ('armor_cover','armor_surface'):mass=[m.volume*r for r in spec['armor_density_range_kg_m3_hypothesis']];scope='Unchanged C15 armor/density hypotheses'
  elif role in ('ground_pad','contact_surface_candidate'):mass=[m.volume*r for r in spec['pad_density_range_kg_m3_hypothesis']];scope='Unchanged C15 independent pad/upper-edge density hypotheses'
  elif p.get('mass_range_kg') or md.get('mass_range_kg'):mass=p.get('mass_range_kg',md.get('mass_range_kg'));scope='Bearing/installation reference range; actual rating unknown'
  elif p.get('assumed_density_kg_m3') or md.get('density_kg_m3'):mass=[m.volume*p.get('assumed_density_kg_m3',md.get('density_kg_m3'))]*3;scope='Actual finite material volume times conditional density'
  elif role in ('visible_mechanism','control_display_ui','control_display_glass','display_module_envelope'):continue
  else:unknown.append(name);continue
  if len(mass)==2:
   mass=[mass[0],sum(mass)/2,mass[1]];scope+='; diagnostic nominal is midpoint of source low/high bounds'
  if not (m.is_watertight and m.is_winding_consistent and m.volume>0):raise ValueError('Invalid physical mass geometry '+name)
  if not (len(mass)==3 and 0<mass[0]<=mass[1]<=mass[2]):raise ValueError('Invalid mass range '+name)
  rows.append({'id':name,'body':h.canonical(p['body']),'mass_range_kg':list(mass),'COM_world_m':m.center_mass.tolist(),'scope':scope,'inertia_proxy_at_COM_kg_m2':(m.moment_inertia*mass[1]/m.volume).tolist(),'actual_mass_distribution_or_SI_accepted':False})
 if unknown:raise ValueError('Unaccounted D physical parts: '+str(unknown))
 for name,members in density_groups.items():
  m=trimesh.boolean.union([meshes[n] for n in members],engine='manifold') if len(members)>1 else meshes[members[0]].copy();meshes[name]=m
  assert m.is_watertight and m.is_winding_consistent and m.volume>0
  mass=m.volume*spec['material']['density_kg_m3'];body=h.canonical(parts[members[0]]['body']);assert all(h.canonical(parts[n]['body'])==body for n in members)
  islands=[c for c in m.split(only_watertight=False) if c.volume>1e-10]
  rows.append({'id':name,'body':body,'mass_range_kg':[mass]*3,'COM_world_m':m.center_mass.tolist(),'scope':'Net finite same rigid material OR one floating actuator motion assembly; geometric union is not connection/rigidity qualification.','member_ids':members,'positive_volume_material_components':len(islands),'inertia_proxy_at_COM_kg_m2':(m.moment_inertia*spec['material']['density_kg_m3']).tolist(),'actual_mass_distribution_or_SI_accepted':False})
 totals=[sum(r['mass_range_kg'][i] for r in rows) for i in range(3)];poses=[];spaces=[]
 foot_paths=next(x for x in foot['pose_scenes'] if x['id']=='neutral_locked')['joint_paths_left']
 for pname,angles in spec['candidate_pose_angles_deg'].items():
  parents,T=h.transforms(points,angles)
  legpose=next(x for x in leg['pose_scenes'] if x['id']==pname);legmesh={p['name']:mesh(p) for p in legpose['parts']}
  # The frozen leg pose source has already applied the root pad-Z alignment.
  T={b:np.array(t) for b,t in legpose['body_transforms'].items()}
  posemesh={}
  for n,p in parts.items():
   if n in legmesh:posemesh[n]=legmesh[n]
   else:
    m=meshes[n].copy();m.apply_transform(T[h.canonical(p['body'])]);posemesh[n]=m
  for n,members in density_groups.items():posemesh[n]=trimesh.boolean.union([posemesh[q] for q in members],engine='manifold') if len(members)>1 else posemesh[members[0]].copy()
  contact=[];cb=[]
  for n,p in parts.items():
   if p['role'] in ('ground_pad','contact_surface_candidate'):
    v=posemesh[n].vertices
    if abs(v[:,2].min())>1e-7:continue
    vv=v[abs(v[:,2])<1e-8]
    for q in vv:contact.append(q);cb.append(p['body'])
  unique=sorted(set((b,*np.round(v,12)) for b,v in zip(cb,contact)));cb=[x[0] for x in unique];V=np.array([x[1:] for x in unique]);assert abs(V[:,2]).max()<1e-7
  cases=[]
  for mass_index,mass_label in enumerate(('all_lower_bounds','diagnostic_nominal','all_upper_bounds')):
   for payload,pressure,factor in ((0,0,1.),(100,0,1.),(100,0,1.5),(0,3000,1.)):
    loads=[{'id':r['id'],'body':r['body'],'position_world_m':posemesh[r['id']].center_mass.tolist(),'force_world_N':[0,0,-r['mass_range_kg'][mass_index]*spec['gravity_m_s2']*factor]} for r in rows]
    if payload:
     for side in ('left','right'):loads.append({'body':side+'_palm','position_world_m':h.transformed(T[side+'_palm'],points[side+'_palm']).tolist(),'force_world_N':[0,0,-payload*.5*spec['gravity_m_s2']*factor]})
    if pressure:loads.append({'body':'torso','position_world_m':h.transformed(T['torso'],[0,0,2.45]).tolist(),'force_world_N':[0,0,-pressure*spec['gravity_m_s2']]})
    models=[]
    for j in scene['joint_supports']:
     distal=h.descendants(parents,j['output_body']);J=h.transformed(T[j['parent_body']],j['center_world_m']);axis=T[j['parent_body']][:3,:3]@j['axis_world'];f,m=resultant([r for r in loads if r['body'] in distal],J)
     coef=np.cross(V-J,[0,0,1])@axis*np.array([b in distal for b in cb]);tau=float(m@axis)
     link=next(x for x in spec['actuator_definitions'] if x['id']==j['id']);a=h.transformed(T[j['parent_body']],link['A_neutral_world_m']);b=h.transformed(T[j['output_body']],link['B_neutral_world_m']);arm=float((b-a)/np.linalg.norm(b-a)@np.cross(axis,b-J))
     Ac=np.pi*(link['bore_m']/2)**2;Aa=Ac-np.pi*(link['rod_m']/2)**2;p=spec['hydraulic_cylinder_supply_pressure_Pa_hypothesis'];pr=spec['hydraulic_return_pressure_Pa_hypothesis']
     if abs(arm)<1e-6:raise ValueError('Actuator near dead point '+j['id'])
     models.append({'id':j['id'],'kind':'hydraulic_pitch','effective_arm_m':arm,'force_gravity_N':-tau/arm,'force_contact_coefficients':(-coef/arm).tolist(),'positive_force_hypothesis_N':p*Ac-pr*Aa,'negative_force_hypothesis_N':p*Aa-pr*Ac,'pressure_is_not_qualified_capacity':True})
    for side,sign in [('left',1),('right',-1)]:
     for j in foot_paths:
      body=j['child'].replace('left_',side+'_');J0=np.array(j['pivot_world_m']);J0[1]*=sign;J=h.transformed(T[side+'_foot'],J0);axis=T[side+'_foot'][:3,:3]@np.array([0,1,0]);f,m=resultant([r for r in loads if r['body']==body],J);coef=np.cross(V-J,[0,0,1])@axis*np.array([b==body for b in cb]);tau=float(m@axis);arm=j['brace_load_paths'][0]['moment_arm_about_hinge_m'];cap=j['brace_load_paths'][0]['ideal_two_pin_double_shear_force_at_yield_FS2_N']
      models.append({'id':j['id'].replace('left_',side+'_'),'kind':'two_foot_compression_braces','effective_arm_m':arm,'force_gravity_N':-tau/(2*arm),'force_contact_coefficients':(-coef/(2*arm)).tolist(),'positive_force_hypothesis_N':cap,'negative_force_hypothesis_N':cap,'capacity_scope':'Gross two16mm-pin double-shear S355 yield/FS2 only; bearing/ligament/tube buckling/collateral load paths unknown. Equal sagittal sharing, not 3D brace-load existence proof.'})
    cases.append({'mass_profile':mass_label,'payload_kg_hypothesis':payload,'separate_pressure_demand_kg':pressure,'gravity_factor_sensitivity':factor,'normal_contact':normal_contacts(V,loads),'unchanged_single_left_normal_contact':normal_contacts(V[[b.startswith('left_') for b in cb]],loads),'mapped_hydraulic_and_foot_pin_LP':asymmetric_contact_lp(V,loads,models),'physical_acceptance':False})
  poses.append({'id':pname,'body_transforms':{k:v.tolist() for k,v in T.items()},'actual_pad_contact_vertices_world_m':V.tolist(),'cases':cases})
  if not args.no_space:
   hits=[];unresolved=[];new=[n for n,p in parts.items() if p['role'] not in ('visible_mechanism','armor_cover','armor_surface','ground_pad','contact_surface_candidate','control_display_ui','control_display_glass','display_module_envelope')];armor=[n for n,p in parts.items() if p['role'] in ('armor_cover','armor_surface')]
   for n in new:
    for o in armor:
     a,b=posemesh[n],posemesh[o]
     if not overlap(a,b):continue
     try:
      v=trimesh.boolean.intersection([a,b],engine='manifold')
      if v.volume>1e-9:hits.append({'physical_part':n,'armor_part':o,'positive_material_intersection_m3':float(v.volume),'bounds_world_m':v.bounds.tolist()})
     except Exception as e:unresolved.append({'pair':[n,o],'error':str(e)})
   spaces.append({'pose':pname,'physical_to_armor_positive_material_hits':hits,'unresolved':unresolved,'screen_scope':'Finite real material/module-envelope to original armor only. Whole new/new articulated mechanisms and paths assessed separately; not collision acceptance.'})
 output={'robot_id':'gorilla_v0_1','candidate':'internal_structure_d','scene_sha256':sha(args.scene),'evaluator_sha256':sha(__file__),'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [args.scene,specpath,ROOT/spec['leg_scene'],ROOT/spec['foot_scene'],ROOT/'scripts/evaluation/evaluate_gorilla_internal_structure.py']},'whole_mass_range_kg':totals,'mass_rows':rows,'mass_aliases_counted_once':counted_aliases,'mass_ledger_no_inherited_A989kg':True,'poses':poses,'armor_space_checks':spaces,'mass_scope':'Complete listed net finite materials and explicit allowances, not complete manufactured mass. OEM/aux internal distributions unresolved; adjacent/independent mechanisms that still interfere are not treated as one material group. All tensors are proxies.','LP_scope':'Four symmetric sagittal configurations, finite upward normal vertices, eight hydraulic axes and four equal-sharing foot brace pin hypotheses. No friction, dynamic/thermal/held-load proof, full serial carrier hierarchy, lateral/yaw actuation or full3D brace reactions. Three coherent all-low/nominal/all-high inventory profiles checked; independent interval worst-case allocations and OEM internal COM variations remain unknown.','geometry_accepted':False,'physics_accepted':False,'stable_physical_contract':False}
 write(args.output,output);print(json.dumps({'candidate':'internal_structure_d','mass_kg':totals,'poses':len(poses),'armor_hit_counts':[len(x['physical_to_armor_positive_material_hits']) for x in spaces],'physical_acceptance':False}))

if __name__=='__main__':main()
