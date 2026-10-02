"""Nominal OEM-CAD contact fit; retain its non-solid rear representation."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import GeomType, import_brep, import_step

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
sys.path.insert(0, str(ROOT/'scripts/diagnostics'))
from build_goose_cad import box, transform
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    layout_file = ROBOT/'evidence/camera_catalog_layout.json'
    carrier_file = ROBOT/'cad/exports/camera_carrier/manifest.json'
    layout, carrier = [json.loads(p.read_text()) for p in [layout_file, carrier_file]]
    vendor_path = ROOT/'artifacts/Goose_V0.1/camera_vendor_docs/b0471.step'
    if sha(vendor_path) != layout['vendor_files']['step']['sha256']:
        raise ValueError('supplier CAD identity changed')
    source = import_step(vendor_path)
    if len(source.children) != 4:
        raise ValueError('all supplier subassemblies must be retained')
    pose = layout['selected']
    rotation = np.asarray(pose['vendor_to_native_rotation'])
    translation = np.asarray(pose['vendor_to_native_translation_mm'])
    own_paths = [ROBOT/p['files']['brep']['path'] for p in carrier['parts']]
    shapes = {p.stem:import_brep(p) for p in own_paths}
    results = []
    for index, child in enumerate(source.children):
        solid_geometry = bool(child.is_valid and child.solids())
        if solid_geometry:
            obstacle = transform(child, rotation, translation)
            method = 'exact valid supplier native subassembly'
        else:
            bb = child.bounding_box()
            lo, hi = np.asarray(list(bb.min)), np.asarray(list(bb.max))
            obstacle = transform(box(hi-lo+1.4, (lo+hi)/2), rotation, translation)
            method = 'complete expanded bounds of supplier non-solid subassembly; not omitted'
        cases = []
        for name, shape in shapes.items():
            common = bounded_common(shape, obstacle, 8.)
            cases.append(dict(part=name, common=common,
                nominal_no_intrusion='error' not in common and common['volume_mm3'] < .01))
        results.append(dict(vendor_child_index=index, label=child.label,
            source_valid=child.is_valid, source_solid_count=len(child.solids()), method=method, cases=cases))
    # Identify four actual circular through-bores of the valid front PCB, not
    # its2.8mm copper contact rings. Their CAD diameters are revision evidence,
    # not a published tolerance for the purchasable B0471-1 batch.
    centers = {}
    for edge in source.children[2].edges().filter_by(GeomType.CIRCLE):
        if 1.0 < edge.radius < 1.3:
            center = np.array(list(edge.arc_center))
            key = tuple(np.round(center[:2], 3))
            centers[key] = dict(center_vendor_xy_mm=center[:2].tolist(), diameter_mm=2*edge.radius)
    if len(centers) != 4:
        raise ValueError(('expected four front-PCB through bores', centers))
    diameter = min(c['diameter_mm'] for c in centers.values())
    value = dict(schema='goose_camera_supplier_native_mount_fit_v1',
        status='FINITE_NOMINAL_VENDOR_MOUNT_GEOMETRY_CHECK', vendor_groups=results,
        supplier_non_solid_group_omitted=False,
        all_named_parts_nominal_no_intrusion=all(c['nominal_no_intrusion'] for r in results for c in r['cases']),
        front_pcb_through_bores=list(centers.values()), nominal_mount_screw_major_diameter_mm=2.,
        minimum_oem_cad_radial_m2_clearance_mm=(diameter-2)/2,
        published_mount_bore_tolerance=None, b0471_1_batch_revision_confirmed=False,
        camera_mass_kg=None, complete_camera_mount_release=False, manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), layout_file, carrier_file,
            ROOT/'scripts/cad/build_goose_cad.py', ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py']+own_paths},
        private_vendor_step_sha256=sha(vendor_path),
        vendor_source_url=layout['vendor_files']['step']['url'],
        limitations=[
            'Four positive conservative front-PCB mounting-box overlaps in the prior carrier screen are resolved only by this exact nominal native solid check.',
            'M2 radial bore clearance is measured in the supplier B0471 CAD; tolerance, purchasable-1 revision and PCB stack retention require confirmation.',
            'No installed bolts, nuts, washers, mating USB plug, service loop or final head-shell transition is claimed here.',
            'No interference in named CAD pairs is not proof of tool access, board bending, component thermal performance or full assembly swept fit.'])
    (ROBOT/'evidence/camera_supplier_native_mount_fit.json').write_text(json.dumps(value,indent=2)+'\n')
    print('OEM CAMERA FIT', value['all_named_parts_nominal_no_intrusion'],
          'M2 radial nominal clearance mm', value['minimum_oem_cad_radial_m2_clearance_mm'], flush=True)


if __name__ == '__main__':
    main()
