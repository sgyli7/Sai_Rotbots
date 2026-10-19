"""UniqueF immutable07 ->08 native motor/Oldham source integration, zero steps."""
import argparse,copy,gzip,json,os,resource,shutil,struct,sys,time
from pathlib import Path
import numpy as np
from goose_drag_hardware_integration_009_06 import W,R,sha,ident,read,save
BASE=R/'models/physics_v0_2_20261020_07_candidate';PACKAGE=R/'models/physics_v0_2_20261020_08_candidate';CAD=R/'cad/source/drag_hardware_integration_009_08';EXPORT=R/'cad/exports/drag_hardware_integration_009_08';EV=R/'evidence/drag_hardware_integration_009_08';RAW=W/'artifacts/goose_v0_2/drag_hardware_sprint_009/integration08'
INPUT=R/'evidence/hip_yaw_oldham_steel_009/c01/integration_handoff.json';INPUT_SHA='276f17da73e447c513ace550f2ce1d6d201c116ab7a8ed9a7df58ca963ec8614';MANIFEST=INPUT.parent/'manifest.json';MANIFEST_SHA='ee7716dd4c9962332d45924f5cf3924925dfea46a5e43a509ed9c8212cb0dda0';SELECTED=EV/'owner_selected_inputs_08.json'

def selected():
 assert sha(INPUT)==INPUT_SHA and sha(MANIFEST)==MANIFEST_SHA
 d=read(INPUT);manifest=read(MANIFEST)
 for row in manifest['files']:assert sha(row['path'])==row['sha256'],row['path']
 p=d['combined_motor_and_slider_proposal'];motor=Path(p['motor_input_packet']['path']);assert sha(motor)==p['motor_input_packet']['sha256'];rows=[];idx=read(R/'cad/source/drag_hardware_integration_009_07/assembly_index.json');ledger={r['name']:r for r in read(BASE/'mass_ledger.json')['items']};retired=[]
 for r in p['replacement_parts']:
  x=copy.deepcopy(r);x['source_parent_occurrence']=r.get('source_parent_occurrence',r.get('retired_name'));x['retired_native_part_index']=r.get('retired_native_part_index',r.get('retired_native_index06'));x['native']=r.get('native',r.get('source'));x.setdefault('density_kg_m3',None);x['center_of_mass_world_mm']=(np.array(x['center_of_mass_world_m'])*1000).tolist();old=idx['parts'][x['retired_native_part_index']];assert old['name']==x['source_parent_occurrence'] and old['body']==x['body'];assert x['source_parent_occurrence']in ledger;assert sha(x['native']['path'])==x['native']['sha256'];assert np.array_equal(x['source_to_target_world_zero_4x4'],np.eye(4));rows.append(x);retired.append({'name':x['source_parent_occurrence'],'body':x['body'],'index':x['retired_native_part_index'],'mass_kg':ledger[x['source_parent_occurrence']]['mass_kg']})
 assert len(rows)==6 and sum(x['mass_kg']for x in rows)-sum(x['mass_kg']for x in retired)>0
 result={'candidate_id':PACKAGE.name,'status':'ROOT_ADOPTED_FINITE_STATIC_HARDWARE_PROTOTYPE_NOT_ACTUAL_AUTHORIZATION','source_handoff':ident(INPUT),'source_manifest':ident(MANIFEST),'source_motor_packet':ident(motor),'parent07':ident(BASE/'manifest.json'),'replacement_parts':rows,'retired_occurrences':retired,'drive_changes':p['proposed_actuator_changes_NOT_applied'],'mass_delta_kg':p['nominal_mass_delta_kg'],'Owner_chain_hard_cap_all_modes_Nm':1.8,'peak_enabled':False,'public_axes_PD_timing_350W_voltage28contacts_unchanged':True,'COTS_MCI_grade':'Supplier262g total and explicit external-volume allocation; estimated COM/fullI, not internal OEM solid or measured material density. Reflected rotor inertia is separate once at actual input coordinate.','source':ident(__file__),'mj_step_calls':0};save(SELECTED,result);return result

