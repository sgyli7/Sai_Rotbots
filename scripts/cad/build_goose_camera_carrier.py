"""One bounded camera-carrier candidate using the complete catalog layout.

Retain the current metal head frame and add a short cantilever and front-PCB
carrier. Exact supplier PCB hole diameter and threaded standoff retention are
unreleased; this is real own CAD, not a claimed installed electronics module.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation
from build123d import Axis, import_brep

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
sys.path.insert(0, str(ROOT/'scripts/diagnostics'))
from build_goose_cad import box, cylinder, holes, transform
from goose_candidate_export import CandidateExport
from check_goose_grip_cassettes import bounded_common


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strut(a, b, depth=3., height=6.):
    a, b = np.asarray(a), np.asarray(b)
    if abs(a[1]-b[1]) > 1e-6:
        raise ValueError('strut lies in one native XZ plane')
    delta = b-a
    angle = -np.arctan2(delta[2], delta[0])
    return transform(box([np.linalg.norm(delta)+2., depth, height]),
                     Rotation.from_euler('y', angle).as_matrix(), (a+b)/2)


def main():
    layout_path = ROBOT/'evidence/camera_catalog_layout.json'
    layout = json.loads(layout_path.read_text())
    selected = layout['selected']
    if selected is None or not selected['finite_expanded_head_installation_screen_pass']:
        raise ValueError('a passing full-stack screen is required')
    for rel, expected in layout['source_hashes'].items():
        if sha(ROOT/rel) != expected:
            raise ValueError(('stale catalog screen', rel))
    optical = np.asarray(selected['optical_front_native_world_mm'])
    rotation = Rotation.from_euler('y', selected['optical_pitch_down_in_head_deg'], degrees=True).as_matrix()
    predecessor_manifest_path = ROBOT/'cad/exports/jaw_retention/manifest.json'
    predecessor_record = next(p for p in json.loads(predecessor_manifest_path.read_text())['parts']
                              if p['name']=='head_frame_with_jaw_retention')
    source = ROBOT/predecessor_record['files']['brep']['path']
    if sha(source) != predecessor_record['files']['brep']['sha256']:
        raise ValueError('current retained-jaw frame identity mismatch')
    predecessor = import_brep(source)
    ledger_path = ROBOT/'evidence/body_bay_mechanical_parameters.json'
    current_items = {p['name']:p for p in json.loads(ledger_path.read_text())['items']}
    replaced_names = ['head_frame_with_jaw_retention', 'flush_camera_window', 'camera_glass', 'camera_inner_lens', 'camera_eye_bezel']
    if abs(current_items[replaced_names[0]]['mass_kg']-predecessor_record['mass_kg']) > 1e-12:
        raise ValueError('current frame mass and ledger disagree')
    # Front camera PCB is 6.32mm behind the pupil in the recorded vendor CAD.
    # All four bore centres come from the published 28x28 grid, but the vendor
    # has not dimensioned bore diameters; 2.4mm here is an unreleased M2 choice.
    front_pcb_face = -6.31999999714
    carrier_front, carrier_back = -2.3, -5.3
    mount_points = [[-3.8, y, z] for y in [-14., 14.] for z in [-14., 14.]]
    ring = box([3., 42., 42.], [-3.8, 0., 0.])-box([8., 36., 36.], [-3.8, 0., 0.])
    for point in mount_points:
        _, y, z = point
        ring += cylinder(3.0, 3., point, 'x')
        # Each radial corner tie lies clear of the lens and component keepout.
        middle = [-3.8, np.sign(y)*17., np.sign(z)*17.]
        tie = box([3., 10., 4.], [0., 0., 0.])
        tie = transform(tie, Rotation.from_euler('x', 45.*np.sign(y*z), degrees=True).as_matrix(), middle)
        ring += tie
        support_length = carrier_back-front_pcb_face
        ring += cylinder(2.6, support_length,
                         [(front_pcb_face+carrier_back)/2, y, z], 'x')
    ring = holes(ring, mount_points, 2.4, 12., 'x')
    ring_world = transform(ring, rotation, optical)
    anchor = np.array([149.7846096908265, 27.25, 613.])
    corner = optical+rotation@np.array([-3.8, 0., 0.])
    endpoint = np.array([corner[0], 27.25, corner[2]])
    extension = strut(anchor, endpoint)
    extension += box([6., 9., 6.], [corner[0], 24., corner[2]])
    frame = predecessor+extension+ring_world
    # Make a true open optical face, instead of the old solid display plate.
    face = box([2.4, 52., 46.], [2.1, 0., 0.])
    face = face.fillet(9., face.edges().filter_by(Axis.X))
    face -= cylinder(6.5, 12., [2.1, 0., 0.], 'x')
    face = holes(face, [[2.1, y, z] for _, y, z in mount_points], 2.4, 12., 'x')
    face_world = transform(face, rotation, optical)
    eye_ring = cylinder(16.7, 1.2, [3.9, 0., 0.], 'x')-cylinder(15.4, 4., [3.9, 0., 0.], 'x')
    eye_world = transform(eye_ring, rotation, optical)
    export = CandidateExport(ROBOT, 'camera_carrier')
    export.emit('head_frame_camera_carrier', frame, 'head_roll', material='titanium', notes=[
        'One integral CNC aluminium revision of the current retained-jaw head frame; no floating skin anchor.',
        'Current bearing caps, tapping bosses and installation recesses are preserved by native union with the unmodified predecessor.',
        'Existing actuator centres, bearing seats and bolt pattern unchanged. Short cantilever starts at front 30deg stator lug.',
        'Four 28x28mm front-PCB mount centres with candidate 2.4mm bores and 1.020mm support lips; vendor bore sizes unconfirmed.',
        'Camera front screw/spacer retention, native tool path, preload and full assembly sweep are not released.'])
    export.emit('camera_open_face', face_world, 'head_roll', rho=1270., material='graphite', notes=[
        'Own printable PETG rounded face with actual diameter13mm optical aperture and four candidate M2 bores.',
        'The large eye remains an exterior design cue; this face is not a glass lens and no fake lens volume closes its aperture.',
        'Axial spacers/face screws and shell transition are not installed in this candidate.'])
    export.emit('camera_open_eye_bezel', eye_world, 'head_roll', rho=1270., material='orange', notes=[
        'Thin printed colour ring retains the33.4mm large-eye cue around the real central optical aperture.',
        'Nominal rear face touches PETG camera face atlocalX3.3mm; adhesive/process retention is unreleased.'])
    # The OEM supplier model includes one non-solid child. Preserve all four
    # children as expanded conservative envelopes exactly as the prior screen.
    vendor_r = np.asarray(selected['vendor_to_native_rotation'])
    vendor_t = np.asarray(selected['vendor_to_native_translation_mm'])
    keepouts = []
    for group in layout['vendor_subassemblies']:
        bounds = np.asarray(group['bounds_mm'])
        keepouts.append((group['label'], transform(box(bounds[1]-bounds[0]+1.4, bounds.mean(axis=0)), vendor_r, vendor_t)))
    native_inputs = [ROBOT/'cad/source/bill_backbones/head_bill_access_shell_left.brep',
                    ROBOT/'cad/source/jaw_retention/head_retention_access_shell_right.brep']
    native_inputs += [ROBOT/'cad/source/head_load_path/beak_motor_catalog_case.brep']
    cases = []
    for name, candidate in [('head_frame_camera_carrier', frame), ('camera_open_face', face_world), ('camera_open_eye_bezel', eye_world)]:
        for path in native_inputs:
            measured = bounded_common(candidate, import_brep(path), 5.)
            cases.append(dict(candidate=name, other=path.stem, common=measured,
                              clear='error' not in measured and measured['volume_mm3'] < .01))
    # PCB support lips intentionally meet the four mounting regions. Expanded
    # component boxes cannot prove this local mating contact is safe; report
    # all common volumes, without broad collision exemptions.
    component_cases = []
    for name, candidate in [('head_frame_camera_carrier', frame), ('camera_open_face', face_world), ('camera_open_eye_bezel', eye_world)]:
        for label, keepout in keepouts:
            component_cases.append(dict(candidate=name, vendor_child=label,
                expanded_box_common=bounded_common(candidate, keepout, 5.)))
    value = export.save(ROOT, [Path(__file__), layout_path, source, predecessor_manifest_path, ledger_path,
        ROOT/'scripts/cad/goose_candidate_export.py', ROOT/'scripts/cad/build_goose_cad.py',
        ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py']+native_inputs,
        replaces=replaced_names,
        extra=dict(status='NATIVE_CAMERA_CARRIER_CANDIDATE', installed=False, default_model_changed=False,
            camera_layout=selected, full_vendor_children_retained=True,
            camera_mass_kg=None, nominal_camera_allowance_kg=.025,
            native_current_part_cases=cases,
            native_current_part_clearance_pass=all(c['clear'] for c in cases),
            vendor_expanded_component_cases=component_cases,
            supplier_mount_hole_diameter_confirmed=False, mating_plug_and_service_loop_pass=False,
            optical_axis_down_head_deg=selected['optical_pitch_down_in_head_deg'],
            aperture_diameter_mm=13., former_frame_mass_kg=predecessor_record['mass_kg'],
            integral_frame_mass_increase_kg=export.parts[0]['mass_kg']-predecessor_record['mass_kg'],
            retained_jaw_frame_predecessor=predecessor_record,
            predecessor_preserved_by_native_union_with_additions=True,
            replaced_native_and_display_items_mass_kg=sum(current_items[n]['mass_kg'] for n in replaced_names),
            net_candidate_parts_mass_change_kg=sum(p['mass_kg'] for p in export.parts)-sum(current_items[n]['mass_kg'] for n in replaced_names),
            camera_allowance_changed=False, head_structure_reserve_consumed=False,
            face_spacers_and_fasteners_installed=False,
            gate='Own native carrier and open face only. Complete camera mounting, plug, shell transition and vision calibration are not released.'))
    print('CAMERA CARRIER', value['native_mass_kg'], 'current-part clearance', value['native_current_part_clearance_pass'], flush=True)


if __name__ == '__main__':
    main()
