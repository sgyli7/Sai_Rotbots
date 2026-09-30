"""Blender entry point: render and save the actual quad rebuild, no image edits."""
import argparse
import ast
import array
import hashlib
import json
import math
import sys
import struct
import zipfile
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--scene',type=Path,required=True)
parser.add_argument('--resolution',type=int,default=1000)
parser.add_argument('--samples',type=int,default=32)
parser.add_argument('--views',default='three_quarter,side,front')
parser.add_argument('--output',type=Path)
parser.add_argument('--geometry-root',type=Path)
parser.add_argument('--candidate-stamp',action='store_true')
parser.add_argument('--blend-output',type=Path)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
directory=args.output.resolve() if args.output else args.scene.resolve().parent
directory.mkdir(parents=True,exist_ok=True)
blend_output=args.blend_output.resolve() if args.blend_output else directory/'goose_fuller_quad.blend'
blend_output.parent.mkdir(parents=True,exist_ok=True)
payload=json.loads(args.scene.read_text())
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
materials={}
specs={
 'ivory':((.68,.68,.645,1),.30,0),
 'orange':((.95,.19,.0015,1),.34,0),
 'graphite':((.021,.028,.033,1),.29,.25),
 'rubber':((.014,.018,.020,1),.72,0),
 'seam':((.065,.068,.068,1),.5,0),
 'titanium':((.32,.35,.36,1),.3,.72),
 'glass':((.008,.018,.025,1),.1,.5),
 'lens':((.003,.009,.016,1),.08,.4),
}
for name,(color,roughness,metallic) in specs.items():
 mat=bpy.data.materials.new(name); mat.use_nodes=True
 bsdf=mat.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value=color
 bsdf.inputs['Roughness'].default_value=roughness; bsdf.inputs['Metallic'].default_value=metallic
 materials[name]=mat
collection=bpy.data.collections.new('Goose fuller body - editable quad exterior'); bpy.context.scene.collection.children.link(collection)
groups={}
def read_npy_2d(raw):
 # Blender's bundled Python has no NumPy here. Read just the two numeric,
 # C-order arrays we generate, with no pickle or executable deserialization.
 if raw[:6]!=b'\x93NUMPY': raise ValueError('Invalid NPY magic')
 version=raw[6];size=2 if version==1 else 4 if version in (2,3) else 0
 if not size: raise ValueError('Unsupported NPY version')
 length=int.from_bytes(raw[8:8+size],'little');start=8+size
 header=ast.literal_eval(raw[start:start+length].decode('latin1'))
 shape=header['shape'];kind=header['descr']
 if header['fortran_order'] or len(shape)!=2 or kind not in ('<f8','<i8','>f8','>i8'): raise ValueError('Unsupported NPY geometry encoding')
 values=array.array('d' if kind.endswith('f8') else 'q');values.frombytes(raw[start+length:])
 if (kind[0]=='<' and sys.byteorder!='little') or (kind[0]=='>' and sys.byteorder!='big'): values.byteswap()
 if len(values)!=shape[0]*shape[1]: raise ValueError('NPY geometry size mismatch')
 iterator=iter(values);return list(zip(*([iterator]*shape[1])))
for part in payload['parts']:
 if part['group'] not in groups:
  group=bpy.data.collections.new(part['group']); collection.children.link(group); groups[part['group']]=group
 if 'geometry_npz' in part:
  if args.geometry_root is None: raise ValueError('NPZ geometry requires --geometry-root')
  root=args.geometry_root.resolve(); file=(root/part['geometry_npz']).resolve()
  if not file.is_relative_to(root) or hashlib.sha256(file.read_bytes()).hexdigest()!=part['source_sha256']: raise ValueError('Geometry identity/hash mismatch')
  with zipfile.ZipFile(file) as data: points=read_npy_2d(data.read('vertices.npy')); faces=read_npy_2d(data.read('faces.npy'))
 else: points=part['vertices']; faces=part['faces']
 if not faces or any(len(f)!=4 for f in faces): raise ValueError('Editable rendering source must contain quads')
 center=Vector(tuple((min(v[i] for v in points)+max(v[i] for v in points))/2 for i in range(3)))
 vertices=[tuple(v[i]-center[i] for i in range(3)) for v in points]
 mesh=bpy.data.meshes.new(part['name']); mesh.from_pydata(vertices,[],faces); mesh.update()
 obj=bpy.data.objects.new(part['name'],mesh); groups[part['group']].objects.link(obj)
 offset=payload.get('assembly_translation_m',[0,0,0])
 if len(offset)!=3 or not all(math.isfinite(float(x)) for x in offset): raise ValueError('Invalid assembly translation')
 obj.location=center+Vector(offset); obj['assembly_translation_m']=offset
 obj.data.materials.append(materials[part['material']]); obj['assembly_group']=part['group']
 obj['source_sha256']=part.get('source_sha256',hashlib.sha256(json.dumps(part,sort_keys=True).encode()).hexdigest()); obj['manufacturing_status']=payload.get('status','unapproved exterior geometry'); obj['part_role']=part.get('role','custom_visual_candidate')
 for face in mesh.polygons: face.use_smooth=True
 mesh.use_auto_smooth=True; mesh.auto_smooth_angle=math.radians(80)
 # Shading normals only; the editable source remains untriangulated quad faces.
 if part.get('role') not in ('hollow_shell_candidate','removable_cover_candidate','shell_outer_surface_candidate','native_nurbs_skin_attachment_pending'):
  modifier=obj.modifiers.new('Area weighted shading normals','WEIGHTED_NORMAL'); modifier.keep_sharp=True; modifier.weight=30

