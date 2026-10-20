"""Read-only independent GLB/accessor and four-region depth diagnostic; no CAD/physics edits."""
from __future__ import annotations
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import argparse,hashlib,json,mmap,struct,sys,tempfile,resource,time
import numpy as np
from PIL import Image,ImageDraw
W=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(W/'scripts/models'))
from render_goose_reference_camera import Rasterizer,load_glb

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def cross2(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]

def main():
 os.sched_setaffinity(0,[18]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=W/'artifacts/goose_v0_2/display_surface_audit_012/c01/independent08');ap.add_argument('--review',type=Path,default=W/'robots/goose_v0_2/images/drag_hardware_integration_009_08/whole_source_review_01/visual_review.json');a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 review_path=a.review;review=json.loads(review_path.read_text());source=W/review['scene']['repository_path'];board_path=W/review['board']['repository_path'];binding=json.loads((W/review['binding']['repository_path']).read_text());started=time.monotonic()
 source_sha=sha(source);assert source_sha==review['scene']['sha256']
 stream=source.open('rb');mm=mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ);jsize,kind=struct.unpack_from('<II',mm,12);doc=json.loads(mm[20:20+jsize]);binsize,kind=struct.unpack_from('<II',mm,20+jsize);bo=28+jsize
 assert bo+binsize==len(mm) and kind==0x004e4942
 def acc(ix):
  r=doc['accessors'][ix];v=doc['bufferViews'][r['bufferView']];dt={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[r['componentType']];n={'SCALAR':1,'VEC3':3,'VEC4':4}[r['type']];item=np.dtype(dt).itemsize;stride=v.get('byteStride',n*item);off=bo+v.get('byteOffset',0)+r.get('byteOffset',0)
  assert v.get('buffer',0)==0 and off+(r['count']-1)*stride+n*item<=bo+v.get('byteOffset',0)+v['byteLength']
  return np.ndarray((r['count'],n),dtype=dt,buffer=mm,offset=off,strides=(stride,item))
 references={};reference_inputs=[]
 for side in ['left','right']:
  p=W/'robots/goose_v0_2/cad/exports/drag_foot_clearance_009/c09'/side/'foot_clearance.glb';parts=load_glb(p.read_bytes());reference_inputs.append({'path':str(p),'SHA256':sha(p),'qualification':'F independently matched these saved sources to healthy native c09; bbox comparison is only a sufficient defect witness, not full surface equivalence.'})
  for part in parts:
   n=part['name'];lo,hi=np.array(part['world_bounds_native_mm'])
   if n in references:references[n]=[np.minimum(references[n][0],lo),np.maximum(references[n][1],hi)]
   else:references[n]=[lo,hi]
 points=[('front',[529.2,802.03]),('front',[399.6,615.805]),('right_side',[369.,560.415]),('oblique',[486.9,779.11])]
 views={x['view']:x['camera'] for x in review['views']};basis=np.array([[1,0,0],[0,0,-1],[0,1,0.]])
 # Crop only the viewport. Every source triangle remains in the depth test.
 crops=[]
 for name,point in points:
  matrix=np.array(views[name]['matrix_2x4']);xy=matrix[:,:3]/np.linalg.norm(matrix[:,:3],axis=1)[:,None];rot=np.vstack([xy,np.cross(*xy)]);origin=np.array(point)-[70,90]
  crops.append({'view':name,'point':point,'matrix':matrix,'rotation':rot,'origin':origin,'image':np.full((360,280,3),248,np.uint8),'depth':np.full((360,280),np.inf),'stats':np.zeros(5,np.uint64),'centre_hits':[],'bad_triangles_near_region':[]})
 bads=[];counts={'primitives':0,'triangles':0,'invalid_indices':0,'nonfinite_positions':0,'negative_transform_determinants':0,'position_metadata_mismatches':0,'zero_3D_area_triangles':0,'repeated_index_triangles':0,'duplicate_index_triangles':0,'invalid_NORMAL_values':0};nodes=doc['nodes'];assert all(not n.get('children') for n in nodes),'Expected saved flattened actual source'
 with tempfile.TemporaryDirectory(prefix='goose_surface_depth_') as tmp:
  raster=Rasterizer(tmp)
  for ni,node in enumerate(nodes):
   if 'mesh' not in node:continue
   assert 'matrix'in node and not any(k in node for k in ['rotation','translation','scale'])
   world=np.array(node['matrix']).reshape(4,4,order='F');assert np.allclose(world[3],[0,0,0,1]);det=float(np.linalg.det(world[:3,:3]));counts['negative_transform_determinants']+=int(det<0)
   for pi,pr in enumerate(doc['meshes'][node['mesh']]['primitives']):
    counts['primitives']+=1;raw=acc(pr['attributes']['POSITION']);ind=acc(pr['indices']).reshape(-1).astype(np.uint32).reshape(-1,3);counts['triangles']+=len(ind)
    if not np.isfinite(raw).all():counts['nonfinite_positions']+=1;continue
    if len(ind) and ind.max()>=len(raw):counts['invalid_indices']+=1;continue
    decl=doc['accessors'][pr['attributes']['POSITION']];lo=np.array(decl.get('min',raw.min(0)));hi=np.array(decl.get('max',raw.max(0)));outside=np.any((raw<lo-1e-6)|(raw>hi+1e-6),axis=1);badind=np.flatnonzero(outside)
    vertices=(raw.astype(float)@world[:3,:3].T+world[:3,3])@basis.T*1000;native_bad=np.zeros(len(raw),dtype=bool);native_bounds=None
    if node.get('name')in references:
     nlo,nhi=references[node['name']];native_bounds=[nlo.tolist(),nhi.tolist()];native_bad=np.any((vertices<nlo-.2)|(vertices>nhi+.2),axis=1)
    outside=outside|native_bad;badind=np.flatnonzero(outside);badfaces=np.flatnonzero(np.any(outside[ind],axis=1))
    row=None
    if len(badind):
     metadata_bad=bool(np.any((raw<lo-1e-6)|(raw>hi+1e-6)));counts['position_metadata_mismatches']+=int(metadata_bad);row={'name':node.get('name'),'owner':binding['occurrence_owners'].get(node.get('name')),'primitive':pi,'position_accessor':pr['attributes']['POSITION'],'indices_accessor':pr['indices'],'node_transform_determinant':det,'declared_raw_minmax':[lo.tolist(),hi.tolist()],'actual_raw_minmax':[raw.min(0).tolist(),raw.max(0).tolist()],'metadata_mismatch':metadata_bad,'independent_same_native_bbox_world_mm':native_bounds,'bad_vertex_indices':badind.tolist(),'bad_raw_positions':raw[badind].tolist(),'bad_world_positions_mm':vertices[badind].tolist(),'referenced_bad_triangles':len(badfaces),'sample_triangle_indices':ind[badfaces[:3]].tolist(),'sample_world_triangles_mm':vertices[ind[badfaces[:3]]].tolist()};bads.append(row)
    edges=vertices[ind[:,1:]]-vertices[ind[:,:1]];areas=np.linalg.norm(np.cross(edges[:,0],edges[:,1]),axis=1)/2;counts['zero_3D_area_triangles']+=int(np.count_nonzero(areas<1e-10));counts['repeated_index_triangles']+=int(np.count_nonzero((ind[:,0]==ind[:,1])|(ind[:,1]==ind[:,2])|(ind[:,2]==ind[:,0])));counts['duplicate_index_triangles']+=int(len(ind)-len(np.unique(np.sort(ind,axis=1),axis=0)));
    if 'NORMAL'in pr['attributes']:counts['invalid_NORMAL_values']+=int(np.count_nonzero(~np.isfinite(acc(pr['attributes']['NORMAL']))))
    rv=vertices;ri=ind
    if 'NORMAL'in pr['attributes']:normals=acc(pr['attributes']['NORMAL']).astype(float)@np.linalg.inv(world[:3,:3])@basis.T
    else:
     rv=vertices[ind.reshape(-1)];tri=rv.reshape(-1,3,3);normals=np.repeat(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),3,axis=0);ri=np.arange(len(rv),dtype=np.uint32).reshape(-1,3)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-14);mat=doc.get('materials',[])[pr['material']]if 'material'in pr else {};assert mat.get('alphaMode','OPAQUE')=='OPAQUE';color=np.array(mat.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1]))[:3]
    for c in crops:
     xy=vertices@c['matrix'][:,:3].T+c['matrix'][:,3];depth=vertices@c['rotation'][2];rxy=rv@c['matrix'][:,:3].T+c['matrix'][:,3];attrs=np.column_stack([(rxy-c['origin'])*2,rv@c['rotation'][2],normals@c['rotation'].T,np.broadcast_to(color,(len(rv),3))]);raster.draw(attrs,ri,c['image'],c['depth'],False,0,[0,0],.1,c['stats'])
     tri=xy[ind];pt=np.array(c['point']);near=np.all(tri.max(1)>=pt-[40,40],axis=1)&np.all(tri.min(1)<=pt+[40,40],axis=1)
     if row is not None:
      ids=np.intersect1d(np.flatnonzero(near),badfaces)
      if len(ids):c['bad_triangles_near_region'].append({'name':node['name'],'owner':row['owner'],'primitive':pi,'triangle_count':len(ids),'triangle_ids':ids[:8].tolist(),'sample_world_triangles_mm':vertices[ind[ids[:2]]].tolist()})
     sel=np.flatnonzero(near)
     if len(sel):
      tt=tri[sel];area=cross2(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]);valid=np.abs(area)>1e-12
      with np.errstate(divide='ignore',invalid='ignore'):
       u=cross2(tt[:,1]-pt,tt[:,2]-pt)/area;v=cross2(tt[:,2]-pt,tt[:,0]-pt)/area;z=1-u-v;hit=valid&(u>=-1e-9)&(v>=-1e-9)&(z>=-1e-9)
      ids=sel[hit]
      for h,ti in zip(np.flatnonzero(hit),ids):
       c['centre_hits'].append({'name':node['name'],'owner':binding['occurrence_owners'].get(node['name']),'primitive':pi,'triangle_id':int(ti),'indices':ind[ti].tolist(),'depth_mm':float(np.array([u[h],v[h],z[h]])@depth[ind[ti]]),'source_position_out_of_declared_bounds':bool(ti in badfaces),'world_triangle_mm':vertices[ind[ti]].tolist()})
   if ni%200==0:print(json.dumps({'node':ni,'elapsed_s':time.monotonic()-started,'bad_primitives':len(bads)}),flush=True)
  original=Image.open(board_path);panel=Image.new('RGB',(4*560,405),(248,248,248));draw=ImageDraw.Draw(panel);regions=[]
  for i,c in enumerate(crops):
   column={'front':0,'right_side':1,'oblique':2}[c['view']];x,y=c['origin'];box=(column*900+x,25+y,column*900+x+140,25+y+180);old=original.crop(box).resize((280,360));panel.paste(old,(i*560,28));panel.paste(Image.fromarray(c['image']),(i*560+280,28));draw.text((i*560+5,5),f'{i+1} original | independent reader + same nearest-Z',fill='black');hits=sorted(c['centre_hits'],key=lambda r:r['depth_mm']);regions.append({'index':i+1,'view':c['view'],'local_point_px':c['point'],'centre_visible_hit':hits[0]if hits else None,'bad_source_triangles_in40px_region':c['bad_triangles_near_region'],'depth_buffer_writes':int(c['stats'][3]),'all_triangles_submitted':int(c['stats'][0]),'crop_pixel_difference_count':int(np.any(np.array(old)!=c['image'],axis=2).sum()),'note':'Crop original resized2x differs by interpolation/sampling; use geometric defects, not exact pixel equality, for classification.'})
  panel.save(a.output/'independent_depth_comparison.png')
 out={'status':'READ_ONLY_CURRENT08_SOURCE_ACCESSOR_AND_NEAREST_Z_DIAGNOSTIC_012','source':str(source),'source_SHA256':source_sha,'board_SHA256':sha(board_path),'producer_SHA256':sha(Path(__file__)),'counts':counts,'healthy_same_native_reference_inputs':reference_inputs,'independent_tessellation_bbox_margin_mm':.2,'bbox_margin_scope':'Conservative witness margin exceeds .10+.04mm export deflections; small sample-bbox differences are not labeled geometry corruption. Full CAD surface equivalence is outside this test.','source_bad_accessors':bads,'regions':regions,'renderer':'Existing unchanged Rasterizer C++ nearest per-sample depth buffer. All source triangles rendered; no omitted source or inferred face repair. Independent mmap accessor reader implements declared offsets/strides/transforms.','normal_or_depth_scope':'Both triangle sides rasterized; reversed normals cannot delete triangles in this renderer. No painter-depth sorting.','elapsed_s':time.monotonic()-started,'maxRSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'cpu_affinity':sorted(os.sched_getaffinity(0)),'physics_integrations':0,'CAD_edits':0,'physical_edits':0}
 (a.output/'source_accessor_diagnostic.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({'counts':counts,'bad_names':sorted(set(r['name']for r in bads)),'regions':[{'index':c['index'],'visible':c['centre_visible_hit'],'bad_count':sum(q['triangle_count']for q in c['bad_source_triangles_in40px_region'])}for c in regions],'elapsed_s':out['elapsed_s'],'maxRSS_KiB':out['maxRSS_KiB']},indent=2))

if __name__=='__main__':main()
