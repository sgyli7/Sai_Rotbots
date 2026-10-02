"""Verify the installed bill/retention increment against its native sources.

This closes scene/ledger replacement bookkeeping, not manufacture or strength.
"""
from pathlib import Path
import hashlib
import json

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'


def main():
    paths = [R/'cad/exports/bill_backbones/manifest.json',
             R/'cad/exports/jaw_retention/manifest.json',
             R/'configs/mechanical_native_replacements.json',
             R/'cad/source/mechanical_preview/scene.json',
             R/'evidence/body_bay_mechanical_parameters.json',
             R/'evidence/mechanical_bill_retention_baseline.json',
             R/'evidence/jaw_retention_native_fit.json',
             R/'evidence/jaw_retention_quad_gate.json']
    bones, kit, mapping, scene, ledger, baseline, fit, mesh = [json.loads(p.read_text()) for p in paths]
    expected, removed = {}, set()
    for folder, manifest in [('bill_backbones', bones), ('jaw_retention', kit)]:
        names = manifest['replaces_existing_parts'] + mapping['additional_replaces_by_folder'].get(folder, [])
        removed.update(names)
        for name in names:
            expected.pop(name, None)
        for part in manifest['parts']:
            if part['name'] in expected:
                raise ValueError('duplicate increment: '+part['name'])
            expected[part['name']] = part
    scene_parts = {p['name']: p for p in scene['parts']}
    items = {p['name']: p for p in ledger['items']}
    lift = np.array([0, 0, ledger['rigid_coordinate_lift_m']])
    records = []
    for name, part in expected.items():
        display, item = scene_parts.get(name), items.get(name)
        files_pass = all(hashlib.sha256((R/f['path']).read_bytes()).hexdigest() == f['sha256']
                         for f in part['files'].values())
        geometry_pass = (display is not None and display['geometry_npz'] == part['files']['npz']['path']
                         and display['source_sha256'] == part['files']['npz']['sha256']
                         and display['body'] == part['body'])
        mass_pass = (item is not None and item['body'] == part['body']
                     and abs(item['mass_kg']-part['mass_kg']) < 1e-12
                     and np.allclose(item['center_m'], np.array(part['center_of_mass_world_m'])+lift, rtol=0, atol=1e-12)
                     and np.allclose(item['inertia_at_com_kg_m2'], part['inertia_at_com_world_kg_m2'], rtol=0, atol=1e-12))
        records.append(dict(part=name, source_files_pass=files_pass, scene_identity_pass=geometry_pass,
                            mass_center_and_full_inertia_pass=bool(mass_pass), installed_candidate_pass=bool(files_pass and geometry_pass and mass_pass)))
    obsolete = sorted(removed & (set(scene_parts) | set(items)))
    old_items = [p for p in baseline['replaced_and_retained_head_items'] if p['name'] in removed]
    expected_delta = sum(p['mass_kg'] for p in expected.values())-sum(p['mass_kg'] for p in old_items)
    actual_delta = ledger['nominal_conditional_mass_kg']-baseline['nominal_conditional_mass_kg']
    reserve_pass = items['head_internal_frame_reserve']['mass_kg'] == .08
    passed = (len(records) == 30 and all(p['installed_candidate_pass'] for p in records)
              and not obsolete and abs(actual_delta-expected_delta) < 1e-10 and reserve_pass
              and fit['passed_samples'] == fit['sample_count'] == 23 and mesh['mesh_identity_and_geometry_pass'])
    old_bodies = {p['name']: p for p in baseline['bodies']}
    body_changes = [dict(body=p['name'], mass_delta_kg=p['mass_kg']-old_bodies[p['name']]['mass_kg'],
                         local_com_shift_mm=float(np.linalg.norm(np.array(p['com_local_m'])-old_bodies[p['name']]['com_local_m'])*1000))
                    for p in ledger['bodies'] if abs(p['mass_kg']-old_bodies[p['name']]['mass_kg']) > 1e-12]
    report = dict(schema='goose_bill_retention_installation_v1', installed_candidate_source_pass=bool(passed),
                  checked_increment_parts=len(records), current_scene_parts=len(scene_parts),
                  current_conditional_mass_kg=ledger['nominal_conditional_mass_kg'],
                  mass_delta_without_reserve_deduction_kg=actual_delta, expected_native_replacement_delta_kg=expected_delta,
                  retained_head_internal_frame_reserve_kg=items['head_internal_frame_reserve']['mass_kg'],
                  obsolete_parts_still_present=obsolete, records=records, body_changes=body_changes,
                  manufacturing_release=False, whole_assembly_clearance_pass=False, structural_release=False,
                  source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
                  limitations=['Installation in candidate display and mass ledger only; physical assembly, camera/pad/shell fastening and strength remain unreleased.',
                               'Native manifests retain their historical generation-time uninstalled flags; this report explicitly records subsequent candidate integration.',
                               'Runtime dynamics and backend verification have separate versioned reports.'])
    (R/'evidence/mechanical_bill_retention_installation.json').write_text(json.dumps(report, indent=2)+'\n')
    print('BILL RETENTION INSTALLED', len(records), '/', len(expected), 'pass', passed,
          'delta kg', actual_delta, 'body changes', body_changes)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
