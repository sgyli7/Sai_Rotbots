"""Review-only re-tessellation of seven exact08 native skin parts. No CAD edit."""
from pathlib import Path
import copy,hashlib,json,mmap,os,resource,struct,sys,time
import numpy as np
from cadgen import build123d as bd
from OCP.BRepAlgoAPI import BRepAlgoAPI_Check
from OCP.BRepCheck import BRepCheck_Analyzer
W=Path(__file__).resolve().parents[2];sys.path.insert(0,str(W/'scripts/models'))
from render_goose_reference_camera import load_glb
O=W/'artifacts/goose_v0_2/display_surface_audit_012/c01';O.mkdir(parents=True,exist_ok=True)
X=W/'robots/goose_v0_2/cad/exports/display_surface_audit_012/c01';X.mkdir(parents=True,exist_ok=False)
E=W/'robots/goose_v0_2/evidence/display_surface_audit_012/c01';E.mkdir(parents=True,exist_ok=True)
def ident(p):return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def resolve(r):
    p=Path(r.get('path',r.get('repository_path')));return p if p.is_absolute()else W/p
os.sched_setaffinity(0,{18});resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));start=time.monotonic()
idx=W/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json';allrows=json.loads(idx.read_text())['parts']
selected=[r for r in allrows if r['name']=='front_main_shell'or'_integrated_AR_shoe_crown_continuous_'in r['name']or'_coaxial_service_shell_clearance_009_c09'in r['name']]
assert len(selected)==7
bind=W/'robots/goose_v0_2/evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json';binding=json.loads(bind.read_text());scene=resolve(binding['scene']);assert ident(scene)['sha256']==binding['scene']['sha256']
with scene.open('rb')as f:
    mm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ);ln,kind=struct.unpack_from('<II',mm,12);doc=json.loads(mm[20:20+ln]);mm.close()
colors={}
for n in doc['nodes']:
    if n.get('name')in [r['name']for r in selected]and'mesh'in n:
        pp=doc['meshes'][n['mesh']]['primitives'];p=pp[0];colors[n['name']]=doc['materials'][p['material']]['pbrMetallicRoughness']['baseColorFactor'][:3]
shapes=[];facts=[]
for r in selected:
    ref=r.get('source_native',r.get('native'));p=resolve(ref);assert ident(p)['sha256']==ref['sha256'];s=bd.import_brep(p);q=BRepAlgoAPI_Check(s.wrapped,True,True);solids=list(s.solids());assert len(solids)==1
    s.label=r['name'];s.color=bd.Color(*colors[r['name']]);b=s.bounding_box();facts.append(dict(name=r['name'],body=r['body'],native=ident(p),native_strict=BRepCheck_Analyzer(s.wrapped,True,False,True).IsValid(),native_SI=q.IsValid(),native_solid_count=len(solids),native_volume_mm3=sum(x.volume for x in solids),native_bbox_mm=[list(b.min),list(b.max)],source_material_RGBA=colors[r['name']]+[1.],source_index=r['native_part_index'],native_edited=False));shapes.append(s)
compound=bd.Compound(children=[copy.deepcopy(s)for s in shapes]);g=X/'seven_same08_native_skins_review.glb';bd.export_gltf(compound,g,binary=True,linear_deflection=.06,angular_deflection=.15)
parts=load_glb(g.read_bytes());names={p['name']for p in parts};assert names=={r['name']for r in selected},names
for f in facts:
    vs=np.vstack([p['vertices']for p in parts if p['name']==f['name']]);bb=np.array(f['native_bbox_mm']);outside=np.max(np.maximum(bb[0]-vs,vs-bb[1]),axis=1)
    f.update(review_display_vertices=len(vs),review_display_bbox_mm=[vs.min(0).tolist(),vs.max(0).tolist()],max_vertex_outside_native_bbox_mm=float(max(0,outside.max())),bbox_difference_max_mm=float(abs(np.array([vs.min(0),vs.max(0)])-bb).max()))
    assert f['native_strict']and f['native_SI']and f['max_vertex_outside_native_bbox_mm']<.15
override=dict(scene=dict(repository_path=str(g.relative_to(W)),sha256=ident(g)['sha256'],bytes=g.stat().st_size),sources=facts,review_only=True,source08_native_index=ident(idx),source08_visual_binding=ident(bind),native_BRep_and_MCI_and_runtime_changed=False,export=dict(linear_deflection_mm=.06,angular_deflection_rad=.15,Compound_root_preserves_native_world_zero=True),elapsed_s=time.monotonic()-start,source_script=ident(Path(__file__)))
save(E/'review_native_override.json',override);print(json.dumps(dict(GLB=ident(g),sources=[dict(name=f['name'],bboxerr=f['bbox_difference_max_mm'],strict=f['native_strict'])for f in facts],elapsed=override['elapsed_s'])),flush=True)
