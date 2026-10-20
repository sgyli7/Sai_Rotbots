"""Priority actual12 AR/metal finite queries, while broad shell distances run.
This is an independent geometry query only; the source contract is immutable.
"""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1")
from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.gp import gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp


def ident(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())


def main(output):
    os.sched_setaffinity(0,{7})
    c=json.loads((output/'pose_contract.json').read_text());parts={r['role']:r for r in c['parts']};shapes={}
    for role,p in parts.items():
        if not any(role.endswith('_'+k) for k in ['AR','Al','steel','AP','shin']):continue
        path=Path(p['source']['path']);assert ident(path)['sha256']==p['source']['sha256']
        s=TopoDS_Shape();assert BRepTools.Read_s(s,str(path),BRep_Builder());shapes[role]=s
    cache_path=output/'native_foot_priority_v1.partial.json'
    previous=json.loads(cache_path.read_text()) if cache_path.exists() else {'rows':[]}
    cache={(r['label'],tuple(r['role_pair'])):r for r in previous['rows']}
    result=dict(script=ident(Path(__file__)),pose_contract=ident(output/'pose_contract.json'),
                scope='Five finite recorded actual states, mandatory AR versus AP metal pairs only; no integration or new hardware.',
                physics_steps=0,LP_calls=0,geometry_edits=0,rows=[])
    for st in sorted(c['states'],key=lambda x:x['time_s']):
        moved={}
        for role,s in shapes.items():
            t=np.array(st['CAD_zero_to_world_mm'][parts[role]['owner']]);g=gp_Trsf();g.SetValues(*t[:3,:].ravel().tolist());moved[role]=BRepBuilderAPI_Transform(s,g,True).Shape()
        pairs=[(side+'_AR',side+'_'+metal) for side in ['left','right'] for metal in ['Al','steel']]
        for ra,rb in pairs:
            cached=cache.get((st['label'],(ra,rb)))
            if cached is not None:
                result['rows'].append(cached);(output/'native_foot_priority.partial.json').write_text(json.dumps(result,indent=2)+'\n');print('CACHED '+json.dumps(cached),flush=True);continue
            start=time.monotonic();a,b=moved[ra],moved[rb];d=BRepExtrema_DistShapeShape(a,b);d.Perform();assert d.IsDone();gap=float(d.Value());volume=0.
            if gap<1e-6:
                op=BRepAlgoAPI_Common(a,b);op.SetRunParallel(False);op.Build();assert op.IsDone();p=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),p);volume=float(p.Mass())
                if volume>1e-9:BRepTools.Write_s(op.Shape(),str(output/(st['label']+'_'+ra+'_'+rb+'_foot_Common.brep')))
            row=dict(label=st['label'],time_s=st['time_s'],state_semantics=st['semantics'],role_pair=[ra,rb],native_distance_mm=gap,Common_mm3=volume,nearest_points_world_mm=[list(d.PointOnShape1(1).Coord()),list(d.PointOnShape2(1).Coord())],elapsed_s=time.monotonic()-start)
            result['rows'].append(row);(output/'native_foot_priority.partial.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(row),flush=True)
    p=output/'native_foot_priority.json';p.write_text(json.dumps(result,indent=2)+'\n');print('FINAL '+str(p),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args().output)
