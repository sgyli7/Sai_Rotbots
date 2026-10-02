"""Finite native fit screen with explicit treatment of an invalid OEM solid.

Valid source solids are all retained. Invalid source material is never
certified from a failed/zero boolean: a conservative enclosing box can only
prove separation when its common has a zero upper bound. Otherwise unresolved.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import subprocess
import sys
import time

from build123d import Compound, GeomType, import_step
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad'), str(ROOT / 'scripts/models'), str(ROOT / 'scripts/diagnostics')]
from build_goose_cad import box, cylinder, transform
from build_goose_stage_two import candidate
from check_goose_grip_cassettes import bounded_common
from sai_agent.goose.morphology import apply_leg_layout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(shape):
    value = shape.bounding_box(optimal=False)
    return np.array(tuple(value.min)), np.array(tuple(value.max))


def drawing_circles(path):
    lines = path.read_text(errors='replace').splitlines()
    pairs = [(lines[i].strip(), lines[i + 1].strip()) for i in range(0, len(lines) - 1, 2)]
    circles, current = [], None
    for code, value in pairs:
        if code == '0':
            if current and all(k in current for k in ['10', '20', '40']):
                circles.append([float(current['10']), float(current['20']), float(current['40'])])
            current = {} if value == 'CIRCLE' else None
        elif current is not None:
            current[code] = value
    return circles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wall-time', type=float, default=240)
    parser.add_argument('--pair-timeout', type=float, default=4)
    args = parser.parse_args()
    started = time.monotonic()
    cfg_path = ROBOT / 'configs/compute_module_mounts.json'
    kit_path = ROBOT / 'cad/exports/compute_module_mounts/manifest.json'
    layout_path = ROBOT / 'configs/body_bay_layout_candidate.json'
    scene_path = ROBOT / 'cad/source/mechanical_preview/scene.json'
    ledger_path = ROBOT / 'evidence/body_bay_mechanical_parameters.json'
    cfg, kit, layout, scene, ledger = [json.loads(p.read_text()) for p in
                                     [cfg_path, kit_path, layout_path, scene_path, ledger_path]]
    paths = [cfg_path, kit_path, layout_path, scene_path, ledger_path, Path(__file__),
             ROOT / 'scripts/diagnostics/check_goose_grip_cassettes.py',
             ROOT / 'src/sai_agent/goose/morphology.py']
    for rel, expected in kit['source_hashes'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError(('Stale native source', rel))
    native, owners, kinds, unsafe, quad_records = {}, {}, {}, {}, []
    for part in kit['parts']:
        for record in part['files'].values():
            if sha(ROBOT / record['path']) != record['sha256']:
                raise ValueError(('Changed native file', part['name']))
        shape = import_step(ROBOT / part['files']['step']['path'])
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(('Invalid original candidate', part['name']))
        name = part['name']
        native[name], owners[name], kinds[name] = shape.solids()[0], 'torso', 'original_mount_or_nominal_fastener'
        data = np.load(ROBOT / part['files']['npz']['path'])
        vertices, faces = data['vertices'], data['faces']
        if faces.ndim != 2 or faces.shape[1] != 4 or not np.isfinite(vertices).all():
            raise ValueError(('Invalid quad array', name))
        mesh = trimesh.Trimesh(vertices, np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]]), process=False)
        error = abs(mesh.volume * 1e9 / part['volume_mm3'] - 1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or error > .005:
            raise ValueError(('Quad topology/volume mismatch', name))
        quad_records.append(dict(name=name, quad_faces=len(faces), all_quad=True,
                                 closed=True, winding_consistent=True, volume_relative_error=error))
    supplier, module_checks = [], []
    for module in cfg['modules']:
        path = ROOT / module['vendor_step_path']
        if sha(path) != module['vendor_step_sha256']:
            raise ValueError(('Changed OEM input', module['name']))
        original = import_step(path)
        solids = list(original.solids())
        invalid = [i for i, s in enumerate(solids) if not s.is_valid]
        if invalid != module['known_invalid_vendor_solid_indices']:
            raise ValueError(('Unexpected vendor validity change', module['name'], invalid))
        axes = []
        for face in solids[0].faces():
            if face.geom_type == GeomType.CYLINDER and abs(face.radius - module['mount_hole_diameter_mm'] / 2) < .0001:
                axis = face.axis_of_rotation
                if abs(abs(axis.direction.Z) - 1) < 1e-8:
                    axes.append([axis.position.X, axis.position.Y])
        for xy in module['mount_holes_local_xy_mm']:
            if not any(np.linalg.norm(np.array(xy) - a) < 1e-5 for a in axes):
                raise ValueError(('Expected OEM mounting bore missing', module['name'], xy))
        drawing_checks = []
        if 'drawing_path' in module:
            drawing = ROOT / module['drawing_path']
            if sha(drawing) != module['drawing_sha256']:
                raise ValueError('Changed drawing')
            circles = drawing_circles(drawing)
            for xy in module['mount_holes_local_xy_mm']:
                matches = [c for c in circles if np.linalg.norm(np.array(xy) - c[:2]) < 1e-5
                           and abs(c[2] - module['drawing_mount_hole_radius_mm']) < 1e-6]
                if not matches:
                    raise ValueError(('DXF circle mismatch', xy))
                drawing_checks.append(dict(xy_mm=xy, dxf_radius_mm=matches[0][2],
                                           step_radius_mm=module['mount_hole_diameter_mm'] / 2,
                                           radius_difference_mm=matches[0][2] - module['mount_hole_diameter_mm'] / 2))
            paths.append(drawing)
        placed = transform(original, position=np.array(module['translation_mm']))
        actual_lo, actual_hi = bounds(placed)
        valid_group = Compound(children=[s for i, s in enumerate(solids) if i not in invalid])
        if not valid_group.is_valid:
            raise ValueError('Valid OEM child group is not valid')
        name = module['name'] + '_valid_vendor_solids'
        native[name] = transform(valid_group, position=np.array(module['translation_mm']))
        owners[name], kinds[name] = 'torso', 'all_valid_private_OEM_solids'
        for i in invalid:
            name = module['name'] + '_invalid_vendor_solid_' + str(i)
            native[name] = transform(solids[i], position=np.array(module['translation_mm']))
            owners[name], kinds[name], unsafe[name] = 'torso', 'invalid_private_OEM_solid_retained', True
        allocation = cfg['proposed_compute_allocation_mm']
        center, size = np.array(allocation['centre']), np.array(allocation['size'])
        margins = np.r_[actual_lo - center + size / 2, center + size / 2 - actual_hi]
        module_checks.append(dict(name=module['name'], assembly_valid=original.is_valid,
            solid_count=len(solids), invalid_solid_indices=invalid, all_source_solids_retained=True,
            bounds_mm=[actual_lo.tolist(), actual_hi.tolist()], actual_mount_axes_confirmed=True,
            drawing_circle_checks=drawing_checks, bare_module_inside_proposed_box=bool(np.min(margins) >= -1e-5),
            proposed_box_margins_mm=margins.tolist(), connectors_pogo_retained=True,
            plug_and_cable_clearance_pass=False))
        supplier.append(dict(name=module['name'], path=str(path.relative_to(ROOT)), sha256=sha(path),
            valid_children=len(solids)-len(invalid), invalid_children=len(invalid), originals_private=True))
        paths.append(path)
    new = set(native)
    system = candidate()
    apply_leg_layout(system, layout)
    installed = {p['name'] for p in scene['parts']}
    replaced = set(kit['replaces_existing_parts'])
    folders = ['body_bay_frame', 'body_bay_roll_carriers', 'body_bay_pitch_forks',
               'body_bay_ankle_assembly', 'neck_root_assembly', 'body_bay_skins', 'power_module_mounts']
    for folder in folders:
        path = ROBOT / 'cad/exports' / folder / 'manifest.json'
        paths.append(path)
        for part in json.loads(path.read_text())['parts']:
            name = part['name']
            if name in replaced or (folder != 'power_module_mounts' and name not in installed):
                continue
            record = part['files']['step']
            if sha(ROBOT / record['path']) != record['sha256']:
                raise ValueError(('Changed existing part', name))
            shape = import_step(ROBOT / record['path'])
            if not shape.is_valid or len(shape.solids()) != 1:
                raise ValueError(('Invalid existing native', name))
            shape = shape.solids()[0]
            placement = part.get('world_from_local_mm')
            if placement:
                shape = transform(shape, np.array(placement['rotation']), np.array(placement['translation']))
            native[name], owners[name], kinds[name] = shape, part['body'], 'current_native_' + folder
        print('COMPUTE FIT INPUT', folder, len(native), flush=True)
    for side in ['right', 'left']:
        for suffix in ['hip_yaw', 'hip_roll', 'hip_pitch', 'knee_pitch', 'ankle_pitch']:
            joint = side + '_' + suffix
            if suffix == 'hip_yaw':
                shape, rotation = cylinder(26.5, 39.2, [0, 0, -.5]), np.eye(3)
            else:
                shape = cylinder(27.5, 53.5, [0, -1.5, 0], 'y') - cylinder(9, 1.5, [0, 25.5, 0], 'y')
                rotation = (np.array([[0., 1., 0.], [1., 0., 0.], [0., 0., -1.]]) if suffix == 'hip_roll'
                            else np.eye(3) if side == 'left' else np.diag([1., -1., -1.]))
            name = joint + '_catalog_stator'
            native[name] = transform(shape, rotation, system.pivots[joint] * 1000)
            owners[name], kinds[name] = system.parents[joint], 'catalog_stator_envelope_not_OEM_full_CAD'
    native['neck_yaw_catalog_stator'] = cylinder(26.5, 39.2, system.pivots['neck_yaw'] * 1000 - [0, 0, .5])
    owners['neck_yaw_catalog_stator'], kinds['neck_yaw_catalog_stator'] = 'torso', 'catalog_stator_envelope_not_OEM_full_CAD'
    for name, allocation in layout['electronics_allowance_boxes_mm'].items():
        if name == 'compute_stack':
            continue
        native[name] = box(allocation['size'], allocation['centre'])
        owners[name], kinds[name] = 'torso', 'retained_module_allowance_not_actual_module_CAD'
    cases = [('zero', {})]
    for side in ['right', 'left']:
        for yaw, roll in itertools.product([-.6, 0, .6], [-.5, 0, .5]):
            if yaw or roll:
                cases.append((side + '_yaw_roll_' + str((yaw, roll)), {side + '_hip_yaw': yaw, side + '_hip_roll': roll}))
    for yaw, roll, opposite in itertools.product([-.6, .6], [-.5, .5], [False, True]):
        q = {side + '_' + axis: value * (-1 if opposite and side == 'right' else 1)
             for side in ['right', 'left'] for axis, value in [('hip_yaw', yaw), ('hip_roll', roll)]}
        cases.append(('bilateral_' + str((yaw, roll, opposite)), q))
    cases += [('static_' + row['name'], row['joint_q_rad']) for row in ledger['results']
              if row['mass_variant'] == 0 and row['drag_x_n'] == 0]
    cases += [('neck_yaw_' + str(q), {'neck_yaw': q}) for q in [-.6, .6]]
    threads = {frozenset([t['screw'], t['tapped_part']]): t for t in kit['nominal_thread_contacts']}
    names = list(native)
    pairs = [(a, b) for a, b in itertools.combinations(names, 2) if a in new or b in new]
    # Do not reinterpret original OEM internal contacts as our mounting clashes.
    pairs = [(a, b) for a, b in pairs if not
             (a.startswith('radxa_zero_3w_') and b.startswith('radxa_zero_3w_') and 'vendor_' in a and 'vendor_' in b)]
    indices = np.array([[names.index(a), names.index(b)] for a, b in pairs])
    cache, reports, queries = {}, [], []
    interrupted = False
    for case_name, q in cases:
        poses, _ = system.fk(q, root_p=system.pivots['torso'])
        posed, boxes = {}, []
        for name in names:
            body = owners[name]
            position, rotation = poses[body]
            offset = (position - rotation @ system.pivots[body]) * 1000
            posed[name] = transform(native[name], rotation, offset)
            boxes.append(bounds(posed[name]))
        boxes = np.array(boxes)
        lo = np.maximum(boxes[indices[:, 0], 0], boxes[indices[:, 1], 0])
        hi = np.minimum(boxes[indices[:, 0], 1], boxes[indices[:, 1], 1])
        relevant = np.flatnonzero(np.all(hi - lo > 1e-6, axis=1))
        hits, unknown, contacts = [], [], []
        for index in relevant:
            a, b = pairs[index]
            if time.monotonic() - started >= args.wall_time:
                interrupted = True
                break
            key = (a, b)
            if owners[a] == 'torso' and owners[b] == 'torso' and key in cache:
                result = cache[key]
            else:
                if a in unsafe or b in unsafe:
                    bad, other = (a, b) if a in unsafe else (b, a)
                    j = names.index(bad)
                    enclosing = box((boxes[j, 1] - boxes[j, 0]).tolist(), ((boxes[j, 1] + boxes[j, 0]) / 2).tolist())
                    upper = bounded_common(enclosing, posed[other], args.pair_timeout)
                    queries.append(dict(case=case_name, a=a, b=b, method='invalid_source_conservative_AABB_upper_bound', **upper))
                    result = (dict(volume_mm3=upper['volume_mm3'], upper_bound_only=True) if
                              'error' not in upper and upper['volume_mm3'] <= .01 else
                              dict(error='Invalid OEM solid cannot be certified; enclosing box overlaps or query is unresolved',
                                   enclosing_box_result=upper))
                else:
                    result = bounded_common(posed[a], posed[b], args.pair_timeout)
                    queries.append(dict(case=case_name, a=a, b=b, **result))
                    if 'error' in result:
                        j = names.index(a)
                        enclosing = box((boxes[j, 1] - boxes[j, 0]).tolist(), ((boxes[j, 1] + boxes[j, 0]) / 2).tolist())
                        upper = bounded_common(enclosing, posed[b], args.pair_timeout)
                        queries.append(dict(case=case_name, a=a, b=b, method='valid_source_conservative_AABB_upper_bound', **upper))
                        if 'error' not in upper and upper['volume_mm3'] <= .01:
                            result = dict(volume_mm3=upper['volume_mm3'], upper_bound_only=True,
                                          original_query_error=result['error'])
                if owners[a] == 'torso' and owners[b] == 'torso':
                    cache[key] = result
            if 'error' in result:
                unknown.append(dict(a=a, b=b, **result))
            elif frozenset([a, b]) in threads:
                contacts.append(dict(a=a, b=b, volume_mm3=result['volume_mm3'], basis='explicit nominal thread envelope'))
            elif result['volume_mm3'] > .01:
                hits.append(dict(a=a, b=b, volume_mm3=result['volume_mm3'], basis=[kinds[a], kinds[b]]))
        own_unknown = [r for r in unknown if r['a'] not in unsafe and r['b'] not in unsafe]
        reports.append(dict(name=case_name, joint_q_rad=q, collisions=hits, unresolved=unknown,
            nominal_thread_contacts=contacts, complete=not interrupted,
            valid_source_sampled_fit_pass=not hits and not own_unknown and not interrupted,
            all_sources_sampled_fit_pass=not hits and not unknown and not interrupted))
        print('COMPUTE FIT CASE', case_name, 'hits', len(hits), 'unresolved', len(unknown), flush=True)
        if interrupted:
            break
    baseline = []
    for path in [scene_path, ledger_path, ROBOT / 'configs/mechanical_physics_contract.json', ROBOT / 'models/mechanical_physics/robot.xml']:
        rel = str(path.relative_to(ROOT))
        previous = subprocess.run(['git', 'show', '34822285:' + rel], cwd=ROOT, capture_output=True, check=True).stdout
        if sha(path) != hashlib.sha256(previous).hexdigest():
            raise ValueError(('Default assembly changed', rel))
        baseline.append(dict(path=rel, sha256=sha(path), unchanged=True))
        if path not in paths:
            paths.append(path)
    complete = len(reports) == len(cases) and all(r['complete'] for r in reports)
    valid_fit = complete and all(r['valid_source_sampled_fit_pass'] for r in reports)
    full_fit = complete and all(r['all_sources_sampled_fit_pass'] for r in reports)
    result = dict(schema='goose_compute_module_mount_fit_v1', own_native_parts=len(kit['parts']),
        own_native_mass_kg=kit['native_mass_kg'], conservative_added_mass_kg=kit['conservative_added_mass_kg'],
        retained_compute_reservation_kg=cfg['retained_combined_compute_mass_reservation_kg'],
        quad_sources=quad_records, supplier_inputs=supplier, module_checks=module_checks,
        new_named_solids=len(new), checked_existing_named_solids=len(native)-len(new),
        considered_pairs_per_pose=len(pairs), requested_poses=len(cases), completed_poses=len(reports),
        cases=reports, actual_native_queries=queries, finite_screen_complete=complete,
        valid_sources_sampled_fit_pass=valid_fit, all_sources_sampled_fit_pass=full_fit,
        supplier_geometry_validity_pass=not unsafe, invalid_supplier_entities=list(unsafe),
        bare_modules_inside_proposed_box=all(m['bare_module_inside_proposed_box'] for m in module_checks),
        frame_stacks=kit['frame_stacks'], nominal_thread_contacts=kit['nominal_thread_contacts'],
        proposed_compute_allocation_mm=cfg['proposed_compute_allocation_mm'],
        old_compute_box_not_silently_changed=True, default_assembly_unchanged=True, default_baseline=baseline,
        can_allocation_issue=dict(source='https://www.waveshare.com/img/devkit/accBoard/USB-CAN-A/USB-CAN-A-details-size.jpg',
            sha256='625b569595c607ca0ba536c1885fb8f62499a23abac1e7c05c8dd9ba77b5e70e',
            overall_length_mm=78.52, body_length_mm=56.38, terminal_length_mm=8.87, plan_width_mm=18.36,
            inherited_box_size_mm=layout['electronics_allowance_boxes_mm']['dual_can_interface_allocation']['size'],
            adapter_plug_body_terminal_not_within_old_70x16_reserve=True, adapter_mount_and_wiring_pass=False),
        installed=False, full_assembly_pass=False, hardware_freeze=False,
        manufacturing_release=False, electrical_release=False, stage_three_four_complete=False,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths},
        limitations=['Finite sampled increment screen; neither continuous sweep nor whole-assembly acceptance.',
            'Radxa V1.11 original has one invalid solid; it is retained. Positive/unknown enclosing-box common is unresolved.',
            'All121 valid hub solids, including USB connector bodies and pogo pins, retained. Real plugs/cables absent.',
            'PCB bore coordinates are checked against OEM STEP; Radxa DXF agrees on centers, radius differs by0.0097mm.',
            'Independent tap posts, insulating washers and nominal thread contacts do not certify tolerances/preload or electrical insulation.',
            'Candidate compute bay grows4mm vertically only; default344-part model and mass/inertia unchanged.',
            'M3 chassis holes and monolithic6061 rack need machining, local-stress and assembly-order review.',
            'USB-CAN-A official plan drawing exceeds inherited70x16mm reserve; actual thickness/plug routing/mount remain unresolved.'])
    out = ROBOT / 'evidence/compute_module_mount_fit.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print('COMPUTE FIT COMPLETE', complete, 'valid_sources_fit', valid_fit, 'all_sources_fit', full_fit, flush=True)
    # A retained failure record is a successful diagnostic run, not a release.
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
