"""Rebuild the Goose mango enclosure from the real unpierced mother surface.

The exterior is inherited analytically, not wrapped over the rejected notched
shell mesh.  The cover is not a load-bearing substitute or frozen physics edit.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import time
from functools import lru_cache

import numpy as np
from cadgen import build123d as b
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common


ROOT = Path(__file__).resolve().parents[2]


def _ctx(context, key, default=None):
    return context.get(key, default) if isinstance(context, dict) else getattr(context, key, default)


def _solid(shape):
    solids = list(shape.solids())
    assert solids, 'Boolean produced no solid'
    return solids[0] if len(solids) == 1 else b.Compound(children=solids)


def _box(lo, hi):
    return b.Solid.make_box(*(np.asarray(hi) - lo), b.Plane(origin=lo))


def _cyl(center, radius, start=-180, stop=180):
    x, _, z = center
    return b.Solid.make_cylinder(radius, stop - start,
                                 b.Plane(origin=(x, start, z), z_dir=(0, 1, 0)))


def _hex_clearance_y(center, across_flats, start=-180., stop=180.):
    """Printed regular clearance; across-flats is not a circular drill size."""
    x, _, z = center
    plane=b.Plane(origin=(x,start,z),z_dir=(0,1,0))
    return b.extrude(plane*b.RegularPolygon(across_flats/(3.**.5),6),amount=stop-start)


def _identity(path, root):
    path = Path(path)
    try:
        name = str(path.relative_to(root))
    except ValueError:
        name = str(path)
    return {'path': name, 'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()}


def _bounds(shape):
    bb = shape.bounding_box()
    return [list(bb.min), list(bb.max)]


def _common_volume(a, c):
    operation = BRepAlgoAPI_Common()
    from OCP.TopTools import TopTools_ListOfShape
    arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    arguments.Append(a.wrapped)
    tools.Append(c.wrapped)
    operation.SetArguments(arguments)
    operation.SetTools(tools)
    operation.SetRunParallel(False)
    operation.Build()
    assert operation.IsDone(), 'Native common failed'
    result = b.Compound.cast(operation.Shape())
    return float(result.volume) if result is not None else 0.0


@lru_cache(maxsize=1)
def _mount_inputs(root_string,out_string):
    root,out=Path(root_string),Path(out_string)
    indices=[656,1108,1160,1212,1243]
    cache=out/'original_attachment_and_structural_inputs.brep'
    if cache.exists():
        parts=list(b.import_brep(str(cache)).solids())
    else:
        source=root/'artifacts/goose_v0_2/design_cleanup_052/native08_readback.brep'
        if not source.exists():
            source=out/'native08_source_readback.brep'
            if not source.exists():
                compressed=root/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/goose_drag_hardware_integration_009_08.brep.gz'
                with gzip.open(compressed,'rb')as src,source.open('wb')as dst:shutil.copyfileobj(src,dst)
        whole=list(b.import_brep(str(source)).solids());assert len(whole)==1827
        parts=[whole[i]for i in indices]
        b.export_brep(b.Compound(children=parts),str(cache))
    assert len(parts)==len(indices)
    return dict(zip(indices,parts))


def _closed_belly(outer,inner,out):
    tools=[];clearance=[]
    for sign in [-1,1]:
        tools.append(b.Solid.make_sphere(1).scale((60,16,38.5)).translate((-12,sign*75,223)))
        clearance.append(b.Solid.make_sphere(1).scale((63,19,41.5)).translate((-12,sign*75,223)))
    shaped=_solid(outer.cut(*tools));edges=[]
    for face in shaped.faces():
        bb=face.bounding_box()
        if face.geom_type==b.GeomType.BSPLINE and bb.max.Z<270 and bb.min.X>-80 and bb.max.X<55 and(bb.min.Y>55 or bb.max.Y<-55):
            edges+=list(face.edges())
    assert len(edges)==8
    shaped=shaped.fillet(2.,edges)
    cavity=_solid(inner.cut(*clearance))
    b.export_brep(shaped,str(out/'closed_belly_outer_selected.brep'))
    b.export_brep(cavity,str(out/'closed_belly_inner_selected.brep'))
    return shaped,cavity


def _restore_attachments(front,rear,original,outer,out):
    """Keep original actual frame nuts, nut access and sliding-cap tongues."""
    regions=[]
    for sign in [-1,1]:
        # Actual08 frame fixings were remounted forward to X65.45 and Y45/51;
        # never reuse the earlier05 coordinates X-64.7,Y76/82 from its script.
        y0,y1=(40.9,82.1)if sign>0 else(-82.1,-40.9)
        regions.append(_box([68.35,y0,324.475],[100.1,y1,338.675]))
        for z in [295.,415.]:
            y0,y1=(60.,113.1)if sign>0 else(-113.1,-60.)
            # The actual positive lower tongue joins the skin above its
            # fastening boss. Preserve that original bridge, not merely a
            # detached boss or an invented plug through the nut access.
            z_margin=16. if sign>0 and z==295. else 6.1
            x_end=-60. if sign>0 and z==295. else -64.9
            regions.append(_box([-81.1,y0,z-z_margin],[x_end,y1,z+z_margin]))
    preserved=[]
    for i,region in enumerate(regions):
        piece=_solid(original.intersect(region))
        piece=_solid(piece.intersect(outer))
        preserved.append(piece)
        b.export_brep(piece,str(out/f'original_mount_region_{i}.brep'))
    front=_solid(front.fuse(*preserved))
    assert len(front.solids())==1
    # The original rib bores continue unnecessarily through the exterior.
    # Actual four M3 bolts end at X77.45; blind their unused continuation from
    # X77.7, keeping the original nuts, shaft space and inside assembly access.
    caps=[]
    for y,z in [(-51,329.575),(-45,335.575),(45,335.575),(51,329.575)]:
        cap=b.Solid.make_cylinder(1.8,40.,b.Plane(origin=(77.7,y,z),z_dir=(1,0,0)))
        caps.append(_solid(cap.intersect(outer)))
    front=_solid(front.fuse(*caps))
    # Four purpose-made printed M3 clearances, on the original two shared axes.
    # These are AF3.3 regular hexagons, not falsely labelled circular drills.
    # Planar sides avoid the exact native orientation defect produced where a
    # small cylindrical bore intersects this particular Bezier mother skin.
    front=_solid(front.cut(*[_hex_clearance_y((-76,0,z),3.3)for z in [295.,415.]]))
    rear=_solid(rear.cut(*[_hex_clearance_y((-76,0,z),3.3)for z in [295.,415.]]))
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.gp import gp_Lin,gp_Pnt,gp_Dir
    query=IntCurvesFace_ShapeIntersector();query.Load(outer.wrapped,1e-7)
    for z in [295.,415.]:
        for sign in [-1,1]:
            query.Perform(gp_Lin(gp_Pnt(-76,0,z),gp_Dir(0,sign,0)),0,180)
            ys=[query.WParameter(i)for i in range(1,query.NbPnt()+1)if query.WParameter(i)>1e-5]
            oy=min(ys);lo,hi=sorted([sign*(oy-.35),sign*(oy+8.)])
            rear=_solid(rear.cut(_hex_clearance_y((-76,0,z),6.2,lo,hi)))
    return front,rear


def _regular_vents(rear):
    """Six paired straight-ended slots with one uncut protective centre rib.

    The centre rib preserves the true mango silhouette in side view. R1 at
    the new inner ends failed both whole-bank and per-slot native filleting;
    use regular planar ends, never loose tolerances or an unreported fillet.
    """
    stations=[363.,371.,379.,387.,395.,403.]
    banks=[(-26.5,-1.5),(1.5,26.5)]
    for z in stations:
        for y0,y1 in banks:
            rear=_solid(rear.cut(_box([-270,y0,z-2.1],[-204,y1,z+2.1])))
    return rear


@lru_cache(maxsize=1)
def _light_inputs(root_string, out_string):
    root, out = Path(root_string), Path(out_string)
    indices = [680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692,
               821, 1280, 1285, 1286, 1287, 1288, 1289, 1290, 1291, 1292, 1293]
    source = root/'artifacts/goose_v0_2/design_cleanup_052/native08_readback.brep'
    cache = out/'original_light_inputs.brep'
    if cache.exists():
        parts = list(b.import_brep(str(cache)).solids())
        assert len(parts) == len(indices)
    else:
        if not source.exists():
            # Fresh checkout: use the already versioned complete native source,
            # rather than requiring a previous local diagnostic run.
            compressed = root/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/goose_drag_hardware_integration_009_08.brep.gz'
            source = out/'native08_source_readback.brep'
            with gzip.open(compressed,'rb') as src,source.open('wb') as dst:
                shutil.copyfileobj(src,dst)
        whole = list(b.import_brep(str(source)).solids())
        assert len(whole) == 1827
        parts = [whole[i] for i in indices]
        b.export_brep(b.Compound(children=parts), str(cache))
    index = json.loads((root/'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json').read_text())['parts']
    for i,s in zip(indices,parts):
        expected = index[i].get('native_bounds_mm',index[i].get('bounds_mm'))
        if expected is not None:
            assert np.max(np.abs(np.asarray(_bounds(s))-np.asarray(expected)))<.02,index[i]['name']
    return {i:(index[i],s) for i,s in zip(indices,parts)}


def _light_remounts(root, out, context):
    """Move the fan3.2mm and one coil base screw10mm; keep all electronics."""
    old = _light_inputs(str(root), str(out))
    coil_delta = np.asarray(_ctx(context, 'coil_root_displacement_mm', (10., 0., 0.)), dtype=float)
    assert np.allclose(coil_delta, (10,0,0)), 'This landing design has one validated root station.'
    fan_delta = np.asarray(_ctx(context, 'fan_displacement_mm', (3.2, 0., 0.)), dtype=float)
    records = []
    for ids, delta, purpose in [
        (range(680, 693), fan_delta, 'Move the intact fan and original fastener stack inward, preserving the outer tail skin.'),
        ([1288,1289], coil_delta, 'Move one complete lower coil-base M3/washer stack to its real remachined receiving root; electronics and wiring remain in place.'),
    ]:
        for i in ids:
            row, shape = old[i]
            moved = shape.translate(tuple(delta))
            assert moved.is_valid and len(moved.solids()) == 1
            records.append({'name': row['name']+'_056', 'shape': moved,
                            'role': purpose, 'mount_body': 'torso', 'nominal_wall_mm': None,
                            'assumptions': ['Rigid translation only; actual supplier geometry and the within-group mounting interfaces are unchanged.',
                                            'Harness service path and thermal/bench qualification remain engineering work.'],
                            'material': row.get('material', 'unchanged_actual_supplier_material'),
                            'original_mass_kg': row.get('mass_kg'),
                            'original_metadata': row,
                            'rigid_displacement_mm': delta.tolist(),
                            'replacement_for': row['name'], 'replaces': [row['name']],
                            'original_native_part_index': i})

    def bore(x,z,r,y0,y1):
        return b.Solid.make_cylinder(r,y1-y0,b.Plane(origin=(x,y0,z),z_dir=(0,1,0)))
    # A constant-thickness CNC outline trims the insulating plate's unused
    # rear-lower corner; all PCB/capacitor receiving geometry is unchanged.
    # The cutting outline comes from a real cavity section, not a display mesh.
    cavity = b.import_brep(str(out/'lighter_inner_cavity.brep'))
    profile = b.section(cavity, section_by=b.Plane.XZ.offset(45.65))
    assert len(profile.faces()) == 1
    mask = b.Solid.extrude(profile.faces()[0], (0,8,0))
    old_base = old[1285][1]
    base_before_bore = _solid(old_base.intersect(mask))
    new_base = _solid(base_before_bore.cut(bore(-185,334,1.6,-46,-39)))
    assert new_base.is_valid and len(new_base.solids()) == 1
    records.append({'name': 'coil12_unclad_g10_mechanical_base_056', 'shape': new_base,
                    'role': 'Original G10 insulating receiver with a clean CNC lower outline and relocated real lower M3 clearance bore.',
                    'mount_body': 'torso', 'nominal_wall_mm': None,
                    'assumptions': ['PCB M2 bores, standoffs, upper M3 root and all electrical component positions are unchanged.',
                                    'Lower M3 clearance bore is3.2mm at X=-185,Z334; associated screw/washer and actual host tap move with it.',
                                    'Outline is a planar cavity section extruded through the original thickness, compatible with CNC profile cutting.'],
                    'material': old[1285][0].get('material','unclad_g10'),
                    'density_kg_m3': old[1285][0].get('density_kg_m3',1850.),
                    'replacement_for': old[1285][0]['name'], 'replaces': [old[1285][0]['name']],
                    'original_native_part_index':1285,
                    'old_volume_mm3':float(old_base.volume), 'new_volume_mm3':float(new_base.volume)})

    row, frame = old[1280]
    # Retire the old protruding tab AND its old lower receiving station, not by
    # leaving an unfastened fixture: a new full4mm M3 tap and matching hardware
    # are established10mm forward in the existing continuous landing.
    dead_corner = _box([-210,-49.4,330.0],[-188.5,-45.2,340.8])
    frame_before_bore = _solid(frame.cut(dead_corner))
    new_frame = _solid(frame_before_bore.cut(bore(-185,334,1.25,-49.4,-45.2)))
    assert new_frame.is_valid and len(new_frame.solids()) == 1
    records.append({'name': 'rear_auxiliary_service_receiving_frame_056', 'shape': new_frame,
                    'role': 'Existing6061 rear receiver frame with unused protruding lower corner removed and a true4mm-engagement lower M3 receiver10mm forward.',
                    'mount_body': 'torso', 'nominal_wall_mm': None,
                    'assumptions': ['Original main spine mounting holes and other device stations preserved.',
                                    'Upper coil M3 and every PCB/electrical interface stay in place; only the lower complete fixing station is relocated.',
                                    'Four-millimetre6061 landing is retained; structural bench/vibration qualification remains pending.'],
                    'material': 'aluminium_6061_t6', 'density_kg_m3': 2700.,
                    'replacement_for': row['name'], 'replaces': [row['name']],
                    'original_native_part_index': 1280,
                    'old_volume_mm3': float(frame.volume),
                    'new_volume_mm3': float(new_frame.volume),
                    'coil_lower_fixing_station_displacement_mm': coil_delta.tolist(),
                    'protected_main_root_axes_world_yz_mm': [[27.5,369.],[27.5,393.]],
                    'coil_root_xz_mm_before': [[-171.25,358.],[-195.,334.]],
                    'coil_root_xz_mm_after': [[-171.25,358.],[-195.+coil_delta[0],334.]],
                    'coil_thread_landing_thickness_mm': 4.,
                    'coil_minimum_original_radial_edge_ligament_mm': 2.25})
    # Prove the new bores pass real, complete material, and that the small
    # corner edit has not consumed a retained PCB or main-spine interface.
    g10_removed = float(base_before_bore.volume-new_base.volume)
    metal_removed = float(frame_before_bore.volume-new_frame.volume)
    assert abs(g10_removed-np.pi*1.6**2*1.6)<1e-5
    assert abs(metal_removed-np.pi*1.25**2*4.)<1e-5
    g10_ring = _solid(bore(-185,334,3.,-45.3,-43.7).cut(bore(-185,334,1.6,-45.4,-43.6)))
    metal_ring = _solid(bore(-185,334,3.5,-49.3,-45.3).cut(bore(-185,334,1.25,-49.4,-45.2)))
    assert abs(_common_volume(new_base,g10_ring)-g10_ring.volume)<1e-5
    assert abs(_common_volume(new_frame,metal_ring)-metal_ring.volume)<1e-5
    preserved = []
    for label,old_shape,new_shape,region in [
        ('coil_PCB_M2_0',old_base,new_base,_box([-195,-45.4,350.5],[-188.4,-39.6,357.])),
        ('coil_PCB_M2_1',old_base,new_base,_box([-182,-45.4,337.1],[-175.2,-39.6,344.])),
        ('coil_upper_M3',old_base,new_base,_box([-174.5,-45.4,354.7],[-167.9,-39.6,361.3])),
        ('main_spine_M3_0',frame,new_frame,_box([-209,23.8,365.3],[-197,31.2,372.7])),
        ('main_spine_M3_1',frame,new_frame,_box([-209,23.8,389.3],[-197,31.2,396.7])),
    ]:
        old_volume = _common_volume(old_shape,region)
        new_volume = _common_volume(new_shape,region)
        assert old_volume>0 and abs(old_volume-new_volume)<1e-5,(label,old_volume,new_volume)
        preserved.append({'interface':label,'old_material_mm3':old_volume,'new_material_mm3':new_volume})
    witness = {'g10_full_actual_clearance_bore_removed_mm3':g10_removed,
               'metal_full_actual_tap_bore_removed_mm3':metal_removed,
               'metal_actual_thread_landing_thickness_mm':4.,
               'metal_radial_edge_ligament_mm':2.25,
               'g10_minimum_nominal_radial_edge_ligament_mm':1.4,
               'g10_full_bearing_ring_supported_mm3':float(g10_ring.volume),
               'metal_full_bearing_ring_supported_mm3':float(metal_ring.volume),
               'preserved_interfaces':preserved,
               'electrical_components_or_harness_poses_changed':False,
               'small_fan_displacement_mm':fan_delta.tolist()}
    (out/'new_root_material_witness.json').write_text(json.dumps(witness,indent=2)+'\n')
    return records


def build(context) -> list[dict]:
    root = Path(_ctx(context, 'root', ROOT))
    out = Path(_ctx(context, 'artifacts', root / 'artifacts/goose_v0_2/enclosure_refinement_056/body'))
    out.mkdir(parents=True, exist_ok=True)
    pivots = _ctx(context, 'pivots')
    if pivots is None:
        contract = json.loads((root / 'robots/goose_v0_2/models/physics_v0_2_20261021_15_candidate/physical_contract.json').read_text())
        pivots = {j['name']: np.asarray(j['pivot_world_at_zero_m']) * 1000 for j in contract['joints']}
    handoff_path = root / 'robots/goose_v0_2/cad/source/enclosure_refinement_056/mango_outer_input_identity.json'
    handoff = json.loads(handoff_path.read_text())
    source = handoff['mother_before_cups']['outer_solid']
    submitted_input = root/'robots/goose_v0_2/cad/source/enclosure_refinement_056/mango_outer_input.brep'
    source_path = Path(_ctx(context,'mango_outer_source',submitted_input if submitted_input.exists() else source['path']))
    assert _identity(source_path, root)['sha256'] == source['sha256']
    outer = _solid(b.import_brep(str(source_path)))
    inner = outer.scale(.98, about=(-69, 0, 348))
    b.export_brep(outer, str(out / 'unchanged_mango_outer.brep'))
    b.export_brep(inner, str(out / 'lighter_inner_cavity.brep'))
    actual_outer,actual_inner=_closed_belly(outer,inner,out)
    stock = _solid(actual_outer.cut(actual_inner))

    # A round interface follows the actual pitch rotor instead of cutting a
    # rectangular staircase down through the belly. The other hip axes remain
    # inside the actual torso volume; the fit audit checks them explicitly.
    hip = np.asarray(pivots['left_hip_pitch'], dtype=float)
    hip_tool = _cyl(hip, 49.7)
    body = _solid(stock.cut(hip_tool))
    # The moving hip enclosure supplies the continuous nested spherical neck;
    # adding another stationary annulus here would obstruct the R49.0 moving
    # neck. Keep its 0.7mm nominal radial gap rather than a false fused joint.

    # A single quiet neck-root opening around the actual yaw hood and pitch
    # cradle, not the old disconnected notches. The cut starts above internal
    # yaw hardware and leaves the original body belly untouched.
    neck_tool = b.extrude(b.Plane(origin=(28, -2, 412)) * b.Ellipse(43.0, 57.5), amount=130)
    body = _solid(body.cut(neck_tool))

    # Preserve the established service split station. Only the service boundary
    # divides the skin; it is not colour blocking or an ornamental panel.
    front = _solid(body.intersect(_box([-69.9, -180, 200], [160, 180, 500])))
    rear = _solid(body.intersect(_box([-300, -180, 200], [-70.6, 180, 500])))
    attachments=_mount_inputs(str(root),str(out))
    front,rear=_restore_attachments(front,rear,attachments[656],outer,out)
    rear=_regular_vents(rear)
    current=b.Compound(children=[front,rear]);structural_witness=[]
    for i in [1108,1160,1212,1243]:
        common=_common_volume(current,attachments[i])
        structural_witness.append({'original_native_part_index':i,'actual_intersection_mm3':common})
    (out/'retained_structural_clearance.json').write_text(json.dumps(structural_witness,indent=2)+'\n')
    common_assumptions = [
        'Actual outer Bezier mango mother inherited without global scaling or fattening; only two closed hidden lower-skin clearance saddles move locally inward.',
        '0.98 homothetic cavity about [-69,0,348]mm; variable wall, NOT constant 2.5mm.',
        'Nonstructural polymer enclosure; primary hardware, load path and axis positions retained.',
        'Static interface audit is not a full-ROM, thermal, fastening or manufacturing qualification.',
        'Tail cap uses the existing X=-70.25mm service station with 0.7mm assembly gap.',
        'One six-row rear exhaust bank at the existing60mm fan: two25mm straight-ended slots per row and 3mm uncut central protective spine; airflow pressure drop unqualified.',
        'Four real side-entry M3 cap stations retained: printed AF3.3 hexagonal clearance and shallow AF6.2 head seat on original axes; actual round M3 shaft/head fit inside these explicit across-flat dimensions.',
        'Original hidden frame ribs, captive-nut interfaces and cap tongues retained; unused exterior continuation bores blinded at X77.7mm, beyond actual M3 shaft ends X77.45mm.',
    ]
    records = []
    for name, shape, role in [
        ('front_main_shell_056', front, 'Smooth intact belly, tight nested side hip openings and neck root'),
        ('rear_service_cap_056', rear, 'Continuous raised tapered tail with one regular exhaust bank'),
    ]:
        assert shape.is_valid and len(shape.solids()) == 1 and shape.volume > 0, name
        shape.label = name
        records.append({'name': name, 'shape': shape, 'role': role, 'mount_body': 'torso',
                        'nominal_wall_mm': None, 'assumptions': list(common_assumptions),
                        'material': 'PETG_nonstructural_cover_budget_1270kgm3',
                        'density_kg_m3': 1270.0,
                        'replacement_for': 'front_main_shell' if 'front' in name else 'rear_service_cap',
                        'replaces': ['front_main_shell' if 'front' in name else 'rear_service_cap']})
    if _ctx(context, 'include_light_remounts', True):
        records += _light_remounts(root, out, context)
    metadata = {
        'schema': 'goose_body_enclosure_056/1', 'outer_source': _identity(source_path, root),
        'outer_input_identity': _identity(handoff_path,root),
        'outer_original_source_sha256':source['sha256'],
        'module_source':_identity(Path(__file__),root),
        'outer_mother_input_unchanged':True,
        'global_scaling_or_enlargement':False,
        'local_closed_belly_clearance':{'centres_mm':[[-12,-75,223],[-12,75,223]],'tool_radii_mm':[60,16,38.5],
                                      'internal_tool_radii_mm':[63,19,41.5],'outer_blend_mm':2.,
                                      'maximum_sampled_vertical_inset_mm':8.188623492438495,
                                      'sample_scope':'27x25 rays, not a certified global maximum; no through-opening'},
        'old_mother_skin_volume_mm3': 855005.0962604987,
        'stock_volume_mm3': float(stock.volume),
        'stationary_hip_lip_added': False, 'hip_mouth_radius_mm': 49.7,
        'moving_hip_neck_nominal_radius_mm': 49.0,
        'cap_fastener_clearance':{'type':'regular_hexagonal_printed_clearance','through_across_flats_mm':3.3,'shallow_seat_across_flats_mm':6.2,'shared_axes_xz_mm':[[-76,295],[-76,415]]},
        'frame_fastener_blind_bore':{'closure_start_x_mm':77.7,'actual_bolt_max_x_mm':77.45,'nominal_end_clearance_mm':.25,'original_nut_and_inside_assembly_entry_retained':True},
        'rear_vent_bank':{'rows':6,'row_centres_z_mm':[363,371,379,387,395,403],'slots_per_row':2,'slot_width_mm':25.,'slot_height_mm':4.2,'corner_radius_mm':0.,'uncut_central_spine_width_mm':3.,'overall_width_mm':53.,'projected_net_open_area_mm2':6*2*25*4.2,'baseline_six_single_slot_area_mm2':6*(50*4.2-(4-np.pi)),'flow_and_pressure_drop_not_measured':True,'bounded_R1_failure':'both all48 and sequential4 native corner constructions failed; planar ends selected, no geometric tolerance relaxation'},
        'neck_root_ellipse_radii_mm': [43.0, 57.5],
        'neck_root_ellipse_center_xy_mm': [28.0, -2.0],
        'parts': [{'name': r['name'], 'volume_mm3': float(r['shape'].volume),
                   'replacement_for':r.get('replacement_for'),
                   'rigid_displacement_mm':r.get('rigid_displacement_mm'),
                   'original_native_part_index':r.get('original_native_part_index'),
                   'mass_kg_at_explicit_density': (float(r['shape'].volume)*r['density_kg_m3']*1e-9
                                                  if 'density_kg_m3' in r else r.get('original_mass_kg')),
                   'bounds_mm': _bounds(r['shape']), 'valid': bool(r['shape'].is_valid),
                   'solids': len(r['shape'].solids()), 'assumptions': r['assumptions']}
                  for r in records],
    }
    (out / 'build_receipt.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return records


def _static_audit(records, root, out, quick=False):
    """Native exact intersections, separately recording old cover replacements."""
    index = json.loads((root / 'robots/goose_v0_2/cad/source/drag_hardware_integration_009_08/assembly_index.json').read_text())['parts']
    native_path = root / 'artifacts/goose_v0_2/design_cleanup_052/native08_readback.brep'
    started = time.monotonic()
    print(json.dumps({'event': 'native_read_start'}), flush=True)
    actual = list(b.import_brep(str(native_path)).solids())
    assert len(actual) == len(index) == 1827
    updated = {}
    for r in records:
        if 'original_native_part_index' in r:
            i = r['original_native_part_index']
            actual[i] = r['shape']
            updated[i] = r
    body = b.Compound(children=[r['shape'] for r in records if r['name'] in ('front_main_shell_056','rear_service_cap_056')])
    # Large native-proved empty interior boxes cover the dense supplier PCB
    # inventories. A part's entire AABB inside one such box is a rigorous zero
    # intersection proof, avoiding thousands of redundant complex OEM Booleans.
    outer = b.import_brep(str(out/'unchanged_mango_outer.brep'))
    macro_candidates = [
        [[-201,-25,345],[-155,35,422]],
        [[-90,-21,418],[-20,22,443]],
        [[-153,-44,292],[-89,29,416]],
        [[-70,-55,280],[62,55,410]],
        [[-164,48,345],[-115,78,407]],
        [[-120,45,342],[-69,63,424]],
        [[-70,-30,345],[-25,30,410]],
        [[-14,-55,350],[63,55,410]],
    ]
    safe = []
    macro_proofs = []
    for lo,hi in macro_candidates:
        cube = _box(lo,hi)
        hit = _common_volume(body,cube)
        outside = cube.volume-_common_volume(outer,cube)
        passed = hit < 1e-6 and abs(outside) < 1e-3
        macro_proofs.append({'bounds_mm':[lo,hi], 'body_common_mm3':hit,
                             'outside_mango_mm3':outside,'proved_safe':passed})
        if passed:
            safe.append((np.asarray(lo),np.asarray(hi),len(macro_proofs)-1))
    checks, skipped = [], []
    priorities = (list(range(0, 7)) + list(range(427, 435)) +
                  list(range(550, 558)) + list(range(630, 653)) +
                  list(range(680, 710)) + list(range(793, 809)) +
                  list(range(885, 887)) + [907, 945, 1078, 1079, 1086, 1280, 1742])
    priorities += list(updated)
    if not quick:
        priorities += list(range(len(index)))
    processed = 0
    for i in dict.fromkeys(priorities):
        p = index[i]
        if any(s in p['name'] for s in ('front_main_shell', 'rear_service_cap')):
            continue
        bb = actual[i].bounding_box()
        if bb.min.Z > 458 or bb.max.Z < 235 or bb.min.X > 120 or bb.max.X < -250:
            continue
        lo, hi = np.asarray(list(bb.min)), np.asarray(list(bb.max))
        recorded = p.get('native_bounds_mm', p.get('bounds_mm'))
        # The saved native index is authoritative. The assembly source must
        # match it before any numerical common is attributed to a named part.
        if recorded is not None and i not in updated:
            err = float(np.max(np.abs(np.stack([lo, hi])-np.asarray(recorded))))
            assert err < .02, (p['name'], err)
        proof = next((n for ml,mh,n in safe if np.all(lo>=ml) and np.all(hi<=mh)),None)
        if proof is not None:
            bound_volume, volume = 0.0, 0.0
        else:
            bound_volume = _common_volume(body, _box(lo, hi))
            volume = _common_volume(body, actual[i]) if bound_volume > 1e-5 else 0.0
        processed += 1
        checks.append({'index': i, 'name': p['name'], 'body': p.get('body'),
                       'intersection_mm3': volume, 'bounds_mm': [lo.tolist(), hi.tolist()],
                       'native_exact_bbox_prefilter_mm3': bound_volume,
                       'native_proved_interior_macro': proof,
                       'material': p.get('material'), 'mass_kg': p.get('mass_kg'),
                       'is_old_cover_or_surface_feature': any(s in p['name'] for s in ('cover', 'hood', 'skin', 'service_lid'))})
        if processed % 100 == 0:
            print(json.dumps({'event': 'fit_progress', 'index': i, 'checks': processed}), flush=True)
            (out / 'static_fit_checkpoint.json').write_text(json.dumps({'checks': checks}, indent=2)+'\n')
    result = {'scope': 'exact native worldzero shell-vs-selected-actual-installed-solids',
              'quick': quick, 'native_solids': len(actual), 'checks': checks,
              'native_empty_interior_macro_proofs':macro_proofs,
              'intersections': [c for c in checks if c['intersection_mm3'] > .01],
              'full_motion_qualified': False, 'elapsed_s': time.monotonic()-started}
    (out / 'static_fit_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'artifacts/goose_v0_2/enclosure_refinement_056/body'
    records = build({'root': ROOT, 'artifacts': out})
    for r in records:
        b.export_brep(r['shape'], str(out / (r['name']+'.brep')))
        print(json.dumps({'part': r['name'], 'valid': bool(r['shape'].is_valid),
                          'volume_mm3': float(r['shape'].volume)}), flush=True)
    b.export_step(b.Compound(children=[r['shape'] for r in records]), str(out/'body_056.step'))
    if args.audit:
        report = _static_audit(records, ROOT, out, args.quick)
        print(json.dumps({'intersections': report['intersections']}), flush=True)


if __name__ == '__main__':
    main()
