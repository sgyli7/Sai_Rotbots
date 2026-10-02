#!/usr/bin/env python3
"""Render actual layout-B source geometry; CPU Blender, no image generation.

Run with the repository Python. --screen and --model obtain per-body transforms
from the specified MuJoCo model, then render the same appearance geometry in FK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
ROBOT=ROOT/'robots/gorilla_v0_1'
BLENDER_ROOT=Path('/home/ethan/Softwares/blender-local/root')


def arguments():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene',type=Path,default=ROBOT/'cad/source/layout_b_scene.json')
    p.add_argument('--screen',type=Path)
    p.add_argument('--model',type=Path,default=ROBOT/'models/full/robot.xml')
    p.add_argument('--resolution',type=int,default=900)
    p.add_argument('--samples',type=int,default=24)
    p.add_argument('--transforms',type=Path)
    if '--' in sys.argv: return p.parse_args(sys.argv[sys.argv.index('--')+1:])
    return p.parse_args()


def checksum(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def wrapper(args):
    env=os.environ.copy()
    env['LD_LIBRARY_PATH']=':'.join(str(BLENDER_ROOT/p) for p in (
        'usr/lib','usr/lib/aarch64-linux-gnu','usr/lib/aarch64-linux-gnu/lapack',
        'usr/lib/aarch64-linux-gnu/blas'))
    env['BLENDER_SYSTEM_SCRIPTS']=str(BLENDER_ROOT/'usr/share/blender/scripts')
    env['BLENDER_SYSTEM_DATAFILES']=str(BLENDER_ROOT/'usr/share/blender/datafiles')
    # Blender links the host Python 3.12.3; uv's standalone prefix misses its
    # host extension ABI paths (notably _ctypes needed by the GLB exporter).
    env['PYTHONHOME']='/usr'
    env['PYTHONNOUSERSITE']='1'
    env['PYTHONPATH']=str(ROOT/'.venv/lib/python3.12/site-packages')
    export=ROBOT/'cad/exports/layout_b'; export.mkdir(parents=True,exist_ok=True)
    cmd=[str(BLENDER_ROOT/'usr/bin/blender'),'-b','--threads','12','--python-exit-code','1','--python',str(Path(__file__).resolve()),'--',
         '--scene',str(args.scene),'--resolution',str(args.resolution),'--samples',str(args.samples)]
    if args.screen:
        import mujoco
        import numpy as np
        scene=json.loads(args.scene.read_text())
        screen=json.loads(args.screen.read_text())
        model=mujoco.MjModel.from_xml_path(str(args.model))
        data=mujoco.MjData(model)
        data.qpos[:]=model.qpos0
        mujoco.mj_forward(model,data)
        bodies={part['body'] for part in scene['parts']}
        neutral={body: {'position':data.xpos[model.body(body).id].tolist(),
                        'rotation':data.xmat[model.body(body).id].reshape(3,3).tolist()} for body in bodies}
        poses=[]
        for pose in screen['poses']:
            q=np.asarray(pose['qpos'])
            if len(q)!=model.nq: raise ValueError('Screen qpos does not match the provided model')
            data.qpos[:]=q; mujoco.mj_forward(model,data)
            poses.append({'name':pose['name'],'bodies':{body: {'position':data.xpos[model.body(body).id].tolist(),
                          'rotation':data.xmat[model.body(body).id].reshape(3,3).tolist()} for body in bodies}})
        transform_file=export/'pose_transforms.json'
        transform_file.write_text(json.dumps({'model_sha256':checksum(args.model),'screen_sha256':checksum(args.screen),
            'scene_sha256':checksum(args.scene),'neutral':neutral,'poses':poses},indent=2)+'\n')
        cmd.extend(['--transforms',str(transform_file)])
    subprocess.run(cmd,env=env,check=True)
    from PIL import Image,ImageDraw,ImageFont
    n=args.resolution
    sheet=Image.new('RGB',(n*2,n*2+110),'white')
    draw=ImageDraw.Draw(sheet)
    try: font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    except OSError: font=ImageFont.load_default()
    labels=[('front',0,0),('left',1,0),('rear',0,1),('top',1,1)]
    paths=[]
    for name,c,r in labels:
        path=ROBOT/'images'/f'layout_b_{name}.png'
        sheet.paste(Image.open(path).convert('RGB'),(c*n,55+r*n))
        draw.text((c*n+20,55+r*n+12),name.upper(),fill='#23394f',font=font)
        paths.append(path)
    draw.text((20,15),'Gorilla V0.1 / layout B / actual source render / appearance candidate',fill='#23394f',font=font)
    draw.text((20,n*2+68),'AA3 proportion reconstruction; not manufacturing or physical acceptance.',fill='#23394f',font=font)
    out=ROBOT/'images/layout_b_four_view.png';sheet.save(out)
    paths.extend([out,ROBOT/'images/layout_b_threequarter.png'])
    paths.extend(sorted((ROBOT/'images').glob('layout_b_pose_*.png')))
    manifest={'schema':'gorilla_actual_render_v1','robot_id':'gorilla_v0_1',
        'checkpoint_id':'gorilla_layout_b','scene_sha256':checksum(args.scene),
        'scene_path':str(args.scene.relative_to(ROOT)),
        'spec_sha256':json.loads(args.scene.read_text())['spec_sha256'],
        'spec_path':json.loads(args.scene.read_text())['spec_path'],
        'image_authority_sha256':json.loads(args.scene.read_text())['image_sha256'],
        'renderer_script_path':str(Path(__file__).resolve().relative_to(ROOT)),
        'renderer_script_sha256':checksum(Path(__file__).resolve()),
        'builder_script_path':'scripts/models/build_gorilla_proportion_layout.py',
        'builder_script_sha256':checksum(ROOT/'scripts/models/build_gorilla_proportion_layout.py'),
        'renderer':'Blender 4.0.2 Cycles CPU','resolution':n,'samples':args.samples,
        'geometry_scope':'Exact editable appearance source; orthographic neutral views and named-body FK poses.',
        'render_scope':'No AI image editing or image stretching; lighting/color management do not modify geometry.',
        'images':[{ 'path':str(p.relative_to(ROOT)),'sha256':checksum(p)} for p in paths],
        'appearance_accepted':False,'physics_accepted':False}
    if args.screen:
        manifest['pose_binding']={'model_path':str(args.model),'model_sha256':checksum(args.model),
            'screen_path':str(args.screen),'screen_sha256':checksum(args.screen),
            'transforms_path':str(transform_file.relative_to(ROOT)),
            'transforms_sha256':checksum(transform_file),
            'scope':'MuJoCo forward kinematics only; no object/contact/task acceptance'}
        model_contract=args.model.with_suffix('.json')
        if model_contract.exists():
            manifest['pose_binding']['model_contract_path']=str(model_contract)
            manifest['pose_binding']['model_contract_sha256']=checksum(model_contract)
    (export/'render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if args.screen:
        evidence=ROBOT/'evidence/layout_b_render.json'
        evidence.parent.mkdir(parents=True,exist_ok=True)
        evidence.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'four_view':str(out),'render_manifest':str(export/'render_manifest.json')}))


def blender_render(args):
    import bpy
    from mathutils import Matrix,Vector
    scene_source=json.loads(args.scene.read_text())
    spec_path=ROOT/scene_source['spec_path']
    authority_path=ROOT/scene_source['appearance_authority_path']
    if checksum(spec_path)!=scene_source['spec_sha256'] or checksum(authority_path)!=scene_source['image_sha256']:
        raise ValueError('Source bindings changed; rebuild the appearance source first')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples
    scene.cycles.use_denoising=False  # This bundled ARM build lacks OpenImageDenoise.
    bpy.context.preferences.filepaths.save_version=0
    scene.render.resolution_x=scene.render.resolution_y=args.resolution
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    scene.view_settings.exposure=-1;scene.view_settings.gamma=1
    world=bpy.data.worlds.new('white_studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    scene.world=world
    meshes=[];neutral_vertices={}
    for part in scene_source['parts']:
        mesh=bpy.data.meshes.new(part['name']+'_mesh')
        mesh.from_pydata(part['vertices_world_m'],[],part['faces']);mesh.update()
        obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj)
        obj['body']=part['body'];obj['role']=part['role']
        obj['shell_thickness_m']=part['shell_thickness_m']
        obj['mass_basis_note']=part['mass_basis_note']
        mesh.use_auto_smooth=True;mesh.auto_smooth_angle=math.radians(42)
        for poly in mesh.polygons:
            poly.use_smooth=len(part['vertices_world_m'])>8 and len(poly.vertices)==4
        def linear(c): return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
        color=tuple(linear(c) for c in part['rgba'][:3])+(part['rgba'][3],)
        material=bpy.data.materials.new(part['name']+'_material');material.diffuse_color=color
        material.use_nodes=True
        bsdf=material.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=color
        bsdf.inputs['Metallic'].default_value=.24 if part['role']=='decoration' else .12
        bsdf.inputs['Roughness'].default_value=.34
        mesh.materials.append(material)
        meshes.append(obj);neutral_vertices[obj.name]=[Vector(v) for v in part['vertices_world_m']]
    # Same exact source mesh is saved and exported; lighting is not shape correction.
    for obj in meshes: obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    glb=ROBOT/'cad/exports/layout_b/layout_b.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008))
    ground=bpy.context.object;ground.name='studio_ground'
    mat=bpy.data.materials.new('studio_floor');mat.diffuse_color=(.94,.94,.94,1);ground.data.materials.append(mat)
    def light(name,pos,power,size):
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=pos
        ob.rotation_euler=(Vector((0,0,1.35))-ob.location).to_track_quat('-Z','Y').to_euler()
    light('front_key',(4,-3,6),600,5);light('left_fill',(1,4,4),400,4);light('rear_fill',(-4,1,4),500,4)
    cam_data=bpy.data.cameras.new('source_view_camera');camera=bpy.data.objects.new('source_view_camera',cam_data)
    bpy.context.collection.objects.link(camera);scene.camera=camera;cam_data.type='ORTHO';cam_data.lens=65
    camera.data.ortho_scale=3.05
    images=ROBOT/'images';images.mkdir(parents=True,exist_ok=True)
    def view(name,pos,target=(0,0,1.325),scale=3.05,top=False):
        camera.location=pos
        camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        if top: camera.rotation_euler=(0,0,math.pi/2)
        camera.data.ortho_scale=scale
        scene.render.filepath=str(images/f'layout_b_{name}.png')
        bpy.ops.render.render(write_still=True)
    # Save an editable neutral source with source binding metadata and studio views.
    scene['source_scene_sha256']=checksum(args.scene);scene['spec_sha256']=scene_source['spec_sha256']
    scene['image_authority_sha256']=scene_source['image_sha256'];scene['appearance_accepted']=False
    camera.location=(4,-6,3.7);camera.rotation_euler=(Vector((0,0,1.325))-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROBOT/'cad/source/layout_b.blend'))
    view('front',(8,0,1.325));view('left',(0,8,1.325));view('rear',(-8,0,1.325))
    view('top',(0,0,8),scale=2.4,top=True);view('threequarter',(4,-6,3.7),scale=3.15)
    if args.transforms:
        transforms=json.loads(args.transforms.read_text())
        if transforms['scene_sha256']!=checksum(args.scene): raise ValueError('Stale FK transforms')
        for pose in transforms['poses']:
            for ob in meshes:
                body=ob['body'];rest=transforms['neutral'][body];current=pose['bodies'][body]
                r0=Matrix(rest['rotation']);r1=Matrix(current['rotation'])
                p0=Vector(rest['position']);p1=Vector(current['position'])
                for vertex,neutral in zip(ob.data.vertices,neutral_vertices[ob.name]):
                    vertex.co=r1@r0.transposed()@(neutral-p0)+p1
                ob.data.update()
            view('pose_'+pose['name'],(4,-6,3.7),scale=3.35)
        for ob in meshes:
            for v,p in zip(ob.data.vertices,neutral_vertices[ob.name]): v.co=p
            ob.data.update()


if __name__=='__main__':
    args=arguments()
    try: import bpy
    except ImportError: wrapper(args)
    else: blender_render(args)
