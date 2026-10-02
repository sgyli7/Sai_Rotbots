#!/usr/bin/env python3
"""Check native segmented-foot endpoints; no load or continuous sweep approval."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/gorilla_v0_1'

def triangles(p):
 v=np.asarray(p['vertices_world_m']);return np.asarray([[v[f[0]],v[f[i]],v[f[i+1]]] for f in p['faces'] for i in range(1,len(f)-1)])

def mesh(p):
 v=np.asarray(p['vertices_world_m']);f=np.asarray([[f[0],f[i],f[i+1]] for f in p['faces'] for i in range(1,len(f)-1)])
 return trimesh.Trimesh(v,f,process=False)

def ray_values(part,points,direction):
 tri=triangles(part);a=tri[:,0];e1=tri[:,1]-a;e2=tri[:,2]-a
 d=np.asarray(direction,float);h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h)
 safe=abs(det)>1e-11;inv=np.zeros_like(det);inv[safe]=1/det[safe];out=[]
 for point in points:
  q=point-a;u=inv*np.einsum('ij,ij->i',q,h);c=np.cross(q,e1);v=inv*np.einsum('ij,j->i',c,d);t=inv*np.einsum('ij,ij->i',e2,c)
  hit=np.sort(t[safe&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>1e-7)]);hit=hit[np.r_[True,np.diff(hit)>1e-7]] if len(hit) else hit;out.append(hit)
 return out

def inside(part,points):
 vals=ray_values(part,points,[1.,.137,.193]);return np.array([len(v)%2==1 for v in vals])

def triangle_surface_hits(a,b):
 # Complete triangle SAT, including the in-plane axes required for coplanar
 # annulus faces; returns true touch/intersection pairs, not just AABB overlap.
 aa,bb=triangles(a),triangles(b);al,ah=aa.min(1),aa.max(1);bl,bh=bb.min(1),bb.max(1)
 ia,ib=np.where(np.all(ah[:,None]>=bl[None]-1e-8,axis=2)&np.all(bh[None]>=al[:,None]-1e-8,axis=2))
 if not len(ia):return []
 aa,bb=aa[ia],bb[ib];ea=np.roll(aa,-1,axis=1)-aa;eb=np.roll(bb,-1,axis=1)-bb
 na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1]);axes=[na,nb]
 axes.extend(np.cross(ea[:,i],eb[:,j]) for i in range(3) for j in range(3))
 axes.extend(np.cross(na,ea[:,i]) for i in range(3));axes.extend(np.cross(nb,eb[:,i]) for i in range(3))
 keep=np.ones(len(ia),bool)
 for axis in axes:
  norm=np.linalg.norm(axis,axis=1);valid=norm>1e-12;p=np.einsum('pvi,pi->pv',aa,axis);q=np.einsum('pvi,pi->pv',bb,axis)
  overlap=(p.max(1)>=q.min(1)-norm*1e-7)&(q.max(1)>=p.min(1)-norm*1e-7);keep&=overlap|~valid
 return np.column_stack([ia[keep],ib[keep]]).tolist()

def relation(a,b):
    hits=triangle_surface_hits(a,b)
    contained=0
    for source,target in ((a,b),(b,a)):
        vertices=np.asarray(source['vertices_world_m'])
        flags=inside(target,vertices)
        if flags.any():
            _,distance,_=trimesh.proximity.closest_point_naive(mesh(target),vertices[flags])
            contained+=int(np.count_nonzero(distance>2e-7))
    return {'parts':[a['name'],b['name']],
            'surface_touch_or_crossing_triangle_pairs':len(hits),
            'strict_material_vertex_containment_count':contained}


def transformed(parts,side,folded):
    result=[]
    for original in parts:
        if original.get('composite_foot_side')!=side:continue
        p=copy.deepcopy(original);v=np.asarray(p['vertices_world_m']);group=p['composite_foot_group']
        if folded and group in ('forefoot','heel'):
            pivot=np.asarray(p['composite_foot_pivot_world_m']);t=math.radians(-15 if group=='forefoot' else 10)
            rotation=np.array([[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]])
            v=(v-pivot)@rotation.T+pivot
        elif folded and group=='lock':v=v+np.asarray(p['composite_foot_unlock_translation_world_m'])
        p['vertices_world_m']=v.tolist();result.append(p)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,default=ROBOT/'cad/source/appearance_c_scene.json')
    parser.add_argument('--output',type=Path,default=ROBOT/'evidence/composite_foot_c15_screen.json')
    args=parser.parse_args();scene=json.loads(args.scene.read_text())
    parts=[p for p in scene['parts'] if 'composite_foot_group' in p]
    if not parts:raise ValueError('Scene has no segmented foot')
    errors=[];poses=[]
    for p in parts:
        m=mesh(p)
        if not(m.is_watertight and m.is_winding_consistent and m.volume>0):errors.append('Invalid native mesh: '+p['name'])
        if p['composite_foot_axis_world']!=[0.,1.,0.]:errors.append('Unexpected fold axis: '+p['name'])
    for side in ('left','right'):
        for folded in (False,True):
            posed=transformed(parts,side,folded);hits=[];expected=[]
            allowed={frozenset((f'{side}_composite_{flank}_{segment}_rotor',
                       f'{side}_composite_{flank}_{group}_neutral_stop'))
                     for flank in ('negative_y','positive_y') for segment,group in (('fore','forefoot'),('heel','heel'))}
            for i,a in enumerate(posed):
                av=np.asarray(a['vertices_world_m'])
                for b in posed[i+1:]:
                    if a['composite_foot_group']==b['composite_foot_group']:continue
                    bv=np.asarray(b['vertices_world_m'])
                    if np.any(av.max(0)<bv.min(0)-1e-8) or np.any(bv.max(0)<av.min(0)-1e-8):continue
                    result=relation(a,b)
                    if not(result['surface_touch_or_crossing_triangle_pairs'] or result['strict_material_vertex_containment_count']):continue
                    if not folded and frozenset(result['parts']) in allowed and result['strict_material_vertex_containment_count']==0:expected.append(result)
                    else:hits.append(result)
            if hits:errors.append(f'{side} {"folded" if folded else "neutral"}: unclassified cross-group contact')
            if not folded and {frozenset(h['parts']) for h in expected}!=allowed:errors.append(side+': neutral stops are not all seated')
            poses.append({'id':side+('_unloaded_fold' if folded else '_neutral'),
                'angles_deg':{'forefoot':-15 if folded else 0,'heel':10 if folded else 0},
                'locks_withdrawn':folded,'expected_stop_contacts':expected,'unexpected_contacts':hits})
            print(poses[-1]['id'], 'unexpected',len(hits),flush=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'schema':'gorilla_composite_foot_geometry_v1','robot_id':'gorilla_v0_1',
        'scene_path':str(args.scene.resolve().relative_to(ROOT)),'scene_sha256':sha(args.scene),
        'checker_path':str(Path(__file__).resolve().relative_to(ROOT)),'checker_sha256':sha(Path(__file__)),
        'native_foot_part_count':len(parts),'poses':poses,'errors':errors,
        'bounded_native_geometry_screen_passed':not errors,
        'scope':'Native closed oriented parts and cross-group triangle SAT/material-vertex containment at neutral and isolated unloaded endpoints. Expected planar stop touches are classified explicitly; fitted tolerances, intra-group interfaces, applied bevels, full-robot clearance, continuous sweep, support, lock capacity and dynamics are unverified.',
        'appearance_accepted':False,'physics_accepted':False,'new_foot_si_contract_defined':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'errors':errors}));raise SystemExit(0 if not errors else 1)


if __name__=='__main__':main()
