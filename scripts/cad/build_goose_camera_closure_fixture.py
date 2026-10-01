"""Same-source whole preview, inertias and measured camera display references.

This creates a new446-part candidate, never overwrites frozen419 assets.
Display-reference masses are zero because the retained25g OEM allowance already
accounts for the commercial camera; references are not manufactured robot parts.
"""
from pathlib import Path
import copy
import csv
import hashlib
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad'), str(ROOT / 'scripts/models')]
from build_goose_cad import box, cylinder, holes, transform
from goose_candidate_export import CandidateExport
from sai_agent.goose.mass_properties import aggregate_rigid_components


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    scene_path = ROBOT / 'cad/source/integrated_hardware_candidate/scene.json'
    ledger_path = ROBOT / 'evidence/integrated_hardware_parameters.json'
    mount_path = ROBOT / 'cad/exports/camera_head_closure/manifest.json'
    mount_scene_path = ROBOT / 'cad/source/camera_head_closure/quad_scene.json'
    scene, ledger, kit, kit_scene = [json.loads(p.read_text()) for p in [scene_path, ledger_path, mount_path, mount_scene_path]]
    if sha(scene_path) != 'bce7ee34419f7cb0898d4e5da14ceba5c6db4f4081f9b659ab00e4491d75d4ab':
        raise ValueError('Frozen419 scene changed')
    for rel, digest in kit['source_hashes'].items():
        if sha(ROOT / rel) != digest:
            raise ValueError(('Changed native closure input', rel))
    rotation = Rotation.from_euler('y', kit['optical_pitch_down_head_deg'], degrees=True).as_matrix()
    optical = np.array(kit['optical_front_native_world_mm'])
    def world(shape):
        return transform(shape, rotation, optical)
    export = CandidateExport(ROBOT, 'camera_closure_fixture')
    # Dimensional facts from the preserved supplier STEP: front PCB1.6mm,
    # 28mm bore grid; AF square9.5mm, lens barrel5.5mm diameter. These are
    # simplified own references, not redistributed vendor CAD or print parts.
    pcb = box([1.6, 34., 34.], [-7.12, 0., 0.])
    pcb = holes(pcb, [[-7.12, y, z] for y in [-14., 14.] for z in [-14., 14.]], 2.3027, 5., 'x')
    barrel = cylinder(2.75, 1.57, [-.785, 0., 0.], 'x') - cylinder(1.5, 3., [-.785, 0., 0.], 'x')
    glass = cylinder(1.5, 1.1318, [-1.0041, 0., 0.], 'x')
    autofocus = box([4.55, 9.5, 9.5], [-3.845, 0., 0.])
    for name, shape, material in [
        ('camera_sensor_board_reference', pcb, 'pcb_reference'),
        ('camera_catalog_barrel_reference', barrel, 'graphite'),
        ('camera_catalog_glass_reference', glass, 'glass'),
        ('camera_autofocus_case_reference', autofocus, 'graphite')]:
        export.emit(name, world(shape), 'head_roll', rho=0., material=material, notes=[
            'Own simplified measured OEM dimensional display reference; not printable or procurement geometry.',
            'Zero additional mass: existing camera_module25g reservation remains in the physical ledger.',
            'Not a complete electronic or optical replica; source vendor full geometry is checked separately.'])
        export.scene[-1]['role'] = 'vendor_dimension_display_reference_not_printable'
    fixture = export.save(ROOT, [Path(__file__), mount_path, ROBOT / 'evidence/camera_supplier_native_mount_fit.json',
        ROBOT / 'evidence/camera_catalog_layout.json', ROOT / 'scripts/cad/goose_candidate_export.py',
        ROOT / 'scripts/cad/build_goose_cad.py'], extra=dict(
        status='SIMPLIFIED_OEM_REFERENCES_NOT_PRINT_PARTS', not_for_manufacture=True,
        measured_supplier_step_sha256='e9224fd36b8103d7c3b66f8ba6d766815911e5af1b6ce6dd77971b64c562aa47',
        nominal_reconstructed_front_pcb_and_optics_only=True, all_original_supplier_children_retained_in_fit=True))
    parts = {p['name']: copy.deepcopy(p) for p in scene['parts']}
    items = {p['name']: copy.deepcopy(p) for p in ledger['items']}
    for name in kit['replaces_existing_parts']:
        parts.pop(name)
        items.pop(name)
    for name in ['camera_board_proxy', 'camera_lens_proxy']:
        parts.pop(name)
    lift = ledger['rigid_coordinate_lift_m']
    for part in kit['parts']:
        for record in part['files'].values():
            if sha(ROBOT / record['path']) != record['sha256']:
                raise ValueError(('Changed closure output', part['name']))
        items[part['name']] = dict(name=part['name'], body=part['body'], mass_kg=part['mass_kg'],
            center_m=(np.array(part['center_of_mass_world_m']) + [0, 0, lift]).tolist(),
            inertia_at_com_kg_m2=part['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
            basis='Same-source native nominal density; material/tolerances/preload/strength unqualified')
    for part in kit_scene['parts'] + export.scene:
        if part['name'] in parts:
            raise ValueError('Duplicate installed geometry')
        parts[part['name']] = copy.deepcopy(part)
    mass = sum(p['mass_kg'] for p in items.values())
    np.testing.assert_allclose(mass, ledger['nominal_conditional_mass_kg'] + kit['net_native_mass_change_kg'], atol=1e-12)
    bodies = [dict(name=b['name'], **aggregate_rigid_components(
        [p for p in items.values() if p['body'] == b['name']], ledger['pivots_world_at_zero_m'][b['name']]))
        for b in ledger['bodies']]
    if len(parts) != 446 or len(bodies) != 19:
        raise ValueError(('Unexpected fixture identity', len(parts), len(bodies)))
    inputs = [Path(__file__), scene_path, ledger_path, mount_path, mount_scene_path,
        ROBOT / 'cad/exports/camera_closure_fixture/manifest.json', ROOT / 'src/sai_agent/goose/mass_properties.py']
    result = dict(schema='goose_camera_head_closure_parameters_v1', parts=446, active_axes=18,
        nominal_conditional_mass_kg=mass, delta_from419_kg=kit['net_native_mass_change_kg'],
        bodies=bodies, items=list(items.values()), pivots_world_at_zero_m=ledger['pivots_world_at_zero_m'],
        rigid_coordinate_lift_m=lift, neutral_joint_order=ledger['neutral_joint_order'],
        camera_mass_reservation_preserved_kg=.025, display_references_add_mass=False,
        frozen419_scene_unchanged=True, default344_scene_changed=False,
        new_collision_model_generated=False, training_release=False, hardware_freeze=False,
        manufacturing_release=False, full_assembly_pass=False, final_appearance_pass=False,
        static_screen_reused_from419=False,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in inputs},
        limitations=['Closed-pose19-body inertias only; passive jaw/sole resplit and fresh dynamics still needed.',
            'Finite own/vendor contact screen and actual render must follow; this builder alone releases no appearance or assembly.',
            'Camera rear USB plug, real mass/thermal limits, shell/frame attachment and purchased revision remain unqualified.'])
    output = ROBOT / 'evidence/camera_head_closure_parameters.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    directory = ROBOT / 'cad/source/camera_closure_fixture'
    preview = dict(unit='m', parts=list(parts.values()), assembly_translation_m=scene['assembly_translation_m'],
        nominal_conditional_mass_kg=mass, status='CAMERA_HEAD_CLOSURE_CANDIDATE_NOT_RELEASED',
        manufacturing_pass=False, final_appearance_pass=False, whole_assembly_clearance_pass=False,
        source_hashes=dict(result['source_hashes'], **{str(output.relative_to(ROOT)): sha(output)}),
        review_views={'head_detail': [[.65, -.82, .73], [.17, 0., .605]]},
        review_ortho_scale_m={'head_detail': .20},
        scope='Frozen419 with29native camera/head replacements and4zero-mass OEM dimensional display references; old camera proxies removed.')
    (directory / 'assembly_scene.json').write_text(json.dumps(preview, separators=(',', ':')) + '\n')
    with (ROBOT / 'hardware/camera_closure_body_parameters.csv').open('w', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(['body','mass_kg','com_x_m','com_y_m','com_z_m','ixx','iyy','izz','ixy','ixz','iyz'])
        for b in bodies:
            t = b['inertia_at_com_body_kg_m2']
            writer.writerow([b['name'], b['mass_kg'], *b['com_local_m'], t[0][0], t[1][1], t[2][2], t[0][1], t[0][2], t[1][2]])
    print('CAMERA CLOSURE FIXTURE', len(parts), 'parts', mass, 'kg; retained camera25g', flush=True)


if __name__ == '__main__':
    main()
