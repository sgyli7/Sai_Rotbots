"""Separate convex collision assets from the current closed component surfaces.

CoACD uses metric metres. Each hull stays a separate asset in every backend;
merging a hollow part into a single convex mesh would fill its openings.
This candidate decomposition is not a manufacturing or gait release.
"""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
import trimesh
import coacd
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'robots/Goose_V0.1'
sys.path.insert(0,str(ROOT/'scripts/models'))
from build_goose_stage_two import candidate


def main():
    path=R/'cad/source/mechanical_preview/scene.json';scene=json.loads(path.read_text())
    ledger_path=R/'evidence/body_bay_mechanical_parameters.json';ledger=json.loads(ledger_path.read_text())
    owners={i['name']:i['body'] for i in ledger['items']};s=candidate()
    # Native STL avoids feeding CoACD the six triangular subdivisions of
    # each original CAD triangle introduced solely to supply editable quads.
    # Both representations remain separately hashed and volume-checked.
    native_stl={};extra_inputs=[]
    for folder in ['bill_backbones','jaw_retention','grip_cassettes','bill_mount_fasteners']:
        native_path=R/'cad/exports'/folder/'manifest.json';extra_inputs.append(native_path)
        for p in json.loads(native_path.read_text())['parts']:
            native_stl[p['name']]=p
    out=R/'models/mechanical_collisions';out.mkdir(exist_ok=True);records=[]
    coacd.set_log_level('warn')
    options=dict(threshold=.001,preprocess_mode='off',resolution=1000,mcts_nodes=10,mcts_iterations=30,mcts_max_depth=2,
        merge=True,decimate=True,max_ch_vertex=64,seed=0,real_metric=True)
    for index,p in enumerate(scene['parts']):
        name=p['name'];owner=p.get('body') or owners.get(name) or s.owner(name)
        if name.endswith('_flexible_sole'):
            records.append(dict(name=name,body=owner,method='six_passive_leaf_contacts',hulls=[],contact_geometry_separate=True));continue
        native_part=native_stl.get(name)
        decomposition_source=None
        native_stl_validation=None
        if native_part is not None:
            if p.get('source_sha256')!=native_part['files']['npz']['sha256']:
                raise ValueError((name,'native collision/quad identity mismatch'))
            stl_info=native_part['files']['stl'];stl_file=R/stl_info['path']
            if hashlib.sha256(stl_file.read_bytes()).hexdigest()!=stl_info['sha256']:
                raise ValueError((name,'native collision STL hash mismatch'))
            decomposition_source=dict(path=stl_info['path'],sha256=stl_info['sha256'],
                input_unit='mm',scale_to_m=.001,method='native_cad_stl_before_display_quad_subdivision')
        source_hash=(p['source_sha256'] if 'geometry_npz' in p else
                     hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest())
        if 'geometry_npz' in p and hashlib.sha256((R/p['geometry_npz']).read_bytes()).hexdigest()!=source_hash:
            raise ValueError((name,'collision/quad input hash mismatch'))
        cache=out/(name+'.json')
        if cache.exists():
            c=json.loads(cache.read_text())
            if c.get('source_sha256')==source_hash and c.get('options')==options and c.get('decomposition_source')==decomposition_source and all(hashlib.sha256((R/h['path']).read_bytes()).hexdigest()==h['sha256'] for h in c['hulls']):
                if c['body']!=owner:
                    c['body']=owner
                    cache.write_text(json.dumps(c,indent=2)+'\n')
                records.append(c);print(index+1,name,'cached',len(c['hulls']),flush=True);continue
        if native_part is not None:
            mesh=trimesh.load(stl_file,force='mesh',process=True)
            mesh.apply_scale(.001)
            relative_error=abs(mesh.volume*1e9/native_part['volume_mm3']-1)
            com_error_m=float(np.linalg.norm(mesh.center_mass-native_part['center_of_mass_world_m']))
            if relative_error>=.005 or com_error_m>=.00015:
                raise ValueError((name,'native STL volume gate',relative_error))
            native_stl_validation=dict(volume_relative_error=relative_error,com_error_m=com_error_m)
        elif 'geometry_npz' in p:
            source=R/p['geometry_npz'];assert hashlib.sha256(source.read_bytes()).hexdigest()==p['source_sha256']
            with np.load(source,allow_pickle=False) as q:v=q['vertices'].copy();f=q['faces'].copy()
            source_hash=p['source_sha256']
        else:v=np.array(p['vertices']);f=np.array(p['faces']);source_hash=hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()
        # The native quad source already shares edge indices. Do not merge
        # distinct vertices within Trimesh's default 1e-8 metre tolerance;
        # merging thin trimmed seams can turn a closed surface non-manifold.
        if native_part is None:
            triangles=np.concatenate([f[:,[0,1,2]],f[:,[0,2,3]]]);mesh=trimesh.Trimesh(v,triangles,process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:raise ValueError((name,'invalid collision input'))
        start=time.monotonic()
        if mesh.is_convex:parts=[(mesh.vertices,mesh.faces)];method='already_convex_source'
        else:parts=coacd.run_coacd(coacd.Mesh(mesh.vertices,mesh.faces),**options);method='coacd_metric_separate_hulls'
        hulls=[]
        for k,(points,faces) in enumerate(parts):
            hull=trimesh.Trimesh(points,faces,process=True)
            # CoACD occasionally emits inconsistent triangulation on nearly
            # coplanar facets. Recompute the convex boundary of those same
            # points; this does not fill cavities in the source component.
            rebuilt=False
            if not hull.is_watertight or not hull.is_winding_consistent or not hull.is_convex:
                hull=trimesh.convex.convex_hull(np.asarray(points,dtype=float));rebuilt=True
            if not hull.is_watertight or not hull.is_winding_consistent or hull.volume<=0 or not hull.is_convex:raise ValueError((name,k,'invalid hull'))
            output=out/(name+f'_{k:03d}.obj');hull.export(output,include_normals=False)
            hulls.append(dict(path=str(output.relative_to(R)),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),vertices=len(hull.vertices),triangles=len(hull.faces),volume_m3=float(hull.volume),coacd_point_hull_rebuilt=rebuilt))
        c=dict(name=name,body=owner,source_sha256=source_hash,options=options,method=method,hulls=hulls,
            decomposition_source=decomposition_source,
            native_stl_validation=native_stl_validation,
            source_volume_m3=float(mesh.volume),sum_hull_volume_m3=sum(h['volume_m3'] for h in hulls),
            duration_s=time.monotonic()-start,unit='m',closed_source=True,collision_release=False)
        cache.write_text(json.dumps(c,indent=2)+'\n');records.append(c)
        print(index+1,name,'hulls',len(hulls),'seconds',round(c['duration_s'],2),flush=True)
    result=dict(schema='goose_current_collision_decomposition_v1',parts=records,convex_hulls=sum(len(p['hulls']) for p in records),
        geometry_unit='m',options=options,manufacturing_pass=False,physical_collision_release=False,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,ledger_path,*extra_inputs,Path(__file__)]},
        tool=dict(name='CoACD',version='1.0.14',source='https://github.com/SarahWeiii/CoACD'),
        limitations=['Approximate metric convex decomposition,1mm requested concavity; not a certified continuous clearance bound.',
            'Sum of hull volumes can include overlaps and is not a union-volume error measurement.',
            'Includes explicit unreleased head/shoe architecture surfaces; native CAD authority and full installation gates remain separate.',
            'Flexible soles use six passive idealized leaf contacts rather than a filled rigid sole mesh.',
            'Actual mating connectors, fastener head sweeps and cables remain absent; this is not a final hardware model.'])
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print('collision hulls',result['convex_hulls'],flush=True)

if __name__=='__main__':main()
