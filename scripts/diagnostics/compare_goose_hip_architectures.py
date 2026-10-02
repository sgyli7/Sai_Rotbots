"""Bounded morphology comparison before training; no manufacturing release.

Screens native stator envelopes against the original (optionally wider) skin,
other motors and explicitly provisional electronics boxes. Static estimates
reuse the existing mass budget, with extra full aluminium strips for longer
legs. Newly arranged mounts/frame/cables have NOT been designed here.
"""
from pathlib import Path
import copy, hashlib, itertools, json, sys
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[2]; R = ROOT/'robots/Goose_V0.1'
sys.path[:0] = [str(ROOT/'scripts/diagnostics'), str(ROOT/'scripts/cad')]
from check_goose_hip_carrier_parameters import configure_candidate
from check_goose_hip_roll_carriers import boolean_regression, ROLL_ROTATION
from build_goose_cad import box, cylinder, transform
from sai_agent.native_cad import common_solid_volume_mm3 as overlap


def prepare(old, original_skins, label, hip_height=None, yaw_mid=False, width=1., repack=False):
    data = copy.deepcopy(old); s = configure_candidate(data)
    before = {n: p.copy() for n, p in s.pivots.items()}
    lift = old['rigid_coordinate_lift_m']
    if yaw_mid:
        for side, sign in [('right', -1), ('left', 1)]:
            y = sign*.065
            points = {'hip_yaw': [-.018, y, hip_height+.068],
                'hip_roll': [-.051, y, hip_height+.013],
                'hip_pitch': [.015, y, hip_height],
                'knee_pitch': [-.050, y, .145 if hip_height == .252 else .152],
                'ankle_pitch': [.001, y, .062], 'ankle_roll': [.061, y, .036]}
            for suffix, pos in points.items():
                s.pivots[side+'_'+suffix] = np.array(pos)+[0, 0, lift]
            delta = s.pivots[side+'_ankle_roll']-before[side+'_ankle_roll']
            s.contact_hulls[side] = ConvexHull(np.array(old['contact_hulls'][side])+delta[:2])
    # Each motor's stator is attached to its parent but anchored at its own axis.
    # Fork pieces are linearly remapped along their two old joint centres.
    for item in s.items:
        n = item['name']; owner = item['body']; p = np.array(item['center_m'])
        anchor = next((j for j in s.names if n in (j, j+'_mount_reserve')), None)
        if anchor:
            p += s.pivots[anchor]-before[anchor]
        elif any(n.startswith(side+'_'+seg+'_') for side in ['right', 'left'] for seg in ['thigh', 'shin']):
            side, segment = n.split('_')[:2]
            a, b = (side+'_hip_pitch', side+'_knee_pitch') if segment == 'thigh' else (side+'_knee_pitch', side+'_ankle_pitch')
            direction = before[b]-before[a]
            t = np.clip(np.dot(p-before[a], direction)/np.dot(direction, direction), 0, 1)
            p += (1-t)*(s.pivots[a]-before[a])+t*(s.pivots[b]-before[b])
        elif owner != 'torso':
            p += s.pivots[owner]-before[owner]
        item['center_m'] = p.tolist()
    # Restore the uncut original skin. Width affects its actual native volume.
    names = {p['name'] for p in original_skins if not p['name'].startswith('goose_head')}
    s.items = [i for i in s.items if i['name'] not in names]
    for p in original_skins:
        if p['name'] not in names: continue
        center = np.array(p['center_of_mass_world_m']); center[1] *= width; center[2] += lift
        s.items.append(dict(name=p['name'], body='torso', mass_kg=p['full_density_mass_kg']*width,
            center_m=center.tolist(), relative_uncertainty=.1,
            basis='original uncut native skin; affine Y enlargement for architecture screening only'))
    added_strip_mass = 0.
    for side in ['right', 'left']:
        for a, b in [('hip_pitch', 'knee_pitch'), ('knee_pitch', 'ankle_pitch')]:
            a, b = side+'_'+a, side+'_'+b
            extra = max(0., np.linalg.norm(s.pivots[b]-s.pivots[a])-np.linalg.norm(before[b]-before[a]))
            mass = extra*2*.0055*.024*2700
            added_strip_mass += mass
            if mass:
                s.items.append(dict(name=a+'_lengthening_bound', body=a, mass_kg=mass,
                    center_m=((s.pivots[a]+s.pivots[b])/2).tolist(), relative_uncertainty=.3,
                    basis='two full 5.5x24mm aluminium strips for incremental length; not new mount design'))
    packing = {
        'battery_service': ([.120, .065, .050], [-.055, 0, .358]),
        'compute_stack': ([.080, .048, .032], [.055, 0, .285]),
        'logic_buck': ([.049, .029, .022], [.085, .040, .318]),
        'servo_buck': ([.049, .029, .022], [.085, -.040, .318]),
        'interfaces_audio': ([.044, .052, .032], [-.030, 0, .240]),
        'dual_can_interface_allocation': ([.070, .040, .016], [-.040, 0, .323]),
    }
    if repack:
        packing['compute_stack'] = ([.080, .048, .032], [-.115, 0, .310])
        packing['interfaces_audio'] = ([.044, .052, .032], [-.105, 0, .275])
    electronics = {}
    by_name = {i['name']: i for i in s.items}
    for name, (size, pos) in packing.items():
        if yaw_mid: by_name[name]['center_m'] = (np.array(pos)+[0, 0, lift]).tolist()
        electronics[name] = box(np.array(size)*1000, np.array(by_name[name]['center_m'])*1000)
    s.contact_center_y_m = {side: float(s.pivots[side+'_ankle_roll'][1]) for side in ['right', 'left']}
    return s, electronics, added_strip_mass


