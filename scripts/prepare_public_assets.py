"""Build a redistributable r24 model without copying unlicensed vendor display CAD.

Known vendor dimensional envelopes are independently constructed primitives.
The approved original shell/SO101 geometry and all physical state remain intact.
"""
import argparse
from collections import defaultdict, Counter
import copy
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import mujoco

ROOT=Path(__file__).resolve().parents[1]
F=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
SO_URL='https://github.com/TheRobotStudio/SO-ARM100/tree/eecbe3e0a9ebb23e25ad7b2759b03884c6660903'
PI_URL='https://pip.raspberrypi.com/categories/892-raspberry-pi-5'


def classification(part):
    name,source=part['name'],part.get('source','')
    if not source:
        assert part.get('body','').startswith('arm_'),name
        return 'upstream_licensed','Apache-2.0',SO_URL
    if source.startswith('vendor/pi5_r14/'):
        return 'upstream_licensed','MIT',PI_URL
    vendor=(source.startswith('CubeMars ') or 'original gobilda' in source.lower()
        or (source.startswith('goBILDA ') and 'original STEP' in source)
        or name.startswith(('cargo_servoblock_','cargo_position_servo_','cargo_force_cell_'))
        or name in ['force_board_complete_pcb','can_hat_mounted_reference',
                    'bus_servo_adapter_reference','maestro6_mounted_reference',
                    'logic_5v_family_reference','arm_12v_family_reference','cargo_6v_family_reference'])
    return ('project_envelope','Apache-2.0',None) if vendor else ('project_original','Apache-2.0',None)


def envelope(part):
    name=part['name']; bounds=np.array(part['bounds_m']); center=bounds.mean(0)
    if part.get('source','').startswith('CubeMars '):
        axis=np.array([1,0,0]) if name.endswith('_haa') else np.array([0,1,0])
        radius,length=(.0265,.0402) if name.endswith('_wheel_motor') else (.0275,.0565)
        mesh=trimesh.creation.cylinder(radius=radius,height=length,sections=48)
        mesh.apply_transform(trimesh.geometry.align_vectors([0,0,1],axis))
    elif name.endswith('_wheel'):
        mesh=trimesh.creation.cylinder(radius=.048,height=.032,sections=64)
        mesh.apply_transform(trimesh.geometry.align_vectors([0,0,1],[0,1,0]))
    else:
        # Independent nominal box, never a hull/remesh of the vendor object.
        mesh=trimesh.creation.box(extents=np.maximum(np.round(bounds[1]-bounds[0],6),.0001))
    mesh.apply_translation(center)
    return mesh


def sanitize(value,source):
    if isinstance(value,dict):return {k:sanitize(v,source) for k,v in value.items()}
    if isinstance(value,list):return [sanitize(v,source) for v in value]
    if isinstance(value,str):return value.replace(str(source),'engineering_source')
    return value


