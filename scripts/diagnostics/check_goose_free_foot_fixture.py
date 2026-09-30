"""Unconstrained single-foot stand-in; this is not a whole biped model."""
from pathlib import Path
import json, hashlib,sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/diagnostics'))
from check_goose_compliant_foot import fixture

def main():
    paths=[R/'cad/exports/compliant_foot/manifest.json',R/'evidence/manufacturing_component_parameters.json',R/'evidence/manufacturing_compliant_foot.json']
    feet,parameters,old=[json.loads(p.read_text()) for p in paths]
    centers=np.array(feet['feet'][0]['pad_centers_world_xy_mm'])/1000;centers[:,1]+=.089
    k=old['elementary_nominal_leaf_stiffness_n_mm']*1000
    results=[]
    for factor in [.5,1.]:
        for fraction in [.5,1.]:
            normal=(parameters['nominal_conditional_mass_kg']+.05)*9.81*fraction
            for cop in [(-.03,0.),(.07,0.),(0.,.012)]:
                for terrain,heights in [('flat',np.zeros(6)),('one_mm_checker',np.array([-.0005,.0005]*3))]:
                    result=fixture(centers,k*factor,normal,heights,guided=False,cop_xy=cop)
                    result.update(stiffness_multiplier=factor,load_fraction=fraction,terrain=terrain)
                    results.append(result)
    refined=[]
    for failed in [p for p in results if not p['fixture_pass']]:
        for dt in [.00005,.000025]:
            r=fixture(centers,k*failed['stiffness_multiplier'],failed['applied_normal_n'],np.array(failed['terrain_heights_mm'])/1000,
                guided=False,cop_xy=failed['imposed_mass_com_xy_m'],timestep=dt)
            r.update(terrain=failed['terrain'],load_fraction=failed['load_fraction'],stiffness_multiplier=failed['stiffness_multiplier'])
            refined.append(r)
    out=dict(schema='goose_free_foot_fixture_v1',results=results,case_count=len(results),free_fixture_pass=all(p['fixture_pass'] for p in results),
        failed_case_timestep_refinements=refined,
        terrain_walk_pass=False,manufacturing_pass=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__),ROOT/'scripts/diagnostics/check_goose_compliant_foot.py']},
        limitations=['Single free six-DOF foot under a point-like load with assumed0.03kgm2 inertia and COM60mm above plate, not the actual whole-robot mass distribution',
            'Three COM offsets and two terrain profiles are sampled; no whole gait, grasp, drag or contact-matched sim2sim proof',
            'TPU stiffness, friction0.65, virtual1g moving pad inertia,1.5mm travel stops and damping remain uncalibrated idealizations',
            'Pass requires six seconds without solver warning/reset, final speed below1e-4,2% normal balance and less than5deg tilt; this is a selected fixture criterion, not hardware acceptance'])
    (R/'evidence/manufacturing_free_foot_fixture.json').write_text(json.dumps(out,indent=2)+'\n')
    print({k:out[k] for k in ['case_count','free_fixture_pass','terrain_walk_pass']})
    print([{k:p[k] for k in ['load_fraction','imposed_mass_com_xy_m','terrain','stiffness_multiplier','final_tilt_rad','fixture_pass','final_max_generalized_speed']} for p in results if not p['fixture_pass']])
    print('Refinements',[(p['terrain'],p['timestep_s'],p['fixture_pass'],p['final_tilt_rad']) for p in refined])
    return 0 if out['free_fixture_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
