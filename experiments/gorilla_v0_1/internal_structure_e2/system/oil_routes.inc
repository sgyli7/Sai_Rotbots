# Complete native oil network. Functional ports in retained OEM envelopes are NOT OEM CAD.
def onode(id,c,owner='torso',kind='oil_port'):oilnodes[id]={'id':id,'center_world_m':list(c),'frame_owner':owner,'kind':kind};return id
def oroute(id,start,end,points=[],ri=.006,ro=.009,flow=0,role='oil_hose'):
 ns=[oilnodes[start],*points,oilnodes[end]];ins=[];outs=[];length=0
 for a,b in zip(ns,ns[1:]):
  aa=np.array(a['center_world_m']);bb=np.array(b['center_world_m']);length+=float(np.linalg.norm(bb-aa));ins.append(cylinder(aa,bb,ri));outs.append(cylinder(aa,bb,ro));mid=(aa+bb)/2
  oilwet(id+'_fluid_half_a_'+str(len(ins)),a['frame_owner'],cylinder(aa,mid,ri));oilwet(id+'_fluid_half_b_'+str(len(ins)),b['frame_owner'],cylinder(mid,bb,ri))
 for i,p0 in enumerate(ns[1:-1]):ins.append(sphere(p0['center_world_m'],ri*1.20));outs.append(sphere(p0['center_world_m'],ro*1.35));oilwet(id+'_elbow_fluid_'+str(i),p0['frame_owner'],sphere(p0['center_world_m'],ri*1.20))
 inside=union(ins);mat=diff(union(outs),[inside]);frames=sorted(set(p['frame_owner'] for p in ns));emit(id,ns[-1]['frame_owner'],'oil_line_native_material',mat,density=1350,own='Own reinforced hose wall+finite elbows; mass density sensitivity only, pressure rating/strain-relief/bend radius/sweep not qualified',route_function=role,endpoint_frames=frames,not_one_rigid_body=len(frames)>1,neutral_flow_L_min_hypothesis=flow)
 oilroutes.append({'id':id,'start':start,'end':end,'nodes':ns,'neutral_length_m':length,'inner_radius_m':ri,'outer_radius_m':ro,'frames':frames,'cross_frame':len(frames)>1,'role':role,'arc_length_bend_radius_sweep_accepted':False});oiledges.append([start,end])
# Tank ports, two complete pump blocks, separate shared pressure/return branches.
ts=onode('e2_tank_suction',[.055,0,1.855]);tr=onode('e2_tank_return',[.015,0,2.14]);tp=onode('e2_pressure_header',[.20,0,2.245]);rt=onode('e2_return_header',[.165,0,1.82]);un=onode('e2_unload_bypass',[.28,0,2.19]);hf=onode('e2_return_filter_in',[.25,.24,2.44]);hfo=onode('e2_return_filter_out',[.25,.24,2.30]);ohin=onode(osp,nodes[osp]['center_world_m']);ohout=onode(orp,nodes[orp]['center_world_m'])
# Real finite multiport headers: eighteen dedicated branch bores, not eighteen hoses at one point.
oil_header_ports={'P':[],'T':[]};oil_header_ends={}
for mode,cc,ri in [('P',np.array([.20,0,2.245]),.009),('T',np.array([.165,0,1.82]),.012)]:
 d=np.array([.064,.384,.084]);cavity=[cylinder(cc+[0,-.210,0],cc+[0,.210,0],ri)];outer=box(cc,d)
 for sg in [-1,1]:
  en=onode('e2_'+mode+'_header_end_'+str(sg),cc+[0,sg*.210,0]);oil_header_ends[(mode,sg)]=en;oiledges.append([en,tp] if mode=='P' else [rt,en]);emit(en+'_fitting','torso','oil_manifold_fitting_material',tube(cc+[0,sg*.1921,0],cc+[0,sg*.210,0],ri+.004,ri),density=7850,own='Native end boss with continuous main fluid bore; pipe flare/seals/service unknown')
 if mode=='P':
  paux=onode('e2_P_header_unload_port',cc+[-.045,0,0]);cavity.append(cylinder(cc,oilnodes[paux]['center_world_m'],.008));oiledges.append([tp,paux]);emit(paux+'_fitting','torso','oil_manifold_fitting_material',tube(cc+[-.0321,0,0],oilnodes[paux]['center_world_m'],.012,.008),density=7850,own='Dedicated full unloading branch bore and fitting')
 for i in range(18):
  y=(i%9-4)*.036;dz=(-1 if i<9 else 1)*.022;port=onode('e2_'+mode+'_header_tap_'+str(i),cc+[.045,y,dz]);oil_header_ports[mode].append(port)
  cavity += [cylinder(cc+[0,y,0],cc+[0,y,dz],.0045 if mode=='P' else .006),cylinder(cc+[0,y,dz],cc+[.045,y,dz],.0045 if mode=='P' else .006)]
  emit(port+'_boss','torso','oil_manifold_fitting_material',tube(cc+[.0321,y,dz],cc+[.045,y,dz],.008 if mode=='P' else .009,.0045 if mode=='P' else .006),density=7850,own='Finite own18 distinct port bosses; thread/seal/extraction/metering pressure qualification unknown')
  oiledges.append([tp if mode=='P' else rt,port] if mode=='P' else [port,rt])
 inner=union(cavity);emit('e2_oil_'+mode+'_18port_header','torso','oil_manifold_native_material',diff(outer,[inner]),density=7850,own='Own steel finite header,24/18mm longitudinal bore+18 individually separated branch bores in2levels; positive material, no pressure fatigue/manufacture/port proof');oilwet('e2_oil_'+mode+'_header_cavity','torso',inner)
