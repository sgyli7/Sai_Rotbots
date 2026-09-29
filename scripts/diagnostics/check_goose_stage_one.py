"""System-level first-stage gates, without converting failures into acceptance."""
from pathlib import Path
import sys,json,hashlib,argparse
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_one import candidate,make_contract,R

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['stage_one','stage_two'],default='stage_one');stage=parser.parse_args().stage
 if stage=='stage_two':
  from build_goose_stage_two import candidate as choose
 else:choose=candidate
 s=choose();contract=json.loads((R/'configs'/f'{stage}_contract.json').read_text());s.pivots['torso']=np.zeros(3)
 cases=[]
 for drop in (0,40,60,80):
  q,r,rot=s.pose(drop);cases.append((f'crouch_{drop}',q,r,rot,['right','left']))
 q,r,rot=s.pose(60,neck=True);cases.append(('low_reach',q,r,rot,['right','left']))
 for side in ('right','left'):
  q,r,rot=s.pose();q,r,rot=s.bank(side,q,r);cases.append((side+'_single_support',q,r,rot,[side]))
 # Same 50g held object as the prior screen; payload not hidden in robot mass.
 s.items.append(dict(name='payload',body='head_roll',mass_kg=.05,center_m=s.grip.tolist(),relative_uncertainty=0))
 results=[];geometry=[];dynamic=mujoco.MjModel.from_xml_path(str(R/'models'/stage/'robot.xml'))
 for name,q,root,rot,sides in cases:
  d=mujoco.MjData(dynamic);d.qpos[:3]=root+rot@np.array([0,0,.29]);from scipy.spatial.transform import Rotation
  d.qpos[3:7]=Rotation.from_matrix(rot).as_quat()[[3,0,1,2]]
  for n,v in q.items():d.qpos[dynamic.joint(n).qposadr]=v
  mujoco.mj_forward(dynamic,d)
  penetration=[dict(a=dynamic.geom(int(c.geom1)).name,b=dynamic.geom(int(c.geom2)).name,depth_m=-float(c.dist)) for c in d.contact if c.dist<-.0005]
  limits=[n for n,v in q.items() if not dynamic.jnt_range[dynamic.joint(n).id,0]<=v<=dynamic.jnt_range[dynamic.joint(n).id,1]]
  geometry.append(dict(name=name,joint_q_rad=q,root_qpos=d.qpos[:7].tolist(),collisions=penetration,joint_limit_violations=limits,pass_coarse_geometry=not penetration and not limits))
 for scale in (-1,0,1):
  model,xml=s.model(scale)
  for name,q,root,rot,sides in cases:
   for drag in (-2,0,2):
    result=s.evaluate(name,q,root,rot,sides,scale,drag,model)
    result['screening_capacity_nm']={j['name']:j['continuous_design_limit_nm'] for j in contract['joints']}
    result['capacity_basis']=stage+' continuous design limits; not a thermal certification'
    results.append(result)
 summary={}
 for j in contract['joints']:
  worst=max(results,key=lambda r:abs(r['joint_torque_nm'][j['name']]));demand=abs(worst['joint_torque_nm'][j['name']]);summary[j['name']]=dict(worst_static_nm=demand,case=worst['name'],continuous_design_limit_nm=j['continuous_design_limit_nm'],training_peak_limit_nm=j['torque_peak_limit_nm'],below_continuous_design_limit=demand<=j['continuous_design_limit_nm'],below_training_peak=demand<=j['torque_peak_limit_nm'])
 mass=sum(i['mass_kg'] for i in s.items)-.05;unc=sum(i['mass_kg']*i['relative_uncertainty'] for i in s.items)
 inertia_checks=[]
 for b in contract['bodies']:
  eig=np.linalg.eigvalsh(b['inertia_at_com_body_kg_m2']);inertia_checks.append(dict(body=b['name'],eigenvalues=eig.tolist(),positive=bool(min(eig)>0),triangle_inequality=bool(eig[2]<=eig[0]+eig[1]+1e-12)))
 report=dict(status='SYSTEM_GATE_RESULTS_NOT_MANUFACTURING_ACCEPTANCE',model_sha256=contract['model_sha256'],contract_sha256=hashlib.sha256((R/'configs'/f'{stage}_contract.json').read_bytes()).hexdigest(),nominal_mass_kg=mass,correlated_mass_assumption_interval_kg=[mass-unc,mass+unc],static_cases=len(results),contact_feasible=sum(r['static_contact_feasible'] for r in results),joint_summary=summary,pose_geometry=geometry,inertia_checks=inertia_checks,results=results,limitations=['Catalog cases are centered on shaft pivots provisionally, not supplier STEP installation geometry','Collision checks use declared primitives and intentional internal assembly exclusions; detailed fastening/harness interference remains open','Static inverse dynamics does not prove sustained walking power or thermal performance','50N bite input is a load case, not demonstrated grip force','Candidate body frame and motor upgrade require hardware fit review before claiming freeze'])
 (R/'evidence'/f'{stage}_system_gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['nominal_mass_kg','correlated_mass_assumption_interval_kg','static_cases','contact_feasible','joint_summary','pose_geometry']},indent=2))
if __name__=='__main__':main()
