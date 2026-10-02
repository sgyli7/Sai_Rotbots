"""Render the 462-part Microduck colour blocking, preserving exact quad geometry.

Run with Blender, not the project Python. Geometry comes exclusively from the
hashed scene inputs; colours never change the mechanical model or mass ledger.
"""
import argparse
import array
import ast
import fnmatch
import hashlib
import json
import math
import os
import threading
import sys
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def srgb_hex_to_linear(value):
    if len(value) != 7 or not value.startswith('#'):
        raise ValueError(f'Invalid sRGB colour: {value}')
    srgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in srgb]


def read_npy_2d(raw):
    # Blender's bundled Python need not contain NumPy. Only numeric arrays are
    # accepted; no pickle and no code execution through deserialization.
    if raw[:6] != b'\x93NUMPY':
        raise ValueError('Invalid NPY magic')
    version = raw[6]
    size = 2 if version == 1 else 4 if version in (2, 3) else 0
    if not size:
        raise ValueError('Unsupported NPY version')
    length = int.from_bytes(raw[8:8 + size], 'little')
    start = 8 + size
    header = ast.literal_eval(raw[start:start + length].decode('latin1'))
    shape, kind = header['shape'], header['descr']
    if header['fortran_order'] or len(shape) != 2 or kind not in ('<f8', '<i8', '>f8', '>i8'):
        raise ValueError('Unsupported NPY geometry encoding')
    values = array.array('d' if kind.endswith('f8') else 'q')
    values.frombytes(raw[start + length:])
    if (kind[0] == '<' and sys.byteorder != 'little') or (kind[0] == '>' and sys.byteorder != 'big'):
        values.byteswap()
    if len(values) != shape[0] * shape[1]:
        raise ValueError('NPY geometry size mismatch')
    iterator = iter(values)
    return list(zip(*([iterator] * shape[1])))


def material_from_spec(name, spec):
    color = spec.get('linear_rgb')
    if color is None:
        color = srgb_hex_to_linear(spec['srgb_hex'])
    if len(color) != 3 or not all(0 <= float(v) <= 1 for v in color):
        raise ValueError(f'Invalid linear RGB for {name}')
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = spec['roughness']
    bsdf.inputs['Metallic'].default_value = spec['metallic']
    mat.diffuse_color = (*color, 1)
    mat['linear_rgb'] = color
    return mat