def main(source):
    source=source.resolve()
    out=ROOT/'models/full'
    for folder in ['contacts','visuals','assets']:(out/folder).mkdir(parents=True,exist_ok=True)
    meta=json.loads((source/'derived/maestro_mount_r19/manifest.json').read_text())
    spec=json.loads((source/'integrations/godot_r24/robot.json').read_text())
    original=copy.deepcopy(spec)
    groups={n:f'cargo_slide_{s}' for n,s in meta['cargo_moving_parts'].items()}
    groups.update({n:'cargo_rotor' for n in meta['cargo_rotating_parts']})
    meshes=defaultdict(lambda:defaultdict(list));provenance=[]
    lod=[]
    for part in meta['parts']:
        name=part['name'];body=groups.get(name,part.get('body','chassis'))
        if body=='arm_base':body='chassis'
        kind,license_id,url=classification(part)
        row=dict(name=name,body=body,origin_kind=kind,license_id=license_id,source_url=url,
                 source_note=part.get('source','SO101 source assembly split'),
                 bounds_world_m=part['bounds_m'])
        if name=='cargo_position_servo_2':
            row.update(redistribution_status='vendor label omitted');provenance.append(row);continue
        if kind=='project_envelope':
            mesh=envelope(part)
            row['redistribution_status']='original vendor display omitted; independent envelope distributed'
        else:
            path=source/'derived/maestro_mount_r19'/part['file']
            mesh=trimesh.load_mesh(path,process=False)
            if 'transform_m' in part:mesh.apply_transform(np.array(part['transform_m']))
            row.update(source_mesh_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       redistribution_status='permitted source derivative')
        before_faces=len(mesh.faces)
        before_bounds=mesh.bounds.copy()
        extent=float(mesh.extents.max())
        limit=6000 if extent>.12 else 3000 if extent>.06 else 1000 if extent>.025 else 256
        # Welding identical STL vertices is lossless to nanometre-scale precision;
        # simplification only affects displays, never contacts or inertia.
        mesh.merge_vertices(digits_vertex=10)
        if len(mesh.faces)>limit:
            candidate=mesh.simplify_quadric_decimation(face_count=limit)
            bound_error=float(np.max(np.abs(candidate.bounds-before_bounds)))
            if bound_error<.0005:mesh=candidate
        row['display_faces']=len(mesh.faces)
        lod.append(dict(name=name,before_faces=before_faces,after_faces=len(mesh.faces),
                        maximum_bounds_change_m=float(np.max(np.abs(mesh.bounds-before_bounds)))))
        mesh.vertices-=np.array(spec['bodies'][body]['origin_m'])
        meshes[body][tuple(part['color'])].append(mesh)
        provenance.append(row)
    # Save source-coordinate visual OBJ for MuJoCo and Y-up GLB for Godot.
    for name,b in spec['bodies'].items():
        b['visuals']=[];scene=trimesh.Scene()
        for i,(color,chunks) in enumerate(meshes[name].items()):
            mesh=trimesh.util.concatenate(chunks)
            file=f'visuals/{name}_{i}.obj';mesh.export(out/file)
            b['visuals'].append(dict(obj=file,rgba=list(color)))
            shown=mesh.copy();shown.vertices=shown.vertices@F.T
            shown.visual=trimesh.visual.ColorVisuals(shown,vertex_colors=np.tile(
                np.array(color)*255,(len(shown.vertices),1)).astype(np.uint8))
            scene.add_geometry(shown,node_name=f'{name}_{i}')
        (out/'assets'/f'{name}.glb').write_bytes(scene.export(file_type='glb'))
        b['godot_glb']=f'res://sai_agent/assets/{name}.glb'
    tree=ET.parse(source/'simulation/r24/train.xml');root=tree.getroot()
    for node in root.findall('.//mesh'):
        path=Path(node.get('file'))
        assert path.parent.name in ['cargo_shell','gripper_8','lower_3','moving_jaw_9',
                                        'pan_carrier_1','upper_2','wrist_7'],path
        file=f'contacts/{path.parent.name}_{path.name}'
        shutil.copyfile(path,out/file);node.set('file',file)
    for b in spec['bodies'].values():
        for contact in b['collision']:
            if contact['type']=='mesh':
                path=Path(contact['mesh_file'])
                contact['mesh_file']=f'contacts/{path.parent.name}_{path.name}'
    root.set('model','Sai_Agent_001_full_r24')
    tree.write(out/'robot.xml',encoding='unicode')
    original_model=mujoco.MjModel.from_xml_path(str(source/'simulation/r24/train.xml'))
    public_model=mujoco.MjModel.from_xml_path(str(out/'robot.xml'))
    checks={}
    for field in ['nq','nv','nu','nbody','neq','ngeom']:
        checks[field]=getattr(original_model,field)==getattr(public_model,field)
    for field in ['body_mass','body_inertia','body_pos','body_quat','body_ipos','body_iquat','jnt_axis',
                  'jnt_pos','jnt_range','geom_pos','geom_quat','geom_size','actuator_gear']:
        checks[field]=bool(np.array_equal(getattr(original_model,field),getattr(public_model,field)))
    assert all(checks.values()),checks
    for name,b in spec['bodies'].items():
        for field in ['parent','origin_m','mass_kg','com_local_m','joint','full_inertia_kgm2']:
            assert b.get(field)==original['bodies'][name].get(field),(name,field)
    spec['status']='Public r24 articulated model; dynamics unchanged, some vendor displays replaced by independent envelopes'
    spec['robot_id']='Sai_Agent_001'
    (out/'robot.json').write_text(json.dumps(sanitize(spec,source),indent=2)+'\n')
    visual_root=copy.deepcopy(root)
    asset=visual_root.find('asset')
    for name,b in spec['bodies'].items():
        body=visual_root.find(f".//body[@name='{name}']")
        assert body is not None,name
        for geom in body.findall('geom'):geom.set('rgba','0 0 0 0')
        for i,v in enumerate(b['visuals']):
            mesh_name=f'public_visual_{name}_{i}'
            ET.SubElement(asset,'mesh',name=mesh_name,file=v['obj'])
            ET.SubElement(body,'geom',type='mesh',mesh=mesh_name,contype='0',conaffinity='0',
                          density='0',group='1',rgba=' '.join(map(str,v['rgba'])))
    ET.ElementTree(visual_root).write(out/'visual.xml',encoding='unicode')
    (ROOT/'models/asset_provenance.json').write_text(json.dumps(sanitize(dict(
        source_CAD_sha256=spec['CAD_STEP_sha256'],parts=provenance,
        physical_invariance_checks=checks),source),indent=2)+'\n')
    (ROOT/'models/visual_lod_summary.json').write_text(json.dumps(dict(
        method='per-part quadric display simplification; no contact/mass changes',
        original_faces=sum(r['before_faces'] for r in lod),
        display_faces=sum(r['after_faces'] for r in lod),parts=lod),indent=2)+'\n')
    (ROOT/'licenses').mkdir(exist_ok=True)
    shutil.copyfile(source/'vendor/so101/LICENSE',ROOT/'licenses/SO101-Apache-2.0.txt')
    shutil.copyfile(source/'vendor/so101/LICENSE',ROOT/'LICENSE')
    shutil.copyfile(source/'vendor/pi5_r14/LICENSE.txt',ROOT/'licenses/RaspberryPi5-MIT.txt')
    print(json.dumps(dict(parts=len(provenance),bodies=len(spec['bodies']),
                         origins=dict(Counter(r['origin_kind'] for r in provenance)),
                         physical_invariance_checks=checks),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path)
    main(p.parse_args().source)
