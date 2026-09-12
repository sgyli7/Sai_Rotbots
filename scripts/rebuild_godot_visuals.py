"""Rebuild display-only GLBs with explicit transformed normals from public OBJ."""
from pathlib import Path
import json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
root=ROOT/'models/full';spec=json.loads((root/'robot.json').read_text())
transform=np.eye(4);transform[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]
for name,body in spec['bodies'].items():
    scene=trimesh.Scene()
    for i,visual in enumerate(body['visuals']):
        mesh=trimesh.load_mesh(root/visual['obj'],process=False)
        mesh.apply_transform(transform)
        mesh.vertex_normals
        mesh.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=visual['rgba'],metallicFactor=0.,roughnessFactor=.65))
        scene.add_geometry(mesh,node_name=f'{name}_{i}',geom_name=f'{name}_mesh_{i}')
    (root/'assets'/f'{name}.glb').write_bytes(scene.export(file_type='glb',include_normals=True))
print('Rebuilt 26 display GLBs; physics assets unchanged')
