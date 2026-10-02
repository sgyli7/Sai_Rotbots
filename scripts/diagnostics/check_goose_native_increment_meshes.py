"""Independently check installed quad meshes against native SI mass properties."""
from pathlib import Path
import argparse, json, hashlib
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,action='append')
    parser.add_argument('--output',type=Path,default=R/'evidence/manufacturing_increment_quad_gate.json')
    args=parser.parse_args()
    paths=[p.resolve() for p in args.manifest] if args.manifest else [R/'cad/exports/pitch_fork_assembly/manifest.json',R/'cad/exports/compliant_foot/manifest.json']
    results=[]
    for path in paths:
        manifest=json.loads(path.read_text())
        for p in manifest['parts']:
            f=R/p['files']['npz']['path']
            with np.load(f,allow_pickle=False) as data:v=data['vertices'];q=data['faces']
            topology=bool(v.ndim==2 and v.shape[1]==3 and q.ndim==2 and q.shape[1]==4 and np.issubdtype(q.dtype,np.integer) and np.isfinite(v).all() and q.min()>=0 and q.max()<len(v))
            if not topology:raise ValueError(p['name'])
            triangles=np.concatenate([q[:,[0,1,2]],q[:,[0,2,3]]])
            m=trimesh.Trimesh(v,triangles,process=False)
            volume_error=abs(m.volume*1e9/p['volume_mm3']-1)
            com_error=np.linalg.norm(m.center_mass-p['center_of_mass_world_m'])*1000
            valid=bool(m.is_watertight and m.is_winding_consistent and m.volume>0 and m.area_faces.min()>1e-18 and volume_error<.01 and com_error<.15 and hashlib.sha256(f.read_bytes()).hexdigest()==p['files']['npz']['sha256'])
            results.append(dict(part=p['name'],quad_faces=len(q),closed=bool(m.is_watertight),consistent=bool(m.is_winding_consistent),volume_relative_error=float(volume_error),world_com_error_mm=float(com_error),pass_mesh=valid))
    result=dict(schema='goose_native_increment_quad_gate_v1',parts=len(results),quad_faces=sum(p['quad_faces'] for p in results),mesh_identity_and_geometry_pass=all(p['pass_mesh'] for p in results),results=results,
        manufacturing_pass=False,full_assembly_pass=False,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]})
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:result[k] for k in ['parts','quad_faces','mesh_identity_and_geometry_pass']})
    print([p for p in results if not p['pass_mesh']])
    return 0 if result['mesh_identity_and_geometry_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
