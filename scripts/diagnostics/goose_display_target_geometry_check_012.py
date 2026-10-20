"""Native-bound target mesh checks, independent of projected edge-on triangles."""
from pathlib import Path
import hashlib,json,mmap,os,resource,struct,sys
import numpy as np
from cadgen import build123d as bd
from OCP.BRepAdaptor import BRepAdaptor_Surface
W=Path(__file__).resolve().parents[2];E=W/'robots/goose_v0_2/evidence/display_surface_audit_012/c01';A=W/'artifacts/goose_v0_2/display_surface_audit_012/c01';sys.path.insert(0,str(W/'scripts/models'))
from render_goose_reference_camera import load_glb
os.sched_setaffinity(0,{18});resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
def ident(p):return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
override=json.loads((E/'review_same_material_override.json').read_text());facts={r['name']:r for r in override['sources']};source=Path(json.loads((W/'robots/goose_v0_2/evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json').read_text())['scene']['path']);fresh=W/override['scene']['repository_path']
stream=source.open('rb');mm=mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ);ln,_=struct.unpack_from('<II',mm,12);doc=json.loads(mm[20:20+ln]);bo=28+ln
def acc(i):
 a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];dt={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']];n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];size=np.dtype(dt).itemsize;off=bo+v.get('byteOffset',0)+a.get('byteOffset',0);return np.ndarray((a['count'],n),dtype=dt,buffer=mm,offset=off,strides=(v.get('byteStride',n*size),size))
group={name:dict(v=[],f=[],n=[])for name in facts};basis=np.array([[1,0,0],[0,0,-1],[0,1,0]])
for node in doc['nodes']:
 if node.get('name')not in group or'mesh'not in node:continue
 g=group[node['name']];T=np.array(node['matrix']).reshape(4,4,order='F')
 for p in doc['meshes'][node['mesh']]['primitives']:
  v=(acc(p['attributes']['POSITION']).astype(float)@T[:3,:3].T+T[:3,3])@basis.T*1000;ix=acc(p['indices']).reshape(-1,3).astype(int);off=sum(len(a)for a in g['v']);g['v'].append(v);g['f'].append(ix+off);g['n'].append(acc(p['attributes']['NORMAL']).astype(float)@np.linalg.inv(T[:3,:3])@basis.T)
fr={name:dict(v=[],f=[],n=[])for name in facts}
for p in load_glb(fresh.read_bytes()):
 g=fr[p['name']];off=sum(len(a)for a in g['v']);g['v'].append(p['vertices']);g['f'].append(p['indices']+off);g['n'].append(p['normals'])
def metrics(g,fact):
 v=np.vstack(g['v']);f=np.vstack(g['f']);n=np.vstack(g['n']);tri=v[f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)/2;ln=np.linalg.norm(n,axis=1);avg=n[f].sum(1);dots=np.einsum('ij,ij->i',cross,avg);valid=(area>1e-8)&(np.linalg.norm(avg,axis=1)>1e-10)
 _,inv=np.unique(np.round(v*1e6).astype(np.int64),axis=0,return_inverse=True);canon=np.sort(inv[f],axis=1);_,counts=np.unique(canon,axis=0,return_counts=True);bb=np.array(fact['native_bbox_mm']);out=np.max(np.maximum(bb[0]-v,v-bb[1]),axis=1)
 opposed=np.flatnonzero(valid&(dots<0));zero=np.flatnonzero(area<1e-10)
 return dict(vertices=len(v),triangles=len(f),zero_3D_area_triangles=int(len(zero)),zero_area_samples=[dict(area_mm2=float(area[k]),triangle_world_mm=tri[k].tolist())for k in zero[:10]],duplicate_exact_position_triangles_excess=int(sum(counts-1)),nonfinite_positions=int(np.count_nonzero(~np.isfinite(v))),nonfinite_normals=int(np.count_nonzero(~np.isfinite(n))),zero_length_normals=int(np.count_nonzero(ln<1e-12)),opposed_face_winding_vs_average_normal=int(len(opposed)),opposed_samples=[dict(area_mm2=float(area[k]),normal_cosine=float(dots[k]/np.linalg.norm(cross[k])/np.linalg.norm(avg[k])),triangle_world_mm=tri[k].tolist())for k in opposed[:10]],max_vertex_outside_native_bbox_mm=float(max(0,out.max())),world_bbox_mm=[v.min(0).tolist(),v.max(0).tolist()])
r=dict(schema='same08_native_selected_skin_display_audit_012',source08=ident(source),fresh_native_review=ident(fresh),parts={},visible_native_witnesses=[],geometry_or_MCI_changed=False,physics_steps=0,source_script=ident(Path(__file__)))
for name in facts:r['parts'][name]=dict(native=facts[name]['native'],source08=metrics(group[name],facts[name]),independent_native_retessellation=metrics(fr[name],facts[name]))
probe=json.loads((A/'independent08/source_accessor_diagnostic.json').read_text())
for roi in probe['regions']:
 hit=roi['centre_visible_hit']
 if not hit or hit['name']not in facts:continue
 fact=facts[hit['name']];p=Path(fact['native']['path']);assert ident(p)['sha256']==fact['native']['sha256'];shape=bd.import_brep(p);tri=np.array(hit['world_triangle_mm']);pts=[*tri,tri.mean(0)]
 ds=[float(shape.distance_to(bd.Vertex(*q)))for q in pts];center=bd.Vertex(*tri.mean(0));fd=sorted((float(f.distance_to(center)),i,f)for i,f in enumerate(shape.faces(),1));dist,i,face=fd[0];bb=face.bounding_box();row=dict(index=roi['index'],name=hit['name'],native=fact['native'],sample_triangle_world_mm=tri.tolist(),vertex_and_centroid_distances_to_native_mm=ds,closest_native_face_index=i,closest_native_face_type=str(face.geom_type),closest_face_bbox_mm=[list(bb.min),list(bb.max)],closest_face_area_mm2=float(face.area),face_distance_mm=dist)
 if face.geom_type==bd.GeomType.SPHERE:
  s=BRepAdaptor_Surface(face.wrapped,True).Sphere();q=s.Location();row.update(sphere_radius_mm=s.Radius(),sphere_center_mm=[q.X(),q.Y(),q.Z()])
 if face.geom_type==bd.GeomType.PLANE:
  p=BRepAdaptor_Surface(face.wrapped,True).Plane();u=p.Axis().Direction();row['plane_normal']=[u.X(),u.Y(),u.Z()]
 r['visible_native_witnesses'].append(row)
(E/'selected_mesh_native_readback.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(report=ident(E/'selected_mesh_native_readback.json'),witnesses=r['visible_native_witnesses'],part_counts={n:{k:(v[k]['triangles'],v[k]['zero_3D_area_triangles'],v[k]['duplicate_exact_position_triangles_excess'])for k in ['source08','independent_native_retessellation']}for n,v in r['parts'].items()})),flush=True)
