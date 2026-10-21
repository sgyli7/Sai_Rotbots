"""Candidate15 preload048 downward-facing head fixture: compile/readback only by default.

No simulator stepping occurs in this script's entry point. Fixed head carrier
mount, free20kg manufactured rod/hanger/weight, physical lowering support table.
F owns a separately authorized driver. No mouth/object equality or live posewrite.
"""
import pathlib,json,hashlib,copy,math,argparse,xml.etree.ElementTree as ET
import numpy as np,mujoco as mj
W=pathlib.Path(__file__).resolve().parents[2];SOURCE=W/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate';PARENT=pathlib.Path('/home/ethan/ProjectBackups/2026-10-21/Sai_Lab/full_goose_r07_030/candidate12_preload_run_011')
E=W/'experiments/goose_v0_2/downward_pull_fixture_041_candidate15'
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
ref=lambda p:dict(path=str(p),sha256=sha(p))
s=lambda a:' '.join(format(float(v),'.17g')for v in a)
def rod_inertia(m,r,h):return [m*(3*r*r+h*h)/12,m*r*r/2,m*(3*r*r+h*h)/12]
def box_inertia(m,d):return [m*(d[(i+1)%3]**2+d[(i+2)%3]**2)/12 for i in range(3)]
def build(out):
 if out.exists():raise ValueError('Refuse overwrite '+str(out))
 src=ET.parse(SOURCE/'robot.xml').getroot();loaded=ET.parse(PARENT/'robot.xml').getroot();root=ET.Element('mujoco',model='candidate15_downward_pull_fixture041')
 for tag in ['compiler','option','default','asset']:
  old=src.find(tag)
  if old is not None:root.append(copy.deepcopy(old))
 for a in root.find('asset'):
  if a.get('file'):a.set('file',str((SOURCE/a.get('file')).resolve()))
 world=ET.SubElement(root,'worldbody');head=copy.deepcopy(src.find(".//body[@name='head_roll']"));head.remove(head.find('joint'));head.set('pos','0 0 1.15');head.set('quat',s([math.sqrt(.5),0,math.sqrt(.5),0]));world.append(head)
 ET.SubElement(head,'site',name='head_carrier_mount_loadcell',pos='0 0 0',size='.002',rgba='.1 .8 .8 1')
 ET.SubElement(world,'geom',name='fixed_carrier_mount_visual',type='box',pos='0 0 1.18',size='.025 .075 .02',contype='0',conaffinity='0',rgba='.15 .2 .3 .4')
 eq=ET.SubElement(root,'equality');eq.append(copy.deepcopy(src.find(".//connect[@name='beak_distal_pin']")))
 act=ET.SubElement(root,'actuator');act.append(copy.deepcopy(src.find(".//motor[@name='beak_hinge_motor']")))
 contact=ET.SubElement(root,'contact');contact.append(copy.deepcopy(src.find(".//pair[@name='actual_grip_closed_pad_contact']")))
 # Exact original12 frame: oldnative[81,0,585.5] at fixedhead origin; Ry90 mapsnative+X toworld-Z.
 R=np.array([[0,0,1],[0,1,0],[-1,0,0]],float);native=np.array([231.5,0,546.]);pos=np.array([0,0,1.15])+R@((native-[81,0,585.5])*.001)
 body=ET.SubElement(world,'body',name='calibrated_hanging_assembly',pos=s(pos));ET.SubElement(body,'freejoint',name='test_object_free6d')
 coremass=8000*math.pi*.004**2*.178;coatmass=1200*math.pi*(.006**2-.004**2)*.152;Icore=np.array(rod_inertia(coremass,.004,.178));PU_y2=(2*(.080**3/3)-2*(.019**3-.015**3)/3)/.152;Icoat=np.array([coatmass*((.006**2+.004**2)/4+PU_y2),coatmass*(.006**2+.004**2)/2,coatmass*((.006**2+.004**2)/4+PU_y2)]);ET.SubElement(body,'inertial',mass=str(coremass+coatmass),pos='0 0 0',diaginertia=s(Icore+Icoat))
 outer=copy.deepcopy(loaded.find(".//geom[@name='cart_bite_bar']"));outer.set('pos','0 0 0');body.append(outer)
 ET.SubElement(body,'geom',name='steel_core_geometry_visual_only',type='cylinder',size='.004 .089',quat=s([math.sqrt(.5),-math.sqrt(.5),0,0]),density='0',contype='0',conaffinity='0',rgba='.5 .53 .58 1')
 parts=[dict(name='304_core',mass_kg=coremass,dimensions_mm=[8,178],geometry='cylinder Ø8x178',material='304 target rho8000'),dict(name='PU_sleeve',mass_kg=coatmass,dimensions_mm=[12,8,152],geometry='OD12 ID8 PU segments [-80,-19],[-15,15],[19,80]mm, metalcollarsreplaceannuli at±17; centralgripPU unchanged',material='unqualified PU rho1200')]
 def piece(name,mass,xyz,I,typ,size,**kw):
  b=ET.SubElement(body,'body',name=name,pos=s(xyz));ET.SubElement(b,'inertial',mass=str(mass),pos='0 0 0',diaginertia=s(I));ET.SubElement(b,'geom',name=name+'_geom',type=typ,size=s(size),density='0',contype='4',conaffinity='7',friction=outer.get('friction'),condim=outer.get('condim'),solref=outer.get('solref'),margin='0',rgba='.4 .43 .48 1',**kw);parts.append(dict(name=name,mass_kg=mass,COM_assembly_m=xyz,I_com_diagonal_kg_m2=I,geometry=typ,size_m=size))
 for sign in [-1,1]:
  mm=8000*math.pi*(.006**2-.004**2)*.004;ii=[mm*(3*(.006**2+.004**2)+.004**2)/12,mm*(.006**2+.004**2)/2,mm*(3*(.006**2+.004**2)+.004**2)/12];piece('welded_end_collar_'+str(sign),mm,[0,sign*.017,0],ii,'cylinder',[.006,.002],quat=s([math.sqrt(.5),-math.sqrt(.5),0,0]))
  dims=[.01,.0005,.15];mm=8000*np.prod(dims);piece('symmetric_hanger_strap_'+str(sign),mm,[0,sign*.017,-.081],box_inertia(mm,dims),'box',[v/2 for v in dims])
 dims=[.01,.044,.005];mm=8000*np.prod(dims);piece('bolted_hanger_crossbar',mm,[0,0,-.1585],box_inertia(mm,dims),'box',[v/2 for v in dims])
 blockmass=20-sum(x['mass_kg']for x in parts);dims=[.1,.1,blockmass/(8000*.01)];blockcenter=-.161-dims[2]/2;piece('calibrated_304_ballast',blockmass,[0,0,blockcenter],box_inertia(blockmass,dims),'box',[v/2 for v in dims]);bottom=pos[2]+blockcenter-dims[2]/2
 table=ET.SubElement(world,'body',name='physical_lowering_platform',pos=s([pos[0],0,bottom-.010]));ET.SubElement(table,'joint',name='platform_slide',type='slide',axis='0 0 1',range='-.12 0',damping='20');ET.SubElement(table,'inertial',mass='8',pos='0 0 0',diaginertia='.05 .05 .08');ET.SubElement(table,'geom',name='physical_support_surface',type='box',size='.09 .11 .01',density='0',contype='8',conaffinity='4',friction='.65 .01 .002',condim='3',solref=outer.get('solref'),rgba='.2 .3 .45 1')
 ET.SubElement(act,'general',name='external_platform_actuator',joint='platform_slide',gaintype='fixed',gainprm='15000',biastype='affine',biasprm=s([28*9.81,-15000,-500]),ctrllimited='true',ctrlrange='-.12 0',forcelimited='true',forcerange='-600 600')
 sen=ET.SubElement(root,'sensor');ET.SubElement(sen,'force',name='mount_force_local',site='head_carrier_mount_loadcell');ET.SubElement(sen,'torque',name='mount_torque_local',site='head_carrier_mount_loadcell')
 out.mkdir(parents=True);ET.indent(root);ET.ElementTree(root).write(out/'scene.xml',encoding='utf-8',xml_declaration=True);m=mj.MjModel.from_xml_path(str(out/'scene.xml'));d=mj.MjData(m)
 # Fresh initial source branch only, before any step; not a runtimepose command.
 q=.29;C=np.array([160+29.87*math.cos(2.4531-q),576+29.87*math.sin(2.4531-q)]);A=np.array([129,601]);w=C-A;rr=np.linalg.norm(w);th=math.atan2(w[1],w[0])-math.acos((7.73**2+rr**2-15**2)/(2*7.73*rr));D=A+7.73*np.array([math.cos(th),math.sin(th)]);alpha=math.atan2(*(C-D)[::-1]);curve=json.load(open(W/'experiments/goose_v0_2/variable_gain_drive_029/fork_c02_headed_pin/kinematic_curve.json'));th0=curve[0]['theta'];C0=np.array(curve[0]['C_native_xz_mm']);D0=np.array(curve[0]['D_native_xz_mm']);al0=math.atan2(*(C0-D0)[::-1]);qin=-(th-th0);qcp=-(alpha-al0)-qin
 for name,val in [('beak_hinge',q),('beak_input_rotor',qin),('beak_coupler_link',qcp)]:d.qpos[int(m.joint(name).qposadr[0])]=val
 mj.mj_forward(m,d);np.savez(out/'initial_state.npz',qpos=d.qpos,qvel=d.qvel,ctrl=d.ctrl);mj.mj_saveModel(m,str(out/'actual_scene.mjb'),None)
 eid=m.equality('beak_distal_pin').id;b1,b2=int(m.eq_obj1id[eid]),int(m.eq_obj2id[eid]);ed=m.eq_data[eid];loop=np.linalg.norm(d.xpos[b1]+d.xmat[b1].reshape(3,3)@ed[:3]-d.xpos[b2]-d.xmat[b2].reshape(3,3)@ed[3:6]);nogrip=[]
 for c in d.contact:names=[m.geom(int(c.geom1)).name,m.geom(int(c.geom2)).name];nogrip.append(dict(names=names,dist_m=float(c.dist)))
 total=sum(m.body_mass[i]for i in range(m.nbody)if m.body_rootid[i]==m.body('calibrated_hanging_assembly').id)
 preserved={}
 sourceM=mj.MjModel.from_xml_path(str(SOURCE/'robot.xml'))
 for name in ['upper_bill_envelope','lower_bill_envelope']:
  i,j=m.geom(name).id,sourceM.geom(name).id;preserved[name]={a:float(np.max(abs(getattr(m,a)[i]-getattr(sourceM,a)[j])))for a in ['geom_friction','geom_solref','geom_solimp','geom_size']}
 manifest=dict(status='ZERO_STEP_SOURCE_BOUND_FIXTURE_PENDING_F_ROOT',builder=ref(pathlib.Path(__file__)),source_model_manifest=ref(SOURCE/'manifest.json'),source_robot=ref(SOURCE/'robot.xml'),source_loaded_bar_xml=ref(PARENT/'robot.xml'),source_adapter=ref(SOURCE/'runtime_adapter.py'),scene=ref(out/'scene.xml'),mjb=ref(out/'actual_scene.mjb'),initial=ref(out/'initial_state.npz'),physics_steps=0,head_mount=dict(fixed_body='head_roll',removed_only_incoming_joint='head_roll',original_native_mount_origin_mm=[81,0,585.5],fixed_world_origin_m=[0,0,1.15],orientation_R=R.tolist(),native_tip_direction_world=[0,0,-1],load_path='Originalmetalcarrier/headframe interface fixed upstream; no pad/object constraint, fixture itself not strengthqualified'),object=dict(free6d=True,assembly_mass_kg=total,gravity_N=total*9.81,initial_bar_center_world_m=pos.tolist(),native_bar_center_mm=native.tolist(),parts=parts,attachment='Two collars welded to locallyexposedcore bandsY±15..19 replacing PU outside centralclamp spanY±15, symmetricstraps/crossbar/ballast bolted as one manufacturedrigidassembly. No attachmenttomouth.',rod_yoke_separation_mm=34,rod_bending_screen=dict(each_half_force_N=98.1,half_cantilever_nominal_mm=17,half_cantilever_max_forceband_mm=17.25,nominal_304_core_bending_MPa=32*98.1*17.25/(math.pi*8**3),nominal_tip_deflection_mm=98.1*17.25**3/(3*193000*(math.pi*8**4/64)),factor6_core_bending_MPa=6*32*98.1*17.25/(math.pi*8**3),conditional_304_Sy_MPa=205,strap_factor6_axial_MPa=6*98.1/(10*.5),scope='One fixturecorrection: Y±17mm with .5mm straps setsforceband<=17.25. Conditional Sy205, factor6 unchanged; weld/haz/actualflexure remain inspectionconditions, not certifiedrigidfixture'),ballastmass_calibration='Ballast reduced by exactrod+hangers so totalassembly20.000kg; not20kgplusfixture'),contact=dict(same_bar_profile_as011=True,original_wholemouth_outerproxy=True,steel_core_collision=False,layer_limit='Original single outerØ12 envelope unchanged; Ø8core visual/nativeMCI only. Retain original2.025mm validitygate, no newhardcore normalmodel.',preserved_mouth_arrays=preserved),platform=dict(physical_slide=True,mass_kg=8,kp=15000,kd=500,fixed_gravity_bias_N=28*9.81,force_cap_N=600,reference_speed_max_m_s=.02,range_m=[-.12,0],initial_surface_gap_m=0.,require_actual_N_zero_and_signed_gap_positive=True,gravitybias_not_hidden_object_support='Only externalplatformactuator; no objectappliedforces. Mustmeasurezeroactualcontactbeforeholdclock.'),initial_readback=dict(nq=m.nq,nv=m.nv,nu=m.nu,neq=m.neq,ncon=d.ncon,loop_m=float(loop),contacts=nogrip,all_applied_forces_zero=bool(not np.any(d.xfrc_applied)and not np.any(d.qfrc_applied))),conditions=['No physicaltime advanced, defaultCLI prepareonly','Rawfixture20kg outwardpull test only, not wholeGoose/cart/universalqualification','Real manufacturedhanger/welds/ballast and fixedbench areengineeringdesign, no materialcertification','Newbushloss/axialfloat idealinternalmodel unchanged','All actual035beam/shaft/needle+037O38/C100+ROM/speed/power/loop/contact2.025 validityguards required every substep','Success requires5continuousseconds actualplatformN~0+positivegap, gravity carried bymouthcontact, nohiddenforce, load direction alongtip.'],run_recipe=dict(max_sim_s=12,max_wall_s=600,CPU=1,threads=1,memory_GiB=8,GPU=0,input_target_torque_Nm=3.,underlying_source_cap_Nm=4.4,phase0='Physicalplatformsettle .15s, inputholdopen; actualplatformN must carry20kg and gap settle beforeapproach, no objectposewrites.',phase1='Sourcephysicalinput qonlyclose, target speed .2rad/s; stopapproach on sustainedbilateral>5N100ms, physicalplatformsupportsweight.',phase2='Originalpositiveclosingtorque ramp5Nm/s to3.0Nm command; source200Hzlimiteronce,10substeps. Allguardsunchanged.',phase3='Platformreference lower at.02m/s to-.04m, actualcontactforcezero+positivegap required; no objectposewrites.',phase4='Holdsame3Nm5s fromactualfullplatformrelease, allstates/contacts/wrenches/slip/cone+energy saved; stopanyguard orfinitebudget, noautoretry.'))
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');E.mkdir(parents=True,exist_ok=True);(E/'preparation_handoff.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(out=str(out),mass=total,loop=loop,ncon=d.ncon,contacts=nogrip),indent=2))
 return m,d
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();build(a.out)


