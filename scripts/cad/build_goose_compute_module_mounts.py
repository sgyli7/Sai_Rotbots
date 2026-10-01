"""Independent OEM-pattern compute supports anchored to the current chassis.

Original candidate geometry only. PCB circuit geometry stays private and is
checked separately; neither source-invalid OEM solids nor connectors vanish.
"""
from pathlib import Path
import json
import sys

from build123d import Pos, RegularPolygon, extrude, import_step

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_cad import box, cylinder, holes
from goose_candidate_export import CandidateExport
from build_goose_power_module_mounts import washer


def screw(xy, bearing, diameter, length, head_od, head_height, sign):
    return (cylinder(diameter / 2, length, [*xy, bearing + sign * length / 2])
            + cylinder(head_od / 2, head_height, [*xy, bearing - sign * head_height / 2]))


def main():
    cfg_path = ROBOT / 'configs/compute_module_mounts.json'
    cfg = json.loads(cfg_path.read_text())
    export = CandidateExport(ROBOT, 'compute_module_mounts')
    frame_manifest = ROBOT / 'cad/exports/body_bay_frame/manifest.json'
    old = next(p for p in json.loads(frame_manifest.read_text())['parts']
               if p['name'] == 'torso_open_chassis_plate')
    old_path = ROBOT / old['files']['step']['path']
    chassis = import_step(old_path)
    chassis = holes(chassis, [[*xy, 313.4] for xy in cfg['frame_anchors_xy_mm']], 3.2, 12, 'z')
    export.emit('torso_compute_mount_chassis_plate', chassis, 'torso', material='graphite', notes=[
        'Replacement of current torso_open_chassis_plate, adding four M3 clearance holes only.',
        'Dedicated compute anchors at X=-96/-78, Y=+/-34mm; battery and neck hole patterns unchanged.',
        '3mm 6061 plate; local hole ligament, screw preload and frame stiffness not released.'])

    # Lower electronics shelf hangs behind the original rear rail ends. Upper
    # shelf sits above its PCB to keep the downward-facing USB sockets open.
    rear_x = cfg['rear_bridge_x_mm']
    lower_z = cfg['lower_carrier_bottom_z_mm']
    upper_z = cfg['upper_carrier_bottom_z_mm']
    flange_z = cfg['carrier_frame_flange_bottom_z_mm']
    thickness = cfg['carrier_thickness_mm']
    rack = box([3, 71, thickness], [rear_x, 0, lower_z + thickness / 2])
    rack += box([3, 43, thickness], [rear_x, 0, upper_z + thickness / 2])
    for sign in [-1, 1]:
        for z in [lower_z, upper_z]:
            rack += box([72.5, 3, thickness], [-116.75, sign * 20, z + thickness / 2])
        rack += box([3, 3, upper_z - lower_z - thickness],
                    [rear_x, sign * 20, (upper_z + lower_z + thickness) / 2])
        rack += box([3, 8, flange_z - lower_z],
                    [rear_x, sign * 34, (flange_z + lower_z + 2 * thickness) / 2])
        rack += box([79, 8, thickness], [-113.5, sign * 34, flange_z + thickness / 2])
    contacts, stacks = [], []
    for module in cfg['modules']:
        tx, ty, _ = module['translation_mm']
        lower = module['support_side'] == 'below_PCB'
        shelf_z = lower_z if lower else upper_z
        mount_xy = [[tx + x, ty + y] for x, y in module['mount_holes_local_xy_mm']]
        for xy in mount_xy:
            x, y = xy
            rail_y = 20 if y > 0 else -20
            rack += box([4.4, abs(rail_y - y) + 1.5, thickness],
                        [x, (rail_y + y) / 2, shelf_z + thickness / 2])
            rack += cylinder(cfg['post_base_radius_mm'], thickness, [x, y, shelf_z + thickness / 2])
            post_lo, post_hi = ((shelf_z + thickness, module['post_contact_z_mm']) if lower
                                else (module['post_contact_z_mm'], shelf_z))
            rack += cylinder(cfg['post_radius_mm'], post_hi - post_lo, [x, y, (post_hi + post_lo) / 2])
        rack = holes(rack, [[*xy, shelf_z] for xy in mount_xy], cfg['m2_tap_minor_diameter_mm'], 16, 'z')
        for i, xy in enumerate(mount_xy):
            prefix = module['name'] + '_pcb_' + str(i)
            top = module['translation_mm'][2]
            bottom = top - module['pcb_thickness_mm']
            for side, z in [('bottom', bottom - .5), ('top', top)]:
                export.emit(prefix + '_' + side + '_washer', washer(xy, z, 4, 2.2, .5), 'torso',
                            rho=1150, material='ivory', notes=['Nominal nylon M2 washer OD4/ID2.2/t0.5mm.'])
            name = prefix + '_m2x6'
            bearing, axis = module['screw_bearing_z_mm'], module['screw_axis_sign']
            export.emit(name, screw(xy, bearing, 2, 6, 3.8, 2, axis), 'torso', rho=7800, material='graphite',
                        notes=['M2x6 major-diameter screw envelope; helical thread and supply tolerances not modeled.'])
            tip = bearing + axis * 6
            solid_lo = shelf_z if lower else module['post_contact_z_mm']
            solid_hi = module['post_contact_z_mm'] if lower else shelf_z + thickness
            engagement = min(max(bearing, tip), solid_hi) - max(min(bearing, tip), solid_lo)
            contacts.append(dict(screw=name, tapped_part='compute_dual_shelf_frame_carrier', nominal_thread='M2',
                                 thread_engagement_mm=engagement, nominal_shaft_diameter_mm=2,
                                 modeled_tap_minor_diameter_mm=1.6))

    rack = holes(rack, [[*xy, flange_z + 1] for xy in cfg['frame_anchors_xy_mm']], 3.2, 12, 'z')
    export.emit('compute_dual_shelf_frame_carrier', rack, 'torso', material='graphite', notes=[
        'Original monolithic 6061 CNC candidate; two independent PCB supports with integral M2 tapped posts.',
        'Shelf ribs 2mm, rear webs 3mm, chassis flanges 2mm. Lower shelf is below Radxa; upper shelf is above HUB HAT B.',
        'Actual connector bodies, pogo pins and source-invalid Radxa main solid retained by the separate fit diagnostic.',
        'Manufacturing access, edge fillets, local stress, machining price and thread tolerance remain gates.'])

    for i, xy in enumerate(cfg['frame_anchors_xy_mm']):
        prefix = 'compute_frame_' + str(i)
        export.emit(prefix + '_bottom_washer', washer(xy, 309.4, 7, 3.2, .5), 'torso', rho=7800, material='graphite')
        export.emit(prefix + '_top_washer', washer(xy, 314.9, 7, 3.2, .5), 'torso', rho=7800, material='graphite')
        export.emit(prefix + '_m3x12', screw(xy, 309.4, 3, 12, 5.5, 3, 1), 'torso', rho=7800, material='graphite')
        nut = Pos(*xy, 315.4) * extrude(RegularPolygon(radius=5.5 / 3**.5, side_count=6), amount=2.4)
        nut -= cylinder(.8 * 1.5, 8, [*xy, 316.6])
        nut_name = prefix + '_m3_nut'
        export.emit(nut_name, nut, 'torso', rho=7800, material='graphite', notes=['Nominal M3 nut AF5.5/h2.4; tap minor2.4, smooth screw envelope.'])
        contacts.append(dict(screw=prefix + '_m3x12', tapped_part=nut_name, nominal_thread='M3',
                             thread_engagement_mm=2.4, nominal_shaft_diameter_mm=3,
                             modeled_tap_minor_diameter_mm=2.4))
        stacks.append(dict(name=prefix, xy_mm=xy, shaft_length_mm=12,
                           flange_mm=2, chassis_mm=3, total_washer_mm=1, nut_mm=2.4,
                           total_stack_mm=8.4, protrusion_mm=3.6, unchanged_battery_fasteners=True))
    manifest = export.save(ROOT, [cfg_path, Path(__file__), old_path, frame_manifest,
        ROOT / 'scripts/cad/goose_candidate_export.py'], replaces=['torso_open_chassis_plate'], extra=dict(
        nominal_thread_contacts=contacts, frame_stacks=stacks,
        replaced_chassis_mass_kg=old['mass_kg'],
        conservative_added_mass_kg=sum(p['mass_kg'] for p in export.parts) - old['mass_kg'],
        retained_compute_allocation_kg=cfg['retained_combined_compute_mass_reservation_kg'],
        default_assembly_changed=False, connector_and_wire_clearance_pass=False,
        supplier_geometry_validity_pass=False))
    print('COMPUTE MOUNT', len(manifest['parts']), 'parts', manifest['native_mass_kg'],
          'added', manifest['conservative_added_mass_kg'], flush=True)


if __name__ == '__main__':
    main()
