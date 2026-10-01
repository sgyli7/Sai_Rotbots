"""Bounded native-section bending screen for the uninstalled bill backbones.

Uses actual STEP intersections, including pad holes, rather than the displayed
plastic envelope. This is a distal-blade cantilever approximation: it does not
resolve the keyed ears, supports, threads, shell/pad fastening or fatigue.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from build123d import Compound, ShapeList, import_step

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "robots/Goose_V0.1"
sys.path.insert(0, str(ROOT / "scripts/cad"))
from build_goose_cad import box
from goose_nurbs_skin import native_properties


def native_section(shape, width):
    volume, center, inertia, _ = native_properties(shape)
    area = volume / width
    iy = inertia[1, 1] / width - area * width**2 / 12
    if not np.isfinite(iy) or iy <= 0:
        raise ValueError("invalid native planar second moment")
    return area, center, iy


def main():
    manifest_file = R / "cad/exports/bill_backbones/manifest.json"
    linkage_file = R / "cad/exports/beak_native_linkage/manifest.json"
    contract_file = R / "configs/mechanical_reference_contract.json"
    manifest = json.loads(manifest_file.read_text())
    linkage = json.loads(linkage_file.read_text())
    contract = json.loads(contract_file.read_text())
    joint = next(p for p in contract["joints"] if p["name"] == "beak_hinge")
    jaw_x = linkage["jaw_axis_world_mm"][0]
    lever = 80.0  # Existing project design target, not measured animal force.
    load_x = jaw_x + lever
    torque = joint["torque_peak_limit_nm"]
    force = torque * 1000 / lever
    slice_width = 0.05
    area_check, _, iy_check = native_section(box([slice_width, 20, 4]), slice_width)
    known_area, known_iy = 20 * 4, 20 * 4**3 / 12
    assert abs(area_check / known_area - 1) < 1e-8
    assert abs(iy_check / known_iy - 1) < 1e-8
    check_x = np.linspace(0, 80, 10001)
    integrated = np.trapezoid(50 * (80 - check_x)**2 / (69000 * known_iy), check_x)
    closed_form = 50 * 80**3 / (3 * 69000 * known_iy)
    assert abs(integrated / closed_form - 1) < 1e-8
    # Include each hole centre and its nearby minimum ligaments.
    positions = np.unique(np.r_[np.linspace(177.1, 234.9, 90),
                                [h + d for h in [185, 216]
                                 for d in [-1.34, -1, -.5, 0, .5, 1, 1.34]]])
    results = {}
    step_files = []
    for name, modulus in [("upper_bill_metal_backbone", 69000.0),
                          ("lower_bill_keyed_backbone", 200000.0)]:
        part = next(p for p in manifest["parts"] if p["name"] == name)
        step_file = R / part["files"]["step"]["path"]
        assert hashlib.sha256(step_file.read_bytes()).hexdigest() == part["files"]["step"]["sha256"]
        step_files.append(step_file)
        solid = import_step(step_file).solids()[0]
        rows = []
        for x in positions:
            section = solid.intersect(box([slice_width, 100, 100], [float(x), 0, 575]))
            if isinstance(section, ShapeList):
                section = Compound(children=list(section))
            if not section or not section.solids():
                raise ValueError((name, float(x), "missing native section"))
            bounds = section.bounding_box()
            # Iyy of a thin slab includes dx^2/12 in addition to the planar
            # integral of (z-zc)^2. Remove it before dividing by the slab width.
            area, center, iy = native_section(section, slice_width)
            extreme = max(bounds.max.Z - center[2], center[2] - bounds.min.Z)
            moment = force * (load_x - x)
            stress = abs(moment) * extreme / iy
            rows.append(dict(x_mm=float(x), area_mm2=float(area),
                             second_moment_y_mm4=float(iy),
                             moment_n_mm=float(moment), nominal_stress_mpa=float(stress)))
        worst = max(rows, key=lambda row: row["nominal_stress_mpa"])
        x = np.array([row["x_mm"] for row in rows])
        iy = np.array([row["second_moment_y_mm4"] for row in rows])
        # Virtual work, with an ideal clamp at x=177mm and the actual distal
        # backing plate terminating at x=235mm. Pad/fixture compliance omitted.
        integrand = force * (load_x - x)**2 / (modulus * iy)
        deflection = float(np.trapezoid(integrand, x))
        results[name] = dict(
            sections=rows, worst_section=worst,
            ideal_distal_blade_deflection_mm=deflection,
            assumed_modulus_mpa=modulus,
            illustrative_required_yield_mpa=worst["nominal_stress_mpa"] * 2 * 2,
            assumed_stress_concentration_multiplier=2,
            assumed_yield_safety_factor=2,
            structural_release=False,
        )
        print("BILL LOAD SCREEN", name, "stress MPa", round(worst["nominal_stress_mpa"], 2),
              "ideal blade deflection mm", round(deflection, 4), flush=True)
    phase = linkage["closed_phase_rad"]
    m, j = np.array(linkage["motor_axis_world_mm"]), np.array(linkage["jaw_axis_world_mm"])
    axis_angle = np.arctan2(j[2] - m[2], j[0] - m[0])
    angles = np.linspace(*joint["range_rad"], 1001)
    sine = np.abs(np.sin(phase - angles - axis_angle))
    pin_force = torque * 1000 / linkage["crank_radius_mm"] / float(sine.min())
    # The round-journal value deliberately does not certify the D-flat or its
    # axial transition. A diameter-6 inscribed circle is only a sizing reference.
    round_tau = 16 * torque * 1000 / (np.pi * 8**3)
    six_tau = 16 * torque * 1000 / (np.pi * 6**3)
    report = dict(
        schema="goose_bill_native_section_load_screen_v1",
        installed=False, structural_release=False, manufacturing_release=False,
        numeric_sanity=dict(native_rectangle_area_relative_error=float(abs(area_check / known_area - 1)),
                            native_rectangle_second_moment_relative_error=float(abs(iy_check / known_iy - 1)),
                            uniform_beam_deflection_relative_error=float(abs(integrated / closed_form - 1))),
        load=dict(project_target_contact_force_n=50, equivalent_design_peak_force_n=force,
                  design_peak_torque_nm=torque, lever_mm=lever, load_world_x_mm=load_x),
        blades=results,
        linkage=dict(sample_count=len(angles), minimum_transmission_sine=float(sine.min()),
                     worst_ideal_pin_force_n=pin_force,
                     mean_bush_pressure_mpa=pin_force / (5 * 4),
                     bush_pressure_status="project 5mm ID / 4mm working width, exact installation and PV not released"),
        shaft=dict(round_8mm_nominal_torsion_mpa=float(round_tau),
                   inscribed_6mm_circle_torsion_reference_mpa=float(six_tau),
                   d_flat_and_transition_strength_released=False,
                   material_certificate_and_axial_retention_released=False),
        source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [manifest_file, linkage_file, contract_file, Path(__file__), *step_files]},
        limitations=[
            "Distal blade only; ideal clamp at X177. Native thin-slab sections include holes, not full 3D support stress.",
            "Load is at X240 beyond the backing plate. Actual pad/shell fixture transferring that load remains absent.",
            "Elastic moduli, concentration multiplier and safety factor are explicit screen assumptions, not material certificates.",
            "No shell normal-thickness, shaft D-flat/transition, lug, bearing seat, bolt/thread, fatigue or thermal release.",
            "No verified real animal bite-force datum; no promise of measured continuous 50N grip.",
            "Not a hard bound on real peak stress or deflection; no whole-head/robot release from this screen.",
        ],
    )
    (R / "evidence/native_bill_load_screen.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
