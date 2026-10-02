"""Compare robot contracts without treating matching total mass as compatibility."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def compare(base,candidate):
    changes=[];budget=[]
    if base['joint_order']!=candidate['joint_order']:changes.append('joint_order')
    for key in ('coordinates','root_origin_at_zero_m','physics_dt_s','torque_dt_s','policy_dt_s','observation_size','action_size','observation_layout','action_semantics','gravity_feedforward_joints','positive_mechanical_power_limit_w','phase_frequency_hz','foot_friction_range','latency_policy_steps','strength_multiplier_range','collision_exclusions','beak_transmission'):
        if base.get(key)!=candidate.get(key):changes.append(key)
    # Contact geometry changes require a new baseline even if total mass matches.
    def contacts(c):
        return [g for g in c.get('collision_geometries',[]) if int(g.get('contype',1)) or int(g.get('conaffinity',1))]
    if contacts(base)!=contacts(candidate):changes.append('collision_geometries')
    # Asset hash changes are deliberately conservative: compatibility review is
    # required even if a changed mesh later proves to be purely visual.
    if base.get('asset_sha256')!=candidate.get('asset_sha256'):changes.append('asset_sha256')
    oldj={j['name']:j for j in base['joints']}
    changes.extend('removed_joint.'+n for n in oldj if n not in {j['name'] for j in candidate['joints']})
    critical=('parent','pivot_world_at_zero_m','axis_parent','range_rad','actuator','armature_kg_m2','torque_peak_limit_nm','continuous_design_limit_nm','kp_nm_rad','kd_nm_s_rad','q_neutral_rad','action_scale_rad','speed_limit_rad_s','frictionloss_nm','damping_nm_s_rad')
    for j in candidate['joints']:
        for key in critical:
            if j['name'] not in oldj or oldj[j['name']].get(key)!=j.get(key):changes.append(j['name']+'.'+key)
    oldb={b['name']:b for b in base['bodies']}
    changes.extend('removed_body.'+n for n in oldb if n not in {b['name'] for b in candidate['bodies']})
    for b in candidate['bodies']:
        if b['name'] not in oldb:changes.append('added_body.'+b['name']);continue
        a=oldb[b['name']];dm=b['mass_kg']-a['mass_kg'];dc=np.array(b['com_local_m'])-a['com_local_m'];I=np.array(b['inertia_at_com_body_kg_m2']);J=np.array(a['inertia_at_com_body_kg_m2'])
        # Generalized eigenvalues bound every possible rotation-axis quadratic form.
        L=np.linalg.cholesky(J);normalized=np.linalg.solve(L,I)@np.linalg.inv(L.T);ev=np.linalg.eigvalsh(normalized)
        mass_ok=abs(dm)<=a['mass_kg']*a['mass_relative_design_uncertainty'];com_ok=max(abs(dc))<=a['com_randomization_m'];lo,hi=a['inertia_multiplier_range'];inertia_ok=min(ev)>=lo and max(ev)<=hi
        budget.append(dict(body=b['name'],mass_delta_kg=dm,com_delta_m=dc.tolist(),inertia_quadratic_form_ratios=ev.tolist(),inside_old_mass_budget=bool(mass_ok),inside_old_com_budget=bool(com_ok),inside_old_inertia_budget=bool(inertia_ok)))
    exceeded=[b['body'] for b in budget if not(b['inside_old_mass_budget'] and b['inside_old_com_budget'] and b['inside_old_inertia_budget'])]
    return dict(base_schema=base['schema'],candidate_schema=candidate['schema'],nominal_mass_delta_kg=candidate['nominal_robot_mass_kg']-base['nominal_robot_mass_kg'],critical_contract_changes=changes,body_comparisons=budget,bodies_outside_old_budget=exceeded,requires_new_training_version=bool(changes or exceeded),policy_reuse_approved=False,note='Parameter envelope membership is necessary, not sufficient for policy transfer; final dynamics and real calibration remain required.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=compare(json.loads(a.base.read_text()),json.loads(a.candidate.read_text()));r['base_sha256']=hashlib.sha256(a.base.read_bytes()).hexdigest();r['candidate_sha256']=hashlib.sha256(a.candidate.read_bytes()).hexdigest();a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('nominal_mass_delta_kg','critical_contract_changes','bodies_outside_old_budget','requires_new_training_version')},indent=2))
if __name__=='__main__':main()