def add_faceplate_paint(mat, eye_spec, settings):
    if not settings.get('enabled'):
        return
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    coord = nodes.new('ShaderNodeTexCoord')
    xyz = nodes.new('ShaderNodeSeparateXYZ')
    links.new(coord.outputs['Object'], xyz.inputs[0])
    square_y, square_z = nodes.new('ShaderNodeMath'), nodes.new('ShaderNodeMath')
    for square, axis in ((square_y, 'Y'), (square_z, 'Z')):
        square.operation = 'MULTIPLY'
        links.new(xyz.outputs[axis], square.inputs[0])
        links.new(xyz.outputs[axis], square.inputs[1])
    radius_squared = nodes.new('ShaderNodeMath'); radius_squared.operation = 'ADD'
    links.new(square_y.outputs[0], radius_squared.inputs[0]); links.new(square_z.outputs[0], radius_squared.inputs[1])
    outer, inner = nodes.new('ShaderNodeMath'), nodes.new('ShaderNodeMath')
    outer.operation, inner.operation = 'LESS_THAN', 'GREATER_THAN'
    outer.inputs[1].default_value = settings['outer_radius_m'] ** 2
    inner.inputs[1].default_value = settings['inner_radius_m'] ** 2
    links.new(radius_squared.outputs[0], outer.inputs[0]); links.new(radius_squared.outputs[0], inner.inputs[0])
    annulus = nodes.new('ShaderNodeMath'); annulus.operation = 'MULTIPLY'
    links.new(outer.outputs[0], annulus.inputs[0]); links.new(inner.outputs[0], annulus.inputs[1])
    mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MIX'
    bsdf = nodes['Principled BSDF']
    mix.inputs[1].default_value = bsdf.inputs['Base Color'].default_value
    rgb = eye_spec.get('linear_rgb') or srgb_hex_to_linear(eye_spec['srgb_hex'])
    mix.inputs[2].default_value = (*rgb, 1)
    links.new(annulus.outputs[0], mix.inputs[0]); links.new(mix.outputs[0], bsdf.inputs['Base Color'])
    mat['paint_only_eye_halo'] = True


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def fingerprint(objects):
    """Hash coordinates, quad topology and placement, excluding all finishes."""
    digest = hashlib.sha256()
    counts = {'parts': len(objects), 'vertices': 0, 'quads': 0}
    for obj in sorted(objects, key=lambda x: x.name):
        digest.update(obj.name.encode())
        coordinates = array.array('f', [0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
        topology = array.array('i', [0]) * len(obj.data.loops)
        obj.data.loops.foreach_get('vertex_index', topology)
        digest.update(topology.tobytes())
        digest.update(repr(tuple(tuple(row) for row in obj.matrix_world)).encode())
        if any(len(face.vertices) != 4 for face in obj.data.polygons):
            raise ValueError(f'Non-quad source mesh: {obj.name}')
        counts['vertices'] += len(obj.data.vertices)
        counts['quads'] += len(obj.data.polygons)
    return digest.hexdigest(), counts


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scene', type=Path, required=True)
parser.add_argument('--geometry-root', type=Path, required=True)
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--manifest', type=Path)
parser.add_argument('--blend-output', type=Path)
parser.add_argument('--live-scene', type=Path, help='Abort within one second if the live canonical source changes')
parser.add_argument('--head-detail', action='store_true', help='Also render Cream head detail from source review camera')
parser.add_argument('--resolution', type=int, default=1200)
parser.add_argument('--samples', type=int, default=192)
parser.add_argument('--schemes', default='cream,graphite,lavender,sky')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
args.output.mkdir(parents=True, exist_ok=True)
payload = json.loads(args.scene.read_text())
config = json.loads(args.config.read_text())
if config['robot_id'] != 'Goose_V0.1':
    raise ValueError('Wrong robot colour configuration')
if sha256(args.scene) != config['source_scene_sha256'] or len(payload['parts']) != 462:
    raise ValueError('The 462-part palette must use its exact frozen scene version')
live_scene = (args.live_scene or args.scene).resolve()
expected_source_sha256 = config['source_scene_sha256']
if sha256(live_scene) != expected_source_sha256:
    raise ValueError('Live source changed before starting; stop and align the candidate version')
guard_stop = threading.Event()
def watch_source():
    while not guard_stop.wait(1.0):
        try:
            observed = sha256(live_scene)
        except Exception as exc:
            print(f'SOURCE_GUARD_FAILURE {live_scene} {exc}', flush=True)
            os._exit(25)
        if observed != expected_source_sha256:
            print(f'SOURCE_VERSION_CHANGED expected={expected_source_sha256} observed={observed} path={live_scene}', flush=True)
            os._exit(24)
threading.Thread(target=watch_source, daemon=True, name='frozen_scene_guard').start()

def require_frozen_source():
    if sha256(live_scene) != expected_source_sha256:
        raise ValueError('Live source version changed; candidate render stopped')

schemes = {scheme['id']: scheme for scheme in config['schemes']}
requested = list(filter(None, args.schemes.split(',')))
if any(key not in schemes for key in requested) or len(set(requested)) != len(requested):
    raise ValueError('Unknown or repeated colour scheme')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
collection = bpy.data.collections.new('Goose colour review - identical quad geometry')
bpy.context.scene.collection.children.link(collection)
groups, robot_objects, part_roles, source_parts = {}, [], {}, []
translation = payload.get('assembly_translation_m', [0, 0, 0])
if len(translation) != 3 or not all(math.isfinite(float(v)) for v in translation):
    raise ValueError('Invalid assembly translation')
root = args.geometry_root.resolve()
for part in payload['parts']:
    group_name = part['group']
    if group_name not in groups:
        group = bpy.data.collections.new(group_name)
        collection.children.link(group)
        groups[group_name] = group
    if 'geometry_npz' in part:
        file = (root / part['geometry_npz']).resolve()
        if not file.is_relative_to(root) or sha256(file) != part['source_sha256']:
            raise ValueError(f"Geometry identity/hash mismatch: {part['name']}")
        with zipfile.ZipFile(file) as data:
            points = read_npy_2d(data.read('vertices.npy'))
            faces = read_npy_2d(data.read('faces.npy'))
    else:
        points, faces = part['vertices'], part['faces']
    if not faces or any(len(face) != 4 for face in faces):
        raise ValueError(f"Editable source must contain quads: {part['name']}")
    center = Vector(tuple((min(v[i] for v in points) + max(v[i] for v in points)) / 2 for i in range(3)))
    mesh = bpy.data.meshes.new(part['name'])
    mesh.from_pydata([tuple(v[i] - center[i] for i in range(3)) for v in points], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(part['name'], mesh)
    groups[group_name].objects.link(obj)
    obj.location = center + Vector(translation)
    obj['source_sha256'] = part.get('source_sha256', hashlib.sha256(json.dumps(part, sort_keys=True).encode()).hexdigest())
    obj['assembly_group'] = group_name
    obj['part_role'] = part.get('role', 'custom_visual_candidate')
    obj['original_material'] = part['material']
    role = config['material_roles'].get(part['material'])
    if role is None:
        raise ValueError(f"New material needs an explicit colour role: {part['material']}")
    for override in config['part_role_overrides']:
        if fnmatch.fnmatchcase(part['name'], override['pattern']):
            role = override['role']
    part_roles[obj.name] = role
    obj['color_role'] = role
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.use_auto_smooth = True
    mesh.auto_smooth_angle = math.radians(80)
    # Closed NURBS skin has shared dense quads. Keep its native smooth vertex
    # normals; only rim edges split. No geometry smoothing/subdivision is used.
    obj['shading_geometry_changed'] = False
    field = config.get('display_normal_fields', {}).get(part['name'])
    if field:
        normal_path = (args.config.resolve().parent.parent / field['path']).resolve()
        if sha256(normal_path) != field['sha256'] or field['geometry_sha256'] != part['source_sha256']:
            raise ValueError('Display normal field is not from this exact geometry')
        with zipfile.ZipFile(normal_path) as data:
            canonical = read_npy_2d(data.read('canonical_normals.npy'))
        if len(canonical) != len(mesh.vertices):
            raise ValueError('Display normal field vertex count mismatch')
        mesh.calc_normals_split()
        display_normals = []
        for polygon in mesh.polygons:
            average = tuple(sum(canonical[v][i] for v in polygon.vertices) / 4 for i in range(3))
            alignment = sum(average[i] * polygon.normal[i] for i in range(3))
            for loop_index in polygon.loop_indices:
                v = mesh.loops[loop_index].vertex_index
                if abs(alignment) > .6:
                    sign = 1 if alignment > 0 else -1
                    display_normals.append(tuple(sign * n for n in canonical[v]))
                else:
                    display_normals.append(tuple(mesh.loops[loop_index].normal))
        mesh.normals_split_custom_set(display_normals)
        mesh.update()
        obj['display_normal_field_sha256'] = field['sha256']
        del canonical, display_normals
    # No modifier is created in this closure review. Source gaps and topology stay visible.
    robot_objects.append(obj)
    source_parts.append({'name': obj.name, 'source_sha256': obj['source_sha256'], 'geometry_npz': part.get('geometry_npz'), 'color_role': role})
    del points, faces
bpy.context.view_layer.update()
geometry_hash, geometry_counts = fingerprint(robot_objects)

studio = config.get('render_settings', {})
floor_mat = material_from_spec('STUDIO neutral grey', {'linear_rgb': studio.get('floor_linear_rgb', [.62, .62, .60]), 'roughness': .78, 'metallic': 0})
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.0002))
bpy.context.object.name = 'STUDIO_floor'
bpy.context.object.data.materials.append(floor_mat)

for name, location, power, size, target in [
    ('STUDIO_key', (.45, -.85, 1.45), studio.get('key_power_w', 60), .7, (0, 0, .3)),
    ('STUDIO_fill', (-.9, -.25, .85), studio.get('fill_power_w', 25), .8, (0, 0, .35)),
    ('STUDIO_rim', (.2, .8, 1.2), studio.get('rim_power_w', 80), .7, (0, 0, .4)),
]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.shape, light.size = power, 'DISK', size
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)
world = bpy.data.worlds.new('Colour review studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (*studio.get('world_linear_rgb', [.65, .66, .67]), 1)
world.node_tree.nodes['Background'].inputs[1].default_value = studio.get('world_strength', .3)
scene = bpy.context.scene
scene.world = world
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = False  # This Blender build has no OpenImageDenoiser.
scene.cycles.seed = 0
scene.render.resolution_x = scene.render.resolution_y = args.resolution
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = False
scene.view_settings.view_transform = studio.get('view_transform', 'AgX')
scene.view_settings.look = studio.get('look', 'AgX - Medium High Contrast')
scene.view_settings.exposure = studio.get('exposure', -.65)
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
camera_data = bpy.data.cameras.new('Identical colour review camera')
camera = bpy.data.objects.new('Identical colour review camera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type, camera_data.ortho_scale, camera_data.lens = 'ORTHO', .78, 70
camera.location = (1.15, -1.75, .99)
point_at(camera, (.05, 0, .325))
scene['source_scene_sha256'] = sha256(args.scene)
scene['colour_config_sha256'] = sha256(args.config)
scene['status'] = 'COLOUR REVIEW OF ACTUAL MECHANICAL CANDIDATE - NOT MANUFACTURING RELEASE'

report = {
    'schema_version': 1, 'robot_id': 'Goose_V0.1',
    'scope': 'Four actual Blender renders of one identical mechanical candidate; colour review only.',
    'source_scene_sha256': sha256(args.scene), 'config_sha256': sha256(args.config),
    'renderer_sha256': sha256(Path(__file__)), 'geometry_fingerprint': geometry_hash,
    'geometry_counts': geometry_counts, 'source_parts': source_parts,
    'render_settings': {'engine': 'CYCLES', 'blender': bpy.app.version_string, 'samples': args.samples,
                        'denoising': False, 'resolution': args.resolution, 'seed': 0,
                        'camera_position': list(camera.location), 'orthographic_scale_m': .78,
                        'view_transform': scene.view_settings.view_transform, 'look': scene.view_settings.look, 'exposure': scene.view_settings.exposure},
    'renders': [], 'review_details': [], 'physical_model_changed': False, 'manufacturing_release': False,
    'geometry_modifiers_created': 0,
    'source_guard': {'live_scene': str(live_scene), 'expected_sha256': expected_source_sha256, 'interval_seconds': 1, 'abort_on_change': True},
}
materials_by_scheme = {}
for key in requested:
    require_frozen_source()
    scheme = schemes[key]
    specs = {**config['common_materials'], **scheme['materials']}
    materials = {role: material_from_spec(f'{key}_{role}', spec) for role, spec in specs.items()}
    add_faceplate_paint(materials['faceplate'], specs['eye_ring'], config['faceplate_painted_halo'])
    materials_by_scheme[key] = materials
    for obj in robot_objects:
        obj.data.materials.clear()
        obj.data.materials.append(materials[part_roles[obj.name]])
    scene['colour_scheme'] = key
    current_hash, current_counts = fingerprint(robot_objects)
    if current_hash != geometry_hash or current_counts != geometry_counts:
        raise ValueError('Changing a finish changed source geometry')
    output = args.output / f'{key}.png'
    scene.render.filepath = str(output.resolve())
    bpy.ops.render.render(write_still=True)
    require_frozen_source()
    report['renders'].append({'scheme': key, 'label': scheme['label'], 'file': output.name,
                              'sha256': sha256(output), 'geometry_fingerprint': current_hash,
                              'source_scene_sha256': report['source_scene_sha256']})
    if args.blend_output and key == config['default_scheme']:
        args.blend_output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend_output.resolve()), compress=True)
        report['cream_blend_sha256'] = sha256(args.blend_output)
    print(f'COLOUR_RENDER_COMPLETE {key} {output}', flush=True)
