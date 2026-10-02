"""Neutral-pose screening of declared complete drive and internal box envelopes.

This checks exclusive-space placement hypotheses, not physical material collision.
Frame/reserve boxes are mass-distribution proxies; armor is not a solid container.
Every overlap has a checked interior witness, and every separation a lower bound.
Uncertified cases remain unknown. No CAD, physics model, or specification is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[2]
ROBOT = ROOT / 'robots/gorilla_v0_1'
TOL = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_vector(value, size, name):
    value = np.asarray(value, dtype=float)
    if value.shape != (size,) or not np.isfinite(value).all():
        raise ValueError(f'Invalid finite {name}')
    return value


def cylinder(name, center, axis, diameter, length, **metadata):
    center = finite_vector(center, 3, 'center')
    axis = finite_vector(axis, 3, 'axis')
    norm = np.linalg.norm(axis)
    if norm <= 0 or min(diameter, length) <= 0:
        raise ValueError('Cylinder dimensions and axis must be positive')
    axis = axis / norm
    return dict(name=name, shape='cylinder', center=center, axis=axis,
                radius=diameter / 2, half_length=length / 2, **metadata)


def box(name, center, size, **metadata):
    size = finite_vector(size, 3, 'box dimensions')
    if np.any(size <= 0):
        raise ValueError('Box dimensions must be positive')
    return dict(name=name, shape='box', center=finite_vector(center, 3, 'center'),
                half_size=size / 2, **metadata)


def extent(shape, direction):
    """Exact support-function radius in a supplied unit direction."""
    if shape['shape'] == 'box':
        return float(np.abs(direction) @ shape['half_size'])
    axial = float(direction @ shape['axis'])
    return shape['half_length'] * abs(axial) + shape['radius'] * np.sqrt(max(0., 1 - axial**2))


def clearance(shape, point):
    """Radius of a ball centered at point inside the solid envelope; negative outside."""
    delta = np.asarray(point) - shape['center']
    if shape['shape'] == 'box':
        return float(np.min(shape['half_size'] - np.abs(delta)))
    axial = float(delta @ shape['axis'])
    radial = np.linalg.norm(delta - axial * shape['axis'])
    return float(min(shape['radius'] - radial, shape['half_length'] - abs(axial)))


def project(shape, point):
    """Euclidean projection onto an axis-aligned box or arbitrarily oriented cylinder."""
    delta = np.asarray(point) - shape['center']
    if shape['shape'] == 'box':
        return shape['center'] + np.clip(delta, -shape['half_size'], shape['half_size'])
    axial = float(delta @ shape['axis'])
    radial = delta - axial * shape['axis']
    norm = np.linalg.norm(radial)
    if norm > shape['radius']:
        radial *= shape['radius'] / norm
    return shape['center'] + radial + np.clip(axial, -shape['half_length'], shape['half_length']) * shape['axis']


def aabb(shape):
    half = np.array([extent(shape, d) for d in np.eye(3)])
    return shape['center'] - half, shape['center'] + half


def inscribed_radius(shape):
    return float(np.min(shape['half_size']) if shape['shape'] == 'box'
                 else min(shape['radius'], shape['half_length']))


def witness_record(a, b, point, method):
    if not np.isfinite(point).all():
        return None
    radius = min(clearance(a, point), clearance(b, point))
    if radius <= TOL:
        return None
    return {'classification': 'declared_envelope_overlap_certified', 'method': method,
            'witness_world_m': np.asarray(point).tolist(),
            'common_interior_ball_radius_m': radius,
            'common_volume_lower_bound_m3': float(4 * np.pi * radius**3 / 3),
            'distance_lower_bound_m': 0., 'distance_upper_bound_m': 0.}


def pair_geometry(a, b, service_clearance):
    """Certify geometry, never infer overlap just from overlapping AABBs."""
    lo_a, hi_a = aabb(a)
    lo_b, hi_b = aabb(b)
    aabb_lower = float(np.linalg.norm(np.maximum(np.maximum(lo_b-hi_a, lo_a-hi_b), 0)))
    if a['shape'] == b['shape'] == 'box':
        low, high = np.maximum(lo_a, lo_b), np.minimum(hi_a, hi_b)
        if np.all(high - low > 2*TOL):
            result = witness_record(a, b, (low+high)/2, 'analytic_axis_aligned_box_intersection')
            result['exact_envelope_intersection_volume_m3'] = float(np.prod(high-low))
            return result
        return {'classification': 'separation_certified' if aabb_lower > TOL else 'touching_or_unknown',
                'method': 'analytic_axis_aligned_box_distance',
                'distance_lower_bound_m': aabb_lower, 'distance_upper_bound_m': aabb_lower}
    delta = b['center'] - a['center']
    distance = np.linalg.norm(delta)
    ra, rb = inscribed_radius(a), inscribed_radius(b)
    if distance < ra+rb-2*TOL:
        if distance+ra <= rb:
            point = a['center']
        elif distance+rb <= ra:
            point = b['center']
        else:
            radius = (ra+rb-distance)/2
            point = a['center'] + delta/distance*(ra-radius)
        result = witness_record(a, b, point, 'inscribed_spheres_strict_interior_witness')
        if result:
            return result
    # Parallel circular cylinders are Cartesian products of disks and intervals.
    if a['shape'] == b['shape'] == 'cylinder' and abs(a['axis'] @ b['axis']) > 1-1e-10:
        axis = a['axis']
        axial = float(delta @ axis)
        radial_vector = delta - axial*axis
        radial = np.linalg.norm(radial_vector)
        low = max(-a['half_length'], axial-b['half_length'])
        high = min(a['half_length'], axial+b['half_length'])
        radial_gap = radial-a['radius']-b['radius']
        axial_gap = low-high
        exact_distance = float(np.hypot(max(0., axial_gap), max(0., radial_gap)))
        if high-low > 2*TOL and radial_gap < -2*TOL:
            if radial+a['radius'] <= b['radius']:
                radial_point = np.zeros(3)
            elif radial+b['radius'] <= a['radius']:
                radial_point = radial_vector
            else:
                radius = (a['radius']+b['radius']-radial)/2
                radial_point = radial_vector/radial*(a['radius']-radius)
            point = a['center'] + radial_point + (low+high)/2*axis
            result = witness_record(a, b, point, 'analytic_parallel_cylinder_intersection')
            if result:
                result['axial_interval_overlap_m'] = high-low
                result['radial_disk_overlap_parameter_m'] = -radial_gap
                return result
        return {'classification': 'separation_certified' if exact_distance > TOL else 'touching_or_unknown',
                'method': 'analytic_parallel_cylinder_distance',
                'distance_lower_bound_m': exact_distance, 'distance_upper_bound_m': exact_distance}
    pa, pb = project(a, b['center']), project(b, a['center'])
    if aabb_lower >= service_clearance:
        return {'classification': 'separation_certified', 'method': 'outer_aabb_distance_lower_bound',
                'distance_lower_bound_m': aabb_lower, 'distance_upper_bound_m': float(np.linalg.norm(pb-pa))}
    # Alternating exact projections produce feasible upper bounds. A support plane
    # in their difference direction produces an independently checkable lower bound.
    lower, upper = aabb_lower, float(np.linalg.norm(pb-pa))
    direction_best = None
    for _ in range(160):
        pa = project(a, pb)
        pb = project(b, pa)
        gap_vector = pb-pa
        upper = float(np.linalg.norm(gap_vector))
        if upper > TOL:
            direction = gap_vector/upper
            gap = float(direction @ delta-extent(a, direction)-extent(b, direction))
            if gap > lower:
                lower, direction_best = gap, direction.tolist()
        if lower > TOL and upper-lower <= 1e-7:
            break
    if lower > TOL:
        return {'classification': 'separation_certified', 'method': 'exact_support_plane_distance_bounds',
                'distance_lower_bound_m': lower, 'distance_upper_bound_m': upper,
                'separating_direction_world': direction_best}
    # Positive validated margins certify strict overlap even if the numerical
    # optimizer does not claim success. A failed witness search never clears a pair.
    def constraints(value):
        p, t = value[:3], value[3]
        return np.array([clearance(a, p)-t, clearance(b, p)-t])
    initial = np.r_[(pa+pb)/2, min(clearance(a, (pa+pb)/2), clearance(b, (pa+pb)/2))]
    result = minimize(lambda x: -x[3], initial, method='SLSQP',
                      constraints=[{'type': 'ineq', 'fun': constraints}],
                      bounds=[(None,None)]*3+[(-10., min(ra,rb))],
                      options={'maxiter': 120, 'ftol': 1e-12})
    candidate = witness_record(a, b, result.x[:3], 'validated_convex_interior_ball_witness')
    if candidate:
        candidate['optimizer_success'] = bool(result.success)
        return candidate
    return {'classification': 'touching_or_unknown', 'method': 'no_strict_certificate',
            'distance_lower_bound_m': lower, 'distance_upper_bound_m': upper,
            'optimizer_success': bool(result.success)}


def serializable(shape):
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k,v in shape.items()}


def load_shapes(spec, contract):
    if contract['joints'] != spec['joints'] or contract['drive_classes'] != spec['drive_classes']:
        raise ValueError('SI contract and specification joint/drive definitions differ')
    if any(j['qpos_neutral_rad'] != 0 for j in spec['joints']):
        raise ValueError('Neutral parent frames are only supported at declared zero angles')
    shapes = []
    for j in spec['joints']:
        drive = spec['drive_classes'][j['drive_class']]
        x,y,length = drive['complete_module_envelope_m']
        if not np.isclose(x, y, rtol=0, atol=1e-12):
            raise ValueError('Elliptical drive envelope cannot be silently treated as circular')
        shape = cylinder(j['name'], j['position_world_m'], j['axis_parent'], x, length,
                         kind='complete_drive_module', body=j['child'], parent=j['parent'],
                         drive_class=j['drive_class'], envelope_source='spec.complete_module_envelope_m',
                         hardware_sku_status=drive['drive_status'])
        shape['axial_endpoints_world_m'] = [shape['center']-length/2*shape['axis'],
                                           shape['center']+length/2*shape['axis']]
        shape['axial_endpoints_world_m'] = [p.tolist() for p in shape['axial_endpoints_world_m']]
        shapes.append(shape)
    for c in spec['mass_components']:
        candidates = [entry for entry in contract['bodies'][c['body']]['components']
                      if entry['name'] == c['name'] and entry['shape'] == 'box']
        if len(candidates) != 1 or not all(np.array_equal(candidates[0][key], c[source])
                                         for key,source in (('position_world_m','position_world_m'),
                                                            ('size_m','box_size_m'),('mass_kg','mass_kg'))):
            raise ValueError(f"SI non-drive allocation differs: {c['name']}")
        shapes.append(box(c['name'], c['position_world_m'], c['box_size_m'],
                          kind='explicit_nondrive_allocation_box', body=c['body'],
                          occupancy_status='estimated allocation proxy, not proven solid material',
                          envelope_source='spec.mass_components.box_size_m'))
    return shapes


def make_report(spec_path, si_path, scene_path, model_path, service_clearance):
    input_paths = {'spec': spec_path, 'si_contract': si_path, 'scene': scene_path, 'model_xml': model_path}
    initial = {name:sha(path) for name,path in input_paths.items()}
    spec, contract = json.loads(spec_path.read_text()), json.loads(si_path.read_text())
    for key, identity in (('spec_sha256','spec'), ('scene_sha256','scene'), ('model_sha256','model_xml')):
        if contract[key] != initial[identity]:
            raise ValueError(f'Frozen source identity mismatch: {key}')
    if spec['checkpoint_id'] != contract['checkpoint_id']:
        raise ValueError('Checkpoint identity differs')
    checked_assets = {}
    for name, identity in contract['asset_manifest'].items():
        actual = sha(si_path.parent/name)
        if actual != identity:
            raise ValueError(f'Asset identity mismatch: {name}')
        checked_assets[name] = actual
    checked_generators = {}
    for name, identity in contract['generator_sha256'].items():
        actual = sha(ROOT/name)
        if actual != identity:
            raise ValueError(f'Generator identity mismatch: {name}')
        checked_generators[name] = actual
    shapes = load_shapes(spec, contract)
    pairs = []
    for a,b in itertools.combinations(shapes,2):
        result = pair_geometry(a,b,service_clearance)
        drive_count = sum(s['kind']=='complete_drive_module' for s in (a,b))
        result.update(a=a['name'], b=b['name'], pair_kind=['box_box','drive_box','drive_drive'][drive_count],
                      same_body=a['body']==b['body'], same_anchor=bool(np.linalg.norm(a['center']-b['center'])<=TOL))
        if drive_count == 2:
            result['axis_angle_deg'] = float(np.degrees(np.arccos(np.clip(abs(a['axis']@b['axis']),0,1))))
            result['parent_child_axes'] = a['body']==b['parent'] or b['body']==a['parent']
            if abs(a['axis']@b['axis']) > 1-1e-10:
                delta = b['center']-a['center']
                axial = float(delta@a['axis'])
                radial = np.linalg.norm(delta-axial*a['axis'])
                result['parallel_axis_offset_m'] = float(radial)
                result['axial_center_separation_m'] = abs(axial)
                if radial <= TOL:
                    result['coaxial_stack_required_center_separation_m'] = a['half_length']+b['half_length']+service_clearance
                    result['coaxial_stack_axial_gap_m'] = abs(axial)-a['half_length']-b['half_length']
        lower,upper = result['distance_lower_bound_m'], result['distance_upper_bound_m']
        result['maintenance_clearance_status'] = (
            'declared_envelopes_overlap' if result['classification']=='declared_envelope_overlap_certified'
            else 'at_screening_gap_within_tolerance' if lower >= service_clearance-TOL and upper <= service_clearance+TOL
            else 'at_least_screening_gap_certified' if lower >= service_clearance+TOL
            else 'below_screening_gap_certified' if upper < service_clearance-TOL
            else 'unknown_at_screening_gap')
        pairs.append(result)
    overlap = [p for p in pairs if p['classification']=='declared_envelope_overlap_certified']
    unknown = [p for p in pairs if p['classification']=='touching_or_unknown']
    drive_overlaps = [p for p in overlap if p['pair_kind']=='drive_drive']
    # These preserve the true interpretation of frame/reserve mass proxies.
    coallocations = [p for p in overlap if p['pair_kind']!='drive_drive']
    risks = sorted(drive_overlaps, key=lambda p:p['common_interior_ball_radius_m'], reverse=True)[:12]
    nearest = {}
    for shape in shapes:
        if shape['kind'] != 'complete_drive_module':
            continue
        neighbors = [p for p in pairs if shape['name'] in (p['a'],p['b'])]
        neighbors.sort(key=lambda p:p['distance_upper_bound_m'])
        nearest[shape['name']] = neighbors[:3]
    report = {
        'schema':'gorilla_internal_layout_screen_v1','robot_id':contract['robot_id'],
        'checkpoint_id':spec['checkpoint_id'],'source_hashes':initial,
        'source_files':{name:str(path.resolve()) for name,path in input_paths.items()},
        'generator_sha256':sha(Path(__file__)), 'asset_manifest':checked_assets,
        'source_generator_hashes':checked_generators,
        'scope':'Frozen neutral pose; unchanged full nominal module envelopes; no hardware resizing or collision-model edit',
        'methods':{'overlap':'analytic product intersection or independently checked strict common interior ball',
                   'separation':'analytic distance or exact support-plane/AABB lower bound; feasible-point upper bound',
                   'tolerance_m':TOL,'unresolved':'touching/uncertified pairs stay RED OPEN'},
        'screening_assumptions':{'complete_drive_envelope':'circular cylinder centered at each neutral joint anchor, length along axis_parent',
            'box_orientation':'world-axis aligned allocation proxy, as in frozen SI mass components',
            'maintenance_gap_m':service_clearance,'maintenance_gap_basis':'screening assumption only, not a tool/connector/thermal clearance specification'},
        'counts':{'drives':sum(s['kind']=='complete_drive_module' for s in shapes),
                  'nondrive_boxes':sum(s['kind']!='complete_drive_module' for s in shapes),
                  'pairs':len(pairs),'declared_drive_envelope_overlap_pairs':len(drive_overlaps),
                  'same_anchor_drive_overlap_pairs':sum(p['same_anchor'] for p in drive_overlaps),
                  'box_coallocation_overlap_pairs':len(coallocations),'uncertified_or_touching_pairs':len(unknown)},
        'largest_drive_overlap_risks':risks,'nearest_drive_neighbors':nearest,
        'envelopes':[serializable(s) for s in shapes],'pair_results':pairs,
        'gates':{
            'drive_centered_envelope_placement':'RED FAILED for declared exclusive envelopes' if drive_overlaps else 'RED OPEN until actual OEM/custom geometry is verified',
            'frame_and_reserve_coallocation':'RED OPEN; allocation boxes are not solid collision geometry',
            'armor_internal_containment':'NOT CHECKED; thin armor is not a solid cavity and must not be filled/convexified',
            'axial_installation_and_service':'RED OPEN; envelope length checked, extraction/tool/cable/fastener paths not defined',
            'joint_sweep':'NOT CHECKED; this is the neutral pose only',
            'mass_allocation_and_rotor_reflection':'RED OPEN; no inference from this space screen'},
        'closure_conditions':[
            'Replace coincident independent complete cylinders with an explicit OEM/custom gimbal assembly; preserve real hardware dimensions.',
            'Provide separate parent/child housings, bearings, motor/gear/brake/encoder and connector positions; demonstrate non-overlapping actual material.',
            'Resolve box allocation conflicts using actual hollow frames, brackets and component-specific envelopes; do not erase mass or suppress collisions.',
            'Verify actual inner armor surfaces, assembly entry and removal path, tool approach, cable bend radius and thermal clearance.',
            'Repeat the same-source screen across core task poses and continuous joint sweeps before stable handoff.'],
        'source_mass_kg':contract['total_robot_mass_kg'],'physical_material_collision_proven':False,
        'internal_packaging_pass':False,'manufacturing_release':False,'physical_hard_freeze':False,
    }
    final = {name:sha(path) for name,path in input_paths.items()}
    if final != initial:
        raise ValueError('Source changed during screening; refusing mixed-version evidence')
    for name,identity in checked_assets.items():
        if sha(si_path.parent/name) != identity:
            raise ValueError('Asset changed during screening')
    for name,identity in checked_generators.items():
        if sha(ROOT/name) != identity:
            raise ValueError('Source generator changed during screening')
    report['source_unchanged_during_screen']=True
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,default=ROBOT/'configs/layout_b_spec.json')
    parser.add_argument('--si',type=Path,default=ROBOT/'models/full/robot.json')
    parser.add_argument('--scene',type=Path,default=ROBOT/'cad/source/layout_b_scene.json')
    parser.add_argument('--model',type=Path,default=ROBOT/'models/full/robot.xml')
    parser.add_argument('--out',type=Path,default=ROBOT/'evidence/layout_b_internal_screen.json')
    parser.add_argument('--maintenance-clearance-mm',type=float,default=20.)
    args=parser.parse_args()
    if not np.isfinite(args.maintenance_clearance_mm) or args.maintenance_clearance_mm <= 0:
        raise ValueError('Maintenance screening clearance must be positive')
    report=make_report(args.spec,args.si,args.scene,args.model,args.maintenance_clearance_mm/1000)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'out':str(args.out),'counts':report['counts'],
                      'internal_packaging_pass':False},ensure_ascii=False))


if __name__=='__main__':
    main()
