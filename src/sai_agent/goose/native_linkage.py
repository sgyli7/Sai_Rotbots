"""Neutral SI description of the equal-crank jaw's two passive moving bodies.

The actuator interface remains eighteen named axes. Passive input/crank and
coupler coordinates are derived from the jaw angle, not policy actions.
"""
from __future__ import annotations

import numpy as np

from .mass_properties import aggregate_rigid_components

INPUT_PARTS = frozenset({
    'beak_native_input_flange', 'beak_input_steel_sleeve',
    'beak_input_washer', 'beak_input_button_screw',
})
COUPLER_PARTS = frozenset({
    'beak_native_coupler', 'beak_input_bush_candidate',
    'beak_output_bush_candidate',
})
PART_OWNERS = {**dict.fromkeys(INPUT_PARTS, 'beak_input_rotor'),
               **dict.fromkeys(COUPLER_PARTS, 'beak_coupler_link')}


def split_linkage(contract: dict, ledger: dict) -> None:
    """Split native parts out of the closed-pose head aggregate, conserving SI mass.

    The ledger's static screen retains its nineteen-body closed-pose reduction.
    This runtime contract instead carries the actual moving parts and inertias.
    """
    transmission = ledger.get('native_beak_transmission')
    if transmission is None:
        return
    lift = np.array([0., 0., ledger['rigid_coordinate_lift_m']])
    motor = np.array(transmission['motor_axis_world_mm']) / 1000 + lift
    phase = transmission['closed_phase_rad']
    delta = transmission['crank_radius_mm'] / 1000 * np.array([np.cos(phase), 0., np.sin(phase)])
    specifications = [
        dict(name='beak_input_rotor', parent='head_roll', pivot_world_at_zero_m=motor.tolist(),
             axis_parent=[0., 1., 0.], range_rad=[0., .55],
             mimic_joint='beak_hinge', mimic_multiplier=1., mimic_offset_rad=0.),
        dict(name='beak_coupler_link', parent='beak_input_rotor',
             pivot_world_at_zero_m=(motor + delta).tolist(),
             axis_parent=[0., 1., 0.], range_rad=[-.55, 0.],
             mimic_joint='beak_hinge', mimic_multiplier=-1., mimic_offset_rad=0.),
    ]
    jaw = next(j for j in contract['joints'] if j['name'] == 'beak_hinge')
    specifications[0].update(armature_kg_m2=jaw['armature_kg_m2'], frictionloss_nm=jaw['frictionloss_nm'])
    jaw.update(actuation_joint='beak_input_rotor', armature_kg_m2=0., frictionloss_nm=0.)
    items = contract['items']
    found = {i['name'] for i in items if i['name'] in PART_OWNERS}
    if found != set(PART_OWNERS):
        raise ValueError('incomplete native linkage mass coverage')
    for item in items:
        if item['name'] in PART_OWNERS:
            if item['body'] != 'head_roll':
                raise ValueError('unexpected static linkage mass owner')
            item['body'] = PART_OWNERS[item['name']]
    head = next(b for b in contract['bodies'] if b['name'] == 'head_roll')
    head.update(aggregate_rigid_components([i for i in items if i['body'] == 'head_roll'],
                                          ledger['pivots_world_at_zero_m']['head_roll']))
    for joint in specifications:
        group = [i for i in items if i['body'] == joint['name']]
        body = dict(name=joint['name'], **aggregate_rigid_components(group, joint['pivot_world_at_zero_m']))
        body['mass_relative_design_uncertainty'] = sum(i['mass_kg'] * i['relative_uncertainty'] for i in group) / body['mass_kg']
        body.update(com_randomization_m=.001, inertia_multiplier_range=[.9, 1.1])
        contract['bodies'].append(body)
    contract['passive_linkage_joints'] = specifications
    contract['passive_linkage_parts'] = dict(PART_OWNERS)
    contract['beak_transmission'].update(
        closed_crank_angle_in_xz_rad=phase,
        lumped_mass_status='Native input rotor and translating coupler are explicit passive bodies; closed-pose static ledger is a separate reduction.',
        passive_constraints='qin=qjaw; qcoupler=-qjaw; URDF mimic and neutral SI authoritative; backend enforcement required.',
    )
    if abs(sum(b['mass_kg'] for b in contract['bodies']) - contract['nominal_robot_mass_kg']) > 1e-10:
        raise ValueError('linkage split changed total mass')


def set_passive_linkage(model, data, contract: dict) -> None:
    """Initialize kinematic mimic coordinates after a pose/reset, by name."""
    for joint in contract.get('passive_linkage_joints', []):
        source = model.joint(joint['mimic_joint'])
        target = model.joint(joint['name'])
        data.qpos[target.qposadr[0]] = (joint['mimic_multiplier'] * data.qpos[source.qposadr[0]]
                                       + joint['mimic_offset_rad'])
        data.qvel[target.dofadr[0]] = joint['mimic_multiplier'] * data.qvel[source.dofadr[0]]