if args.head_detail:
    if 'cream' not in materials_by_scheme:
        raise ValueError('Cream must be requested for the head detail')
    require_frozen_source()
    for obj in robot_objects:
        obj.data.materials.clear()
        obj.data.materials.append(materials_by_scheme['cream'][part_roles[obj.name]])
    view = config['camera_head_detail']
    camera.location = view['position']
    camera_data.ortho_scale = view['orthographic_scale_m']
    point_at(camera, view['target'])
    bpy.context.view_layer.update()
    current_hash, current_counts = fingerprint(robot_objects)
    if current_hash != geometry_hash or current_counts != geometry_counts or any(obj.modifiers for obj in robot_objects):
        raise ValueError('Head review changed source geometry or created a modifier')
    detail_output = args.output / 'cream_head_detail.png'
    scene['colour_scheme'] = 'cream'
    scene.render.filepath = str(detail_output.resolve())
    bpy.ops.render.render(write_still=True)
    require_frozen_source()
    report['review_details'].append({'scheme': 'cream', 'view': 'head_detail', 'file': detail_output.name,
                                    'sha256': sha256(detail_output), 'geometry_fingerprint': current_hash,
                                    'source_scene_sha256': expected_source_sha256,
                                    'camera_position': list(camera.location), 'camera_target': view['target'],
                                    'orthographic_scale_m': camera_data.ortho_scale})
    print(f'COLOUR_HEAD_DETAIL_COMPLETE {detail_output}', flush=True)
require_frozen_source()
report['all_four_schemes_rendered'] = set(requested) == {'cream', 'graphite', 'lavender', 'sky'}
report['identical_geometry_verified'] = all(row['geometry_fingerprint'] == geometry_hash for row in report['renders'])
manifest = args.manifest or args.output / 'manifest.json'
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
require_frozen_source()
guard_stop.set()
print(f'COLOUR_REVIEW_COMPLETE {manifest}', flush=True)
