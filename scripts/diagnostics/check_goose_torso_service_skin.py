"""Independent checks of the repaired skins; not a complete door mechanism.

The rigid sweep proves a bound only against the two named bare fixed skins.
It does not cover roof mounts, chassis, wiring, a hinge, latch, or other poses.
"""
from pathlib import Path
import hashlib
import json
import math
import platform
import sys
import build123d
import OCP
from build123d import Axis, import_brep

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT / 'scripts/cad'), str(ROOT / 'scripts/diagnostics')]
from goose_nurbs_skin import native_properties
from check_goose_grip_cassettes import bounded_common
from sai_agent.native_cad_query import native_solid_integrity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def certify_rotation_distance(moving, fixed, axis_yz, sign, angle_range, margin, smallest_interval, max_queries=256):
    """Adaptive rigid-displacement upper bound for an unchanged valid solid.

    Any point moves at most 2*R*sin(half_interval/2) from the midpoint pose;
    distance to a fixed closed set is 1-Lipschitz. A positive residual bounds
    the entire interval. Failed/too-small intervals remain rejected.
    """
    if (len(axis_yz) != 2 or len(angle_range) != 2
            or not all(math.isfinite(v) for v in [*axis_yz, *angle_range, margin, smallest_interval])
            or sign not in (-1, 1) or angle_range[1] <= angle_range[0]
            or angle_range[1]-angle_range[0] > 360 or margin < 0 or smallest_interval <= 0
            or not isinstance(max_queries, int) or max_queries <= 0):
        raise ValueError('Finite rigid sweep interval and positive query budget required')
    y0, z0 = axis_yz
    bounds = moving.bounding_box(optimal=False)
    radius = max(math.hypot(y-y0, z-z0)
                 for y in [bounds.min.Y, bounds.max.Y] for z in [bounds.min.Z, bounds.max.Z])
    axis = Axis((0, y0, z0), (1, 0, 0))
    pending = [tuple(angle_range)]
    intervals, rejected, samples = [], [], []
    while pending:
        lo, hi = pending.pop()
        if len(samples) >= max_queries:
            rejected.extend(dict(interval_deg=[a, b], reason='DISTANCE_QUERY_BUDGET')
                            for a, b in [(lo, hi), *pending])
            break
        mid = (lo+hi)/2
        pose = moving.rotate(axis, sign*mid)
        distance = float(pose.distance_to(fixed))
        if not math.isfinite(distance) or distance < 0:
            raise ValueError('Invalid native sweep distance')
        displacement_bound = 2*radius*math.sin(math.radians(hi-lo)/4)
        lower_bound = distance-displacement_bound
        row = dict(interval_deg=[lo, hi], midpoint_deg=mid,
                   midpoint_distance_mm=distance, displacement_upper_bound_mm=displacement_bound,
                   whole_interval_distance_lower_bound_mm=lower_bound)
        samples.append(row)
        #1um additional arithmetic/geometry guard; this is not a print tolerance.
        if lower_bound > margin+.001:
            intervals.append(row)
        elif hi-lo <= smallest_interval:
            rejected.append(row)
        else:
            pending.extend([(lo, mid), (mid, hi)])
    intervals.sort(key=lambda row:row['interval_deg'])
    return dict(axis_yz_mm=list(axis_yz), rotation_sign=sign, angle_range_deg=list(angle_range),
                conservative_rotation_radius_mm=radius, required_geometric_margin_mm=margin,
                native_distance_queries=len(samples), maximum_distance_queries=max_queries, certified_intervals=intervals,
                rejected_intervals=rejected, bare_skin_rotation_bound_pass=not rejected,
                scope='Unchanged source door rotating rigidly against this one bare fixed skin; no actual hinge')


