"""Native hollow bill candidates from the current accepted outer construction.

These shells remain independent until their backbone, shaft attachment and
fasteners pass assembly checks. They do not replace the running model by name.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import Edge, Wire, Solid, import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder
from goose_candidate_export import CandidateExport
from goose_nurbs_skin import native_properties
from sai_agent.native_cad import common_solid_volume_mm3


def bill_rings(part):
    vertices = np.array(part['vertices'])*1000
    # section_solid writes monotonic axial rings, followed by two planar quad
    # cap grids. The grids are not additional loft sections.
    first_cap = int(np.flatnonzero(np.diff(vertices[:, 0]) < -.001)[0]+1)
    assert first_cap % 48 == 0
    rings = vertices[:first_cap].reshape(-1, 48, 3)
    assert np.all(np.ptp(rings[:, :, 0], axis=1) < 1e-8)
    return rings


def loft(rings):
    result = Solid.make_loft([Wire(Edge.make_spline(row.tolist(), periodic=True))
                              for row in rings], ruled=False)
    if not result.is_valid or len(result.solids()) != 1:
        raise ValueError('invalid smooth bill loft')
    return result


def cavity(rings, wall=2.2):
    centers = rings.mean(axis=1)
    half = np.max(abs(rings-centers[:, None, :]), axis=1)
    usable = (half[:, 1] > wall+1.2) & (half[:, 2] > wall+1.2)
    inner = rings[usable].copy()
    assert len(inner) >= 4 and np.flatnonzero(usable)[0] == 0
    for index, (center, radii) in enumerate(zip(centers[usable], half[usable])):
        inner[index, :, 1:] = center[1:]+(inner[index, :, 1:]-center[1:])*(radii[1:]-wall)/radii[1:]
    # Open rear for installation. The forward closed nose is deliberately
    # left solid where its radii cannot sustain the nominal wall thickness.
    rear = inner[0].copy()
    rear[:, 0] -= 2.
    return loft(np.concatenate([rear[None, :, :], inner])), float(inner[-1, 0, 0])


def main():
    scene_path = R/'cad/source/mechanical_preview/scene.json'
    head_path = R/'cad/exports/head_load_path/manifest.json'
    scene, head = [json.loads(p.read_text()) for p in [scene_path, head_path]]
    export = CandidateExport(R, 'bill_shells')
    comparisons = []
    for original, name, owner in [('fixed_upper_bill', 'upper_bill_hollow_shell', 'head_roll'),
                                   ('hinged_lower_bill', 'lower_bill_hollow_shell', 'beak_hinge')]:
        part = next(p for p in scene['parts'] if p['name'] == original)
        rings = bill_rings(part)
        outer = loft(rings)
        hollow, cavity_end = cavity(rings)
        shell = outer-hollow
        original_hits = []
        for hardware in head['parts']:
            item = import_step(R/hardware['files']['step']['path']).solids()[0]
            volume = common_solid_volume_mm3(outer, item)
            if volume > .01:
                original_hits.append(dict(part=hardware['name'], common_volume_mm3=volume))
        if owner == 'head_roll':
            # Real bearing housings cross the old solid rear bill envelope.
            # Two local side installation windows preserve the central roof.
            for y in [23.5, -26.5]:
                shell -= cylinder(12.4, 9.2, [160., y, 576.], 'y')
        if not shell.is_valid or len(shell.solids()) != 1:
            raise ValueError((name, 'hollow shell disconnected'))
        intersections = []
        for hardware in head['parts']:
            item = import_step(R/hardware['files']['step']['path']).solids()[0]
            volume = common_solid_volume_mm3(shell, item)
            if volume > .01:
                intersections.append(dict(part=hardware['name'], common_volume_mm3=volume))
        export.emit(name, shell, owner, rho=1270., material='orange', notes=[
            'PETG native hollow loft reconstructed through current bill ring nodes; not a mesh repair.',
            '2.2mm coordinate wall allocation; true normal minimum and print orientation remain gates.',
            'Rear installation opening and solid forward nose; separate backbone and fasteners required.',
            'Upper shell has two bearing-housing side windows; full jaw/linkage sweep and installed appearance pending.',
        ])
        comparisons.append(dict(source=original, candidate=name, loft_ring_count=len(rings),
                                old_solid_envelope_intersections=original_hits,
                                native_shell_support_intersections=intersections,
                                cavity_forward_end_x_mm=cavity_end,
                                shell_mass_kg=native_properties(shell)[0]*1270e-9,
                                support_interference_screen_pass=not intersections))
        print('HOLLOW BILL', name, 'support hits', len(intersections), flush=True)
    export.save(ROOT, [scene_path, head_path, Path(__file__), ROOT/'scripts/cad/goose_candidate_export.py'],
                extra=dict(status='HOLLOW_BILL_CANDIDATE_NOT_INSTALLED', comparisons=comparisons,
                           installed=False, backbone_complete=False, shaft_attachment_complete=False,
                           minimum_normal_wall_verified=False, full_head_sweep_pass=False,
                           manufacturing_release=False))
    report = dict(schema='goose_native_bill_shell_support_screen_v1', comparisons=comparisons,
                  installed=False, full_assembly_release=False,
                  source_scene_sha256=hashlib.sha256(scene_path.read_bytes()).hexdigest(),
                  builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (R/'evidence/native_bill_shell_support_screen.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if all(x['support_interference_screen_pass'] for x in comparisons) else 1


if __name__ == '__main__':
    raise SystemExit(main())