for side,sg in [('left',1),('right',-1)]:
 pi=onode('e2_'+side+'_pump_suction',[.085,sg*.145,2.255]);po=onode('e2_'+side+'_pump_pressure',[.085,sg*.145,2.365]);pd=onode('e2_'+side+'_pump_case_drain',[.02,sg*.145,2.35]);oroute('e2_'+side+'_suction',ts,pi,[point([.055,sg*.145,1.87],'torso'),point([.055,sg*.145,2.20],'torso')],ri=.014,ro=.019,role='low_pressure_suction',flow=19.161)
 oroute('e2_'+side+'_pump_pressure',po,oil_header_ends[('P',sg)],[point([.16,sg*.145,2.365],'torso')],ri=.008,ro=.012,flow=19.161,role='shared_pressure');oroute('e2_'+side+'_case_drain',pd,tr,[point([.015,sg*.145,2.17],'torso')],ri=.004,ro=.006,role='case_drain_not_measured')
 oiledges.append([pi,po])
emit('e2_shared_unload_relief_accumulator_reserve','torso','hydraulic_safety_complete_reserve',box([.29,0,2.17],[.09,.10,.15]),[1.5,3.0,6.0],own='Complete nonzero unloading/shock relief/check/pulsation reserve, not selected valve; control fail-state and accumulator sizing unknown')
oroute('e2_pressure_to_unload',paux,un,[point([.25,0,2.24],'torso')],ri=.008,ro=.012,role='idle_or_excess_flow_bypass');oroute('e2_unload_to_return',un,oil_header_ends[('T',1)],[point([.29,0,1.92],'torso')],ri=.014,ro=.019,role='idle_low_pressure_unload_not_full_pressure_burn')
oroute('e2_return_to_real_oil_HX',oil_header_ends[('T',-1)],ohin,[point([.12,0,1.80],'torso'),point([-.286,0,1.80],'torso')],ri=.014,ro=.019,role='oil_heat_rejection_return');oroute('e2_oil_HX_to_filter',ohout,hf,[point([-.114,.24,1.68],'torso'),point([.25,.24,1.68],'torso')],ri=.014,ro=.019,role='cooled_return');oroute('e2_filter_to_tank',hfo,tr,[point([.25,.10,2.20],'torso')],ri=.014,ro=.019,role='filtered_tank_return');oiledges += [[ohin,ohout],[hf,hfo]]
# Preserve source bank8. Add ten independent EA slices, not unproved balanced parallel pairs.
Dspec=json.loads((ROOT/'robots/gorilla_v0_1/configs/internal_structure_d_spec.json').read_text());macro=json.loads((ROOT/'.scratch/gorilla_internal_e_macro/comparison.json').read_text());cylinders=[]
for a in Dspec['actuator_definitions']:
 id=a['id'];side,fam=id.split('_');parent={'hip':'pelvis','knee':side+'_thigh','fold':side+'_middle_shank','ankle':side+'_distal_shank'}[fam];child={'hip':side+'_thigh','knee':side+'_middle_shank','fold':side+'_distal_shank','ankle':side+'_foot'}[fam]
 cylinders.append({'id':id,'A':a['A_neutral_world_m'],'B':a['B_neutral_world_m'],'bore':a['bore_m'],'rod':a['rod_m'],'stroke':a['stroke_design_m'],'zero':a['zero_eye_design_m'],'parent':parent,'child':child,'valve_center':[.26,(1 if side=='left' else -1)*(.159+['hip','knee','fold','ankle'].index(fam)*.052),1.83],'source':'frozenD own finite cylinder, not OEM ports'})
