"""Counterexamples for contact-statics evidence: no invented ground support."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/evaluation/evaluate_gorilla_layout.py'
MODULE_SPEC = importlib.util.spec_from_file_location('gorilla_screen', MODULE_PATH)
MODULE = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(MODULE)


def make_screen(tmp_path, foot_height=.45, disabled=False, torque_limit=100, friction=1.0,
                palm_height=.95, spring=False, obstacle=False, gravcomp=0, condim=3,
                unnamed_ground_structure=False):
    mask = 'contype="0" conaffinity="0"' if disabled else 'contype="1" conaffinity="1"'
    xml = f'''<mujoco><compiler angle="radian"/><option gravity="0 0 -9.81"/>
      <worldbody><geom name="floor" type="plane" size="3 3 .1" friction="{friction} .005 .0001" condim="{condim}"/>
      {'<geom name="obstacle" type="box" pos="0 .43 .08" size=".05 .05 .05"/>' if obstacle else ''}
      <body name="pelvis" pos="0 0 .95" gravcomp="{gravcomp}"><freejoint/>
      <geom type="box" size=".1 .1 .1" mass="4" contype="0" conaffinity="0"/>
      <body name="left_foot" pos="0 .43 {foot_height + .05 - .95}">
        <geom {'' if unnamed_ground_structure else 'name="left_sole"'} type="box" size=".10 .08 .05" mass="1" friction="{friction} .005 .0001" condim="{condim}" {mask}/></body>
      <body name="right_foot" pos="0 -.43 {foot_height + .05 - .95}">
        <geom name="right_sole" type="box" size=".10 .08 .05" mass="1" friction="{friction} .005 .0001" condim="{condim}" {mask}/></body>
      <body name="left_palm" pos="0 .2 {palm_height - .95}"><inertial mass=".1" pos="0 0 0" diaginertia=".01 .01 .01"/></body>
      <body name="right_palm" pos="0 -.2 {palm_height - .95}"><inertial mass=".1" pos="0 0 0" diaginertia=".01 .01 .01"/></body>
      <body name="counterweight"><joint name="test_joint" axis="0 1 0" range="-1 1" {'stiffness="1000" springref="1"' if spring else ''}/>
        <geom pos=".25 0 0" type="box" size=".02 .02 .02" mass=".3" contype="0" conaffinity="0"/></body>
      {'<body name="nonsole_structure" pos=".3 0 -.93"><geom type="box" size=".05 .05 .05" mass=".1"/></body>' if unnamed_ground_structure else ''}
      </body></worldbody><actuator><position joint="test_joint" kp="10" forcelimited="true" forcerange="{-torque_limit} {torque_limit}"/></actuator>
      </mujoco>'''
    model = tmp_path / 'model.xml'
    model.write_text(xml)
    spec = tmp_path / 'spec.json'
    spec.write_text(json.dumps({'joints': [{'name': 'test_joint', 'drive_class': 'test',
                                          'range_rad': [-1, 1]}],
        'drive_classes': {'test': {'design_torque_nm': torque_limit, 'design_speed_rad_s': 1}},
        # Deliberately false foot anchors; the screen must use actual sole geometry.
        'points_world_m': {'left_foot': [0, .43, 0], 'left_palm': [0, .2, palm_height]}}))
    return MODULE.Screen(model, spec)


def pose(screen):
    return {'name': 'counterexample', 'qpos': screen.neutral.copy(), 'feet': ['left', 'right'],
            'ik_position_error_m': 0, 'ik_rotation_matrix_error': 0,
            'horizontal_door_force_n': 0}


def test_floating_small_sole_cannot_pass_using_false_spec_anchors(tmp_path):
    screen = make_screen(tmp_path)
    result = screen.static(pose(screen), 0)
    assert result['contact_lp_success']  # Force equilibrium alone is insufficient.
    assert result['foot_corner_height_error_m'] == pytest.approx(.45)
    assert not result['limited_screen_pass']
    actual = screen.sole_corners_local['left']
    assert np.ptp(actual[:, 0]) == pytest.approx(.2)
    assert np.ptp(actual[:, 1]) == pytest.approx(.16)


def test_disabled_collision_sole_has_no_fictitious_support(tmp_path):
    with pytest.raises(ValueError, match='no active collision sole box'):
        make_screen(tmp_path, disabled=True)


def test_grounded_supported_sample_and_insufficient_joint_torque(tmp_path):
    screen = make_screen(tmp_path, foot_height=0)
    result = screen.static(pose(screen), 0)
    assert result['limited_screen_pass']
    weak = make_screen(tmp_path, foot_height=0, torque_limit=.0001)
    result = weak.static(pose(weak), 0)
    assert result['contact_lp_success']
    assert result['max_design_torque_utilization'] > 1
    assert not result['limited_screen_pass']


def test_low_friction_floor_cannot_support_door_reaction(tmp_path):
    screen = make_screen(tmp_path, foot_height=0, friction=.1, palm_height=.4)
    loaded = pose(screen)
    loaded['horizontal_door_force_n'] = 8
    result = screen.static(loaded, 0)
    assert result['friction_pyramid_mu'] == pytest.approx(.1)
    assert not result['contact_lp_success']
    assert not result['limited_screen_pass']


def test_passive_spring_cannot_hide_required_motor_torque(tmp_path):
    screen = make_screen(tmp_path, foot_height=0, spring=True)
    result = screen.static(pose(screen), 0)
    assert result['passive_joint_force_nm']['test_joint'] == pytest.approx(1000)
    assert result['contact_lp_success']
    assert result['max_design_torque_utilization'] > 9
    assert not result['limited_screen_pass']


def test_foot_collision_with_world_obstacle_is_not_ground_exemption(tmp_path):
    screen = make_screen(tmp_path, foot_height=0, obstacle=True)
    result = screen.static(pose(screen), 0)
    assert result['collision']['nonfoot_or_self_penetration_count'] > 0
    assert result['collision']['max_penetration_m'] == pytest.approx(.07)
    assert not result['limited_screen_pass']


def test_hidden_gravity_support_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='gravity compensation'):
        make_screen(tmp_path, foot_height=0, gravcomp=1)


def test_normal_only_contact_cannot_supply_friction(tmp_path):
    screen = make_screen(tmp_path, foot_height=0, condim=1, palm_height=.4)
    loaded = pose(screen)
    loaded['horizontal_door_force_n'] = 1
    result = screen.static(loaded, 0)
    assert result['friction_pyramid_mu'] == 0
    assert not result['contact_lp_success']


def test_unnamed_nonsole_ground_collision_cannot_use_sole_exemption(tmp_path):
    screen = make_screen(tmp_path, foot_height=0, unnamed_ground_structure=True)
    result = screen.static(pose(screen), 0)
    assert any('nonsole_structure' in p['bodies'] for p in result['collision']['pairs'])
    assert not result['limited_screen_pass']


def test_last_integrated_tick_penetration_is_checked_at_new_state(tmp_path):
    screen = make_screen(tmp_path, foot_height=.001)
    result = screen.reject_run(.04, seconds=.04)
    assert result['actual_integrations'] == 1
    assert result['completed']
    assert result['max_contact_penetration_m'] > .005
    assert 'contact_penetration_exceeded_5mm' in result['stop_reasons']
    assert not result['limited_rejection_pass']
