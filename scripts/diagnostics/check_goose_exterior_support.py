"""Screen the exterior-study sole footprint without inventing a mass model.

The sole meshes are visual geometry, so this reports necessary geometric
conditions only. It cannot certify static balance or a walking gait.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def contact_extent(mesh_path: Path) -> dict:
    vertices = np.asarray(trimesh.load_mesh(mesh_path).vertices)
    floor_z = float(vertices[:, 2].min())
    contact = vertices[vertices[:, 2] <= floor_z + 1.0]
    if len(contact) < 4:
        raise ValueError(f'Insufficient sole contact vertices in {mesh_path}')
    return {
        'x_mm': [round(float(contact[:, 0].min()), 2),
                 round(float(contact[:, 0].max()), 2)],
        'y_mm': [round(float(contact[:, 1].min()), 2),
                 round(float(contact[:, 1].max()), 2)],
        'min_z_mm': round(floor_z, 2),
        'sampled_vertices': int(len(contact)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    left = contact_extent(args.appearance_dir / 'foot_sole_-1.stl')
    right = contact_extent(args.appearance_dir / 'foot_sole_1.stl')
    x_front = min(left['x_mm'][1], right['x_mm'][1])
    x_rear = max(left['x_mm'][0], right['x_mm'][0])
    inner_clearance = min(abs(left['y_mm'][1]), abs(right['y_mm'][0]))
    hip_vertices = np.asarray(trimesh.load_mesh(args.appearance_dir / 'hip_1.stl').vertices)
    hip_x = float((hip_vertices[:, 0].min() + hip_vertices[:, 0].max()) / 2)
    body_vertices = np.asarray(trimesh.load_mesh(args.appearance_dir / 'body.stl').vertices)
    body_center_x = float((body_vertices[:, 0].min() + body_vertices[:, 0].max()) / 2)
    body_front_x = float(body_vertices[:, 0].max())
    beak_vertices = np.asarray(trimesh.load_mesh(args.appearance_dir / 'beak_upper.stl').vertices)
    result = {
        'status': 'support_geometry_only_no_static_or_walking_certification',
        'source_manifest_sha256': hashlib.sha256((args.appearance_dir / 'manifest.json').read_bytes()).hexdigest(),
        'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'coordinate_unit': 'provisional_mm',
        'visual_sole_contact_vertex_extents': {'left': left, 'right': right},
        'double_support_necessary_x_com_interval_mm': [x_rear, x_front],
        'x_com_interval_with_20mm_geometric_margin_mm': [round(x_rear + 20, 2),
                                                          round(x_front - 20, 2)],
        'single_foot_requires_lateral_com_shift_from_centerline_at_least_mm': round(inner_clearance, 2),
        'single_foot_shift_with_10mm_geometric_margin_mm': round(inner_clearance + 10, 2),
        'visual_landmarks_mm': {
            'hip_x': round(hip_x, 2),
            'body_center_x': round(body_center_x, 2),
            'body_front_x': round(body_front_x, 2),
            'beak_upper_front_x': round(float(beak_vertices[:, 0].max()), 2),
            'body_center_minus_hip_x': round(body_center_x - hip_x, 2),
            'sole_front_minus_body_front_x': round(x_front - body_front_x, 2),
        },
        'decision': 'Do not release: there is no measured or component-based center of mass, inertia, foot friction, joint torque or gait test for this appearance study.',
        'limitations': [
            'Visual sole mesh vertices are not a validated rubber contact patch or pressure distribution.',
            'The center-of-mass intervals are necessary geometric conditions, not proof of balance.',
            'Two-foot convex support does not imply single-support walking; the lateral shift must be produced dynamically.',
            'A ground-reach pose changes upper-body projection and requires a separate mass, torque and contact check.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'double_support_necessary_x_com_interval_mm',
                                            'single_foot_requires_lateral_com_shift_from_centerline_at_least_mm',
                                            'visual_landmarks_mm')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
