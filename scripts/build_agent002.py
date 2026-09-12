"""Reproduce Sai_Agent_002 from the preserved 001 and public per-part inputs.

--engineering-source is a one-time import of project/licensed display parts.
Subsequent builds use checked-in source/chassis.npz and never require vendor CAD.
"""
import argparse
from collections import defaultdict
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import mujoco
from prepare_model import prepare
from prepare_public_assets import classification, envelope

ROOT=Path(__file__).resolve().parents[1]
VARIANT=ROOT/'robots/Sai_Agent_002'
SOURCE=VARIANT/'source'
MODELS=VARIANT/'models'
REMOVED_BODIES={'cargo_slide_-1','cargo_slide_1','cargo_rotor'}


def removed(name):
    return ((name.startswith('cargo_') and name not in {'cargo_shell','cargo_mat'})
            or name.startswith(('force_board_', 'maestro')))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def bootstrap(engineering):
    source=engineering/'derived/maestro_mount_r19'
    meta=json.loads((source/'manifest.json').read_text())
    public=json.loads((ROOT/'models/asset_provenance.json').read_text())
    provenance={p['name']:p for p in public['parts']}
    archive={};rows=[]
    for part in meta['parts']:
        name=part['name']
        if removed(name) or part.get('body','chassis') not in {'chassis','arm_base'}:continue
        kind,_,_=classification(part)
        row=copy.deepcopy(provenance[name])
        row['body']='chassis'
        if name in {'cargo_shell','cargo_mat'}:
            mesh=trimesh.load_mesh(VARIANT/'cad'/f'{name}.stl',process=False)
            row.update(origin_kind='project_original',source_note='002 continuous floor restoration',
                       source_mesh_sha256=sha(VARIANT/'cad'/f'{name}.stl'))
        elif kind=='project_envelope':mesh=envelope(part)
        else:
            mesh=trimesh.load_mesh(source/part['file'],process=False)
            if 'transform_m' in part:mesh.apply_transform(np.array(part['transform_m']))
        mesh.merge_vertices(digits_vertex=10)
        limit=6000 if mesh.extents.max()>.12 else 3000 if mesh.extents.max()>.06 else 1000 if mesh.extents.max()>.025 else 256
        if len(mesh.faces)>limit:
            candidate=mesh.simplify_quadric_decimation(face_count=limit)
            if np.max(np.abs(candidate.bounds-mesh.bounds))<.0005:mesh=candidate
        i=len(rows)
        archive[f'v{i}']=np.asarray(mesh.vertices)
        archive[f'f{i}']=np.asarray(mesh.faces)
        row.update(rgba=part['color'],bounds_world_m=mesh.bounds.tolist(),display_faces=len(mesh.faces))
        rows.append(row)
    SOURCE.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(SOURCE/'chassis.npz',**archive)
    save(SOURCE/'chassis.json',dict(parts=rows,source_001_sha256=sha(ROOT/'models/full/robot.json'),
         archive_sha256=sha(SOURCE/'chassis.npz'),
         removed_parts=[p['name'] for p in meta['parts'] if removed(p['name'])]))


def parallel(m,p):return m*(np.eye(3)*np.dot(p,p)-np.outer(p,p))
def tensor(six):
    a,b,c,d,e,f=six
    return np.array([[a,d,e],[d,b,f],[e,f,c]])
def six(t):return [float(t[0,0]),float(t[1,1]),float(t[2,2]),float(t[0,1]),float(t[0,2]),float(t[1,2])]
def component_tensor(c,origin):
    m=c['mass_kg'];d=np.asarray(c['dimensions_proxy_m']);p=np.asarray(c['com_world_m'])-origin
    return np.diag(m/12*(np.sum(d*d)-d*d))+parallel(m,p)


