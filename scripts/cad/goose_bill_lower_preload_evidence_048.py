"""One15 local lower rib-depth patch, original14 immutable; no physics."""
from pathlib import Path
import sys,json,hashlib,copy
import numpy as np
from cadgen import build123d as b,read_step
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin,gp_Pnt,gp_Dir
W=Path(__file__).resolve().parents[2];sys.path.insert(0,str(W/'scripts/cad'));sys.path.insert(0,str(W/'scripts/diagnostics'));from goose_bill_longitudinal_r05_024 import common,props,box
from goose_mouth_actual_beam_screen_035 import screen_beams
E=W/'experiments/goose_v0_2/bill_lower_preload_patch_048/c01';O=W/'robots/goose_v0_2/cad/exports/bill_lower_preload_patch_048/c01';E.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True);base=W/'robots/goose_v0_2/cad/exports/bill_lower_local_patch_043/c01';oldm=base/'lower_backbone_integral_local_depth_h900.step';oldp=base/'lower_grip_shell_internal_local_relief.step';metal=read_step(str(oldm));shell=read_step(str(oldp));profile=[(231.5,549.7),(233,547.60),(241,547.60),(248,548.5),(249,548.5),(254,549.7)];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loft(clear=False):
 wires=[]
 for x,z in profile:
  w=min(4.5,7-(x-239)*4/19-.1)if x>239 else 4.5;lo=z-(.15 if clear else 0);hi=549.9 if clear else 549.71;wires.append(b.Wire.make_polygon([(x,-w,lo),(x,w,lo),(x,w,hi),(x,-w,hi)],close=True))
 return b.Solid.make_loft(wires,ruled=True)
rib=loft();tool=loft(True);newmetal=read_step(str(O/'lower_backbone_integral_preload_depth_h900.step'));newPA=read_step(str(O/'lower_grip_shell_internal_preload_relief.step'));records=[]
for name,s,rho,oldpath,oldshape in [('lower_backbone_integral_preload_depth_h900',newmetal,7800,oldm,metal),('lower_grip_shell_internal_preload_relief',newPA,1270,oldp,shell)]:
 p=O/(name+'.step');records.append(dict(name=name,body='beak_hinge',path=str(p),sha256=sha(p),old_path=str(oldpath),old_sha256=sha(oldpath),density_kg_m3=rho,new_source_mci=props(s,rho),old_source_mci=props(oldshape,rho),delta_mass_kg=(s.volume-oldshape.volume)*rho*1e-9,translation_to_zero_mm=[-13.55,0,32.305],body_origin_oldnative_mm=[160,0,576]))
# Tool contains whole newrib, oldmetal/oldshell13 was0; direct completedactualCommon independently below.
fit=dict(actual_added_rib_vs_finalPA_Common_mm3=common(rib,newPA),wholepair_Common_status='Timedoutbeforecompletion; constructiveparentclearance+actualaddedribCommon used, Fmustindependentlyclosewholepairbeforeadoption',rib_containment_missing_mm3=rib.volume-common(rib,tool),metal_solid_count=len(newmetal.solids()),PA_solid_count=len(newPA.solids()),oldPA_bbox_mm=[list(shell.bounding_box().min),list(shell.bounding_box().max)],newPA_bbox_mm=[list(newPA.bounding_box().min),list(newPA.bounding_box().max)])
print('fit',fit,flush=True)
table=json.load(open(W/'experiments/goose_v0_2/bill_lower_local_patch_043/c01/actual_section_table_043_002.json'));before=copy.deepcopy(table)
for sec in table['sections']:
 if sec['side']!='lower'or sec['x_mm']<231.5:continue
 x=sec['x_mm'];th=.02;op=BRepAlgoAPI_Common(newmetal.wrapped,box(x-.01,-50,520,.02,100,100).wrapped);op.Build();s=b.Compound(op.Shape());A=s.volume/th;C=s.center(b.CenterOf.MASS);I=s.matrix_of_inertia;bb=s.bounding_box();sec['normal_tensor']=dict(area_mm2=A,centroid_yz_mm=[C.Y,C.Z],B_yz_area_mm4=[[I[2][2]/th-A*th*th/12,-I[1][2]/th],[-I[1][2]/th,I[1][1]/th-A*th*th/12]],max_abs_y_mm=max(C.Y-bb.min.Y,bb.max.Y-C.Y),max_abs_z_mm=max(C.Z-bb.min.Z,bb.max.Z-C.Z))
