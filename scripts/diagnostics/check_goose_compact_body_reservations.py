"""Screen existing component reservations against a compact visual torso.

The visual torso is a scaled, filleted solid, not a hollow printable enclosure.
This check only asks whether previously reserved component boxes lie inside a
nominal inner surface after shell/fit allowance. It does not place mounts,
connectors, service-door hardware, structural ribs, or wiring paths.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from check_goose_exterior_reach import body_signed_distance, pivots_from_manifest


BASE_HALF_SIZE_MM = np.array([175.0, 102.5, 115.0])
BASE_FILLET_RADIUS_MM = 92.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_body_clearance_mm(point_mm: np.ndarray, center_mm: np.ndarray,
                              scale: np.ndarray) -> float:
    """Conservative distance-to-surface bound for an affine-scaled round box."""
    unscaled = (point_mm - center_mm) / scale
    distance_in_base = float(body_signed_distance(unscaled[np.newaxis, :],
                                                 np.zeros(3), BASE_HALF_SIZE_MM,
                                                 BASE_FILLET_RADIUS_MM)[0])
    # For a point within a scaled solid, the least singular value gives a
    # conservative lower bound on real clearance to any outer surface.
    return -distance_in_base * float(scale.min())


def screen(appearance_dir: Path, reservations_path: Path,
           wall_mm: float, fit_mm: float) -> dict:
    manifest_path = appearance_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if not manifest.get('compact_body_study'):
        raise ValueError('This check expects a compact-body appearance study')
    scale = np.array(manifest['body_scale_xyz'], dtype=float)
    center = pivots_from_manifest(appearance_dir)['body_center']
    reservations = json.loads(reservations_path.read_text())
    if reservations['coordinate_frame'] != 'torso_x_forward_y_left_z_up' or reservations['units'] != 'SI':
        raise ValueError('Component reservation frame or units do not match')
    rows = []
    for item in reservations['components']:
        local_center = np.array(item['center_m'], dtype=float) * 1000
        half_size = np.array(item['reserved_xyz_m'], dtype=float) * 500
        corners = [center + local_center + half_size * np.array(sign)
                   for sign in itertools.product((-1, 1), repeat=3)]
        minimum = min(rounded_body_clearance_mm(corner, center, scale)
                      for corner in corners)
        rows.append({
            'name': item['name'],
            'sku': item['sku'],
            'minimum_conservative_outer_surface_clearance_mm': round(minimum, 2),
            'shell_and_fit_allowance_mm': round(wall_mm + fit_mm, 2),
            'nominal_inner_surface_margin_mm': round(minimum - wall_mm - fit_mm, 2),
            'within_nominal_inner_surface': bool(minimum >= wall_mm + fit_mm),
        })
    rows.sort(key=lambda row: row['nominal_inner_surface_margin_mm'])
    return {
        'status': 'component_box_reservation_screen_only_not_mounting_or_service_access',
        'appearance_manifest_sha256': sha256(manifest_path),
        'component_reservations_sha256': sha256(reservations_path),
        'source_script_sha256': sha256(Path(__file__)),
        'visual_body_dimensions_mm': np.round(2 * BASE_HALF_SIZE_MM * scale, 2).tolist(),
        'visual_body_center_mm': np.round(center, 2).tolist(),
        'shell_and_fit_allowance_mm': round(wall_mm + fit_mm, 2),
        'all_box_corners_within_nominal_inner_surface': all(
            row['within_nominal_inner_surface'] for row in rows),
        'minimum_nominal_inner_surface_margin_mm': min(
            row['nominal_inner_surface_margin_mm'] for row in rows),
        'reservations': rows,
        'limitations': [
            'The surface is currently a solid appearance mesh. This assumes it can be hollowed without ribs, doors, joints or fasteners taking the same space.',
            'A component reservation is an axis-aligned planning box, not a vendor STEP model, board mount or connector/thermal clearance.',
            'The fused_harness_switches reservation is an estimated distributed mass and routing allowance; its box overlaps other reservations and cannot be interpreted as one rigid part.',
            'Hip and neck motors, service-door hinges, battery extraction, cable bend radii and the load-bearing frame are not screened.',
            'This is a necessary spatial screen, not a manufacturing, electrical, mass or thermal release.',
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--reservations', type=Path, required=True)
    parser.add_argument('--wall-mm', type=float, default=2.4)
    parser.add_argument('--fit-mm', type=float, default=0.3)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if args.wall_mm <= 0 or args.fit_mm < 0:
        parser.error('Shell wall must be positive and fit allowance nonnegative')
    result = screen(args.appearance_dir, args.reservations,
                    args.wall_mm, args.fit_mm)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'body_mm': result['visual_body_dimensions_mm'],
        'all_within': result['all_box_corners_within_nominal_inner_surface'],
        'minimum_margin_mm': result['minimum_nominal_inner_surface_margin_mm'],
        'nearest_reservation': result['reservations'][0]['name'],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
