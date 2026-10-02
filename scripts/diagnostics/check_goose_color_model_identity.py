"""Verify rendered finishes still use the current mechanical candidate geometry.

Run with Blender. A scene's source bookkeeping may change without changing its
parts; this separate report preserves the original rendering source hash.
"""
import argparse
import array
import hashlib
import json
import sys
from pathlib import Path

import bpy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robot-root', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    root = args.robot_root.resolve()
    scene_path = root/'cad/source/mechanical_preview/scene.json'
    blend_path = root/'cad/source/mechanical_preview/quad_assembly.blend'
    manifest_path = root/'evidence/microduck_color_scheme_render_manifest.json'
    scene = json.loads(scene_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    old_parts = {p['name']: p for p in manifest['source_parts']}
    assert set(old_parts) == {p['name'] for p in scene['parts']}
    for part in scene['parts']:
        assert old_parts[part['name']]['source_sha256'] == part['source_sha256']
        if part.get('geometry_npz'):
            assert sha(root/part['geometry_npz']) == part['source_sha256']
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    objects = [bpy.data.objects[p['name']] for p in scene['parts']]
    digest = hashlib.sha256()
    counts = dict(parts=len(objects), vertices=0, quads=0)
    for obj in sorted(objects, key=lambda x: x.name):
        digest.update(obj.name.encode())
        coordinates = array.array('f', [0]) * (len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
        topology = array.array('i', [0]) * len(obj.data.loops)
        obj.data.loops.foreach_get('vertex_index', topology)
        digest.update(topology.tobytes())
        digest.update(repr(tuple(tuple(row) for row in obj.matrix_world)).encode())
        assert all(len(face.vertices) == 4 for face in obj.data.polygons)
        counts['vertices'] += len(obj.data.vertices)
        counts['quads'] += len(obj.data.polygons)
    geometry_hash = digest.hexdigest()
    assert geometry_hash == manifest['geometry_fingerprint']
    assert counts == manifest['geometry_counts']
    assert {r['scheme'] for r in manifest['renders']} == {'cream', 'graphite', 'lavender', 'sky'}
    for render in manifest['renders']:
        assert sha(root/'images/microduck_color_schemes'/render['file']) == render['sha256']
        assert render['geometry_fingerprint'] == geometry_hash
    report = dict(
        schema='goose_color_current_model_identity_v1',
        original_render_scene_sha256=manifest['source_scene_sha256'],
        current_scene_sha256=sha(scene_path),
        scene_bookkeeping_changed=sha(scene_path) != manifest['source_scene_sha256'],
        all_current_part_source_hashes_match=True,
        current_blend_geometry_fingerprint=geometry_hash,
        geometry_counts=counts,
        all_four_current_geometry_and_file_hashes_pass=True,
        manufacturing_release=False,
        source_hashes={str(p.relative_to(root)): sha(p) for p in [scene_path, blend_path, manifest_path]},
        checker_sha256=sha(Path(__file__)),
    )
    (root/'evidence/microduck_color_current_model_identity.json').write_text(
        json.dumps(report, indent=2) + '\n')
    print('FOUR COLOURS CURRENT GEOMETRY PASS', counts, flush=True)


if __name__ == '__main__':
    main()
