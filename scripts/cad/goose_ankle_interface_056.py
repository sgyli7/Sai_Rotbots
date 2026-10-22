"""Bounded native AP/AR interface candidate; never edits the frozen runtime.

Retains the complete C02 steel collector and OEM rotor. A one-piece receiver
extension and an axially offset saddle resolve the added C02 front-face clash.
The local 1.78mm secondary-floor relief remains a structural condition, not a
claim of full mechanical or manufacturing release.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from cadgen import build123d as b
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

ROOT = Path(__file__).resolve().parents[2]
OFFSET = 1.5
SCREW_SHA = '6a91ccbe1547ec4d9262561a7e07ab6b94e346e57b58bb5fd922e229d88258c5'
SCREW_ID = 'button_head_screw_m3_l0012_simple'
SCREW_URL = 'https://media.githubusercontent.com/media/earthtojake/step.parts/c6113328a5695b976a010a203a90fe86191769bf/catalog/step/button_head_screw_m3_l0012_simple.step'


def _solid(s):
    parts=list(s.solids());assert len(parts)==1
    return b.Solid(parts[0].wrapped)


def _box(lo, hi):
    return b.Solid.make_box(*(np.asarray(hi)-lo),b.Plane(origin=lo))


def _cyl_x(r, lo, hi, y, z):
    return b.Solid.make_cylinder(r,hi-lo,b.Plane(origin=(lo,y,z),z_dir=(1,0,0)))


def _common(a, c):
    op=BRepAlgoAPI_Common(a.wrapped,c.wrapped);op.SetRunParallel(False);op.Build()
    assert op.IsDone()
    return b.Compound.cast(op.Shape())


def _volume(s):
    return sum(float(p.volume)for p in s.solids())


def _props(s, density):
    g=GProp_GProps();BRepGProp.VolumeProperties_s(s.wrapped,g)
    inertia=g.MatrixOfInertia()
    return {'volume_mm3':g.Mass(),'mass_kg':g.Mass()*density*1e-9,
            'com_world_mm':list(g.CentreOfMass().Coord()),
            'inertia_at_com_world_kg_m2':[[inertia.Value(i+1,j+1)*density*1e-15 for j in range(3)]for i in range(3)]}


def _inputs(root,out):
    source=root/'robots/goose_v0_2/cad/source/enclosure_refinement_056'
    manifest=json.loads((source/'retained_hardware_input.json').read_text())
    desired=set()
    for side in ['left','right']:
        desired|={side+'_foot_front_saddle',side+'_ankle_roll_output_adapter'}
        desired|={side+f'_AR_adapter_to_front_saddle_{kind}_{i}' for i in range(3)for kind in ['M3x10','washer']}
    selected=[p for p in manifest['parts']if p['name']in desired]
    assert len(selected)==16 and all(p['solid_count']==1 for p in selected)
    cache=out/'retained_receiver_inputs.brep'
    binding=out/'retained_receiver_inputs_binding.json'
    identity={'original_input_sha256':manifest['uncompressed_native_sha256'],'names':[p['name']for p in selected]}
    if cache.exists()and binding.exists()and json.loads(binding.read_text())==identity:
        shapes=list(b.import_brep(str(cache)).solids())
    else:
        raw=out/'retained_hardware_input.brep'
        if not raw.exists():
            with gzip.open(source/'retained_hardware_input.brep.gz','rb')as src,raw.open('wb')as dst:
                shutil.copyfileobj(src,dst)
        assert hashlib.file_digest(raw.open('rb'),'sha256').hexdigest()==manifest['uncompressed_native_sha256']
        native=list(b.import_brep(str(raw)).solids());assert len(native)==manifest['native_solids']
        shapes=[native[p['solid_start']]for p in selected]
        b.export_brep(b.Compound(children=shapes),str(cache));binding.write_text(json.dumps(identity,indent=2)+'\n')
    assert len(shapes)==16
    index=json.loads((root/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json').read_text())['parts']
    result={}
    for p,s in zip(selected,shapes):
        bb=s.bounding_box();assert np.max(abs(np.asarray([list(bb.min),list(bb.max)])-p['bounds_mm']))<.001
        row=index[p['native_part_index']];assert row['name']==p['name']
        result[p['name']]=(row,s)
    return result


def _saddle(old, side):
    y=125. if side=='left'else-125.
    split=15.0750002
    upper=_solid(old.intersect(_box([0,y-80,split],[150,y+80,100])))
    base=_solid(old.intersect(_box([0,y-80,0],[150,y+80,split])))
    shifted=upper.translate((OFFSET,0,0))
    new=_solid(base.fuse(shifted))
    # This channel is behind the new load column (new back X79.25). The four
    # original foot screw/washer regions are outside its X/Y footprint.
    new=_solid(new.cut(_cyl_x(27.8,77.5,79.,y,40.655)))
    for sign in [-1,1]:
        new=_solid(new.cut(b.Solid.make_cylinder(3.4,10.,b.Plane(origin=(76.5,y+sign*24,12.855)))))
    return new


def _adapter(old, hole_centres):
    # Extrude the actual receiving face, carrying every wire/service opening
    # with it. Existing rotor countersinks and rotor screws remain at X77.75;
    # the new length is an open service well above their original heads.
    faces=[f for f in old.faces()if f.geom_type==b.GeomType.PLANE and all(abs(v.X-77.75)<1e-5 for v in f.vertices())]
    assert faces
    new=_solid(old.fuse(*[b.Solid.extrude(f,(OFFSET,0,0))for f in faces]))
    for yy,zz in hole_centres:
        new=_solid(new.cut(_cyl_x(1.6,77.75,79.250001,yy,zz)))
    return new


def build(context):
    root=Path(context.get('root',ROOT));out=Path(context.get('artifacts',root/'artifacts/goose_v0_2/enclosure_refinement_056/body/ar_interference_056/candidate'))
    out.mkdir(parents=True,exist_ok=True);inputs=_inputs(root,out)
    screw_path=Path(context.get('catalog_screw_step',root/'robots/goose_v0_2/cad/source/enclosure_refinement_056/ankle_receiver_setback_056'/f'{SCREW_ID}.step'))
    assert hashlib.file_digest(screw_path.open('rb'),'sha256').hexdigest()==SCREW_SHA
    screw=_solid(b.import_step(str(screw_path)));sb=screw.bounding_box()
    assert abs(sb.min.Z+12)<1e-5 and abs(sb.max.Z-1.65)<1e-5
    contract_path=root/'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json'
    contract=json.loads(contract_path.read_text());assert abs(contract['nominal_robot_mass_kg']-16.869881395484015)<1e-9
    records=[];interfaces=[]
    def add(name,shape,body,role,density,old_name=None,extra=None,old_density=None):
        shape=_solid(shape);shape.label=name
        row={'name':name,'shape':shape,'role':role,'mount_body':body,'material':'aluminium_original_density_budget_grade_unqualified'if density==2700 else'steel_standard_fastener','density_kg_m3':density,'nominal_wall_mm':None,
             'assumptions':['Native CAD candidate only; frozen15 model, joint axes, sole contact and limits unchanged.','No whole-ROM, fatigue, bolt-preload or manufacturing approval is inherited.'],**_props(shape,density)}
        if old_name:
            original,geometry=inputs[old_name];old_props=_props(geometry,old_density if old_density is not None else density)
            row.update(replacement_for=old_name,replaces=[old_name],original_native_part_index=original['native_part_index'],original_metadata=original,old_mass_kg_at_original_density=old_props['mass_kg'],original_density_budget_kg_m3=old_density if old_density is not None else density,mass_delta_kg=row['mass_kg']-old_props['mass_kg'])
        else:row.update(replaces=[],mass_delta_kg=row['mass_kg'])
        if extra:row.update(extra)
        records.append(row);return shape
    for side in ['left','right']:
        body=side+'_ankle_roll';y=125. if side=='left'else-125.
        sn=side+'_foot_front_saddle';an=side+'_ankle_roll_output_adapter'
        saddle=add(side+'_foot_front_saddle_setback_056',_saddle(inputs[sn][1],side),body,'One-piece saddle with original four foot fixing stations; upper receiving plate shifted axially1.5mm; local hidden secondary-floor clearance.',2810,sn,
                   {'material':'7075_T651_conditional','density_kg_m3':2810.,'original_density_budget_kg_m3':2700.,'conditional_yield_lower_bound_MPa':420.58019488327,'design_factor_for_nominal_screen':1.5,'conditional_allowable_after_factor_MPa':280.38679658884666,'material_basis':'robots/goose_v0_2/evidence/drag_leg_structure_009/c02/material_contract.json; same existing Kaiser7075 conditional design basis, not a new material certificate','upper_plate_displacement_mm':[OFFSET,0,0],'original_foot_fixings_displaced':False,'local_secondary_floor_by_construction_mm':1.78,'local_thin_floor_strength_not_qualified':True},old_density=2700.)
        hole_centres=[]
        for i in range(3):
            bb=inputs[side+f'_AR_adapter_to_front_saddle_M3x10_{i}'][1].bounding_box()
            hole_centres.append(((bb.min.Y+bb.max.Y)/2,(bb.min.Z+bb.max.Z)/2))
        receiver=add(side+'_ankle_roll_integral_receiver_056',_adapter(inputs[an][1],hole_centres),body,'One-piece receiver face extension; original rotor countersinks and four-mmM3 threads retained; new1.5mm segment is clearance-only.',2700,an,
                     {'original_rotor_connection_unchanged':True,'original_M3_effective_thread_mm':4.,'new_extension_M3_clearance_diameter_mm':3.2,'separate_spacer_added':False})
        for i in range(3):
            bolt=side+f'_AR_adapter_to_front_saddle_M3x10_{i}';washer=side+f'_AR_adapter_to_front_saddle_washer_{i}'
            old_bolt=inputs[bolt][1];bb=old_bolt.bounding_box();yy=(bb.min.Y+bb.max.Y)/2;zz=(bb.min.Z+bb.max.Z)/2
            shape=screw.rotate(b.Axis.Y,90).translate((85.75,yy,zz))
            add(side+f'_AR_receiver_M3x12_{i}_056',shape,body,'Actual ISO7380 M3x12 catalogue STEP; original tip X73.75/4mm engagement retained with two0.5mm washers.',7850,bolt,
                {'procurement_sku':'ISO7380-1 M3x12','catalogue_id':SCREW_ID,'catalogue_input_sha256':SCREW_SHA,'catalogue_step_url':SCREW_URL,'nominal_thread_engagement_mm':4.,'maximum_permitted_thread_insertion_mm':4.,'head_datum_world_mm':[85.75,yy,zz],'head_outward_normal':[1,0,0]})
            add(washer+'_056',inputs[washer][1].translate((1.5,0,0)),body,'Original exact3.2x7x0.5 washer translated to offset saddle face.',7850,washer,{'rigid_displacement_mm':[1.5,0,0]})
            add(side+f'_AR_receiver_additional_washer_{i}_056',inputs[washer][1].translate((2.,0,0)),body,'One additional exact3.2x7x0.5 washer closes the two-mm length increment without changing thread penetration.',7850,None,{'source_occurrence':washer,'rigid_displacement_from_source_mm':[2.,0,0]})
        interfaces.append({'side':side,'AR_axis_world_mm':[70.15,y,40.655],'axis_direction':[1,0,0],'old_saddle_receiving_face_x_mm':77.75,'new_saddle_receiving_face_x_mm':79.25,'receiver_material_front_x_mm':79.25,'C02_steel_front_face_x_mm':78.75,'nominal_vertical_plate_axial_gap_mm':.5,'source_foot_fixings_xy_mm':[[xx,y+dy]for xx in [69,89]for dy in [-18,18]],'new_M3_stack_mm':{'saddle':5.5,'washers':1.,'receiver_clearance':1.5,'original_effective_thread':4.},'screw_underhead_length_mm':12.,'thread_tip_x_mm':73.75,'total_length_identity_mm':5.5+1+1.5+4})
    assert len(records)==22
    receipt={'schema':'goose_native_ankle_receiver_setback_056/1','status':'ACTUAL_CAD_CANDIDATE_PENDING_FINITE_INTERFACE_AND_LOCAL_STRUCTURE_SCREEN','module_sha256':hashlib.file_digest(Path(__file__).open('rb'),'sha256').hexdigest(),'source_hardware':str(root/'robots/goose_v0_2/cad/source/enclosure_refinement_056/retained_hardware_input.json'),'catalogue_part':{'id':SCREW_ID,'input':str(screw_path),'sha256':SCREW_SHA,'step_url':SCREW_URL,'api_url':'https://api.step.parts/v1/parts/'+SCREW_ID,'upstream_repository_commit':'c6113328a5695b976a010a203a90fe86191769bf','upstream_root_license':'MIT, Copyright (c) 2026 earthtojake','source_metadata':'robots/goose_v0_2/cad/source/enclosure_refinement_056/ankle_receiver_setback_056/catalogue_source.json','license_notice':'robots/goose_v0_2/cad/source/enclosure_refinement_056/ankle_receiver_setback_056/STEP_PARTS_LICENSE.txt','individual_api_license_field_present':False},'interfaces':interfaces,'frozen15_mass_kg':contract['nominal_robot_mass_kg'],'robot_mass_change_not_written_into_frozen_package':True,'CAD_mass_delta_kg':sum(p['mass_delta_kg']for p in records),'parts':[{k:v for k,v in p.items()if k not in ['shape','original_metadata']}for p in records]}
    (out/'build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return records


if __name__=='__main__':
    output=ROOT/'artifacts/goose_v0_2/enclosure_refinement_056/body/ar_interference_056/candidate'
    rows=build({'root':ROOT,'artifacts':output})
    for row in rows:b.export_brep(row['shape'],str(output/(row['name']+'.brep')))
    b.export_step(b.Compound(children=[row['shape']for row in rows]),str(output/'ankle_receiver_setback_056.step'))
    print(json.dumps({'parts':len(rows),'mass_delta_kg':sum(row['mass_delta_kg']for row in rows)}),flush=True)
