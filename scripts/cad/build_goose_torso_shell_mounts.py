"""Four internal frame-to-roof mounts; preserve the frozen446 head candidate.

Shell bosses remain as-printed pilot holes. Heat-insert interference is an
explicit installation allowance, not a rigid-body collision exemption.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

import numpy as np
from build123d import Pos, RegularPolygon, extrude, import_brep

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad')]
from build_goose_cad import box, cylinder, holes, transform
from goose_candidate_export import CandidateExport
from goose_nurbs_skin import surface
from goose_structured_shell_export import emit_structured_shell
from build_goose_power_module_mounts import nominal_screw, washer
from sai_agent.goose.morphology import body_grids
from sai_agent.goose.mass_properties import aggregate_rigid_components


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alignment(normal):
    x = np.array([1., 0., 0.])
    x -= normal * np.dot(normal, x)
    x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(normal, x), normal])


def strut(a, b, width, thickness):
    delta = b-a
    z = delta / np.linalg.norm(delta)
    x = np.array([1., 0., 0.])
    x -= z * np.dot(x, z)
    x /= np.linalg.norm(x)
    rotation = np.column_stack([x, np.cross(z, x), z])
    return transform(box([width, thickness, np.linalg.norm(delta)+2]), rotation, (a+b)/2)


def main():
    cfg_path = ROBOT / 'configs/torso_shell_mounts.json'
    layout_path = ROBOT / 'configs/body_bay_layout_candidate.json'
    scene_path = ROBOT / 'cad/source/camera_closure_fixture/assembly_scene.json'
    parameter_path = ROBOT / 'evidence/camera_head_closure_parameters.json'
    cfg, layout, old_scene, old_parameters = [json.loads(p.read_text()) for p in
        [cfg_path, layout_path, scene_path, parameter_path]]
    if sha(scene_path) != cfg['source_scene_sha256']:
        raise ValueError('Frozen446 input changed')
    for relative, digest in old_parameters['source_hashes'].items():
        if sha(ROOT / relative) != digest:
            raise ValueError(('Changed parameter input', relative))
    vendor = cfg['insert']
    for kind in ['step', 'drawing']:
        if sha(ROOT / vendor['manufacturer_'+kind+'_path']) != vendor['manufacturer_'+kind+'_sha256']:
            raise ValueError('Changed manufacturer input')
    if cfg['boss_radius_mm']-vendor['max_nominal_od_mm']/2 < vendor['minimum_radial_wall_mm']:
        raise ValueError('Boss wall below manufacturer minimum')
    export = CandidateExport(ROBOT, 'torso_shell_mounts')
    replaced, interfaces, threads, inputs = [], [], [], [cfg_path, layout_path, scene_path, parameter_path,
        Path(__file__), ROOT / 'scripts/cad/goose_candidate_export.py',
        ROOT / 'scripts/cad/goose_nurbs_skin.py', ROOT / 'scripts/cad/build_goose_cad.py',
        ROOT / 'scripts/cad/goose_structured_shell_export.py',
        ROOT / 'scripts/cad/build_goose_power_module_mounts.py',
        ROOT / 'src/sai_agent/goose/morphology.py', ROOT / 'src/sai_agent/goose/mass_properties.py']
    for anchor in cfg['anchors']:
        label, side, x = anchor['name'], anchor['side'], anchor['x_mm']
        out, inside = body_grids(layout['body_profile_x_cz_ry_rz_mm'], side,
            layout['body_wall_mm'], layout['lower_limb_exit_boundary_u_v'])
        outer, inner = surface(out), surface(inside)
        lo, hi, v = 0., 1., cfg['roof_surface_v']
        for _ in range(45):
            u = (lo+hi)/2
            if outer.Value(u, v).X() < x:
                lo = u
            else:
                hi = u
        u = (lo+hi)/2
        p, pi = np.array(outer.Value(u, v).Coord()), np.array(inner.Value(u, v).Coord())
        normal = (p-pi)/np.linalg.norm(p-pi)
        rotation = alignment(normal)
        entry = p-normal*cfg['boss_inside_entry_depth_mm']
        def place(shape):
            return transform(shape, rotation, entry)
        old_path = ROBOT / anchor['source_shell']
        inputs.append(old_path)
        shell = import_brep(old_path)
        boss_height = cfg['boss_inside_entry_depth_mm']-cfg['boss_outer_end_depth_mm']
        boss = place(cylinder(cfg['boss_radius_mm'], boss_height, [0, 0, boss_height/2]))
        # A blind hole opened from the inside leaves the exterior intact.
        pilot = place(cylinder(cfg['insert_pilot_diameter_mm']/2,
            cfg['insert_pilot_depth_mm']+.02, [0, 0, cfg['insert_pilot_depth_mm']/2-.01]))
        shell = (shell+boss)-pilot
        shell_name = 'torso_mounted_shell_'+label
        old_npz=ROBOT/next(p['geometry_npz'] for p in old_scene['parts'] if p['name']==anchor['replaces_shell'])
        inputs.append(old_npz)
        emit_structured_shell(export,shell_name,shell,old_npz,boss,pilot)
        replaced.append(anchor['replaces_shell'])
        zbase, y = anchor['base_z_mm'], side*34.
        foot = box(cfg['frame_flange_mm'], [x, side*36., zbase+1])
        knee = np.array([x, side*cfg['stem_abs_y_mm'], cfg['stem_turn_z_mm']])
        start = np.array([x, side*cfg['stem_abs_y_mm'], zbase+1])
        roof_center = entry-normal*cfg['roof_pad_thickness_mm']/2
        carrier = foot+strut(start, knee, *cfg['brace_section_mm'])
        # Reach the pad's outer ligament so the socket corridor does not sever
        # the load path. The screw and tool remain on the original pad axis.
        carrier += strut(knee, roof_center+rotation[:,0]*5., *cfg['brace_section_mm'])
        carrier += place(cylinder(cfg['roof_pad_radius_mm'], cfg['roof_pad_thickness_mm'],
            [0, 0, -cfg['roof_pad_thickness_mm']/2]))
        carrier = holes(carrier, [[x, y, zbase+1]], 3.2, 12, 'z')
        carrier -= place(cylinder(1.6, 40, [0, 0, -12]))
        # Keep a real socket/tool corridor behind the roof bearing pad.
        carrier -= place(cylinder(4., 32., [0, 0, -18.5]))
        # The brace must approach only the pad underside, never enter the
        # boss or insert above its bearing plane. Keep0.25mm radial clearance.
        carrier -= place(cylinder(cfg['boss_radius_mm']+cfg['boss_carrier_radial_clearance_mm'],20.,[0,0,10.]))
        carrier_name = 'torso_roof_frame_carrier_'+label
        export.emit(carrier_name, carrier, 'torso', rho=2700, material='graphite', notes=[
            'Monolithic6061 machining candidate:8x3mm brace,2mm frame flange,2.5mm roof pad.',
            'Shared existing M3 chassis anchor; no adhesive or exterior fastener.',
            'Machining path, fillets, local strength, clamp preload and fatigue remain gates.'])
        insert_name = 'torso_roof_m3_insert_'+label
        insert = cylinder(vendor['max_nominal_od_mm']/2, vendor['length_mm'], [0, 0, vendor['length_mm']/2])
        insert -= cylinder(vendor['thread_minor_envelope_mm']/2, 10, [0, 0, 3])
        export.emit(insert_name, place(insert), 'torso', rho=vendor['nominal_brass_density_kg_m3'],
            material='titanium', notes=['Own maximum nominal OD/length envelope, not a printable insert or redistributed supplier CAD.',
                'Conservative solid-envelope brass mass/inertia; purchased revision, density and actual thread/knurl tolerances unqualified.'])
        roof_washer = 'torso_roof_washer_'+label
        wt = cfg['roof_washer_mm'][2]
        pad = cfg['roof_pad_thickness_mm']
        ring = cylinder(cfg['roof_washer_mm'][0]/2, wt, [0, 0, -pad-wt/2])
        ring -= cylinder(cfg['roof_washer_mm'][1]/2, 3, [0, 0, -pad-wt/2])
        export.emit(roof_washer, place(ring), 'torso', rho=7850, material='graphite')
        screw_name = 'torso_roof_m3x8_'+label
        diameter, length, head_od, head_height = cfg['roof_screw_mm']
        bearing = -pad-wt
        screw = cylinder(diameter/2, length, [0, 0, bearing+length/2])
        screw += cylinder(head_od/2, head_height, [0, 0, bearing-head_height/2])
        export.emit(screw_name, place(screw), 'torso', rho=7850, material='graphite')
        engagement = length-pad-wt
        threads.append(dict(screw=screw_name, tapped_part=insert_name, engagement_mm=engagement,
            expected_thread_overlap_mm3=float(np.pi*((diameter/2)**2-(vendor['thread_minor_envelope_mm']/2)**2)*engagement)))
        prefix = anchor['frame_group']
        top_z = zbase+2
        if prefix.startswith('compute'):
            top_washer = prefix+'_top_washer'
            screw = prefix+'_m3x16'
            nut_name = prefix+'_raised_m3_nut'
            export.emit(top_washer, washer([x, y], top_z, 7, 3.2, .5), 'torso', rho=7800, material='graphite')
            shape = cylinder(1.5, 16, [x, y, 309.4+8])+cylinder(2.75, 3, [x, y, 307.9])
            export.emit(screw, shape, 'torso', rho=7800, material='graphite')
            nut = Pos(x, y, top_z+.5)*extrude(RegularPolygon(5.5/3**.5, 6), amount=2.4)
            nut -= cylinder(1.2, 6, [x, y, top_z+1.7])
            export.emit(nut_name, nut, 'torso', rho=7800, material='graphite')
            threads.append(dict(screw=screw, tapped_part=nut_name, engagement_mm=2.4,
                expected_thread_overlap_mm3=float(np.pi*(1.5**2-1.2**2)*2.4)))
            replaced += [prefix+'_top_washer', prefix+'_m3x12', prefix+'_m3_nut']
            frame_stack = dict(bearing_z_mm=309.4, tip_z_mm=325.4, total_stack_mm=10.4, protrusion_mm=5.6)
        else:
            top_washer = prefix+'_top_washer'
            screw = prefix+'_m3x20'
            export.emit(top_washer, washer([x, y], top_z, 6, 3.2, .5), 'torso', rho=7800, material='graphite')
            export.emit(screw, nominal_screw([x, y], top_z+.5, 3, 20, 5.5, 3), 'torso', rho=7800, material='graphite')
            threads.append(dict(screw=screw, tapped_part=prefix+'_m3_nut', engagement_mm=2.4,
                expected_thread_overlap_mm3=float(np.pi*(1.5**2-1.25**2)*2.4)))
            replaced += [prefix+'_top_washer', prefix+'_m3x18']
            frame_stack = dict(bearing_z_mm=326.4, tip_z_mm=306.4, total_stack_mm=17.4, protrusion_mm=2.6)
        interfaces.append(dict(name=label, source_surface_uv=[u, v], outer_point_mm=p.tolist(),
            inner_point_mm=pi.tolist(), outward_normal=normal.tolist(), insert_entry_mm=entry.tolist(),
            rotation_from_insert_z=rotation.tolist(), replaced_shell=anchor['replaces_shell'],
            mounted_shell=shell_name, roof_carrier=carrier_name, insert=insert_name,
            intentional_as_printed_heat_insert_interference_mm3=float(np.pi*((4.6/2)**2-(4/2)**2)*5.7),
            insert_tip_clearance_mm=5.7-engagement, frame_anchor_mm=[x, y, zbase], frame_stack=frame_stack))
        print('SHELL MOUNT', label, 'native', len(export.parts), flush=True)
    # Old frame screw groups can be conservative aggregate bounds rather than
    # individual ledger items; retain that allowance and add only their changes.
    old_items = {p['name']:copy.deepcopy(p) for p in old_parameters['items']}
    parts = {p['name']:copy.deepcopy(p) for p in old_scene['parts']}
    for name in replaced:
        if name not in parts:
            raise ValueError(('Replacement absent', name))
        parts.pop(name)
    removed_mass = 0.
    for name in replaced:
        if name in old_items:
            removed_mass += old_items.pop(name)['mass_kg']
    lift = old_parameters['rigid_coordinate_lift_m']
    # The two forward neck screws and their washers are already represented by
    # retained whole-stack upper bounds. Only2mm extra shafts add physical mass.
    aggregate_bound_parts = set()
    for anchor in cfg['anchors']:
        if anchor['frame_group'].startswith('neck'):
            prefix=anchor['frame_group']
            aggregate_bound_parts |= {prefix+'_top_washer', prefix+'_m3x20'}
            name='torso_roof_extra_m3_shaft_'+anchor['name']
            added_mass=np.pi*1.5**2*2*7800e-9
            radius,length=.0015,.002
            transverse=added_mass*(3*radius**2+length**2)/12
            axial=added_mass*radius**2/2
            old_items[name]=dict(name=name,body='torso',mass_kg=added_mass,
                center_m=[anchor['x_mm']/1000,anchor['side']*.034,(325.4/1000)+lift],
                inertia_at_com_kg_m2=np.diag([transverse,transverse,axial]).tolist(),relative_uncertainty=.1,
                basis='Additional2mm shaft upper bound; original conservative neck screw/washer aggregate retained')
    for p in export.parts:
        if p['name'] not in aggregate_bound_parts:
            old_items[p['name']]=dict(name=p['name'],body=p['body'],mass_kg=p['mass_kg'],
                center_m=(np.array(p['center_of_mass_world_m'])+[0,0,lift]).tolist(),
                inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],relative_uncertainty=.1,
                basis='Same-source native density / conservative bought envelope; material and print fit unqualified')
    for p in export.scene:
        if p['name'] in parts:
            raise ValueError(('Duplicate new scene name',p['name']))
        parts[p['name']]=copy.deepcopy(p)
    mass=sum(p['mass_kg'] for p in old_items.values())
    kit=export.save(ROOT,inputs,replaces=replaced,extra=dict(
        interfaces=interfaces,nominal_thread_contacts=threads,skin_mounting_candidate=True,
        exterior_profile_authoring_grid_unchanged=True,wing_hinge_and_latch_included=False,
        net_physical_mass_change_kg=mass-old_parameters['nominal_conditional_mass_kg'],
        source446_unchanged=True,manufacturing_release=False,
        limitations=['Four fixed roof shell points only; seam supports, doors, end plugs and local strength remain gates.',
            'Printed pilot/insert envelope interference represents heat setting; not rigid installed geometry acceptance.',
            'Full body/driver/connector clearance and fresh same-source static screen must follow before adoption.']))
    kit_path=ROBOT/'cad/exports/torso_shell_mounts/manifest.json'
    items=list(old_items.values())
    parameters=dict(schema='goose_torso_shell_mount_parameters_v1',parts=len(parts),active_axes=18,
        nominal_conditional_mass_kg=mass,delta_from446_kg=mass-old_parameters['nominal_conditional_mass_kg'],
        items=items,bodies=[dict(name=b['name'],**aggregate_rigid_components(
            [p for p in items if p['body']==b['name']],old_parameters['pivots_world_at_zero_m'][b['name']]))
            for b in old_parameters['bodies']],pivots_world_at_zero_m=old_parameters['pivots_world_at_zero_m'],
        rigid_coordinate_lift_m=lift,neutral_joint_order=old_parameters['neutral_joint_order'],
        full_assembly_pass=False,manufacturing_release=False,training_release=False,final_appearance_pass=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs+[kit_path]})
    parameter_out=ROBOT/'evidence/torso_shell_mount_parameters.json'
    parameter_out.write_text(json.dumps(parameters,indent=2)+'\n')
    source=ROBOT/'cad/source/torso_shell_mount_fixture';source.mkdir(exist_ok=True)
    preview=dict(unit='m',parts=list(parts.values()),assembly_translation_m=old_scene['assembly_translation_m'],
        nominal_conditional_mass_kg=mass,status='INTERNAL_SHELL_SUPPORT_CANDIDATE_NOT_RELEASED',
        manufacturing_pass=False,final_appearance_pass=False,source_hashes={
            str(parameter_out.relative_to(ROOT)):sha(parameter_out),str(kit_path.relative_to(ROOT)):sha(kit_path)},
        review_views=old_scene.get('review_views',{}),review_ortho_scale_m=old_scene.get('review_ortho_scale_m',{}))
    (source/'assembly_scene.json').write_text(json.dumps(preview,separators=(',',':'))+'\n')
    print('SHELL FIXTURE',len(parts),'source objects',mass,'kg; delta',parameters['delta_from446_kg'],flush=True)


if __name__=='__main__':
    main()