def native():
 from cadgen import build123d as bd
 sys.path.insert(0,str(W/'scripts/cad'));from goose_drag_leg_structure_009 import quality
 os.sched_setaffinity(0,{7});resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));t=time.monotonic();p=selected();parent=R/'cad/source/drag_hardware_integration_009_07/assembly_index.json';idx=read(parent);n=W/'artifacts/goose_v0_2/drag_hardware_sprint_009/integration07/whole_candidate_07/goose_drag_hardware_integration_009_07.brep';assert sha(n)==idx['uncompressed_native_sha256'];parts=list(bd.import_brep(n).solids());rows=copy.deepcopy(idx['parts']);assert len(parts)==len(rows)==1827;checks=[];EXPORT.mkdir(parents=True,exist_ok=True);CAD.mkdir(parents=True,exist_ok=True)
 for r in p['replacement_parts']:
  s=bd.import_brep(r['native']['path']);q=quality(s);assert q['strict_valid'] and q['self_intersection_valid'] and q['solid_count']==1;qvol=float(s.volume);assert abs(qvol-r['native_volume_mm3'])<.01
  s=s.solids()[0];s.label=r['name'];i=r['retired_native_part_index'];parts[i]=s;rows[i]={**r,'native_part_index':i,'source_parent_index':i,'integration_origin':'Root_selected08_realAK45_and_H900','native_readback_quality':q};glb=EXPORT/(r['name']+'.glb');bd.export_gltf(bd.Compound(children=[s]),glb,binary=True,linear_deflection=.02,angular_deflection=.05);step=EXPORT/(r['name']+'.step');bd.export_step(s,step);again=bd.import_step(step);qs=quality(again);assert len(again.solids())==1 and abs(float(again.volume)-qvol)<.01;checks.append({'name':r['name'],'body':r['body'],'native':r['native'],'strict_SI':q,'volume_mm3':qvol,'MCI_source':{'mass_kg':r['mass_kg'],'COM_m':r['center_of_mass_world_m'],'fullI_kg_m2':r['inertia_at_com_world_kg_m2'],'density_kg_m3':r['density_kg_m3'],'not_measured':True},'source_shape_not_modified':True,'GLB':ident(glb),'STEP':ident(step),'STEP_readback':{'solid_count':1,'strict_valid':qs['strict_valid'],'SI_valid':qs['self_intersection_valid'],'volume_error_mm3':float(again.volume)-qvol}})
 whole=RAW/'goose_drag_hardware_integration_009_08.brep';bd.export_brep(bd.Compound(children=parts),whole);loaded=list(bd.import_brep(whole).solids());assert len(loaded)==1827;errors=[]
 for i,(a,b)in enumerate(zip(parts,loaded,strict=True)):
  e=abs(float(a.volume)-float(b.volume))
  if e>max(.02,abs(float(a.volume))*1e-7):errors.append([i,e])
 assert not errors,errors
 gz=CAD/'goose_drag_hardware_integration_009_08.brep.gz'
 with whole.open('rb')as src,gz.open('wb')as dst:
  with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0)as stream:shutil.copyfileobj(src,stream)
 result={'schema':'goose08_actual_native_whole_source_v1','candidate_id':PACKAGE.name,'native_parts':1827,'parts':rows,'native':ident(gz),'uncompressed_native_sha256':sha(whole),'parent07_native_index':ident(parent),'selected_inputs':ident(SELECTED),'actual_replacement_checks':checks,'all1827_volume_readbacks_pass':True,'source_zero_frame':'NativeCADmm,+Xforward/+Yleft/+Zup,identity placements.','source':ident(__file__),'elapsed_s':time.monotonic()-t,'mj_step_calls':0};save(CAD/'assembly_index.json',result);save(EV/'native_readback_08.json',{k:v for k,v in result.items()if k!='parts'});print({'stage':'native','native_solids':1827,'elapsed_s':result['elapsed_s']},flush=True)