newindex=0
for fam in macro['B_route']['finite_pairs']:
 if fam['family'] not in ['waist_pitch','hip_roll','foot_roll']:continue
 sides=['center'] if fam['family']=='waist_pitch' else ['left','right']
 for side in sides:
  sg=1 if side!='right' else -1
  for d in fam['pair_cylinders']:
   A=np.array(d['neutral_A_world_m']);B=np.array(d['neutral_B_world_m']);A[1]*=sg;B[1]*=sg
   parent='pelvis' if fam['family'] in ['waist_pitch','hip_roll'] else side+'_distal_shank';child='torso' if fam['family']=='waist_pitch' else side+('_thigh' if fam['family']=='hip_roll' else '_foot');id='e2_'+side+'_'+fam['family']+'_pair'+str(d['index']);sgbank=1 if newindex<5 else -1;y=sgbank*(.055+(newindex%5)*.052);vc=[.30,y,1.475];vbase=id+'_valve'
   emit(vbase+'_body','torso','added_hydraulic_EA_valve',box(vc,[.080,.0495,.096]),[2.8]*3,own='HAWE PSL3 size3 slice body dimension benchmark, own configured bank/interface pending',exact_source=data['sources']['psl3']['exact_source']);emit(vbase+'_EAcoil','torso','added_hydraulic_EA_valve',box([.30,y,1.5475],[.0692,.049,.049]),[.6]*3,own='Source section allocation2.8+.6+.3=3.7kg; not volume-derived OEM mass',exact_source=data['sources']['psl3']['exact_source']);emit(vbase+'_full_lever','torso','added_hydraulic_EA_valve',cylinder([.30,y,1.561],[.30,y,1.7918],.0065),[.3]*3,own='Full268.8mm EA height retained from bodytop1.523; no shortening',exact_source=data['sources']['psl3']['exact_source'])
   cylinders.append({'id':id,'A':A.tolist(),'B':B.tolist(),'bore':fam['bore_rod_wall_m'][0],'rod':fam['bore_rod_wall_m'][1],'stroke':d['design_stroke_m'],'zero':d['allocated_custom_zero_eye_m'],'parent':parent,'child':child,'valve_center':vc,'source':'macro pair only; must relocate to matching E2 native carrier/cylinder source','new_pair':True});newindex+=1
for sg in [-1,1]:
 emit('e2_added_bank_'+str(sg)+'_connection_end','torso','hydraulic_bank_complete_reserve',box([.30,sg*.315,1.475],[.09,.06,.10]),[4.8]*3,own='Source PSL3 connection3.8kg+E4end1.0kg, full own configured footprint unknown')
# Bind to actual E2 neutral interface delivered by the independent structure branch.
interface_path=ROOT/'.scratch/gorilla_internal_e2_structure/interface.json';interface=json.loads(interface_path.read_text());imap={a['id']:a for a in interface['actuators']}
for a in cylinders:
 old=a['id'];key=old.replace('e2_center_','').replace('e2_','').replace('_pair0','_pair_0').replace('_pair1','_pair_1');v=imap[key]
 a.update({'interface_id':key,'A':v['neutral_A_world_m'],'B':v['neutral_B_world_m'],'bore':v['bore_m'],'rod':v['rod_m'],'stroke':v['actual_stroke_design_m'],'zero':v['allocated_custom_zero_eye_length_m'],'parent':v['base_body'],'child':v['output_body'],'axis_world':v['axis_world'],'pivot_world_m':v['pivot_world_m'],'source':'actual E2 interface finite custom cylinder, no OEM pressure/port CAD','interface_sha256':sha(interface_path)})

