"""Remove zero-area export facets from a Goose visual STL.

This only fixes a mesh-topology defect. It does not add mechanical features,
wall strength, tolerances or print-ready status to the CAD design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--source-step', type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Keep the raw STL; the cleaned mesh needs a new path')
    raw = trimesh.load_mesh(args.input)
    if not isinstance(raw, trimesh.Trimesh) or not raw.is_winding_consistent:
        raise ValueError('Expected one consistently wound triangle mesh')

    clean = raw.copy()
    clean.update_faces(clean.nondegenerate_faces(height=1e-8))
    clean.remove_unreferenced_vertices()
    removed = len(raw.faces) - len(clean.faces)
    if removed <= 0 or not clean.is_watertight or not clean.is_winding_consistent:
        raise ValueError('Removing degenerate facets did not close the STL')
    if np.max(np.abs(raw.bounds - clean.bounds)) > 1e-6:
        raise ValueError('Cleanup changed the mesh bounds')
    if abs(raw.volume - clean.volume) > 1e-5:
        raise ValueError('Cleanup changed the enclosed volume')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    clean.export(args.output)
    checked = trimesh.load_mesh(args.output)
    if not checked.is_watertight or not checked.is_winding_consistent:
        raise ValueError('The exported cleaned STL did not survive reload')
    if np.max(np.abs(raw.bounds - checked.bounds)) > 1e-6:
        raise ValueError('Export changed the cleaned STL bounds')
    if abs(raw.volume - checked.volume) > 1e-5:
        raise ValueError('Export changed the cleaned STL volume')

    result = {
        'status': 'visual_mesh_topology_cleaned_not_manufacturing_release',
        'source_script_sha256': sha256(Path(__file__)),
        'source_step': str(args.source_step),
        'source_step_sha256': sha256(args.source_step),
        'raw_stl': str(args.input),
        'raw_stl_sha256': sha256(args.input),
        'clean_stl': str(args.output),
        'clean_stl_sha256': sha256(args.output),
        'removed_zero_area_facets': removed,
        'triangle_count_before_after': [len(raw.faces), len(checked.faces)],
        'watertight_before_after': [bool(raw.is_watertight), bool(checked.is_watertight)],
        'winding_consistent_before_after': [bool(raw.is_winding_consistent),
                                           bool(checked.is_winding_consistent)],
        'volume_mm3_before_after': [round(float(raw.volume), 5),
                                    round(float(checked.volume), 5)],
        'bounds_mm_before_after': [raw.bounds.round(5).tolist(),
                                   checked.bounds.round(5).tolist()],
        'limitations': [
            'Removing zero-area facets changes mesh topology but does not change or validate the source BREP design.',
            'Watertightness alone cannot approve local wall thickness, joint clearance, fastening, print orientation, slicer settings or material strength.',
            'The v95 head remains an appearance study and cannot be printed as a functional robot part.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'],
                      'removed_zero_area_facets': removed,
                      'watertight_after': result['watertight_before_after'][1],
                      'volume_mm3_before_after': result['volume_mm3_before_after']}))


if __name__ == '__main__':
    main()
