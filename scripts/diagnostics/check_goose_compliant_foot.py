"""Independent native fit and guided MuJoCo compression tests for soft soles.

Guided press fixtures validate spring/contact wiring, not robot stability or
material performance. Actual printed force curves and traction remain tests.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import mujoco
from build123d import import_step

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from build_goose_cad import cylinder


def fixture(centers,k,normal_n,heights):
    half=.00075; mass_per_pad=.001
    xs=''.join(f'<geom type="box" pos="{x} {y} {h/2-.01}" size=".015 .016 {h/2+.01}" friction=".65 .01 .002"/>' for (x,y),h in zip(centers,heights))
    pads=''.join(f'''<body name="pad{i}" pos="{x} {y} -.00245">
      <joint name="leaf{i}" type="slide" axis="0 0 1" range="0 .0015" stiffness="{k}" damping="2" springref="0" solreflimit=".003 1"/>
      <inertial mass="{mass_per_pad}" pos="0 0 0" diaginertia="1e-8 1e-8 1e-8"/>
      <geom name="contact{i}" type="box" size=".0025 .012 {half}" friction=".65 .01 .002"/>
      </body>''' for i,(x,y) in enumerate(centers))
    # Only vertical root motion is allowed: all fixture moments are reacted by
    # the guide. This deliberately cannot be counted as free-foot balance.
    xml=f'''<mujoco><compiler angle="radian" inertiafromgeom="false"/>
      <option timestep=".0001" gravity="0 0 -9.81" integrator="implicitfast" iterations="100"/>
      <default><geom solref=".003 1" solimp=".95 .99 .001"/></default>
      <worldbody>{xs}<body name="press" pos="0 0 .0082">
      <joint name="guide" type="slide" axis="0 0 1" limited="false" damping="4"/>
      <inertial mass="{normal_n/9.81-len(centers)*mass_per_pad}" pos="0 0 .06" diaginertia=".03 .03 .03"/>
      {pads}</body></worldbody></mujoco>'''
    model=mujoco.MjModel.from_xml_string(xml);data=mujoco.MjData(model)
    for _ in range(60000):mujoco.mj_step(model,data)
    compressions=np.array([data.qpos[model.joint('leaf'+str(i)).qposadr[0]] for i in range(len(centers))])
    contact_normal=0.
    for i in range(data.ncon):
        f=np.zeros(6);mujoco.mj_contactForce(model,data,i,f);contact_normal+=f[0]
    finite=bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all())
    warnings=[int(x.number) for x in data.warning]
    return dict(applied_normal_n=normal_n,terrain_heights_mm=(np.array(heights)*1000).tolist(),
        stiffness_n_per_m=k,compression_mm=(compressions*1000).tolist(),
        peak_speed_m_s=float(abs(data.qvel).max()),summed_contact_normal_n=float(contact_normal),
        normal_balance_relative_error=abs(contact_normal-normal_n)/normal_n,
        bottom_out_count=int((compressions>=.00149).sum()),finite=finite,warning_counts=warnings,simulated_seconds=float(data.time),
        fixture_pass=bool(finite and not any(warnings) and data.time>5.999 and abs(data.qvel).max()<1e-4 and abs(contact_normal-normal_n)<normal_n*.02))


def main():
    path=R/'cad/exports/compliant_foot/manifest.json';m=json.loads(path.read_text());shapes={};native=[]
    for p in m['parts']:
        for meta in p['files'].values():assert hashlib.sha256((R/meta['path']).read_bytes()).hexdigest()==meta['sha256']
        shape=import_step(R/p['files']['step']['path']);assert shape.is_valid and len(shape.solids())==1
        shapes[p['name']]=shape
    for f in m['feet']:
        sole=shapes[f['side']+'_flexible_sole'];plate=shapes[f['side']+'_tapped_load_plate']
        intersection=sole&plate;v=sum(x.volume for x in intersection.solids()) if intersection is not None else 0.
        tests=[]
        for point in f['fastener_positions_mm']:
            # Both bores are probed along their actual shared manufacturing axes.
            for part,d in [(sole,3.2),(plate,2.5)]:
                q=part&cylinder(d*.499,12,point,'z');iv=sum(s.volume for s in q.solids()) if q is not None else 0.
                tests.append(iv<.01)
        native.append(dict(side=f['side'],sole_plate_overlap_mm3=v,all_eight_bore_probes_clear=all(tests),pass_fit=v<.01 and all(tests)))
    f=m['feet'][0];E=m['material_data']['youngs_modulus_z_mpa']
    L=f['leaf_span_mm'];b=f['leaf_width_mm'];t=f['leaf_thickness_mm']
    I=b*t**3/12
    k=192*E*I/L**3 # fixed-fixed center load, N/mm
    centers=np.array(f['pad_centers_world_xy_mm'])/1000;centers[:,1]+=.089
    results=[]
    for factor in [.5,1.,2.]:
        for normal in [43.4265,86.853,125.,175.]:
            for name,heights in [('flat',np.zeros(6)),('one_mm_checker',np.array([-.0005,.0005]*3))]:
                r=fixture(centers,k*1000*factor,normal,heights);r.update(profile=name,stiffness_multiplier=factor)
                r['elementary_flat_deflection_mm']=normal/(6*k*factor)
                r['nominal_leaf_surface_strain_estimate']=12*t*min(r['elementary_flat_deflection_mm'],1.5)/L**2
                results.append(r)
    # Existing completely solid thin-sole claim would deform very little under
    # broad uniform contact. This is a deliberately unconfined small-strain bound.
    full_area=13600.;old_thickness=3.;old_compression=125*old_thickness/(E*full_area)
    report=dict(schema='goose_soft_foot_gate_v1',manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        native_fit=native,partial_native_fit_pass=all(x['pass_fit'] for x in native),
        elementary_nominal_leaf_stiffness_n_mm=k,elementary_total_foot_stiffness_n_mm=6*k,
        broad_dense_3mm_sole_125n_compression_mm=old_compression,
        guided_fixture_results=results,guided_fixture_pass=all(x['fixture_pass'] for x in results),
        printed_material_pass=False,terrain_walk_pass=False,manufacturing_pass=False,old_stage_two_model_modified=False,
        requested_design_scope='replaceable elastic tread with1.5mm geometric travel; first terrain target1mm local height variation and ankle-aligned shallow slopes, not stairs or arbitrary debris',
        limitations=['Youngs modulus from tensile coupons substitutes for unknown printed flexural response; large-strain stretching, hysteresis and fatigue require a printed coupon',
            'Stiffness multipliers0.5/1/2 are sensitivity scenarios, not a statistical or manufacturer tolerance',
            'MuJoCo tests a guided compression fixture with1.5mm travel limits and assumed contact friction; fixture guide reacts all moments and prevents falling',
            'Bottomed-out fixtures can balance load but no longer provide the same compliant travel; they are explicitly counted',
            'No free biped, manipulation, traction, obstacle traversal or cross-engine success is inferred',
            'New contact outline is smaller than old full-foot hull; new version and support/CoP checks are required'])
    out=R/'evidence/manufacturing_compliant_foot.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['partial_native_fit_pass','guided_fixture_pass','elementary_nominal_leaf_stiffness_n_mm','broad_dense_3mm_sole_125n_compression_mm']},indent=2))
    return 0 if report['partial_native_fit_pass'] and report['guided_fixture_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
