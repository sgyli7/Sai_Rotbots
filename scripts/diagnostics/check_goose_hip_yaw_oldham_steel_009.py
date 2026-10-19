"""Two-mesh, unchanged-native Oldham H900 steel screening; never updates runtime.

Reuse immutable original Gmsh meshes/loads/supports. Only homogeneous elastic
material changes. The bilateral flank model is explicitly not a wear, fatigue,
impact, nonlinear contact, or manufacturing qualification.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, resource, subprocess, time
import numpy as np

W = Path(__file__).resolve().parents[2]
BASE = W / 'artifacts/goose_v0_2/tangpa_mango_ankle_integration_34/whole_stage_01/mango_primary_form_reset_01/whole_body_architecture_05'
OLD = BASE / 'upper_short_yaw_delivery_47_oldham_fe_04'
APP = Path('/home/ethan/.local/opt/freecad_1_1_4_aarch64/squashfs-root/AppRun')

def identity(p):
    return {'path': str(p.resolve()), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def bounded_child():
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))

def inp_domains(p):
    nodes, upper, loads = {}, [], {}
    mode = None
    for ln in p.open():
        s=ln.strip()
        if s.startswith('*'):
            u=s.upper()
            mode = 'node' if u=='*NODE' else 'upper' if u=='*NSET,NSET=UPPER_NORMAL' else 'load' if u=='*CLOAD' else None
            continue
        if mode=='node':
            a=s.split(',');nodes[int(a[0])]=np.array(list(map(float,a[1:])))
        elif mode=='upper': upper.extend(map(int,s.split(',')))
        elif mode=='load':
            a=s.split(',');assert int(a[1])==2;loads[int(a[0])]=float(a[2])
    return nodes, upper, loads

def run(out, reuse_coarse=None, fine_solver=None):
    assert not out.exists(), 'Independent revisions never overwrite runs'
    out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('oldham_original_reader',W/'scripts/diagnostics/check_goose_oldham_actual_fe_screen.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    old=json.loads((OLD/'actual_oldham_fe_screen.json').read_text())
    report={
      'schema':'goose_hip_yaw_oldham_17_4ph_h900_two_mesh_screen_009_c01',
      'status':'RUNNING','source_script':identity(Path(__file__)),
      'original_screen':identity(OLD/'actual_oldham_fe_screen.json'),
      'geometry':old['source'],'boundary':old['boundary'],
      'material':{'name':'wrought UNS S17400 / 17-4PH Condition H900',
         'E_MPa':197000.,'poisson':.272,'density_kg_m3':7800.,
         'procurement_required_minimum_yield_MPa':1170.,
         'yield_design_safety_factor':2.,'allowable_static_MPa':585.,
         'property_sources':[
          'https://www.carpentertechnology.com/hubfs/7407324/Material%20Saftey%20Data%20Sheets/Custom%20630%20%2817-4%20PH%29.pdf',
          'https://www.atimaterials.com/Products/Documents/datasheets/stainless-specialty-steel/precipitationhardening/ati_17-4_tds_en_v2.pdf'],
         'actual_mill_certificate_received':False},
      'applied_torque_Nm':2.,'physics_steps':0,'runtime_modified':False,
      'fatigue_wear_impact_manufacturing_released':False,'cases':[]}
    rp=out/'two_mesh_screen.json';start=time.monotonic()
    def save():
        report['elapsed_s']=time.monotonic()-start
        rp.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
      sizes=[.45,.3]
      if reuse_coarse:
        reused=json.loads(reuse_coarse.read_text())
        row=next(c for c in reused['cases'] if c['mesh_size_mm']==.45)
        assert row['status']=='SOLVED_CONDITIONAL_STATIC_ONLY'
        assert reused['material']==report['material']
        report['cases'].append(row)
        report['reused_completed_coarse_report']=identity(reuse_coarse)
        report['previous_fine_direct_memory_failure_preserved']=True
        sizes=[.3]
      for size in sizes:
        oldcase=next(c for c in old['cases'] if c['nominal_mesh_size_mm']==size)
        src=OLD/f"mesh_{str(size).replace('.','p')}"/'actual_oldham.inp'
        assert identity(src)['sha256']==oldcase['input']['sha256']
        case=out/f"mesh_{str(size).replace('.','p')}";case.mkdir()
        text=src.read_text();assert text.count('170000.,0.28')==1
        text=text.replace('FCD400_ASSUMED_E','S17400_H900').replace('170000.,0.28','197000.,0.272').replace('ACTUAL FCD400 DISC - CONDITIONAL ELASTIC CONTACT SCREEN','UNCHANGED ACTUAL OLDHAM H900 - CONDITIONAL 2NM ELASTIC SCREEN')
        if size==.3 and fine_solver:
            assert fine_solver=='ITERATIVE CHOLESKY'
            text=text.replace('*STATIC\n','*STATIC,SOLVER=ITERATIVE CHOLESKY\n')
        inp=case/'oldham_h900.inp';inp.write_text(text)
        row={'mesh_size_mm':size,'status':'SOLVING','input':identity(inp),'original_input':identity(src),
          'mesh_reused_exact':oldcase['mesh'],'nodes':oldcase['nodes'],'linear_tetrahedra':oldcase['linear_tetrahedra'],
          'applied_torque_Z_Nmm':oldcase['applied_torque_Z_Nmm'],
          'contact_area_per_flank_mm2':oldcase['contact_area_per_flank_mm2'],
          'force_per_flank_N':oldcase['force_per_flank_N'],'mean_pressure_per_flank_MPa':oldcase['mean_pressure_per_flank_MPa'],
          'linear_solver':fine_solver if size==.3 and fine_solver else 'default_SPOOLES'}
        report['cases'].append(row);save();print(json.dumps({'event':'solve_start','size':size}),flush=True)
        env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBER_OF_CPUS='1')
        t=time.monotonic()
        with (case/'solver.log').open('w') as f:
            cp=subprocess.run(['/usr/bin/time','-v',str(APP),'ccx','-i','oldham_h900'],cwd=case,stdout=f,stderr=subprocess.STDOUT,env=env,preexec_fn=bounded_child,timeout=300)
        row['solve_wall_s']=time.monotonic()-t
        row['solver_return_code']=cp.returncode
        log=(case/'solver.log').read_text()
        assert cp.returncode==0 and 'Job finished' in log,log[-2000:]
        nodes,upper,loads=inp_domains(inp)
        u,rf,s=reader.read_dat(case/'oldham_h900.dat')
        assert len(u)==row['nodes'] and len(s)==row['linear_tetrahedra']
        ss=s[:,1:];vm=np.sqrt(.5*((ss[:,0]-ss[:,1])**2+(ss[:,1]-ss[:,2])**2+(ss[:,2]-ss[:,0])**2)+3*(ss[:,3:]**2).sum(1))
        R=sum((np.array(v) for v in rf.values()),np.zeros(3));M=sum((np.cross(nodes[n],v) for n,v in rf.items()),np.zeros(3))
        tensile=sum(abs(rf[n][0]) for n in upper if rf[n][0]*nodes[n][1]<0)
        rfabs=sum(abs(rf[n][0]) for n in upper)
        peak=int(np.argmax(vm));elem=int(s[peak,0])
        row.update(status='SOLVED_CONDITIONAL_STATIC_ONLY',
          max_displacement_mm=max(np.linalg.norm(v) for v in u.values()),
          strain_energy_Nmm=.5*sum(loads[n]*u[n][1] for n in loads),
          von_mises_MPa={'max':float(vm.max()),'p95':float(np.percentile(vm,95)),'p99':float(np.percentile(vm,99))},
          max_vm_element=elem,nominal_yield_safety_factor=1170./float(vm.max()),
          reaction_sum_N=R.tolist(),reaction_moment_Nmm=M.tolist(),
          torque_balance_relative_error=abs(M[2]+2000.)/2000.,
          force_balance_N=float(np.linalg.norm(R+np.array([0.,sum(loads.values()),0.]))),
          tensile_normal_reaction_fraction=tensile/rfabs,
          results_dat=identity(case/'oldham_h900.dat'),results_frd=identity(case/'oldham_h900.frd'))
        del nodes,u,rf,s,ss,vm
        save();print(json.dumps({'event':'solve_done','case':row}),flush=True)
      a,b=report['cases'];peak=b['von_mises_MPa']['max']
      report['two_mesh_relative_change_vs_finer']={
        'peak_vm':abs(b['von_mises_MPa']['max']-a['von_mises_MPa']['max'])/peak,
        'displacement':abs(b['max_displacement_mm']-a['max_displacement_mm'])/b['max_displacement_mm'],
        'strain_energy':abs(b['strain_energy_Nmm']-a['strain_energy_Nmm'])/b['strain_energy_Nmm']}
      report['mesh_allowance_screen']={'factor':1.2,'engineering_guard_not_rigorous_convergence_bound':True,
        'guarded_stress_MPa':1.2*peak,'yield_safety_factor_after_guard':1170/(1.2*peak),
        'guarded_stress_below_SF2_allowable':1.2*peak<=585}
      report['status']='TWO_MESH_STATIC_SCREEN_COMPLETE_NOT_FATIGUE_OR_MANUFACTURING_RELEASE'
    except Exception as e:
      report['status']='FAILURE_OR_BUDGET_LIMIT_PRESERVED';report['error']=repr(e)
      import traceback;report['traceback']=traceback.format_exc()
    save();print(json.dumps({'event':'complete','report':identity(rp),'status':report['status']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--reuse-coarse',type=Path);p.add_argument('--fine-solver',choices=['ITERATIVE CHOLESKY'])
    a=p.parse_args();run(a.output.resolve(),a.reuse_coarse,a.fine_solver)
