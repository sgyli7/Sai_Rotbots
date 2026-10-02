"""Close the actual camera/head gap and replace stepped rear skin boundaries.

Independent native candidate; preserves the frozen419-part scene. Commercial
optics remain a measured dimensional display reference, never a print part.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from scipy.spatial.transform import Rotation
from build123d import Axis, Edge, Wire, Solid, import_brep, export_brep

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad'), str(ROOT / 'scripts/diagnostics')]
from build_goose_cad import box, cylinder, holes, transform
from build_goose_manufacturing_skins import head_grid
from goose_nurbs_skin import skin
from goose_candidate_export import CandidateExport


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_paths = [
        ROBOT / 'cad/exports/camera_carrier/manifest.json',
        ROBOT / 'evidence/camera_catalog_layout.json',
        ROBOT / 'cad/source/stage_two_architecture/scene.json',
        ROBOT / 'cad/source/camera_carrier/head_frame_camera_carrier.brep',
        ROBOT / 'cad/source/camera_carrier/camera_open_face.brep',
        ROBOT / 'cad/source/bill_backbones/head_bill_access_shell_left.brep',
        ROBOT / 'cad/source/jaw_retention/head_retention_access_shell_right.brep',
    ]
    manifest, catalog, old_scene = [json.loads(p.read_text()) for p in source_paths[:3]]
    optical = np.array(catalog['selected']['optical_front_native_world_mm'])
    rotation = Rotation.from_euler('y', catalog['selected']['optical_pitch_down_in_head_deg'], degrees=True).as_matrix()
    def world(shape):
        return transform(shape, rotation, optical)
    parts = {}
    export = CandidateExport(ROBOT, 'camera_head_closure')
    thread_contacts, bearing_contacts, supplier_threads = [], [], []

    # Keep the four OEM corner standoffs; own front support uses clearance
    # bores and insulation. Screws enter OEM posts from the optical side.
    predecessor_path = ROBOT / 'cad/source/jaw_retention/head_frame_with_jaw_retention.brep'
    source_paths.append(predecessor_path)
    ring_outer = box([3., 40., 40.], [-3.8, 0., 0.])
    ring_outer = ring_outer.fillet(9., ring_outer.edges().filter_by(Axis.X))
    ring_inner = box([8., 36., 36.], [-3.8, 0., 0.])
    ring_inner = ring_inner.fillet(7., ring_inner.edges().filter_by(Axis.X))
    ring = ring_outer - ring_inner
    for y in [-14., 14.]:
        for z in [-14., 14.]:
            ring += cylinder(3., 3., [-3.8, y, z], 'x')
            tie = transform(box([3., 4., 2.]), Rotation.from_euler('x', 45.*np.sign(y*z), degrees=True).as_matrix(),
                [-3.8, np.sign(y)*15.9, np.sign(z)*15.9])
            ring += tie
            ring += cylinder(2.6, .52, [-5.56, y, z], 'x')
            ring -= cylinder(1.2, 12., [-4., y, z], 'x')
    # Separate face fasteners avoid two opposing screws in one tapped bore.
    face_centers = [(y, z) for y in [-19., 19.] for z in [-12., 12.]]
    for y, z in face_centers:
        ring += cylinder(2.6, 3., [-3.8, y, z], 'x')
        ring += cylinder(2.6, 1.5, [-1.55, y, z], 'x')
        ring -= cylinder(.8, 12., [-3.8, y, z], 'x')
    corner = optical + rotation @ np.array([-3.8, 0., 0.])
    anchor = np.array([149.7846096908265, 27.25, 613.])
    endpoint = np.array([corner[0], 19.2, corner[2]])
    elbow = np.array([160., 27.25, 611.])
    def carrier_strut(a, b):
        delta = b - a
        axis_x = delta / np.linalg.norm(delta)
        axis_z = np.array([0., 0., 1.]) - axis_x * axis_x[2]
        axis_z /= np.linalg.norm(axis_z)
        axis_y = np.cross(axis_z, axis_x)
        return transform(box([np.linalg.norm(delta)+2., 3., 6.]),
            np.column_stack([axis_x, axis_y, axis_z]), (a+b)/2)
    # Remain outside the real motor until X160mm, then turn inward.
    extension = carrier_strut(anchor, elbow) + carrier_strut(elbow, endpoint)
    frame = import_brep(predecessor_path) + extension + world(ring)
    if not frame.is_valid or len(frame.solids()) != 1:
        failure = ROOT / 'artifacts/Goose_V0.1/camera_closure_failures'
        failure.mkdir(parents=True, exist_ok=True)
        export_brep(frame, failure / 'camera_tapped_frame_invalid.brep')
        raise ValueError(('camera frame native failure', frame.is_valid, len(frame.solids())))
    parts['head_frame_camera_fastened_carrier'] = frame
    export.emit('head_frame_camera_fastened_carrier', frame, 'head_roll', material='titanium', notes=[
        'Current jaw-retaining frame preserved; four PCB support bores are2.4mm clearance with shortened insulation seats.',
        'Four separate face M2 taps at Y±19/Z±12; OEM PCB corner standoffs are retained and receive the front mounting screws.',
        'Nominal thread, CNC tool path, grade/preload and local strength still require release.'])

    face = box([2.4, 52., 46.], [2.1, 0., 0.])
    face = face.fillet(9., face.edges().filter_by(Axis.X))
    face -= cylinder(6.5, 12., [2.1, 0., 0.], 'x')
    face = holes(face, [[2.1, y, z] for y, z in face_centers], 2.4, 12., 'x')
    parts['camera_fastened_open_face'] = world(face)
    export.emit('camera_fastened_open_face', parts['camera_fastened_open_face'], 'head_roll', rho=1270., material='graphite', notes=[
        'Original optical plane, rounded52x46mm face,13mm aperture and large-eye ring retained.',
        'Four new independent face mounting positions; obsolete floating-face hole pattern removed.'])

    # Match the rear perimeter to the actual head source, then form a smooth
    # thin shell toward the real tilted face. No image-only gap filler.
    outer, _ = head_grid(old_scene)
    rear = outer[-1].copy()
    rear[:, 0] += .25
    # The existing chin is already cut away belowZ581mm. Do not loft an
    # imaginary lower perimeter through the bill or across the tilted face.
    z = rear[:, 2]
    rear[:, 2] = .5 * (z + 581.5 + np.sqrt((z - 581.5)**2 + .3**2))
    inner_rear = rear.copy()
    for row in inner_rear:
        v = row - [177.25, 0., 600.]
        v[0] = 0.
        row -= 2.2 * v / np.linalg.norm(v)
    phi = np.linspace(-np.pi / 2, 3 * np.pi / 2, 65)
    def front_ring(ry, rz):
        local = np.column_stack((np.full(65, .4),
            ry * np.sign(np.cos(phi)) * np.abs(np.cos(phi))**(2 / 2.8),
            rz * np.sign(np.sin(phi)) * np.abs(np.sin(phi))**(2 / 2.8)))
        return local @ rotation.T + optical
    front, front_inner = front_ring(27., 24.), front_ring(24.8, 21.8)
    t = np.linspace(0., 1., 6)[:, None, None]
    out_grid = rear[None] * (1 - t) + front[None] * t
    in_grid = inner_rear[None] * (1 - t) + front_inner[None] * t
    def loop(points):
        return Wire(Edge.make_spline([tuple(p) for p in points[:-1]], periodic=True))
    nose = Solid.make_loft([loop(rear), loop(front)], ruled=True)
    a = inner_rear * 1.06 - front_inner * .06
    b = front_inner * 1.06 - inner_rear * .06
    nose -= Solid.make_loft([loop(a), loop(b)], ruled=True)
    print('NOSE LOFT', nose.is_valid, len(nose.solids()), flush=True)
    land = box([1.2, 52., 46.], [.3, 0., 0.])
    land = land.fillet(9., land.edges().filter_by(Axis.X))
    land -= cylinder(6.5, 12., [.3, 0., 0.], 'x')
    land = holes(land, [[.3, y, z] for y, z in face_centers], 2.4, 12., 'x')
    # Driver access to the four OEM-standoff screws, hidden under the face.
    for y in [-14., 14.]:
        for z in [-14., 14.]:
            land -= cylinder(2.15, 2., [.3, y, z], 'x')
    nose += world(land)
    print('NOSE LAND', nose.is_valid, len(nose.solids()), flush=True)
    access = box([44., 66., 34.], [163., 0., 564.])
    access = access.fillet(4., access.edges())
    nose -= access
    print('NOSE ACCESS', nose.is_valid, len(nose.solids()), flush=True)
    if not nose.is_valid or len(nose.solids()) != 1:
        failure = ROOT / 'artifacts/Goose_V0.1/camera_closure_failures'
        failure.mkdir(parents=True, exist_ok=True)
        export_brep(nose, failure / 'camera_nose_invalid.brep')
        np.savez_compressed(failure / 'camera_nose_construction.npz', outer=out_grid, inner=in_grid)
        raise ValueError(('camera nose native failure', nose.is_valid, len(nose.solids())))
    parts['head_camera_nose_shroud'] = nose
    export.emit('head_camera_nose_shroud', nose, 'head_roll', rho=1270., material='ivory', notes=[
        'Printable smooth hollow bridge from original head front perimeter X177mm to actual tilted camera face.',
        'Rear0.25mm nominal assembly seam;1.2mm front land retained by the four face bolts with nylon isolation.',
        'Existing rounded chin installation cut retained; open optics unchanged.',
        'Source nodes share the actual head contour; no mesh displacement or cosmetic solid plugging.'])

    # The old grid-mask aperture ended at X<99mm. One continuous native rear
    # cut replaces its stair steps; the input remains preserved unmodified.
    for side, source in [('left', source_paths[5]), ('right', source_paths[6])]:
        shape = import_brep(source) - box([1000., 1000., 1000.], [-399.25, 0., 600.])
        rear_edges = [e for e in shape.edges() if
            abs(e.bounding_box().min.X - 100.75) < 1e-4 and
            abs(e.bounding_box().max.X - 100.75) < 1e-4 and e.length > .3]
        # A modest rolled edge, less than a quarter of the nominal2.2mm wall.
        shape = shape.fillet(.4, rear_edges)
        name = 'head_camera_access_shell_' + side
        parts[name] = shape
        export.emit(name, shape, 'head_roll', rho=1270., material='ivory', notes=[
            'Original front/cheek native skin and access holes retained; continuous rear opening at X100.75mm replaces the grid-mask stair boundary.',
            'Native0.4mm rear edge fillet; no shading-only smoothing.',
            'Rear service opening is intentional; rear collar/cable seal and complete head shell/frame attachment remain gates.'])

    def washer(name, x, y, z):
        shape = world(cylinder(2., .5, [x, y, z], 'x') - cylinder(1.1, 2., [x, y, z], 'x'))
        parts[name] = shape
        export.emit(name, shape, 'head_roll', rho=1150., material='seam', notes=['Nominal M2 nylon4OD/2.2ID/.5mm insulating washer; purchase tolerance/creep pending.'])
    def screw(name, seat, y, z, length, engagement, direction=-1.):
        local = cylinder(1., length, [seat + direction * length / 2, y, z], 'x')
        local += cylinder(1.9, 2., [seat - direction, y, z], 'x')
        parts[name] = world(local)
        export.emit(name, parts[name], 'head_roll', rho=7850., material='titanium', notes=[
            f'Nominal M2x{length:g} socket-head screw,3.8OD/2.0height nominal head; thread envelope only; bought SKU/grade/preload/drive tool pending.'])
        thread_contacts.append(dict(screw=name, frame='head_frame_camera_fastened_carrier',
            major_diameter_mm=2., minor_diameter_mm=1.6, thread_engagement_mm=engagement,
            expected_thread_overlap_mm3=float(np.pi * (1.**2 - .8**2) * engagement)))
    for i, (y, z) in enumerate((y, z) for y in [-14., 14.] for z in [-14., 14.]):
        washer(f'camera_pcb_{i}_head_nylon_washer', -2.05, y, z)
        washer(f'camera_pcb_{i}_front_nylon_washer', -6.07, y, z)
        screw(f'camera_pcb_{i}_m2x10', -1.8, y, z, 10., 3.88)
        thread_contacts.pop()
        supplier_threads.append(dict(screw=f'camera_pcb_{i}_m2x10', supplier_group='UC-A51_Rev_B',
            major_diameter_mm=2., source_bore_radius_mm=.7835, thread_engagement_mm=3.88,
            expected_thread_overlap_mm3=float(np.pi*(1.-.7835**2)*3.88),
            basis='Nominal M2 envelope in retained OEM corner standoff; bought thread and preload unqualified'))
        bearing_contacts += [dict(a=f'camera_pcb_{i}_front_nylon_washer', b='supplier_front_pcb')]
    for i, (y, z) in enumerate(face_centers):
        washer(f'camera_face_{i}_front_nylon_washer', 3.55, y, z)
        washer(f'camera_face_{i}_rear_nylon_washer', -.55, y, z)
        screw(f'camera_face_{i}_m2x10', 3.8, y, z, 10., 4.5)

    replaced = ['head_frame_camera_carrier', 'camera_open_face',
                'head_bill_access_shell_left', 'head_retention_access_shell_right']
    predecessor_mass = manifest['parts'][0]['mass_kg'] + manifest['parts'][1]['mass_kg']
    ledger = json.loads((ROBOT / 'evidence/integrated_hardware_parameters.json').read_text())
    predecessor_mass += sum(p['mass_kg'] for p in ledger['items'] if p['name'] in replaced[2:])
    inputs = source_paths + [Path(__file__), ROBOT / 'evidence/integrated_hardware_parameters.json',
        ROOT / 'scripts/cad/goose_candidate_export.py', ROOT / 'scripts/cad/goose_nurbs_skin.py',
        ROOT / 'scripts/cad/build_goose_manufacturing_skins.py', ROOT / 'scripts/cad/build_goose_cad.py']
    value = export.save(ROOT, inputs, replaces=replaced, extra=dict(
        status='CAMERA_AND_HEAD_CLOSURE_NATIVE_CANDIDATE', installed=False,
        optical_front_native_world_mm=optical.tolist(), optical_pitch_down_head_deg=20.,
        rear_opening_x_native_mm=100.75, rear_edge_fillet_mm=.4,
        nominal_thread_contacts=thread_contacts, nominal_oem_thread_contacts=supplier_threads, nominal_pcb_washer_contacts=bearing_contacts,
        replaced_native_mass_kg=predecessor_mass,
        net_native_mass_change_kg=sum(p['mass_kg'] for p in export.parts) - predecessor_mass,
        camera_mass_allowance_kg=.025, camera_allowance_consumed=False,
        vendor_revision_and_plug_release=False, head_shell_to_frame_release=False,
        source419_scene_changed=False, final_appearance_pass=False,
        gate='Native closure and fasteners only; verify all own/vendor contacts, mass and render before adoption.'))
    print('HEAD CLOSURE', len(value['parts']), 'parts', 'mass delta', value['net_native_mass_change_kg'], flush=True)


if __name__ == '__main__':
    main()
