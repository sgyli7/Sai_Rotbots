"""Compare the selected long pointed visual bill to the inherited mouth mass target.

The surface-area shell estimate is conditional: actual hollow walls, cutouts,
infill, mounts, pads, gears, shaft supports and wire mass need printable CAD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import trimesh


PETG_DENSITY_KG_M3 = 1250.0
XL330_M288_T_MASS_G = 18.0
INHERITED_MOUTH_MODULE_TARGET_G = 65.0
ROBOTIS_XL330_SOURCE = 'https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appearance-dir', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.appearance_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['beak_pose'] != 'closed_visual_only':
        parser.error('Mass comparison requires the closed visual bill')
    parts = {}
    for name in ('beak_upper', 'beak_lower'):
        path = args.appearance_dir / f'{name}.stl'
        mesh = trimesh.load_mesh(path)
        if not mesh.is_watertight or mesh.area <= 0:
            raise ValueError(f'Invalid closed visual solid: {name}')
        parts[name] = {
            'stl_sha256': sha256(path),
            'visual_bounds_mm': mesh.bounds.round(2).tolist(),
            'outer_surface_area_mm2': round(float(mesh.area), 2),
            'solid_volume_mm3': round(float(abs(mesh.volume)), 2),
        }
    total_area_mm2 = sum(p['outer_surface_area_mm2'] for p in parts.values())
    cases = {}
    for wall_mm in (0.8, 1.2, 1.6, 2.4):
        shell_mass_g = total_area_mm2 * wall_mm * 1e-3 * PETG_DENSITY_KG_M3 * 1e-3
        shells_and_motor_g = shell_mass_g + XL330_M288_T_MASS_G
        cases[str(wall_mm)] = {
            'visual_surface_times_uniform_wall_shell_estimate_g': round(shell_mass_g, 2),
            'shells_plus_xl330_only_g': round(shells_and_motor_g, 2),
            'remaining_to_inherited_65g_target_before_gears_frame_pads_wires_g': round(
                INHERITED_MOUTH_MODULE_TARGET_G - shells_and_motor_g, 2),
        }
    result = {
        'status': 'conditional_visual_bill_mass_screen_not_measured_or_manufacturing_release',
        'appearance_manifest_sha256': sha256(manifest_path),
        'source_script_sha256': sha256(Path(__file__)),
        'selected_pointed_bill_parts': parts,
        'combined_outer_surface_area_mm2': round(total_area_mm2, 2),
        'petg_density_assumption_kg_m3': PETG_DENSITY_KG_M3,
        'inherited_mouth_module_mass_target_g': INHERITED_MOUTH_MODULE_TARGET_G,
        'xl330_m288_t_vendor_mass_g': XL330_M288_T_MASS_G,
        'xl330_vendor_source': ROBOTIS_XL330_SOURCE,
        'cases_by_assumed_uniform_wall_mm': cases,
        'limitations': [
            'Visual orange solids are not hollow print parts; surface-area times uniform wall is a proxy, not a minimum possible or actual printed mass.',
            'The jaw gear train, bilateral four-bar, bearings, screws, contact pads, cable, head carrier, reinforcement and tolerances are omitted.',
            'The 65 g target came from an earlier approximately 60-65 mm bill sketch, while this visual bill is longer; the target is not validated for the selected silhouette.',
            'Vendor mass excludes connector and lead; no torque, stiffness, drag or head-neck thermal validation is performed.',
        ],
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'combined_outer_surface_area_mm2': result['combined_outer_surface_area_mm2'],
        'shells_plus_motor_g_at_1p6mm': cases['1.6']['shells_plus_xl330_only_g'],
        'remaining_to_65g_target_g_at_1p6mm': cases['1.6']['remaining_to_inherited_65g_target_before_gears_frame_pads_wires_g'],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
