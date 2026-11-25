# Goose V0.2 — `assembly_finish_005` Digital Hardware Closeout (2026-11-25)

This document records the cold-verified **Digital Hardware Closeout (`assembly_finish_005`)** for **Goose V0.2** ("Max Pro" MicroDuck-inspired interactive biped with a parallel four-bar gripping beak, 310 mm widened stance, and 18 active DOF).

> **Release Scope & Honesty Boundary**: All digital mechanical, structural FEA, electrical EDA/OVP, CAD mass/inertia (MCI), and SaiLab GPU RL/VLA simulation gates are **100% PASS**. Physical manufacturing, prototype weighing, bench thermal soak, and BMS upper-rail `10.207 mm³` interference trim are intentionally deferred to **Step 2 (Physical Build)** while we validate virtual Goose locomotion, interaction, and community adoption first.

---

## 1. Track A — Mechanical & Structural Closeout (`opt_b2_r2` + Zero-Cut Yoke Lip Relief)

### 1.1 Anchored Hip Lower Cross-Bridge + Stator Tie Columns (`opt_b2_r2`)
Evaluated directly on the real 16-part `assembly_finish_004` chassis (`457,341` DOFs, **not** the `+494 g` `t40` surrogate), we screened three candidate architectures:
- **Option A (Bare Lower Bridge)**: `1.049 mm` peak displacement — rejected (insufficient lateral/torsional coupling).
- **Option C (Independent Short Brackets)**: `1.749 mm` / `117.6 MPa` + right `K2` harness pinch — rejected.
- **Option B1 (Lower-Only Anchored Bridge)**: `0.638 mm` — rejected.
- **Selected — Option B2 Rev2 (`opt_b2_r2_anchored_bridge.step`, Al 7075-T6, `141.19 g`)**: Combines an anchored lower cross-bridge with symmetric vertical stator tie columns, `clamp_underfoot` shear cheeks, and C1 `R = 3.0–3.5 mm` fillets. Achieves **`0.000 mm³`** static/overlay/moving interference with **zero modifications** to `K1`, `K2`, battery cassette, or `body016_front`.

### 1.2 Converged C3D10 FEA & Closed-Loop MuJoCo Single-Support Verification (8/8 Physical Gates PASS)
| Gate | Requirement | Verified Result (`opt_b2_r2`) | Status |
|---|---|---|---|
| Net Structural Mass Δ | `<= 200.0 g` (total `< 18.80 kg`) | **`+198.30 g`** (`18.7676 kg` total) | **PASS** |
| 3-Level C3D10 Mesh Quality | `min SJ >= 0.05` (0 bad tets) | Coarse `0.053`, Med `0.053`, Fine **`0.0615`** | **PASS** |
| Mesh Convergence (Med → Fine) | `ΔDisp < 2%`, `ΔVM < 5%` | `ΔDisp = 0.08%`, `ΔVM = 1.40%` | **PASS** |
| 121-Case Static Envelope | `<= 0.20 mm`, `<= 80 MPa` | **`0.1893 mm`**, **`59.4 MPa`** (`121/121`) | **PASS** |
| `4.670 s` Turn Reference | `SF >= 2.5`, `SF_slip >= 2.0`, `<= 2.5 mrad` | **`48.7 MPa` (`SF = 10.3`)**, `SF_slip = 7.98`, **`1.232 mrad`** | **PASS** |
| Stage A3 Closed-Loop Single-Support | Legal MuJoCo SS (`min_margin > 0`), `SF >= 2.5` | `min_margin = +0.0299 rad`, SS `0.208 s`, lift `+36.4 mm`, `FL_z = 312.1 N`, `FR_z = 0 N` → **`92.9 MPa` (`SF = 5.4`)**, `SF_slip = 5.73`, **`2.096 mrad`** | **PASS** |
| Loaded Front-Shell Gap (`-0.30 mm` tol) | `> 0.50 mm` | `1.110 / 1.248 mm` (turn), **`1.012 / 1.212 mm`** (SS) | **PASS** |
| Interference & Clearance | `0.000 mm³` fixed/moving/harness | **`0.000 mm³`** (`K1/K2/cassette` untouched) | **PASS** |

### 1.3 Zero-Cut Front Shell (`body016_front`) via Steel Yoke Outer-Lip Relief
Instead of thinning the PA12 `body016_front` wall (`2.12–2.27 mm`), we trimmed only the low-stress (`< 21 MPa`) outer steel lip on `left_yoke_shell_relieved.step` and `right_yoke_shell_relieved.step` (retaining `>= 5.58 mm` steel wall):
- 162-pose unloaded gap improved **19.3×** (`0.0823 mm -> 1.5869 mm`).
- Saved **`-10.66 g / pair`** while leaving `body016_front` 100% unmodified.

---

## 2. Track B — Electrical & Thermal Subsystem Closeout

