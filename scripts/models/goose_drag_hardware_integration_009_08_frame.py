"""Saved08 native-to-actual-display zero-frame verification, no integration."""
import os,sys,numpy as np
from cadgen import build123d as bd
from goose_drag_hardware_integration_009_08_source import W,R,EV,SELECTED,EXPORT,read,save,ident
from render_goose_reference_camera import load_glb
os.sched_setaffinity(0,{7});p=read(SELECTED);rows=[]
for r in p['replacement_parts']:
 s=bd.import_brep(r['native']['path']);b=s.bounding_box();bbox=np.array([list(b.min),list(b.max)]);gp=EXPORT/(r['name']+'.glb');pr=load_glb(gp.read_bytes());v=np.vstack([x['vertices']for x in pr]);bb=np.array([v.min(0),v.max(0)]);err=abs(bbox-bb).max();assert err<.02,(r['name'],bbox,bb,err);assert {x['name']for x in pr}=={r['name']};rows.append({'name':r['name'],'native':r['native'],'GLB':ident(gp),'native_bbox_mm':bbox.tolist(),'GLB_bbox_CAD_mm':bb.tolist(),'max_bbox_error_mm':float(err),'source_identityplacement':True})
save(EV/'visual_source_frame_readback_08.json',{'status':'PASS_SIX_REAL_NATIVE_GLB_WORLDZERO_FRAMES','source_checks':rows,'max_bbox_error_mm':max(r['max_bbox_error_mm']for r in rows),'material_density_not_used_to_estimate_COTS_mass':True,'mj_step_calls':0,'source':ident(__file__)});print({'max_bbox_error_mm':max(r['max_bbox_error_mm']for r in rows)},flush=True)
