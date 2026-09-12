"""One-process launcher for the policy service and independent Godot simulation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from .paths import resource_root


def prepare_godot(root,destination):
    destination.mkdir(parents=True,exist_ok=True)
    for path in (root/'integrations/godot').iterdir():
        if path.is_file():shutil.copy2(path,destination/path.name)
    assets=destination/'sai_agent'
    assets.mkdir(exist_ok=True)
    shutil.copy2(root/'models/full/robot.json',assets/'robot.json')
    shutil.copytree(root/'models/full/assets',assets/'assets',dirs_exist_ok=True)
    return destination


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['godot'])
    parser.add_argument('--godot-bin',default=shutil.which('godot'))
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--case',choices=['stop','W','S','A','D','WA','shift','W_shift'])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--runtime-dir',type=Path)
    parser.add_argument('--screenshot',type=Path,help='Save an actual rendered game frame (requires a display)')
    parser.add_argument('--screenshot-at',type=float,default=.5,help='Simulated time in seconds for the screenshot')
    parser.add_argument('--stairs',type=float,default=0.,help='Experimental four-riser course, height in metres')
    parser.add_argument('--descending',action='store_true')
    parser.add_argument('--duration',type=float,default=12.)
    parser.add_argument('--task',choices=['drive','cargo'],default='drive')
    parser.add_argument('--cargo-obstacle-height',type=float,default=.018)
    parser.add_argument('--no-clamp',action='store_true',help='Cargo interlock negative control')
    args=parser.parse_args(argv)
    if not args.godot_bin:parser.error('Godot executable not found; pass --godot-bin')
    from .godot_controller import GodotController
    root=resource_root()
    cache=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'Sai_Agent_001'
    destination=prepare_godot(root,args.runtime_dir or cache/'godot')
    # Import local GLB resources before runtime; no manual editor step required.
    subprocess.run([args.godot_bin,'--headless','--editor','--path',str(destination),'--import'],check=True)
    while True:
        if args.task=='cargo':
            from .cargo_godot import CargoGodotController
            controller=CargoGodotController(no_clamp=args.no_clamp)
        else:controller=GodotController(root)
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind(('127.0.0.1',0));listener.listen(1)
            port=listener.getsockname()[1]
            command=[args.godot_bin,'--path',str(destination)]
            if args.headless:command+=['--headless']
            else:command+=['--disable-vsync','--max-fps','60']
            command+=['--',f'--port={port}']
            command+=[f'--stairs={args.stairs}',f'--duration={args.duration}']
            command+=[f'--screenshot-at={args.screenshot_at}']
            command+=[f'--task={args.task}',f'--cargo-obstacle-height={args.cargo_obstacle_height}']
            if args.descending:command+=['--descending']
            if args.headless:command+=['--no-visuals']
            if args.case:command+=[f'--case={args.case}']
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                command+=[f'--output={args.output.resolve()}']
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True,exist_ok=True)
                command+=[f'--screenshot={args.screenshot.resolve()}']
            with ThreadPoolExecutor(max_workers=1) as pool:
                stop=threading.Event()
                listener.settimeout(.25)
                service=pool.submit(controller.serve,listener,stop)
                child=None
                try:
                    child=subprocess.Popen(command)
                    started=time.monotonic();finished_at=None
                    while child.poll() is None:
                        if service.done():
                            service.result()
                            if finished_at is None:finished_at=time.monotonic()
                            if time.monotonic()-finished_at>5:
                                raise RuntimeError('Godot did not exit after ending the controller session')
                        if args.headless and (args.case or args.task=='cargo'):
                            expected=72 if args.task=='cargo' else args.duration
                            if time.monotonic()-started>expected*4+60:
                                raise TimeoutError('Godot acceptance run exceeded its wall-time budget')
                        time.sleep(.1)
                    if child.returncode not in (0,75):raise SystemExit(child.returncode)
                finally:
                    stop.set()
                    if child is not None and child.poll() is None:
                        child.terminate()
                        try:child.wait(timeout=5)
                        except subprocess.TimeoutExpired:child.kill();child.wait()
                    service.result(timeout=5)
        if child.returncode!=75:return 0


if __name__=='__main__':main()
