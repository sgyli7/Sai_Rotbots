"""Check appearance asset identity; never promote partial skins to a full robot."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/Goose_V0.1'
REQUIRED_RELEASE_GATES=('mechanical_assembly','electrical_design','procurement','mouth_load_path','swept_clearance','physical_parameter_consistency')

def safe_file(root,path):
    file=(root/path).resolve()
    if not file.is_relative_to(root.resolve()):raise ValueError('path escapes robot root')
    if not file.is_file():raise ValueError('file missing')
    return file

def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()

def assembly_identity(manifest,source_sha256):
    # Bind display geometry/material/placement AND every native part record.
    # Native file hashes are independently checked above, so a CAD revision
    # also invalidates old receipts even if display scene bytes stay equal.
    payload={'source_sha256':source_sha256,'parts':sorted(manifest.get('parts',[]),key=lambda p:p.get('name',''))}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def inspect(root,manifest_file,source_file):
    root=Path(root);manifest_file=Path(manifest_file);source_file=Path(source_file)
    errors=[];release=[];parts=[]
    try:
        manifest=json.loads(manifest_file.read_text());scene=json.loads(source_file.read_text())
    except (OSError,ValueError) as e:
        return {'integrity_pass':False,'final_appearance_pass':False,'errors':[str(e)],'release_blockers':['unreadable inputs'],'parts':[]}
    source_parts=scene.get('parts',[]);cad_parts=manifest.get('parts',[])
    source_names=[p.get('name') for p in source_parts];cad_names=[p.get('name') for p in cad_parts]
    if len(set(source_names))!=len(source_names) or len(set(cad_names))!=len(cad_names):errors.append('duplicate part identity')
    if set(source_names)!=set(cad_names):errors.append('CAD/source part identity mismatch')
    if not cad_parts:errors.append('empty assembly')
    if scene.get('unit')!='m':errors.append('source unit must explicitly be m')
    project_root=root.resolve().parents[1]
    for path,digest in manifest.get('source_hashes',{}).items():
        try:
            if sha(safe_file(project_root,path))!=digest:errors.append(f'input source hash mismatch: {path}')
        except (OSError,ValueError) as e:errors.append(f'input source {path}: {e}')
    source_by_name={p.get('name'):p for p in source_parts}
    for record in cad_parts:
        name=record.get('name');part_errors=[]
        if record.get('unit')!='mm':part_errors.append('native CAD unit must be mm')
        if record.get('manufacturing_released') is not True:release.append(f'{name}: manufacturing unreleased')
        if record.get('remaining_gates'):release.append(f'{name}: attachment/assembly gates open')
        files=record.get('files',{})
        if not {'brep','step','stl'}<=set(files):part_errors.append('missing BREP/STEP/STL identity')
        for kind,entry in files.items():
            try:
                file=safe_file(root,entry['path'])
                if sha(file)!=entry.get('sha256'):part_errors.append(f'{kind}: hash mismatch')
            except (KeyError,ValueError,OSError) as e:part_errors.append(f'{kind}: {e}')
        source=source_by_name.get(name)
        mesh_result={}
        if source is not None:
            role=source.get('role','')
            if any(word in role.lower() for word in ('proxy','envelope','reserve','blank','placeholder','pending','candidate')):
                release.append(f'{name}: non-final role {role}')
            try:
                if 'geometry_npz' in source:
                    file=safe_file(root,source['geometry_npz'])
                    if sha(file)!=source.get('source_sha256'):raise ValueError('quad source hash mismatch')
                    with np.load(file,allow_pickle=False) as data:
                        vertices=np.asarray(data['vertices'],dtype=float);raw=np.asarray(data['faces'])
                else:
                    vertices=np.asarray(source['vertices'],dtype=float);raw=np.asarray(source['faces'])
                    canonical=json.dumps({'vertices':source['vertices'],'faces':source['faces']},sort_keys=True,separators=(',',':')).encode()
                    if hashlib.sha256(canonical).hexdigest()!=source.get('source_sha256'):raise ValueError('quad source hash mismatch')
                if vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all():raise ValueError('invalid finite xyz vertices')
                if raw.ndim!=2 or raw.shape[1]!=4 or not np.issubdtype(raw.dtype,np.integer):raise ValueError('source must contain integer quad faces')
                faces=raw.astype(np.int64,copy=False)
                if faces.size==0 or faces.min()<0 or faces.max()>=len(vertices):raise ValueError('invalid quad indices')
                if any(len(set(f))!=4 for f in faces):raise ValueError('collapsed quad')
                tri=np.vstack([faces[:,[0,1,2]],faces[:,[0,2,3]]]);mesh=trimesh.Trimesh(vertices,tri,process=False)
                if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:raise ValueError('quad shell not closed consistently oriented positive volume')
                # This checks scale independently of declarations and flags.
                reference=record.get('volume_mm3')
                if reference is None or not np.isfinite(reference) or reference<=0:raise ValueError('invalid native volume')
                delta=abs(mesh.volume*1e9-reference)/reference
                if delta>.02:raise ValueError('SI/CAD volume mismatch exceeds 2%')
                reference_com=np.asarray(record.get('center_of_mass_world_m',[]),dtype=float)
                if reference_com.shape!=(3,) or not np.isfinite(reference_com).all():raise ValueError('native world COM identity absent')
                com_error=float(np.linalg.norm(mesh.center_mass-reference_com))
                if com_error>.00025:raise ValueError('source/native placement mismatch exceeds 0.25mm')
                mesh_result={'quad_count':len(faces),'volume_relative_difference':float(delta),'center_of_mass_difference_m':com_error,'closed':True}
            except (KeyError,TypeError,ValueError,IndexError) as e:part_errors.append(str(e))
        errors.extend(f'{name}: {e}' for e in part_errors)
        parts.append({'name':name,'integrity_pass':not part_errors,**mesh_result})
    # A scalar `manufacturing_pass:true` cannot override unresolved parts or
    # substitute for the same-version full assembly and its audit receipts.
    if manifest.get('scope')!='FULL_ASSEMBLY':release.append('partial skins only; full purchased/printed/machined assembly not delivered')
    inventory=manifest.get('assembly_inventory')
    if inventory!=sorted(cad_names):release.append('full assembly inventory not bound to source parts')
    assembly_sha=manifest.get('assembly_sha256')
    actual_assembly_sha=assembly_identity(manifest,sha(source_file))
    receipts=manifest.get('release_receipts',{})
    if not assembly_sha:release.append('assembly geometry identity absent')
    elif assembly_sha!=actual_assembly_sha:release.append('assembly identity does not bind actual source scene and native parts')
    for gate in REQUIRED_RELEASE_GATES:
        try:
            entry=receipts[gate];file=safe_file(root,entry['path'])
            if sha(file)!=entry['sha256']:raise ValueError('receipt hash mismatch')
            receipt=json.loads(file.read_text())
            if receipt.get('pass') is not True or not assembly_sha or receipt.get('assembly_sha256')!=assembly_sha:raise ValueError('gate not passed on this assembly')
        except (KeyError,OSError,ValueError) as e:release.append(f'{gate}: {e}')
    return {'schema':'goose_manufacturing_appearance_gate_v1','integrity_pass':not errors,'final_appearance_pass':not errors and not release,'computed_assembly_sha256':actual_assembly_sha,'manifest_sha256':sha(manifest_file),'source_sha256':sha(source_file),'errors':errors,'release_blockers':release,'parts':parts,'scope':'Hash, identity, quad topology and SI scale checks; no unperformed physical or full assembly proof.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--robot-root',type=Path,default=ROBOT)
    p.add_argument('--manifest',type=Path);p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);p.add_argument('--require-final',action='store_true')
    a=p.parse_args();root=a.robot_root
    report=inspect(root,a.manifest or root/'cad/exports/manufacturing_skins/manifest.json',a.source or root/'cad/source/manufacturing_skins/quad_scene.json')
    output=a.output or root/'evidence/manufacturing_appearance_gate.json'
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'integrity_pass':report['integrity_pass'],'final_appearance_pass':report['final_appearance_pass'],'parts':len(report['parts']),'errors':report['errors'],'release_blockers':len(report['release_blockers'])},indent=2))
    raise SystemExit(0 if report['integrity_pass'] and (not a.require_final or report['final_appearance_pass']) else 1)
if __name__=='__main__':main()
