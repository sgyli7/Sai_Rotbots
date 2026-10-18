"""Cart02 native CAD/MCI/tote and actual FK context review. No dynamics.
Run native mode with cadgen0.7.21 Python; context mode with the existing MuJoCo3.10 environment.
"""
import sys
MODE=sys.argv[1] if len(sys.argv)>1 else 'native'
if MODE=='native':
    from pathlib import Path
    import sys,json,hashlib,math
    W=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(W/'scripts/cad'))
    from goose_low_profile_stock_cart_02 import make_cart
    from cadgen import read_step,build123d as bd
    shape,rows,p=make_cart();exp=W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_02';E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_02'
    for row,ch in zip(rows,shape.children):
        rho=p['materials'][row['material']]['density_kg_m3'];row['full_inertia_about_COM_kg_m2']=[[v*rho*1e-15 for v in rr] for rr in ch.matrix_of_inertia];row['bounds_mm']={'min':list(ch.bounding_box().min),'max':list(ch.bounding_box().max)}
    saved=read_step(exp/'goose_low_profile_stock_cart_02.step')
    tote=bd.Pos(325,0,256.5)*bd.Box(600,400,150)
    checks=[]
    for ch in shape.children:
        ov=ch.intersect(tote);vol=ov.volume if ov is not None else 0.0
        checks.append({'part':ch.label,'overlap_volume_mm3':vol,'distance_mm':ch.distance_to(tote)})
    old_path=W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_01/goose_low_profile_stock_cart_01.step'
    old=read_step(old_path) if old_path.exists() else None;old_ov=old.intersect(tote) if old is not None else None
    (E/'tote_clearance.json').write_text(json.dumps({'revision':p.get('revision'),'tote_envelope_mm':{'center':[325,0,256.5],'size':[600,400,150],'bottom_z':181.5},'scope':'Native positive-volume envelope test at intended centered load pose only. Deck support face touch allowed. No insertion sweep, loose-goods or dynamic retention qualification.','old_r2_STEP_SHA256':hashlib.sha256(old_path.read_bytes()).hexdigest() if old_path.exists() else None,'old_r2_tote_overlap_volume_mm3':sum(x.volume for x in old_ov) if isinstance(old_ov,list) else (old_ov.volume if old_ov is not None else 0.0),'new_positive_overlaps_above_0p001mm3':[r for r in checks if r['overlap_volume_mm3']>0.001],'new_mast_gusset_clearances':[r for r in checks if 'mast_base_gusset' in r['part']],'part_checks':checks},indent=2)+'\n')
    m=sum(r['mass_kg'] for r in rows);com=[sum(r['mass_kg']*r['COM_mm'][i] for r in rows)/m for i in range(3)]
    # Explicit unmodelled fastening/reserve, not density inflation or double counted M6s.
    reserve=.35;reserve_com=[260,0,180];mt=m+reserve;ct=[(m*com[i]+reserve*reserve_com[i])/mt for i in range(3)]
    payload=20.;cargo=[325,0,331.5];total=mt+payload;combined=[(mt*ct[i]+payload*cargo[i])/total for i in range(3)]
    draw=[r for r in rows if any(w in r['name'] for w in ['drawbar_','roll_bearing','rotating_forward','bite_yoke','bite_core','bite_304','replaceable_bite'])];dm=sum(r['mass_kg'] for r in draw);dc=[sum(r['mass_kg']*r['COM_mm'][i] for r in draw)/dm for i in range(3)]
    g=9.81;F=30.;t=p['frame_wall'];I=(20*30**3-(20-2*t)*(30-2*t)**3)/12;P=total*g;span=490.;M=P*span/4;stress=M*15/I;defl=P*span**3/(48*69000*I)
    I_mast=(32**4-28**4)/12;M_mast=F*(p['grip_center'][2]-150);maststress=M_mast*16/I_mast
    Fx_tip=total*g*(combined[0]-80)/p['grip_center'][2];Fy_tip=total*g*(165-abs(combined[1]))/p['grip_center'][2]
    support={'nominal_wheel_contact_centers_mm':[[x,y,0] for x in [80,570] for y in [-190,190]],'caster_all_headings_conservative_support_rectangle_mm':{'x':[80,570],'y':[-165,165]},'cargo_COM_allowed_mm':{'x':[225,425],'y':[-75,75],'z_max':400},'centered_payload_COM_assumed_mm':cargo,'loaded_COM_mm':combined,'nominal_loaded_tip_angle_side_deg':math.degrees(math.atan(190/combined[2])),'nominal_loaded_tip_angle_fore_aft_min_deg':math.degrees(math.atan(min(combined[0]-80,570-combined[0])/combined[2])),'cart_ideal_horizontal_pull_tip_thresholds_N':{'toward_goose_minusX':Fx_tip,'lateral':Fy_tip},'not_certification':'Rigid level four-point support only; swivel sweep, payload shift, slope and one-wheel obstacles separately require tests.'}
    forces=[]
    for rr in [.01,.02,.03]:
     for accel in [0,.2]:
      for slope in [0,.02]:forces.append({'rolling_coefficient_assumed':rr,'accel_m_s2':accel,'grade_assumed':slope,'estimated_required_F_N':rr*total*g+total*accel+total*g*slope,'excludes':'caster alignment, bearing seal losses, thresholds and floor joints'})
    sources={'hydro_6061':'https://www.hydro.com/globalassets/01-products--services/extruded-profiles/americas/ena-resources/alloy-data-sheets/hydro_2019_data_sheet_6061.pdf','castor_resistance_context':'https://www.blickle.com/guide/info-box-wheel-series','note':'No vendor rolling percentage or off-the-shelf wheel capacity is assigned to the custom envelope. rr values are explicit scenario assumptions to be measured.'}
    out={'design_id':'low_profile_stock_cart_02','revision':p['revision'],'status':'CAD_GEOMETRY_AND_ANALYTICAL_SCREEN_ONLY','parts':rows,'CAD_part_count':len(rows),'native_solid_count':len(shape.solids()),'all_individual_valid_positive':all(r['positive_volume'] and r['valid_native'] for r in rows),'CAD_mass_kg':m,'CAD_COM_mm':com,'unmodelled_reserve_kg':reserve,'reserve_reason':'Basket quick pins, frame joint angle brackets/corner hardware, remaining locking nuts, spring ends and anti-drop fasteners not yet fully detailed. Existing modelled wheel/mast M6s not counted twice.','estimated_empty_mass_kg':mt,'estimated_empty_mass_range_kg':[mt*.9,mt*1.15],'estimated_empty_COM_mm':ct,'payload_kg':payload,'gross_mass_kg':total,'over_goose_weight_ratio_gross':total/16.97020392883353,'drawbar_hand_end_moving_mass_kg':dm,'drawbar_COM_mm':dc,'unbalanced_vertical_bite_force_N':dm*g*abs(dc[0]+95)/abs(p['grip_center'][0]+95),'pitch_balance_spring_target_Nm':dm*g*abs(dc[0]+95)*.001,'support_screen':support,'analytical_structure':{'rail_section_mm':[20,30,p['frame_wall']],'rail_I_mm4':I,'2g_gross_load_split_two_rails_one_center_load_each_stress_MPa':stress,'same_deflection_mm':defl,'assumed_screen_allowable_MPa':70,'mast_F30N_actual_grip_minus150mm_arm_stress_MPa':maststress,'wheel_module_min_design_rating_N_each':total*g*2/3,'limit':'Beam nominal screening only. Joint groups, gusset/base plate, three-wheel events and caster/fork bolts not FEA or certified. Deck requires 600x400 tote/supporting box base; concentrated feet need local spreading plate.','cargo_tote_fit_mm':[610,410]},'force_scenarios':forces,'saved_step':{'bytes':(exp/'goose_low_profile_stock_cart_02.step').stat().st_size,'SHA256':hashlib.sha256((exp/'goose_low_profile_stock_cart_02.step').read_bytes()).hexdigest(),'solid_count':len(saved.solids()),'is_valid':saved.is_valid,'bounds_mm':{'min':list(saved.bounding_box().min),'max':list(saved.bounding_box().max)},'volume_delta_mm3':saved.volume-shape.volume},'sources':sources,'physics_integrations':0,'GPU':0,'training_updates':0}
    
    import numpy as np
    I_total=np.zeros((3,3));c=np.array(com)*.001
    for r in rows:
        dv=np.array(r['COM_mm'])*.001-c
        I_total+=np.array(r['full_inertia_about_COM_kg_m2'])+r['mass_kg']*((dv@dv)*np.eye(3)-np.outer(dv,dv))
    out['CAD_full_inertia_about_COM_kg_m2']=I_total.tolist()
    out['reserve_COM_mm']=reserve_com
    out['reserve_independent_inertia']='UNKNOWN; intrinsic inertia not determined. Simulation assignment remains an explicit provisional assumption.'
    out['actual_bite_center_cart_mm']=p['grip_center']
    out['drawhead_pitch_deg']=p['drawhead_pitch_deg']
    out['drawhead_pivot_center_mm']=p['drawhead_pivot_center']
    (E/'geometry_mass_screen.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['CAD_part_count','native_solid_count','all_individual_valid_positive','CAD_mass_kg','estimated_empty_mass_kg','CAD_COM_mm','CAD_full_inertia_about_COM_kg_m2','saved_step']},indent=2))
elif MODE=='context':
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
    
    W=Path(__file__).resolve().parents[2];PKG=W/'robots/goose_v0_2/models/physics_v0_2_20261018_04';IMG=W/'robots/goose_v0_2/images/low_profile_stock_cart_02';E=W/'robots/goose_v0_2/evidence/low_profile_stock_cart_02'
    C=json.loads((PKG/'physical_contract.json').read_text());p=json.loads((W/'robots/goose_v0_2/cad/source/low_profile_stock_cart_02/parameters.json').read_text())
    m=mj.MjModel.from_xml_path(str(PKG/'robot.xml'));d=mj.MjData(m);d.qpos[:]=p['robot_full_qpos']
    for n,q in zip(['neck_pitch','neck_mid_pitch','head_pitch'],p['robot_04_preferred_neck_pitch_mid_head_rad']):d.qpos[int(m.joint(n).qposadr[0])]=q
    d.qpos[int(m.joint('beak_hinge').qposadr[0])]=.19682523003160665
    for j in C['passive_linkage_joints']:d.qpos[int(m.joint(j['name']).qposadr[0])]=j['mimic_multiplier']*d.qpos[int(m.joint(j['mimic_joint']).qposadr[0])]+j['mimic_offset_rad']
    mj.mj_forward(m,d)
    robot=[]
    for g in range(m.ngeom):
     if m.geom_type[g]!=mj.mjtGeom.mjGEOM_MESH:continue
     mid=int(m.geom_dataid[g]);v=m.mesh_vert[int(m.mesh_vertadr[mid]):int(m.mesh_vertadr[mid]+m.mesh_vertnum[mid])];f=m.mesh_face[int(m.mesh_faceadr[mid]):int(m.mesh_faceadr[mid]+m.mesh_facenum[mid])];vv=(v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g])*1000
     robot.append({'name':m.geom(g).name,'v':vv,'f':f.copy(),'color':m.geom_rgba[g,:3].copy()})
    scene=trimesh.load(W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_02/goose_low_profile_stock_cart_02.glb');cart=[]
    for node in scene.graph.nodes_geometry:
     T,key=scene.graph[node];geom=scene.geometry[key];vv=trimesh.transform_points(geom.vertices,T);vv=np.c_[vv[:,0],-vv[:,2],vv[:,1]]*1000;vv+=np.array(p['cart_origin_robot_frame_mm'])
     mat=geom.visual.material;rgba=getattr(mat,'baseColorFactor',None);col=np.array(rgba[:3])/255 if rgba is not None else [.75,.78,.8]
     cart.append({'name':node,'v':vv,'f':geom.faces,'color':col})
    
    def side():
     fig,ax=plt.subplots(figsize=(15,7),layout='constrained');fig.patch.set_facecolor('#f7f8fa');ax.set_facecolor('#f7f8fa')
     for obj in cart+robot:
      tri=obj['v'][obj['f']];order=np.argsort(tri[:,:,1].mean(1))[::-1];poly=PolyCollection(tri[order][:,:,[0,2]],facecolor=obj['color'],edgecolor='none');ax.add_collection(poly)
     ax.axhline(0,color='#647381',lw=1);ax.set_xlim(-270,1370);ax.set_ylim(-35,745);ax.set_aspect('equal');ax.set_xlabel('World X / mm  (robot faces +X; backward towing moves -X)');ax.set_ylabel('Height / mm')
     ax.scatter([300],[420],s=45,c='#dd4c31',zorder=20);ax.annotate('Actual bite TCP: (300, 0, 420) mm; drawhead pitch +10 deg',xy=(300,420),xytext=(50,705),arrowprops={'arrowstyle':'->','color':'#b63f25'},fontsize=10,color='#a83c2b')
     ax.annotate('Deck 181.5 mm\nLow rim 290 mm',xy=(1000,182),xytext=(1040,425),arrowprops={'arrowstyle':'->'},fontsize=10)
     ax.annotate('',xy=(646.125977,-15),xytext=(1296.125977,-15),arrowprops={'arrowstyle':'<->'});ax.text(975,-25,'650 mm platform',ha='center',va='top',fontsize=9)
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
    out={'source_robot':'physics_v0_2_20261018_04','robot_xml_sha256':hashlib.sha256((PKG/'robot.xml').read_bytes()).hexdigest(),'cart_GLB_sha256':hashlib.sha256((W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_02/goose_low_profile_stock_cart_02.glb').read_bytes()).hexdigest(),'robot_geometry':'14 loaded convex physics meshes, not native exterior CAD','robot_named_joints_rad':dict(zip(['neck_pitch','neck_mid_pitch','head_pitch'],p['robot_04_preferred_neck_pitch_mid_head_rad'])),'cart_origin_robot_frame_mm':p['cart_origin_robot_frame_mm'],'grip_TCP_robot_frame_mm':[300,0,420],'deck_world_x_range_mm':[p['cart_origin_robot_frame_mm'][0],p['cart_origin_robot_frame_mm'][0]+650],'basket_rim_z_mm':290,'shoes_to_cart_deck_front_horizontal_separation_mm':p['cart_origin_robot_frame_mm'][0]-front_shoe,'loaded_robot_self_penetration_beyond0p1mm':negative,'robot_geom_bounds_mm':bounds,'physics_integrations':0,'training':0,'GPU':0,'qualifications':'Geometry context only. Shoe-to-platform X separation is a sufficient plane separation at this single FK pose; cart tow head and jaws require separate local clearance/contact checks. No swept gait or dynamic support qualification.'}
    out['full_qpos']=d.qpos.tolist();out['joint_qpos_addresses']={m.joint(j).name:int(m.jnt_qposadr[j]) for j in range(m.njnt)}
    np.savez_compressed(E/'selected_fk_state.npz',qpos=d.qpos.copy(),qvel=d.qvel.copy(),grip_center_robot_m=np.array([.3,0,.42]),cart_origin_robot_m=np.array(p['cart_origin_robot_frame_mm'])*.001)
    (E/'goose_cart_context.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'geometry_bounds':bounds,'shoe_to_deck_X_mm':p['cart_origin_robot_frame_mm'][0]-front_shoe,'self_penetrations':negative,'physics_integrations':0},indent=2))
    
    # Both panels retain the exact same world scale, camera and full foot/cart bounds.
    new_robot,new_cart=robot,cart
    old_state=np.load(W/'robots/goose_v0_2/evidence/low_profile_stock_cart_01/selected_fk_state.npz')
    d.qpos[:]=old_state['qpos'];mj.mj_forward(m,d)
    old_robot=[]
    for g in range(m.ngeom):
     if m.geom_type[g]!=mj.mjtGeom.mjGEOM_MESH:continue
     mid=int(m.geom_dataid[g]);v=m.mesh_vert[int(m.mesh_vertadr[mid]):int(m.mesh_vertadr[mid]+m.mesh_vertnum[mid])];f=m.mesh_face[int(m.mesh_faceadr[mid]):int(m.mesh_faceadr[mid]+m.mesh_facenum[mid])]
     old_robot.append({'v':(v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g])*1000,'f':f.copy(),'color':m.geom_rgba[g,:3].copy()})
    old_scene=trimesh.load(W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_01/goose_low_profile_stock_cart_01.glb');old_cart=[]
    for node in old_scene.graph.nodes_geometry:
     T,key=old_scene.graph[node];geom=old_scene.geometry[key];vv=trimesh.transform_points(geom.vertices,T);vv=np.c_[vv[:,0],-vv[:,2],vv[:,1]]*1000;vv[:,0]+=650
     rgba=getattr(geom.visual.material,'baseColorFactor',None);col=np.array(rgba[:3])/255 if rgba is not None else [.75,.78,.8]
     old_cart.append({'v':vv,'f':geom.faces,'color':col})
    fig,axs=plt.subplots(2,1,figsize=(15,12),layout='constrained');fig.patch.set_facecolor('#f7f8fa')
    for ax,rr,cc,hh,tt in [(axs[0],old_robot,old_cart,480,'R2 / OLD: grip 480 mm, level head and drawbar'),(axs[1],new_robot,new_cart,420,'R3 / LOW: grip 420 mm, head and passive drawbar pitch 10 deg')]:
     ax.set_facecolor('#f7f8fa')
     for obj in cc+rr:
      tri=obj['v'][obj['f']];order=np.argsort(tri[:,:,1].mean(1))[::-1];ax.add_collection(PolyCollection(tri[order][:,:,[0,2]],facecolor=obj['color'],edgecolor='none'))
     ax.axhline(0,color='#647381',lw=1);ax.set_xlim(-270,1370);ax.set_ylim(-35,745);ax.set_aspect('equal');ax.set_xlabel('World X / mm');ax.set_ylabel('Actual height above floor / mm');ax.set_title(tt,fontsize=14,loc='left',pad=9)
     ax.plot(300,hh,'o',c='#bd4937',ms=6);ax.annotate(f'Bite center: {hh} mm',xy=(300,hh),xytext=(450,650),arrowprops={'arrowstyle':'->','color':'#bd4937'},color='#9e392c',fontsize=11)
     ax.annotate('',xy=(300,0),xytext=(300,hh),arrowprops={'arrowstyle':'<->','color':'#bd4937'});ax.text(313,hh/2,f'{hh} mm',color='#9e392c',va='center')
     ax.text(1000,600,'20 kg useful cargo TARGET\n+ actual empty cart mass\nNo dynamic drag qualification',fontsize=10,ha='center',color='#334653',bbox={'facecolor':'white','edgecolor':'#bbc6ce','pad':7})
    fig.suptitle('GOOSE 04 + PASSIVE STOCK CART | SAME WORLD SCALE / REAL FK + CAD\nRobot: 14 loaded convex physics proxies; cart: native CAD export. No robot hardware or actuator change.',fontsize=13)
    fig.savefig(IMG/'grip_height_comparison.png',dpi=160);plt.close(fig)
    # Restore selected state before independent true-outer-surface mouth clearance.
    d.qpos[:]=p['robot_full_qpos'];mj.mj_forward(m,d)
    root=ET.parse(PKG/'robot.xml').getroot()
    for mesh in root.findall('./asset/mesh'):mesh.set('file',str((PKG/mesh.get('file')).resolve()))
    piv=np.array(p['drawhead_pivot_center'])*.001;angle=np.deg2rad(p['drawhead_pitch_deg']);co=np.cos(angle);si=np.sin(angle);R=np.array([[co,0,si],[0,1,0],[-si,0,co]]);origin=np.array(p['cart_origin_robot_frame_mm'])*.001
    z=piv[2]
    rods={'bite_sleeve':([-.350,-.080,z],[-.350,.080,z],.006),'bite_yoke_positiveY':([-.287,0,z],[-.350,.085,z],.007),'bite_yoke_negativeY':([-.287,0,z],[-.350,-.085,z],.007),'shaft_socket':([-.299,0,z],[-.275,0,z],.007),'steel_roll_shaft':([-.305,0,z],[-.195,0,z],.004),'roll_housing_outer':([-.245,0,z],[-.203,0,z],.017)}
    world_rods={}
    for n,(a,b,r) in rods.items():
     aa=(R@(np.array(a)-piv)+piv+origin).tolist();bb=(R@(np.array(b)-piv)+piv+origin).tolist();world_rods[n]=[aa,bb,r];ET.SubElement(root.find('worldbody'),'geom',name='cart_'+n,type='cylinder',fromto=' '.join(map(str,aa+bb)),size=str(r),density='0',contype='0',conaffinity='0')
    qm=mj.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'));qd=mj.MjData(qm);qd.qpos[:]=p['robot_full_qpos'];mj.mj_forward(qm,qd);dist=[]
    for n in rods:
     for jaw in ['upper_bill_envelope','lower_bill_envelope']:
      seg=np.zeros(6);v=mj.mj_geomDistance(qm,qd,qm.geom('cart_'+n).id,qm.geom(jaw).id,1,seg);dist.append({'cart_part':n,'robot_geom':jaw,'signed_distance_m':float(v),'closest_segment_world_m':seg.tolist()})
    clear={'revision':p['revision'],'query':'Frozen04 loaded convex jaw proxies versus exact outer cylinders of native CAD rods transformed around true +Y pitch pivot. Holes ignored only where external mouth surface is unchanged.','scope':'Nominal single posture only; no approach, gait, yaw/pitch sweep, clamp force or dynamic test.','distances':dist,'world_rods':world_rods,'physics_integrations':0,'GPU':0,'training_updates':0}
    (E/'local_mouth_clearance.json').write_text(json.dumps(clear,indent=2)+'\n')
    print(json.dumps({'mouth_clearance_min_nonbite_mm':min(r['signed_distance_m'] for r in dist if r['cart_part']!='bite_sleeve')*1000,'bite_distances_mm':[r['signed_distance_m']*1000 for r in dist if r['cart_part']=='bite_sleeve'],'comparison':'grip_height_comparison.png'},indent=2))
elif MODE=='drawing':
    from pathlib import Path
    import json
    import cadgen
    from cadgen.eng_drawing import Sheet,eng_drawing
    from goose_low_profile_stock_cart_02 import PARAMS
    W=Path(__file__).resolve().parents[2]
    
    @eng_drawing(out='../../robots/goose_v0_2/cad/exports/low_profile_stock_cart_02/goose_low_profile_stock_cart_02_drawing.pdf')
    def goose_low_profile_stock_cart_02_drawing():
        p=json.loads(PARAMS.read_text())
        part=cadgen.read_step(W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_02/goose_low_profile_stock_cart_02.step')
        sheet=Sheet('A2',scale=.2,title='GOOSE LOW STOCK CART',part_number='CART-01',material='Al frame/deck, steel pins, PU wheels',revision='R3 LOW 420',author='Sai_Rotbots',notes=['NOMINAL GEOMETRY / DESIGN REVIEW.', '20 kg PAYLOAD TARGET, NOT LOAD CERTIFIED.', 'ACTUAL BITE HEIGHT: 400/420/440, DEFAULT 420.', 'CARRIAGE HOLE Z: 355.720/375.720/395.720.', 'PASSIVE PITCH +10 DEG. MAST TOP 440.', 'NO ROBOT DRAG OR BRAKE QUALIFICATION.'])
        top,front,right=sheet.three_views(part,gap=60)
        iso=sheet.view(part,'iso',at=(465,300),label='ISOMETRIC 1:10',scale=.1)
        top.overall();front.overall();right.overall()
        front.dim((0,0,p['deck_top_z']),(p['platform_length'],0,p['deck_top_z']),orientation='h')
        front.dim((80,-190,0),tuple(p['grip_center']),orientation='v')
        front.dim((80,-190,62.5),(570,-190,62.5),orientation='h')
        top.dim((325,-225,p['deck_top_z']),(325,225,p['deck_top_z']),orientation='v')
        top.dim(tuple(p['grip_center']),(0,0,p['deck_top_z']),orientation='h')
        return sheet
    
    if __name__=='__main__':goose_low_profile_stock_cart_02_drawing()
elif MODE=='closeup':
    from pathlib import Path
    import json
    from cadgen import read_step,build123d as bd
    W=Path(__file__).resolve().parents[2]
    saved=read_step(W/'robots/goose_v0_2/cad/exports/low_profile_stock_cart_02/goose_low_profile_stock_cart_02.step')
    # A visible-only subset of saved native solids; no surface or position is changed.
    chosen=[s for s in saved.solids() if s.center(bd.CenterOf.MASS).X < -40 and s.center(bd.CenterOf.MASS).Z > 300]
    dst=W/'artifacts/goose_v0_2/low_handle_study_01/cart02_tow_head_detail.step'
    bd.export_step(bd.Compound(children=chosen,label='native_cart02_tow_head_detail'),dst)
    print(json.dumps({'source':'saved complete cart02 STEP','selection':'COM.x<-40mm and COM.z>300mm','solid_count':len(chosen),'visible_subset_only':True,'path':str(dst)}))
