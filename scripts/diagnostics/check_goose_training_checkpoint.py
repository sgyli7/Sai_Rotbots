"""Bounded same-version model loading, SI boundary and finite physics smoke.

No optimizer steps; failing dynamics are reported without claiming acceptance.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
import mujoco
from sai_agent.goose.stage_one import StageOneEnv
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--steps',type=int,default=10);ap.add_argument('--output',type=Path,default=R/'evidence/training_checkpoint_entry.json');a=ap.parse_args()
    if not 1<=a.steps<=100:raise ValueError('bounded smoke steps1..100')
    cp=R/'configs/training_checkpoint_contract.json';mp=R/'models/training_checkpoint/robot.xml';c=json.loads(cp.read_text())
    for p,h in c['source_hashes'].items():
        if sha(ROOT/p)!=h:raise ValueError(('stale input',p))
    started=time.monotonic();env=StageOneEnv(mp,cp,1,29,randomize=False,commands=False,auto_reset=False)
    m,d=env.models[0],env.data[0];obs=env.observations();initial=[]
    for co in d.contact:
        names=[m.geom(int(g)).name for g in co.geom]
        if 'ground' not in names and co.dist<-.0002:initial.append(dict(geoms=names,penetration_m=float(-co.dist)))
    np.testing.assert_allclose(m.body_mass.sum(),10.430762602736852,atol=1e-10,rtol=0)
    rows=[];warnings=[]
    for k in range(a.steps):
        obs,reward,done,info=env.step(np.zeros((1,18)))
        rows.append(dict(step=k+1,simulated_s=float(d.time),finite=bool(np.isfinite(obs).all() and np.isfinite(reward).all() and np.isfinite(d.qpos).all()),done=bool(done[0]),**info[0]))
        warnings=[int(w.number) for w in d.warning]
        if any(warnings) or done[0] or time.monotonic()-started>90:break
    finite=all(p['finite'] for p in rows) and not any(warnings)
    c['training_entry_verified']=finite
    c['training_validation_scope']='model_loading_full_si_boundary_0.2s_nominal_smoke_no_policy_acceptance'
    cp.write_text(json.dumps(c,indent=2)+'\n')
    report=dict(schema='goose_training_checkpoint_entry_v1',model_sha256=sha(mp),contract_sha256=sha(cp),source_scene_sha256=c['source_scene_sha256'],source_parts=c['source_part_count'],nominal_mass_kg=float(m.body_mass.sum()),nq=int(m.nq),nv=int(m.nv),nu=int(m.nu),runtime_rigid_bodies=int(m.nbody-1),observation_size=obs.shape[1],action_size=18,root_free=True,external_root_force=False,initial_self_contact_candidates=initial,initial_self_contact_candidate_count=len(initial),steps=rows,solver_warning_counts=warnings,simulated_s=float(d.time),elapsed_s=time.monotonic()-started,model_loading_pass=True,si_boundary_pass=True,finite_smoke_pass=finite,stance_smoke_pass=bool(finite and len(rows)==a.steps and not rows[-1]['done'] and not initial),walking_pass=False,turning_pass=False,grasp_drag_pass=False,manufacturing_release=False,hardware_freeze=False,optimizer_steps=0,versions=dict(mujoco=mujoco.__version__,numpy=np.__version__))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['steps','initial_self_contact_candidates']},indent=2))
    return 0 if finite else 1
if __name__=='__main__':raise SystemExit(main())
