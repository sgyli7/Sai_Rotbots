"""Seal bounded four-point display/native diagnosis. No hardware changes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
import numpy as np
from cadgen import build123d as bd
from OCP.BRepAdaptor import BRepAdaptor_Surface
W=Path(__file__).resolve().parents[2];E=W/'robots/goose_v0_2/evidence/display_surface_audit_012/c01';A=W/'artifacts/goose_v0_2/display_surface_audit_012/c01';I=W/'robots/goose_v0_2/images/display_surface_audit_012/c01';D=W/'robots/goose_v0_2/design/display_surface_audit_012/c01';D.mkdir(parents=True,exist_ok=True);os.sched_setaffinity(0,{18})
def ident(p):
 p=p.resolve();h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return dict(path=str(p),sha256=h.hexdigest(),bytes=p.stat().st_size)
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
oldp=W/'artifacts/goose_v0_2/drag_hardware_sprint_009/mouth/four_surface_diagnostic_01/source_accessor_diagnostic.json';old=read(oldp);curp=A/'independent08/source_accessor_diagnostic.json';cur=read(curp);selp=E/'selected_mesh_native_readback.json';sel=read(selp);overp=E/'review_same_material_override.json';over=read(overp);visualp=E/'four_point_visual_readback.json';visual=read(visualp)
idxp=W/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json';idx=read(idxp);bindingp=W/'robots/goose_v0_2/evidence/drag_hardware_integration_009_08/actual_visual_binding_08_final.json';binding=read(bindingp)
assert ident(idxp)['sha256']==binding['native_assembly']['sha256'];assert ident(Path(binding['scene']['path']))['sha256']==binding['scene']['sha256'];assert over['source08_native_index']['sha256']==ident(idxp)['sha256']
stable=[]
for f in over['sources']:
 p=Path(f['native']['path']);assert ident(p)['sha256']==f['native']['sha256'];stable.append(ident(p))
model=W/'robots/goose_v0_2/models/physics_v0_2_20261020_08_candidate';mp=model/'manifest.json';runtime=read(mp);fail=[]
for f in runtime['files']:
 p=model/f['path']
 if not p.is_file()or ident(p)['sha256']!=f['sha256']:fail.append(f['path'])
assert not fail,fail
preservation=dict(source08_native_index=ident(idxp),source08_visual_binding=ident(bindingp),source08_complete_scene=ident(Path(binding['scene']['path'])),all_seven_native_sources_match=stable,
 runtime08_manifest=ident(mp),runtime08_all_manifest_files_checked=len(runtime['files']),runtime08_hash_failures=fail,native_or_MCI_or_runtime_mutations=0,verification='Read-only SHA match to original sealed08 bindings and manifest; no rewritten assembly, inertia, collision, caps, normals or material in08.')
save(E/'immutable08_readback.json',preservation)
# Exact native planar walls at the original10 vent Y boundaries.
fp=Path(over['sources'][0]['native']['path']);assert over['sources'][0]['name']=='front_main_shell';shape=bd.import_brep(fp);ys=[-77,-69,-61,-53,-45,45,53,61,69,77];edges=[q+t for q in ys for t in [-2.5,2.5]];vents=[]
for j,f in enumerate(shape.faces(),1):
 if f.geom_type!=bd.GeomType.PLANE:continue
 p=BRepAdaptor_Surface(f.wrapped,True).Plane();u=p.Axis().Direction();y=p.Location().Y();b=f.bounding_box()
 if abs(u.Y())>.999999 and min(abs(y-e)for e in edges)<1e-5 and b.min.Z<277.001 and b.max.Z>210 and b.max.X>-29.001 and b.min.X<53.001:
  vents.append(dict(native_face_index=j,plane_Y_mm=y,bounds_mm=[list(b.min),list(b.max)],area_mm2=float(f.area)))
ventproof=dict(native=ident(fp),source_original_functional_gate=ident(W/'robots/goose_v0_2/evidence/drag_shell_native_recovery_009/c06/final_feature_MCI_STEP_checks.json'),original_vent_centres_Y_mm=ys,original_vent_tool='Rounded82x5mm XY section centeredX12/Ylisted, Z210..277; unchanged original20mm inner air corridor.',native_planar_vent_boundary_faces=vents,
  front_camera_projection_X_px=[450+1.13*y for y in ys],identity_scope='Native plane positions plus the frozen exact vent-void gate identify the lower-front notches as actual functional cut geometry. This is not cosmetic/strength/manufacturing approval and not a global wall certificate.')
save(E/'additional_blue_lower_edge_vent_identity.json',ventproof)
regions=[
dict(point=1,normalized_old_xy=[.196,.866],label='前视脚部外伸长条',old='原左c09脚罩1片坏显示三角伸向原生包围盒以外，穿过这一ROI。',current='08长飞线已除；同native独立重网格仍无飞线。现有鞋轮廓/开口保留。',status='OLD_DISPLAY_OUTLIER_REMOVED',complete_cosmetic_manufacturing_pass=False),
dict(point=2,normalized_old_xy=[.148,.671],label='前视右腿内缘长片',old='原右c09脚罩1片坏显示三角被拉到躯干高度，在腿内缘形成长线。',current='08长飞片已除。此ROI上方另外仍露出原生蓝壳下缘通风缺口，不把它冒充同一条飞面。',status='OLD_DISPLAY_OUTLIER_REMOVED_REAL_VENT_EDGE_REMAINS',complete_cosmetic_manufacturing_pass=False),
dict(point=3,normalized_old_xy=[.47,.613],label='中右视髋口下方',old='原右c09坏显示三角经过此ROI；旧蓝壳也有叠片形态。',current='08拉长飞片已除，叠片宏观减少；剩余髋口/球背壁的裁边与开口为真实c06原生。最近见证为SPHERE face436，三角中心距native0.007480mm。重新细分仍见该边，不能用法线/材质消除后称修复。',status='REAL_NATIVE_HIP_OPENING_BACKING_EDGE_REMAINS',complete_cosmetic_manufacturing_pass=False),
dict(point=4,normalized_old_xy=[.847,.842],label='斜视前脚罩/鞋边',old='原左c09坏显示三角在鞋边伸出长细条。',current='08长飞条已除；现有AR c03后跟/鞋边口沿是真实曲面，见证为BSPLINE face130，三角中心距native0.018151mm。此见证不是已公布1.326mm薄唇的同一位置证明；该脚罩制造wall/STEP限制仍保留。',status='REAL_NATIVE_SHOE_RIM_REMAINS_OLD_OUTLIER_REMOVED',complete_cosmetic_manufacturing_pass=False)]
result=dict(schema='four_original_user_points_display_audit_012',status='FROZEN_DISPLAY_OUTLIERS_REMOVED_NATIVE_OPEN_EDGES_REMAIN_NOT_COSMETIC_OR_MANUFACTURING_RELEASE',start_UTC='2026-10-19T23:54:44+00:00',hardstop_UTC='2026-10-20T00:14:44+00:00',frozen_UTC=datetime.now(timezone.utc).isoformat(),
 old_source_diagnostic=ident(oldp),current08_independent_diagnostic=ident(curp),old_actual_bad_accessor_records=old['source_bad_accessors'],current08_counts=cur['counts'],current08_bad_accessor_records=cur['source_bad_accessors'],regions=regions,
 exact_same_native_retessellation=ident(overp),selected_geometry_readback=ident(selp),original_four_views=ident(visualp),immutable08=ident(E/'immutable08_readback.json'),additional_blue_vent_identity=ident(E/'additional_blue_lower_edge_vent_identity.json'),
 final_image=ident(I/'whole_and_four_original_regions.png'),four_point_comparison=ident(I/'four_user_points_old_08_fresh_native.png'),fresh_whole=ident(I/'whole_native_same_material/whole_three_views.png'),
 unchanged_OCC_count=1974,omitted_occurrences=[],physics_steps=0,CAD_modifications=0,MCI_modifications=0,public08_asset_modifications=0,AI_fill_or_pixel_retouch=False,
 mesh_limits='The whole08 GLB has2108 3D zero-area triangles,72 repeated-index triangles and21 within-primitive duplicate-index entries among7,929,614 submitted triangles. The seven selected skins have10 zero-area entries and0 exact-position duplicate triangles; independent native retessellation retains those10 at analytic seams/poles. They have no finite painted area and were not deleted to manufacture a pass. Other2100+ entries outside selected skins were not individually qualified.',
 normal_limits='Seven selected source skins have finite nonzero vertex normals. Original L/R crowns each have one0.2101768mm2 triangle with face-normal/interpolated-normal cosine-.2649 atX85.55; independent retessellation has0 such sign mismatches. These are remote fromP4 witness and neither renderer culls triangle sides; this small shading defect cannot explain the original long strips or true openings.',
 transform_limits='Full independent08 reader found0 negative determinants,0 invalid indices,0 nonfinite positions/normals,0 declared POSITION-bound violations. Same-native7part bbox comparison max.003145mm. Bbox agreement alone is not global surface equivalence; P3/P4 native distances are finite local witnesses.',
 manufacturing_limits='Native strict/SI validity and triangle cleanup do not certify minimum wall, fair edge design, STEP or manufacturing. c06 shell and c03 crowns retain original manufacturing/STEP FAIL states. This display audit grants no new motion/strength/manufacturing qualification.',
 rejected_private_render_stage=dict(image=ident(I/'whole_native_retessellation/whole_three_views.png'),reason='Native Color setter reinterpreted stored linear glTF colors and darkened the first private review. Final review reuses exact08 material dictionaries; BIN geometry/indices/normals of that independent remesh are unchanged. Initial stage preserved, not the final appearance recommendation.'),
 final_review_GLB=ident(W/over['scene']['repository_path']),source_script=ident(Path(__file__)),jobs='NO JOBS AFTER FREEZE; no geometry repair branch or integration requested.')
save(E/'audit_report.json',result)
text='''# 原图四处显示问题与08核查

**旧图两片异常脚罩显示三角造成的长飞线已经从08消失；仍可见的髋口/背壁和鞋边属于真实原生几何，不能说四处外观均修好。** 本轮只做显示审查，没有修改08 CAD、MCI、物理、碰撞或运行资产。

对照图上部是同08原生重新细分的整机三视图，下部按用户原四个归一化坐标给出“旧图 / 08保存显示 / 同08原生独立重网格”三列。全部1974显示occurrence保留；没有删零件、手工涂面或AI补面，机位使用原图固定矩阵，局部实际重新以2倍比例深度光栅渲染。

| 原点 | 08核查结论 |
|---|---|
| 1：19.6%,86.6%，前视脚部长条 | 旧左c09脚罩坏三角的飞线已除，独立重导出也没有。真实脚罩轮廓仍在。 |
| 2：14.8%,67.1%，前视右腿内缘 | 旧右c09坏三角的长片已除。ROI上方另有真实蓝壳通风缺口，不能混为同一飞片。 |
| 3：47.0%,61.3%，中右视髋口下方 | 飞片已除、旧叠片减少；真实c06球背壁/口沿裁边仍在。原生见证SPHERE face436，中心距离0.007480mm；不是靠换法线能闭合的开口。 |
| 4：84.7%,84.2%，斜视脚罩/鞋边 | 飞条已除；真实c03后跟/鞋边仍在。见证BSPLINE face130，中心距原生0.018151mm；未把这个位置冒称为另处已记录1.326mm薄唇的局部壁厚。 |

额外发现：蓝壳前下缘一排齿状缺口仍见于独立native图；对应原10个5mm通风切口Y=±45/53/61/69/77mm及真实平面切壁。原生切口存在，不是长飞三角或反法线。其外观是否可接受和边缘可制造性仍未放行；不能填风道或删显示三角来让图看起来平整。

独立读取08完整GLB：6162 primitives、7,929,614三角。非法索引、非有限坐标/法线、负变换行列式、POSITION声明越界均0。旧图实际异常顶点分别为左[1,-0.190075,1]mm、右[-229.959,-19.4,411.038]mm，各仅1片脚罩三角，但明显越出各自真实native；新08没有这些越界三角。

从08原始BREP单独重导出c06蓝壳、双c03脚罩与4个AP罩，共7件，全部原生strict/SI/单正实体通过。显示bbox最大差0.003145mm。局部三角顶点/中心到原生距离和面ID在JSON中；这不是全表面误差、全壁厚或全ROM证书。

网格也不是完美：全机有2108条三维零面积三角等小退化记录；7个审查皮件共10条，独立细分仍有10条，未为通过而删掉。它们没有有限绘制面积，不是厘米级飞片的来源。原两脚罩另各有1片0.210177mm²法线/面向符号不一致，位于X85.55，独立网格消失；它不是P4后跟的见证位置。CPU光栅器双面绘制、逐样本深度比较，不以背面剔除/画家排序遮盖几何。

首轮私有重导出因CAD Color对线性色再次转换而变暗，作为失败stage保留。最终审查直接复用08精确材质字典（含roughness/doubleSided）；该步BIN位置/索引/法线字节不变，不用材质盖住开口。

结论：P1/P2原长飞面已除；P3/P4真实原生边仍待工程外观/制造修正。c06和c03既有wall/STEP制造FAIL保持，不能把本次显示审核写成几何、运动或制造放行。原08全部运行包manifest文件与7件原生SHA均核对一致。仅独立review资产，无新集成源。NO JOBS。
'''
(D/'engineering_review.md').write_text(text)
folders=[E,A,I,W/'robots/goose_v0_2/cad/exports/display_surface_audit_012/c01',D];files=sorted({p.resolve()for folder in folders for p in folder.rglob('*')if p.is_file()and p.name not in ['manifest.json','seal_hash_readback.json']});files+=sorted((W/'scripts/diagnostics').glob('goose_display_*_012.py'))
deps=[ident(oldp),ident(W/'robots/goose_v0_2/images/drag_hardware_integration_009/candidate_actual_review/whole_three_views.png'),ident(W/'robots/goose_v0_2/images/drag_hardware_integration_009_08/whole_source_review_01/whole_three_views.png'),ident(W/'robots/goose_v0_2/images/drag_hardware_integration_009_08/whole_source_review_01/visual_review.json'),ident(idxp),ident(bindingp),ident(mp),ident(Path(binding['scene']['path'])),ident(W/'scripts/models/render_goose_reference_camera.py'),ident(W/'robots/goose_v0_2/evidence/drag_shell_native_recovery_009/c06/frozen_native_handoff.json'),ident(W/'robots/goose_v0_2/evidence/drag_ar_continuous_clearance_009/c03/integration_handoff.json')]+stable
manifest=dict(status=result['status'],frozen_UTC=result['frozen_UTC'],audit=ident(E/'audit_report.json'),report=ident(D/'engineering_review.md'),final_image=result['final_image'],artifacts=[ident(p)for p in sorted(set(files))],readonly_dependencies=deps,geometry_MCI_physics_changes=0,jobs='NO JOBS');save(E/'manifest.json',manifest)
bad=[];count=0
def check(x,parent):
 global count
 if isinstance(x,dict):
  path=x.get('path',x.get('repository_path'));sha=x.get('sha256')
  if isinstance(path,str)and isinstance(sha,str):
   p=Path(path);p=p if p.is_absolute()else W/p;count+=1
   if not p.is_file()or ident(p)['sha256']!=sha:bad.append(dict(parent=str(parent),ref=str(p)))
  for v in x.values():check(v,parent)
 elif isinstance(x,list):
  for v in x:check(v,parent)
for p in files+[E/'manifest.json']:
 if p.suffix=='.json':check(read(p),p)
assert not bad,bad
seal=dict(manifest=ident(E/'manifest.json'),audit=ident(E/'audit_report.json'),final_image=ident(I/'whole_and_four_original_regions.png'),artifact_count=len(manifest['artifacts']),checked_direct_refs=count,failures=bad,public08_files_checked=len(runtime['files']),status='FROZEN_HASH_ALL_PASS_NO_JOBS');save(E/'seal_hash_readback.json',seal);print(json.dumps(seal),flush=True)
