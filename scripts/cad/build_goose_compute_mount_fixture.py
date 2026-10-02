"""Editable original compute-rack review; PCB references omit circuitry."""
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
    cfg_path = ROBOT / 'configs/compute_module_mounts.json'
    cfg = json.loads(cfg_path.read_text())
    export = CandidateExport(ROBOT, 'compute_module_fixture')
    for module in cfg['modules']:
        tx, ty, top = module['translation_mm']
        width, height = module['pcb_xy_mm']
        thick = module['pcb_thickness_mm']
        center = [tx + width / 2, ty + height / 2, top - thick / 2]
        shape = box([width, height, thick], center)
        shape = holes(shape, [[tx+x, ty+y, center[2]] for x, y in module['mount_holes_local_xy_mm']],
                      module['mount_hole_diameter_mm'], 8, 'z')
        export.emit(module['name'] + '_mounting_reference', shape, 'torso', rho=1800,
                    material='pcb_reference', notes=['Original flat PCB mounting reference only; no circuit/connector geometry, not a print or manufacturing part.'])
        export.scene[-1]['role'] = 'own_flat_PCB_reference_NOT_circuitry_or_manufacturing_part'
    kit_manifest = ROBOT / 'cad/exports/compute_module_mounts/manifest.json'
    kit_scene = ROBOT / 'cad/source/compute_module_mounts/quad_scene.json'
    frame_manifest = ROBOT / 'cad/exports/body_bay_frame/manifest.json'
    frame_scene = ROBOT / 'cad/source/body_bay_frame/quad_scene.json'
    inputs = [Path(__file__), cfg_path, kit_manifest, kit_scene, frame_manifest, frame_scene]
    export.save(ROOT, inputs, extra=dict(reference_only=True, installed=False,
        reference_mass_not_added_to_robot=True, vendor_fit_evidence='evidence/compute_module_mount_fit.json'))
    frame = json.loads(frame_scene.read_text())
    names = {s + '_battery_support_rail' for s in ['right', 'left']} | {
        s + '_battery_frame_post_' + str(i) for s in ['right', 'left'] for i in range(2)}
    old_parts = [p for p in frame['parts'] if p['name'] in names]
    if {p['name'] for p in old_parts} != names:
        raise ValueError('Incomplete current battery frame fixture')
    kit = json.loads(kit_scene.read_text())
    scene = dict(unit='m', status='COMPUTE RACK CANDIDATE - FLAT PCB REFERENCES OMIT CIRCUITS/PLUGS - NOT RELEASED',
        assembly_translation_m=[0,0,0], parts=kit['parts'] + old_parts + export.scene,
        reference_only=True, manufacturing_pass=False, final_appearance_pass=False,
        review_views=dict(three_quarter=[[.02, -.24, .47], [-.096, 0, .314]],
                          rear=[[-.34, -.10, .365], [-.12, 0, .314]],
                          top=[[-.096, 0, .75], [-.096, 0, .314]]),
        review_ortho_scale_m=dict(three_quarter=.20, rear=.15, top=.21),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs},
        scope='42 original candidate parts, six actual current battery-frame parts and two original flat PCB references. Full private vendor source is checked by the fit diagnostic.')
    out = ROBOT / 'cad/source/compute_module_fixture/assembly_scene.json'
    out.write_text(json.dumps(scene,separators=(',', ':')) + '\n')
    print('COMPUTE FIXTURE', len(scene['parts']), 'parts', flush=True)


if __name__ == '__main__':
    main()
