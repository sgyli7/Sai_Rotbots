"""Bounded catalog-camera installation screen against current native head CAD.

Vendor geometry stays private in artifacts. Complete child bounds, including
the vendor's non-solid rear-board representation, supply conservative keepouts.
Positive keepout common volumes reject this screen, not the real product.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

from build123d import Compound, import_brep, import_step
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/cad'), str(ROOT/'scripts/diagnostics')]
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    vendor = ROOT/'artifacts/Goose_V0.1/camera_vendor_docs/b0471.step'
    if sha(vendor) != 'e9224fd36b8103d7c3b66f8ba6d766815911e5af1b6ce6dd77971b64c562aa47':
        raise ValueError('vendor CAD revision mismatch; rescreen new drawing')
    source = import_step(vendor)
    groups = []
    for child in source.children:
        bb = child.bounding_box()
        groups.append(dict(label=child.label, bounds_mm=[list(bb.min), list(bb.max)],
                          closed_solid_count=len(child.solids()), native_valid=child.is_valid))
    if len(groups) != 4:
        raise ValueError('all four vendor subassemblies must be retained')
    inputs = [ROBOT/'cad/source/bill_backbones/head_bill_access_shell_left.brep',
              ROBOT/'cad/source/jaw_retention/head_retention_access_shell_right.brep',
              ROBOT/'cad/source/jaw_retention/head_frame_with_jaw_retention.brep',
              ROBOT/'cad/source/head_load_path/beak_motor_catalog_case.brep']
    scene_file = ROBOT/'cad/source/mechanical_preview/scene.json'
    scene = json.loads(scene_file.read_text())
    installed_names = {p['name'] for p in scene['parts']}
    if len(scene['parts']) != 344 or not all(p.stem in installed_names for p in inputs):
        raise ValueError('screen must use actual names of the current344-part assembly')
    shapes = {p.stem:import_brep(p) for p in inputs}
    for name, shape in shapes.items():
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(('invalid current native input', name))
    # Vendor +Z is forward and its board centre is X/Y14mm. The 180deg
    # clocking puts the rear Type-C edge toward the upper service region.
    mapping = np.array([[0., 0., 1.], [1., 0., 0.], [0., 1., 0.]])
    clock = np.diag([1., -1., -1.])
    pupil = np.array([14., 14., 15.619998659664])
    expansion_mm = .7  # .2 catalog dimensional allowance + .5 separation guard
    results = []
    started = time.monotonic()
    stopped = 'ALL_FINITE_CANDIDATES_TESTED'
    for optic_x in [188., 190., 192., 194.]:
        for optic_z in [602., 604.5]:
            for tilt in [20., 25.]:
                if time.monotonic()-started > 100.:
                    stopped = 'NATIVE_SCREEN_TIME_BOUND'
                    break
                rotation = Rotation.from_euler('y', tilt, degrees=True).as_matrix()@clock@mapping
                optical = np.array([optic_x, 0., optic_z])
                translation = optical-rotation@pupil
                keepouts = []
                for group in groups:
                    bounds = np.asarray(group['bounds_mm'])
                    envelope = box(bounds[1]-bounds[0]+2*expansion_mm, bounds.mean(axis=0))
                    keepouts.append(transform(envelope, rotation, translation))
                envelope = Compound(keepouts)
                cases = []
                for name, shape in shapes.items():
                    bb, other = envelope.bounding_box(), shape.bounding_box()
                    lo, hi = np.asarray(list(bb.min)), np.asarray(list(bb.max))
                    other_lo, other_hi = np.asarray(list(other.min)), np.asarray(list(other.max))
                    separate = bool(np.any(hi < other_lo) or np.any(other_hi < lo))
                    common = {'volume_mm3':0., 'method':'disjoint native bounding boxes'} if separate else bounded_common(envelope, shape, 3.)
                    clear = 'error' not in common and common['volume_mm3'] < .01
                    cases.append(dict(part=name, expanded_keepout_common=common, clear=clear))
                clear = all(c['clear'] for c in cases)
                results.append(dict(optical_front_native_world_mm=optical.tolist(),
                    optical_pitch_down_in_head_deg=tilt, vendor_clocking_rad=float(np.pi),
                    vendor_to_native_rotation=rotation.tolist(), vendor_to_native_translation_mm=translation.tolist(),
                    complete_expanded_bounds_mm=[list(envelope.bounding_box().min),list(envelope.bounding_box().max)],
                    cases=cases, finite_expanded_head_installation_screen_pass=clear))
                print('CAMERA', optical.tolist(), tilt, 'clear', clear,
                      [(c['part'],c['expanded_keepout_common']) for c in cases if not c['clear']], flush=True)
            if stopped != 'ALL_FINITE_CANDIDATES_TESTED':
                break
        if stopped != 'ALL_FINITE_CANDIDATES_TESTED':
            break
    passing = [r for r in results if r['finite_expanded_head_installation_screen_pass']]
    # Prefer the existing optical height and then the least forward movement.
    selected = min(passing, key=lambda r:(abs(r['optical_front_native_world_mm'][2]-604.5),
        r['optical_front_native_world_mm'][0], abs(r['optical_pitch_down_in_head_deg']-25.))) if passing else None
    report = dict(schema='goose_camera_complete_catalog_layout_v1', status=stopped,
        robot='Goose_V0.1', procurement_candidate_sku='B0471-1', supplier_cad_label=source.label,
        supplier_cad_is_complete_valid_solid=False, supplier_closed_solids=len(source.solids()),
        vendor_subassemblies=groups, invalid_or_surface_group_omitted=False,
        dimensional_and_separation_expansion_each_side_mm=expansion_mm,
        candidates=results, selected=selected, finite_candidate_count=len(results),
        finite_passing_count=len(passing), wall_seconds=time.monotonic()-started,
        camera_mass_kg=None, existing_camera_allowance_kg=.025,
        nominal_mounting_grid_mm=[28.,28.], mounting_hole_diameter_released=False,
        module_and_plug_installation_release=False, optical_task_release=False,
        manufacturing_release=False, installed=False, default_model_changed=False,
        vendor_files={'step':{'url':'https://download.arducam.com/3D-Drawing/B0471.STEP','sha256':sha(vendor),
                        'private_not_redistributed':True}},
        sources=['https://www.arducam.com/arducam-16mp-imx519-fast-auto-focus-usb-3-0-camera-module-without-enclosure.html',
            'https://www.arducam.com/downloads/datasheet/B0471_16MP_IMX519_USB3.0_Camera_Datasheet.pdf'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs+[scene_file, Path(__file__),
            ROOT/'scripts/cad/build_goose_cad.py', ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py']},
        limitations=['Four conservative catalog subassembly boxes preserve every vendor child, including non-solid UC-A48 rear representation; they are not manufactured electronic replicas.',
          'Negative common with expanded boxes proves only the tested nominal native pairs; positive box common may be a conservative rejection.',
          'The old decorative solid face and glass must be replaced by an actual optical opening and chassis; they are not included as valid camera mounting parts.',
          'Type-C mating plug, cable bend/service loop, actual PCB contact-free mounts and exterior housing remain gates.',
          'Current page specifies10cm focus while2023 B0471 PDF says3m; batch/variant and close-focus bench validation remain explicit.',
          'Vendor CAD has no usable published mass or internal material model; no camera weight/inertia is inferred from electronic CAD volume.'])
    (ROBOT/'evidence/camera_catalog_layout.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CAMERA SUMMARY', len(passing), 'passing', 'selected', selected and selected['optical_front_native_world_mm'], flush=True)


if __name__ == '__main__':
    main()
