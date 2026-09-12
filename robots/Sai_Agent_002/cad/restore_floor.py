"""Restore the existing project shell floor, in mm; build123d 0.11.1.

Input is the project-owned Sai 001 shell BREP, never supplier motor CAD.
The output retains its rim, arm mounting, screen aperture and outer silhouette.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from build123d import Box, Pos, export_step, import_brep


def main(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    shell = import_brep(source)
    # Restore the 4 mm original floor thickness only inside the cleared bay.
    # The mat ends 1.2 mm before the retained rear-screen cover and 3.5 mm
    # behind the actual SO101 base. Nothing new is stacked above the old floor.
    fill = Pos(-52, 0, 255) * Box(152, 220, 4)
    restored = shell.fuse(fill).clean()
    mat = Pos(-52, 0, 258) * Box(152, 220, 2)
    assert restored.is_valid and len(restored.solids()) == 1
    for name, shape in [('cargo_shell', restored), ('cargo_mat', mat)]:
        shape.label = name
        export_step(shape, destination / f'{name}.step')
        vertices, faces = shape.tessellate(.15, .15)
        trimesh.Trimesh(vertices=np.array([[v.X,v.Y,v.Z] for v in vertices])*.001,
                        faces=np.array(faces), process=False).export(destination/f'{name}.stl')
    report = dict(units='mm', source_shell_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  source_volume_mm3=shell.volume, restored_volume_mm3=restored.volume,
                  filled_volume_mm3=restored.volume-shell.volume,
                  mat_bounds_mm=[[-128,-110,257],[24,110,259]],
                  shell_valid=restored.is_valid, shell_solids=len(restored.solids()),
                  status='Nominal project CAD; existing mounting geometry retained; no hardware test')
    (destination/'floor-change.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    args=p.parse_args();main(args.source,args.destination)
