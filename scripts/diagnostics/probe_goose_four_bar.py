"""Reproduce the ideal R2 loop transfer, including Jolt's small-inertia trap.

Run with --mass-unit-scale 1 to reproduce the failed SI-mass case. This is an
isolated solver/units check, not a real servo, CAD or grasp acceptance test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def mujoco_probe(output: Path) -> dict:
    import math
    import mujoco
    import numpy as np
    L,H=.025,.014
    xml=f'''<mujoco model="goose_r2_loop_probe"><compiler angle="radian"/>
    <option timestep="0.0005" gravity="0 0 0" iterations="100" tolerance="1e-12"/>
    <default><joint damping="0.000001"/><geom type="capsule" size="0.001" contype="0" conaffinity="0"/></default>
    <worldbody>
    <body name="lower_crank"><joint name="drive" axis="0 -1 0"/>
    <geom fromto="0 0 0 {L} 0 0" mass="0.005"/>
    <body name="jaw" pos="{L} 0 0"><joint name="jaw_pin" axis="0 -1 0"/>
    <geom fromto="0 0 0 0 0 {H}" mass="0.020"/><site name="jaw_c" pos="0 0 {H}"/></body></body>
    <body name="upper_crank" pos="0 0 {H}"><joint name="follower" axis="0 -1 0"/>
    <geom fromto="0 0 0 {L} 0 0" mass="0.005"/><site name="upper_c" pos="{L} 0 0"/></body>
    </worldbody><equality><connect name="loop" site1="jaw_c" site2="upper_c" solref="0.002 1" solimp="0.999 0.999 0.001"/></equality>
    <actuator><motor name="drive_motor" joint="drive" ctrllimited="true" ctrlrange="-.05 .05"/></actuator></mujoco>'''
    model=mujoco.MjModel.from_xml_string(xml)
    (output / 'mechanism.xml').write_text(xml+'\n')
    rows=[]
    for fx,fz in [(0.,0.),(.5,0.),(1.,0.),(0.,.5)]:
        data=mujoco.MjData(model)
        closed=math.radians(40);opened=math.radians(-33.863234334283845)
        data.qpos[:]=[closed,-closed,closed]
        mujoco.mj_forward(model,data)
        jaw=model.body('jaw').id; sj=model.site('jaw_c').id; sc=model.site('upper_c').id
        max_c=max_angle=max_path=max_tracking=0.;sat=0;samplecount=0;q_min=math.inf;q_max=-math.inf
        for i in range(12000):
            t=i*model.opt.timestep
            target=closed+(opened-closed)*(.5-.5*math.cos(math.tau*t/4.))
            q=data.qpos[0]
            tau=.012*(target-q)-.0003*data.qvel[0]-L*(-fx*math.sin(q)+fz*math.cos(q))
            data.ctrl[0]=np.clip(tau,-.05,.05)
            sat+=int(abs(tau)>.05)
            data.xfrc_applied[jaw,:3]=[fx,0,fz]
            mujoco.mj_step(model,data)
            if i%10==0 and i>=1000:
                mujoco.mj_forward(model,data)
                mat=data.xmat[jaw].reshape(3,3)
                angle=math.atan2(mat[2,0],mat[0,0])
                q=data.qpos[0]
                expected=np.array([L*math.cos(q),0,L*math.sin(q)+H])
                max_c=max(max_c,float(np.linalg.norm(data.site_xpos[sj]-data.site_xpos[sc])))
                max_path=max(max_path,float(np.linalg.norm(data.site_xpos[sj]-expected)))
                max_angle=max(max_angle,abs(angle))
                max_tracking=max(max_tracking,abs(q-target));q_min=min(q_min,q);q_max=max(q_max,q)
                samplecount+=1
        rows.append({'artificial_applied_jaw_com_force_N':[fx,0,fz],
                     'max_loop_residual_mm':max_c*1000,'max_jaw_tilt_deg':math.degrees(max_angle),
                     'max_ideal_path_residual_mm':max_path*1000,'max_target_tracking_error_deg':math.degrees(max_tracking),
                     'actual_crank_range_deg':[math.degrees(q_min),math.degrees(q_max)],'drive_saturation_steps':sat,'samples':samplecount})
    report={'scope':'Isolated fixed-base ideal loop with artificial masses and PD drive; not full robot/CAD/servo/grasp validation',
            'mujoco_version':mujoco.__version__,'dt_s':model.opt.timestep,'L_m':L,'H_m':H,
            'gravity':[0,0,0],'geometric_contacts_disabled':True,'masses_kg':{'each_crank':.005,'jaw':.020},
            'real_motor_model':False,'ideal_known_force_feedforward':True,'passive_compliance_model':False,'ground_or_grasp_object':False,
            'kinematic_tree_hinges':model.njnt,'actuators':model.nu,'closure_equality_constraints':model.neq,'cases':rows}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot', default='godot')
    parser.add_argument('--mass-unit-scale', type=float, default=100.0)
    parser.add_argument('--output', type=Path, default=Path('artifacts/Goose_V0.1/four_bar_probe'))
    args = parser.parse_args()
    if args.mass_unit_scale <= 0:
        parser.error('mass-unit-scale must be positive')
    root = Path(__file__).resolve().parents[2]
    template = root / 'integrations/godot/goose_four_bar_probe'
    args.output.mkdir(parents=True, exist_ok=True)
    project = args.output / 'godot'
    project.mkdir(exist_ok=True)
    source_hashes = {}
    for name in ('project.godot', 'main.tscn', 'godot_probe.gd', 'drive_body.gd', 'inertia.json'):
        src = template / name
        source_hashes[str(src.relative_to(root))] = hashlib.sha256(src.read_bytes()).hexdigest()
        shutil.copy2(src, project / name)
    gd = project / 'godot_probe.gd'
    gd.write_text(gd.read_text().replace('const MASS_UNIT_SCALE := 100.0',
                                       f'const MASS_UNIT_SCALE := {args.mass_unit_scale}'))
    mujoco_result = mujoco_probe(args.output)
    godot = []
    for force in (0.0, 0.5, 1.0):
        cmd = [args.godot, '--headless', '--path', str(project.resolve()),
               '--fixed-fps', '2000', '--', str(force)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        (args.output / f'godot_{force}.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'Godot failed ({result.returncode}); see output log')
        row = json.loads((project / f'godot_result_{force}.json').read_text())
        godot.append(row)
    accepted = all(r['max_target_tracking_error_deg'] < 2.0
                   and r['max_loop_residual_mm'] < 0.1
                   and r['max_jaw_tilt_deg'] < 0.05 for r in godot)
    parity = all(abs(g['max_target_tracking_error_deg']-m['max_target_tracking_error_deg']) < 0.1
                 and max(abs(a-b) for a,b in zip(g['actual_crank_range_deg'], m['actual_crank_range_deg'])) < 0.1
                 for g,m in zip(godot, mujoco_result['cases'][:3]))
    accepted = accepted and parity
    report = {'scope': 'isolated artificial fixed-base loop only',
              'engineering_acceptance': False, 'probe_pass': accepted,
              'source_sha256': source_hashes,
              'godot_mass_unit_scale': args.mass_unit_scale, 'godot_cases': godot,
              'mujoco_result': mujoco_result}
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'probe_pass': accepted, 'mass_unit_scale': args.mass_unit_scale,
                      'max_tracking_deg': [r['max_target_tracking_error_deg'] for r in godot],
                      'result': str(args.output / 'result.json')}))
    return 0 if accepted else 2


if __name__ == '__main__':
    raise SystemExit(main())
