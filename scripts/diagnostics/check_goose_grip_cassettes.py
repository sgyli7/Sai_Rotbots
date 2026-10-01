"""Bounded native fit of grip cassettes against the installed head candidates.

Do not filter pads, carriers, shell windows or screw/nut interference by body
ownership. Nominal thread contacts are measured separately from clearance.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import multiprocessing
import sys
import time

import numpy as np
from build123d import import_brep, import_step
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'robots/Goose_V0.1'
sys.path.insert(0, str(ROOT/'scripts/cad'))
from build_goose_cad import transform
from sai_agent.goose.native_linkage import INPUT_PARTS, COUPLER_PARTS
from sai_agent.native_csg import contained_in_one_void


def baseline_pair_coverage(paths, manifests, additional):
    """Reconstruct exactly the named pair scope of the preserved earlier report.

    That report records interference <=.01mm3, not an exact zero for every
    pair. Its source code and all inputs must still match before inheritance.
    This is never coverage for new parts or for a different jaw angle.
    """
    file = R/'evidence/jaw_retention_native_fit.json'
    report = json.loads(file.read_text())
    if report['schema'] != 'goose_jaw_retention_native_fit_v1':
        raise ValueError('Unknown inherited native report schema')
    for path, expected in report['source_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError(('Stale inherited native report', path))
    records = {}
    for path, manifest in zip(paths[:-1], manifests[:-1]):
        for name in manifest.get('replaces_existing_parts', []) + additional.get(path.parent.name, []):
            records.pop(name, None)
        records.update({p['name']: p for p in manifest['parts']})
    names = set(records) | {'rear_clip_any_orientation_envelope'}
    new = {p['name'] for p in manifests[-2]['parts']} | {'rear_clip_any_orientation_envelope'}
    omitted = frozenset(['rear_clip_any_orientation_envelope', 'jaw_rear_din471_ring'])
    pairs = {frozenset((a, b)) for a, b in itertools.combinations(names, 2)
             if (a in new or b in new) and frozenset((a, b)) != omitted}
    if len(pairs) != report['tested_pair_count'] or len(records) != report['checked_native_parts']:
        raise ValueError('Inherited native pair scope mismatch')
    if len(report['cases']) != 23 or not all(c['sampled_geometry_pass'] and not c['collisions']
                                            for c in report['cases']):
        raise ValueError('Inherited native report is not a passed 23-pose matrix')
    angles = [c['q_rad'] for c in report['cases']]
    return records, pairs, angles, dict(path=str(file.relative_to(ROOT)),
                                       sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                                       volume_upper_bound_mm3=.01)


def common_worker(connection, a, b):
    # Parent already uses conservative non-optimal native bounds. Avoid the
    # expensive optimal-box reconstruction in the general helper here.
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopTools import TopTools_ListOfShape
    try:
        arguments=TopTools_ListOfShape();arguments.Append(a.wrapped)
        tools=TopTools_ListOfShape();tools.Append(b.wrapped)
        operation=BRepAlgoAPI_Common();operation.SetArguments(arguments);operation.SetTools(tools)
        operation.SetNonDestructive(True);operation.SetUseOBB(True);operation.Build()
        if not operation.IsDone():raise ValueError('OCCT common did not finish')
        explorer=TopExp_Explorer(operation.Shape(),TopAbs_SOLID);volume=0.
        while explorer.More():
            properties=GProp_GProps()
            BRepGProp.VolumeProperties_s(explorer.Current(),properties,True)
            volume+=float(properties.Mass());explorer.Next()
        if volume< -1e-7:raise ValueError('Negative common volume')
        connection.send(dict(volume_mm3=volume))
    except Exception as error:
        connection.send(dict(error=repr(error)))
    finally:
        connection.close()


def bounded_common(a,b,timeout):
    context=multiprocessing.get_context('fork')
    receive,send=context.Pipe(duplex=False)
    process=context.Process(target=common_worker,args=(send,a,b));started=time.monotonic()
    process.start();send.close();process.join(timeout)
    if process.is_alive():
        process.terminate();process.join(2)
        if process.is_alive():process.kill();process.join()
        result=dict(error='NATIVE_PAIR_TIMEBOX')
    elif receive.poll():
        try:result=receive.recv()
        except EOFError:result=dict(error='NATIVE_PAIR_PIPE_EOF_'+str(process.exitcode))
    else:result=dict(error='NATIVE_PAIR_PROCESS_EXIT_'+str(process.exitcode))
    receive.close();result['wall_seconds']=time.monotonic()-started
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wall-time',type=float,default=180.)
    parser.add_argument('--pair-timeout',type=float,default=8.)
    parser.add_argument('--scope',choices=['full','mechanical_core'],default='full')
    args=parser.parse_args();started=time.monotonic()
    folders = ['head_load_path','beak_native_linkage','bill_backbones','jaw_retention','grip_cassettes']
    paths = [R/'cad/exports'/f/'manifest.json' for f in folders]
    manifests = [json.loads(p.read_text()) for p in paths]
    replacement_file = R/'configs/mechanical_native_replacements.json'
    additional = json.loads(replacement_file.read_text())['additional_replaces_by_folder']
    shapes, groups = {}, {}
    for folder, manifest in zip(folders, manifests):
        for name in manifest.get('replaces_existing_parts',[])+additional.get(folder,[]):
            shapes.pop(name,None); groups.pop(name,None)
        for p in manifest['parts']:
            f=R/p['files']['step']['path']
            assert hashlib.sha256(f.read_bytes()).hexdigest()==p['files']['step']['sha256'],p['name']
            shapes[p['name']]=import_step(f).solids()[0]
            groups[p['name']]=('input' if p['name'] in INPUT_PARTS else
                               'coupler' if p['name'] in COUPLER_PARTS else
                               'jaw' if p['body']=='beak_hinge' else 'fixed')
        print('GRIP INPUT',folder,'current native solids',len(shapes),flush=True)
    kit=manifests[-1]; new={p['name'] for p in kit['parts']}
    for path, expected in kit['source_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError(('Stale native CSG construction source', path))
    old_records, old_pairs, old_angles, baseline = baseline_pair_coverage(paths, manifests, additional)
    # The original backbone manifest also embeds exact measured closed-pose
    # commons. Only pairs of unchanged, same-body predecessors are reusable
    # under a common rigid transform; nothing is inferred for cross-body pairs.
    original_bones=manifests[2]
    for path, expected in original_bones['source_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError(('Stale initial backbone fit source',path))
    original_records={p['name']:p for p in original_bones['parts']}
    rigid_baselines={}
    for record in original_bones['initial_fit']:
        a,b=record['candidate'],record['other']
        if (a in old_records and b in old_records and
            old_records[a]==original_records.get(a) and old_records[b]==original_records.get(b) and
            old_records[a]['body']==old_records[b]['body'] and record['pass_no_interference']):
            rigid_baselines[frozenset((a,b))]=dict(
                path=str(paths[2].relative_to(ROOT)),sha256=hashlib.sha256(paths[2].read_bytes()).hexdigest(),
                volume_upper_bound_mm3=record['common_volume_mm3'],
                method='embedded_exact_predecessor_common_same_body_rigid_invariance')
    relations = kit.get('native_csg_relations', {})
    operands, predecessors = {}, {}
    for name, relation in relations.items():
        old = relation['predecessor']
        if old != old_records.get(old['name']) or not relation['subset_of_predecessor_union_additions']:
            raise ValueError(('Native CSG predecessor identity mismatch', name))
        predecessors[name] = import_step(R/old['files']['step']['path']).solids()[0]
        operands[name] = {}
        for kind in ['additive_solids', 'subtractive_solids']:
            operands[name][kind] = []
            for record in relation[kind]:
                file = R/record['path']
                if record['unit'] != 'mm' or hashlib.sha256(file.read_bytes()).hexdigest() != record['sha256']:
                    raise ValueError(('Native CSG operand identity mismatch', name, record))
                shape = import_brep(file)
                if not shape.is_valid or len(shape.solids()) != 1:
                    raise ValueError(('Native CSG operand validity', name, record))
                operands[name][kind].append(shape.solids()[0])
    excluded=[]
    if args.scope=='mechanical_core':
        excluded=['upper_grip_shell','lower_grip_shell','head_bill_access_shell_left',
                  'head_retention_access_shell_right']
        for name in excluded:
            if name not in shapes:raise ValueError(('missing declared excluded skin',name))
            shapes.pop(name);groups.pop(name);new.discard(name)
    threads={frozenset([p['screw'],p['nut']]):p for p in kit['nominal_thread_contacts']}
    pairs=[(a,b) for a,b in itertools.combinations(shapes,2) if a in new or b in new]
    pairs.sort(key=lambda p:(0 if frozenset(p) in threads else 1 if p[0] in new and p[1] in new else 2))
    m=np.array(manifests[1]['motor_axis_world_mm']); j=np.array(manifests[1]['jaw_axis_world_mm'])
    phase=manifests[1]['closed_phase_rad'];radius=manifests[1]['crank_radius_mm']
    crank=radius*np.array([np.cos(phase),0,np.sin(phase)])
    cache,cases={},[];unresolved_cache={};native_queries=[];certificates=[];wall_stop=False
    for q in np.linspace(0,.55,23):
        rotation=Rotation.from_rotvec([0,q,0]).as_matrix(); posed={}; bounds={}
        for n,s in shapes.items():
            group=groups[n]
            posed[n]=(s if group=='fixed' else transform(s,rotation,j-rotation@j)
                      if group=='jaw' else transform(s,rotation,m-rotation@m)
                      if group=='input' else transform(s,np.eye(3),rotation@crank-crank))
            bb=posed[n].bounding_box(optimal=False);bounds[n]=(np.array(tuple(bb.min)),np.array(tuple(bb.max)))
        print('GRIP POSE BOUNDS READY',round(q,3),flush=True)
        def pose(shape, name):
            group=groups[name]
            return (shape if group=='fixed' else transform(shape,rotation,j-rotation@j)
                    if group=='jaw' else transform(shape,rotation,m-rotation@m)
                    if group=='input' else transform(shape,np.eye(3),rotation@crank-crank))

        placed_operands = {n: {kind: [pose(s, n) for s in items]
                               for kind, items in record.items()}
                           for n, record in operands.items() if n in shapes}
        ancestor_bounds = {}

        def enclosing_bounds(name):
            if name not in ancestor_bounds:
                shape = pose(predecessors[name], name) if name in predecessors else posed[name]
                bb = shape.bounding_box()
                lo, hi = np.array(tuple(bb.min)), np.array(tuple(bb.max))
                for added in placed_operands.get(name, {}).get('additive_solids', []):
                    ab = added.bounding_box(optimal=False)
                    lo=np.minimum(lo, tuple(ab.min)); hi=np.maximum(hi, tuple(ab.max))
                ancestor_bounds[name] = lo, hi
            return ancestor_bounds[name]

        def certify(a, b):
            # If P is contained in a recorded void V and B = predecessor - V,
            # B intersect P is bounded by the measured P - V remainder.
            for target, part in [(a,b),(b,a)]:
                voids=placed_operands.get(target, {}).get('subtractive_solids', [])
                if voids:
                    proof=contained_in_one_void(posed[part], voids)
                    if proof is not None:
                        return dict(method='recorded_native_subtraction_containment',
                                    target=target, part=part, **proof,
                                    volume_upper_bound_mm3=proof['outside_volume_mm3'])
            pa=relations[a]['predecessor']['name'] if a in relations else a
            pb=relations[b]['predecessor']['name'] if b in relations else b
            if not (a in relations or b in relations):
                return None
            key=frozenset((pa,pb))
            if key in old_pairs and any(abs(q-angle)<1e-12 for angle in old_angles):
                prior=baseline
            elif groups[a]==groups[b] and key in rigid_baselines:
                prior=rigid_baselines[key]
            else:
                return None
            additions=[]
            # A' subset A union added_A; B' subset B union added_B. The earlier
            # A/B bound can be inherited only after every added solid is
            # independently shown disjoint from the complete other new part.
            for source, other in [(a,b),(b,a)]:
                for index, added in enumerate(placed_operands.get(source, {}).get('additive_solids', [])):
                    bb=added.bounding_box(optimal=False)
                    lo,hi=np.array(tuple(bb.min)),np.array(tuple(bb.max))
                    olo,ohi=enclosing_bounds(other)
                    if np.any(np.minimum(hi,ohi)-np.maximum(lo,olo)<=1e-6):
                        additions.append(dict(source=source,index=index,method='native_enclosing_aabb_separation'))
                        continue
                    proof=contained_in_one_void(added, placed_operands.get(other, {}).get('subtractive_solids', []))
                    if proof is not None and proof['outside_volume_mm3']==0:
                        additions.append(dict(source=source,index=index,method='native_added_solid_in_removed_void',**proof))
                        continue
                    return None
            return dict(method='source_bound_subtraction_inheritance_with_added_solid_checks',
                        predecessor_pair=[pa,pb], additions=additions,
                        baseline=prior, volume_upper_bound_mm3=prior['volume_upper_bound_mm3'])

        hits,contacts,unresolved=[],[],[];tested=0
        for a,b in pairs:
            if time.monotonic()-started>args.wall_time:
                wall_stop=True;break
            key=frozenset([a,b]);invariant=groups[a]==groups[b]
            if invariant and key in unresolved_cache:
                unresolved.append(dict(a=a,b=b,**unresolved_cache[key],invariant_cached=True))
                continue
            if invariant and key in cache:v=cache[key]
            elif np.any(np.minimum(bounds[a][1],bounds[b][1])-np.maximum(bounds[a][0],bounds[b][0])<=1e-6):v=0.
            else:
                proof=certify(a,b)
                if proof is not None:
                    certificates.append(dict(q_rad=float(q),a=a,b=b,**proof))
                    v=proof['volume_upper_bound_mm3']
                else:
                    result=bounded_common(posed[a],posed[b],min(args.pair_timeout,max(.1,args.wall_time-(time.monotonic()-started))))
                    native_queries.append(dict(q_rad=float(q),a=a,b=b,**result))
                    if 'error' in result:
                        if invariant:unresolved_cache[key]=result
                        unresolved.append(dict(a=a,b=b,**result))
                        print('GRIP UNRESOLVED',a,b,result['error'],flush=True)
                        continue
                    v=result['volume_mm3']
            if invariant:cache[key]=v
            tested+=1
            if key in threads:
                expected=threads[key]['expected_thread_overlap_mm3']
                contacts.append(dict(a=a,b=b,intersection_mm3=v,expected_nominal_thread_overlap_mm3=expected,
                                     nominal_thread_contact_pass=abs(v-expected)<.02))
            elif v>.01:hits.append(dict(a=a,b=b,intersection_mm3=v))
        passed=not hits and not unresolved and tested==len(pairs) and len(contacts)==8 and all(p['nominal_thread_contact_pass'] for p in contacts)
        cases.append(dict(jaw_q_rad=float(q),collisions=hits,intended_thread_contacts=contacts,
                          tested_pair_count=tested,unresolved_pairs=unresolved,
                          sampled_geometry_pass=passed))
        print('GRIP CASSETTE FIT',round(q,3),'hits',len(hits),'threads',len(contacts),flush=True)
        for hit in hits:print('COLLISION',hit,flush=True)
        if wall_stop:break
    report=dict(schema='goose_grip_cassette_native_fit_v1',candidate_parts=len(kit['parts']),
                scope=args.scope,checked_increment_parts=len(new),excluded_native_skins=excluded,
                checked_native_parts=len(shapes),tested_pair_count=len(pairs),sample_count=len(cases),
                passed_samples=sum(c['sampled_geometry_pass'] for c in cases),cases=cases,
                complete_sample_matrix=len(cases)==23 and not wall_stop,
                elapsed_wall_seconds=time.monotonic()-started,wall_time_limit_seconds=args.wall_time,
                native_pair_timeout_seconds=args.pair_timeout,native_queries=native_queries,
                native_csg_certificates=certificates, inherited_report=baseline,
                boolean_engine='OCCT direct common with OBB;conservative non-optimal native AABB;isolated Linux fork timeout',
                nominal_mounts=kit['mounts'],installed=False,manufacturing_release=False,
                pad_retention_strength_pass=False,pad_snap_installation_qualified=False,
                source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in paths+[replacement_file,Path(__file__),ROOT/'src/sai_agent/native_csg.py']},
                limitations=[
                    '23discrete nominal jaw poses,new cassette kit against listed head/linkage neighbours;not continuous or whole assembly.',
                    'Eight explicitly measured nominal nut/thread contacts;not actual helical-thread/preload qualification.',
                    'Mushroom pad positive-retention geometry requires elastic installation;material friction,strain,tear,creep and wear not qualified.',
                    'Updated backbone nut bosses and pad reliefs require fresh local stress/fatigue assessment.',
                    'Nut/screw port geometry is not a complete tool approach or assembly-order proof.',
                    'Not installed in314-part scene,ledger,runtime or current four colour images.',
                    'Native pair timeout/process failure or untested pair is unresolved,never counted as zero intersection or a passed pose.',
                    'Mechanical-core scope,when selected,explicitly omits four declared skins;it cannot supersede the separate full fit report or release those interfaces.',
                    'Recorded native CUT containment and source-bound subtraction inheritance are separately labelled volume upper bounds,not fabricated direct common volumes. Earlier pair scope/source hashes/angles and every added boss are checked before inheritance.',
                ])
    filename='grip_cassette_native_fit.json' if args.scope=='full' else 'grip_cassette_core_native_fit.json'
    (R/'evidence'/filename).write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['complete_sample_matrix'] and report['passed_samples']==23 else 1


if __name__=='__main__':
    raise SystemExit(main())