def observe_fixture(model,data,guard_config,screen_table):
 """One already-forwarded ACTUAL state readback; no integration or mutation of q/control.
 F must call every .5ms, with original source driver limiter once each5ms.
 """
 import sys,importlib.util
 if str(W/'scripts/diagnostics')not in sys.path:sys.path.insert(0,str(W/'scripts/diagnostics'))
 from goose_mouth_actual_wrench_screen_035 import screen_contacts
 from goose_mouth_actual_axial_reaction_031 import screen_actual_axial_reactions
 points=[];contacts=[];grip={'upper':0.,'lower':0.};platformN=0.;platformF=np.zeros(3);mouth_on_object=np.zeros(3);other_on_object=np.zeros(3);nonmouth_support_N=0.;coat=0.;object_id=model.body('calibrated_hanging_assembly').id
 for k,c in enumerate(data.contact):
  names=[model.geom(int(c.geom1)).name,model.geom(int(c.geom2)).name];f=np.zeros(6);mj.mj_contactForce(model,data,k,f);R=c.frame.reshape(3,3);world=R.T@f[:3];couple=R.T@f[3:];g1,g2=int(c.geom1),int(c.geom2)
  root1=int(model.body_rootid[int(model.geom_bodyid[g1])]);root2=int(model.body_rootid[int(model.geom_bodyid[g2])]);on1=root1==object_id;on2=root2==object_id;sg=1 if on2 else -1
  if 'physical_support_surface'in names and (on1 or on2):platformN+=max(0.,float(f[0]));platformF+=sg*world
  mouth=next((n for n in names if n in ['upper_bill_envelope','lower_bill_envelope']),None)
  if mouth and 'cart_bite_bar'in names:
   side='upper'if'upper'in mouth else'lower';body='head_roll'if side=='upper'else'beak_hinge';origin=np.array([81,0,585.5]if side=='upper'else[160,0,576]);bid=model.body(body).id;rot=data.xmat[bid].reshape(3,3);sign=1 if names[1]==mouth else-1
   axial_contact_local=float((data.xmat[object_id].reshape(3,3).T@(c.pos-data.xpos[object_id]))[1]);contact_on_PU=abs(axial_contact_local)<.015
   points.append(dict(test_rod_axial_contact_m=axial_contact_local,unmodified_central_PU_span=contact_on_PU,mouth=mouth,normal_N=float(f[0]),native_point_mm=(origin+1000*rot.T@(c.pos-data.xpos[bid])).tolist(),native_force_on_mouth_N=(rot.T@(sign*world)).tolist(),native_couple_on_mouth_Nm=(rot.T@(sign*couple)).tolist()));grip[side]+=max(0.,float(f[0]));coat=max(coat,-float(c.dist));mouth_on_object+=sg*world
  if (on1 or on2) and 'physical_support_surface'not in names and not (mouth and 'cart_bite_bar'in names):
   other_on_object+=sg*world;nonmouth_support_N+=max(0.,float(f[0]))
  contactrow=dict(names=names,pos=c.pos.tolist(),frame=c.frame.tolist(),dist=float(c.dist),wrench6=f.tolist())
  if on1!=on2:
   jo=np.zeros((3,model.nv));jj=jo.copy();ob=int(model.geom_bodyid[g2 if on2 else g1]);ot=int(model.geom_bodyid[g1 if on2 else g2]);mj.mj_jac(model,data,jo,None,c.pos,ob);mj.mj_jac(model,data,jj,None,c.pos,ot);rel=(jo-jj)@data.qvel;n=sg*R[0];tf=sg*world-n*float((sg*world)@n);vt=rel-n*float(rel@n)
   contactrow.update(relative_tangent_velocity_world_m_s=vt.tolist(),friction_power_W=float(tf@vt),cone_utilization=float(np.linalg.norm(f[1:3])/max(1e-12,c.friction[0]*max(0.,f[0]))))
  contacts.append(contactrow)
 outside_PU=sum(p['normal_N']for p in points if not p.get('unmodified_central_PU_span',True))
 qjaw=float(data.qpos[int(model.joint('beak_hinge').qposadr[0])]);beams=screen_contacts(points,qjaw,screen_table);axial=screen_actual_axial_reactions(model,data,guard_config);reasons=[r for r in beams['reasons']if not r.endswith('_net_Fy_finitefixture_domain_exited')]+axial['reasons']
 if outside_PU>1.:reasons.append('contact_outside_unmodified_central_PU_testspan')
 if nonmouth_support_N>1.:reasons.append('nonmouth_object_contact_bypass_domain')
 if coat>.002025:reasons.append('original_outerbar2p025mm_proxy_validity_domain_exited')
 eid=model.equality('beak_distal_pin').id;b1,b2=int(model.eq_obj1id[eid]),int(model.eq_obj2id[eid]);e=model.eq_data[eid];loop=float(np.linalg.norm(data.xpos[b1]+data.xmat[b1].reshape(3,3)@e[:3]-data.xpos[b2]-data.xmat[b2].reshape(3,3)@e[3:6]));j=model.joint('beak_input_rotor').id;speed=float(data.qvel[int(model.jnt_dofadr[j])]);tau=float(data.actuator_force[0]);
 if loop>25e-6:reasons.append('source_loop25um')
 if abs(speed)>1.:reasons.append('original_input_speed1rad_s')
 if abs(tau)>4.4+1e-9:reasons.append('original_input4p4Nm_cap')
 if abs(tau*speed)>350:reasons.append('source350W_positive_power_guard')
 for n in ['beak_hinge','beak_input_rotor']:
  ji=model.joint(n).id;q=float(data.qpos[int(model.jnt_qposadr[ji])]);lo,hi=model.jnt_range[ji]
  if not lo-1e-8<=q<=hi+1e-8:reasons.append('source_ROM_'+n)
 if any(x.number for x in data.warning):reasons.append('physics_warning')
 if not all(np.isfinite(x).all()for x in [data.qpos,data.qvel,data.qacc,data.ctrl,data.actuator_force]):reasons.append('nonfinite_state_force')
 if np.any(data.xfrc_applied)or np.any(data.qfrc_applied):reasons.append('hidden_applied_force')
 distance=float(mj.mj_geomDistance(model,data,model.geom('physical_support_surface').id,model.geom('calibrated_304_ballast_geom').id,1.,None));mount=np.array(data.sensordata[:3]);Rmount=data.xmat[model.body('head_roll').id].reshape(3,3);mount_world=Rmount@mount
 return dict(time=float(data.time),reasons=sorted(set(reasons)),contacts=contacts,material_points=points,actual_wrench_screen=beams,actual_C_O=axial,input_tau_Nm=tau,input_speed_rad_s=speed,grip_normal_N=grip,platform_N=platformN,platform_force_on_object_world_N=platformF.tolist(),platform_ballast_signed_gap_m=distance,mouth_force_on_object_world_N=mouth_on_object.tolist(),other_force_on_object_world_N=other_on_object.tolist(),nonmouth_object_contact_normal_N=nonmouth_support_N,outward_direction_world=[0,0,-1],payload_COM_world_m=data.subtree_com[object_id].tolist(),native_workpiece_center_mm=(np.array([81,0,585.5])+1000*data.xmat[model.body('head_roll').id].reshape(3,3).T@(data.geom_xpos[model.geom('cart_bite_bar').id]-data.xpos[model.body('head_roll').id])).tolist(),mount_force_world_N=mount_world.tolist(),coat_envelope_penetration_m=coat,loop_m=loop,gravity_load_N=196.2,hold_eligibility=bool(platformN<.05 and distance>.0005 and nonmouth_support_N<.05 and mouth_on_object[2]>190),note='Holdclock>=5s requires every substep tablefree+positivegap+actualmouthgravitysupport; record allforcebalance/acceleration/slip, not thresholdonlysuccess. No hardwarequalification.')
