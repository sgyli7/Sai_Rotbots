"""Studio review of real 056 native enclosures on the retained Goose hardware.

Run with the existing Blender 4.0 launcher. Geometry is exported separately from
the source-bound native display cache; no part is hidden, moved or remeshed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'artifacts/goose_v0_2/enclosure_refinement_056'


PALETTE = ROOT / 'robots/Goose_V0.1/configs/microduck_color_blocking_manual_wing_service.json'


def material(name, rgb, roughness, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    mat.diffuse_color = (*rgb, 1)
    return mat


def linear(spec):
    if 'linear_rgb' in spec:
        return spec['linear_rgb']
    x = np.asarray([int(spec['srgb_hex'][i:i+2], 16)/255 for i in (1, 3, 5)])
    return np.where(x <= .04045, x/12.92, ((x+.055)/1.055)**2.4).tolist()


def colour_role(row):
    """One finish per real component; no cut-face paint islands or new trim."""
    name, original = row['name'], row['original_material']
    if name == 'camera_open_eye_bezel':
        return 'eye_ring'
    if name == 'camera_fastened_open_face':
        return 'faceplate'
    if original in ['glass', 'lens']:
        return original
    if name.endswith('flat_rounded_sole') or 'grip_cassette_pad' in name:
        return 'rubber'
    if name in ['front_main_shell_056', 'rear_service_cap_056', 'head_integral_print_shell']:
        return 'shell'
    if ('grip_shell' in name and not any(k in name for k in ['screw', 'washer', 'nut'])) or name.endswith('shoe_upper_056') or ('shoe' in name and 'tpu' in name and not any(k in name for k in ['screw', 'washer', 'nut'])):
        return 'accent'
    if name.endswith('_056') and any(k in name for k in ['protective_skin', 'flexible_knee_sleeve', 'ankle', 'neck', 'head_rear_integrated', 'head_pitch_soft_receiver', 'smooth_flexible', 'flexible_mouth', 'internal_coaxial']):
        return 'structural_dark'
    if original in ['pcb', 'pcb_reference']:
        return 'pcb_reference'
    if original in ['graphite', 'core', 'reference_neck_core', 'rubber', 'seam']:
        return 'mechanism'
    if original in ['metal', 'titanium'] or any(k in name.lower() for k in ['screw', 'washer', 'nut', 'bolt']):
        return 'metal_connector'
    return 'mechanism'


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--views', nargs='+', default=['oblique', 'front', 'side', 'rear'])
    ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--resolution', type=int, default=1100)
    ap.add_argument('--engine', choices=['CYCLES', 'BLENDER_WORKBENCH'], default='CYCLES')
    ap.add_argument('--geometry', type=Path, default=RAW / 'render_geometry.json')
    ap.add_argument('--output', type=Path, default=RAW / 'review')
    ap.add_argument('--colorway', choices=['clay', 'cream', 'graphite', 'lavender', 'sky'], default='clay')
    ap.add_argument('--receipt-name', help='Separate receipt filename for independent view batches')
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
    start = time.monotonic()
    source = args.geometry
    renderer_sha = hashlib.file_digest(Path(__file__).open('rb'), 'sha256').hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = json.loads(source.read_text())
    binding = None
    if source.resolve() == (RAW/'render_geometry.json').resolve():
        binding = json.loads((RAW/'render_binding.json').read_text())
        for field in ['assembly_manifest', 'geometry', 'retained_native_input']:
            item = binding[field]
            path = ROOT/item['path']
            assert hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() == item['sha256'], field
        assert all(r.get('mesh_sha256') for r in rows), 'Canonical renders require every mesh content hash'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    clay = material('Uniform uncoloured clay', (.72, .74, .76), .44)
    tread = material('Sole contact rubber', (.045, .045, .045), .85)
    glass = material('Camera optical surface', (.07, .07, .07), .25)
    colours = {}
    palette = json.loads(PALETTE.read_text())
    if args.colorway != 'clay':
        scheme = next(s for s in palette['schemes'] if s['id'] == args.colorway)
        for role, spec in {**palette['common_materials'], **scheme['materials']}.items():
            colours[role] = material(role, linear(spec), spec.get('roughness', .45), spec.get('metallic', 0))
    role_bindings = []
    mesh_inputs = []
    count = 0
    for i, row in enumerate(rows):
        actual_mesh_sha = hashlib.file_digest(Path(row['path']).open('rb'), 'sha256').hexdigest()
        assert row.get('mesh_sha256', actual_mesh_sha) == actual_mesh_sha, row['name']
        mesh_inputs.append({'part': row['name'], 'sha256': actual_mesh_sha,
                            'native_source': row.get('native_source')})
        with np.load(row['path'], allow_pickle=False) as data:
            vertices, faces, normals = data['vertices'], data['faces'], data['normals']
        mesh = bpy.data.meshes.new(row['name'])
        mesh.vertices.add(len(vertices))
        mesh.vertices.foreach_set('co', vertices.ravel())
        mesh.loops.add(faces.size)
        mesh.loops.foreach_set('vertex_index', faces.ravel())
        mesh.polygons.add(len(faces))
        mesh.polygons.foreach_set('loop_start', np.arange(len(faces), dtype=np.int32) * 3)
        mesh.polygons.foreach_set('loop_total', np.full(len(faces), 3, dtype=np.int32))
        mesh.polygons.foreach_set('use_smooth', np.ones(len(faces), dtype=bool))
        mesh.update()
        mesh.use_auto_smooth = True
        mesh.normals_split_custom_set_from_vertices(normals.tolist())
        obj = bpy.data.objects.new(row['name'], mesh)
        bpy.context.collection.objects.link(obj)
        if args.colorway == 'clay':
            mat = tread if row['name'].endswith('flat_rounded_sole') or 'grip_cassette_pad' in row['name'] else glass if row['original_material'] in ['glass', 'lens'] or row['name'] == 'camera_fastened_open_face' else clay
            role = mat.name
        else:
            role = colour_role(row)
            mat = colours[role]
        obj.data.materials.append(mat)
        role_bindings.append({'part': row['name'], 'finish': role})
        count += len(faces)
        if i % 400 == 0:
            print('GEOMETRY', i, len(rows), flush=True)
    assert count == sum(r['triangles'] for r in rows)
    floor = material('Neutral studio floor', (.80, .80, .80), .80)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.0052))
    bpy.context.object.name = 'STUDIO_floor'
    bpy.context.object.data.materials.append(floor)
    floor_object = bpy.context.object
    for name, location, power, size in [('key', (.55, -.85, 1.65), 60, .9),
                                         ('fill', (-.85, -.35, 1.0), 25, 1.2),
                                         ('rim', (.15, .90, 1.30), 80, .8)]:
        light = bpy.data.lights.new('STUDIO_' + name, 'AREA')
        light.energy, light.shape, light.size = power, 'DISK', size
        obj = bpy.data.objects.new(light.name, light)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        aim(obj, (0, 0, .35))
    world = bpy.data.worlds.new('Neutral studio')
    world.color = (.86, .87, .88)
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.90, .90, .90, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .65
    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = args.engine
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'BOTH'
    scene.display.shading.curvature_ridge_factor = 1.15
    scene.display.shading.curvature_valley_factor = 1.0
    scene.display.shading.background_type = 'VIEWPORT'
    scene.display.shading.background_color = (.91, .92, .93)
    scene.cycles.samples = args.samples
    scene.cycles.seed = 0
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 6
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = round(args.resolution * 1.08)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX' if args.engine == 'CYCLES' else 'Standard'
    scene.view_settings.look = 'AgX - Medium High Contrast' if args.engine == 'CYCLES' else 'None'
    scene.view_settings.exposure = -1.0 if args.engine == 'CYCLES' else 0
    camera_data = bpy.data.cameras.new('Design review camera')
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = .83
    positions = {'oblique': (1.15, -1.75, 1.01), 'front': (2, 0, .35),
                 'side': (0, -2, .35), 'rear': (-2, 0, .35), 'top': (0, 0, 2),
                 'bottom': (0, 0, -2), 'feet': (.40, -.80, .28),
                 'heel': (-.40, -.80, .25), 'neck': (.6, -1, .8),
                 'inboard_left': (.65, .55, .37),
                 'inboard_right': (.65, -.55, .37),
                 'body': (.8, -1.4, .68), 'body_rear': (-2, 0, .348),
                 'body_side': (-.069, -2, .348), 'body_bottom': (-.069, 0, -2)}
    receipt = {'source': str(source), 'source_sha256': hashlib.file_digest(source.open('rb'), 'sha256').hexdigest(),
               'display_objects': len(rows), 'source_triangles': count, 'omitted_objects': [],
               'geometry_modifiers': 0, 'physics_steps': 0, 'views': [], 'samples': args.samples,
               'scope': 'Actual native056 enclosure surfaces and retained hardware; engineering qualification separately recorded',
               'denoising': False, 'hardware_geometry_hidden': False}
    receipt.update(colorway=args.colorway, whole_part_finish_bindings=role_bindings,
                   renderer_source=str(Path(__file__).relative_to(ROOT)), renderer_sha256=renderer_sha,
                   assembly_binding=binding, source_bound_meshes=mesh_inputs,
                   identity_status='SOURCE_BOUND_NATIVE_ASSEMBLY' if binding else 'UNBOUND_DIAGNOSTIC_DISPLAY',
                   palette_source=str(PALETTE.relative_to(ROOT)),
                   palette_sha256=hashlib.file_digest(PALETTE.open('rb'), 'sha256').hexdigest(),
                   new_colour_boundary_geometry=0, face_colour_partitions=0)
    receipt['render_engine'] = args.engine
    for view in args.views:
        camera.location = positions[view]
        if view in ['inboard_left', 'inboard_right']:
            target = (.015, 0, .235)
            camera_data.ortho_scale = .64
        else:
            target = (.025, -.125, .075) if view in ['feet', 'heel'] else (.06, 0, .55) if view == 'neck' else (-.069, 0, .348) if view.startswith('body') else (.015, 0, .345)
            camera_data.ortho_scale = .27 if view in ['feet', 'heel'] else .40 if view == 'neck' else .46 if view.startswith('body') else .83
        floor_object.hide_render = view in ['top', 'bottom', 'body_bottom']
        aim(camera, target)
        scene.render.filepath = str(args.output / (args.colorway + '_' + view + '.png'))
        bpy.ops.render.render(write_still=True)
        image = Path(scene.render.filepath)
        receipt['views'].append({'view': view, 'image': str(image),
                                 'camera_position_m': list(camera.location), 'target_m': target,
                                 'ortho_scale_m': camera_data.ortho_scale, 'studio_floor_hidden': floor_object.hide_render,
                                 'sha256': hashlib.file_digest(image.open('rb'), 'sha256').hexdigest()})
        receipt['elapsed_s'] = time.monotonic() - start
        assert hashlib.file_digest(Path(__file__).open('rb'), 'sha256').hexdigest() == renderer_sha, 'Renderer changed during this view set'
        receipt_path = args.output / (args.receipt_name or args.colorway + '_render_receipt.json')
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
        print('DESIGN_VIEW_COMPLETE', view, image, flush=True)


if __name__ == '__main__':
    main()