floor_mat=bpy.data.materials.new('Studio warm grey'); floor_mat.diffuse_color=(.62,.62,.60,1); floor_mat.use_nodes=True
floor_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.78
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0002)); floor=bpy.context.object; floor.name='STUDIO_floor'; floor.data.materials.append(floor_mat)
def point_at(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def area(name,location,power,size,target):
 data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size
 obj=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(obj); obj.location=location; point_at(obj,target)
area('STUDIO_key',(.45,-.85,1.45),60,1.0,(0,0,.3))
area('STUDIO_fill',(-.9,-.25,.85),25,.85,(0,0,.35))
area('STUDIO_rim',(.2,.8,1.2),80,.9,(0,0,.4))
world=bpy.data.worlds.new('Studio world'); world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.65,.66,.67,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.3
scene=bpy.context.scene; scene.world=world; scene.render.engine='CYCLES'
scene.cycles.samples=args.samples; scene.cycles.use_denoising=False
scene.render.resolution_x=args.resolution; scene.render.resolution_y=args.resolution; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
if args.candidate_stamp:
 scene.render.use_stamp=True;scene.render.use_stamp_note=True;scene.render.stamp_note_text='CANDIDATE - NOT MANUFACTURING RELEASE'
 scene.render.use_stamp_date=False;scene.render.use_stamp_time=False;scene.render.use_stamp_frame=False;scene.render.use_stamp_filename=False;scene.render.use_stamp_scene=False;scene.render.use_stamp_camera=False;scene.render.use_stamp_render_time=False;scene.render.stamp_font_size=14
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.65
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
camera_data=bpy.data.cameras.new('Review camera'); camera=bpy.data.objects.new('Review camera',camera_data); scene.collection.objects.link(camera); scene.camera=camera
camera_data.type='ORTHO'; camera_data.ortho_scale=.78; camera_data.lens=70
views={'three_quarter':((1.15,-1.75,.99),(.05,0,.325)),
       'side':((.045,-2,.40),(.045,0,.325)),
       'front':((2,0,.40),(.045,0,.325)),
       'rear':((-2,0,.40),(.045,0,.325)),
       'head_detail':((.65,-.82,.73),(.18,0,.576)),
       'mechanism':((1.15,-1.75,.99),(.05,0,.325)),
       'foot_detail':((.52,-.70,.48),(.01,-.015,.055)),
       'top':((.02,0,2),(.02,0,.32)),
       'door_detail':((.65,-1.7,.65),(-.02,0,.29))}
scene['status']=payload.get('status','EXTERIOR CANDIDATE - NOT MANUFACTURING OR PHYSICS RELEASE')
for name in filter(None,args.views.split(',')):
 position,target=views[name]; camera.location=position; point_at(camera,target)
 for obj in collection.all_objects:
  obj.hide_render = name=='mechanism' and (obj.name.startswith(('torso_shell_','wing_access_cover_','goose_head_shell')) or '_foot_upper' in obj.name or obj.name.endswith('_ankle_service_hood'))
 camera_data.ortho_scale=.34 if name=='foot_detail' else .31 if name=='head_detail' else .46 if name=='door_detail' else .78
 scene.render.filepath=str(directory/(name+'.png'))
 bpy.ops.wm.save_as_mainfile(filepath=str(blend_output),compress=True)
 bpy.ops.render.render(write_still=True)
for obj in collection.all_objects: obj.hide_render=False
position,target=views['three_quarter']; camera.location=position; point_at(camera,target); camera_data.ortho_scale=.78
bpy.ops.wm.save_as_mainfile(filepath=str(blend_output),compress=True)
# The deliverable is the editable .blend and quad OBJ. Preview GLB is not required.
print('REBUILD_RENDER_COMPLETE',flush=True)
