"""Internal AB6M maintenance-reset candidate, without an exterior opening.

Retains the three original manufacturer solids and their original unit mass
allowance. New native fixture routes around the untouched contactor leads and
clamps the existing lower rear-frame beam. A narrow insulated service pusher,
not a claimed full-finger aisle, is checked after removing the full tail cap.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from cadgen import build123d as b
from OCP.gp import gp_Trsf
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

ROOT=Path(__file__).resolve().parents[2]
DATUM=np.array([-113.,-55.,312.5])
SOURCE=Path('robots/goose_v0_2/cad/source/enclosure_refinement_056/service_inputs')


def _sha(p):return hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
def _one(s):
    ss=list(s.solids());assert len(ss)==1
    return b.Solid(ss[0].wrapped)
def _box(lo,hi):return b.Solid.make_box(*(np.asarray(hi)-lo),b.Plane(origin=lo))
def _props(s,density):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,g);m=g.MatrixOfInertia()
    return {'volume_mm3':g.Mass(),'mass_kg':g.Mass()*density*1e-9,'com_world_mm':list(g.CentreOfMass().Coord()),'inertia_at_com_world_kg_m2':[[m.Value(i+1,j+1)*density*1e-15 for j in range(3)]for i in range(3)]}
def _bore_z(x,y):return b.Solid.make_cylinder(1.6,25.,b.Plane(origin=(x,y,329)))


def build(context):
    root=Path(context.get('root',ROOT));src=root/SOURCE
    out=Path(context.get('artifacts',root/'artifacts/goose_v0_2/enclosure_refinement_056/service/candidate'))
    out.mkdir(parents=True,exist_ok=True)
    binding=json.loads((src/'source_bound_inputs.json').read_text())
    input_rows={r['name']:r for r in binding['parts']}
    index=json.loads((root/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json').read_text())['parts']
    for n in ['tail_reset_oem_000','tail_reset_oem_001','tail_reset_oem_002']:
        assert _sha(src/(n+'.brep'))==input_rows[n]['native']['sha256']
    old=np.asarray(index[1732]['source_to_world_zero_4x4']);Rnew=np.array([[0.,0.,-1.],[1.,0.,0.],[0.,-1.,0.]])
    A=Rnew@old[:3,:3].T;T=np.eye(4);T[:3,:3]=A;T[:3,3]=DATUM-A@old[:3,3]
    assert np.allclose(A.T@A,np.eye(3),atol=1e-12)and abs(np.linalg.det(A)-1)<1e-12
    tr=gp_Trsf();tr.SetValues(*map(float,T[:3,:4].reshape(-1)))
    records=[]
    for i in range(3):
        old_name=f'tail_reset_oem_{i:03d}';s=_one(b.import_brep(str(src/(old_name+'.brep'))));s=_one(s.moved(b.Location(tr)))
        # The actual collar bearing is X=datum; original ring bearing is +4mm.
        # Move only the threaded lock ring toward the head by 1mm for this
        # true 3mm receiving plate. Four shallow seats accept its real teeth;
        # no supplier body is cut, scaled or healed.
        if i==2:s=_one(s.translate((-1,0,0)))
        n=f'internal_tail_reset_oem_{i:03d}_056';s.label=n
        records.append({'name':n,'shape':s,'role':'Retained original IDEC AB6M reset component, relocated inside full removable tail cap.','mount_body':'torso','nominal_wall_mm':None,'replacement_for':old_name,'replaces':[old_name],'original_native_part_index':1732+i,'original_metadata':index[1732+i],'source_to_candidate_world_4x4':T.tolist(),'additional_lock_ring_world_translation_mm':[-1,0,0]if i==2 else[0,0,0],'mass_delta_kg':0.,'procurement_unit_id':'tail_reset_whole_unit','retained_unit_mass_allowance_kg':.007,'unit_mass_count':1 if i==0 else 0,'assumptions':['The existing unmeasured 7g whole-unit allowance is retained once, not converted into homogeneous plastic or metal.','Supplier family CAD is retained; selected SPDT terminal clocking and actual SKU mass remain unmeasured.','No exterior hole, new emergency-stop function or frozen physics change.']})
    pieces=[_box([-164,-64.5,338],[-146,-48.5,340]),
            _box([-150,-70,336],[-140,-61,338]),
            _box([-144,-70,316],[-140,-68,338]),
            b.Solid.extrude(b.Face(b.Wire.make_polygon([(-144,-70,316),(-144,-68,316),(-130,-72.5,316),(-110,-72.5,316),(-110,-74.5,316),(-130,-74.5,316)],close=True)),(0,0,6)),
            _box([-115,-74.5,316],[-110,-72.5,325.5]),
            _box([-115,-74.5,323.5],[-110,-43.5,325.5]),
            _box([-113,-68,301.5],[-110,-43.5,323.5])]
    bracket=_one(pieces[0].fuse(*pieces[1:]));panel_hole=b.Solid.make_cylinder(8.1,5.,b.Plane(origin=(-114,-55,312.5),z_dir=(1,0,0)))
    # Clearance for the actual receiving-frame downstand, not a new frame hole.
    clearance=[_box([-156.7,-54.2,337.8],[-153.3,-50.3,340.2])]
    # Four real locking-ring teeth enter the back of the panel. Local 1.2mm
    # seats leave 1.8mm minimum front web; the remaining flat annulus bears
    # at X=-110. These are functional key seats, never exterior decoration.
    for ya,yb in [(-64.2,-60.65),(-49.35,-45.8)]:
        for za,zb in [(303.3,306.85),(318.15,321.7)]:
            clearance.append(_box([-111.2,ya,za],[-109.9,yb,zb]))
    bracket=_one(bracket.cut(panel_hole,*clearance,*[_bore_z(x,-60.5)for x in [-160,-150]]))
    keeper=_one(_box([-164,-64.5,344],[-146,-48.5,346]).cut(*[_bore_z(x,-60.5)for x in [-160,-150]]))
    def add(n,s,role,density,material,extra=None):
        s=_one(s);s.label=n
        r={'name':n,'shape':s,'role':role,'mount_body':'torso','nominal_wall_mm':2.,'material':material,'density_kg_m3':density,'replaces':[],'assumptions':['Native service-fixture candidate; no moving joints, motor limits, sole contacts or frozen15 physical values are changed.','Fixture clamp preload and machining tolerance require bench confirmation.'],**_props(s,density)}
        r['mass_delta_kg']=r['mass_kg']
        if extra:r.update(extra)
        records.append(r)
    add('internal_tail_reset_receiver_056',bracket,'One-piece CNC6061 service receiver and cable-clearing support, clamped to the unmodified original lower frame beam.',2700.,'aluminium_6061_T6_design_budget',{'panel_outer_x_mm':-113.,'panel_inner_x_mm':-110.,'receiver_panel_thickness_mm':3.,'four_lock_ring_key_seats_depth_mm':1.2,'front_web_at_key_seats_mm':1.8,'panel_cutout_diameter_mm':16.2,'original_frame_native_part_index':1280,'original_beam_contact_box_mm':[[-164,-54,340],[-146,-50.5,344]],'unmodified_frame_no_new_holes':True})
    add('internal_tail_reset_clamp_keeper_056',keeper,'Separate removable 2mm upper keeper; two real through M3 stacks grip the original four-mm beam.',2700.,'aluminium_6061_T6_design_budget')
    screw_path=root/'robots/goose_v0_2/cad/source/enclosure_refinement_056/ankle_receiver_setback_056/button_head_screw_m3_l0012_simple.step'
    assert _sha(screw_path)=='6a91ccbe1547ec4d9262561a7e07ab6b94e346e57b58bb5fd922e229d88258c5'
    screw=_one(b.import_step(str(screw_path)))
    hardware={}
    for n in ['iso7092din433_m3flatwasher','iso4032_hex_nut_m3']:
        meta=json.loads((src/(n+'.json')).read_text());assert _sha(src/(n+'.step'))==meta['sha256'];hardware[n]=(_one(b.import_step(str(src/(n+'.step')))),meta)
    washer,wm=hardware['iso7092din433_m3flatwasher'];nut,nm=hardware['iso4032_hex_nut_m3']
    assert abs(washer.bounding_box().size.Z-.5)<1e-5 and abs(nut.bounding_box().size.Z-2.4)<1e-5
    for i,x in enumerate([-160.,-150.]):
        add(f'internal_tail_reset_clamp_M3x12_{i}_056',screw.translate((x,-60.5,346.5)),'Exact catalogue ISO7380 M3x12, underhead Z346.5, actual thread tip Z334.5.',7850.,'steel_standard_fastener',{'catalogue_id':'button_head_screw_m3_l0012_simple','catalogue_input_sha256':_sha(screw_path),'screw_underhead_length_mm':12.,'nut_nominal_engagement_mm':2.4,'tip_projection_below_nut_mm':.6})
        for label,z in [('upper',346.),('lower',337.5)]:
            bb=washer.bounding_box();shape=washer.translate((x-(bb.min.X+bb.max.X)/2,-60.5-(bb.min.Y+bb.max.Y)/2,z-bb.min.Z))
            add(f'internal_tail_reset_clamp_{label}_washer_{i}_056',shape,'Exact catalogue M3 0.5mm flat washer.',7850.,'steel_standard_fastener',{'catalogue_id':wm['id'],'catalogue_input_sha256':wm['sha256']})
        bb=nut.bounding_box();shape=nut.translate((x-(bb.min.X+bb.max.X)/2,-60.5-(bb.min.Y+bb.max.Y)/2,335.1-bb.min.Z))
        add(f'internal_tail_reset_clamp_nut_{i}_056',shape,'Exact catalogue ISO4032 M3 nut; 2.4mm engagement and 0.6mm free tip.',7850.,'steel_standard_fastener',{'catalogue_id':nm['id'],'catalogue_input_sha256':nm['sha256']})
    assert len(records)==13
    report={'schema':'internal_tail_reset_service_056/1','status':'ACTUAL_NATIVE_CANDIDATE_PENDING_STATIC_AND_ACCESS_SCREEN','module_sha256':_sha(Path(__file__)),'datum_world_mm':DATUM.tolist(),'outward_axis':[-1,0,0],'retained_function':'Original AB6M momentary maintenance-reset switch, not an emergency stop','independent_estop_and_hard_isolation_modified':False,'unit_mass_allowance_retained_once_kg':.007,'new_hardware_mass_delta_kg':sum(r.get('mass_delta_kg',0)for r in records),'frozen_runtime_modified':False,'requires_full_tail_cap_removed':True,'proposed_access':'5mm diameter insulated service pusher, axis +X, center Y=-50.5/Z312.5; full finger aisle is not claimed.','manufacturer_family_operating_stroke_mm':3.,'stroke_primary_source':{'document':'IDEC SAPEN01A-B147B167-A6-Global.pdf','sha256':'5e65e65ec449c0644b5af451fbd49f7d5e765a2441ff2ce8cfefb53f42e09589','page':'1, printed B-147; operating stroke 3mm visually checked','archived_download_manifest':'artifacts/goose_v0_2/tangpa_mango_ankle_integration_34/whole_stage_01/mango_primary_form_reset_01/whole_delivery_sprint_01/external_controls_01/manufacturer_download_manifest_01.json'},'terminal_reserve_box_mm':[[-85,-61,306],[-78,-49,319]],'selected_SPDT_terminal_mapping_verified':False,'parts':[{k:v for k,v in r.items()if k not in ['shape','original_metadata']}for r in records]}
    (out/'build_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    return records


if __name__=='__main__':
    out=ROOT/'artifacts/goose_v0_2/enclosure_refinement_056/service/candidate';records=build({'root':ROOT,'artifacts':out})
    for r in records:b.export_brep(r['shape'],str(out/(r['name']+'.brep')))
    b.export_step(b.Compound(children=[r['shape']for r in records]),str(out/'internal_tail_reset_service_056.step'))
    print(json.dumps({'parts':len(records),'new_mass_delta_kg':sum(r.get('mass_delta_kg',0)for r in records)}),flush=True)
