"""Bounded same-model reset contacts and 200-drive-tick cost; no task/policy."""
from pathlib import Path
import argparse,json,importlib.util,time
import numpy as np,mujoco


def main(a):
 p=a.package.resolve();s=importlib.util.spec_from_file_location('packaged',p/'runtime_adapter.py');mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod);env=mod.FrozenPhysics(p);m,d=env.model,env.data;cases=[]
 for x in[0,.15,.3,.5]:
  env.reset({'neck_pitch':x,'neck_mid_pitch':-x});rows=[]
  for c in d.contact:
   names=[m.geom(int(g)).name for g in c.geom]
   if c.dist<0:rows.append(dict(geoms=names,depth_mm=-float(c.dist)*1000,pos_m=c.pos.tolist(),owner_bodies=[m.body(int(m.geom_bodyid[g])).name for g in c.geom]))
  rows.sort(key=lambda r:-r['depth_mm']);cases.append(dict(neck_pitch=x,neck_mid_pitch=-x,contact_count=d.ncon,negative_contacts=len(rows),deepest=rows[:30],neck_body_pairs=[r for r in rows if any('neck'in x for x in r['owner_bodies'])and'torso'in r['owner_bodies']]))
 env.reset();start=time.perf_counter();error=None
 try:
  for _ in range(50):env.step(np.zeros(18))
 except Exception as e:error=repr(e)
 elapsed=time.perf_counter()-start;out=dict(schema='goose_actual_reset_contacts_and_bounded_step_cost_v1',cases=cases,controller_updates=env.controller_updates,policy_updates=env.policy_updates,physical_time_s=float(d.time),elapsed_wall_s=elapsed,mean_physics_step_ms=elapsed*1000/max(env.controller_updates*env.substeps,1),warnings=[int(w.number)for w in d.warning],finite_state=all(np.isfinite(getattr(d,k)).all()for k in['qpos','qvel','qacc']),exception=error,no_task_reward_or_external_support=True);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(report=str(a.output),cases=[dict(q=x['neck_pitch'],ncon=x['contact_count'],negative=x['negative_contacts'],neckbody=len(x['neck_body_pairs']))for x in cases],cost_ms=out['mean_physics_step_ms'],warnings=out['warnings'],exception=error)))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
