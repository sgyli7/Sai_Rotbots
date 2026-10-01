"""Assembly-review fixture from the actual original power carriers and frame.

Green board silhouettes are our own mounting references derived from public
dimensions and bore coordinates. They omit circuitry and are not print parts
or OEM STEP redistribution. No fixture mass is used in the robot ledger.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT / 'scripts/cad'))
from build_goose_cad import box, holes
from goose_candidate_export import CandidateExport


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config_path = ROBOT / 'configs/power_module_mounts.json'
    config = json.loads(config_path.read_text())
    export = CandidateExport(ROBOT, 'power_module_fixture')
    for module in config['modules']:
        tx, ty, tz = module['translation_mm']
        width, height = module['pcb_xy_mm']
        thickness = module['pcb_thickness_mm']
        center = [tx + width / 2, ty + height / 2, tz + thickness / 2]
        shape = box([width, height, thickness], center)
        locations = [[tx + x, ty + y, center[2]] for x, y in module['mount_holes_local_xy_mm']]
        shape = holes(shape, locations, module['mount_hole_diameter_mm'], 5, 'z')
        export.emit(module['name'] + '_mounting_reference', shape, 'torso', material='pcb_reference',
            catalog_mass=module['mass_kg'], notes=['Own simplified PCB mounting silhouette, not circuitry or OEM geometry; not a manufacturing part.'])
        export.scene[-1]['role'] = 'own_simplified_PCB_mounting_reference_NOT_manufacturing_part'
    inputs = [config_path, Path(__file__), ROBOT / 'cad/exports/power_module_mounts/manifest.json',
              ROBOT / 'cad/source/power_module_mounts/quad_scene.json',
              ROBOT / 'cad/exports/body_bay_frame/manifest.json',
              ROBOT / 'cad/source/body_bay_frame/quad_scene.json']
    export.save(ROOT, inputs, extra=dict(
        reference_only=True, installed=False,
        reference_mass_not_added_to_robot=True,
        current_oem_fit_evidence='evidence/power_module_mount_fit.json'))
    own_scene = json.loads(inputs[3].read_text())
    frame_scene = json.loads(inputs[5].read_text())
    names = {'neck_yaw_rear_frame_plate'} | {'neck_frame_spacer_' + str(i) for i in range(4)}
    frame_parts = [p for p in frame_scene['parts'] if p['name'] in names]
    if {p['name'] for p in frame_parts} != names:
        raise ValueError('Current frame reference incomplete')
    scene = dict(unit='m', status='FRAME MOUNT REVIEW - PCB CIRCUITRY OMITTED - NOT MANUFACTURING RELEASE',
        assembly_translation_m=[0, 0, 0], parts=own_scene['parts'] + frame_parts + export.scene,
        reference_only=True, manufacturing_pass=False, final_appearance_pass=False,
        review_views=dict(three_quarter=[[.24, -.24, .5], [.071, 0, .323]],
                          top=[[.071, 0, .85], [.071, 0, .323]]),
        review_ortho_scale_m=dict(three_quarter=.18, top=.16),
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in inputs},
        scope='36 actual original mounting/fastener parts, five actual current native frame parts, two own simplified PCB mounting references. OEM actual full solids used separately by fit diagnostic.')
    path = ROBOT / 'cad/source/power_module_fixture/assembly_scene.json'
    path.write_text(json.dumps(scene, separators=(',', ':')) + '\n')
    print('POWER FIXTURE', len(scene['parts']), 'parts', flush=True)


if __name__ == '__main__':
    main()