# Ports/chambers reconstructed using full finite zero/stroke budget, not massless rods.
for ci,a in enumerate(cylinders):
 A=np.array(a['A']);B=np.array(a['B']);u=(B-A)/np.linalg.norm(B-A);S=a['stroke'];ext=float(np.linalg.norm(B-A)-a['zero']);tail=max(0,a['zero']-S-.14);tube0=.04+tail;gland=tube0+S+.02;p0=tube0+ext;bo=a['bore']/2;rr=a['rod']/2
 hat=np.array([1.,0,0]);hat-=u*(u@hat);hat/=np.linalg.norm(hat)
 cstart=A+u*(tube0+.001);cend=A+u*(p0-.001);rstart=A+u*(p0+.021);rend=A+u*(gland-.001)
 assert ext>=0 and ext<=S,a['id']
 capfluid=cylinder(cstart,cend,bo-.001);rodfluid=tube(rstart,rend,bo-.001,rr+.001);oilwet(a['id']+'_cap_chamber',a['parent'],capfluid);oilwet(a['id']+'_rod_chamber',a['parent'],rodfluid)
 cport=onode(a['id']+'_cap_port',(cstart+cend)/2+hat*(bo+.018),a['parent']);rport=onode(a['id']+'_rod_port',(rstart+rend)/2+hat*(bo+.018),a['parent']);oilwet(a['id']+'_cap_bore',a['parent'],cylinder((cstart+cend)/2,nodes0 if False else oilnodes[cport]['center_world_m'],.003));oilwet(a['id']+'_rod_bore',a['parent'],cylinder((rstart+rend)/2+hat*(rr+.002),oilnodes[rport]['center_world_m'],.003))
 for port,cc in [(cport,(cstart+cend)/2),(rport,(rstart+rend)/2)]:emit(port+'_fitting',a['parent'],'oil_fitting_material',tube(cc+hat*(bo+.005),oilnodes[port]['center_world_m'],.006,.003),density=7850,own='Own positive fitting/seal bore; source cylinder port drill/seal/installed wall not matched, requires real cylinder rebuild')
 vc=np.array(a['valve_center']);vP=onode(a['id']+'_valve_P',vc+[-.050,0,.02]);vT=onode(a['id']+'_valve_T',vc+[-.050,0,-.02]);vA=onode(a['id']+'_valve_A',vc+[.05,-.012,.025]);vB=onode(a['id']+'_valve_B',vc+[.05,.012,-.025]);hc=(np.array(oilnodes[cport]['center_world_m'])+np.array(oilnodes[rport]['center_world_m']))/2+hat*.025;hold=onode(a['id']+'_hold',hc,a['parent']);holdbores=[];hports={}
 for mode,sg0 in [('A',-1),('B',1)]:
  hp=hc+u*(sg0*.016);hi=onode(a['id']+'_hold_'+mode+'_in',hp+hat*.035,a['parent']);ho=onode(a['id']+'_hold_'+mode+'_out',hp-hat*.035,a['parent']);bore=cylinder(oilnodes[hi]['center_world_m'],oilnodes[ho]['center_world_m'],.0045);holdbores.append(bore);oilwet(a['id']+'_hold_'+mode+'_internal',a['parent'],bore);hports[mode]=(hi,ho);oiledges.append([hi,ho])
 emit(a['id']+'_load_hold_complete',a['parent'],'load_hold_native_reserve',diff(box(hc,[.09,.09,.10]),holdbores),density=7850,own='Finite own steel-body mass from actual native volume, no unverifiable lightweight complete valve. One independent two working-port bored hold/shock reservation per cylinder, both hoses explicitly passthrough separate real bores. Own finite geometry/mass reserve, actual check/relief internals/electronics/fault position not specified; not safety-qualified or paired balance guarantee')
 oroute(a['id']+'_P_feed',oil_header_ports['P'][ci],vP,[point([.20,vc[1],2.20],'torso')],ri=.006,ro=.009,role='independent_valve_pressure');oroute(a['id']+'_T_return',vT,oil_header_ports['T'][ci],[point([.16,vc[1],1.81],'torso')],ri=.008,ro=.012,role='independent_valve_return')
 # C15-body waypoints; port endpoint is parent barrel hinge, not fixed torso ownership.
 sg=1 if A[1]>=0 else -1;way=[]
 if 'waist_' in a['parent']:way=[point([.32,vc[1],2.15],'torso'),point([.05,vc[1],2.32],a['parent'])]
 elif a['parent']!='torso':way=[point([.18,sg*.30,1.74],'torso'),point([.10,sg*.32,1.60],'pelvis')]
 if 'thigh' in a['parent']:way +=[point([.04,sg*.44,1.45],sg>0 and 'left_thigh' or 'right_thigh')]
 if 'shank' in a['parent']:way +=[point([.04,sg*.44,1.45],sg>0 and 'left_thigh' or 'right_thigh'),point([.02,sg*.49,.91],sg>0 and 'left_middle_shank' or 'right_middle_shank')]
 if 'distal' in a['parent']:way +=[point([.02,sg*.55,.52],a['parent'])]
 oroute(a['id']+'_A_working',vA,hports['A'][0],way+[point(np.array(oilnodes[cport]['center_world_m'])+hat*.025,a['parent'])],ri=.0045,ro=.008,role='bidirectional_cap_working');oroute(a['id']+'_B_working',vB,hports['B'][0],[{**w,'center_world_m':(np.array(w['center_world_m'])+[0,.015,0]).tolist()} for w in way]+[point(np.array(oilnodes[rport]['center_world_m'])+hat*.025,a['parent'])],ri=.0045,ro=.008,role='bidirectional_rod_working')
 oroute(a['id']+'_hold_A_to_cap',hports['A'][1],cport,[],ri=.0045,ro=.008,role='held_cap_connection');oroute(a['id']+'_hold_B_to_rod',hports['B'][1],rport,[],ri=.0045,ro=.008,role='held_rod_connection')
 oiledges +=[[vP,vA],[vB,vT],[vP,vB],[vA,vT]];a['native_chamber_volume_L']=[float(capfluid.volume*1000),float(rodfluid.volume*1000)];a['port_matches_structural_source']=False;a['barrel_hinge_is_independent_motion_not_parent_rigid']=True