def static_screen(s, contract):
    cases = []
    for drop in [0, 40, 60, 80]:
        q, p, rot = s.pose(drop); cases.append(('crouch_'+str(drop), q, p, rot, ['right', 'left']))
    q, p, rot = s.pose(60, neck=True); cases.append(('low_reach', q, p, rot, ['right', 'left']))
    for side in ['right', 'left']:
        q, p, rot = s.pose(); q, p, rot = s.bank(side, q, p)
        cases.append((side+'_single_support', q, p, rot, [side]))
    rows = []
    for scale in [-1, 0, 1]:
        model, _ = s.model(scale)
        for name, q, p, rot, supports in cases:
            for drag in [-2, 0, 2]:
                value = s.evaluate(name, q, p, rot, supports, scale, drag, model)
                value['joint_limit_violations'] = [j['name'] for j in contract['joints'] if not j['range_rad'][0] <= q[j['name']] <= j['range_rad'][1]]
                rows.append(value)
    summary = []
    for j in contract['joints']:
        worst = max(rows, key=lambda row: abs(row['joint_torque_nm'][j['name']]))
        value = abs(worst['joint_torque_nm'][j['name']])
        summary.append(dict(joint=j['name'], max_static_nm=value,
            continuous_limit_nm=j['continuous_design_limit_nm'], margin_nm=j['continuous_design_limit_nm']-value,
            case=worst['name'], mass_variant=worst['mass_variant'], drag_n=worst['drag_x_n']))
    return dict(cases=len(rows), feasible=sum(r['static_contact_feasible'] and not r['joint_limit_violations'] for r in rows),
        all_static_torques_pass=all(j['margin_nm'] >= 0 for j in summary),
        nominal_com_m=next(r['com_m'] for r in rows if r['name']=='crouch_0' and r['mass_variant']==0 and r['drag_x_n']==0),
        low_reach_grip_m=next(r['grip_m'] for r in rows if r['name']=='low_reach' and r['mass_variant']==0 and r['drag_x_n']==0),
        joint_summary=summary, results=rows)


def motor_shapes(s):
    shapes, owners = {}, {}
    for side in ['right', 'left']:
        for suffix in ['hip_yaw', 'hip_roll', 'hip_pitch']:
            n = side+'_'+suffix
            if suffix == 'hip_yaw':
                shape = cylinder(26.5, 39.2, [0, 0, -.5], 'z')
            else:
                shape = cylinder(27.5, 53.5, [0, -1.5, 0], 'y')
                rot = ROLL_ROTATION if suffix == 'hip_roll' else np.eye(3) if side == 'left' else np.diag([1., -1., -1.])
                shape = transform(shape, rot)
            shapes[n] = transform(shape, np.eye(3), s.pivots[n]*1000)
            owners[n] = s.parents[n]
    # Fixed neck yaw is included: relocated electronics must not erase it.
    n = 'neck_yaw'; shapes[n] = cylinder(26.5, 39.2, s.pivots[n]*1000-[0, 0, .5], 'z'); owners[n] = 'torso'
    return shapes, owners