def build():
    inputs=json.loads((SOURCE/'chassis.json').read_text())
    assert inputs['source_001_sha256']==sha(ROOT/'models/full/robot.json')
    assert inputs['archive_sha256']==sha(SOURCE/'chassis.npz')
    if MODELS.exists():shutil.rmtree(MODELS)
    shutil.copytree(ROOT/'models',MODELS)
    full=MODELS/'full'
    spec=json.loads((full/'robot.json').read_text())
    original=copy.deepcopy(spec)
    for name in REMOVED_BODIES:
        del spec['bodies'][name]
        (full/'assets'/f'{name}.glb').unlink()
        for path in (full/'visuals').glob(f'{name}_*.obj'):path.unlink()
    chassis=spec['bodies']['chassis'];origin=np.array(chassis['origin_m'])
    old_components=chassis['mass_components']
    removed_components=[c for c in old_components if removed(c['name']) or c['name'] in {'cargo_shell','cargo_mat'}]
    kept=[c for c in old_components if c not in removed_components]
    floor=json.loads((VARIANT/'cad/floor-change.json').read_text())
    old_shell=next(c for c in old_components if c['name']=='cargo_shell')
    new_shell=copy.deepcopy(old_shell)
    new_shell['mass_kg']*=floor['restored_volume_mm3']/floor['source_volume_mm3']
    new_shell['mass_basis']='Restored CAD volume; same assumed density as 001 shell'
    # Retained shell COM/AABB proxy with changed CAD volume, explicitly approximate.
    new_shell['com_basis']='001 shell COM retained as approximation after filling local holes'
    new_mat=dict(name='cargo_mat',mass_kg=.152*.220*.002*1100,
        com_world_m=[-.052,0,.258],dimensions_proxy_m=[.152,.220,.002],
        mass_basis='Nominal solid rubber, assumed density 1100 kg/m3; not weighed',
        com_basis='Geometric box centre',inertia_basis='Uniform box')
    new_components=[new_shell,new_mat]
    m=chassis['mass_kg'];c=np.array(chassis['com_local_m'])
    inertia=tensor(chassis['full_inertia_kgm2'])+parallel(m,c)
    moment=m*c
    for comp in removed_components:
        m-=comp['mass_kg'];moment-=comp['mass_kg']*(np.array(comp['com_world_m'])-origin)
        inertia-=component_tensor(comp,origin)
    for comp in new_components:
        m+=comp['mass_kg'];moment+=comp['mass_kg']*(np.array(comp['com_world_m'])-origin)
        inertia+=component_tensor(comp,origin)
    c=moment/m;inertia-=parallel(m,c)
    assert np.linalg.eigvalsh(inertia).min()>0
    chassis.update(mass_kg=m,com_local_m=c.tolist(),full_inertia_kgm2=six(inertia),
        diagonal_inertia_kgm2=np.diag(inertia).tolist(),mass_components=kept+new_components)
    # One continuous plane, exactly at the previous mat's top height.
    mat_contact=next(x for x in chassis['collision'] if x.get('source_part')=='cargo_mat')
    mat_contact.update(pos=[-.052,0,.038],size=[.076,.110,.001])
    chassis['collision'].append(dict(type='box',pos=[-.052,0,.035],size=[.076,.110,.002],source_part='cargo_floor_restoration'))
    archive=np.load(SOURCE/'chassis.npz',allow_pickle=False)
    grouped=defaultdict(list)
    for i,row in enumerate(inputs['parts']):
        mesh=trimesh.Trimesh(vertices=archive[f'v{i}']-origin,faces=archive[f'f{i}'],process=False)
        grouped[tuple(row['rgba'])].append(mesh)
    for path in (full/'visuals').glob('chassis_*.obj'):path.unlink()
    chassis['visuals']=[];scene=trimesh.Scene()
    transform=np.eye(4);transform[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]
    for i,(rgba,chunks) in enumerate(grouped.items()):
        mesh=trimesh.util.concatenate(chunks);file=f'visuals/chassis_{i}.obj';mesh.export(full/file)
        chassis['visuals'].append(dict(obj=file,rgba=list(rgba)))
        mesh.apply_transform(transform);mesh.vertex_normals
        mesh.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=rgba,metallicFactor=0.,roughnessFactor=.65))
        scene.add_geometry(mesh,node_name=f'chassis_{i}',geom_name=f'chassis_mesh_{i}')
    (full/'assets/chassis.glb').write_bytes(scene.export(file_type='glb',include_normals=True))
    spec.update(robot_id='Sai_Agent_002',status='Flat cargo bay derived from 001; provisional hardware parameters',
        cargo=dict(retention='passive_floor_and_walls',active_clamp=False,
                   bounds_world_m=[[-.128,-.110,.254],[.024,.110,.315]],
                   floor_top_m=.259,mat_size_m=[.152,.220,.002]),
        total_robot_mass_kg=sum(b['mass_kg'] for b in spec['bodies'].values()))
    spec['source_001_CAD_STEP_sha256']=spec.pop('CAD_STEP_sha256')
    spec['source_001_CAD_manifest_sha256']=spec.pop('CAD_manifest_sha256')
    spec['CAD_STEP_sha256']=sha(VARIANT/'cad/cargo_shell.step')
    spec['CAD_scope']='Hash identifies changed project shell only; not a complete new robot STEP'
    original_parts=json.loads((ROOT/'models/asset_provenance.json').read_text())['parts']
    spec['source_visual_parts']=len(inputs['parts'])+sum(p['body'] not in REMOVED_BODIES and p['body']!='chassis' for p in original_parts)
    spec['limitations']=[s for s in spec['limitations'] if not any(x in s for x in ['belt','rotor','0.12 Nm','moving masses'])]
    spec['limitations']+=['Passive cargo retention only; object may slide or fall on rough terrain',
        '001 unmodelled 600 g allowance retained: removed unassigned electronics cannot be subtracted accurately',
        'Chassis inertia updated by component box estimates; filled shell COM uses original proxy']
    tree=ET.parse(full/'robot.xml');root=tree.getroot();root.set('model','Sai_Agent_002_full')
    for parent in root.iter():
        for child in list(parent):
            if child.tag=='body' and child.get('name') in REMOVED_BODIES:parent.remove(child)
    for tag in ['equality','keyframe']:
        if root.find(tag) is not None:root.remove(root.find(tag))
    for act in list(root.find('actuator')):
        if act.get('joint','').startswith('cargo_'):root.find('actuator').remove(act)
    cb=root.find(".//body[@name='chassis']")
    cb.find('inertial').attrib.clear()
    cb.find('inertial').attrib.update(mass=str(m),pos=' '.join(map(str,c)),fullinertia=' '.join(map(str,six(inertia))))
    cb.find("geom[@name='chassis_contact_1']").set('pos','-.052 0 .038')
    cb.find("geom[@name='chassis_contact_1']").set('size','.076 .110 .001')
    ET.SubElement(cb,'geom',name='cargo_floor_restoration',type='box',pos='-.052 0 .035',size='.076 .110 .002')
    ET.indent(tree);tree.write(full/'robot.xml',encoding='unicode')
    visual=copy.deepcopy(root);asset=visual.find('asset')
    for name,b in spec['bodies'].items():
        body=visual.find(f".//body[@name='{name}']")
        for geom in body.findall('geom'):geom.set('rgba','0 0 0 0')
        for i,v in enumerate(b['visuals']):
            mesh_name=f'public_visual_{name}_{i}'
            ET.SubElement(asset,'mesh',name=mesh_name,file=v['obj'])
            ET.SubElement(body,'geom',type='mesh',mesh=mesh_name,contype='0',conaffinity='0',density='0',group='1',rgba=' '.join(map(str,v['rgba'])))
    ET.ElementTree(visual).write(full/'visual.xml',encoding='unicode')
    save(full/'robot.json',spec)
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp)
        shutil.copy(full/'robot.xml',temp/'train.xml');shutil.copy(full/'robot.json',temp/'robot.json')
        shutil.copytree(full/'contacts',temp/'contacts')
        prepare(temp,MODELS)
    reduced=ET.parse(MODELS/'locomotion.xml');reduced.getroot().set('model','Sai_Agent_002_locomotion');reduced.write(MODELS/'locomotion.xml',encoding='unicode')
    manifest=json.loads((MODELS/'robot_manifest.json').read_text())
    manifest.update(robot_id='Sai_Agent_002',model_sha256=sha(MODELS/'locomotion.xml'),CAD_scope=spec['CAD_scope'])
    manifest['limitations']=spec['limitations']+['Arm fixed at home only in reduced training model; full model remains articulated']
    save(MODELS/'robot_manifest.json',manifest)
    (full/'locomotion-articulated.xml').unlink(missing_ok=True)
    source_provenance=json.loads((ROOT/'models/asset_provenance.json').read_text())
    source_provenance['parts']=[p for p in source_provenance['parts'] if p['body']!='chassis' and p['body'] not in REMOVED_BODIES]+inputs['parts']
    source_provenance.pop('physical_invariance_checks',None)
    source_provenance.update(robot_id='Sai_Agent_002',source_001_robot_sha256=sha(ROOT/'models/full/robot.json'),
        removed_parts=inputs['removed_parts'],changed_parts=['cargo_shell','cargo_mat'],
        inherited_unchanged_bodies=[n for n in spec['bodies'] if n!='chassis'])
    save(MODELS/'asset_provenance.json',source_provenance)
    (MODELS/'visual_lod_summary.json').unlink(missing_ok=True)
    model=mujoco.MjModel.from_xml_path(str(full/'robot.xml'))
    assert model.nu==22 and model.neq==0
    assert np.isclose(model.body_mass.sum()-.1,spec['total_robot_mass_kg'])
    save(VARIANT/'changes.json',dict(robot_id=spec['robot_id'],removed_bodies=sorted(REMOVED_BODIES),
         removed_parts=inputs['removed_parts'],mass_before_kg=original['total_robot_mass_kg'],
         estimated_mass_after_kg=spec['total_robot_mass_kg'],mass_delta_kg=spec['total_robot_mass_kg']-original['total_robot_mass_kg'],
         joint_count=22,active_clamp=False,object_constraints=0,mat_bounds_m=[[-.128,-.110,.257],[.024,.110,.259]],
         robot_xml_sha256=sha(full/'robot.xml'),robot_json_sha256=sha(full/'robot.json')))
    print('BUILT Sai_Agent_002',spec['total_robot_mass_kg'],'kg, 22 actuators, zero clamp constraints')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--engineering-source',type=Path)
    args=p.parse_args()
    if args.engineering_source:bootstrap(args.engineering_source.resolve())
    build()
