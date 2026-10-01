"""Detached six-part tip contact candidate; does not alter the installed robot.

Extends the actual metal-backed TPU contact surface toward the bill nose while
retaining current M2.5 positions, mushroom plugs, backbone and drive geometry.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import Solid, Wire, export_brep, import_brep

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_cad import cylinder, holes
from build_goose_grip_cassettes import SCREWS, PLUGS, cone_at
from goose_candidate_export import CandidateExport
from sai_agent.native_csg import subtraction_witness_violations


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def footprint(lo, hi, inset=0.):
    points = [(179+inset, -12+inset), (215, -12+inset),
              (239, -7+inset), (258-inset, -3+inset),
              (258-inset, 3-inset), (239, 7-inset),
              (215, 12-inset), (179+inset, 12-inset)]
    return Solid.make_loft([Wire.make_polygon([(x, y, z) for x, y in points], close=True)
                            for z in [lo, hi]], ruled=True)


def main():
    source = R/'cad/exports/grip_cassettes/manifest.json'
    manifest = json.loads(source.read_text())
    records = {p['name']: p for p in manifest['parts']}
    export = CandidateExport(R, 'tip_grip_candidate')
    relations = {}
    for side, body, bottom, top, pad_lo, pad_hi, direction, face in [
        ('upper', 'head_roll', 554.2, 557.2, 553., 554.2, 1., 554.2),
        ('lower', 'beak_hinge', 549.7, 551.7, 551.7, 553., -1., 551.7),
    ]:
        carrier = footprint(bottom, top)
        pad = footprint(pad_lo, pad_hi, .3)
        for x, y in SCREWS:
            carrier -= cone_at(x, y, face, direction)
        carrier = holes(carrier, [[x, y, .5*(bottom+top)] for x, y in SCREWS], 2.7, 8., 'z')
        back = top if side == 'upper' else bottom
        for x, y in PLUGS:
            carrier -= cylinder(1.35, top-bottom+2, [x, y, .5*(bottom+top)], 'z')
            stem_end = back+direction*.6
            attach_face = pad_hi if side == 'upper' else pad_lo
            pad += cylinder(1.2, abs(stem_end-attach_face)+.02,
                            [x, y, .5*(stem_end+attach_face)], 'z')
            pad += cylinder(2.2, .6, [x, y, back+direction*.3], 'z')
        old = records[side+'_grip_shell']
        file = R/old['files']['brep']['path']
        if sha(file) != old['files']['brep']['sha256']:
            raise ValueError(('stale shell', side))
        shell = import_brep(file)
        cut = footprint(min(bottom, pad_lo, back-.6 if side == 'lower' else back)-.2,
                        max(top, pad_hi)+.2, -.2)
        control_file = export.source/(side+'_tip_removed_window.brep')
        export_brep(cut, control_file)
        shell -= cut
        violations = subtraction_witness_violations(shell, [cut])
        if not shell.is_valid or len(shell.solids()) != 1 or violations:
            failure = dict(side=side, native_valid=bool(shell.is_valid), solids=len(shell.solids()),
                           subtraction_witness_violations=violations, builder_sha256=sha(Path(__file__)),
                           installed=False, reason='Rejected exact native CUT; no fragment selection.')
            (R/'evidence/tip_grip_native_construction_failure.json').write_text(json.dumps(failure, indent=2)+'\n')
            raise ValueError(failure)
        relations[side+'_grip_shell'] = dict(predecessor=old, additive_solids=[],
            subtractive_solids=[dict(path=str(control_file.relative_to(R)), sha256=sha(control_file), unit='mm')],
            construction='Exact native CUT of current shell with extended cassette window',
            sampled_subtraction_semantics_pass=True, subtraction_witnesses_per_operand=7,
            subset_of_predecessor_union_additions=True)
        export.emit(side+'_grip_shell', shell, body, rho=1270., material='orange', notes=[
            'Actual extended contact aperture; no collision filtering or hidden shell overlap.',
            'Distal wall thickness and shell attachment remain manufacturing release gates.'])
        export.emit(side+'_grip_carrier', carrier, body, notes=[
            'Existing four M2.5 screws/plugs; metal extends to X258mm with6mm-wide distal face.',
            'Mid-region50N target retained; distal contact screened separately at20N, not50N.'])
        export.emit(side+'_grip_cassette_pad', pad, body, rho=1100., material='rubber', notes=[
            'Contact sheet extends toX257.7mm; nominal85A TPU, friction/tear not experimentally qualified.',
            'Same four retained mushroom plugs and compression-supported carrier as installed candidate.'])
        print('TIP GRIP', side, 'exported', flush=True)
    replacements = [side+suffix for side in ['upper', 'lower']
                    for suffix in ['_grip_shell', '_grip_carrier', '_grip_cassette_pad']]
    old_mass = sum(records[n]['mass_kg'] for n in replacements)
    # Transparent cantilever screen of the extension only. Nominal material
    # modulus/allowable values are assumptions, not certified stock properties.
    force, length, width, thickness, modulus = 20., 20., 15.6666666667, 2., 69000.
    stress = 6*force*length/(width*thickness**2)
    deflection = force*length**3/(3*modulus*(width*thickness**3/12))
    payload = export.save(ROOT, [source, Path(__file__), ROOT/'scripts/cad/goose_candidate_export.py',
                                ROOT/'scripts/cad/build_goose_grip_cassettes.py'],
        replaces=replacements, extra=dict(status='DETACHED_TIP_CONTACT_CANDIDATE', installed=False,
            old_replaced_mass_kg=old_mass, native_csg_relations=relations,
            front_contact_native_world_m=[.255, 0., .553],
            middle_contact_native_world_m=[.220, 0., .553],
            front_design_clamp_force_n=20., middle_design_clamp_force_n=50.,
            extension_screen=dict(root_x_mm=235., load_x_mm=255., force_n=force,
                root_width_mm=width, lower_plate_thickness_mm=thickness,
                assumed_aluminum_modulus_mpa=modulus, assumed_allowable_mpa=120.,
                assumed_stress_concentration_factor=2., nominal_stress_mpa=stress,
                screened_stress_mpa=2*stress, nominal_deflection_mm=deflection,
                local_nominal_screen_pass=2*stress<120., whole_structure_strength_pass=False),
            actual_floor_pickup_pass=False, complete_fit_pass=False,
            csg_operands_are_control_volumes_not_physical_parts=True))
    print('TIP KIT', len(payload['parts']), 'mass delta', payload['native_mass_kg']-old_mass, flush=True)


if __name__ == '__main__':
    main()
