"""Create a content-addressed, self-contained initial-training handoff ZIP.

Includes the final parameter baseline and minimal runtime; no historical policy
is labelled compatible with the final model. Full generation history stays in Git.
"""
from pathlib import Path
import json,hashlib,zipfile,argparse,xml.etree.ElementTree as ET
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'artifacts/Goose_V0.1/goose_stage_one_20260930.zip');a=p.parse_args();c=json.loads((R/'configs/stage_one_contract.json').read_text());model=R/'models/stage_one'
 assets=set(c['asset_sha256']);assets|={m.attrib['filename'] for m in ET.parse(model/'robot.urdf').findall('.//mesh')}
 files=[model/'robot.xml',model/'robot.urdf']+[model/x for x in sorted(assets)]
 files+=list((R/'configs').glob('stage_one_*'))+[R/'hardware/stage_one_actuator_bom.csv',R/'design/stage_one_parameter_handoff.md']
 files+=list((R/'evidence').glob('stage_one_*.json'));files=[x for x in files if x.name!='stage_one_delivery_manifest.json']
 files+=list((R/'images').glob('stage_one_*.png'))+[R/'cad/source/stage_one_architecture/scene.json',R/'cad/source/stage_one_architecture/goose_stage_one_quad.blend']
 files+=[ROOT/'src/sai_agent/__init__.py',ROOT/'src/sai_agent/paths.py']+[ROOT/'src/sai_agent/goose'/f for f in ('__init__.py','stage_one.py','stage_one_gravity.py','rsl.py','control.py','spec.py')]
 files+=[ROOT/'scripts/training/train_goose_stage_one.py',ROOT/'scripts/diagnostics/validate_goose_stage_one_entry.py',ROOT/'scripts/evaluation/evaluate_goose_stage_one.py',ROOT/'tests/test_goose_stage_one.py',ROOT/'LICENSE',ROOT/'THIRD_PARTY_NOTICES.md']
 files+=list((ROOT/'licenses').rglob('*'));files=[f for f in files if not f.is_dir()]
 files=sorted(set(files));missing=[str(x) for x in files if not x.is_file()]
 if missing:raise FileNotFoundError(missing)
 for rel,h in c['asset_sha256'].items():
  if digest(model/rel)!=h:raise ValueError('asset changed after parameter contract')
 for name in ('stage_one_system_gate.json','stage_one_pd_holdout.json','stage_one_trainer_entry.json'):
  record=json.loads((R/'evidence'/name).read_text())
  if record['model_sha256']!=c['model_sha256'] or record['contract_sha256']!=digest(R/'configs/stage_one_contract.json'):raise ValueError('stale evidence: '+name)
  for rel,h in record.get('source_sha256',{}).items():
   if digest(ROOT/rel)!=h:raise ValueError('stale source evidence: '+name+' '+rel)
 scene=json.loads((R/'cad/source/stage_one_architecture/scene.json').read_text());geometry=[]
 for part in scene['parts']:
  f=np.asarray(part['faces']);m=trimesh.Trimesh(part['vertices'],np.vstack((f[:,[0,1,2]],f[:,[0,2,3]])),process=False)
  ok=f.shape[1]==4 and m.is_watertight and m.is_winding_consistent and m.volume>0
  geometry.append(dict(name=part['name'],quad_faces=len(f),watertight=bool(m.is_watertight),consistent_winding=bool(m.is_winding_consistent),volume_m3=float(m.volume),pass_geometry=bool(ok)))
 if not all(g['pass_geometry'] for g in geometry):raise ValueError('quad source check failed')
 geofile=R/'evidence/stage_one_geometry_gate.json';geofile.write_text(json.dumps(dict(status='EDITABLE_SOURCE_QUAD_GEOMETRY_PASS',parts=geometry,part_count=len(geometry),quad_faces=sum(p['quad_faces'] for p in geometry),all_quads_closed_positive=True,scene_sha256=digest(R/'cad/source/stage_one_architecture/scene.json'),blend_sha256=digest(R/'cad/source/stage_one_architecture/goose_stage_one_quad.blend')),indent=2)+'\n');files=sorted(set(files+[geofile]))
 manifest=dict(schema='goose_stage_one_handoff_v1',status='INITIAL_TRAINING_PARAMETER_BASELINE',model_sha256=c['model_sha256'],contract_sha256=digest(R/'configs/stage_one_contract.json'),nominal_mass_kg=c['nominal_robot_mass_kg'],joint_count=18,physical_hard_freeze=False,manufacturing_release=False,walking_acceptance=False,policy_included=False,tests='48 repository tests passed; final-model CUDA/RSL initialization checked with zero optimizer updates',open_items=['jaw transmission and continuous bite output','small AK driver supply window and protection','ground-pick trajectory/feedback','manufacturing fastening/cavities and calibration'],files={str(f.relative_to(ROOT)):digest(f) for f in files})
 manifestfile=R/'evidence/stage_one_delivery_manifest.json';manifestfile.write_text(json.dumps(manifest,indent=2)+'\n')
 readme='''# Goose stage-one parameter handoff\n\nStart with robots/Goose_V0.1/design/stage_one_parameter_handoff.md (Chinese).\n\nThis is an 18-axis initial-training parameter baseline, NOT a manufacturing or walking release. Mass 8.625 kg estimated. No deployable policy is included.\n\nPython 3.12. Reuse a MuJoCo/PyTorch/RSL environment if available. Core dependencies are in requirements.txt; training extras in requirements_train.txt. On DGX Spark, use the tested existing PyTorch 2.9.1+cu129 environment.\n\nFrom this directory:\n\n    PYTHONPATH=src python scripts/diagnostics/validate_goose_stage_one_entry.py --device cuda --output artifacts/entry.json\n    PYTHONPATH=src python scripts/training/train_goose_stage_one.py --output artifacts/first_run --iterations 2 --envs 4 --horizon 16 --device cuda\n\nUse --device cpu without CUDA. Training output must be a new directory. This bundle has runtime/model inputs and editable scene/Blender. Rebuilding from original CAD history uses the full Git repository, not this compact bundle.\n\nIntegrity: robots/Goose_V0.1/evidence/stage_one_delivery_manifest.json lists SHA-256 for every delivered source/data file.\n'''
 core_requirements='mujoco==3.10.0\nnumpy>=2.0,<3\nscipy>=1.14,<2\nonnxruntime==1.24.4\npytest>=8,<10\n'
 train_requirements='torch==2.9.1\nrsl-rl-lib==5.0.1\nonnx==1.22.0\n'
 manifest['generated_files_sha256']={name:hashlib.sha256(value.encode()).hexdigest() for name,value in {'README.md':readme,'requirements.txt':core_requirements,'requirements_train.txt':train_requirements}.items()}
 manifestfile.write_text(json.dumps(manifest,indent=2)+'\n')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for f in files+[manifestfile]:z.write(f,str(f.relative_to(ROOT)))
  z.writestr('README.md',readme);z.writestr('requirements.txt',core_requirements);z.writestr('requirements_train.txt',train_requirements)
 with zipfile.ZipFile(a.output) as z:
  if z.testzip():raise ValueError('corrupt bundle')
 print(json.dumps(dict(path=str(a.output),sha256=digest(a.output),size_bytes=a.output.stat().st_size,manifest_files=len(files)),indent=2))
if __name__=='__main__':main()