def visual():
 from goose_drag_hardware_integration_009 import glb_header,flattened_nodes
 os.sched_setaffinity(0,{6});resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));p=read(SELECTED);pb=R/'evidence/drag_hardware_integration_009_07/actual_visual_binding_07_final.json';binding=read(pb);parent=Path(binding['scene']['path']);assert sha(parent)==binding['scene']['sha256'];doc,off,length=glb_header(parent);result=copy.deepcopy(doc);nodes=flattened_nodes(doc);blocks=[(parent,off,length)];records=[]
 for r in p['replacement_parts']:
  oldname=r['source_parent_occurrence'];name=r['name'];path=EXPORT/(name+'.glb');old=next(n for n in nodes if n['name']==oldname);pack,po,pl=glb_header(path);pn=flattened_nodes(pack);assert len(pn)==1;new=pn[0];oldmaterials={x.get('material')for x in result['meshes'][old['mesh']]['primitives']};assert len(oldmaterials)==1;material=next(iter(oldmaterials));vi,ai,mi=len(result['bufferViews']),len(result['accessors']),len(result['meshes'])
  for v in pack['bufferViews']:
   v=copy.deepcopy(v);v['byteOffset']=v.get('byteOffset',0)+sum(b[2]for b in blocks);result['bufferViews'].append(v)
  for a in pack['accessors']:
   a=copy.deepcopy(a);a['bufferView']+=vi;result['accessors'].append(a)
  mesh=copy.deepcopy(pack['meshes'][new['mesh']])
  for a in mesh['primitives']:a['attributes']={k:v+ai for k,v in a['attributes'].items()};a['indices']+=ai;a['material']=material
  result['meshes'].append(mesh);new['mesh']=mi;new['name']=name;nodes=[new if n['name']==oldname else n for n in nodes];blocks.append((path,po,pl));binding['occurrence_owners'].pop(oldname);binding['occurrence_owners'][name]=r['body'];records.append({'retired':oldname,'new':name,'owner':r['body'],'source_native':r['native'],'source_GLB':ident(path),'complete_source_mesh':True,'source_node_matrix_preserved':True,'parent_material_index_preserved':material})
 result['nodes']=nodes;result['scenes']=[{'nodes':list(range(len(nodes)))}];result['scene']=0;length=sum(b[2]for b in blocks);result['buffers']=[{'byteLength':length}];encoded=json.dumps(result,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);dest=RAW/'goose_drag_hardware_integration_009_08_actual_appearance.glb'
 with dest.open('wb')as f:
  f.write(struct.pack('<4sII',b'glTF',2,28+len(encoded)+length));f.write(struct.pack('<II',len(encoded),0x4e4f534a));f.write(encoded);f.write(struct.pack('<II',length,0x004e4942))
  for path,offset,size in blocks:
   with path.open('rb')as src:
    src.seek(offset)
    while size:
     b=src.read(min(1024**2,size));assert b;f.write(b);size-=len(b)
 assert glb_header(dest)[0]==result;binding.update(scene=ident(dest),native_assembly=ident(CAD/'assembly_index.json'),parent_display_binding=ident(pb),display_revision='08_realAK45two_motor_and_same_geometry_H900_slider',approved_native_replacements=records,display_occurrences=len(nodes),all_other_occurrences_and_original_BIN_preserved=True,source=ident(__file__),actual_steps=0);save(EV/'actual_visual_binding_08_preliminary.json',binding);print({'stage':'visual','occurrences':len(nodes),'scene':ident(dest)},flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--stage',choices=['native','visual'],required=True);v=a.parse_args();RAW.mkdir(parents=True,exist_ok=True);EV.mkdir(parents=True,exist_ok=True);{'native':native,'visual':visual}[v.stage]()
