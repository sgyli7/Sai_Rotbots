"""Blender entry point: render and save the actual quad rebuild, no image edits."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--scene',type=Path,required=True)
parser.add_argument('--resolution',type=int,default=1000)
parser.add_argument('--samples',type=int,default=32)
parser.add_argument('--views',default='three_quarter,side,front')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
directory=args.scene.resolve().parent
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
collection=bpy.data.collections.new('Goose R2 - editable quad exterior'); bpy.context.scene.collection.children.link(collection)
groups={}
for part in payload['parts']:
 if part['group'] not in groups:
  group=bpy.data.collections.new(part['group']); collection.children.link(group); groups[part['group']]=group
 center=Vector(tuple((min(v[i] for v in part['vertices'])+max(v[i] for v in part['vertices']))/2 for i in range(3)))
 vertices=[tuple(Vector(v)-center) for v in part['vertices']]
 mesh=bpy.data.meshes.new(part['name']); mesh.from_pydata(vertices,[],part['faces']); mesh.update()
 obj=bpy.data.objects.new(part['name'],mesh); groups[part['group']].objects.link(obj); obj.location=center
 obj.data.materials.append(materials[part['material']]); obj['assembly_group']=part['group']
 obj['source_sha256']=part['source_sha256']; obj['manufacturing_status']='unapproved exterior geometry'; obj['part_role']=part.get('role','custom_visual_candidate')
 for face in mesh.polygons: face.use_smooth=True
 mesh.use_auto_smooth=True; mesh.auto_smooth_angle=math.radians(80)
 # Shading normals only; the editable source remains untriangulated quad faces.
 if part.get('role') not in ('hollow_shell_candidate','removable_cover_candidate','shell_outer_surface_candidate'):
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
       'door_detail':((.65,-1.7,.65),(-.02,0,.29))}
scene['status']='EXTERIOR CANDIDATE - NOT MANUFACTURING OR PHYSICS RELEASE'
for name in filter(None,args.views.split(',')):
 position,target=views[name]; camera.location=position; point_at(camera,target)
 for obj in collection.all_objects:
  obj.hide_render = name=='mechanism' and (obj.name.startswith(('torso_shell_','wing_access_cover_','goose_head_shell')) or obj.name.endswith(('_foot_upper','_ankle_service_hood')))
 camera_data.ortho_scale=.31 if name=='head_detail' else .46 if name=='door_detail' else .78
 scene.render.filepath=str(directory/(name+'.png'))
 bpy.ops.wm.save_as_mainfile(filepath=str(directory/'goose_integrated_quad.blend'))
 bpy.ops.render.render(write_still=True)
for obj in collection.all_objects: obj.hide_render=False
position,target=views['three_quarter']; camera.location=position; point_at(camera,target); camera_data.ortho_scale=.78
bpy.ops.wm.save_as_mainfile(filepath=str(directory/'goose_integrated_quad.blend'))
# The deliverable is the editable .blend and quad OBJ. Preview GLB is not required.
print('REBUILD_RENDER_COMPLETE',flush=True)
