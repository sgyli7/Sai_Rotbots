from pathlib import Path
import importlib.util
import json
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import pytest

from sai_agent.goose.task_samples import aggregate_si, primitives, rotation
from sai_agent.goose.task_goal import TaskGoal

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'robots/Goose_V0.1/models/task_samples_v1/object_catalog.json'


@pytest.mark.parametrize('family',['cylinder_weight','handle_weight'])
@pytest.mark.parametrize('mass',[.1,.2,.3])
def test_analytic_si_matches_independently_compiled_primitive_mass(family,mass):
    parts=primitives(family,mass);expected=aggregate_si(parts)
    tree=ET.Element('mujoco');ET.SubElement(tree,'compiler',inertiafromgeom='true')
    body=ET.SubElement(ET.SubElement(tree,'worldbody'),'body',name='sample');ET.SubElement(body,'freejoint')
    for p in parts:
        ET.SubElement(body,'geom',type=p['type'],size=' '.join(map(str,p['size'])),
            pos=' '.join(map(str,p['pos'])),quat=' '.join(map(str,p['quat'])),mass=str(p['mass_kg']))
    # No explicit inertial element: the native compiler derives the reference.
    m=mujoco.MjModel.from_xml_string(ET.tostring(tree,encoding='unicode'));bid=m.body('sample').id
    R=rotation(m.body_iquat[bid]);I=R@np.diag(m.body_inertia[bid])@R.T
    assert m.body_mass[bid]==pytest.approx(mass,abs=1e-12)
    np.testing.assert_allclose(m.body_ipos[bid],expected['com_body_m'],atol=1e-12,rtol=0)
    np.testing.assert_allclose(I,expected['inertia_at_com_body_kg_m2'],atol=1e-14,rtol=1e-10)


def test_all_serialized_formal_samples_have_counted_free_bodies():
    c=json.loads(CATALOG.read_text());formal=[x for x in c['objects'] if not x['development_only']]
    assert len(formal)==6 and sorted({x['SI']['mass_kg'] for x in formal})==[.1,.2,.3]
    for item in formal:
        m=mujoco.MjModel.from_xml_path(str(CATALOG.parent/item['model']));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
        assert m.nbody-1==1 and m.nq==7 and m.nv==6 and m.neq==0
        assert m.ngeom==item['collision_leaves']==(3 if item['family']=='cylinder_weight' else 4)
        assert all(m.geom_contype==1) and all(m.geom_conaffinity==3)
        assert all(m.geom_margin==0) and all(m.geom_priority==2)
        assert m.body_mass[1]==pytest.approx(item['SI']['mass_kg'],abs=1e-12)


def test_native_includes_preserve_full_robot_si_for_each_formal_sample():
    source=ROOT/'robots/Goose_V0.1/models/task_proxy_11_v1/robot.xml'
    original=mujoco.MjModel.from_xml_path(str(source))
    for item in json.loads(CATALOG.read_text())['objects']:
        if item['development_only']:continue
        tree=ET.Element('mujoco')
        ET.SubElement(tree,'include',file=str(source))
        ET.SubElement(tree,'include',file=str(CATALOG.parent/item['model']))
        m=mujoco.MjModel.from_xml_string(ET.tostring(tree,encoding='unicode'))
        for field in ['body_mass','body_ipos','body_inertia','body_iquat']:
            np.testing.assert_array_equal(getattr(m,field)[:original.nbody],getattr(original,field))
        assert m.nbody==original.nbody+1 and m.nq==original.nq+7
        assert m.ngeom==original.ngeom+item['collision_leaves']
        assert m.body(item['object_id']).mass[0]==pytest.approx(item['SI']['mass_kg'])


