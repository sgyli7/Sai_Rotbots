"""Bounded intrinsic native integrity inventory for a hashed assembly scene.

Unmapped display pieces and timeouts stay unknown. Does not check placements,
assembly fit, minimum walls, purchased qualification, or manufacturing release.
"""
from pathlib import Path
import argparse, hashlib, json, multiprocessing, platform, time
from build123d import import_brep
from sai_agent.native_cad_query import native_solid_integrity
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def work(pipe,row):
 try:
  path=R/row['source']
  if sha(path)!=row['sha256']:raise ValueError('Changed declared native source')
  pipe.send(dict(**row,**native_solid_integrity(import_brep(path))))
 except Exception as e:pipe.send(dict(**row,error=repr(e)))
 finally:pipe.close()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--scene',required=True);ap.add_argument('--output',required=True);ap.add_argument('--seconds-per-part',type=float,default=10);ap.add_argument('--seconds-total',type=float,default=600);a=ap.parse_args()
 if a.seconds_per_part<=0 or a.seconds_total<=0:raise ValueError('Positive timeboxes required')
 sp=R/a.scene;out=R/a.output
 for p in [sp,out]:
  if not p.resolve().is_relative_to(R.resolve()):raise ValueError('Paths must stay within the robot directory')
 scene=json.loads(sp.read_text());lookup={};inputs=[sp,Path(__file__),ROOT/'src/sai_agent/native_cad_query.py']
 for file in sorted((R/'cad/exports').glob('*/manifest.json')):
  data=json.loads(file.read_text())
  for part in data.get('parts',[]):
   f=part.get('files',{})
   if 'npz' in f and 'brep' in f:
    key=(f['npz']['path'],f['npz']['sha256']);rec=f['brep']
    if key in lookup and lookup[key]!=rec:raise ValueError('Conflicting native lineage')
    lookup[key]=rec
  inputs.append(file)
 items=[];missing=[]
 for part in scene['parts']:
  rec=lookup.get((part.get('geometry_npz'),part.get('source_sha256')))
  if rec:items.append(dict(name=part['name'],source=rec['path'],sha256=rec['sha256']))
  else:missing.append(part['name'])
 items.sort(key=lambda x:x['name']);active=[];results=[];started=time.monotonic()
 # Separate Linux fork workers give each native CAD query a real termination
 # boundary; a timed-out thread is insufficient to bound an OCCT operation.
 ctx=multiprocessing.get_context('fork')
 while items or active:
  while items and len(active)<3 and time.monotonic()-started<a.seconds_total:
   row=items.pop(0);recv,send=ctx.Pipe(False);proc=ctx.Process(target=work,args=(send,row));proc.start();send.close();active.append((proc,recv,row,time.monotonic()))
  for entry in active[:]:
   proc,recv,row,t0=entry
   if recv.poll():
    try:result=recv.recv()
    except EOFError:result=dict(**row,error='NO_NATIVE_RESULT')
    proc.join();recv.close();results.append(result);active.remove(entry)
   elif not proc.is_alive() or time.monotonic()-t0>a.seconds_per_part:
    error='NATIVE_INTEGRITY_QUERY_TIMEBOX' if proc.is_alive() else 'NO_NATIVE_RESULT'
    if proc.is_alive():proc.terminate()
    proc.join();recv.close();results.append(dict(**row,error=error));active.remove(entry)
   else:continue
   if len(results)%100==0:print('NATIVE INVENTORY',len(results),flush=True)
  if items and time.monotonic()-started>=a.seconds_total:
   results.extend(dict(**row,error='GLOBAL_INTEGRITY_TIMEBOX') for row in items);items=[]
  if active:time.sleep(.02)
 results.sort(key=lambda x:x['name'])
 counts=dict(checked_native=len(results),passed=sum(bool(x.get('boolean_input_integrity_pass')) for x in results),failed=sum(x.get('boolean_input_integrity_pass') is False for x in results),unknown=sum('error' in x for x in results),unmapped_display=len(missing))
 report=dict(schema='goose_scene_intrinsic_native_integrity_v1',scene=str(sp.relative_to(ROOT)),scene_sha256=sha(sp),environment=dict(python=platform.python_version(),platform=platform.platform()),counts=counts,results=results,unmapped_display_names=missing,seconds_per_part=a.seconds_per_part,seconds_total=a.seconds_total,wall_seconds=time.monotonic()-started,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs},complete_native_source_inventory_pass=not missing and not counts['unknown'] and not counts['failed'],manufacturing_release=False,scope='Intrinsic source solids only; display lineage inventory is not placement, fit, minimum-wall or supplier qualification')
 out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(counts),flush=True)
if __name__=='__main__':main()