def packing_screen(s, skins, electronics):
    source, owners = motor_shapes(s)
    fixed_hits = []
    for a, b in itertools.combinations(electronics, 2):
        volume = overlap(electronics[a], electronics[b])
        if volume > .01: fixed_hits.append(dict(a=a, b=b, mm3=volume, kind='provisional_electronics_boxes'))
    # A convex outer hull is only a NECESSARY fit condition. Passing it does
    # not prove fit in the true concave interior or leave connector clearances.
    outer = ConvexHull(np.vstack(list(skins.values())))
    outer_fit = []
    for n, shape in electronics.items():
        corners = np.array([tuple(v.center()) for v in shape.vertices()])
        margin = -np.max(corners@outer.equations[:, :3].T+outer.equations[:, 3])
        outer_fit.append(dict(name=n, necessary_convex_outer_margin_mm=float(margin), pass_necessary_bound=bool(margin >= .2)))
    cases = [('zero', {})]
    for side in ['right', 'left']:
        for yaw, roll in itertools.product([-.6, 0., .6], [-.5, 0., .5]):
            if yaw == roll == 0: continue
            cases.append((side+'_'+str((yaw, roll)), {side+'_hip_yaw': yaw, side+'_hip_roll': roll}))
    for yaw, roll in itertools.product([-.6, .6], [-.5, .5]):
        cases.append(('bilateral_same_'+str((yaw, roll)), {side+'_'+axis:value for side in ['right', 'left'] for axis,value in [('hip_yaw', yaw), ('hip_roll', roll)]}))
        cases.append(('bilateral_opposed_'+str((yaw, roll)), {side+'_'+axis:value*sign for side,sign in [('right', -1), ('left', 1)] for axis,value in [('hip_yaw', yaw), ('hip_roll', roll)]}))
    rows = []; lower = np.full(3, np.inf); upper = -lower
    for name, q in cases:
        poses, _ = s.fk(q); installed = {}; cylinders = {}
        for n, shape in source.items():
            p, rot = poses[owners[n]]
            installed[n] = transform(shape, rot, (p-rot@s.pivots[owners[n]])*1000)
            axis = rot@s.axes[n]
            center = s.point(poses, owners[n], s.pivots[n])*1000-axis*(.5 if n.endswith('yaw') else 1.5)
            cylinders[n] = (center, axis, 26.5 if n.endswith('yaw') else 27.5, 19.6 if n.endswith('yaw') else 26.75)
            if n != 'neck_yaw':
                bb = installed[n].bounding_box(); lower = np.minimum(lower, list(bb.min)); upper = np.maximum(upper, list(bb.max))
        hits = copy.deepcopy(fixed_hits)
        for a, b in itertools.combinations(installed, 2):
            volume = overlap(installed[a], installed[b])
            if volume > .01: hits.append(dict(a=a, b=b, mm3=volume, kind='motor_envelopes'))
        for a, shape in installed.items():
            for b, fixed in electronics.items():
                volume = overlap(shape, fixed)
                if volume > .01: hits.append(dict(a=a, b=b, mm3=volume, kind='provisional_electronics_box'))
            center, axis, radius, half = cylinders[a]
            for b, points in skins.items():
                bb = shape.bounding_box()
                nearby = points[np.all((points >= np.array(tuple(bb.min))) & (points <= np.array(tuple(bb.max))), axis=1)]
                delta = nearby-center; axial = delta@axis
                radial2 = np.einsum('ij,ij->i', delta, delta)-axial**2
                # Positive interior samples prove overlap in the surface
                # approximation; zero samples NEVER prove clearance.
                count = int(np.sum((np.abs(axial) < half-.2) & (radial2 < (radius-.2)**2)))
                if count: hits.append(dict(a=a, b=b, interior_surface_samples=count, kind='sampled_skin'))
        rows.append(dict(name=name, q_rad=q, collisions=hits, pass_screen=not hits))
    return dict(sampled_poses=len(rows), passed_poses=sum(r['pass_screen'] for r in rows),
        necessary_whole_packing_pass=bool(all(r['pass_screen'] for r in rows) and all(r['pass_necessary_bound'] for r in outer_fit)),
        necessary_electronics_outer_hull=outer_fit,
        hip_motor_swept_bounds_mm=dict(min=lower.tolist(), max=upper.tolist()),
        skin_hit_cases=sum(any(h['kind']=='sampled_skin' for h in r['collisions']) for r in rows),
        motor_hit_cases=sum(any(h['kind']=='motor_envelopes' for h in r['collisions']) for r in rows),
        electronics_hit_cases=sum(any(h['kind']=='provisional_electronics_box' for h in r['collisions']) for r in rows), cases=rows)


