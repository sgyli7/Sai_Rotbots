"""Variant acceptance: no inherited clamp, same arm/legs, real load surface."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from sai_agent.paths import model_root, robot_catalog

ROOT=Path(__file__).resolve().parents[1]


def test_preserved_001_and_removed_002_mechanism():
    assert set(robot_catalog())=={'Sai_Agent_001','Sai_Agent_002'}
    a=json.loads((model_root('Sai_Agent_001')/'full/robot.json').read_text())
    b=json.loads((model_root('Sai_Agent_002')/'full/robot.json').read_text())
    assert a['robot_id']=='Sai_Agent_001' and a['cargo']['slider_stroke_m']==.067
    assert b['robot_id']=='Sai_Agent_002' and b['cargo']['active_clamp'] is False
    assert set(a['bodies'])-set(b['bodies'])=={'cargo_slide_-1','cargo_slide_1','cargo_rotor'}
    for name,body in b['bodies'].items():
        if name!='chassis':assert body==a['bodies'][name]
    assert a['cameras']==b['cameras']
    for name in ['touch_inner_service_cover','battery_candidate','main_camera_module']:
        assert next(c for c in a['bodies']['chassis']['mass_components'] if c['name']==name)==next(c for c in b['bodies']['chassis']['mass_components'] if c['name']==name)
    parts=json.loads((model_root('Sai_Agent_002')/'asset_provenance.json').read_text())['parts']
    assert not any(p['name'].startswith(('force_board_','maestro')) for p in parts)
    assert {p['name'] for p in parts if p['name'].startswith('cargo_')}=={'cargo_shell','cargo_mat'}


def test_002_physics_mass_and_flat_surface():
    directory=model_root('Sai_Agent_002')
    full=mujoco.MjModel.from_xml_path(str(directory/'full/robot.xml'))
    reduced=mujoco.MjModel.from_xml_path(str(directory/'locomotion.xml'))
    visual=mujoco.MjModel.from_xml_path(str(directory/'full/visual.xml'))
    spec=json.loads((directory/'full/robot.json').read_text())
    assert full.nu==22 and full.neq==0 and reduced.nu==16
    assert np.isclose(full.body_mass.sum()-.1,reduced.body_mass.sum())
    assert np.isclose(reduced.body_mass.sum(),spec['total_robot_mass_kg'])
    assert np.array_equal(full.body_mass,visual.body_mass)
    assert spec['total_robot_mass_kg']<9.27575862830697
    assert all(not full.joint(j).name.startswith('cargo_') for j in range(full.njnt))
    # Raycast the physical mat itself across the entire newly recovered area.
    data=mujoco.MjData(full);mujoco.mj_forward(full,data)
    geom=full.geom('chassis_contact_1').id
    for x in np.linspace(-.125,.021,12):
        for y in np.linspace(-.107,.107,12):
            distance=mujoco.mju_rayGeom(data.geom_xpos[geom],data.geom_xmat[geom],full.geom_size[geom],np.array([x,y,.4]),np.array([0.,0.,-1.]),mujoco.mjtGeom.mjGEOM_BOX)
            assert np.isclose(.4-distance, .259 + data.xpos[full.body("chassis").id,2] - .22, atol=1e-9)


def test_godot_controller_accepts_22_joint_variant_and_rejects_mismatch():
    from sai_agent.godot_controller import GodotController
    c=GodotController(ROOT,robot_id='Sai_Agent_002')
    state=dict(robot_id='Sai_Agent_002',physics_owner='Godot/Jolt',q=[0.]*22,v=[0.]*22,
               time=0.,base_position=[0,0,.22],base_rotation_columns=np.eye(3).tolist(),
               base_linear_world=[0,0,0],base_angular_world=[0,0,0],command=[0,0,0],terrain_heights=[0.]*24)
    assert len(c.command(state)['target_leg'])==16
    import pytest
    with pytest.raises(ValueError):c.command(dict(state,robot_id='Sai_Agent_001'))
    with pytest.raises(ValueError):c.command(dict(state,q=[0.]*25,v=[0.]*25))
