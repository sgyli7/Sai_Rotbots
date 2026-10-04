"""Manual wing doors with actual integral hinge arms and a screw closure.

New independent candidate. Retained roof carriers and active kinematics are
unchanged. Service poses have the thumbscrew/washer removed; these doors are
locked and attached to the torso during robot operation. No frozen model edit.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import numpy as np
from scipy.optimize import brentq
from OCP.gp import gp_Pnt, gp_Vec
from build123d import (SkipClean, Polygon, Plane, Pos, RegularPolygon, extrude,
                      import_brep, import_step)

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder, transform
from goose_candidate_export import CandidateExport
from goose_structured_shell_export import emit_structured_shell
from goose_nurbs_skin import surface
from sai_agent.goose.torso_service_skin import service_skin_grids
from sai_agent.goose.mass_properties import aggregate_rigid_components
from sai_agent.native_cad_query import native_solid_integrity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alignment(normal):
    z = np.asarray(normal, dtype=float)
    z /= np.linalg.norm(z)
    seed = [0, 0, 1] if abs(z[2]) < .9 else [1, 0, 0]
    x = np.cross(seed, z)
    x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def strip(points_yz, width, x, thickness):
    p = np.asarray(points_yz, dtype=float)
    tangents = np.diff(p, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1)[:, None]
    normals = np.column_stack([-tangents[:, 1], tangents[:, 0]])
    bisectors = np.vstack([normals[0], normals[:-1]+normals[1:], normals[-1]])
    bisectors /= np.linalg.norm(bisectors, axis=1)[:, None]
    offsets = bisectors*width/2
    loop = np.vstack([p+offsets, (p-offsets)[::-1]])
    # build123d variadic points must be tuples/Vector: nested lists can be
    # flattened into scalars and silently produce a zero-area wire.
    face = Plane.YZ*Polygon(*[tuple(v) for v in loop], align=None)
    result = Pos(x-thickness/2, 0, 0)*extrude(face, amount=thickness, dir=(1, 0, 0))
    if not result.is_valid or result.volume <= 0 or len(result.solids()) != 1:
        raise ValueError('Degenerate hinge strip')
    return result


def union(shapes):
    result = shapes[0]
    with SkipClean():
        for shape in shapes[1:]:
            result += shape
    return result


def apply_features(base, additions, cutters):
    # Keep the original trimmed surface partitions. Automatic face merging
    # produced a rejected self-interference result on this actual left skin.
    with SkipClean():
        result = base
        for add in additions:
            result += add
        for cutter in cutters:
            result -= cutter
    if not native_solid_integrity(result)['boolean_input_integrity_pass']:
        raise ValueError('Feature-bearing skin failed native integrity')
    return result


def main():
    cp = R/'configs/manual_wing_service.json'
    cfg = json.loads(cp.read_text())
    sp, pp, smp, rmp, lp = [R/cfg[k] for k in
        ['source_scene', 'source_parameters', 'skin_manifest', 'roof_manifest', 'layout']]
    if sha(sp) != cfg['source_scene_sha256']:
        raise ValueError('Frozen460 source changed')
    old_scene, old_params, skin, roof, layout = [json.loads(p.read_text()) for p in [sp, pp, smp, rmp, lp]]
    roof_cfg_path = R/'configs/torso_shell_mounts.json'
    roof_cfg = json.loads(roof_cfg_path.read_text())
    skin_cfg_path = R/'configs/torso_service_skin.json'
    export = CandidateExport(R, 'manual_wing_service')
    inputs = [cp, sp, pp, smp, rmp, lp, roof_cfg_path, skin_cfg_path, Path(__file__),
              ROOT/'scripts/cad/goose_candidate_export.py', ROOT/'scripts/cad/goose_structured_shell_export.py',
              ROOT/'scripts/cad/goose_nurbs_skin.py', ROOT/'scripts/cad/build_goose_cad.py',
              ROOT/'scripts/cad/build_goose_actuator_interfaces.py',
              ROOT/'src/sai_agent/goose/torso_service_skin.py',
              ROOT/'src/sai_agent/goose/mass_properties.py', ROOT/'src/sai_agent/native_cad_query.py']
    by_name = {p['name']: p for p in skin['parts']}
    replaced, interfaces, thread_contacts = [], [], []
    def source_part(name):
        rec = by_name[name]
        for key in ['brep', 'npz']:
            path = R/rec['files'][key]['path']
            if sha(path) != rec['files'][key]['sha256']:
                raise ValueError('Changed repaired skin')
            inputs.append(path)
        shape = import_brep(R/rec['files']['brep']['path'])
        if not native_solid_integrity(shape)['boolean_input_integrity_pass']:
            raise ValueError('Invalid repaired skin')
        return shape, R/rec['files']['npz']['path']
    for side, label in [(-1, 'right'), (1, 'left')]:
        grids = service_skin_grids(layout['body_profile_x_cz_ry_rz_mm'], side,
            layout['body_wall_mm'], layout['lower_limb_exit_boundary_u_v'])
        sf = surface(grids[0])
        def point(x, v):
            u = brentq(lambda u: sf.Value(u, v).X()-x, 0, 1)
            p, a, b = gp_Pnt(), gp_Vec(), gp_Vec()
            sf.D1(u, v, p, a, b)
            n = np.cross(a.Coord(), b.Coord())
            n /= np.linalg.norm(n)
            if n[1]*side < 0:
                n = -n
            return np.asarray(p.Coord()), n
        fore_add, fore_cut, door_add, door_cut = [], [], [], []
        axis = np.array([0, -side*cfg['axis_right_yz_mm'][0], cfg['axis_right_yz_mm'][1]], dtype=float)
        for index, x in enumerate(cfg['hinge_x_mm']):
            q, n = point(x, .70)
            door_add.append(transform(cylinder(4.5, 6), alignment(n), q+n))
            pts = [(point(x, v)[0]+cfg['moving_arm_offset_mm']*point(x, v)[1])[1:]
                   for v in cfg['moving_arm_latitudes']]+[axis[1:]]
            door_add += [strip(pts, cfg['arm_width_mm'], x, cfg['moving_barrel_length_mm']),
                         cylinder(cfg['barrel_od_mm']/2, cfg['moving_barrel_length_mm'], [x, *axis[1:]], axis='x')]
            for dx in [-cfg['fixed_barrel_center_offset_x_mm'], cfg['fixed_barrel_center_offset_x_mm']]:
                a, n = point(x+dx, cfg['fixed_anchor_latitude'])
                fore_add += [transform(cylinder(4, 6), alignment(n), a+n),
                    strip([(a+3*n)[1:], axis[1:]], cfg['arm_width_mm'], x+dx, cfg['fixed_barrel_length_mm']),
                    cylinder(cfg['barrel_od_mm']/2, cfg['fixed_barrel_length_mm'], [x+dx, *axis[1:]], axis='x')]
            bore = cylinder(cfg['barrel_bore_mm']/2, 12, [x, *axis[1:]], axis='x')
            fore_cut.append(bore)
            door_cut.append(bore)
            key = f'wing_hinge_{label}_{index}'
            screw_cfg = cfg['shoulder_screw']
            rot = alignment([1, 0, 0])
            origin = axis+np.array([x-5, 0, 0])
            screw = union([cylinder(screw_cfg['shaft_d_mm']/2, 10, [0, 0, 5]),
                           cylinder(screw_cfg['head_d_mm']/2, 2.5, [0, 0, -1.25]),
                           cylinder(1.5, 6, [0, 0, 13])])
            socket = Pos(0, 0, -2.51)*extrude(RegularPolygon(3/np.sqrt(3), 6), amount=1.61)
            with SkipClean():
                screw -= socket
            export.emit(key+'_shoulder_screw', transform(screw, rot, origin), 'torso',
                rho=cfg['density_steel_kg_m3'], material='graphite', notes=[screw_cfg['sku'], 'Own nominal purchased envelope; threads/undercuts simplified, not a printable fastener.'])
            washer = cylinder(3.5, .5, [0, 0, 10.25])-cylinder(1.6, 2, [0, 0, 10.25])
            export.emit(key+'_m3_washer', transform(washer, rot, origin), 'torso', rho=cfg['density_steel_kg_m3'], material='graphite')
            nut = Pos(0, 0, 10.5)*extrude(RegularPolygon(5.5/np.sqrt(3), 6), amount=4)
            nut -= cylinder(1.25, 8, [0, 0, 12.5])
            export.emit(key+'_retention_nut', transform(nut, rot, origin), 'torso', rho=cfg['density_steel_kg_m3'], material='graphite', notes=[cfg['retention_nut']['sku'], cfg['retention_nut']['model_basis']])
            thread_contacts.append(dict(screw=key+'_shoulder_screw', tapped_part=key+'_retention_nut', nominal_engagement_mm=4, protrusion_mm=1.5))
            interfaces.append(dict(name=key, axis_point_mm=[x, *axis[1:]], axis_direction=[1, 0, 0],
                diametral_printed_bore_clearance_mm=.3, moving_fixed_axial_gap_mm=.25,
                axial_end_float_mm=.5, shoulder_screw_sku=screw_cfg['sku'],
                pin_retention='Nut tightens against the shoulder/metal washer; nominal plastic knuckle stack9.5mm does not take clamp preload.'))
        q, n = point(cfg['latch_door_x_mm'], cfg['latch_latitude'])
        qf, nf = point(cfg['latch_fixed_x_mm'], cfg['latch_latitude'])
        a, b = q-6.9*n, qf-cfg['latch_link_fixed_inward_mm']*nf
        d = b-a
        fore_add += [transform(cylinder(4.6, 8), alignment(n), a),
                     transform(cylinder(5, 7), alignment(nf), qf-2.5*nf),
                     transform(cylinder(3.5, np.linalg.norm(d)+2), alignment(d), (a+b)/2)]
        fore_cut.append(transform(cylinder(2, 6.72), alignment(n), q-6.25*n))
        door_cut.append(transform(cylinder(1.7, 12), alignment(n), q))
        key = 'wing_closure_'+label
        rot = alignment(n)
        screw = union([cylinder(1.5, 8, [0, 0, -3.5]), cylinder(6, 2.5, [0, 0, 1.75])])
        export.emit(key+'_thumb_screw', transform(screw, rot, q), 'torso', rho=cfg['density_steel_kg_m3'], material='graphite', notes=[cfg['thumb_screw']['sku'], 'Tool-free positive closure, removable, NOT captive; own nominal envelope.'])
        washer = cylinder(3.5, .5, [0, 0, .25])-cylinder(1.6, 2, [0, 0, .25])
        export.emit(key+'_m3_washer', transform(washer, rot, q), 'torso', rho=cfg['density_steel_kg_m3'], material='graphite')
        insert = cylinder(2.3, 5.7, [0, 0, -5.75])-cylinder(1.25, 10, [0, 0, -5.75])
        export.emit(key+'_m3_insert', transform(insert, rot, q), 'torso', rho=roof_cfg['insert']['nominal_brass_density_kg_m3'], material='titanium', notes=['Ruthex RX-M3x5.7 own nominal maximum-OD envelope; as-printed4mm pilot represents intentional heat setting.'])
        interfaces.append(dict(name=key, outer_surface_point_mm=q.tolist(), outward_normal=n.tolist(),
            pilot_diameter_mm=4, pilot_depth_mm=6.7, insert_entry_inward_mm=2.9,
            nominal_thread_engagement_mm=4.6, nominal_insert_tip_clearance_mm=1.1,
            removable_parts=[key+'_thumb_screw', key+'_m3_washer']))
        thread_contacts.append(dict(screw=key+'_thumb_screw', tapped_part=key+'_m3_insert', nominal_engagement_mm=4.6))
        for suffix in ['aft', 'fore', 'door']:
            old_name = 'wing_access_cover_'+label if suffix == 'door' else 'torso_mounted_shell_'+label+'_'+suffix
            base_name = 'wing_service_door_'+label if suffix == 'door' else 'torso_service_shell_'+label+'_'+suffix
            base, npz = source_part(base_name)
            additions, cutters = (door_add, door_cut) if suffix == 'door' else ([], [])
            if suffix != 'door':
                anchor = next(p for p in roof['interfaces'] if p['name'] == label+'_'+suffix)
                rotation, entry = np.asarray(anchor['rotation_from_insert_z']), np.asarray(anchor['insert_entry_mm'])
                additions = [transform(cylinder(4.6, 8, [0, 0, 4]), rotation, entry)]
                cutters = [transform(cylinder(2, 6.72, [0, 0, 3.34]), rotation, entry)]
                if suffix == 'fore':
                    additions += fore_add
                    cutters += [cylinder(cfg['neck_port_radius_mm'], cfg['neck_port_cut_height_mm'], cfg['neck_port_center_mm'])]+fore_cut
            result = apply_features(base, additions, cutters)
            new_name = 'wing_manual_door_'+label if suffix == 'door' else 'torso_manual_shell_'+label+'_'+suffix
            emit_structured_shell(export, new_name, result, npz, union(additions), union(cutters))
            record = export.parts[-1]
            record['native_integrity'] = native_solid_integrity(result)
            record['step_integrity'] = native_solid_integrity(import_step(R/record['files']['step']['path']))
            if not record['step_integrity']['boolean_input_integrity_pass']:
                raise ValueError((new_name, 'STEP self-interference'))
            record['notes'] = ['Repaired shared native skin, integral manual hinges and screw-closure lug; actual native/STEP self-interference passed.',
                'No automatic same-surface merge; no enlarged Boolean fuzzy tolerance.',
                'Heat-set pilot/envelope is as-printed geometry; material/print fit, strength, local support and whole assembly remain qualification gates.']
            replaced.append(old_name)
    items = {p['name']:copy.deepcopy(p) for p in old_params['items']}
    removed_mass = sum(items.pop(name)['mass_kg'] for name in replaced)
    lift = old_params['rigid_coordinate_lift_m']
    for p in export.parts:
        items[p['name']] = dict(name=p['name'], body=p['body'], mass_kg=p['mass_kg'],
            center_m=(np.asarray(p['center_of_mass_world_m'])+[0, 0, lift]).tolist(),
            inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'], relative_uncertainty=.1,
            basis='Same-source adaptive native solid / nominal purchased envelope; print/material/fit unqualified')
    all_items = list(items.values())
    mass = sum(p['mass_kg'] for p in all_items)
    export.save(ROOT, inputs, replaces=replaced, extra=dict(interfaces=interfaces,
        nominal_thread_contacts=thread_contacts, repaired_skins_and_roof_mounts=True,
        integral_hinges_and_positive_screw_closure=True, service_axis_changed_from_bare_skin=True,
        removed_skin_mass_kg=removed_mass, net_physical_mass_change_kg=mass-old_params['nominal_conditional_mass_kg'],
        active_axes_unchanged=True, collision_proxy_modified=False,
        whole_assembly_pass=False, finite_service_check_pass=False, manufacturing_release=False))
    mp = R/'cad/exports/manual_wing_service/manifest.json'
    scene_parts = [copy.deepcopy(p) for p in old_scene['parts'] if p['name'] not in replaced]+export.scene
    params = dict(schema='goose_manual_wing_service_parameters_v1', parts=len(scene_parts), active_axes=18,
        nominal_conditional_mass_kg=mass, delta_from460_kg=mass-old_params['nominal_conditional_mass_kg'],
        items=all_items, bodies=[dict(name=b['name'], **aggregate_rigid_components(
            [p for p in all_items if p['body']==b['name']], old_params['pivots_world_at_zero_m'][b['name']]))
            for b in old_params['bodies']], pivots_world_at_zero_m=old_params['pivots_world_at_zero_m'],
        rigid_coordinate_lift_m=lift, neutral_joint_order=old_params['neutral_joint_order'],
        full_assembly_pass=False, manufacturing_release=False, training_release=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs+[mp]})
    po = R/'evidence/manual_wing_service_parameters.json'
    po.write_text(json.dumps(params, indent=2)+'\n')
    scene = dict(unit='m', parts=scene_parts, assembly_translation_m=old_scene['assembly_translation_m'],
        nominal_conditional_mass_kg=mass, status='MANUAL_WING_SERVICE_CANDIDATE_NOT_RELEASED',
        manufacturing_pass=False, final_appearance_pass=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [po, mp]},
        review_views=old_scene.get('review_views', {}), review_ortho_scale_m=old_scene.get('review_ortho_scale_m', {}))
    (export.source/'assembly_scene.json').write_text(json.dumps(scene, separators=(',', ':'))+'\n')
    print('MANUAL SERVICE CANDIDATE', len(scene_parts), 'objects', mass, 'kg', flush=True)


if __name__ == '__main__':
    main()
