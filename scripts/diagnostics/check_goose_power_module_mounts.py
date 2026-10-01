"""Bounded OEM/native screen for the two frame-mounted DC/DC candidates.

Checks every new-new pair and every new-current named solid pair in finite
poses. Intended smooth-shaft/tap-bore overlap is measured separately. A
timebox or kernel error is unresolved, never treated as zero intersection.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import subprocess
import sys
import time

from build123d import GeomType, import_step
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wall-time', type=float, default=240)
    parser.add_argument('--pair-timeout', type=float, default=4)
    args = parser.parse_args()
    started = time.monotonic()
    config_path = ROBOT / 'configs/power_module_mounts.json'
    mount_path = ROBOT / 'cad/exports/power_module_mounts/manifest.json'
    layout_path = ROBOT / 'configs/body_bay_layout_candidate.json'
    scene_path = ROBOT / 'cad/source/mechanical_preview/scene.json'
    ledger_path = ROBOT / 'evidence/body_bay_mechanical_parameters.json'
    config, kit, layout, scene, ledger = [json.loads(p.read_text()) for p in
        [config_path, mount_path, layout_path, scene_path, ledger_path]]
    paths = [config_path, mount_path, layout_path, scene_path, ledger_path, Path(__file__),
        ROOT / 'scripts/diagnostics/check_goose_grip_cassettes.py',
        ROOT / 'src/sai_agent/goose/morphology.py']
    for rel, expected in kit['source_hashes'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError(('Stale mount construction', rel))

    system = candidate()
    apply_leg_layout(system, layout)
    native, owners, kinds, quad_records = {}, {}, {}, []
    for part in kit['parts']:
        for record in part['files'].values():
            path = ROBOT / record['path']
            if sha(path) != record['sha256']:
                raise ValueError(('Changed own native file', part['name'], path))
        shape = import_step(ROBOT / part['files']['step']['path'])
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(('Invalid native candidate', part['name']))
        native[part['name']] = shape.solids()[0]
        owners[part['name']], kinds[part['name']] = 'torso', 'original_mount_or_nominal_fastener'
        data = np.load(ROBOT / part['files']['npz']['path'])
        vertices, faces = data['vertices'], data['faces']
        if faces.ndim != 2 or faces.shape[1] != 4 or not np.isfinite(vertices).all():
            raise ValueError(('Invalid quad source', part['name']))
        mesh = trimesh.Trimesh(vertices, np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]]), process=False)
        relative = abs(mesh.volume * 1e9 / part['volume_mm3'] - 1)
        if not mesh.is_watertight or not mesh.is_winding_consistent or relative > .005:
            raise ValueError(('Invalid quad volume/closure', part['name']))
        quad_records.append(dict(part=part['name'], faces=len(faces), all_quad=True,
            closed=True, winding_consistent=True, volume_relative_error=relative))

    supplier, module_checks = [], []
    for module in config['modules']:
        path = ROOT / module['vendor_step_path']
        drawing = ROOT / module['drawing_path']
        if sha(path) != module['vendor_step_sha256'] or sha(drawing) != module['drawing_sha256']:
            raise ValueError(('Changed OEM input', module['name']))
        original = import_step(path)
        if not original.is_valid or len(original.solids()) != 1:
            raise ValueError(('Invalid OEM solid', module['name']))
        original = original.solids()[0]
        axes = []
        for face in original.faces():
            if face.geom_type == GeomType.CYLINDER and abs(face.radius - module['mount_hole_diameter_mm'] / 2) < 1e-5:
                axis = face.axis_of_rotation
                if abs(abs(axis.direction.Z) - 1) < 1e-8:
                    axes.append([axis.position.X, axis.position.Y])
        for hole in module['mount_holes_local_xy_mm']:
            if not any(np.linalg.norm(np.array(hole) - axis) < 1e-5 for axis in axes):
                raise ValueError(('Expected PCB mounting bore absent from actual OEM STEP', module['name'], hole))
        placed = transform(original, position=np.array(module['translation_mm']))
        name = module['name'] + '_supplier_solid'
        native[name], owners[name], kinds[name] = placed, 'torso', 'actual_private_OEM_STEP'
        actual_lo, actual_hi = bounds(placed)
        allocation = layout['electronics_allowance_boxes_mm'][module['name']]
        center, size = np.array(allocation['centre']), np.array(allocation['size'])
        margin_lo, margin_hi = actual_lo - (center - size / 2), center + size / 2 - actual_hi
        module_checks.append(dict(name=module['name'], conservative_native_bounds_mm=[actual_lo.tolist(), actual_hi.tolist()],
            unchanged_allocation_bounds_mm=[(center-size/2).tolist(), (center+size/2).tolist()],
            bare_module_in_allocated_box=bool(np.min(np.r_[margin_lo, margin_hi]) >= -1e-5),
            lower_clearance_mm=margin_lo.tolist(), upper_clearance_mm=margin_hi.tolist(),
            actual_oem_mount_holes_confirmed=True, soldered_wire_clearance_pass=False))
        supplier.append(dict(name=module['name'], path=str(path.relative_to(ROOT)), sha256=sha(path),
                             drawing_sha256=sha(drawing), unit='mm', retained_private=True))

    new = set(native)
    installed_names = {p['name'] for p in scene['parts']}
    # Keep the actual current lower-body structures and neck root, not the
    # historical carriers that were replaced in the344-part scene.
    folders = ['body_bay_frame', 'body_bay_roll_carriers', 'body_bay_pitch_forks',
               'body_bay_ankle_assembly', 'neck_root_assembly', 'body_bay_skins']
    for folder in folders:
        path = ROBOT / 'cad/exports' / folder / 'manifest.json'
        paths.append(path)
        for part in json.loads(path.read_text())['parts']:
            name = part['name']
            if name not in installed_names:
                continue
            record = part['files']['step']
            step_path = ROBOT / record['path']
            if sha(step_path) != record['sha256']:
                raise ValueError(('Changed current native source', name))
            shape = import_step(step_path)
            if not shape.is_valid or len(shape.solids()) != 1:
                raise ValueError(('Invalid current native source', name))
            shape = shape.solids()[0]
            placement = part.get('world_from_local_mm')
            if placement:
                shape = transform(shape, np.array(placement['rotation']), np.array(placement['translation']))
            native[name], owners[name], kinds[name] = shape, part['body'], 'current_native_' + folder
        print('POWER FIT INPUT', folder, len(native), flush=True)

    for side in ['right', 'left']:
        for suffix in ['hip_yaw', 'hip_roll', 'hip_pitch', 'knee_pitch', 'ankle_pitch']:
            joint = side + '_' + suffix
            if suffix == 'hip_yaw':
                shape = cylinder(26.5, 39.2, [0, 0, -.5])
                rotation = np.eye(3)
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
        if name in ['logic_buck', 'servo_buck']:
            continue  # Replaced by the actual OEM solids above, not counted as clashes with their own allowance.
        native[name] = box(allocation['size'], allocation['centre'])
        owners[name], kinds[name] = 'torso', 'retained_module_allowance_not_actual_module_CAD'

    cases = [('zero', {})]
    for side in ['right', 'left']:
        for yaw, roll in itertools.product([-.6, 0, .6], [-.5, 0, .5]):
            if yaw or roll:
                cases.append((side + '_yaw_roll_' + str((yaw, roll)),
                              {side + '_hip_yaw': yaw, side + '_hip_roll': roll}))
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
    cache, reports, queries = {}, [], []
    interrupted = False
    for case_name, q in cases:
        poses, _ = system.fk(q, root_p=system.pivots['torso'])
        posed, boxes = {}, {}
        for name, shape in native.items():
            body = owners[name]
            position, rotation = poses[body]
            offset = (position - rotation @ system.pivots[body]) * 1000
            posed[name] = transform(shape, rotation, offset)
            boxes[name] = bounds(posed[name])
        hits, unknown, contacts = [], [], []
        for a, b in pairs:
            if time.monotonic() - started >= args.wall_time:
                interrupted = True
                break
            lo = np.maximum(boxes[a][0], boxes[b][0])
            hi = np.minimum(boxes[a][1], boxes[b][1])
            if np.any(hi - lo <= 1e-6):
                continue
            key = (a, b)
            if owners[a] == 'torso' and owners[b] == 'torso' and key in cache:
                result = cache[key]
            else:
                result = bounded_common(posed[a], posed[b], args.pair_timeout)
                queries.append(dict(case=case_name, a=a, b=b, **result))
                if 'error' in result:
                    # BRep conservative bounds contain the entire original
                    # solid, not merely its sampled mesh. A passed native
                    # box-versus-B common bounds the original common from
                    # above. Positive/unknown box results cannot acquit it.
                    enclosing = box((boxes[a][1] - boxes[a][0]).tolist(),
                                    ((boxes[a][1] + boxes[a][0]) / 2).tolist())
                    bound = bounded_common(enclosing, posed[b], args.pair_timeout)
                    queries.append(dict(case=case_name, a=a, b=b, method='conservative_native_AABB_upper_bound',
                        enclosing_bounds_mm=[boxes[a][0].tolist(), boxes[a][1].tolist()], **bound))
                    if 'error' not in bound and bound['volume_mm3'] <= .01:
                        result = dict(volume_mm3=bound['volume_mm3'],
                            upper_bound_only=True, original_native_query_error=result['error'],
                            method='original solid contained in conservative native AABB with measured common <=.01mm3')
                if owners[a] == 'torso' and owners[b] == 'torso':
                    cache[key] = result
            if 'error' in result:
                unknown.append(dict(a=a, b=b, **result))
            elif frozenset([a, b]) in threads:
                contacts.append(dict(a=a, b=b, volume_mm3=result['volume_mm3'],
                                     basis='explicit smooth major-diameter shaft against tap minor bore'))
            elif result['volume_mm3'] > .01:
                hits.append(dict(a=a, b=b, volume_mm3=result['volume_mm3'], basis=[kinds[a], kinds[b]]))
        passed = not hits and not unknown and not interrupted
        reports.append(dict(name=case_name, joint_q_rad=q, collisions=hits, unresolved=unknown,
            nominal_thread_contacts=contacts, complete=not interrupted, nominal_named_fit_pass=passed))
        print('POWER FIT CASE', case_name, 'hits', len(hits), 'unresolved', len(unknown), flush=True)
        if interrupted:
            break

    pass_fit = len(reports) == len(cases) and all(row['nominal_named_fit_pass'] for row in reports)
    shaft_increment = 4 * np.pi * (3 / 2) ** 2 * 2 * 7850e-9
    own_new_mass = sum(p['mass_kg'] for p in kit['parts'] if not p['name'].startswith('neck_power_frame_'))
    baseline_commit = '34822285'
    baseline_files = [scene_path, ledger_path, ROBOT / 'configs/mechanical_physics_contract.json',
                      ROBOT / 'models/mechanical_physics/robot.xml']
    baseline = []
    for path in baseline_files:
        relative = str(path.relative_to(ROOT))
        previous = subprocess.run(['git', 'show', baseline_commit + ':' + relative],
            cwd=ROOT, capture_output=True, check=True).stdout
        expected = hashlib.sha256(previous).hexdigest()
        if sha(path) != expected:
            raise ValueError(('Default assembly was modified', relative))
        baseline.append(dict(path=relative, sha256=expected, unchanged=True))
    paths.extend(baseline_files[2:])
    result = dict(schema='goose_power_module_mount_fit_v1',
        own_native_parts=len(kit['parts']), own_native_mass_kg=kit['native_mass_kg'],
        quad_sources=quad_records, supplier_inputs=supplier, module_checks=module_checks,
        new_named_parts=len(new), checked_existing_named_solids=len(native) - len(new),
        considered_pairs_per_pose=len(pairs), requested_poses=len(cases), completed_poses=len(reports),
        cases=reports, actual_native_queries=queries, named_sampled_fit_pass=pass_fit,
        bare_modules_in_original_boxes=all(row['bare_module_in_allocated_box'] for row in module_checks),
        shared_frame_stacks=kit['shared_frame_stacks'], nominal_thread_contacts=kit['nominal_thread_contacts'],
        conservative_candidate_added_mass_kg=own_new_mass + shaft_increment,
        retained_default_buck_mass_allocations_kg=.065,
        candidate_mass_method='Retain all existing65g module/thermal/wiring allocations and old four M3 fastener upper envelopes; add only two carriers/PCB fixation and four2mm M3 shaft increments. No silent consumption of reserves.',
        default_assembly_unchanged=True, default_baseline_commit=baseline_commit, default_baseline=baseline,
        installed=False, electrical_release=False, thermal_release=False, full_assembly_pass=False,
        stage_three_four_complete=False, hardware_freeze=False,
        source_hashes={str(path.relative_to(ROOT)): sha(path) for path in paths},
        limitations=['Finite new-versus-current named pair screen is not continuous full joint sweep or whole assembly acceptance.',
            'Existing module reserves and actuator stator envelopes are identified as approximations; no connectors/wires/strain relief added.',
            'Mounting bores and bare module bounds are OEM-derived; PCB insulating washers, screws, machining tolerance/preload and enclosed cooling still require manufacturing release.',
            'Local carrier strength and existing neck-frame stiffness/bearing capacity are not certified by intersection tests.',
            'Nominal smooth-shaft/tapped-bore overlap is recorded explicitly; no actual helical thread or tolerance stack is certified.'])
    output = ROBOT / 'evidence/power_module_mount_fit.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print('POWER FIT COMPLETE', len(reports), '/', len(cases), 'pass', pass_fit,
          'added_mass_g', result['conservative_candidate_added_mass_kg'] * 1000, flush=True)
    return 0 if pass_fit and result['bare_modules_in_original_boxes'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
