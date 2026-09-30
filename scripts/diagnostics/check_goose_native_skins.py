"""Re-read actual CAD and native STL, with no hole/normal repair."""
from pathlib import Path
import sys
import hashlib,json
import numpy as np
import trimesh
from build123d import import_step,CenterOf
ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/cad'))
from goose_nurbs_skin import native_properties

def main():
    manifest_path=ROBOT/'cad/exports/manufacturing_skins/manifest.json'
    manifest=json.loads(manifest_path.read_text());rows=[]
    for part in manifest['parts']:
        step=ROBOT/part['files']['step']['path'];stl=ROBOT/part['files']['stl']['path']
        shape=import_step(step)
        native_volume,native_center,_,integration_error=native_properties(shape)
        # STL repeats vertices per triangle. Merge equal coordinates on import;
        # no fill_holes, fix_normals, watertight repair or body reconstruction.
        mesh=trimesh.load_mesh(stl,process=True)
        reference=part['volume_mm3'];delta=abs(mesh.volume-reference)/reference
        row={'part':part['name'],'step_sha256':hashlib.sha256(step.read_bytes()).hexdigest(),'stl_sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'native_solid_count':len(shape.solids()),'native_cad_valid':bool(shape.is_valid),'native_step_volume_mm3':native_volume,'step_volume_relative_error':float(abs(native_volume-reference)/reference),'estimated_integration_error':integration_error,'stl_faces':len(mesh.faces),'stl_watertight':bool(mesh.is_watertight),'stl_winding_consistent':bool(mesh.is_winding_consistent),'stl_positive_volume':bool(mesh.volume>0),'stl_degenerate_faces':int((mesh.area_faces<1e-12).sum()),'stl_vs_native_volume_relative_error':float(delta),'finite_vertices':bool(np.isfinite(mesh.vertices).all())}
        row['native_com_m']=list(native_center/1000)
        row['manifest_com_error_m']=float(np.linalg.norm(np.asarray(row['native_com_m'])-part['center_of_mass_world_m']))
        row['stl_native_com_error_m']=float(np.linalg.norm(mesh.center_mass/1000-row['native_com_m']))
        row['pass']=bool(row['native_solid_count']==1 and row['native_cad_valid'] and row['step_volume_relative_error']<1e-7 and row['stl_watertight'] and row['stl_winding_consistent'] and row['stl_positive_volume'] and row['stl_degenerate_faces']==0 and row['finite_vertices'] and delta<.02 and row['manifest_com_error_m']<1e-6 and row['stl_native_com_error_m']<.00025)
        rows.append(row);print(part['name'],row['pass'],flush=True)
    report={'schema':'goose_native_skin_exchange_gate_v1','status':'EXCHANGE_VALIDITY_NOT_MANUFACTURING_RELEASE','manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Eight native skins only. Units mm; duplicate STL vertices merged on import, no topology/normal/hole repair. Does not validate attachments, full assembly sweep or complete printing release.','parts':rows,'all_pass':all(r['pass'] for r in rows),'manufacturing_pass':False}
    output=ROBOT/'evidence/manufacturing_skin_stl_gate.json';output.write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if report['all_pass'] else 1)
if __name__=='__main__':main()
