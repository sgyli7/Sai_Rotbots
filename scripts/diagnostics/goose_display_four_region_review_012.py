"""Old four user ROIs, current08, and exact-same-native independent CPU render."""
from pathlib import Path
import hashlib,json,os,resource,sys,tempfile
import numpy as np
from PIL import Image,ImageDraw
W=Path(__file__).resolve().parents[2];sys.path.insert(0,str(W/'scripts/models'))
from render_goose_reference_camera import load_glb,render,Rasterizer
os.sched_setaffinity(0,{18});resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
I=W/'robots/goose_v0_2/images/display_surface_audit_012/c01';E=W/'robots/goose_v0_2/evidence/display_surface_audit_012/c01'
def ident(p):return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def read(p):return json.loads(p.read_text())
oldp=W/'robots/goose_v0_2/images/drag_hardware_integration_009/candidate_actual_review/whole_three_views.png';currentp=W/'robots/goose_v0_2/images/drag_hardware_integration_009_08/whole_source_review_01/whole_three_views.png';meta=read(W/'robots/goose_v0_2/images/drag_hardware_integration_009_08/whole_source_review_01/visual_review.json');cameras={r['view']:r['camera']for r in meta['views']};binding=read(W/'robots/goose_v0_2/evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json');scene=Path(binding['scene']['path']);primitives=load_glb(scene.read_bytes());override=read(E/'review_same_material_override.json');fresh=W/override['scene']['repository_path'];extra=load_glb(fresh.read_bytes());names={x['name']for x in primitives};selected={x['name']for x in extra};primitives=[r for r in primitives if r['name']not in selected]+extra;assert {x['name']for x in primitives}==names and len(names)==1974
points=[('front',[529.2,802.03]),('front',[399.6,615.805]),('right_side',[369.,560.415]),('oblique',[486.9,779.11])];old=Image.open(oldp);current=Image.open(currentp);panel=Image.new('RGB',(1680,815),(248,248,248));draw=ImageDraw.Draw(panel);records=[]
with tempfile.TemporaryDirectory(prefix='goose_012_roi_')as temporary:
 raster=Rasterizer(temporary)
 for i,(view,p)in enumerate(points):
  origin=np.array(p)-[70,90];column={'front':0,'right_side':1,'oblique':2}[view];mat=np.array(cameras[view]['matrix_2x4']);mat[:,3]-=origin;mat*=2;camera=dict(kind='orthographic',viewport_px=[280,360],matrix_2x4=mat.tolist());im,metrics,_=render(primitives,camera,280,360,1,.1,raster);path=I/f'point_{i+1}_same08_native_x2.png';im.save(path)
  box=(column*900+origin[0],25+origin[1],column*900+origin[0]+140,25+origin[1]+180);cropold=old.crop(box).resize((280,360));cropcurrent=current.crop(box).resize((280,360));gx=(i%2)*840;gy=(i//2)*400
  for j,(img,label)in enumerate([(cropold,'OLD image'),(cropcurrent,'08 saved display'),(im,'same08 native / fresh mesh')]):panel.paste(img,(gx+j*280,gy+25));draw.text((gx+j*280+6,gy+6),f'P{i+1} {label}',fill='#222222')
  records.append(dict(point=i+1,user_old_board_normalized_xy=[[.196,.866],[.148,.671],[.47,.613],[.847,.842]][i],view=view,old_local_pixel_point=p,old_source_crop_box=box,camera=camera,all1974_occurrences_present=True,omitted_occurrences=[],metrics=metrics,image=ident(path)))
 # Extra observation, outside original four coordinates.
 origin=np.array([300.,535.]);mat=np.array(cameras['front']['matrix_2x4']);mat[:,3]-=origin;mat*=3;camera=dict(kind='orthographic',viewport_px=[900,300],matrix_2x4=mat.tolist());im,metrics,_=render(primitives,camera,900,300,1,.1,raster);bp=I/'extra_blue_front_lower_edge_same_native_x3.png';im.save(bp)
panelpath=I/'four_user_points_old_08_fresh_native.png';panel.save(panelpath)
whole=Image.open(I/'whole_native_same_material/whole_three_views.png');overview=Image.new('RGB',(2700,1825),(248,248,248));overview.paste(whole,(0,0));overview.paste(panel,(510,990));dr=ImageDraw.Draw(overview);dr.text((20,960),'Current08 whole scene, same native + exact08 materials; four original user regions below. No CAD/MCI/physics changes.',fill='#222222');overviewpath=I/'whole_and_four_original_regions.png';overview.save(overviewpath)
out=dict(schema='four_original_user_points_same_native_display_review_012',old_board=ident(oldp),saved08_board=ident(currentp),review_override=ident(E/'review_same_material_override.json'),fresh_whole_review=ident(I/'whole_native_same_material/visual_review.json'),points=records,extra_blue_lower_edge=dict(image=ident(bp),camera=camera,metrics=metrics,not_one_of_original_four=True),comparison_board=ident(panelpath),whole_and_four=ident(overviewpath),source_geometry_or_public08_assets_modified=False,pixel_retouch_or_AI_fill=False,renderer='All source occurrences, CPU nearest-Z; only original-image crops are resized for comparison. Independent native crops are actually rerendered at2x from fixed original camera.',source_script=ident(Path(__file__)))
(E/'four_point_visual_readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(board=ident(panelpath),overview=ident(overviewpath))),flush=True)
