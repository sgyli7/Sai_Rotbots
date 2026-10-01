"""Verify native grip/frame integration against the immutable 314-part baseline.

Source identity, mass, complete tensors and contact reference are checked.
This is candidate installation bookkeeping, not manufacturing qualification.
"""
from pathlib import Path
import hashlib
import json

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [R/'cad/exports/grip_cassettes/manifest.json',
             R/'cad/exports/bill_mount_fasteners/manifest.json',
             R/'evidence/mechanical_grip_installation_baseline.json',
             R/'cad/source/mechanical_preview/scene.json',
             R/'evidence/body_bay_mechanical_parameters.json',
             R/'configs/mechanical_grip_reference.json',
             R/'evidence/grip_cassette_native_fit.json',
             R/'evidence/grip_cassette_quad_gate.json',
             R/'evidence/bill_mount_fasteners_native_fit.json',
             R/'evidence/bill_mount_fasteners_quad_gate.json']
    grip, frame, baseline, scene, ledger, reference, fit, quads, frame_fit, frame_quads = [
        json.loads(p.read_text()) for p in paths]
    for evidence in [fit, quads, frame_fit, frame_quads]:
        for relative, digest in evidence['source_hashes'].items():
            if sha(ROOT/relative) != digest:
                raise ValueError(('stale native candidate evidence', relative))
    expected = {p['name']: p for p in grip['parts']+frame['parts']}
    if len(expected) != 36:
        raise ValueError('expected 36 distinct native increment parts')
    removed = set(grip['replaces_existing_parts']+frame['replaces_existing_parts'])
    scene_parts = {p['name']: p for p in scene['parts']}
    items = {p['name']: p for p in ledger['items']}
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    records = []
    for name, native in expected.items():
        display, item = scene_parts.get(name), items.get(name)
        source_pass = all(sha(R/f['path']) == f['sha256'] for f in native['files'].values())
        geometry_pass = (display is not None and display['geometry_npz'] == native['files']['npz']['path']
                         and display['source_sha256'] == native['files']['npz']['sha256']
                         and display['body'] == native['body'])
        mass_pass = (item is not None and item['body'] == native['body']
                     and abs(item['mass_kg']-native['mass_kg']) < 1e-12
                     and np.allclose(item['center_m'], np.array(native['center_of_mass_world_m'])+lift, rtol=0, atol=1e-12)
                     and np.allclose(item['inertia_at_com_kg_m2'], native['inertia_at_com_world_kg_m2'], rtol=0, atol=1e-12))
        records.append(dict(part=name, source_files_pass=source_pass, scene_identity_pass=geometry_pass,
                            mass_center_and_full_inertia_pass=bool(mass_pass),
                            installed_candidate_pass=bool(source_pass and geometry_pass and mass_pass)))
    obsolete = sorted(removed & (set(scene_parts) | set(items)))
    old = {i['name']: i for i in baseline['replaced_and_retained_items']}
    if removed-set(old):
        raise ValueError('baseline is missing replaced mass items')
    expected_delta = sum(i['mass_kg'] for i in expected.values())-sum(old[n]['mass_kg'] for n in removed)
    actual_delta = ledger['nominal_conditional_mass_kg']-baseline['nominal_conditional_mass_kg']
    reference_world = np.array(reference['reference_native_world_m'])+lift
    reference_pass = np.allclose(reference_world, ledger['grip_world_at_zero_m'], rtol=0, atol=1e-12)
    payload_pass = np.allclose(reference_world+reference['payload_reference_offset_m'],
                               items['specified_payload_50g']['center_m'], rtol=0, atol=1e-12)
    reserve_pass = items['head_internal_frame_reserve']['mass_kg'] == old['head_internal_frame_reserve']['mass_kg'] == .08
    count_pass = len(scene_parts) == baseline['scene_parts']-len(removed)+len(expected) == 344
    passed = (all(r['installed_candidate_pass'] for r in records) and not obsolete
              and abs(expected_delta-actual_delta) < 1e-10 and reserve_pass and count_pass
              and reference_pass and payload_pass and fit['passed_samples'] == fit['sample_count'] == 23
              and frame_fit['passed_samples'] == frame_fit['sample_count'] == 23
              and quads['mesh_identity_and_geometry_pass'] and frame_quads['mesh_identity_and_geometry_pass'])
    old_bodies = {b['name']: b for b in baseline['bodies']}
    body_changes = [dict(body=b['name'], old_mass_kg=old_bodies[b['name']]['mass_kg'], new_mass_kg=b['mass_kg'],
                         mass_delta_kg=b['mass_kg']-old_bodies[b['name']]['mass_kg'],
                         local_com_shift_mm=float(np.linalg.norm(np.array(b['com_local_m'])-old_bodies[b['name']]['com_local_m'])*1000))
                    for b in ledger['bodies'] if abs(b['mass_kg']-old_bodies[b['name']]['mass_kg']) > 1e-12]
    report = dict(schema='goose_grip_frame_installation_v1', installed_candidate_source_pass=bool(passed),
                  checked_increment_parts=len(records), current_scene_parts=len(scene_parts),
                  current_conditional_mass_kg=ledger['nominal_conditional_mass_kg'],
                  mass_delta_without_reserve_deduction_kg=actual_delta, expected_native_replacement_delta_kg=expected_delta,
                  retained_head_internal_frame_reserve_kg=items['head_internal_frame_reserve']['mass_kg'],
                  obsolete_parts_still_present=obsolete, records=records, body_changes=body_changes,
                  old_grip_reference_world_m=baseline['grip_world_at_zero_m'],
                  grip_reference_world_m=reference_world.tolist(), reference_and_payload_pass=bool(reference_pass and payload_pass),
                  historical_baseline_git_commit=baseline['source_git_commit'],
                  source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths+[Path(__file__)]},
                  manufacturing_release=False, material_and_strength_release=False,
                  whole_assembly_clearance_pass=False, whole_task_release=False,
                  limitations=['Verifies the 36-part increment and six replacements against the immutable 314-part baseline; not the whole assembly fit.',
                               'Native manifests retain generation-time installed:false; this report records subsequent candidate integration.',
                               'CAD fit uses separately labelled constructive/inherited bounds; unresolved kernel defects were not silently treated as direct intersection passes.',
                               'Pad snap insertion, tear/creep/friction, preload, real tool access and physical assembly remain unqualified.',
                               'The contact reference is changed; old task and training evidence cannot be substituted for same-version checks.'])
    (R/'evidence/mechanical_grip_installation.json').write_text(json.dumps(report, indent=2)+'\n')
    print('GRIP FRAME INSTALLED', len(records), 'parts', len(scene_parts), 'pass', passed, 'delta kg', actual_delta, flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
