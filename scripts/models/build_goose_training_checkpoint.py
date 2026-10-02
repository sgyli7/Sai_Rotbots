"""Build a bounded, source-locked training checkpoint; no hardware release.

Reuses only hashed unchanged collision shapes. New concave shapes use local
5 mm surface clusters, explicitly approximate. Visuals are source-derived LOD;
the source scene and four full-resolution renders remain appearance authority.
"""
from pathlib import Path
import copy,hashlib,json,sys,time
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
import build_goose_mechanical_reference as reference
from build_goose_stage_two import candidate

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')

def main():
    source=R/'cad/source/one_piece_head_service_fixture/assembly_scene.json'
    lp=R/'evidence/one_piece_head_service_parameters.json'
    scene=json.loads(source.read_text());ledger=json.loads(lp.read_text());base=json.loads((R/'evidence/body_bay_mechanical_parameters.json').read_text())
    for d in [scene,ledger]:
        for p,h in d['source_hashes'].items():
            if sha(ROOT/p)!=h:raise ValueError(('stale source',p))
    for k in ['contact_hulls','grip_world_at_zero_m','tip_world_at_zero_m','native_beak_transmission']:ledger[k]=copy.deepcopy(base[k])
    old=json.loads((R/'configs/stage_two_contract.json').read_text())
    # Keep the shared builder intact. Adapt its data/output boundary and bound
    # runtime visual triangle count; no LOD is used for mass/inertia accounting.
    reference.PALETTE.update(pcb_reference=(.04,.18,.10,1),catalog_reference=(.15,.17,.18,1))
    for part in scene['parts']:
        reference.PALETTE.setdefault(part['material'],(.15,.17,.18,1))
    reference.OUT=R/'models/training_reference';reference.CONTRACT=R/'configs/training_reference_contract.json'
    reference.source_inputs=lambda:(old,ledger,scene,[source,lp,R/'evidence/body_bay_mechanical_parameters.json'])
    code=Path(reference.__file__).read_text()
    begin=code.index('def build():');end=code.index("\n\nif __name__ == '__main__':")
    function=code[begin:end].replace("f'mechanical_reference_{suffix}.csv'","f'training_reference_{suffix}.csv'")
    function=function.replace("groups.setdefault((owner, part['material']), []).append(mesh)","if len(mesh.faces)>10000:\n            mesh=mesh.simplify_quadric_decimation(face_count=10000)\n        groups.setdefault((owner, part['material']), []).append(mesh)")
    exec(compile(function,str(Path(__file__)), 'exec'),reference.__dict__)
    existing=json.loads(reference.CONTRACT.read_text()) if reference.CONTRACT.exists() else {}
    if existing.get('visual_lod',{}).get('source_scene_sha256')!=sha(source):reference.build()
    cp=reference.CONTRACT;contract=json.loads(cp.read_text())
    contract['visual_lod']=dict(maximum_triangles_per_part=10000,source_scene_sha256=sha(source),manufacturing_geometry=False,appearance_authority='source quad scene and native CAD; runtime visuals are simplified')
    write(cp,contract)
    prior=json.loads((R/'models/mechanical_collisions/manifest.json').read_text());cache={p['name']:p for p in prior['parts']}
    out=R/'models/training_collisions';out.mkdir(exist_ok=True)
    owners={i['name']:i['body'] for i in contract['items']};system=candidate();records=[]
    import scipy.spatial
    for index,p in enumerate(scene['parts']):
        name=p['name'];owner=p.get('body') or owners.get(name) or system.owner(name)
        source_hash=p.get('source_sha256') or hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()
        cached=cache.get(name)
        if cached and cached.get('source_sha256')==source_hash:
            record=copy.deepcopy(cached);record['body']=owner
            for h in record['hulls']:
                if sha(R/h['path'])!=h['sha256']:raise ValueError(('stale reused hull',name))
            record['reuse_from']='mechanical_collisions';records.append(record);continue
        if name.endswith('_flexible_sole'):
            records.append(dict(name=name,body=owner,source_sha256=source_hash,method='six_passive_leaf_contacts',hulls=[]));continue
        if 'geometry_npz' in p:
            f=R/p['geometry_npz'];assert sha(f)==source_hash
            with np.load(f,allow_pickle=False) as q:v=q['vertices'].copy();faces=q['faces'].copy()
        else:v=np.array(p['vertices']);faces=np.array(p['faces'])
        triangles=np.concatenate([faces[:,[0,1,2]],faces[:,[0,2,3]]]);mesh=trimesh.Trimesh(v,triangles,process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:raise ValueError(('invalid source',name))
        if mesh.is_convex:hulls=[mesh.convex_hull];method='source_convex_hull'
        else:
            method='local_surface_clusters_5mm_approximate'
            if len(mesh.faces)>40000:mesh=mesh.simplify_quadric_decimation(face_count=40000)
            tris=mesh.triangles;bins=np.floor(tris.mean(axis=1)/.005).astype(np.int64)
            _,inverse=np.unique(bins,axis=0,return_inverse=True);order=np.argsort(inverse);cuts=np.r_[0,np.flatnonzero(np.diff(inverse[order]))+1,len(order)]
            hulls=[]
            for a,b in zip(cuts[:-1],cuts[1:]):
                faces_xyz=tris[order[a:b]];points=np.unique(faces_xyz.reshape(-1,3),axis=0)
                if len(points)<3:continue
                if np.linalg.matrix_rank(points-points.mean(axis=0),tol=1e-10)<3:
                    normals=np.cross(faces_xyz[:,1]-faces_xyz[:,0],faces_xyz[:,2]-faces_xyz[:,0]);normal=normals[np.argmax(np.linalg.norm(normals,axis=1))]
                    if np.linalg.norm(normal)<1e-12:continue
                    normal=normal/np.linalg.norm(normal)*.000025;points=np.vstack([points+normal,points-normal])
                h=trimesh.convex.convex_hull(points)
                if h.volume>1e-15:hulls.append(h)
        infos=[]
        for n,h in enumerate(hulls):
            fallback=False
            if not h.is_watertight or not h.is_winding_consistent or h.volume<=0:
                bounds=h.bounds;size=np.maximum(bounds[1]-bounds[0],.00005)
                h=trimesh.creation.box(size);h.apply_translation(bounds.mean(axis=0));fallback=True
            if not h.is_watertight or not h.is_winding_consistent or h.volume<=0:raise ValueError(('invalid hull',name,n))
            f=out/(name+f'_{n:03d}.obj');h.export(f,include_normals=False)
            infos.append(dict(path=str(f.relative_to(R)),sha256=sha(f),vertices=len(h.vertices),triangles=len(h.faces),volume_m3=float(h.volume),degenerate_cluster_aabb_fallback=fallback))
        records.append(dict(name=name,body=owner,source_sha256=source_hash,method=method,hulls=infos,closed_source=True,collision_release=False))
        print('NEW COLLISION',index+1,name,len(infos),flush=True)
    collision=dict(schema='goose_training_checkpoint_collision_v1',parts=records,convex_hulls=sum(len(p['hulls']) for p in records),source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [source,lp,Path(__file__)]},limitations=['Reused unchanged shapes: original CoACD requested concavity1mm; not a certified error bound.','Degenerate local hulls use conservative local AABBs with minimum50micrometre thickness, recorded per hull. New concave shapes: local5mm surface clusters with optional40000-triangle LOD and25micrometre planar thickness; approximate cavities, no global clearance bound.','Not full hardware collision qualification; no walking or manipulation success inferred.'])
    write(out/'manifest.json',collision)
    # Adapt the existing compliant-pad exporter into this independent version.
    path=ROOT/'scripts/models/build_goose_mechanical_physics.py';code=path.read_text()
    code=code.replace("R/'configs/mechanical_reference_contract.json'","R/'configs/training_reference_contract.json'").replace("R/'models/mechanical_collisions/manifest.json'","R/'models/training_collisions/manifest.json'").replace("R/'evidence/body_bay_mechanical_parameters.json'","R/'evidence/one_piece_head_service_parameters.json'").replace("R/'models/mechanical_reference/robot.xml'","R/'models/training_reference/robot.xml'").replace("R/'models/mechanical_reference/robot.urdf'","R/'models/training_reference/robot.urdf'").replace("R/'models/mechanical_physics'","R/'models/training_checkpoint'").replace('../mechanical_reference/','../training_reference/').replace("R/'configs/mechanical_physics_contract.json'","R/'configs/training_checkpoint_contract.json'")
    env={'__file__':str(path),'__name__':'checkpoint_builder'};exec(compile(code,str(path),'exec'),env);env['main']()
    cp=R/'configs/training_checkpoint_contract.json';c=json.loads(cp.read_text())
    c.update(schema='goose_one_piece_head_training_checkpoint_si_v1',status='EXPERIMENTAL_TRAINING_CHECKPOINT_HARDWARE_UNRELEASED',training_release=False,training_entry_verified=False,source_scene_sha256=sha(source),source_part_count=460)
    c['limitations']=[x for x in c['limitations'] if not x.startswith('No collision geometry:')]+['No qualified joint sweep, gait, turn, ground pickup or drag acceptance. Start with nominal stance and low amplitude rejection tests.','AK48 supply, regeneration, watchdog and actual actuator thermal limits are unresolved; this model is not hardware authorization.']
    c['asset_sha256'].update({'../training_reference/'+p:h for p,h in contract['asset_sha256'].items()})
    c['source_hashes'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    write(cp,c)
    print('CHECKPOINT BUILT',c['nominal_robot_mass_kg'],c['active_axes'],len(c['collision_geometries']),flush=True)

if __name__=='__main__':main()
