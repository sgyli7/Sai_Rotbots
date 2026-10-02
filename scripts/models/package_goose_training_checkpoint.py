"""Portable same-version training handoff with per-file integrity and extract test."""
from pathlib import Path
import argparse,csv,hashlib,json,subprocess,sys,zipfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'artifacts/Goose_V0.1/goose_training_checkpoint_460.zip');a=ap.parse_args();a.output=a.output.resolve()
    cp=R/'configs/training_checkpoint_contract.json';c=json.loads(cp.read_text());entry=json.loads((R/'evidence/training_checkpoint_entry.json').read_text())
    assert entry['model_sha256']==c['model_sha256'] and entry['contract_sha256']==sha(cp)
    assert entry['model_loading_pass'] and entry['si_boundary_pass'] and entry['finite_smoke_pass']
    files=set()
    def add(p):
        p=ROOT/p if not isinstance(p,Path) else p
        assert p.is_file(),p;files.add(p)
    for folder in ['training_checkpoint','training_reference']:
        for p in (R/'models'/folder).rglob('*'):
            if p.is_file():add(p)
    for rel in ['configs/training_checkpoint_contract.json','configs/training_reference_contract.json','configs/training_reference_bodies.csv','configs/training_reference_joints.csv','models/training_collisions/manifest.json','evidence/training_checkpoint_entry.json','evidence/training_checkpoint_geometry.json','evidence/training_checkpoint_rsl_initialization.json','evidence/training_checkpoint_validation_finalization.json','evidence/training_checkpoint_build_recovery.json','evidence/one_piece_head_service_parameters.json','evidence/one_piece_head_service_fit.json','evidence/one_piece_head_step_exchange_recovery.json','hardware/one_piece_head_service_body_parameters.csv','hardware/one_piece_head_service_bom.csv','hardware/one_piece_head_service_bom.xlsx','hardware/stage_two_actuator_bom.csv','hardware/mechanical_candidate_bom.csv','hardware/mechanical_candidate_bom_manifest.json','hardware/power_module_mount_bom.csv','hardware/compute_module_mount_bom.csv','hardware/camera_head_closure_bom.csv','hardware/torso_shell_mount_bom.csv','design/training_checkpoint_handoff.md','cad/source/one_piece_head_service_fixture/assembly_scene.json']:
        add(R/rel)
    for p in c['source_hashes']:add(p)
    scene=json.loads((R/'cad/source/one_piece_head_service_fixture/assembly_scene.json').read_text())
    for p in scene['parts']:
        if 'geometry_npz' in p:
            path=R/p['geometry_npz'];assert sha(path)==p['source_sha256'];add(path)
    for p in (R/'cad/exports/one_piece_head_service').glob('*'):add(p)
    add(R/'cad/source/one_piece_head_service/head_integral_print_shell.brep')
    for p in (R/'images/microduck_color_blocking_one_piece_head_service').glob('*.png'):add(p)
    for p in (ROOT/'src/sai_agent').rglob('*.py'):add(p)
    for p in ['scripts/diagnostics/check_goose_training_checkpoint.py','scripts/training/train_goose_checkpoint.py','scripts/models/package_goose_training_checkpoint.py','LICENSE','THIRD_PARTY_NOTICES.md'] :add(p)
    for p in (ROOT/'licenses').rglob('*'):
        if p.is_file():add(p)
    readme='''# Goose V0.1 — 460-part experimental training checkpoint

Start: robots/Goose_V0.1/design/training_checkpoint_handoff.md.
18 active axes;65 observations;18 actions;10.430762603kg nominal conditional mass.
MJCF and URDF are same-version.33 moving rigid bodies include2 passive jaw links
and12 passive sole pads. No policy, optimizer work or hardware release included.

Python3.12. From this extracted directory:

    python -m pip install -r requirements.txt
    PYTHONPATH=src python scripts/diagnostics/check_goose_training_checkpoint.py --steps 10 --output artifacts/entry.json

Read the delivered entry report before PPO. Only if stance_smoke_pass=true:

    python -m pip install -r requirements_train.txt
    PYTHONPATH=src python scripts/training/train_goose_checkpoint.py --output artifacts/first_run --iterations 2 --envs 1 --horizon 4 --device cpu

CUDA selects the neural network device; this entry uses CPU MuJoCo physics.
For Sai_Lab GPU physics, import the neutral SI contract into its own environment.
Do not substitute MicroDuck observations, actuator constants or joint ordering.
No Godot/Jolt, Unity or Bevy dynamics acceptance is claimed. Contract carries
jaw mimic, inertia, timestep, sole springs and actuator limits for every backend.

Runtime visuals use source-derived LOD. Full quad inputs and actual4colour
renders are included; simplification never changes mass/inertia. New concave
collisions are local5mm surface clusters, not certified CAD clearance bounds.

Checkpoints are experimental. Walking, turns, ground pickup and drag are not
accepted. Electrical protection, exact AK48 limits and complete assembly remain
unresolved. Do not use this package as a purchase/energization authorization.

All files are hashed by delivery_manifest.json. Raw logs and old PPO are excluded.
'''
    generated={'README.md':readme,'requirements.txt':'mujoco==3.10.0\nnumpy>=2,<3\nscipy>=1.14,<2\n','requirements_train.txt':'torch==2.9.1\nrsl-rl-lib==5.0.1\ntensordict==0.14.1\n'}
    manifest=dict(schema='goose_460_training_delivery_v1',source_scene_sha256=c['source_scene_sha256'],model_sha256=c['model_sha256'],contract_sha256=sha(cp),mass_kg=c['nominal_robot_mass_kg'],active_axes=18,observation_size=65,action_size=18,hardware_freeze=False,manufacturing_release=False,stance_smoke_pass=entry['stance_smoke_pass'],walking_pass=False,optimizer_steps=0,files={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},generated_files_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in generated.items()})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
        for p,v in generated.items():z.writestr(p,v)
        z.writestr('delivery_manifest.json',json.dumps(manifest,indent=2)+'\n')
    digest=sha(a.output);a.output.with_suffix('.zip.sha256').write_text(digest+'  '+a.output.name+'\n')
    extracted=a.output.parent/'training_checkpoint_extract';extracted.mkdir(exist_ok=False)
    with zipfile.ZipFile(a.output) as z:
        assert z.testzip() is None;z.extractall(extracted)
    for p,h in {**manifest['files'],**manifest['generated_files_sha256']}.items():assert sha(extracted/p)==h,p
    model=extracted/'robots/Goose_V0.1/models/training_checkpoint/robot.xml'
    # Verify every relative runtime mesh URI in both backend formats.
    for folder in ['training_checkpoint','training_reference']:
        base=extracted/'robots/Goose_V0.1/models'/folder
        mj=ET.parse(base/'robot.xml').getroot();meshdir=base/mj.find('compiler').get('meshdir','.')
        for mesh in mj.findall('./asset/mesh'):assert (meshdir/mesh.get('file')).is_file(),mesh.attrib
        for mesh in ET.parse(base/'robot.urdf').getroot().findall('.//geometry/mesh'):assert (base/mesh.get('filename')).is_file(),mesh.attrib
    import mujoco,numpy as np
    m=mujoco.MjModel.from_xml_path(str(model));d=mujoco.MjData(m);mujoco.mj_forward(m,d);assert m.nu==18 and np.isfinite(d.qpos).all();np.testing.assert_allclose(m.body_mass.sum(),manifest['mass_kg'],atol=1e-10)
    receipt=dict(schema='goose_training_zip_check_v1',zip=str(a.output.relative_to(ROOT)),sha256=digest,size_bytes=a.output.stat().st_size,file_count=len(files)+4,all_hashes_pass=True,all_runtime_relative_mesh_links_pass=True,extracted_model_loading_pass=True,mass_kg=float(m.body_mass.sum()),nu=int(m.nu),source_scene_sha256=c['source_scene_sha256'],stance_smoke_pass=entry['stance_smoke_pass'],manufacturing_release=False)
    (R/'evidence/training_checkpoint_bundle_check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
