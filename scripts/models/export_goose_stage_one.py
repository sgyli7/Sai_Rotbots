"""Export reviewable structural parameters, URDF and preserved editable quads."""
from pathlib import Path
import sys,json,csv,hashlib
import xml.etree.ElementTree as ET
from collections import Counter
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/models'));sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_stage_one import candidate,R,OUT,vec
from build_goose_r2_reference_rebuild import cylinder

def main():
 s=candidate();c=json.loads((R/'configs/stage_one_contract.json').read_text());cad=R/'cad/source/stage_one_architecture';cad.mkdir(parents=True,exist_ok=True)
 parts=[p.copy() for p in s.parts.values() if p['group'] not in s.selected and p['group']!='torso_electronics']
 for n,key in s.selected.items():
  cat=s.catalog[key];m=cylinder(tuple(s.pivots[n]*1000),cat['diameter']*500,cat['length']*1000,int(np.argmax(abs(s.axes[n]))),.4)
  parts.append(dict(name=n+'_catalog_case',material='graphite',group=n,role='manufacturer_dimension_cylinder_not_vendor_cad',vertices=(m.vertices/1000).tolist(),faces=np.asarray(m.faces).tolist()))
 for p in parts:
  p['source_sha256']=hashlib.sha256(json.dumps(dict(vertices=p['vertices'],faces=p['faces']),sort_keys=True).encode()).hexdigest()
  if any(len(f)!=4 for f in p['faces']):raise ValueError('Editable source is not all quads')
 payload=dict(status='STRUCTURAL_TRAINING_CANDIDATE_NOT_MANUFACTURING_CAD',appearance_pass=False,physics_pass=False,manufacturing_pass=False,parts=parts)
 (cad/'scene.json').write_text(json.dumps(payload,separators=(',',':'))+'\n')
 # Standard URDF keeps full inertial tensors. Simulator-specific actuator,
 # collision exclusions, contact solver and armature are carried in SI JSON.
 urdf=ET.Element('robot',name='goose_stage_one_18axis');world=ET.SubElement(urdf,'link',name='world')
 root=ET.SubElement(urdf,'joint',name='root',type='floating');ET.SubElement(root,'parent',link='world');ET.SubElement(root,'child',link='torso');ET.SubElement(root,'origin',xyz=vec(c['root_origin_at_zero_m']),rpy='0 0 0')
 links={}
 for b in c['bodies']:
  node=ET.SubElement(urdf,'link',name=b['name']);links[b['name']]=node;i=ET.SubElement(node,'inertial');ET.SubElement(i,'origin',xyz=vec(b['com_local_m']),rpy='0 0 0');ET.SubElement(i,'mass',value=str(b['mass_kg']));I=np.array(b['inertia_at_com_body_kg_m2']);ET.SubElement(i,'inertia',ixx=str(I[0,0]),iyy=str(I[1,1]),izz=str(I[2,2]),ixy=str(I[0,1]),ixz=str(I[0,2]),iyz=str(I[1,2]))
 for j in c['joints']:
  n=ET.SubElement(urdf,'joint',name=j['name'],type='revolute');ET.SubElement(n,'parent',link=j['parent']);ET.SubElement(n,'child',link=j['name']);ET.SubElement(n,'origin',xyz=vec(s.pivots[j['name']]-s.pivots[j['parent']]),rpy='0 0 0');ET.SubElement(n,'axis',xyz=vec(j['axis_parent']));ET.SubElement(n,'limit',lower=str(j['range_rad'][0]),upper=str(j['range_rad'][1]),effort=str(j['torque_peak_limit_nm']),velocity=str(j['speed_limit_rad_s']));ET.SubElement(n,'dynamics',damping=str(j['damping_nm_s_rad']),friction=str(j['frictionloss_nm']))
 xml=ET.parse(OUT/'robot.xml');mesh_files={m.attrib['name']:m.attrib['file'] for m in xml.findall('./asset/mesh')}
 for g in c['collision_geometries']:
  is_collision=g.get('contype','1')!='0'
  modes=['collision'] if g.get('group')=='3' else (['visual','collision'] if is_collision else ['visual'])
  for mode in modes:
   node=ET.SubElement(links[g['body']],mode,name=g['name']);pos=np.array([float(v) for v in g.get('pos','0 0 0').split()]);rpy=np.zeros(3);geom=ET.SubElement(node,'geometry');kind=g['type']
   if kind=='mesh':ET.SubElement(geom,'mesh',filename='assets/'+mesh_files[g['mesh']])
   elif kind=='cylinder':
    ft=np.array([float(v) for v in g['fromto'].split()]).reshape(2,3);pos=ft.mean(0);delta=ft[1]-ft[0];rot=trimesh.geometry.align_vectors([0,0,1],delta);rpy=Rotation.from_matrix(rot[:3,:3]).as_euler('xyz');ET.SubElement(geom,'cylinder',radius=g['size'],length=str(np.linalg.norm(delta)))
   elif kind=='ellipsoid':
    # URDF has no ellipsoid primitive. Keep analytic dimensions in the SI
    # contract; this tessellated proxy is only an interchange approximation.
    asset=g['name']+'.obj';m=trimesh.creation.icosphere(subdivisions=3);m.vertices*=np.array([float(v) for v in g['size'].split()]);m.export(OUT/'assets'/asset);ET.SubElement(geom,'mesh',filename='assets/'+asset)
   else:raise ValueError(kind)
   ET.SubElement(node,'origin',xyz=vec(pos),rpy=vec(rpy))
   if mode=='visual':mat=ET.SubElement(node,'material',name=g['name']+'_material');ET.SubElement(mat,'color',rgba=g.get('rgba','.7 .7 .7 1'))
 ET.indent(urdf);(OUT/'robot.urdf').write_text(ET.tostring(urdf,encoding='unicode')+'\n')
 # Inspectable flat tables, generated from the authoritative contract.
 for filename,records in [('stage_one_joints.csv',c['joints']),('stage_one_bodies.csv',c['bodies'])]:
  with (R/'configs'/filename).open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows({k:json.dumps(v,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in records)
 allv=np.vstack([p['vertices'] for p in parts]);shellv=np.vstack([p['vertices'] for p in parts if p['group'] in ('shell','wing_right','wing_left')]);feet={}
 for side in ('right','left'):
  h=s.contact_hulls[side];feet[side]=dict(support_polygon_world_xy_m=h.points[h.vertices].tolist(),plane_z_m=.0005)
 spans={n:float(np.linalg.norm(s.pivots[b]-s.pivots[a])) for n,a,b in [('lower_neck','neck_pitch','neck_mid_pitch'),('upper_neck','neck_mid_pitch','head_pitch'),('thigh','left_hip_pitch','left_knee_pitch'),('shin','left_knee_pitch','left_ankle_pitch')]}
 reserve=[dict(name='battery_service',center_m=[-.07,0,.28],size_m=[.12,.065,.05],mass_kg=.4,sku='CNHL 220406BK',source='https://chinahobbyline.com/products/cnhl-black-series-2200mah-6s-22-2v-40c-lipo-battery-with-xt60-plug',supplier_size_m=[.108,.055,.035],supplier_mass_kg=.372),dict(name='compute_stack',center_m=[-.06,0,.345],size_m=[.08,.048,.032],mass_kg=.054),dict(name='logic_buck',center_m=[-.063,.055,.322],size_m=[.049,.029,.022],mass_kg=.025),dict(name='servo_buck',center_m=[-.063,-.055,.322],size_m=[.049,.029,.022],mass_kg=.04),dict(name='main_protection',center_m=[.083,0,.301],size_m=[.044,.048,.038],mass_kg=.093),dict(name='interfaces_audio',center_m=[.025,0,.250],size_m=[.044,.052,.032],mass_kg=.1023)]
 overlaps=[]
 for k,a in enumerate(reserve):
  for b in reserve[k+1:]:
   overlap=(np.array(a['size_m'])+b['size_m'])/2-abs(np.array(a['center_m'])-b['center_m'])
   if np.all(overlap>0):overlaps.append([a['name'],b['name'],overlap.tolist()])
 counts=Counter(s.selected.values());hardware=[dict(model=s.catalog[k]['model'],quantity=v,unit_mass_kg=s.catalog[k]['mass'],unit_usd_public_reference=s.catalog[k]['usd'],url=s.catalog[k]['url'],status='proposed architecture; China stock/quotation pending') for k,v in counts.items()]
 hardware.extend([dict(model='XM540-W270-T beak motor',quantity=1,unit_mass_kg=.165,unit_usd_public_reference=419.9,url='https://en.robotis.com/shop_en/item.php?it_id=902-0137-000',status='retained candidate; continuous output and custom 3:1 gears NOT verified'),dict(model='XC330-M288-T head roll',quantity=1,unit_mass_kg=.023,unit_usd_public_reference=89.9,url='https://en.robotis.com/shop_en/item.php?it_id=902-0173-000',status='retained candidate; torque screen NOT measured rating')])
 with (R/'hardware/stage_one_actuator_bom.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(hardware[0]),lineterminator='\n');w.writeheader();w.writerows(hardware)
 spec=dict(schema='goose_structure_stage_one_v1',status='PARAMETER_BASELINE_FOR_INITIAL_TRAINING_NOT_HARDWARE_FREEZE',contract_sha256=hashlib.sha256((R/'configs/stage_one_contract.json').read_bytes()).hexdigest(),overall_visual_aabb_m=[allv.min(0).tolist(),allv.max(0).tolist()],torso_visual_aabb_m=[shellv.min(0).tolist(),shellv.max(0).tolist()],link_axis_distances_m=spans,hip_pitch_spacing_m=.178,feet=feet,printed_shell_wall_m=.0024,paired_fork=dict(material='aluminium, white paint; 6061-T6 candidate',plate_thickness_m=.0055,plate_center_spacing_m=.0665,motor_axial_clearance_each_side_m=.00225,bridges='relocated halfway between endpoint motors; do not span through a shaft',strength_status='section screening only, holes/contact loads/FEA not released'),backend_basis_maps={'godot_jolt':[[0,-1,0],[0,0,1],[-1,0,0]],'bevy':[[0,-1,0],[0,0,1],[-1,0,0]],'unity':[[0,-1,0],[0,0,1],[1,0,0]]},backend_vector_rule='polar vectors p,v: C*v; axial vectors angular velocity/torque: det(C)*C*v; tensors: C*I*C^T; confirm native joint sign via FK conformance before applying drives',component_reservations=reserve,electronics_reservation_aabb_overlaps=overlaps,actuator_counts=dict(counts),actuator_usd_reference_total=sum(r['quantity']*r['unit_usd_public_reference'] for r in hardware),power=dict(main_bus='6S LiPo 22.2V nominal, 25.2V full; AK V3 supply limits/regeneration protection require vendor/manual confirmation before purchase',capacity_wh=48.84,logic_rail_v=5,servo_rail_v=12,mechanical_positive_power_controller_limit_w=350,design_main_current_a=40,current_is_design_requirement_not_validated_rating=True,ttl_axes=2,can_axes=16,can_buses=2,can_update_hz=200,policy_hz=50),change_budget=dict(joint_order_axis_contact_shape='immutable within this experiment version; revise version if changed',mass_com_inertia='per body values/ranges in stage_one_contract.json; combined mass budget is not a statistical confidence interval',details_allowed='PCB topology/holes/fasteners may change only while meeting body mass/COM/inertia, clearance, stiffness and power budgets',outside_budget='regenerate model, collision/inertia tests and policy robustness validation; retraining may be needed'),open_structural_items=['Jaw reduction gear set and sustained bite output are not selected/validated; head mass allocation must not be silently exceeded','Actual 6S voltage window, regenerative energy handling and branch power protection remain to be confirmed','Fork/motor mounting and hollow-shell openings are not manufacturing drawings; preserve allocated joint axes and envelope','Low reach has geometric clearance; simple joint interpolation is not a validated ground-pick controller'],quad_source_parts=len(parts),quad_source_faces=sum(len(p['faces']) for p in parts),all_editable_faces_quads=True)
 (R/'configs/stage_one_structure.json').write_text(json.dumps(spec,indent=2)+'\n');print(json.dumps({k:spec[k] for k in ('overall_visual_aabb_m','link_axis_distances_m','actuator_counts','actuator_usd_reference_total','electronics_reservation_aabb_overlaps','quad_source_parts','quad_source_faces')},indent=2))
if __name__=='__main__':main()
