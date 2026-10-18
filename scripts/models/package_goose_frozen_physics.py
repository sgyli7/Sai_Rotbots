"""Save a portable artifact and exact Git whitelist for the fixed physics data."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile,datetime
ROOT=Path(__file__).resolve().parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(a):
 p=a.package.resolve();p.mkdir(parents=True,exist_ok=True)
 for src,dest in[(ROOT/'src/sai_agent/goose/frozen_physics_runtime.py','runtime_adapter.py'),(ROOT/'scripts/diagnostics/verify_goose_physics_package_files.py','verify_package.py'),(ROOT/'scripts/diagnostics/verify_goose_frozen_physics_independent.py','verify_physics.py'),(ROOT/'scripts/diagnostics/verify_goose_frozen_contacts_independent.py','verify_contacts.py'),(ROOT/'LICENSE','LICENSE')]:shutil.copyfile(src,p/dest)
 if(ROOT/'THIRD_PARTY_NOTICES.md').exists():shutil.copyfile(ROOT/'THIRD_PARTY_NOTICES.md',p/'THIRD_PARTY_NOTICES.md')
 files=[]
 for path in sorted(p.rglob('*')):
  if not path.is_file()or path.name=='manifest.json'or '__pycache__'in path.parts or path.suffix=='.pyc':continue
  files.append(dict(path=str(path.relative_to(p)),bytes=path.stat().st_size,sha256=sha(path)))
 manifest=dict(schema='goose_frozen_physical_release_file_manifest_v1',release_id=p.name,files=files,manifest_self_digest='ZIP sha256 is stored separately; this manifest intentionally doesnot recursively hash itself',runtime_entry='robot.xml + physical_contract.json + actuator_contract.json; reference runtime_adapter.py',canonical_runtime_source=dict(repository_path='src/sai_agent/goose/frozen_physics_runtime.py',sha256=sha(ROOT/'src/sai_agent/goose/frozen_physics_runtime.py')),runtime_dependencies='Only package-relative files and declared Python requirements; provenance paths are historical data, never dereferenced by the runtime')
 (p/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');a.archive.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(a.archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for rel in[r['path']for r in files]+['manifest.json']:z.write(p/rel,arcname=p.name+'/'+rel)
 receipt=dict(release_id=p.name,archive=str(a.archive.resolve()),archive_sha256=sha(a.archive),archive_bytes=a.archive.stat().st_size,manifest_sha256=sha(p/'manifest.json'),package_files=len(files)+1,max_regular_file_bytes=max(x['bytes']for x in files),model_sha256=sha(p/'robot.xml'),physical_contract_sha256=sha(p/'physical_contract.json'),created_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 a.archive.with_suffix('.sha256').write_text(receipt['archive_sha256']+'  '+a.archive.name+'\n');a.archive.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 whitelist=[str((p/r).relative_to(ROOT))for r in[r['path']for r in files]+['manifest.json']];whitelist+=['robots/goose_v0_2/README.md','robots/goose_v0_2/hardware/training_physics_20261018_followup.md','src/sai_agent/goose/frozen_physics_runtime.py','src/sai_agent/goose/frozen_mjcf.py','scripts/models/freeze_goose_training_physics.py','scripts/models/revise_goose_frozen_material_physics.py','scripts/models/assemble_goose_frozen_runtime.py','scripts/models/package_goose_frozen_physics.py','scripts/models/render_goose_frozen_physics.py','scripts/models/export_goose_frozen_contact_preview.py','scripts/diagnostics/check_goose_frozen_physics_release.py','scripts/diagnostics/verify_goose_physics_package_files.py','scripts/diagnostics/verify_goose_frozen_physics_independent.py','scripts/diagnostics/verify_goose_frozen_contacts_independent.py','scripts/diagnostics/read_goose_frozen_contacts.py']
 a.archive.with_suffix('.git_whitelist.json').write_text(json.dumps(dict(files=sorted(whitelist),archive_is_local_delivery_not_git_staged=True),indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);main(p.parse_args())