def main():
    cfg_path = R/'configs/torso_service_skin.json'
    manifest_path = R/'cad/exports/torso_service_skin/manifest.json'
    cfg, manifest = [json.loads(p.read_text()) for p in [cfg_path, manifest_path]]
    for relative, digest in manifest['source_hashes'].items():
        if sha(ROOT/relative) != digest:
            raise ValueError(('Stale construction source', relative))
    shapes, sources = {}, [cfg_path, manifest_path]
    for part in manifest['parts']:
        for file in part['files'].values():
            path = R/file['path']
            if sha(path) != file['sha256']:
                raise ValueError(('Changed part', path))
        path = R/part['files']['brep']['path']
        sources.append(path)
        shape = import_brep(path)
        integrity = native_solid_integrity(shape)
        if not integrity['boolean_input_integrity_pass']:
            raise ValueError(('Invalid imported native part', part['name'], integrity))
        shapes[part['name']] = shape
    closed, rotation = [], []
    for label, side in [('right', -1), ('left', 1)]:
        door_name = 'wing_service_door_'+label
        door = shapes[door_name]
        volume = native_properties(door)[0]
        control = bounded_common(door, door, 15)
        if 'error' in control or not .99*volume < control['volume_mm3'] < 1.01*volume:
            raise ValueError(('Common positive control', control, volume))
        closed.append(dict(pair=[door_name, door_name], positive_control=True, common=control))
        for suffix in ['aft', 'fore']:
            fixed_name = 'torso_service_shell_'+label+'_'+suffix
            fixed = shapes[fixed_name]
            common = bounded_common(door, fixed, 15)
            distance = float(door.distance_to(fixed))
            passed = ('error' not in common and common['volume_mm3'] == 0
                      and distance >= cfg['minimum_closed_pair_distance_mm'])
            closed.append(dict(pair=[door_name, fixed_name], common=common,
                distance_mm=distance, minimum_required_distance_mm=cfg['minimum_closed_pair_distance_mm'],
                bare_skin_closed_pair_pass=passed))
            y, z = cfg['service_axis_right_yz_mm']
            axis = [-side*y, z]
            proof = certify_rotation_distance(door, fixed, axis,
                cfg['service_rotation_sign_right']*(-side), cfg['service_angle_range_deg'],
                cfg['sweep_minimum_margin_mm'], cfg['sweep_smallest_interval_deg'],
                max_queries=cfg['sweep_maximum_distance_queries_per_pair'])
            rotation.append(dict(pair=[door_name, fixed_name], **proof))
            print('SKIN CHECK', label, suffix, 'closed', passed, 'gap_mm', distance,
                  'bounded_sweep', proof['bare_skin_rotation_bound_pass'],
                  'queries', proof['native_distance_queries'], flush=True)
    # Preserve the original failure, checking all six original native inputs.
    original_paths = [R/('cad/source/body_bay_skins/wing_access_cover_'+label+'.brep')
                      for label in ['right', 'left']]
    original_paths += [R/('cad/source/torso_shell_mounts/torso_mounted_shell_'+label+'_'+suffix+'.brep')
                       for label in ['right', 'left'] for suffix in ['aft', 'fore']]
    original_checks = [dict(path=str(p.relative_to(ROOT)), sha256=sha(p),
                            **native_solid_integrity(import_brep(p))) for p in original_paths]
    closed_pass = all(row['bare_skin_closed_pair_pass'] for row in closed if not row.get('positive_control'))
    rotation_pass = all(row['bare_skin_rotation_bound_pass'] for row in rotation)
    report = dict(schema='goose_torso_service_skin_fit_v1',
        environment=dict(python=platform.python_version(), build123d=build123d.__version__, ocp=OCP.__version__),
        original_native_integrity=original_checks, repaired_native_part_count=len(shapes),
        repaired_native_input_integrity_pass=True, closed_pairs=closed, rotation_bounds=rotation,
        bare_skin_closed_fit_pass=closed_pass, bare_skin_rotation_distance_bound_pass=rotation_pass,
        manual_door_assembly_pass=False, full_assembly_pass=False, manufacturing_release=False,
        actual_hinge_and_latch_included=False, whole_mass_parameters_updated=False,
        physical_parameters_modified=False, runtime_collision_proxy_modified=False,
        integrations=0, optimizer_steps=0,
        limitations=manifest['limitations']+[
            'Rotation bounds cover only the bare door and same-side bare aft/fore skins; not the installed robot.',
            'This geometric axis candidate is not a constructed hinge or validated joint.',
            'Fixed left/right midsplit seam fit and the six-piece assembly have not been released.'],
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources+original_paths+[
            Path(__file__), ROOT/'src/sai_agent/native_cad_query.py',
            ROOT/'scripts/diagnostics/check_goose_grip_cassettes.py']})
    (R/'evidence/torso_service_skin_fit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(bare_skin_closed_fit_pass=closed_pass,
                         bare_skin_rotation_distance_bound_pass=rotation_pass,
                         manual_door_assembly_pass=False)), flush=True)
    if not closed_pass or not rotation_pass:
        raise SystemExit('Repaired bare skin gate failed')


if __name__ == '__main__':
    main()
