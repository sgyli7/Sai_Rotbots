"""Physical/contract regression gates for the separate 18-axis candidate."""
import json
from pathlib import Path
import numpy as np
import mujoco
import pytest
from sai_agent.goose.stage_one import StageOneEnv
from sai_agent.goose.stage_one_gravity import NominalNeckGravity
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'robots/Goose_V0.1'

@pytest.fixture(params=['stage_one','stage_two'])
def baseline(request):
 return (R/'models'/request.param/'robot.xml', R/'configs'/f'{request.param}_contract.json', request.param)

def test_free_root_mass_and_positive_physical_inertias(baseline):
 MODEL,CONTRACT,stage=baseline
 c=json.loads(CONTRACT.read_text());m=mujoco.MjModel.from_xml_path(str(MODEL))
 assert (m.nq,m.nv,m.nu)==(25,24,18)
 assert m.jnt_type[0]==mujoco.mjtJoint.mjJNT_FREE
 assert m.body_mass.sum()==pytest.approx(c['nominal_robot_mass_kg'],abs=1e-10)
 for b in c['bodies']:
  eigen=np.linalg.eigvalsh(b['inertia_at_com_body_kg_m2']);assert min(eigen)>0;assert eigen[2]<=eigen[0]+eigen[1]+1e-12
 for j in c['joints']:
  k=m.joint(j['name']).id;assert m.dof_armature[m.jnt_dofadr[k]]==pytest.approx(j['armature_kg_m2'])

def test_urdf_and_mjcf_share_kinematics_mass_and_com(baseline):
 MODEL,CONTRACT,stage=baseline
 a=mujoco.MjModel.from_xml_path(str(MODEL));b=mujoco.MjModel.from_xml_path(str(MODEL.with_suffix('.urdf')));da=mujoco.MjData(a);db=mujoco.MjData(b);rng=np.random.default_rng(613)
 c=json.loads(CONTRACT.read_text());assert (b.nq,b.nv)==(25,24)
 for k in range(12):
  root=np.r_[rng.normal(0,.1,3),rng.normal(size=4)];root[3:]/=np.linalg.norm(root[3:]);da.qpos[:7]=db.qpos[:7]=root
  for j in c['joints']:
   q=rng.uniform(*j['range_rad']);da.qpos[a.joint(j['name']).qposadr]=q;db.qpos[b.joint(j['name']).qposadr]=q
  mujoco.mj_forward(a,da);mujoco.mj_forward(b,db)
  for body in c['bodies']:
   ia,ib=a.body(body['name']).id,b.body(body['name']).id
   np.testing.assert_allclose(da.xpos[ia],db.xpos[ib],atol=1e-10)
   np.testing.assert_allclose(da.xipos[ia],db.xipos[ib],atol=1e-10)
   np.testing.assert_allclose(da.xmat[ia],db.xmat[ib],atol=1e-10)
   assert a.body_mass[ia]==pytest.approx(b.body_mass[ib],abs=1e-12)

def test_free_fall_has_no_hidden_root_support(baseline):
 MODEL,CONTRACT,stage=baseline
 m=mujoco.MjModel.from_xml_path(str(MODEL));d=mujoco.MjData(m);d.qpos[2]+=1.;mujoco.mj_forward(m,d)
 mujoco.mj_step(m,d,nstep=20);mujoco.mj_forward(m,d);mujoco.mj_subtreeVel(m,d)
 assert d.ncon==0
 np.testing.assert_allclose(d.subtree_linvel[m.body('torso').id],[0,0,-9.81*.02],atol=3e-5)

def test_engine_neutral_neck_gravity_matches_independent_mujoco(baseline):
 MODEL,CONTRACT,stage=baseline
 c=json.loads(CONTRACT.read_text());f=NominalNeckGravity(c);m=mujoco.MjModel.from_xml_path(str(MODEL));d=mujoco.MjData(m);rng=np.random.default_rng(718)
 for k in range(30):
  d.qpos[3:7]=rng.normal(size=4);d.qpos[3:7]/=np.linalg.norm(d.qpos[3:7]);d.qpos[7:]=rng.uniform(-.6,.6,18);mujoco.mj_forward(m,d)
  np.testing.assert_allclose(f(d.qpos[7:13],d.qpos[3:7]),d.qfrc_bias[6:11],atol=1e-10)

def test_action_map_reaches_all_screened_poses(baseline):
 MODEL,CONTRACT,stage=baseline
 c=json.loads(CONTRACT.read_text());cases=json.loads((R/'evidence'/f'{stage}_system_gate.json').read_text())['pose_geometry']
 for pose in cases:
  for j in c['joints']:
   q=pose['joint_q_rad'][j['name']];a=q/j['action_scale_rad'];assert abs(a)<=1+1e-12
   assert j['range_rad'][0]<=q<=j['range_rad'][1]

def test_parameter_runtime_finite_and_nominal_feedforward_is_not_randomized(baseline):
 MODEL,CONTRACT,stage=baseline
 e=StageOneEnv(MODEL,CONTRACT,2,seed=215,commands=False);reference=NominalNeckGravity(e.contract)
 assert not np.array_equal(e.models[0].body_mass,e.models[1].body_mass)
 for _ in range(8):
  obs,reward,done,rows=e.step(np.zeros((2,18)))
  assert obs.shape==(2,65) and np.isfinite(obs).all() and np.isfinite(reward).all()
  assert (abs(e.last_tau)<=e.peak+1e-10).all()
 np.testing.assert_allclose(e.gravity(np.zeros(6),[1,0,0,0]),reference(np.zeros(6),[1,0,0,0]),atol=1e-12)

def test_contract_rejects_asset_mismatch(tmp_path, baseline):
 MODEL,CONTRACT,stage=baseline
 c=json.loads(CONTRACT.read_text());key=next(iter(c['asset_sha256']));c['asset_sha256'][key]='0'*64;p=tmp_path/'bad.json';p.write_text(json.dumps(c))
 with pytest.raises(ValueError,match='Asset/contract hash mismatch'):StageOneEnv(MODEL,p,1)


def test_contract_rejects_mass_redistribution_even_when_total_is_unchanged(tmp_path, baseline):
 MODEL,CONTRACT,stage=baseline
 c=json.loads(CONTRACT.read_text());c['bodies'][0]['mass_kg']+=.01;c['bodies'][1]['mass_kg']-=.01;p=tmp_path/'inconsistent.json';p.write_text(json.dumps(c))
 with pytest.raises(ValueError,match='Body inertia/contract mismatch'):StageOneEnv(MODEL,p,1)