def test_goal_uses_grip_body_frame_and_keeps_com_separate():
    item=next(x for x in json.loads(CATALOG.read_text())['objects'] if x['object_id']=='handle_weight_300g_v1')
    m=mujoco.MjModel.from_xml_path(str(CATALOG.parent/item['model']));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
    bid=m.body(item['object_id']).id
    goal=TaskGoal(item['object_id'],tuple(d.xpos[bid]),tuple(d.xquat[bid]),(.8,0,.051))
    obs=goal.actor_extension(np.zeros(3),np.array([1,0,0,0]),np.eye(3),0)
    np.testing.assert_allclose(obs[:3],d.xpos[bid],atol=1e-8)
    assert abs(d.xipos[bid,2]-obs[2])>.02
    assert obs.shape==(17,) and obs[-1]==1


def test_local_contact_bench_rejects_zero_friction_grip():
    spec=importlib.util.spec_from_file_location('sample_bench',ROOT/'scripts/evaluation/check_goose_sample_contact.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    item=next(x for x in json.loads(CATALOG.read_text())['objects'] if x['object_id']=='handle_weight_100g_v1')
    normal=module.bench(item);negative=module.bench(item,friction=0.)
    assert normal['integrations']==375 and normal['both_jaws_positive_normal_ticks']==250
    assert normal['dual_contact_hold']
    assert not negative['dual_contact_hold']
    assert normal['object_attachment_constraints']==negative['object_attachment_constraints']==0
    assert not normal['contact_quality_qualification'] and not normal['full_pickup_qualification']


def test_loaded_generalized_gravity_matches_independent_potential_energy():
    spec=importlib.util.spec_from_file_location('ground_screen',ROOT/'scripts/evaluation/check_goose_sample_ground_static.py')
    screen=importlib.util.module_from_spec(spec);spec.loader.exec_module(screen)
    m,d=screen.m,screen.d
    d.qpos[screen.qidx[1:4]]=[1.1,-.5,.4]
    d.qpos[screen.qidx[5]]=.22
    screen.sync()
    base=d.qpos.copy();head=m.body('head_roll').id
    payload=.3;local=np.array([.139,0.,-.045])
    def energy():
        mujoco.mj_forward(m,d)
        pos=d.xpos[head]+d.xmat[head].reshape(3,3)@local
        return -float(np.sum(m.body_mass[:,None]*d.xipos*m.opt.gravity))+payload*9.81*pos[2]
    com=d.xpos[head]+d.xmat[head].reshape(3,3)@local
    demand=screen.gravity_demand(payload,com)
    derivatives=[];epsilon=1e-6
    for column in screen.T.T:
        values=[]
        for sign in [-1,1]:
            d.qpos[:]=base
            mujoco.mj_integratePos(m,d.qpos,column,sign*epsilon)
            values.append(energy())
        derivatives.append((values[1]-values[0])/(2*epsilon))
    np.testing.assert_allclose(derivatives,demand,atol=2e-7,rtol=1e-7)


def test_ground_admission_checks_weight_block_not_only_grip_bar():
    spec=importlib.util.spec_from_file_location('pose_contacts',ROOT/'scripts/evaluation/check_goose_sample_pose_contacts.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    report=json.loads((ROOT/'robots/Goose_V0.1/evidence/task_samples_v1_handoff.json').read_text())
    row=next(x for x in report['ground_endpoint_screen']['results']
        if x['family']=='handle_weight' and x['grip_offset_body_m'][0]==0.)
    item=next(x for x in json.loads(CATALOG.read_text())['objects'] if x['object_id']=='handle_weight_100g_v1')
    m,_,nq,ngeom=checker.scene(item);d=mujoco.MjData(m)
    d.qpos[:nq]=row['qpos'];qa=int(m.joint(item['object_id']+'_free').qposadr[0])
    d.qpos[qa:qa+7]=[*row['object_grip_origin_world_m'],1,0,0,0]
    mujoco.mj_forward(m,d)
    distance=mujoco.mj_geomDistance(m,d,m.geom('lower_bill_envelope').id,m.geom(item['object_id']+'_weight').id,1,None)
    assert distance < -.01
    assert not row['actual_sample_robot_clear']