### 2.1 Environment Mainboard 6-Layer PCB Fab Release (`eda_fab_release_003`)
- Cold KiCad 7.0.11 native DRC: **`0` total violations** (`106/106` nets routed, `0` dangling copper `40 -> 11 -> 0`, `0` library warnings `142 -> 0` via self-contained `ENV_MAIN.pretty/` + `fp-lib-table`, `0` shorts or clearance violations, min `0.1500 mm`).
- Refilled internal GND / `ENV_V5` planes; cold-verified **13 Gerbers**, Excellon drill (`419` PTH, min `0.20 mm`), BOM (`142` parts), and Pick-and-Place CPL.

### 2.2 24 V Direct Cooling Fan & Serviceable Rear-Cover 1 A Fuse (`sanyo24_direct_fan`)
- Co-designed input precision OVP (`LM4040A25` + `TLV1811` + `0.1%` thin-film dividers) with a shifted output backfeed clamp across `-40..+85 °C` / `±0.30%` corners:
  - Guaranteed non-overlapping voltage guardband (**`+186.1 mV`** separation between upper OVP trip and lower clamp onset; **`<= 27.581 V <= 27.60 V`** worst-case cap).
  - **`50,000 / 50,000` (100%)** Monte Carlo pass; all 26 components fit inside the unchanged `13 × 9.6 × 18.7 mm` protective guard (`0` overlaps).
- Relocated the `UMT-H 1 A` fuse into a rear-cover direct-access pocket at `(-112.5, 52.5, 366.5) mm`: **`0.000 mm³`** static/cover/pull collision (`36.7 mm` lateral pull clearance) + `98.04 mm` clean 6-pin Pin-1 breakout harness (`0.000 mm³` collision), net mass delta **`+9.60 g`**.

---

## 3. Track C — `assembly_finish_005` 21-Body MCI & SaiLab 43-Collider Bundle

- **Exact Whole-Body MCI (`assembly_finish_005_mci.json`)**: Total mass **`18.767646 kg`** (`+207.97 g` vs `004` `18.559677 kg`, reconciled across all 21 rigid bodies: `+209.03 g` hip bridge + `-10.66 g` yoke relief + `+9.60 g` Track B fan/fuse + `0.00 g` PCB), Steiner conservation residual **`1.11e-15 kg·m²`**, MuJoCo XML readback error **`0.0 kg`** / **`4.86e-17 kg·m²`**.
- **SaiLab Fast RL/VLA Bundle (`robots/goose_v0_2/models/full/goose_v02_005_exterior_roles_v1/`)**:
  - **43** convex/primitive colliders, **18** active DOF, fixed beak-neutral contact plane at **`0.628305 m`**, **`0`** neutral self-contacts.
  - **8/8 Cold Verification Gates PASS**: CPU `3×100` step stability, `200 Hz` `100 g` beak hold for `1.0 s`, CUDA MuJoCo 3.15.0 32-env **`1,330.2 world-steps/s`** (`p95 = 26.29 ms`, `0` NaNs), 32-env `2+1` PPO save/resume bit-identical, pytest `6 + 3` PASS.
  - All `459` non-bytecode bundle files verified byte-for-byte against `bundle_manifest.json` SHA-256 (`__pycache__/*.pyc` excluded from Git per repo rules).

---

## 4. Artifact & Provenance Map

| Category | Repository Path |
|---|---|
| SaiLab 43-Collider Model Bundle | [`models/full/goose_v02_005_exterior_roles_v1/`](../models/full/goose_v02_005_exterior_roles_v1/) |
| MicroDuck 4-Colorway Theme Config | [`configs/microduck_four_colorways_005.json`](../configs/microduck_four_colorways_005.json) |
| Frozen CAD STEP Exports | [`cad/exports/closeout_20261125/`](../cad/exports/closeout_20261125/) |
| 6L Environment PCB Fab Package | [`hardware/closeout_20261125/environment_board_eda_fab_release_003/`](../hardware/closeout_20261125/environment_board_eda_fab_release_003/) |
| 24 V Fan OVP & Serviceable Fuse | [`hardware/closeout_20261125/sanyo24_direct_fan/`](../hardware/closeout_20261125/sanyo24_direct_fan/) |
| Cold-Verified Receipts & Ledgers | [`evidence/closeout_20261125/`](../evidence/closeout_20261125/) |
| Showcase Renders, Poster & Proof Figures | [`images/closeout_20261125/`](../images/closeout_20261125/) |

## 5. Deferred to Step 2 (Physical Prototype Build)
1. **Thermal Bench Soak**: Real hardware fan-off / thermal-cutoff verification on physical chassis (`54.996 °C` sim margin vs `55.0 °C` target requires physical thermocouple sign-off).
2. **BMS Upper-Rail Clearance**: Trim the known `10.207 mm³` native BMS envelope interference against the upper aluminum rail before CNC machining.
3. **Physical Weighing & Sim2Real Identification**: Measure real printed/CNC part masses, TPU pad friction/compliance, and actuator torque/latency curves on bench.