reg={}
for run in ['018','019','033']:
 path=(f'/home/ethan/ProjectBackups/2026-10-21/Sai_Lab/downward_pull_fixture_041/candidate13_run_{run}/result.json' if run=='018' else '/home/ethan/ProjectBackups/2026-10-21/Sai_Lab/hanging_mass_ceiling_043/'+('candidate13_10kg_run_019'if run=='019'else'candidate14_continuous_virtual_load_fullinput_run_033')+'/result.json');r=json.load(open(path));reg[run]=dict(before=screen_beams(r['actual_observation']['material_points'],before),after=screen_beams(r['actual_observation']['material_points'],table))
wall=[]
for x in [233,237,239.05,241,245,248,249,250,252]:
 for y in [-4,0,4]:
  a=IntCurvesFace_ShapeIntersector();a.Load(newPA.wrapped,1e-7);a.Perform(gp_Lin(gp_Pnt(x,y,520),gp_Dir(0,0,1)),0,100);z=sorted(set(round(a.Pnt(i).Z(),8)for i in range(1,a.NbPnt()+1)));wall.append(dict(x_mm=x,y_mm=y,z_mm=z,wall_mm=z[-1]-z[0]if len(z)==2 else None))
table['version']='candidate15_lower_preload_depth_048';table['source_geometry'].append(dict(path=records[0]['path'],sha256=records[0]['sha256']));tp=E/'actual_section_table_048_001.json';tp.write_text(json.dumps(table,indent=2)+'\n');out=dict(candidate_id='candidate15_lower_preload_depth_048',status='AUTHOR_ONE_GEOMETRY_FOR_F_INDEPENDENT_REVIEW_NO_PHYSICS',source=dict(path=str(Path(__file__)),sha256=sha(__file__)),parent14_handoff=dict(path=str(W/'experiments/goose_v0_2/bill_lower_local_patch_043/c01/module_handoff_core_revision_002.json'),sha256=sha(W/'experiments/goose_v0_2/bill_lower_local_patch_043/c01/module_handoff_core_revision_002.json')),parts=records,retired_native_exact_names=['local043_lower_backbone_integral_local_depth_h900','local043_lower_grip_shell_internal_local_relief'],retired_runtime_aliases='F applies actual14ledger sourceDelta; originalupper14 andallotherparts retained',profile_x_bottomz_mm=profile,root_radius='No newlyclaimedfillet; actualC0taper andKt3 retained as condition',fit=fit,wall_rays=wall,min_sampled_wall_mm=min(v['wall_mm']for v in wall if v['wall_mm']is not None),section_table=dict(path=str(tp),sha256=sha(tp)),beam_function=dict(path=str(W/'scripts/diagnostics/goose_mouth_actual_beam_screen_035.py'),sha256=sha(W/'scripts/diagnostics/goose_mouth_actual_beam_screen_035.py')),saved_actual_wrench_regression=reg,net_source_mass_delta_kg=sum(v['delta_mass_kg']for v in records),preserved='Originalouterbill/continuousselectedTPU/workingplanes/installholes/Oaxis/shaft/drive/caps/mu/contact all unchanged; upper14 unchanged',limits=['No physics; original018/019/033 preserved','Actual018/019/033recorded4.4 wrench regression only, not future5s20kg ormanufacturingqualification','Samefactor6/Sy1170andoriginalfulltensor+provencontainedSVcore retained','Finitewallrays not fullminimumwall/tolerance/heat-treatment/fatiguecertification'])
hp=E/'module_handoff.json';hp.write_text(json.dumps(out,indent=2)+'\n');(E/'freeze_index.json').write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p))for p in [Path(__file__),hp,tp]]+[dict(path=r['path'],sha256=r['sha256'])for r in records]),indent=2)+'\n');print('FINAL',sha(hp),'mass',out['net_source_mass_delta_kg'],'wall',out['min_sampled_wall_mm'],'regression_max',[(k,max((x['utilization'],x['side'],x['x_mm'])for x in v['after']['beam_sections']))for k,v in reg.items()],flush=True)
