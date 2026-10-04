from pathlib import Path
import json
import mujoco
import numpy as np
import pytest
from sai_agent.goose.task_proxy_runtime import TaskProxyRuntime
from sai_agent.goose.task_goal import TaskGoal

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'robots/Goose_V0.1/models/task_proxy_11_v1/robot.xml'
CONTRACT=ROOT/'robots/Goose_V0.1/configs/task_proxy_11_v1_contract.json'


def runtime(**kwargs):return TaskProxyRuntime(MODEL,CONTRACT,**kwargs)


def test_collision_geometry_has_no_added_mass_and_keeps_physical_tree():
 m=mujoco.MjModel.from_xml_path(str(MODEL));c=json.loads(CONTRACT.read_text())
 assert m.ngeom-1==11 and m.nbody-1==21 and m.nu==18
 assert sum(m.body_mass)==pytest.approx(10.43069082136313,abs=1e-10)
 for b in c['bodies']:
  bid=m.body(b['name']).id;r=np.empty(9);mujoco.mju_quat2Mat(r,m.body_iquat[bid]);r=r.reshape(3,3)
  assert np.allclose(r@np.diag(m.body_inertia[bid])@r.T,b['inertia_at_com_body_kg_m2'],rtol=1e-10,atol=1e-12)
  assert np.allclose(m.body_ipos[bid],b['com_local_m'],atol=1e-12)


@pytest.mark.parametrize('bad',[np.zeros(17),np.zeros(19),np.full(18,np.nan),np.full(18,np.inf)])
def test_rejects_malformed_policy_input_before_integrating(bad):
 r=runtime()
 with pytest.raises(ValueError):r.step(bad)
 assert r.physics_integrations==0 and r.data.time==0


def test_one_tick_is_one_integrated_feedback_update():
 r=runtime()
 for tick in range(25):
  obs,info=r.step(np.zeros(18))
  assert obs.shape==(65,) and np.isfinite(obs).all()
  assert info['physics_integrations']==info['controller_updates']==tick+1
  assert info['time_s']==pytest.approx((tick+1)*.02,abs=1e-12)
  assert info['auto_reset'] is False


def test_goal_observation_is_explicit_82_field_contract():
 r=runtime(skill='pickup');invalid=r.observations();assert invalid.shape==(82,) and invalid[-1]==0
 r.goal=TaskGoal('item',(.2,.1,.02),(1,0,0,0),(.4,-.1,.02));obs,_=r.step(np.zeros(18))
 assert obs.shape==(82,) and obs[-1]==1 and obs[75]==1


def test_unknown_candidate_or_modified_model_hash_is_rejected(tmp_path):
 c=json.loads(CONTRACT.read_text());c['candidate']='other_robot';p=tmp_path/'contract.json';p.write_text(json.dumps(c))
 with pytest.raises(ValueError,match='identity'):TaskProxyRuntime(MODEL,p)
 c['candidate']='goose_task_proxy_11_v1';c['model_sha256']='0'*64;p.write_text(json.dumps(c))
 with pytest.raises(ValueError,match='hash'):TaskProxyRuntime(MODEL,p)


def test_modified_collision_asset_is_rejected(tmp_path):
 import shutil
 for p in MODEL.parent.iterdir():
  if p.is_file():shutil.copy2(p,tmp_path/p.name)
 with (tmp_path/'torso_envelope.obj').open('a') as f:f.write('\n# changed\n')
 with pytest.raises(ValueError,match='asset identity'):TaskProxyRuntime(tmp_path/'robot.xml',CONTRACT)


def test_same_identity_cannot_silently_change_contact_method(tmp_path):
 c=json.loads(CONTRACT.read_text());c['contact_mapping']['method']='different';p=tmp_path/'contract.json';p.write_text(json.dumps(c))
 with pytest.raises(ValueError,match='contact mapping'):TaskProxyRuntime(MODEL,p)


def test_source_foundation_load_and_friction_fixture():
 # This invokes the exact production _integrate hook on a small independent
 # native fixture. It is not an analytical test duplicating only its formula.
 def probe(force):
  r=TaskProxyRuntime.__new__(TaskProxyRuntime)
  r.model=mujoco.MjModel.from_xml_string('''<mujoco><option timestep=".02" integrator="Euler" cone="elliptic"/><worldbody><geom name="floor" type="plane" size="1 1 .1" friction=".65 .01 .002"/><body pos="0 0 .012"><freejoint/><inertial pos="0 0 0" mass="5.215" diaginertia=".003 .003 .003"/><geom name="foot" type="box" size=".07 .04 .01" margin=".01" condim="3" friction=".65 .01 .002"/></body></worldbody></mujoco>''')
  r.data=mujoco.MjData(r.model);r.ground=r.model.geom('floor').id;r.foot_geoms={r.model.geom('foot').id};r.contract=json.loads(CONTRACT.read_text());r.contract['contact_mapping'].pop('ground_contact_quadrature',None)
  for tick in range(200):r.data.xfrc_applied[1,0]=force if tick>=100 else 0.;r._integrate()
  return .01-r.data.qpos[2],r.data.qvel[0]
 depth,velocity=probe(0.);assert depth==pytest.approx(5.215*9.81/140142.1824,abs=1e-5)
 assert abs(velocity)<1e-4
 assert abs(probe(10.)[1])<.01
 assert probe(50.)[1]>1.
