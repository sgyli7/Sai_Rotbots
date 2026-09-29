"""Run inside Blender to check the saved editable mesh, excluding studio props."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
import bmesh

parser=argparse.ArgumentParser()
parser.add_argument('blend',type=Path)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
parts=[]
for obj in bpy.data.objects:
    if obj.type!='MESH' or obj.name.startswith('STUDIO_'):
        continue
    bm=bmesh.new(); bm.from_mesh(obj.data)
    counts={str(n):sum(len(face.verts)==n for face in bm.faces)
            for n in sorted({len(face.verts) for face in bm.faces})}
    bad_edges=sum(not edge.is_manifold for edge in bm.edges)
    zero_faces=sum(face.calc_area()<=1e-14 for face in bm.faces)
    volume=bm.calc_volume(signed=True)
    passed=counts=={'4':len(bm.faces)} and bool(bm.faces) and bad_edges==0 and zero_faces==0 and volume>0
    parts.append(dict(name=obj.name,faces=len(bm.faces),face_sides=counts,
                      nonmanifold_edges=bad_edges,zero_area_faces=zero_faces,
                      positive_signed_volume=volume>0,passed=passed))
    bm.free()
report=dict(scope='Editable Blender source topology only; not shape, self-intersection, assembly, manufacturing or physics acceptance',
            source_sha256=hashlib.sha256(args.blend.read_bytes()).hexdigest(),
            parts=len(parts),quad_faces=sum(p['face_sides'].get('4',0) for p in parts),
            passed=bool(parts) and all(p['passed'] for p in parts),results=parts)
args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
if not report['passed']: raise RuntimeError('Saved Blender quad source failed topology audit')
