"""Package exact Git objects as an honest, hash-verified manufacturing increment."""
from pathlib import Path
import argparse,subprocess,json,hashlib,zipfile

ROOT=Path(__file__).resolve().parents[2]

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--revision',default='HEAD');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    base=git('rev-parse',args.base).decode().strip();revision=git('rev-parse',args.revision).decode().strip()
    names=git('diff','--name-only','--diff-filter=ACMRT',base,revision).decode().splitlines()
    removed=git('diff','--name-only','--diff-filter=D',base,revision).decode().splitlines()
    files={p:git('show',revision+':'+p) for p in names}
    if any(Path(p).is_absolute() or '..' in Path(p).parts for p in files):raise ValueError('Unsafe member')
    report=dict(schema='goose_manufacturing_increment_bundle_v1',robot_id='Goose_V0.1',base_git_commit=base,git_commit=revision,
        standalone=False,installation='Apply these changed files onto the exact base Git checkout; remove only listed deleted files. The draft PR branch is the preferred complete checkout.',
        deleted_paths=removed,stage_three_complete=False,stage_four_complete=False,hardware_freeze=False,final_appearance_pass=False,new_training_release=False,
        files=[dict(path=p,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for p,data in files.items()],
        exclusions='No Python environment, temporary logs, vendor raw CAD downloads or continuous training checkpoints.',
        notes='Contains verified native component candidates and known failed screens. Read robots/Goose_V0.1/design/stage_three_four_extension.md before using it. Old stage-two training models are not modified.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():raise FileExistsError('Never overwrite a published bundle')
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,data in files.items():z.writestr(p,data)
        z.writestr('manufacturing_increment_manifest.json',json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(args.output) as z:
        if z.testzip() is not None:raise ValueError('CRC failure')
        for p,data in files.items():
            if hashlib.sha256(z.read(p)).digest()!=hashlib.sha256(data).digest():raise ValueError(p)
    sha=hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix('.zip.sha256').write_text(sha+'  '+args.output.name+'\n')
    print(json.dumps(dict(path=str(args.output),git_commit=revision,bytes=args.output.stat().st_size,members=len(files)+1,sha256=sha,all_members_verified=True,stage_three_complete=False,stage_four_complete=False),indent=2))

if __name__=='__main__':main()
