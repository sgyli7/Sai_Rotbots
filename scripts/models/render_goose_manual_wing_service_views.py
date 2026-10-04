"""Blender inspection of actual integral service CAD; no geometry modifiers."""
from pathlib import Path
import argparse,array,ast,hashlib,json,math,sys,zipfile
import bpy
from mathutils import Vector,Matrix

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def npy(raw):
 size=2 if raw[6]==1 else 4;n=int.from_bytes(raw[8:8+size],'little');start=8+size;h=ast.literal_eval(raw[start:start+n].decode('latin1'));kind=h['descr'];v=array.array('d' if kind.endswith('f8') else 'q');v.frombytes(raw[start+n:])
 if (kind[0]=='<' and sys.byteorder!='little') or (kind[0]=='>' and sys.byteorder!='big'):v.byteswap()
 if h['fortran_order'] or len(h['shape'])!=2 or kind not in ['<f8','<i8','>f8','>i8']:raise ValueError('Unexpected source array')
 if len(v)!=math.prod(h['shape']):raise ValueError('Source array size')
 it=iter(v);return list(zip(*([it]*h['shape'][1])))
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);args=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.root.resolve();r=root/'robots/Goose_V0.1';mp=r/'cad/exports/manual_wing_service/manifest.json';cp=r/'configs/manual_wing_service.json';kit=json.loads(mp.read_text());cfg=json.loads(cp.read_text());inputs=[mp,cp,Path(__file__)];out=r/'images/manual_wing_service_views';out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);objects={};mat={}
for key,color,metal in [('fixed',(0.72,.76,.78,1),0),('moving',(.9,.32,.06,1),0),('hardware',(.13,.16,.18,1),.5)]:
 m=bpy.data.materials.new(key);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=.4;p.inputs['Metallic'].default_value=metal;mat[key]=m
for rec in kit['parts']:
 f=rec['files']['npz'];p=r/f['path']
 if sha(p)!=f['sha256']:raise ValueError('Changed inspection source')
 inputs.append(p)
 with zipfile.ZipFile(p) as z:points=npy(z.read('vertices.npy'));faces=npy(z.read('faces.npy'))
 if any(len(f)!=4 for f in faces):raise ValueError('Non-quad source')
 name=rec['name'];mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],faces);mesh.update();mesh.use_auto_smooth=True;mesh.auto_smooth_angle=math.radians(80)
 for face in mesh.polygons:face.use_smooth=True
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(mat['moving' if name.startswith('wing_manual_door') else 'fixed' if name.startswith('torso_manual_shell') else 'hardware']);objects[name]=obj
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.5;scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.9,.92,.94,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
for name,pos,power,size in [('key',(.2,-.6,.9),5.5,.5),('fill',(-.4,-.3,.55),2.5,.4),('rim',(.1,.4,.7),4,.3)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=pos;aim(obj,(0,0,.33))
data=bpy.data.cameras.new('inspection');data.type='ORTHO';camera=bpy.data.objects.new('inspection',data);bpy.context.collection.objects.link(camera);scene.camera=camera;views=[]
for name,pos,target,scale,angle in [('closed',(.46,-.65,.56),(0,0,.32),.40,0),('open45',(.46,-.65,.56),(0,-.03,.32),.44,-45),('detail',(.14,-.33,.47),(.013,-.105,.37),.115,0)]:
 for obj in objects.values():obj.matrix_world=Matrix.Identity(4);obj.hide_render=False
 if angle:
  origin=Vector((0,cfg['axis_right_yz_mm'][0]/1000,cfg['axis_right_yz_mm'][1]/1000));objects['wing_manual_door_right'].matrix_world=Matrix.Translation(origin)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-origin)
  for suffix in ['thumb_screw','m3_washer']:objects['wing_closure_right_'+suffix].hide_render=True
 camera.location=pos;aim(camera,target);data.ortho_scale=scale;path=out/(name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);views.append(dict(name=name,path=str(path.relative_to(r)),sha256=sha(path),camera_position=pos,target=target,scale_m=scale,right_door_service_rotation_deg=angle));print('INSPECTION_RENDER',name,flush=True)
report=dict(schema='goose_manual_wing_service_blender_views_v1',views=views,blender=bpy.app.version_string,source_parts=len(objects),actual_cad_derived_quads=True,geometry_modifiers=0,render_settings=dict(engine='CYCLES',samples=48,denoising=False,resolution=800,view_transform=scene.view_settings.view_transform,look=scene.view_settings.look,exposure=scene.view_settings.exposure,light_powers_w=[5.5,2.5,4]),inspection_colours_not_final_product_colours=True,manufacturing_release=False,source_hashes={str(p.resolve().relative_to(root)):sha(p) for p in inputs})
(r/'evidence/manual_wing_service_blender_views.json').write_text(json.dumps(report,indent=2)+'\n')
