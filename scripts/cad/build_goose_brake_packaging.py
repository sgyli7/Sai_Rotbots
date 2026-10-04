"""Independent brake installation candidate, raw zero-pose millimetres.

Purchased parts are conservative nominal envelopes, never printable hardware
or an electrical/thermal release. The frozen training model is not modified.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

import numpy as np
from build123d import Plane, Polygon, Pos, RegularPolygon, extrude, import_brep

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_cad import box, cylinder, transform
from goose_candidate_export import CandidateExport
from sai_agent.goose.mass_properties import aggregate_rigid_components


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alignment(direction):
    z = np.asarray(direction, dtype=float)
    z /= np.linalg.norm(z)
    seed = [0, 0, 1] if abs(z[2]) < .9 else [1, 0, 0]
    x = np.cross(seed, z)
    x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def screw(length, head_d=5.5, head_h=3., socket_af=2.5, socket_depth=1.6):
    # ISO4762 nominal maximum outside geometry; simplified unthreaded shaft.
    shape = cylinder(1.5, length, [0, 0, length/2]) + cylinder(head_d/2, head_h, [0, 0, -head_h/2])
    socket = Pos(0, 0, -head_h-.01) * extrude(RegularPolygon(socket_af/np.sqrt(3), 6), amount=socket_depth+.01)
    return shape - socket


def washer():
    return cylinder(3.5, .5, [0, 0, .25]) - cylinder(1.6, 2, [0, 0, .25])


def nut(height=4.):
    shape = extrude(RegularPolygon(5.5/np.sqrt(3), 6), amount=height)
    # Clearance rather than intersecting nominal threads; no preload proof.
    return shape - cylinder(1.6, height+2, [0, 0, height/2])


def main():
    cp = R / 'configs/brake_packaging_candidate.json'
    cfg = json.loads(cp.read_text())
    sp, pp, ep, ip, lp = [R/cfg[k] for k in ['source_scene', 'source_parameters',
        'source_chopper_config', 'source_native_inventory', 'source_layout']]
    for path, expected in [(sp, cfg['source_scene_sha256']), (ep, cfg['source_chopper_sha256']),
                           (R/cfg['chassis']['source_brep'], cfg['chassis']['source_sha256'])]:
        if sha(path) != expected:
            raise ValueError(('Changed packaging input', path))
    scene, params = [json.loads(p.read_text()) for p in [sp, pp]]
    export = CandidateExport(R, 'brake_packaging')
    inputs = [cp, sp, pp, ep, ip, lp, R/cfg['chassis']['source_brep'], Path(__file__),
        ROOT/'scripts/cad/goose_candidate_export.py', ROOT/'scripts/cad/build_goose_cad.py',
        ROOT/'scripts/cad/goose_nurbs_skin.py', ROOT/'scripts/cad/build_goose_actuator_interfaces.py',
        ROOT/'src/sai_agent/goose/mass_properties.py']
    rot = np.array(cfg['plate']['orientation_local_xyz_to_world'])
    origin = np.array(cfg['plate']['centre_mm'])
    size = cfg['plate']['size_mm']
    half_t = size[2]/2
    rd = cfg['resistor']
    pf = cfg['package_fastener']
    w, h, depth = rd['dimensions_mm']
    hole_offset = h/2-rd['hole_from_top_mm']
    plate = box(size)
    contacts, resistor_holes = [], []
    for row_index, row in enumerate(rd['row_centres_local_y_mm']):
        flip = np.diag([-1, -1, 1]) if row > 0 else np.eye(3)
        for col_index, column in enumerate(rd['column_centres_local_x_mm']):
            key = f'brake_rd_{row_index}_{col_index}'
            local = np.array([column, row, 0.])
            shape = box([w, h, depth], [0, 0, half_t+depth/2])
            for x in [-rd['lead_spacing_mm']/2, rd['lead_spacing_mm']/2]:
                wide = rd['lead_initial_length_mm']
                distal = rd['lead_length_mm']-wide
                z = half_t+rd['lead_plane_from_back_mm']
                shape += box([rd['lead_initial_width_mm'], wide, rd['lead_thickness_mm']], [x, -h/2-wide/2, z])
                shape += box([rd['lead_distal_width_mm'], distal, rd['lead_thickness_mm']], [x, -h/2-wide-distal/2, z])
            shape -= cylinder(rd['body_hole_d_mm']/2, depth+2, [0, hole_offset, half_t+depth/2])
            world = transform(shape, rot@flip, origin+rot@local)
            export.emit(key, world, 'torso', material='graphite', catalog_mass=rd['mass_upper_kg'],
                notes=[rd['sku'], 'Vendor maximum 3.5g includes both leads. Own dimension envelope; not OEM CAD or thermal qualification.'])
            xy = (local+flip@np.array([0, hole_offset, 0.]))[:2]
            resistor_holes.append(xy.tolist())
            plate -= cylinder(cfg['plate_clearance_d_mm']/2, size[2]+2, [*xy, 0])
            # Package screw enters from +local Z towards -local Z.
            bolt_origin = origin+rot@np.array([*xy, half_t+depth+.5])
            axis = -rot[:, 2]
            bolt = key+'_m3x16'
            fastener = screw(pf['shaft_length_mm'], pf['head_d_mm'], pf['head_h_mm'],
                             pf['socket_af_mm'], pf['socket_depth_min_mm'])
            export.emit(bolt, transform(fastener, alignment(axis), bolt_origin), 'torso', material='graphite',
                catalog_mass=pf['screw_catalog_mass_kg'], notes=[pf['nominal'], pf['screw_source_url'],
                    pf['screw_dimensions_basis'], 'Own conservative cylindrical head; not printable or OEM CAD; preload unqualified.'])
            wa = key+'_washer'
            export.emit(wa, transform(washer(), alignment(axis), bolt_origin), 'torso', rho=7850, material='graphite')
            nu = key+'_nut'
            export.emit(nu, transform(nut(pf['nut_h_mm']), alignment(axis), origin+rot@np.array([*xy, -half_t])), 'torso', material='graphite',
                catalog_mass=pf['nut_catalog_mass_kg'], notes=['DIN934 all-metal A2 nut; own maximum dimensional envelope; bore omits actual thread.',
                    pf['nut_source_url'], pf['nut_dimensions_basis'], pf['anti_loosen_candidate']])
            contacts += [[key, 'brake_thermal_plate'], [key, wa], [wa, bolt], [nu, 'brake_thermal_plate'],
                         [bolt, key], [bolt, 'brake_thermal_plate'], [bolt, nu]]
    for x, y in cfg['plate_mount_hole_local_xy_mm']:
        plate -= cylinder(cfg['plate_clearance_d_mm']/2, size[2]+2, [x, y, 0])
    export.emit('brake_thermal_plate', transform(plate, rot, origin), 'torso', material='titanium',
        notes=['Own machined aluminium candidate, 2700kg/m3. Not a qualified continuous heat sink.'])
    chassis = import_brep(R/cfg['chassis']['source_brep'])
    old_chassis_volume = chassis.volume
    bc = cfg['brackets']
    yf, zf, yv, zv = [bc[k] for k in ['flange_world_y_range_mm', 'flange_world_z_range_mm',
                                      'vertical_world_y_range_mm', 'vertical_world_z_range_mm']]
    loop = [(yv[0], zv[0]), (yv[1], zv[0]), (yv[1], zf[0]),
            (yf[1], zf[0]), (yf[1], zf[1]), (yv[0], zf[1])]
    for index, x in enumerate(bc['x_centres_mm']):
        key = f'brake_bracket_{index}'
        face = Plane.YZ * Polygon(*loop, align=None)
        bracket = Pos(x-bc['width_mm']/2, 0, 0) * extrude(face, amount=bc['width_mm'], dir=(1, 0, 0))
        bracket -= cylinder(1.6, 6, [x, sum(yv)/2, bc['plate_bolt_world_z_mm']], 'y')
        bracket -= cylinder(1.6, 6, [x, bc['chassis_bolt_world_y_mm'], sum(zf)/2])
        export.emit(key, bracket, 'torso', material='titanium', notes=['Own aluminium L bracket; alloy, bend radius, strength and preload not released.'])
        chassis -= cylinder(1.6, 8, [x, bc['chassis_bolt_world_y_mm'], 313.4])
        pb = key+'_plate_m3x16'
        pz = bc['plate_bolt_world_z_mm']
        export.emit(pb, transform(screw(16), alignment([0, 1, 0]), [x, origin[1]-half_t-.5, pz]), 'torso', rho=7850, material='graphite')
        pw = key+'_plate_washer'
        export.emit(pw, transform(washer(), alignment([0, 1, 0]), [x, origin[1]-half_t-.5, pz]), 'torso', rho=7850, material='graphite')
        pn = key+'_plate_nut'
        export.emit(pn, transform(nut(), alignment([0, 1, 0]), [x, yv[1], pz]), 'torso', rho=7850, material='graphite')
        cb = key+'_chassis_m3x12'
        cy = bc['chassis_bolt_world_y_mm']
        cf = cfg['chassis_fastener']
        envelope = screw(cf['length_mm'], cf['head_d_max_mm'], cf['head_h_max_mm'], cf['socket_af_mm'], cf['socket_depth_min_mm'])
        export.emit(cb, transform(envelope, alignment([0, 0, -1]), [x, cy, 314.9]), 'torso', material='graphite',
            catalog_mass=cf['catalog_mass_kg'], notes=[cf['nominal'], cf['source_url'], cf['dimensions_basis'],
                'Conservative head cylinder, not OEM dome CAD. Supplier/preload/tool path unqualified.'])
        cw = key+'_chassis_washer'
        export.emit(cw, transform(washer(), alignment([0, 0, -1]), [x, cy, zf[0]]), 'torso', rho=7850, material='graphite')
        cn = key+'_chassis_nut'
        export.emit(cn, transform(nut(), alignment([0, 0, -1]), [x, cy, zf[0]-.5]), 'torso', rho=7850, material='graphite')
        contacts += [[key, 'brake_thermal_plate'], [key, 'brake_chassis_plate'],
                     [pw, pb], [pw, 'brake_thermal_plate'], [pn, key],
                     [pb, 'brake_thermal_plate'], [pb, key], [pb, pn],
                     [cb, 'brake_chassis_plate'], [cb, key], [cb, cw], [cb, cn], [cw, key], [cw, cn], [key, cn]]
    export.emit('brake_chassis_plate', chassis, 'torso', material='titanium',
        notes=['Independent replacement of retained compute chassis: two 3.2mm through holes only. Old source preserved.'])
    # No solid mass is fabricated for the PCB draft envelope. The retained 93g
    # protection/board/harness reserve remains at its existing declared centre.
    items = {p['name']: copy.deepcopy(p) for p in params['items']}
    replaces = [cfg['chassis']['name'], 'brake_hardware_extra_allocation']
    removed = {name: items.pop(name) for name in replaces}
    lift = params['rigid_coordinate_lift_m']
    for p in export.parts:
        items[p['name']] = dict(name=p['name'], body=p['body'], mass_kg=p['mass_kg'],
            center_m=(np.asarray(p['center_of_mass_world_m'])+[0, 0, lift]).tolist(),
            inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
            basis=p['mass_basis']+'; bracket/alloy/preload or catalogue upper mass unqualified')
    all_items = list(items.values())
    mass = sum(p['mass_kg'] for p in all_items)
    kit = export.save(ROOT, inputs, replaces=replaces, extra=dict(
        nominal_mating_pairs=contacts, resistor_hole_local_xy_mm=resistor_holes,
        source_chassis_removed_volume_mm3=old_chassis_volume-chassis.volume,
        removed_ledger_items=removed, unchanged_main_protection_reserve_kg=items['main_protection']['mass_kg'],
        net_physical_mass_change_kg=mass-params['nominal_conditional_mass_kg'],
        pcb_draft_envelope_has_mass=False, active_axes_unchanged=True,
        electrical_release=False, thermal_release=False, collision_proxy_modified=False))
    mp = export.out/'manifest.json'
    scene_parts = [copy.deepcopy(p) for p in scene['parts'] if p['name'] not in replaces]+export.scene
    candidate = dict(schema='goose_brake_packaging_parameters_v1', parts=len(scene_parts), active_axes=18,
        nominal_conditional_mass_kg=mass, delta_from_manual_wing_service_kg=mass-params['nominal_conditional_mass_kg'],
        items=all_items, bodies=[dict(name=b['name'], **aggregate_rigid_components(
            [p for p in all_items if p['body']==b['name']], params['pivots_world_at_zero_m'][b['name']])) for b in params['bodies']],
        pivots_world_at_zero_m=params['pivots_world_at_zero_m'], rigid_coordinate_lift_m=lift,
        neutral_joint_order=params['neutral_joint_order'], remaining_protection_reserve_kg=.093,
        full_assembly_pass=False, manufacturing_release=False, training_release=False,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in inputs+[mp]})
    po = R/'evidence/brake_packaging_parameters.json'
    po.write_text(json.dumps(candidate, indent=2)+'\n')
    assembled = dict(scene, parts=scene_parts, nominal_conditional_mass_kg=mass,
        status='BRAKE_INSTALLATION_CANDIDATE_NOT_RELEASED', manufacturing_pass=False,
        final_appearance_pass=False, source_hashes={str(p.relative_to(ROOT)): sha(p) for p in [po, mp]})
    (export.source/'assembly_scene.json').write_text(json.dumps(assembled, separators=(',', ':'))+'\n')
    print('BRAKE PACKAGING', len(export.parts), 'new parts', len(scene_parts), 'scene objects', mass, 'kg', flush=True)


if __name__ == '__main__':
    main()
