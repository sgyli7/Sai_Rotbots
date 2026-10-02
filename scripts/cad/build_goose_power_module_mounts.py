"""Two frame-anchored DC/DC carriers using the selected OEM mounting holes.

Only original carriers and nominal fasteners are exported. OEM source solids
remain private; their fit is checked separately. CAD coordinates are mm before
the independent whole-assembly 3.7 mm physics lift.
"""
from pathlib import Path
import json
import sys

from build123d import Pos, RegularPolygon, extrude

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_cad import box, cylinder, holes
from goose_candidate_export import CandidateExport


def washer(xy, bottom, od, bore, height):
    center = [*xy, bottom + height / 2]
    return cylinder(od / 2, height, center) - cylinder(bore / 2, height + 2, center)


def nominal_screw(xy, bearing_z, diameter, length, head_od, head_height):
    # Smooth major-diameter shaft: screw/tapped-bore overlaps are recorded as
    # nominal thread contacts, never silently discarded as collision noise.
    return (cylinder(diameter / 2, length, [*xy, bearing_z - length / 2])
            + cylinder(head_od / 2, head_height, [*xy, bearing_z + head_height / 2]))


def main():
    config_path = ROBOT / 'configs/power_module_mounts.json'
    config = json.loads(config_path.read_text())
    export = CandidateExport(ROBOT, 'power_module_mounts')
    bottom = config['carrier_bottom_z_mm']
    thickness = config['carrier_thickness_mm']
    top = bottom + thickness
    center_z = bottom + thickness / 2
    washer_t = config['insulating_washer_thickness_mm']
    pcb_z = config['pcb_bottom_z_mm']
    frames, modules, contacts = [], [], []

    def emit(name, shape, density=2700, material='graphite', notes=()):
        export.emit(name, shape, 'torso', rho=density, material=material, notes=notes)
        print('POWER MOUNT', name, 'mass_g', round(export.parts[-1]['mass_kg'] * 1000, 4), flush=True)

    for module in config['modules']:
        name = module['name']
        tx, ty, _ = module['translation_mm']
        width, height = module['pcb_xy_mm']
        cx, cy = tx + width / 2, ty + height / 2
        anchors = module['frame_anchors_xy_mm']
        sign = 1 if cy > 0 else -1
        foot = box([28, 8, thickness], [43, sign * 34, center_z])
        ring = (box([width + 4, height + 4, thickness], [cx, cy, center_z])
                - box([width, height, thickness + 4], [cx, cy, center_z]))
        # Arm joins only the outer ring; it does not cover the PCB solder pads.
        inner_x = tx - 1
        arm = box([inner_x - 54, 8, thickness], [(inner_x + 54) / 2, sign * 34, center_z])
        carrier = foot + arm + ring
        mount_xy = [[tx + x, ty + y] for x, y in module['mount_holes_local_xy_mm']]
        for xy in mount_xy:
            carrier += cylinder(config['post_base_radius_mm'], thickness, [*xy, center_z])
            post_height = config['post_top_z_mm'] - top
            carrier += cylinder(config['post_radius_mm'], post_height, [*xy, top + post_height / 2])
        carrier = holes(carrier, [[*xy, center_z] for xy in anchors], 3.2, 20, 'z')
        carrier = holes(carrier, [[*xy, center_z] for xy in mount_xy], config['m2_tap_minor_diameter_mm'], 20, 'z')
        carrier_name = name + '_frame_carrier'
        emit(carrier_name, carrier, notes=[
            '6061-T6 CNC candidate, 2mm exterior perimeter carrier and integral M2 tapped posts.',
            'Mount above the current neck_yaw_rear_frame_plate using two shared M3x18 through-bolts.',
            'M2 holes model the 1.6mm tap minor bore; helical thread, tolerances and finish remain drawing requirements.',
            'Not a thermal or electrical insulation release; OEM wire/strain-relief geometry remains pending.'])

        for index, xy in enumerate(mount_xy):
            prefix = name + '_pcb_' + str(index)
            for side, washer_bottom in [('bottom', pcb_z - washer_t),
                                        ('top', pcb_z + module['pcb_thickness_mm'])]:
                emit(prefix + '_' + side + '_washer',
                     washer(xy, washer_bottom, config['insulating_washer_od_mm'],
                            config['insulating_washer_id_mm'], washer_t),
                     density=1150, material='ivory', notes=['Nylon M2 insulation washer candidate; OD4/ID2.2/t0.5mm.'])
            bearing = pcb_z + module['pcb_thickness_mm'] + washer_t
            screw_name = prefix + '_m2x6'
            emit(screw_name, nominal_screw(xy, bearing, 2, 6, 3.8, 2),
                 density=7800, notes=['Nominal M2x6 socket screw envelope, head OD3.8/h2mm; smooth major-diameter shaft.'])
            tip = bearing - 6
            engagement = min(config['post_top_z_mm'], bearing) - max(bottom, tip)
            contacts.append(dict(screw=screw_name, tapped_part=carrier_name,
                                 nominal_thread='M2', thread_engagement_mm=engagement,
                                 nominal_shaft_tip_z_mm=tip))

        modules.append(dict(name=name, sku=module['sku'], world_from_vendor_mm=dict(
            rotation=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], translation=module['translation_mm']),
            mount_axes_world_xy_mm=mount_xy, pcb_bottom_z_mm=pcb_z,
            pcb_mount_hole_mm=module['mount_hole_diameter_mm'],
            source_step_sha256=module['vendor_step_sha256']))

        for xy in anchors:
            index = [([34, -34]), ([34, 34]), ([52, -34]), ([52, 34])].index(xy)
            prefix = 'neck_power_frame_' + str(index)
            # The current three-plate stack is bottom311.9..top323.9mm.
            for side, washer_bottom in [('top', top), ('bottom', 311.4)]:
                emit(prefix + '_' + side + '_washer', washer(xy, washer_bottom, 6, 3.2, .5), density=7800)
            screw_name, nut_name = prefix + '_m3x18', prefix + '_m3_nut'
            emit(screw_name, nominal_screw(xy, top + .5, 3, 18, 5.5, 3), density=7800)
            # Across flats5.5mm, h2.4mm; minor bore2.5mm is a thread envelope.
            nut = Pos(*xy, 309.0) * extrude(RegularPolygon(5.5 / 2, 6, major_radius=False), amount=2.4)
            nut -= cylinder(1.25, 8, [*xy, 310.2])
            emit(nut_name, nut, density=7800)
            contacts.append(dict(screw=screw_name, tapped_part=nut_name,
                                 nominal_thread='M3', thread_engagement_mm=2.4,
                                 nominal_shaft_tip_z_mm=top + .5 - 18))
            frames.append(dict(anchor_xy_mm=xy, original_group='neck_frame_through_screw_' + str(index),
                original_length_mm=16, selected_length_mm=18, original_stack_mm=13.4,
                added_plate_mm=2, new_stack_mm=15.4, protrusion_mm=2.6,
                screw=screw_name, nut=nut_name, carrier=carrier_name))

    inputs = [config_path, Path(__file__), ROOT / 'scripts/cad/goose_candidate_export.py',
              ROOT / 'scripts/cad/build_goose_cad.py', ROBOT / 'cad/exports/body_bay_frame/manifest.json',
              ROBOT / 'configs/body_bay_layout_candidate.json']
    report = export.save(ROOT, inputs, extra=dict(
        module_placements=modules, shared_frame_stacks=frames, nominal_thread_contacts=contacts,
        pcb_board_mass_kg=sum(m['mass_kg'] for m in config['modules']),
        installation_state='DETACHED_FRAME_ANCHORED_NATIVE_CANDIDATE',
        retained_default_buck_allocations_kg=.065,
        electrical_release=False, thermal_release=False, wired_installation_pass=False,
        limitations=['Selected OEM STEP files remain private and must match the recorded hashes for fit reproduction.',
            'Only named geometric interfaces are verified; local strength, thread preload, thermal/current and wiring release remain open.',
            'Current default344-part assembly and its mass allocations are not silently replaced.']))
    print('POWER MOUNTS COMPLETE', len(report['parts']), 'native_mass_g', report['native_mass_kg'] * 1000, flush=True)


if __name__ == '__main__':
    main()