def main():
    paths = [R/'evidence/hip_clearance_wide_component_parameters.json',
        R/'cad/exports/manufacturing_skins/manifest.json', R/'configs/stage_two_contract.json']
    old, skins_manifest, contract = [json.loads(p.read_text()) for p in paths]
    skins = {}
    for p in skins_manifest['parts']:
        if p['name'].startswith('goose_head'): continue
        stl = R/p['files']['stl']['path']; paths.append(stl)
        assert hashlib.sha256(stl.read_bytes()).hexdigest() == p['files']['stl']['sha256']
        mesh = trimesh.load(stl, force='mesh', process=True)
        points = np.vstack([mesh.vertices, mesh.triangles_center]); points[:, 2] += old['rigid_coordinate_lift_m']*1000
        skins[p['name']] = points
    regression = boolean_regression(); results = []
    options = [('existing_uncut', None, False, 1., False), ('mid_hip_centered_yaw', .252, True, 1., False),
        ('high_hip_centered_yaw', .267, True, 1., False), ('high_hip_wider_skin', .267, True, 1.15, False),
        ('high_hip_repacked', .267, True, 1.15, True)]
    for label, height, centered, width, repack in options:
        s, electronics, extra = prepare(old, skins_manifest['parts'], label, height, centered, width, repack)
        static = static_screen(s, contract)
        print(label, 'static', static['feasible'], '/', static['cases'], 'torques', static['all_static_torques_pass'], flush=True)
        packing = packing_screen(s, {n:points*np.array([1, width, 1]) for n,points in skins.items()}, electronics)
        value = dict(name=label, skin_y_scale=width, nominal_conditional_mass_estimate_kg=sum(i['mass_kg'] for i in s.items if i['name']!='specified_payload_50g'),
            incremental_leg_strip_mass_bound_kg=extra, joint_pivots_m={n:p.tolist() for n,p in s.pivots.items()},
            electronics_box_centres_m={n:np.array(tuple(shape.center())).tolist() for n,shape in electronics.items()},
            static=static, packing=packing, selected=False, manufacturing_pass=False)
        # Electronics coordinates above are native millimetres; label precisely.
        value['electronics_box_centres_mm'] = value.pop('electronics_box_centres_m')
        results.append(value)
        print(label, 'packing', packing['passed_poses'], '/', packing['sampled_poses'], 'skin/motor/electronics failures', packing['skin_hit_cases'], packing['motor_hit_cases'], packing['electronics_hit_cases'], flush=True)
    paths.extend([ROOT/'scripts/diagnostics/check_goose_hip_carrier_parameters.py',
        ROOT/'scripts/diagnostics/check_goose_hip_roll_carriers.py', ROOT/'scripts/models/build_goose_stage_two.py',
        ROOT/'scripts/models/build_goose_stage_one.py', ROOT/'src/sai_agent/native_cad.py',
        ROOT/'scripts/cad/build_goose_cad.py', R/'hardware/stage_three_actuator_mounts.json'])
    report = dict(schema='goose_hip_architecture_comparison_v1', analytical_boolean_regression=regression,
        candidates=results, chosen_candidate=None, training_release=False, hardware_freeze=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__), ROOT/'scripts/diagnostics/screen_goose_system_loads.py']},
        limitations=['Bounded comparison, not global optimisation; no candidate selected from static or visual success alone',
            'Motor cylinders use catalogue stator dimensions; connectors, brackets, bearings, shafts and cables are omitted',
            'Electronics dimensions are prior packaging allowances, not complete component/connector geometry; main protection omitted',
            'Changed bracket masses reuse prior budget, with full extra leg strips; new frame and mounts not designed or weighed',
            'No new mass tensor/contract or dynamic walking/turning validation is released',
            '25 sampled yaw/roll poses include opposed extremes; a failure may require coupled range constraints but cannot be silently ignored',
            'Original skin affine scaling is a diagnostic interior-volume comparison, not a final exterior design'])
    report['limitations'].append('Skin uses STL vertex/triangle-centre interior probes with0.2mm depth threshold; zero probes are NOT exact clearance or continuous native validation')
    report['limitations'].append('Convex outer-hull fit is only necessary; actual interior wall, electronics mounts and plug bends remain unverified')
    (R/'evidence/hip_architecture_comparison.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__': main()
