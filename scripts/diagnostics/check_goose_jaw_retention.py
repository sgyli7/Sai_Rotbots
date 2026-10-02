"""Expanded native jaw-retainer fit, including any rear-circlip orientation.

Only the new kit against its actual head/bill/linkage neighbours is covered.
Seven explicit nominal thread contacts are measured, never called clearance.
"""
from pathlib import Path
import hashlib
import itertools
import json
import sys

import numpy as np
from build123d import import_step
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder, transform
from sai_agent.goose.native_linkage import COUPLER_PARTS, INPUT_PARTS
from sai_agent.native_cad import common_solid_volume_mm3


def main():
    paths = [R/'cad/exports'/folder/'manifest.json' for folder in
             ['head_load_path', 'beak_native_linkage', 'bill_backbones', 'jaw_retention']]
    manifests = [json.loads(p.read_text()) for p in paths]
    kit = manifests[-1]
    replacements_path = R/'configs/mechanical_native_replacements.json'
    replacements = json.loads(replacements_path.read_text())['additional_replaces_by_folder']
    shapes, groups = {}, {}
    for manifest_path, manifest in zip(paths, manifests):
        folder = manifest_path.parent.name
        for name in manifest.get('replaces_existing_parts', []) + replacements.get(folder, []):
            shapes.pop(name, None)
            groups.pop(name, None)
        for p in manifest['parts']:
            file = R/p['files']['step']['path']
            assert hashlib.sha256(file.read_bytes()).hexdigest() == p['files']['step']['sha256']
            shapes[p['name']] = import_step(file).solids()[0]
            groups[p['name']] = ('input' if p['name'] in INPUT_PARTS else
                                  'coupler' if p['name'] in COUPLER_PARTS else
                                  'jaw' if p['body'] == 'beak_hinge' else 'fixed')
    new = {p['name'] for p in kit['parts']}
    # Bounding annulus includes every orientation of the standard rear clip,
    # rather than requiring the assembled ring to retain a chosen angle.
    shapes['rear_clip_any_orientation_envelope'] = (
        cylinder(7.2, .85, [160, -32.475, 576], 'y') -
        cylinder(3.8, 2., [160, -32.475, 576], 'y'))
    groups['rear_clip_any_orientation_envelope'] = 'jaw'
    new.add('rear_clip_any_orientation_envelope')
    # Axisymmetric moving parts about the actual jaw axis have invariant
    # placed geometry. Their mass/body ownership still remains jaw, not head.
    invariant = {name for name, group in groups.items() if group == 'fixed'}
    invariant |= {name for name in shapes if name.startswith('jaw_') and name.endswith('_spacer')}
    invariant |= {'jaw_front_axial_stop_washer', 'jaw_front_axial_stop_screw',
                  'rear_clip_any_orientation_envelope'}
    # The envelope intentionally contains the actual clip; neither comparison
    # could add fit information. All other neighbouring parts remain checked.
    same_clip = frozenset(['rear_clip_any_orientation_envelope', 'jaw_rear_din471_ring'])
    threads = {frozenset([t['screw'], t['frame']]): t for t in kit['nominal_thread_contacts']}
    link = manifests[1]
    m = np.array(link['motor_axis_world_mm'])
    j = np.array(link['jaw_axis_world_mm'])
    phase, radius = link['closed_phase_rad'], link['crank_radius_mm']
    d = radius*np.array([np.cos(phase), 0., np.sin(phase)])
    cache, cases = {}, []
    candidate_pairs = [(a, b) for a, b in itertools.combinations(shapes, 2)
                       if (a in new or b in new) and frozenset([a, b]) != same_clip]
    for q in np.linspace(0, .55, 23):
        rot = Rotation.from_rotvec([0, q, 0]).as_matrix()
        posed, bounds = {}, {}
        for name, shape in shapes.items():
            group = groups[name]
            if name in invariant:
                posed[name] = shape
            elif group == 'jaw':
                posed[name] = transform(shape, rot, j-rot@j)
            elif group == 'input':
                posed[name] = transform(shape, rot, m-rot@m)
            elif group == 'coupler':
                posed[name] = transform(shape, np.eye(3), rot@d-d)
            else:
                posed[name] = shape
            bb = posed[name].bounding_box()
            bounds[name] = np.array(tuple(bb.min)), np.array(tuple(bb.max))
        hits, contacts = [], []
        for a, b in candidate_pairs:
            key = frozenset([a, b])
            rigid_pair = groups[a] == groups[b] or (a in invariant and b in invariant)
            if rigid_pair and key in cache:
                volume = cache[key]
            elif np.any(np.minimum(bounds[a][1], bounds[b][1]) -
                        np.maximum(bounds[a][0], bounds[b][0]) <= 1e-6):
                volume = 0.
                if rigid_pair:
                    cache[key] = volume
            else:
                volume = common_solid_volume_mm3(posed[a], posed[b])
                if rigid_pair:
                    cache[key] = volume
            if key in threads:
                expected = threads[key]['expected_thread_overlap_mm3']
                contacts.append(dict(a=a, b=b, intersection_mm3=volume,
                                     expected_nominal_thread_overlap_mm3=expected,
                                     nominal_contact_pass=abs(volume-expected)<.02))
            elif volume > .01:
                hits.append(dict(a=a, b=b, intersection_mm3=volume))
        passed = not hits and len(contacts) == len(threads) and all(p['nominal_contact_pass'] for p in contacts)
        cases.append(dict(q_rad=float(q), collisions=hits, intended_thread_contacts=contacts,
                          sampled_geometry_pass=passed))
        print('JAW RETENTION FIT', round(q, 3), 'hits', len(hits), 'threads', len(contacts), flush=True)
        for hit in hits:
            print('COLLISION', hit, flush=True)
    report = dict(schema='goose_jaw_retention_native_fit_v1', candidate_parts=len(kit['parts']),
                  checked_native_parts=len(shapes)-1, tested_pair_count=len(candidate_pairs), cases=cases,
                  sample_count=len(cases), passed_samples=sum(c['sampled_geometry_pass'] for c in cases),
                  any_rear_clip_orientation_envelope_checked=True, nominal_stack_endfloat_mm=kit['nominal_stack_endfloat_mm'],
                  installed=False, manufacturing_release=False, whole_head_release=False,
                  source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in paths+[replacements_path, Path(__file__)]},
                  limitations=[
                      'New retention kit versus listed head/bill/linkage native solids only; not whole robot or continuous clearance.',
                      'Seven explicitly measured nominal major-thread/tap-drill contacts, not thread/preload qualification.',
                      'Rear circlip all-angle envelope, catalogue-derived conservative model, not exact supplied CAD or tool-path approval.',
                      '698 bearing race/chamfer abutments, shims/tolerances, shaft D-flat/tap/groove, cap stresses and fatigue not qualified.',
                      'Existing kit pairs retain their separate reports; no load, thermal, task or manufacture inference from overlap tests.',
                  ])
    (R/'evidence/jaw_retention_native_fit.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['passed_samples'] == len(cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
