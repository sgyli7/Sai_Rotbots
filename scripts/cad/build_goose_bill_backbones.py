"""Uninstalled metal bill backbone and fixed-frame mounting candidate.

Construct a positive D-shaft lower-jaw load path and an upper-jaw path to the
head frame. Interference reports, rather than names or visual alignment, decide
whether these parts can replace the earlier reserved masses.
"""
from pathlib import Path
import itertools
import json
import sys

import numpy as np
from build123d import Pos, Rot, Solid, Wire, import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import box, cylinder, holes
from build_goose_beak_linkage import bar
from goose_candidate_export import CandidateExport
from sai_agent.native_cad import common_solid_volume_mm3


def blade(sections):
    wires = []
    for x, half_width, bottom, top in sections:
        wires.append(Wire.make_polygon([(x, -half_width, bottom),
                                         (x, half_width, bottom),
                                         (x, half_width, top),
                                         (x, -half_width, top)], close=True))
    return Solid.make_loft(wires, ruled=True)


def main():
    head_file = R/'cad/exports/head_load_path/manifest.json'
    bill_file = R/'cad/exports/bill_shells/manifest.json'
    skin_file = R/'cad/exports/head_linkage_clearance_skins/manifest.json'
    head = json.loads(head_file.read_text())
    bills = json.loads(bill_file.read_text())
    skins = json.loads(skin_file.read_text())
    shapes = {p['name']: import_step(R/p['files']['step']['path']).solids()[0]
              for p in head['parts']+bills['parts']+skins['parts']}
    export = CandidateExport(R, 'bill_backbones')
    frame = shapes['head_motor_jaw_frame']
    mount_centers = []
    # Two holes per side prevent reliance on a single friction-clamped pivot.
    # Bosses join the real bearing-housing material, not its rotating shaft.
    for y in [23.5, -23.]:
        frame += box([22, 4, 10], [175, y, 566])
        points = [[x, y, 566] for x in [174, 182]]
        frame = holes(frame, points, 3.2, 10, 'y')
        mount_centers.extend(points)
    for y in [23.5, -26.5]:
        # Restoring the real seat after adding bosses prevents added material
        # from filling part of a stationary bearing envelope.
        frame -= cylinder(9.5, 9, [160, y, 576], 'y')
    export.emit('head_frame_with_bill_mounts', frame, 'head_roll', notes=[
        'Two M3 clearance holes per fixed side boss, 8mm spacing; CNC frame replacement candidate.',
        'Fastener grades, clamp preload, thread/nut arrangement and bracket stress remain release gates.',
    ])

    upper = blade([(177, 12, 557.2, 561.0), (195, 12, 557.2, 561.0),
                   (215, 12, 557.2, 560.2), (235, 8, 557.2, 559.5)])
    for y in [19.5, -19.]:
        tab = holes(box([16, 4, 8], [178, y, 566]),
                    [[x, y, 566] for x in [174, 182]], 3.2, 10, 'y')
        tab -= cylinder(12.5, 6, [160, y, 576], 'y')
        upper += tab + bar([175, y, 564], [185, y, 560.8], 3, 4, y)
    upper += box([12, 42.5, 2.5], [184, .25, 560.8])
    upper = holes(upper, [[x, y, 558.45] for x in [185, 216] for y in [-8, 8]],
                  2.7, 10, 'z')
    export.emit('upper_bill_metal_backbone', upper, 'head_roll', notes=[
        '6061 density candidate; load route from pad fasteners through blade and twin tabs to fixed frame.',
        'Four M2.5 pad/shell attachment positions; screw lengths, nut access and local pad fixture pending.',
        'No strength or manufacturing release from this geometry alone.',
    ])

    # A tapered steel blade avoids pretending that a thin PETG display surface
    # carries the complete jaw torque. Grade/finish selection is not released.
    lower = blade([(177, 15, 545.9, 549.7), (190, 15, 546.3, 549.7),
                   (215, 11, 547.1, 549.7), (235, 7, 547.7, 549.7)])
    for y in [-14.5, 14.5]:
        hub = cylinder(7.5, 4, [160, y, 576], 'y')
        keyed_hole = cylinder(4.05, 10, [160, y, 576], 'y')-box([10, 12, 12], [152, y, 576])
        ear = bar([160, y, 576], [179, y, 548], 6, 4, y)
        lower += (hub+ear)-keyed_hole
    lower = holes(lower, [[x, y, 548] for x in [185, 216] for y in [-8, 8]],
                  2.7, 15, 'z')
    export.emit('lower_bill_keyed_backbone', lower, 'beak_hinge', rho=7850., material='titanium', notes=[
        'One-piece steel candidate with two 8.1mm D bores mating central shaft flats at Y±14.5mm.',
        'Tapered blade plus two ears; positive torque transfer, not a bonded or friction-only printed hub.',
        'The bores deliberately share the shaft flat; fits, strength, corrosion finish and axial retention pending.',
        'Four M2.5 pad/shell attachment positions; fasteners and pad backing fixture not yet supplied.',
    ])

    # Installation slots are modelled as actual removed shell material. They
    # expose the moving ears locally; the central gripping face stays present.
    # Full-motion clearance is a later independent gate, not implied by these
    # closed-pose cuts.
    upper_shell = shapes['upper_bill_hollow_shell']
    lower_shell = shapes['lower_bill_hollow_shell']
    for y in [-14.5, 14.5]:
        upper_shell -= box([34, 5.4, 30], [163, y, 566])
        lower_shell -= box([37, 5.4, 5], [187, y, 551.5])
    for y in [23.5, -23.]:
        upper_shell -= box([22.6, 4.6, 10.6], [175, y, 566])
    export.emit('upper_bill_backbone_shell', upper_shell, 'head_roll', rho=1270., material='orange', notes=[
        'Independent hollow-bill replacement with two explicit lower-ear installation/sweep slots.',
        'Nominal 0.7mm side slot allowance; actual fit, minimum walls, support and complete sweep remain gates.',
    ])
    export.emit('lower_bill_backbone_shell', lower_shell, 'beak_hinge', rho=1270., material='orange', notes=[
        'Independent hollow-bill replacement with two local roof slots for keyed backbone ears.',
        'Central pad surface retained; pad fasteners, sealing and verified print orientation remain gates.',
    ])
    shapes['upper_bill_hollow_shell'] = upper_shell
    shapes['lower_bill_hollow_shell'] = lower_shell
    access = box([44, 66, 34], [163, 0, 564])
    access = access.fillet(4, access.edges())
    for side in ['left', 'right']:
        name = 'head_bill_access_shell_'+side
        shapes[name] = shapes['goose_head_shell_'+side]-access
        export.emit(name, shapes[name], 'head_roll', rho=1270., material='ivory', notes=[
            'Native head-shell candidate with one filleted mouth installation window; no collision masking.',
            'Existing exterior retained outside the local window; lip, camera mount and shell fastening are not released.',
            'Window permits the keyed backbone and fixed bill to pass through the chin; complete sweep independently checked.',
        ])

    report = []
    candidates = {'upper_bill_metal_backbone': upper, 'lower_bill_keyed_backbone': lower}
    for name, shape in candidates.items():
        for other in ['upper_bill_hollow_shell', 'lower_bill_hollow_shell',
                      'beak_motor_catalog_case', 'jaw_front_bearing', 'jaw_rear_bearing']:
            volume = common_solid_volume_mm3(shape, shapes[other])
            report.append(dict(candidate=name, other=other, common_volume_mm3=volume,
                               pass_no_interference=volume < .01))
    for name in ['upper_bill_metal_backbone', 'lower_bill_keyed_backbone',
                 'upper_bill_backbone_shell', 'lower_bill_backbone_shell']:
        shape = {'upper_bill_backbone_shell': upper_shell,
                 'lower_bill_backbone_shell': lower_shell}.get(name, candidates.get(name))
        for side in ['left', 'right']:
            other = 'head_bill_access_shell_'+side
            volume = common_solid_volume_mm3(shape, shapes[other])
            report.append(dict(candidate=name, other=other, common_volume_mm3=volume,
                               pass_no_interference=volume < .01))
    for side in ['left', 'right']:
        other = 'head_bill_access_shell_'+side
        volume = common_solid_volume_mm3(frame, shapes[other])
        report.append(dict(candidate='head_frame_with_bill_mounts', other=other,
                           common_volume_mm3=volume, pass_no_interference=volume < .01))
    kit_shapes = {'head_frame_with_bill_mounts': frame, **candidates,
                  'upper_bill_backbone_shell': upper_shell,
                  'lower_bill_backbone_shell': lower_shell,
                  **{n: s for n, s in shapes.items() if n.startswith('head_bill_access_shell_')}}
    for a, b in itertools.combinations(kit_shapes, 2):
        volume = common_solid_volume_mm3(kit_shapes[a], kit_shapes[b])
        report.append(dict(candidate=a, other=b, common_volume_mm3=volume,
                           pass_no_interference=volume < .01, scope='all_7_part_closed_kit_pairs'))
    for hardware in ['beak_motor_catalog_case', 'jaw_front_bearing', 'jaw_rear_bearing']:
        volume = common_solid_volume_mm3(frame, shapes[hardware])
        report.append(dict(candidate='head_frame_with_bill_mounts', other=hardware,
                           common_volume_mm3=volume, pass_no_interference=volume < .01))
    volume = common_solid_volume_mm3(upper, lower)
    report.append(dict(candidate='upper_bill_metal_backbone', other='lower_bill_keyed_backbone',
                       common_volume_mm3=volume, pass_no_interference=volume < .01))
    payload = export.save(ROOT, [Path(__file__), head_file, bill_file, skin_file,
                                 ROOT/'scripts/cad/goose_candidate_export.py'], extra=dict(
        status='BILL_BACKBONE_INITIAL_FIT_CANDIDATE_NOT_INSTALLED',
        installed=False, mounting_hole_centers_world_mm=mount_centers,
        initial_fit=report, initial_fit_pass=all(r['pass_no_interference'] for r in report),
        fasteners_complete=False, shaft_retention_complete=False,
        swept_assembly_pass=False, structural_strength_pass=False,
    ))
    (R/'evidence/native_bill_backbone_initial_fit.json').write_text(
        json.dumps(dict(schema='goose_native_bill_backbone_initial_fit_v1',
                        records=report, installed=False, manufacturing_release=False), indent=2)+'\n')
    print('BILL BACKBONES', len(export.parts), payload['native_mass_kg'],
          'initial fit', payload['initial_fit_pass'], flush=True)
    for item in report:
        if not item['pass_no_interference']:
            print('FIT FAILURE', item, flush=True)
    return 0 if payload['initial_fit_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
