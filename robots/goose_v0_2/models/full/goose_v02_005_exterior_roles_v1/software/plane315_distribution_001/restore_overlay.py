#!/usr/bin/env python3
"""Restore/verify only the frozen source overlay; no imports, pip, GPU or globals."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path);p.add_argument('--verify-only',action='store_true');a=p.parse_args();manifest=json.loads((ROOT/'distribution_manifest.json').read_text());D=(a.destination or Path(manifest['default_destination'])).expanduser().absolute()
 for relative,digest in manifest['files'].items():
  source=ROOT/relative
  if not source.is_file() or sha(source)!=digest:raise RuntimeError('Distribution bytes changed: '+relative)
 if D.exists():
  for relative,digest in manifest['payload_files'].items():
   path=D/relative
   if not path.is_file() or sha(path)!=digest:raise RuntimeError('Existing destination differs; preserve it and select a new directory: '+str(path))
  print(json.dumps(dict(status='EXISTING_OVERLAY_EXACT_VERIFY_PASS',destination=str(D),files=len(manifest['payload_files']),files_overwritten=0,imports_or_GPU_or_pip=0)));return
 if a.verify_only:raise FileNotFoundError('Overlay destination absent: '+str(D))
 D.mkdir(parents=True,exist_ok=False)
 for relative,digest in manifest['payload_files'].items():
  target=D/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'payload'/relative,target)
  if sha(target)!=digest:raise RuntimeError('Copied overlay mismatch: '+relative)
 print(json.dumps(dict(status='SOURCE_OVERLAY_RESTORED',destination=str(D),files=len(manifest['payload_files']),files_overwritten=0,shared_environment_modified=False,imports_or_GPU_or_pip=0,requirement='Use a launcher lock matching this exact destination; existing Python/MuJoCo/Warp/Torch stack remains external.')))
if __name__=='__main__':main()
