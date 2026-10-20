"""Preserve the exact08 material during private native re-tessellation review."""
from pathlib import Path
import copy,hashlib,json,mmap,struct
W=Path(__file__).resolve().parents[2];E=W/'robots/goose_v0_2/evidence/display_surface_audit_012/c01';o=json.loads((E/'review_native_override.json').read_text());old=W/o['scene']['repository_path'];source=Path(json.loads((W/'robots/goose_v0_2/evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json').read_text())['scene']['path'])
def ident(p):return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
with source.open('rb')as f:
 mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);ln,_=struct.unpack_from('<II',mm,12);src=json.loads(mm[20:20+ln]);mm.close()
raw=old.read_bytes();ln,_=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+ln]);bo=28+ln;bs,_=struct.unpack_from('<II',raw,20+ln);binary=raw[bo:bo+bs];mats={}
for f in o['sources']:
 name=f['name'];rows=[src['materials'][p['material']]for n in src['nodes']if n.get('name')==name for p in src['meshes'][n['mesh']]['primitives']];unique={json.dumps({k:v for k,v in m.items()if k!='name'},sort_keys=True)for m in rows};assert len(unique)==1;new=copy.deepcopy(rows[0]);new['name']='exact08_'+name;mats[name]=len(doc['materials']);doc['materials'].append(new)
for node in doc['nodes']:
 if node.get('name')in mats:
  for p in doc['meshes'][node['mesh']]['primitives']:p['material']=mats[node['name']]
j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary+=b'\0'*((-len(binary))%4);target=old.with_name('seven_same08_native_skins_same_material_review.glb');target.write_bytes(struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary)
o['scene']=dict(repository_path=str(target.relative_to(W)),sha256=ident(target)['sha256'],bytes=target.stat().st_size);o['material_binding']=dict(source08_scene=ident(source),native_export_stage=ident(old),stage_reason='Native exporter interprets Color inputs as sRGB; directly passing stored linear glTF colors darkens a review. Final private GLB reuses exact source material dictionaries, including doubleSided and roughness. No normal, transform, vertex, index or native source changed.',BIN_geometry_index_normal_bytes_exact=True,position_normal_index_accessor_metadata_unchanged=True,source_materials_by_name={n:doc['materials'][i]for n,i in mats.items()},source_script=ident(Path(__file__)))
(E/'review_same_material_override.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps(dict(GLB=ident(target),override=ident(E/'review_same_material_override.json'))))
