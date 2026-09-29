"""Run the independent full-body Godot adapter in an artifact directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from sai_agent.paths import resource_root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--duration',type=float,default=4)
    p.add_argument('--output',type=Path,default=Path('artifacts/Goose_V0.1/godot_home'))
    p.add_argument('--godot',default='godot');a=p.parse_args();root=resource_root();a.output.mkdir(parents=True,exist_ok=True)
    for source in (root/'integrations/godot/goose_robot').iterdir():
        if source.suffix in ('.gd','.godot','.tscn'):shutil.copyfile(source,a.output/source.name)
    transfer=root/'robots/Goose_V0.1/models/full/rigid_transfer.json';shutil.copyfile(transfer,a.output/'rigid_transfer.json')
    proc=subprocess.run([a.godot,'--headless','--path',str(a.output.resolve()),'--','%g'%a.duration],capture_output=True,text=True,timeout=90)
    (a.output/'engine.log').write_text(proc.stdout+proc.stderr)
    if not (a.output/'result.json').exists():
        print(proc.stdout[-3000:]+proc.stderr[-7000:]);raise RuntimeError(f'Godot produced no result: exit {proc.returncode}')
    result=json.loads((a.output/'result.json').read_text());result['source_transfer_sha256']=hashlib.sha256(transfer.read_bytes()).hexdigest()
    result['adapter_sha256']=hashlib.sha256((a.output/'goose_adapter.gd').read_bytes()).hexdigest();result['engine_exit_code']=proc.returncode
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0 if result['pass'] and proc.returncode==0 else 2


if __name__=='__main__':raise SystemExit(main())
