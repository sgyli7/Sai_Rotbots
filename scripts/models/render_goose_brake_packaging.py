"""Actual 48-part quad CAD kit review in Blender, no generated imagery."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--resolution', type=int, default=1000)
parser.add_argument('--samples', type=int, default=64)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
args.output.mkdir(parents=True, exist_ok=True)
assembly = R/'cad/source/brake_packaging/assembly_scene.json'
payload = json.loads(assembly.read_text())
payload['parts'] = [p for p in payload['parts'] if p['group']=='brake_packaging']
payload['status'] = 'BRAKE INSTALLATION KIT ONLY - NOT THERMAL/MANUFACTURING RELEASE'
payload['review_views'] = {'brake_fit': [[.34,-.40,.43],[.015,.012,.282]],
                         'brake_rear': [[-.27,.42,.38],[.015,.012,.282]]}
payload['review_ortho_scale_m'] = {'brake_fit':.27, 'brake_rear':.27}
view = args.output/'kit_review_scene.json'
view.write_text(json.dumps(payload, separators=(',', ':'))+'\n')
renderer = ROOT/'scripts/models/render_goose_mechanical_preview.py'
sys.argv = [str(renderer), '--', '--scene', str(view), '--geometry-root', str(R),
            '--output', str(args.output), '--resolution', str(args.resolution), '--samples', str(args.samples),
            '--views', 'brake_fit,brake_rear', '--candidate-stamp']
runpy.run_path(str(renderer), run_name='__main__')
inputs = [assembly, renderer, Path(__file__), R/'cad/exports/brake_packaging/manifest.json',
          R/'evidence/brake_packaging_parameters.json']
images = [args.output/(name+'.png') for name in ['brake_fit','brake_rear']]
manifest = dict(schema='goose_brake_packaging_render_v1', parts=len(payload['parts']),
    status=payload['status'], same_quad_geometry=True, exterior_or_pcb_shown=False,
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in images})
(R/'evidence/brake_packaging_render.json').write_text(json.dumps(manifest, indent=2)+'\n')
