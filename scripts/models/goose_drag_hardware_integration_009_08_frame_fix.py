"""Correct observed single-root GLTF transform export using existing Compound contract."""
import copy,json,os,shutil,sys
from pathlib import Path
import numpy as np
from cadgen import build123d as bd
from goose_drag_hardware_integration_009_08_source import W,R,CAD,EV,RAW,EXPORT,SELECTED,read,save,sha,ident
from render_goose_reference_camera import load_glb
os.sched_setaffinity(0,{7});p=read(SELECTED);failure=RAW/'single_shape_gltf_frame_failure_01';failure.mkdir(exist_ok=True);checks=[]
for r in p['replacement_parts']:
 gp=EXPORT/(r['name']+'.glb');old=ident(failure/gp.name)if(failure/gp.name).exists()else ident(gp);shutil.copyfile(gp,failure/gp.name)if not(failure/gp.name).exists()else None;s=bd.import_brep(r['native']['path']).solids()[0];s.label=r['name'];bd.export_gltf(bd.Compound(children=[s]),gp,binary=True,linear_deflection=.02,angular_deflection=.05);b=s.bounding_box();nb=np.array([list(b.min),list(b.max)]);pr=load_glb(gp.read_bytes());v=np.vstack([x['vertices']for x in pr]);gb=np.array([v.min(0),v.max(0)]);err=float(abs(nb-gb).max());print({'name':r['name'],'compound_bbox_error_mm':err},flush=True);assert err<.02,(nb,gb);assert {x['name']for x in pr}=={r['name']};checks.append({'name':r['name'],'failed_single_shape_GLB':old,'failed_copy':ident(failure/gp.name),'correct_compound_GLB':ident(gp),'same_native':r['native'],'max_bbox_error_mm':err,'native_bbox_mm':nb.tolist(),'correct_GLB_bbox_mm':gb.tolist(),'cause':'SinglelocatedSolidroot GLTF changes source transform; same existing Compound(children=[solid])export usedbyparent assemblies preservesCADframe. No source geometry/MCI ortransforms werealtered.'})
idx=read(CAD/'assembly_index.json');oldindex=copy.deepcopy(idx);save(failure/'original_assembly_index_before_display_frame_correction.json',oldindex)
for row in idx['actual_replacement_checks']:row['GLB']=ident(EXPORT/(row['name']+'.glb'))
idx['display_frame_correction_receipt']=str(EV/'source_GLB_frame_correction_08.json');save(CAD/'assembly_index.json',idx);save(EV/'source_GLB_frame_correction_08.json',{'status':'PASS_CORRECT_SAME_NATIVE_COMPOUND_EXPORT_ALL6','checks':checks,'geometry_material_or_MCI_changed':False,'native_identity_unchanged':True,'rejected_single_shape_export_preserved':True,'source':ident(__file__),'mj_step_calls':0});save(EV/'visual_source_frame_readback_08.json',{'status':'PASS_SIX_REAL_NATIVE_GLB_WORLDZERO_FRAMES','source_checks':checks,'max_bbox_error_mm':max(x['max_bbox_error_mm']for x in checks),'correction_receipt':ident(EV/'source_GLB_frame_correction_08.json'),'mj_step_calls':0})
