#!/usr/bin/env python3
"""Pinned local launcher for the frozen native50 training entry; default is bounded smoke."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,importlib.util,importlib.machinery,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def locked_path(path):
 path=Path(path)
 return path if path.is_absolute() else ROOT/path

def checked_relative(root,relative):
 p=Path(relative)
 if p.is_absolute() or '..' in p.parts:raise ValueError('Operational bundle path must be relative: '+relative)
 target=(root/p).resolve(strict=True)
 if not target.is_relative_to(root):raise ValueError('Bundle path escapes its root: '+relative)
 return target

def module_spec_without_import(name):
 roots=None;spec=None
 for i in range(1,len(name.split('.'))+1):
  fullname='.'.join(name.split('.')[:i]);spec=importlib.machinery.PathFinder.find_spec(fullname,roots)
  if spec is None:return None
  roots=spec.submodule_search_locations
 return spec

def environment_check(lock,bundle=None):
 if Path(sys.prefix)!=Path(lock['python_prefix']):raise RuntimeError('Wrong Python environment prefix: '+sys.prefix)
 if sys.version_info[:2]!=(3,12):raise RuntimeError('This native50 entry requires Python3.12')
 rows={}
 for name,wanted in lock['versions'].items():
  version=importlib.metadata.version(name)
  if version!=wanted:raise RuntimeError(f'Wrong active distribution {name}: {version} != {wanted}')
  rows[name]=dict(version=version,metadata_path=str(importlib.metadata.distribution(name)._path))
 for path,digest in lock['environment_files'].items():
  if sha(locked_path(path))!=digest:raise RuntimeError('Environment source/metadata bytes changed: '+path)
 for key,value in lock.get('runtime_environment',{}).items():
  if key!='WARP_CACHE_PATH':raise RuntimeError('Unsupported extra runtime environment key: '+key)
  if os.environ.get(key)!=value:raise RuntimeError('Wrong locked runtime environment: '+key)
 origins={}
 for module,parent in lock['module_origins'].items():
  spec=module_spec_without_import(module)
  if spec is None or spec.origin is None or not Path(spec.origin).resolve().is_relative_to(Path(parent).resolve()):
   raise RuntimeError('Wrong module origin for '+module+': '+str(spec))
  origins[module]=spec.origin
 if bundle is not None:
  spec=importlib.util.find_spec('bevy_microduck_tools')
  if spec is None or not Path(spec.origin).resolve().is_relative_to(bundle/'runtime_tools'):
   raise RuntimeError('Runtime must resolve from frozen bundle/runtime_tools')
  origins['bevy_microduck_tools']=spec.origin
 return dict(executable=sys.executable,python_prefix=sys.prefix,versions=rows,module_origins=origins,environment_files_checked=len(lock['environment_files']),GPU_initialized=False)

def bundle_check(bundle,manifest_sha=None):
 manifest=bundle/'bundle_manifest.json'
 if manifest_sha and sha(manifest)!=manifest_sha:raise ValueError('Bundle manifest hash mismatch')
 m=json.loads(manifest.read_text());files=m['files']
 for relative,digest in files.items():
  if sha(checked_relative(bundle,relative))!=digest:raise ValueError('Bundle file hash mismatch: '+relative)
 contract=json.loads((bundle/'contract.json').read_text())
 if sha(bundle/'robot.xml')!=contract['model_sha256']:raise ValueError('Plant model hash mismatch')
 for relative,digest in contract['asset_sha256'].items():
  if sha(checked_relative(bundle,relative))!=digest:raise ValueError('Operational asset mismatch: '+relative)
 expected={'assembly','motion','mci','fk_receipt','fk_xml','hardware_contract','beak_mapping_module','beak_mapping_evidence','baseline_model','baseline_contract','contact'}
 refs=contract['closeout_native50']['source_refs']
 if set(refs)!=expected:raise ValueError('Native50 requires exact11 source refs')
 for name,row in refs.items():
  if sha(checked_relative(bundle,row['path']))!=row['sha256']:raise ValueError('Operational source mismatch: '+name)
 if contract['joint_order'][5]!='beak_input_rotor' or len(contract['joint_order'])!=18:raise ValueError('Public motor order mismatch')
 if contract['observation_sizes']['locomotion']!=65 or contract['observation_sizes']['recovery']!=65:raise ValueError('Public Actor65 mismatch')
 entry='runtime_tools/bevy_microduck_tools/goose/closeout_training.py'
 if entry not in files:raise ValueError('Training entry is absent from frozen manifest')
 return dict(bundle=str(bundle),manifest_sha256=sha(manifest),files_checked=len(files),model_sha256=sha(bundle/'robot.xml'),contract_sha256=sha(bundle/'contract.json'),training_entry_sha256=sha(bundle/entry),candidate=contract['candidate'],training_ready=contract.get('training_ready',False),source_refs=refs)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--lock',type=Path,default=ROOT/'launcher_environment_lock_uncaptured_001.json')
 p.add_argument('--bundle',type=Path)
 p.add_argument('--bundle-manifest-sha256')
 p.add_argument('--output',type=Path)
 p.add_argument('--mode',choices=['smoke','train'],default='smoke')
 p.add_argument('--num-envs',type=int,default=2)
 p.add_argument('--steps',type=int,default=32)
 p.add_argument('--memory-gib',type=int,default=16,choices=range(1,17))
 p.add_argument('--timeout-s',type=int)
 p.add_argument('--resume',type=Path,help='Previous checkpoint.pt or successful train-segment receipt.json')
 p.add_argument('--segment-seconds',type=float)
 p.add_argument('--iterations',type=int)
 p.add_argument('--use-reference',action='store_true')
 p.add_argument('--check-only',action='store_true')
 p.add_argument('--environment-only',action='store_true')
 p.add_argument('--_environment-child',action='store_true',help=argparse.SUPPRESS)
 a=p.parse_args();a.execution_mode='uncaptured';lock=json.loads(a.lock.read_text());
 if lock.get('qualified_execution_mode')!='uncaptured' or lock.get('use_cuda_graph')is not False:raise RuntimeError('Final source007 delivery lock must require uncaptured execution')
 implicit_bundle=ROOT if (ROOT/'robot.xml').is_file() and (ROOT/'bundle_manifest.json').is_file() else None;bundle=a.bundle.resolve(strict=True) if a.bundle else implicit_bundle
 if a.timeout_s is None:a.timeout_s=600 if a.mode=='train' else 180
 if not 1<=a.timeout_s<=600:p.error('--timeout-s must be in1..600 seconds')
 if a.resume is not None:
  if a.mode!='train':p.error('--resume is valid only with --mode train')
  a.resume=a.resume.expanduser().resolve()
  if a.resume.suffix=='.json':
   if not a.resume.is_file():p.error('Resume segment receipt does not exist')
   previous=json.loads(a.resume.read_text())
   if previous.get('schema')!='goose_source007_training_entry_probe_v1' or previous.get('mode')!='train' or previous.get('passed')is not True or not previous.get('last_checkpoint'):p.error('Resume JSON must be a successful train-segment receipt with a saved checkpoint')
   checkpoint=Path(previous['last_checkpoint']['path'])
   a.resume=(checkpoint if checkpoint.is_absolute() else a.resume.parent/checkpoint).resolve()
   if not a.resume.is_file() or sha(a.resume)!=previous['last_checkpoint']['sha256']:p.error('Previous segment checkpoint is missing or changed')
  if not a.resume.is_file():p.error('--resume must name an existing checkpoint file')
  a.resume_sidecar=a.resume.with_suffix('.binding.json')
  if not a.resume_sidecar.is_file():p.error('--resume requires the matching checkpoint.with_suffix(.binding.json) sidecar')
  a.resume_binding=json.loads(a.resume_sidecar.read_text())
  if a.resume_binding.get('checkpoint_sha256')!=sha(a.resume):p.error('Resume checkpoint SHA differs from its binding sidecar')
 if a.mode=='train':
  if a.segment_seconds is None:a.segment_seconds=a.timeout_s-30
  if not 0<a.segment_seconds<=a.timeout_s-30:p.error('--segment-seconds must be positive and at least30s below guard --timeout-s')
 elif a.segment_seconds is not None:p.error('--segment-seconds is train-only')
 if bundle is None and not a.environment_only:p.error('--bundle is required except for --environment-only')
 if a.mode=='train' and (not a.iterations or a.iterations<1 or a.use_reference):p.error('--mode train requires positive --iterations and forbids --use-reference')
 if not a.check_only and not a.environment_only and a.output is None:p.error('--output is required for a real rollout/train invocation')
 if not a.check_only and not a.environment_only and a.output is not None and a.output.exists():p.error('--output must be a new directory; preserve the earlier segment')
 if a.mode=='train' and a.steps!=32:p.error('This qualified training horizon is fixed to steps=32')
 candidate = json.loads((bundle/'contract.json').read_text())['candidate'] if bundle is not None else None
 allowed_counts = (2, 32) if candidate == 'goose_v02_005_exterior_roles_v1' else (2,)
 if a.num_envs not in allowed_counts:p.error(f'Qualified world counts are {allowed_counts}')
 if not 1<=a.steps<=100:p.error('Bounded smoke steps1..100 required')
 if not a._environment_child:
  env=os.environ.copy();paths=([str(bundle/'runtime_tools')] if bundle else [])+lock['overlay_paths'];env.update(PYTHONPATH=os.pathsep.join(paths),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1');env.update(lock.get('runtime_environment',{}))
  os.execve(lock['python_executable'],[lock['python_executable'],str(Path(__file__).resolve()),*sys.argv[1:],'--_environment-child'],env)
 result={'environment':environment_check(lock,bundle)}
 if bundle:result['bundle']=bundle_check(bundle,a.bundle_manifest_sha256)
 result['execution_request']=dict(mode=a.mode,num_envs=a.num_envs,horizon_ticks=a.steps,guard_timeout_s=a.timeout_s,segment_seconds=a.segment_seconds,execution_mode=a.execution_mode or 'from_bound_Owner_approval_or_diagnostic_default',resume=None if a.resume is None else dict(path=str(a.resume),sha256=sha(a.resume),sidecar=str(a.resume_sidecar),sidecar_sha256=sha(a.resume_sidecar),checkpoint_semantics_checked_by='frozen training module exactbinding guard'))
 if a.environment_only or a.check_only:
  print(json.dumps(dict(status='READ_ONLY_PREFLIGHT_PASS',**result),indent=2));return
 # Smoke can inspect diagnostic/admission bundles. Policy training needs adopted identity.
 if a.mode=='train' and (result['bundle']['candidate'] not in ('goose_v02_native50_source007_adopted_20261110_v1','goose_v02_005_exterior_roles_v1') or not result['bundle']['training_ready']):
  raise RuntimeError('Training requires a qualified bundle')
 argv=[sys.executable,'-m','bevy_microduck_tools.goose.closeout_training','--bundle',str(bundle),'--output',str(a.output.resolve()),'--mode',a.mode,'--num-envs',str(a.num_envs),'--steps',str(a.steps)]
 if a.iterations is not None:argv+=['--iterations',str(a.iterations)]
 if a.use_reference:argv+=['--use-reference']
 if a.resume is not None:argv+=['--resume',str(a.resume)]
 if a.segment_seconds is not None:argv+=['--segment-seconds',str(a.segment_seconds)]
 if a.execution_mode is not None:argv+=['--execution-mode',a.execution_mode]
 print('PREFLIGHT '+json.dumps(result),flush=True)
 guard=lock['resource_guard']
 if sha(locked_path(guard['script']))!=guard['sha256']:raise RuntimeError('Resource guard bytes changed')
 env_args=['PYTHONPATH='+os.environ['PYTHONPATH'],'PYTHONNOUSERSITE=1','PYTHONDONTWRITEBYTECODE=1']+[key+'='+value for key,value in lock.get('runtime_environment',{}).items()]
 if 'MUJOCO_GL' in os.environ:env_args+=['MUJOCO_GL='+os.environ['MUJOCO_GL']]
 command=[guard['python'],str(locked_path(guard['script'])),'--name','native50_local_'+a.mode,'--memory-gib',str(a.memory_gib),'--timeout',str(a.timeout_s),'--cwd',str(bundle),'--','/usr/bin/env',*env_args,*argv]
 print('RESOURCE_GUARD '+json.dumps(dict(aggregate_memory_GiB=32,job_memory_GiB=a.memory_gib,max_jobs=2,swap_bytes=0,timeout_s=a.timeout_s,automatic_retry=False,command=command)),flush=True)
 os.execv(guard['python'],command)
if __name__=='__main__':main()
