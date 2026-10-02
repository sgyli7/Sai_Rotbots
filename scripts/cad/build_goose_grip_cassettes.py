"""Native replaceable grip cassettes, independent of the installed candidate.

The metal carriers span the old pad/backbone gap. Four screws per side carry
clamp loads; four elastic mushroom plugs per pad provide positive retention.
This builds nominal geometry, not qualified TPU snap strain or thread preload.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import Plane, Solid, Wire, export_brep, import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_cad import box, cylinder, holes
from goose_candidate_export import CandidateExport
from goose_nurbs_skin import native_properties
from sai_agent.native_csg import subtraction_witness_violations

SCREWS = [(x, y) for x in [185., 216.] for y in [-8., 8.]]
PLUGS = [(x, y) for x in [198., 228.] for y in [-5., 5.]]


def footprint(lo, hi, inset=0.):
    points = [(179+inset, -12+inset), (215, -12+inset),
              (239-inset, -7+inset), (239-inset, 7-inset),
              (215, 12-inset), (179+inset, 12-inset)]
    return Solid.make_loft([Wire.make_polygon([(x, y, z) for x, y in points], close=True)
                            for z in [lo, hi]], ruled=True)


def cone_at(x, y, face, direction, clearance=0.):
    return Solid.make_cone(2.35+clearance, 1.25+clearance, 1.4,
                           Plane(origin=(x, y, face), z_dir=(0, 0, direction)))


def flat_screw(x, y, face, direction, length):
    stem_len = length-1.4+.01
    stem_z = face+direction*(1.4-.01+.5*stem_len)
    return cone_at(x, y, face, direction)+cylinder(1.25, stem_len, [x, y, stem_z], 'z')


def nut(x, y, lo, hi):
    circumradius = 5./np.sqrt(3)
    points = [(x+circumradius*np.cos(a), y+circumradius*np.sin(a))
              for a in np.linspace(0, 2*np.pi, 6, endpoint=False)]
    shape = Solid.make_loft([Wire.make_polygon([(a, b, z) for a, b in points], close=True)
                             for z in [lo, hi]], ruled=True)
    return shape-cylinder(1.025, hi-lo+2, [x, y, .5*(lo+hi)], 'z')


def main():
    inputs = [R/'cad/exports'/folder/'manifest.json'
              for folder in ['bill_backbones', 'jaw_retention']]
    manifests = [json.loads(p.read_text()) for p in inputs]
    wanted = {'upper_bill_retention_backbone', 'lower_bill_keyed_backbone',
              'upper_bill_retention_shell', 'lower_bill_backbone_shell'}
    records = {p['name']: p for m in manifests for p in m['parts'] if p['name'] in wanted}
    shapes = {name: import_step(R/p['files']['step']['path']).solids()[0]
              for name, p in records.items()}
    export = CandidateExport(R, 'grip_cassettes')
    contacts, mounts, relations = [], [], {}

    def operand(name, shape):
        """Store the exact native operand used by this construction, not a proxy."""
        file = export.source/(name+'.brep')
        export_brep(shape, file)
        return dict(path=str(file.relative_to(R)),
                    sha256=hashlib.sha256(file.read_bytes()).hexdigest(), unit='mm')

    for side, body, bottom, top, pad_lo, pad_hi, direction, face, nut_face, length in [
        ('upper', 'head_roll', 554.2, 557.2, 553., 554.2, 1., 554.2, 563., 12.),
        ('lower', 'beak_hinge', 549.7, 551.7, 551.7, 553., -1., 551.7, 545., 10.),
    ]:
        carrier = footprint(bottom, top)
        pad = footprint(pad_lo, pad_hi, .3)
        backbone = shapes['upper_bill_retention_backbone' if side=='upper' else 'lower_bill_keyed_backbone']
        shell = shapes['upper_bill_retention_shell' if side=='upper' else 'lower_bill_backbone_shell']
        additive, subtractive, negative_shapes = [], [], []
        # The same four clearance positions are retained. Planar metal nut
        # seats replace reliance on the original sloping blade surfaces.
        for x, y in SCREWS:
            boss = (cylinder(3.3, 4., [x, y, 561.], 'z') if side=='upper'
                    else cylinder(3.3, 4.7, [x, y, 547.35], 'z'))
            additive.append(operand(f'{side}_grip_added_boss_{len(additive)}', boss))
            backbone += boss
            carrier -= cone_at(x, y, face, direction)
        backbone = holes(backbone, [[x, y, 557.] for x, y in SCREWS], 2.7, 35., 'z')
        carrier = holes(carrier, [[x, y, .5*(bottom+top)] for x, y in SCREWS], 2.7, 8., 'z')
        back = top if side=='upper' else bottom
        # Mushroom heads sit in real metal reliefs. Pad stems are inside
        # clearance bores; normal compression acts on the broad metal face.
        for x, y in PLUGS:
            carrier -= cylinder(1.35, top-bottom+2, [x, y, .5*(bottom+top)], 'z')
            stem_end = back+direction*.6
            attach_face = pad_hi if side=='upper' else pad_lo
            pad += cylinder(1.2, abs(stem_end-attach_face)+.02,
                            [x, y, .5*(stem_end+attach_face)], 'z')
            pad += cylinder(2.2, .6, [x, y, back+direction*.3], 'z')
            backbone -= cylinder(2.4, .8, [x, y, back+direction*.4], 'z')
        # Real shell pockets expose the cassette gripping faces; larger
        # local ports admit nut/screw installation envelopes, not fake holes.
        cut = footprint(min(bottom,pad_lo,back-.6 if side=='lower' else back)-.2,
                        max(top,pad_hi)+.2, -.2)
        subtractive.append(operand(side+'_grip_removed_cassette_volume', cut))
        negative_shapes.append(cut)
        shell -= cut
        if side=='upper':
            # The cassette aperture otherwise disconnects the rear central
            # floor from the outer shell. Define an actual continuous rear
            # installation opening through that floor, instead of silently
            # choosing the largest of the three disconnected solids.
            cut = box([84.,24.8,6.],[198.5,0.,555.])
            subtractive.append(operand(side+'_grip_removed_rear_volume', cut))
            negative_shapes.append(cut)
            shell -= cut
        for x, y in SCREWS:
            if side=='upper':
                # Cover the entire screw/nut stack, including the previous
                # 558..559mm uncut interval behind the rear service opening.
                cut = cylinder(3.8, 14., [x, y, 560.8], 'z')
            else:
                cut = cylinder(4., 13., [x, y, 546.], 'z')
            subtractive.append(operand(f'{side}_grip_removed_bolt_volume_{len(subtractive)}', cut))
            negative_shapes.append(cut)
            shell -= cut
        if side=='upper':
            # These are the complete fixed-tab/frame M3 stacks, not just the
            # 4mm frame contact band that the prior shell cut exposed. Preserve
            # actual room for the inner nuts and outside heads/washers.
            for index,y in enumerate([21.75,-21.75]):
                # A connected rectangular service slot meets the existing
                # cassette aperture. Four isolated round cuts caused OCCT to
                # generate material in an originally empty cylindrical void.
                # Extend through the outside skin, rather than leave the
                # observed unsupported0.26mm strip atY=-29.01..-28.75mm.
                cut=box([20.,18.5,18.],[178.,y,565.])
                subtractive.append(operand(f'upper_grip_removed_frame_mount_{index}',cut))
                negative_shapes.append(cut)
                shell-=cut
        export.emit(side+'_grip_backbone', backbone, body,
                    rho=2700. if side=='upper' else 7850.,
                    material='ivory' if side=='upper' else 'titanium', notes=[
                        'Replacement metal backbone with four2.7mm clearance holes and planar nut seating bosses.',
                        'Pad mushroom-head reliefs are actual removed metal; local stress and strength not qualified.',
                    ])
        violations=subtraction_witness_violations(shell,negative_shapes)
        if not shell.is_valid or len(shell.solids())!=1 or violations:
            failure=dict(schema='goose_grip_shell_native_failure_v1',side=side,
                         valid=bool(shell.is_valid),solid_count=len(shell.solids()),
                         solids=[dict(volume_mm3=native_properties(s)[0],
                                      minimum_mm=list(s.bounding_box().min),
                                      maximum_mm=list(s.bounding_box().max)) for s in shell.solids()],
                         builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         subtraction_witness_violations=violations,
                         reason='Physical cassette/bolt pockets disconnected native shell;no fragment selected or discarded.')
            target=R/'evidence'/('grip_cassette_shell_lower_first_failure.json'
                                  if side=='lower' else 'grip_cassette_shell_repeat_failure.json')
            if target.exists():
                target=R/'evidence'/('grip_cassette_shell_failure_'+failure['builder_sha256'][:12]+'.json')
            if target.exists():raise ValueError(('preserve existing failure',failure))
            target.write_text(json.dumps(failure,indent=2)+'\n')
            raise ValueError(failure)
        export.emit(side+'_grip_shell', shell, body, rho=1270., material='orange', notes=[
            'Actual cassette aperture and local nut/screw installation ports in prior hollow bill.',
            'Shell fastening, wall/print process and full tool approach remain release gates.',
        ])
        bone_source = records['upper_bill_retention_backbone' if side=='upper' else 'lower_bill_keyed_backbone']
        shell_source = records['upper_bill_retention_shell' if side=='upper' else 'lower_bill_backbone_shell']
        relations[side+'_grip_backbone'] = dict(
            predecessor=bone_source, additive_solids=additive, subtractive_solids=[],
            construction='predecessor union recorded bosses, then clearance holes and pad reliefs removed',
            subset_of_predecessor_union_additions=True)
        relations[side+'_grip_shell'] = dict(
            predecessor=shell_source, additive_solids=[], subtractive_solids=subtractive,
            construction='successive native CUT with each recorded negative operand',
            sampled_subtraction_semantics_pass=True,
            subtraction_witnesses_per_operand=7,
            subset_of_predecessor_union_additions=True)
        export.emit(side+'_grip_carrier', carrier, body, notes=[
            '60mm-long tapered metal backing,24mm maximum width;3mm upper or2mm lower thickness.',
            'Four M2.5 clearance/countersink positions and four2.7mm elastic-pad plug bores.',
            'Broad compression face contacts the backbone; not an adhesive-only load route.',
        ])
        export.emit(side+'_grip_cassette_pad', pad, body, rho=1100., material='rubber', notes=[
            'Nominal85A TPU density assumption;1.2/1.3mm contact sheet plus four molded/printed mushroom plugs.',
            '4.4mm mushroom diameter through2.7mm bore requires elastic installation; strain, tear and friction not qualified.',
            'Peel off soft pad to service flat screws; pad contact geometry replaces the old unattached42mm-wide proxy.',
        ])
        for index, (x, y) in enumerate(SCREWS):
            screw_name = f'{side}_grip_flat_screw_{index}'
            nut_name = f'{side}_grip_nut_{index}'
            screw = flat_screw(x, y, face, direction, length)
            nlo, nhi = (nut_face, nut_face+2) if side=='upper' else (nut_face-2, nut_face)
            export.emit(screw_name, screw, body, rho=7850., material='titanium', notes=[
                f'Own M2.5x{length:g} flat-head envelope,4.7mm head diameter/1.4mm head depth;not OEM threaded CAD.',
                'Selected head dimensions, grade, corrosion protection, preload and locking require release.',
            ])
            export.emit(nut_name, nut(x, y, nlo, nhi), body, rho=7850., material='titanium', notes=[
                'Own nominal M2.5 nut5mm AF x2mm;2.05mm thread-minor envelope.',
                'Nominal major/minor overlap is recorded as thread contact, not qualified thread geometry.',
            ])
            contacts.append(dict(screw=screw_name,nut=nut_name,
                                  expected_thread_overlap_mm3=float(np.pi*(1.25**2-1.025**2)*2)))
            mounts.append(dict(side=side,center_xy_world_mm=[x,y],carrier_face_z_mm=face,
                               nut_seat_z_mm=nut_face,screw_nominal_length_mm=length,
                               nut_full_height_mm=2.,nominal_engagement_mm=2.,
                               screw_protrusion_past_nut_mm=abs(face+direction*length-(nhi if side=='upper' else nlo))))
        print('GRIP CASSETTE', side, 'native parts exported', flush=True)
    replacements = ['upper_bill_retention_backbone', 'lower_bill_keyed_backbone',
                    'upper_bill_retention_shell', 'lower_bill_backbone_shell',
                    'upper_grip_pad', 'lower_grip_pad']
    payload = export.save(ROOT, inputs+[Path(__file__), ROOT/'scripts/cad/goose_candidate_export.py',ROOT/'src/sai_agent/native_csg.py'],
                          replaces=replacements, extra=dict(
                              status='GRIP_CASSETTE_NOMINAL_CANDIDATE_NOT_INSTALLED', installed=False,
                              nominal_thread_contacts=contacts, mounts=mounts,
                              native_csg_relations=relations,
                              csg_operands_are_control_volumes_not_physical_parts=True,
                              pad_contact_plane_closed_world_z_mm=553.,
                              pad_snap_installation_qualified=False, structural_strength_pass=False,
                              shell_attachment_pass=False, complete_tool_approach_pass=False))
    print('GRIP KIT',len(payload['parts']),'mass',payload['native_mass_kg'],flush=True)


if __name__ == '__main__':
    main()
