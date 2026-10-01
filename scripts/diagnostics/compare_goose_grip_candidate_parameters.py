"""Potential closed-pose SI parameter delta; never installs or releases a kit."""
from pathlib import Path
import copy
import hashlib
import json

import numpy as np
from sai_agent.goose.mass_properties import aggregate_rigid_components

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'robots/Goose_V0.1'


def main():
    paths=[R/'evidence/body_bay_mechanical_parameters.json',
           R/'cad/source/mechanical_preview/scene.json',
           R/'cad/exports/grip_cassettes/manifest.json',
           R/'cad/exports/bill_mount_fasteners/manifest.json']
    ledger,scene,grip,mounts=[json.loads(p.read_text()) for p in paths]
    for filename in ['grip_cassette_native_fit.json','grip_cassette_quad_gate.json',
                     'bill_mount_fasteners_native_fit.json','bill_mount_fasteners_quad_gate.json']:
        file=R/'evidence'/filename;gate=json.loads(file.read_text());paths.append(file)
        if 'passed_samples' in gate and (gate['sample_count']!=23 or gate['passed_samples']!=23):
            raise ValueError(('Candidate geometry gate not complete',filename))
        if 'mesh_identity_and_geometry_pass' in gate and not gate['mesh_identity_and_geometry_pass']:
            raise ValueError(('Candidate quad gate not passed',filename))
        for relative,expected in gate['source_hashes'].items():
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                raise ValueError(('Stale candidate geometry gate',filename,relative))
    old_items=[copy.deepcopy(i) for i in ledger['items'] if i['name']!='specified_payload_50g']
    removed=set(grip['replaces_existing_parts'])
    replaced=[i for i in old_items if i['name'] in removed]
    if {i['name'] for i in replaced}!=removed:
        raise ValueError('Not all six predecessor mass items exist')
    parts=grip['parts']+mounts['parts']
    if len({p['name'] for p in parts})!=len(parts):raise ValueError('Duplicate candidate part')
    added=[]
    lift=np.array([0.,0.,ledger['rigid_coordinate_lift_m']])
    for p in parts:
        added.append(dict(name=p['name'],body=p['body'],mass_kg=p['mass_kg'],
                          center_m=(np.array(p['center_of_mass_world_m'])+lift).tolist(),
                          inertia_at_com_kg_m2=p['inertia_at_com_world_kg_m2'],
                          relative_uncertainty=.1,basis='native density estimate,independent grip/frame clamp candidate'))
    candidate=[i for i in old_items if i['name'] not in removed]+added
    if len({i['name'] for i in candidate})!=len(candidate):raise ValueError('Duplicate candidate mass item')
    nominal=sum(i['mass_kg'] for i in candidate)
    before=sum(i['mass_kg'] for i in old_items)
    if abs(before-ledger['nominal_conditional_mass_kg'])>1e-10:raise ValueError('Current baseline mass mismatch')
    deltas=[]
    for body in ['head_roll','beak_hinge']:
        origin=ledger['pivots_world_at_zero_m'][body]
        previous=aggregate_rigid_components([i for i in old_items if i['body']==body],origin)
        proposed=aggregate_rigid_components([i for i in candidate if i['body']==body],origin)
        eigen=np.linalg.eigvals(np.linalg.solve(np.array(previous['inertia_at_com_body_kg_m2']),
                                               np.array(proposed['inertia_at_com_body_kg_m2']))).real
        deltas.append(dict(body=body,previous=previous,proposed=proposed,
                           relative_mass_change=proposed['mass_kg']/previous['mass_kg']-1,
                           com_shift_m=float(np.linalg.norm(np.array(proposed['com_local_m'])-previous['com_local_m'])),
                           generalized_inertia_ratios=eigen.tolist()))
    old_reserves=[i for i in old_items if 'reserve' in i['name'] or 'allocation' in i['name']]
    if any(i not in candidate for i in old_reserves):raise ValueError('No implicit reserve deduction allowed')
    pads=[]
    for p in grip['parts']:
        if p['name'].endswith('_grip_cassette_pad'):
            file=R/p['files']['npz']['path']
            if hashlib.sha256(file.read_bytes()).hexdigest()!=p['files']['npz']['sha256']:
                raise ValueError(('Pad source identity',p['name']))
            with np.load(file) as mesh:
                points=mesh['vertices'];pads.append((points.min(axis=0),points.max(axis=0)))
    if len(pads)!=2:raise ValueError('Exactly two actual pad sources required')
    distal=min(float(hi[0]) for lo,hi in pads)
    old_reference=np.array(ledger['grip_world_at_zero_m'])-lift
    outside=any(old_reference[0]>hi[0] for lo,hi in pads)
    pad_geometry=dict(maximum_width_m=max(float(hi[1]-lo[1]) for lo,hi in pads),
                      closed_contact_plane_native_z_m=grip['pad_contact_plane_closed_world_z_mm']/1000,
                      distal_pad_x_m=distal,old_grip_reference_native_x_m=float(old_reference[0]),
                      old_reference_point_inside_new_contact_footprint=not outside,
                      proposed_contact_reference_native_m=[.220,0.,.553],
                      contact_reference_accepted=False,
                      effect='Fresh task/contact placement and physical grip tests required;old50g trial does not release this kit.')
    simple=dict(schema='goose_grip_cassette_parameter_delta_v2',installed=False,
                current_scene_parts=len(scene['parts']),current_conditional_mass_kg=before,
                candidate_native_parts=len(grip['parts']),candidate_kit_mass_kg=grip['native_mass_kg'],
                additional_frame_mount_parts=len(mounts['parts']),additional_frame_mount_mass_kg=mounts['native_mass_kg'],
                replaced_items=[dict(name=i['name'],body=i['body'],mass_kg=i['mass_kg']) for i in replaced],
                replaced_mass_kg=sum(i['mass_kg'] for i in replaced),
                nominal_replacement_delta_kg=nominal-before,possible_conditional_mass_kg=nominal,
                possible_scene_parts=len(scene['parts'])-len(removed)+len(parts),reserve_deduction_kg=0.,
                body_deltas=deltas,contact_geometry=pad_geometry,
                source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]},
                manufacturing_release=False,training_release=False,structural_release=False,
                limitations=['Closed-pose forecast only;not installed in the scene,ledger,runtime,collisions,BOM or current fourimages.',
                             'Fresh whole-robot torque/collision/task/FK/inertia checks and render identity required before installation.',
                             '80g head internal reserve retained in full;coating,camera,wiring and closure allowances not spent.',
                             'Nominal screw/nut thread-envelope mass overlaps are not exact helical hardware mass;material/process/preload unqualified.',
                             'New narrower contact surface and proposed reference invalidate silent reuse of old grip-task placement.'])
    (R/'evidence/grip_cassette_parameter_delta.json').write_text(json.dumps(simple,indent=2)+'\n')
    print('INDEPENDENT CANDIDATE forecast',simple['possible_scene_parts'],'mass',nominal,'net kg',nominal-before)
    print('BODY DELTAS',[(d['body'],d['relative_mass_change'],d['com_shift_m']) for d in deltas])


if __name__=='__main__':
    main()
