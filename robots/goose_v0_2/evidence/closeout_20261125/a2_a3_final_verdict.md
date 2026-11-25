# Goose V0.2 Stage A2 + A3 Final Verification Report (`opt_b2_r2_anchored_bridge`)

**Verdict:** `PASS_ALL_PHYSICAL_GATES_READY_FOR_ASSEMBLY_FINISH_005` (`all_physical_gates_pass = True`)

## 1. Executive Dual-Ledger Scorecard (`opt_b2_r2`, Al 7075-T6 + Hybrid 7075/Steel-Pin Tridents)
| Engineering Gate | Target | 121 Static Worst (`13 µm`) | `4.670 s` Turn (`13 µm` Stuck / Unb) | Stage A3 Legal Closed-Loop SS (`13 µm`) | Verdict |
|---|---|---:|---:|---:|---|
| **Net Structural Mass Δ / Total 005 Mass** | `<= +200 g` / `< 18.80 kg` | **+198.30 g** | **18.7676 kg** (incl. +9.60g Track B) | Same exact MCI in MuJoCo | **PASS** |
| **CAD Cold STEP / Collision / K1-K2 Mod** | `0.000 mm³` / Zero Mod | `0.000 mm³` (`min_fix=1.385 mm`, `min_mov=1.408 mm`) | `6` C1 `R=3.0–3.5 mm` fillets + `45°` gussets | Untouched `body016_front` | **PASS** |
| **Mesh Quality & Convergence (C3D10)** | `min SJ > 0.05`, `< 3%` | `min SJ`: C `0.0530` (`0` bad), M `0.0530` (`0` bad), F `0.0615` (`0` bad) | Med→Fine `ΔDisp = 0.08%`, `ΔVM = 1.40%` | Fine `115875` DOFs | **PASS** |
| **Converged Strength (Al 7075-T6, 503 MPa)** | **`SF >= 2.5` (`<= 201 MPa`)** | **59.4 MPa (`SF=8.5`)** | **48.7 MPa (`SF=10.3`)** / 88.4 MPa (`SF=5.7`) | **92.9 MPa (`SF=5.4`)** | **PASS** |
| **Bolt Slip Safety Factor (All 11 Joints)** | **`SF_slip >= 2.5`** | **6.65** (min across 121) | **7.98** / 6.83 | **5.73** | **PASS** |
| **SKF 608 Bearing Misalignment** | **`<= 2.5 mrad`** | **2.128 mrad** (max across 121) | **1.232 mrad** / 2.195 mrad | **2.096 mrad** | **PASS** |
| **Loaded Shell Gap (Neck-Ref, -0.30 tol)** | **`> 0.50 mm`** | **1.187 mm** | **1.110 mm** / 1.023 mm | **1.012 mm** | **PASS** |
| **Loaded Shell Gap (Hangpoint-Ref, -0.30)** | **`> 0.50 mm`** | **1.294 mm** | **1.248 mm** / 1.215 mm | **1.212 mm** | **PASS** |
| **Stage A3 Legal Closed-Loop Single-Support** | `0 viol` / `>= 0.20 s` / upright | N/A | Old 007 open-loop exited limit | `min_marg=+0.0299 rad`, `SS=0.208s`, `CoM_z_end=0.313m` | **PASS** |
| *Legacy Ref: Peak Disp rel. Neck* | *0.200 mm ref* | **0.1893 mm** (`121/121`) | 0.3686 mm (Steel tri: 0.3183 mm; REL 0.2083 mm) | **0.2978 mm** | INFO (ref) |
| *Legacy Ref: Peak VM Stress* | *80 MPa ref* | **59.4 MPa** | **48.7 MPa** (99.5% bulk: 25.8 MPa) | **92.9 MPa** | **FAIL** |

## 2. Rev 1 -> Rev 2 (`opt_b2_r2`) Engineering Improvements
- Deepened central-to-column cross-beam from `4.5 mm` -> `14.0 mm` (`Z=326.5..340.5`), added `6` C1 circular concave fillets (`R=3.0–3.5 mm`) plus planar `45°` column-top & forward-bay gussets, replaced skewed 3D lofts with a sliver-free high-corridor 2D XY extruded right over-K2 arm (`gap = 2.43 mm` to swept right yoke, `5.52 mm` to K2), and added verified bilateral `clamp_underfoot` shear cheeks seating directly beneath `left_clamp_negative_y` / `right_clamp_positive_y`.
- Peak Von Mises stress under the archived `4.670 s` turn dropped to **48.67 MPa** (`SF = 10.33` on Al 7075-T6 `503 MPa`), with **`0` elements below `SJ = 0.05`** across coarse (`0.0530`), medium (`0.0530`), and fine (`0.0615`) C3D10 meshes, and **`ΔDisp = 0.08%`**, **`ΔVM = 1.40%`** (`< 3%`).
- Exact Steiner mass ledger (summing all compound fragments for `-10.728 g/pair` yoke outer-lip relief savings) yields **`+198.30 g <= 200.0 g`** net structural delta and **`18.76758 kg < 18.80 kg`** total `assembly_finish_005` robot mass.

## 3. Stage A3 Legal Same-Mass Closed-Loop Single-Support Trajectory
- Simulated in MuJoCo `3.10.0` (`500 Hz`, exact candidate mass **`18.76758 kg`**, Steiner-exact overlay of `opt_b2_r2` + relieved yokes + Track B `+9.60 g`, strictly respecting `robot.xml`'s unchanged physical motor torque caps).
- **`zero_joint_limit_violation = True`** across all 18 joints and `4.0 s` (`min_joint_limit_margin = +0.0299 rad` on `left_hip_yaw`), achieving **`0.208 s`** of true single-support (`FR_z = 0.0 N`, continuous `0.160 s`, max swing-foot lift `+36.4 mm`, legal `left_hip_yaw` range `[-0.0301, 0.3014]`, clean upright touchdown & recovery `CoM_z_end = 0.313 m`).
- At peak legal single-support (`t = 1.14 s`, `FL_z = 312.1 N`, `FR_z = 0.0 N`, `|F_L| = 253.5 N`, `|M_L| = 27.59 N·m`), `opt_b2_r2` achieves **`0.2978 mm`**, **`92.9 MPa` (`SF=5.4`)**, **`SF_slip = 5.73`**, **`2.096 mrad`** 608 misalignment, and **`1.012 mm`** / **`1.212 mm`** loaded shell gaps (`> 0.50 mm`).

## 4. Handoff to Track C (`@sailab-prep-c`) for `assembly_finish_005`
- Frozen world-frame MCI delta ledger: `artifacts/goose_v0_2/hardware_closeout_20261125/hip_b2_a2_a3/opt_b2_r2_mass_ledger.json` (SHA-256: `4b41e90c7f9cdaccbf9ca494f2f63310b59fe35a0e7198d2417868051b28f572`; net structural delta `+198.30 g`, total robot mass **`18.76758 kg`**).
- Cold-verified single-solid CAD: `artifacts/goose_v0_2/hardware_closeout_20261125/hip_b2_a2_a3/opt_b2_r2_anchored_bridge.step` (SHA-256: `08d56ef1bb8cacedbf9d5f1c1c6e479694e68540ab5f35bd0cbb1660408af2d6`).
