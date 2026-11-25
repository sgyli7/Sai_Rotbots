"""Render multi-panel engineering visual for body016_front untouched + yoke outer-lip relief."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path("/home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots")
OUT = ROOT / "artifacts/goose_v0_2/hardware_closeout_20261125/front_shell_relief"
ART_VIS = Path("/home/ethan/.gemini/antigravity/brain/80941710-c752-44e4-ac0f-f61926d12fb5/visuals")


def main() -> None:
    survey = json.loads((OUT / "front_shell_clearance_survey.json").read_text())
    relief = json.loads((OUT / "yoke_outer_lip_relief_receipt.json").read_text())
    polar = json.loads((OUT / "yoke_and_shell_polar_sections.json").read_text())
    npz = np.load(ROOT / "artifacts/goose_v0_2/hip_yaw_hour_20261118_001/source003_step2_structure_clearance_20261120/smooth_006/nominal_left/mb_s006_left_fields.npz")

    plt.rcParams.update({
        "font.size": 9.5,
        "axes.edgecolor": "#334155",
        "axes.linewidth": 0.9,
        "grid.color": "#cbd5e1",
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
    })

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.2), dpi=180)
    fig.patch.set_facecolor("#f8fafc")

    # Panel A: Full-yaw clearance BEFORE vs AFTER
    ax = axes[0]
    ax.set_facecolor("white")
    s_l = survey["sides"]["left"]["samples"]
    r_l = relief["sides"]["left"]["sweep"]
    s_r = survey["sides"]["right"]["samples"]
    r_r = relief["sides"]["right"]["sweep"]

    ax.plot([x["yaw_deg"] for x in s_l], [x["gap_mm"] for x in s_l], color="#dc2626", lw=2.0, label="Before (004/006 Left): min 0.082 mm")
    ax.plot([x["yaw_deg"] for x in s_r], [x["gap_mm"] for x in s_r], color="#f97316", lw=1.4, ls="--", label="Before (004/006 Right): min 0.082 mm")
    ax.plot([x["yaw_deg"] for x in r_l], [x["gap_mm"] for x in r_l], color="#059669", lw=2.2, label="After (Yoke Lip Relief Left): min 1.587 mm")
    ax.plot([x["yaw_deg"] for x in r_r], [x["gap_mm"] for x in r_r], color="#0284c7", lw=1.4, ls="--", label="After (Yoke Lip Relief Right): min 1.587 mm")
    ax.axhline(1.50, color="#0f766e", ls=":", lw=1.3, label="Target Unloaded Floor (1.50 mm)")
    ax.axhspan(0.0, 0.50, color="#fecaca", alpha=0.35, label="Manufacturing Scrape Hazard (<0.5 mm)")

    ax.annotate("Band 1 worst:\n0.082 mm @ 10.7°", xy=(10.73, 0.0823), xytext=(5.5, 0.62),
                arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.2), fontsize=8.3, fontweight="bold", color="#991b1b",
                bbox=dict(boxstyle="round,pad=0.25", fc="#fee2e2", ec="#dc2626", lw=0.8))
    ax.annotate("Band 0 worst:\n0.303 mm @ 32.7°", xy=(32.66, 0.3029), xytext=(8.5, 1.08),
                arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.2), fontsize=8.3, color="#991b1b",
                bbox=dict(boxstyle="round,pad=0.25", fc="#fee2e2", ec="#dc2626", lw=0.8))
    ax.annotate("Global min after:\n1.587 mm (19.3x)\n0/162 poses <1.5 mm", xy=(10.31, 1.5869), xytext=(-31, 2.02),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1.2), fontsize=8.3, fontweight="bold", color="#065f46",
                bbox=dict(boxstyle="round,pad=0.25", fc="#d1fae5", ec="#059669", lw=0.8))

    ax.set_title("A. Full-Yaw Unloaded Clearance vs body016_front\n(body016_front 100% Untouched)", fontweight="bold", fontsize=10.5)
    ax.set_xlabel("Hip Yaw Angle (deg)")
    ax.set_ylabel("Minimum 3D Distance (mm)")
    ax.set_xlim(-35, 35)
    ax.set_ylim(0, 2.55)
    ax.grid(True)
    ax.legend(loc="lower left", fontsize=7.2, framealpha=0.95)

    # Panel B: Radial Envelope Profile (R from HY Axis vs Z)
    ax = axes[1]
    ax.set_facecolor("white")
    prof = relief["sides"]["left"]["shell_min_r_profile_zr_wall"]
    zs_s = np.array([p[0] for p in prof])
    rin_s = np.array([p[1] for p in prof])
    rout_s = rin_s + np.array([p[2] for p in prof])

    ax.fill_betweenx(zs_s, rin_s, rout_s, color="#94a3b8", alpha=0.45, label="Untouched PA12 Shell (2.12-2.27 mm wall)")
    ax.plot(rin_s, zs_s, color="#334155", lw=1.8, label="Shell Inner Wall R_in(z)")
    ax.plot(rout_s, zs_s, color="#0f172a", lw=1.2, ls="--", label="Shell Outer Silhouette (Unchanged)")

    # Old vs New Yoke max_r from polar slices & relief checks
    z_old, r_old, r_inner = [], [], []
    for z_str, sl in sorted(polar["yoke_slices"].items(), key=lambda kv: float(kv[0])):
        if sl.get("empty"):
            continue
        outer_rays = [r for r in sl["rays"] if 40 <= r["theta_deg"] <= 140]
        if outer_rays:
            z_old.append(float(z_str))
            r_old.append(max(r["solid_r_intervals_mm"][-1][1] for r in outer_rays))
            # representative inner collar wall
            r_in_vals = [r["solid_r_intervals_mm"][-1][0] for r in outer_rays if r["solid_r_intervals_mm"][-1][0] > 28]
            r_inner.append(np.median(r_in_vals) if r_in_vals else r_old[-1] - 7.0)

    z_old = np.array(z_old)
    r_old = np.array(r_old)
    r_inner = np.array(r_inner)
    r_allow = np.interp(z_old, zs_s, rin_s - 1.62)
    r_new = np.minimum(r_old, r_allow)

    ax.fill_betweenx(z_old, r_inner, r_new, color="#10b981", alpha=0.35, label="Retained Steel Yoke Wall (>=5.58 mm)")
    ax.fill_betweenx(z_old, r_new, r_old, color="#ef4444", alpha=0.55, label="Trimmed Outer Lip (-5.36 g/side)")
    ax.plot(r_old, z_old, color="#dc2626", lw=1.6, ls="--")
    ax.plot(r_new, z_old, color="#059669", lw=2.0)

    ax.annotate("Band 1 (z=394): trim 1.49 mm\nSteel wall: 7.10 -> 5.58 mm", xy=(42.2, 394.2), xytext=(32.6, 396.3),
                arrowprops=dict(arrowstyle="->", color="#991b1b", lw=1.1), fontsize=8.0, color="#7f1d1d",
                bbox=dict(boxstyle="round,pad=0.2", fc="#fef2f2", ec="#dc2626", lw=0.7))
    ax.annotate("Band 0 (z=370): trim 1.32 mm\nSteel wall: 7.00 -> 5.60 mm", xy=(44.3, 370.2), xytext=(32.6, 376.5),
                arrowprops=dict(arrowstyle="->", color="#991b1b", lw=1.1), fontsize=8.0, color="#7f1d1d",
                bbox=dict(boxstyle="round,pad=0.2", fc="#fef2f2", ec="#dc2626", lw=0.7))

    ax.set_title("B. Radial Cross-Section Around Left HY Axis\n(No Shell Thinning, -10.72 g/pair Steel Saved)", fontweight="bold", fontsize=10.5)
    ax.set_xlabel("Radius from HY Axis (-60, +60) [mm]")
    ax.set_ylabel("World Z [mm]")
    ax.set_xlim(32, 49)
    ax.set_ylim(363, 400)
    ax.grid(True)
    ax.legend(loc="lower left", fontsize=7.2, framealpha=0.95)

    # Panel C: FEA Stress Proof in Trimmed Outer Skin
    ax = axes[2]
    ax.set_facecolor("white")
    cent = npz["el_cent"]
    r_el = np.hypot(cent[:, 0] + 60.0, cent[:, 1] - 60.0)
    th_el = np.degrees(np.arctan2(cent[:, 1] - 60.0, cent[:, 0] + 60.0))
    z_el = cent[:, 2]
    vms = np.max([npz[k] for k in npz.keys() if k.startswith("el_vm_")], axis=0)

    mask_upper = (z_el >= 364) & (z_el <= 398) & (th_el >= 30) & (th_el <= 150) & (r_el >= 32)
    sc = ax.scatter(r_el[mask_upper], z_el[mask_upper], c=vms[mask_upper], cmap="viridis", s=11, vmin=0, vmax=80, alpha=0.85)
    cb = fig.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("Max Static VM Stress across 12 Cases (MPa)", fontsize=8.5)
    ax.plot(r_new, z_old, color="#dc2626", lw=2.0, ls="-", label="Trim Cut Line (Removed Skin <= 21 MPa)")
    ax.fill_betweenx(z_old, r_new, r_old, color="#ef4444", alpha=0.18)

    ax.text(33.0, 383.5, "Removed Outer Skin Stress:\n• Band 0 (z=368-373): med 14.7 / max 19.6 MPa\n• Band 1 (z=391-396): med 14.7 / max 21.0 MPa\n• Steel Yield (45# QT): 350 MPa (<6% yield!)\n• PA12 Shell Wall: 2.12-2.27 mm UNTOUCHED",
            fontsize=8.0, color="#0f172a", bbox=dict(boxstyle="round,pad=0.35", fc="#f1f5f9", ec="#475569", lw=0.8))

    ax.set_title("C. FEA Stress Proof in Trimmed Steel Skin\n(Removed Lip Carries <6% Yield Stress)", fontweight="bold", fontsize=10.5)
    ax.set_xlabel("Radius from HY Axis [mm]")
    ax.set_ylabel("World Z [mm]")
    ax.set_xlim(32, 46)
    ax.set_ylim(363, 400)
    ax.grid(True)
    ax.legend(loc="lower left", fontsize=7.8, framealpha=0.92)

    fig.suptitle("Goose V0.2 Front Shell Clearance Closeout: Yoke Outer-Lip Relief Preserves 100% of body016_front", fontsize=12.5, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_png = OUT / "fig_a3_body016_yoke_relief_envelope.png"
    fig.savefig(out_png, dpi=180)
    ART_VIS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_png, ART_VIS / out_png.name)
    print("Saved:", out_png, "and copied to", ART_VIS / out_png.name)


if __name__ == "__main__":
    main()
