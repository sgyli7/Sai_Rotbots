"""Drive Godot using the shared Python controller and versioned SI messages."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time

from sai_agent.goose.protocol import SensorFrame,encode_message
from sai_agent.goose.runtime import BackendController
from sai_agent.paths import resource_root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--duration',type=float,default=4);p.add_argument('--godot',default='godot')
    p.add_argument('--static-double-support',action='store_true')
    p.add_argument('--policy',type=Path);p.add_argument('--policy-metadata',type=Path)
    p.add_argument('--allow-experimental',action='store_true');a=p.parse_args()
    root=resource_root();transfer=root/'robots/Goose_V0.1/models/full/rigid_transfer.json'
    a.output.mkdir(parents=True,exist_ok=False)
    for source in (root/'integrations/godot/goose_robot').iterdir():
        if source.suffix in ('.gd','.godot','.tscn'):shutil.copyfile(source,a.output/source.name)
    shutil.copyfile(transfer,a.output/'rigid_transfer.json')
    controller=BackendController(a.output/'rigid_transfer.json',a.policy,a.policy_metadata,a.allow_experimental,a.static_double_support)
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',19042));sock.settimeout(.2)
    proc=subprocess.Popen([a.godot,'--headless','--path',str(a.output.resolve()),'--',str(a.duration),'--udp'],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    frames=0;maximum_torque=0.;error=None;last_sensor=None;sensor_rows=[];start=time.monotonic()
    try:
        while proc.poll() is None:
            if time.monotonic()-start>90:raise TimeoutError('Backend run exceeded wall-clock deadline')
            try:packet,address=sock.recvfrom(65535)
            except socket.timeout:continue
            if address[0]!='127.0.0.1':raise ValueError('Unexpected backend sender')
            frame=SensorFrame.from_message(json.loads(packet),controller.names)
            last_sensor={'timestamp_s':frame.timestamp_s,
                         'gravity_body_unit':frame.gravity_body_unit.tolist(),
                         'positions_rad':frame.positions_rad.tolist(),
                         'velocities_rad_s':frame.velocities_rad_s.tolist()}
            sensor_rows.append(last_sensor)
            action=controller.tick(frame);maximum_torque=max(maximum_torque,max(abs(x) for x in action['torque_Nm']))
            sock.sendto(encode_message(action),('127.0.0.1',19041));frames+=1
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}';proc.terminate()
    finally:
        sock.close()
        try:stdout,stderr=proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();stdout,stderr=proc.communicate()
        (a.output/'engine.log').write_text(stdout+stderr)
        (a.output/'sensor_trace.json').write_text(json.dumps(sensor_rows)+'\n')
    result=json.loads((a.output/'result.json').read_text()) if (a.output/'result.json').exists() else {'pass':False}
    result.update(shared_python_controller=True,SI_sensor_frames=frames,controller_error=error,
        max_motor_torque_Nm=maximum_torque,source_transfer_sha256=hashlib.sha256(transfer.read_bytes()).hexdigest(),
        controller_sha256=hashlib.sha256((root/'src/sai_agent/goose/runtime.py').read_bytes()).hexdigest(),
        adapter_sha256=hashlib.sha256((a.output/'goose_adapter.gd').read_bytes()).hexdigest(),
        policy_sha256=hashlib.sha256(a.policy.read_bytes()).hexdigest() if a.policy else None,
        policy_metadata_sha256=hashlib.sha256(a.policy_metadata.read_bytes()).hexdigest() if a.policy_metadata else None,
        static_double_support=a.static_double_support,engine_exit_code=proc.returncode,
        external_root_support=False,policy_used=a.policy is not None,last_sensor=last_sensor)
    result['pass']=bool(result['pass'] and frames>=int(a.duration/controller.contract['torque_update_dt_s'])-1
                        and not error and proc.returncode==0)
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['pass'] else 2


if __name__=='__main__':raise SystemExit(main())