# Disjoint oil across modeled lines/HX/chambers once; remaining tank oil is reduced from30L.
groups=collections.defaultdict(list)
for f in oilfluid:groups[f['body']].append(f['mesh'])
oiloccupied=None;oilinventory=[]
for body in sorted(groups):
 m=union(groups[body]);m=diff(m,[oiloccupied]) if oiloccupied is not None else m
 if m.volume<=1e-9:continue
 oilinventory.append({'body':body,'volume_L':m.volume*1000,'mass_range_kg':[m.volume*820,m.volume*850,m.volume*880]});emit('e2_oil_inventory_'+body,body,'oil_inventory_once',m,[m.volume*820,m.volume*850,m.volume*880],own='Disjoint actual native oil in lines/HX/chambers, subtracted from total30L; cylinder fluid body fields are neutral COM proxies only, independent barrel hinge/rod state not frozen')
 oiloccupied=union([oiloccupied,m]) if oiloccupied is not None else m.copy()
external_L=sum(q['volume_L'] for q in oilinventory);remaining_L=30-external_L;assert remaining_L>0
height=remaining_L/1000/(.256*.436);tc=np.array([.025,0,1.99-.305/2+.004+height/2]);tankoil=box(tc,[.256,.436,height]);emit('e2_tank_remaining_oil','torso','oil_inventory_once',tankoil,[remaining_L*.82,remaining_L*.85,remaining_L*.88],own='Remaining30L minus explicit disjoint lines/cylinders/HX oil. 4mm bottom liquid clearance; tank30L not counted again',remaining_tank_volume_L=remaining_L)
# Complete components retain unknown internal-oil volume out of this native estimate.
oil_unknown='OEM pump/filter/valve/loadhold internal oil CAD unknown; modeled external network is partial volume. Total30L remains fixed, later allocate these volumes from tank without adding stock.'
