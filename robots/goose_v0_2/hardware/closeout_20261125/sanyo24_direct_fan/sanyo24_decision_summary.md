# Goose V0.2 24 V Direct Fan OVP/Clamp Coordination, Fuse Serviceability & BMS Hold Summary

**Status:** `SANYO24_TRACK_B_DIGITAL_DESIGN_FREEZE_COMPLETE_WITH_STEP2_BENCH_GATES`  
**Figure:** [fig_b2_sanyo24_voltage_window_and_fuse_access.png](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/fig_b2_sanyo24_voltage_window_and_fuse_access.png)  
**Machine-Readable Receipt:** [sanyo24_closeout_receipt.json](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/sanyo24_closeout_receipt.json)

---

## 1. Unified Input OVP + Output Backfeed Clamp + Current-Limit Coordination

### Problem Resolved (Astra's Circuit Interaction Catch)
In the baseline [electrical_receipt.json](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261122/internal_layout/sanyo24_direct_power_001/electrical_receipt.json), MAX17608's internal OVLO (`330 kΩ / 20 kΩ` against `1.45–1.55 V`) gave `25.247–27.261 V` (only `46.6 mV` above `25.20 V` 6S max, with `24.413 V` low-corner reset latching cooling off at full pack). Simply raising internal OVLO to `26.6 V` overlaps the output active clamp (`25.828–26.874 V`), causing battery current to dump through the `2 × 130 Ω` (`65 Ω`) clamp (`0.409 A > 0.318–0.345 A` `ILIM`) and latch off MAX17608 (`36–44 ms` `CLMODE`).

### Redesigned Circuit & BOM
- **Dedicated Input-Side OVP Stage** (decoupled from `OUT` backfeed, drives `MAX17608` `OVLO` pin with `100 kΩ` pull-down, leaving `EN` solely for `VOS618A-8T` command and preserving `CLMODE` latch):
  - **Supply Clamp:** `470 Ω (0603, 1%)` + `33 V` Zener (`MM3Z33VB` / `BZT52C33`) + `100 nF / 50 V` cap from `IN` (`0.0266 A` / `0.879 W` Zener pulse during `45.4 V` `SMAJ28A` surge; well within `TLV1811` `40 V` op / `42 V` abs max).
  - **Reference & Comparator:** Dedicated input-side `LM4040A25IDBZR` (`2.500 V ±0.1%` @ `25°C`, `≤100 ppm/°C` -> `2.480–2.520 V` across `-40..+85°C` incl. line/load), fed via `100 kΩ (1%)` (`155 µA` at `18.0 V >> 75 µA` min) + `TLV1811DCKR` (`V_OS = ±4 mV` max, `I_bias = ±1.5 nA` max).
  - **Precision Divider:** `R_t = 75.0 kΩ` (`0.1%, 25 ppm/°C`), `R_b = 8.06 kΩ` (`0.1%, 25 ppm/°C`), `R_fb = 12.0 MΩ` (`1%, 100 ppm/°C`, `152–166 mV` same-unit hysteresis).
- **Upgraded Output Active Clamp Stage** (powered from `OUT`):
  - Keeps existing `LM4040A25IDBZR`, `TLV1811DCKR`, `Si2308BDS`, and `2 × 130 Ω` 2512 HP pulse resistors (`65 Ω` total; `0.399 A` min sink `> 0.25 A` regen / `> 0.345 A` `ILIM`; `5.919 W` max each at `27.6 V` / `5.911 W` at `27.581 V`).
  - **Precision Divider:** `R_t = 84.5 kΩ` (`0.1%, 25 ppm/°C`), `R_b = 8.66 kΩ` (`0.1%, 25 ppm/°C`), `R_fb = 15.0 MΩ` (`1%, 100 ppm/°C`, `143–157 mV` same-unit hysteresis).

### Worst-Case Corners & 50,000-Trial Monte Carlo Verification
Verified by [goose004_sanyo24_ovp_clamp_coord_20261125.py](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/scripts/diagnostics/goose004_sanyo24_ovp_clamp_coord_20261125.py) and logged in [ovp_clamp_coordination.json](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/ovp_clamp_coordination.json):

| Band / Boundary | Conservative `±0.30%` R, `-40..+85°C` Ref | Nominal `±0.25%` R, `-40..+85°C` Ref | `0..+70°C` `±0.2125%` R |
| --- | ---: | ---: | ---: |
| `V_OVP_reset` (V) | `25.2331 – 26.0087` | `25.2558 – 25.9853` | `25.3238 – 25.9163` |
| `V_OVP_trip` (V) | `25.3923 – 26.1680` | `25.4152 – 26.1443` | `25.4838 – 26.0749` |
| `V_clamp_off` (V) | `26.3541 – 27.1649` | `26.3779 – 27.1403` | `26.4491 – 27.0682` |
| `V_clamp_on` (V) | `26.5040 – 27.3148` | `26.5281 – 27.2901` | `26.5997 – 27.2175` |
| `V_clamp_peak_max` (`10 µs` / `3 µs`) (V) | `27.5807` / `27.5223` | `27.5559` / `27.4976` | `27.4833` / `27.4250` |
| Margin `V_OVP_rst_min - 25.20 V` | **`+33.1 mV`** | **`+55.8 mV`** | **`+123.8 mV`** |
| Margin `V_clamp_off_min - V_OVP_trip_max` | **`+186.1 mV`** | **`+233.6 mV`** | **`+374.2 mV`** |
| Margin `V_clamp_on_min - V_OVP_trip_max` | **`+336.1 mV`** | **`+383.7 mV`** | **`+524.8 mV`** |
| Margin `27.60 V - V_clamp_peak_max` (`10 µs` / `3 µs`) | **`+19.3 mV`** / **`+77.7 mV`** | **`+44.1 mV`** / **`+102.4 mV`** | **`+116.7 mV`** / **`+175.0 mV`** |

- **50,000-Trial Monte Carlo (`-20..+85°C`, seed `20261125`):** **`50,000 / 50,000` pass (`100.0000%`)**; minimum observed MC gaps are `+200.3 mV` above `25.20 V`, `+583.1 mV` (`V_clamp_off - V_OVP_trip`), `+731.4 mV` (`V_clamp_on - V_OVP_trip`), and `+261.3 mV` below `27.60 V`.
- **Unchanged UVP & Low-Voltage Floor:** `191 kΩ / 20 kΩ` UVLO = `15.223–16.431 V`; at `18.0 V` loaded corner (`0.25 A`, `1.4945 Ω` hot R), fan terminal steady voltage = **`17.6209 V`** (`+0.1209 V` above `17.5 V` floor); `C_OUT <= 66.4 µF` charges in `26.98 ms < 36.0 ms` blanking.
- **Updated Mini-Board 3D Fit:** All **26 components** (16 baseline + 10 added input-OVP parts, exported to [updated_direct_power_component_placement.step](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/updated_direct_power_component_placement.step)) fit strictly inside the unchanged **`13.0 × 9.6 × 18.7 mm`** guard (`X[-119, -106], Y[48, 57.6], Z[335.65, 354.35]`) with **`0` internal overlaps** (`27` valid solids).

---

## 2. Native 3D CAD Serviceable `UMT-H 1 A` Fuse Architecture (`assembly_finish_004`)

Evaluated in native OCCT/`build123d` via [goose004_sanyo24_fuse_access_20261125.py](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/scripts/cad/goose004_sanyo24_fuse_access_20261125.py) ([fuse_access_cad_receipt.json](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/fuse_access_cad_receipt.json)) across all `2,529` parts of `assembly_finish_004`:

| Candidate Architecture | Static & `+0.5 mm` Probe | Cover Departure | `+Y` Tool / Gripper Extraction | Verdict |
| --- | --- | --- | --- | --- |
| Legacy site `(-124, 38.5, 412.5) mm` | Clear (`0.5 mm` probe) | N/A | **BLOCKED**: `12P` (`2125.3 mm³`), `left_thermal_high_rail` (`756.0 mm³`), `+Z G10` (`210.9 mm³`), `XT60` (`25.5 mm³`) + AWG20 stub `4.298/3.822 mm < 7.65 mm` | **Rejected** |
| Option (b) `B1_upper_portal_corridor` (`Z[377.5, 395.5]`) | `0.000 mm³` | Clear | **BLOCKED** along `+Y`: `samtec_fixed_peek_receiving_frame` (`22.77 mm³`), `samtec_keyed_6061_guide_rail` (`42.00 mm³`) | **Rejected** |
| Option (b) `B2_lower_portal`, `B3_6p_minusY`, `B4_rear_bay` | **BLOCKED** (`1299.6`, `685.2`, `931.0 mm³`) | — | Blocked statically (`WT901`, `Radxa/gate`, `TinyBMS`) | **Rejected** |
| **Option (a) Rear-Cover Direct Pocket** (`X[-116, -109], Y[49, 56], Z[357.5, 375.5]`) + **6P Pin-1 Breakout** | **`0.000 mm³`** (`882.0 mm³` inside `COVER_DOMAIN`) | **`True`** (`0` hits across all 15 poses) | **`0.000 mm³`** (`+Y -> 108 mm`, `36.7 mm` min lateral clearance) | **Selected & Verified** |

- **Removable 6P Pin-1 Breakout Harness:** Exits the `+X` load side of `Flogic_all_loads_service_MicroFit_6p` Pin 1 (`(-126.2, 25.0, 423.5) mm`) via a removable Molex Micro-Fit 3.0 Pin-1 breakout tap (zero cutting of the clamped AWG20 source stub), routes `87.21 mm` (`OD = 1.4 mm` AWG22 PTFE) under `left_thermal_high_rail` (`Z = 400.2 mm`) and up `Y = 48.8 mm` into the pocket top, then `10.83 mm` (`98.04 mm` total) into `VBAT_FUSED` (`(-117.9, 53.41, 349.18)`). Verified **`0.000 mm³` collision** (`>= 0.518 mm` clearance to `tinybms_high_power_body`, `>= 0.600 mm` to `left_thermal_high_rail`, `>= 1.032 mm` to `bminus_route_00`) and **`0` hits** across all 15 rear-cover departure poses ([serviceable_fuse_pocket_guard.step](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/serviceable_fuse_pocket_guard.step), [serviceable_fuse_breakout_harness.step](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261125/sanyo24_fan_b1/serviceable_fuse_breakout_harness.step)).

---

## 3. Loss-of-Fan Thermal Lockout, BMS Hold Ledger & `assembly_finish_005` Mass Delta

- **Steady-State Heat & Adiabatic Lockout:** Input-OVP circuitry adds only `14.6 mW`, bringing total auxiliary loss to `0.3121 W` and `full_mix_upper_W` to **`5.8121 W`** (`0.2049 W` below `6.017 W` limit). Upon any fan loss (`Sservice` open, `1 A` fuse open, `UVOV`/`FLAG` latch, `V_fan < 17.5 V`, `FG=0`, or `FLOW` drop), `C_OUT` (`66.4 µF`) sustains `5.50 W` for only `1.98 ms`; adiabatic FE for one residual `580 J` pulse gives **`54.9963°C`** (baseline aux) / **`54.9999°C`** (updated aux) vs `59.797°C` if a second `580 J` pulse occurs. **Closed-loop rule:** immediate drive inhibit (`no-next-brake` lockout) on any fan fault; **Step-2 bench thermal verification required** given the sub-`0.01°C` digital margin to `55°C`.
- **BMS Physical-Sample Hold ([manufacturer_envelope_assessment.json](file:///home/ethan/.codex/worktrees/goose-delivery-navigation/Sai_Rotbots/artifacts/goose_v0_2/hardware_closeout_20261122/power_harness/charge_architecture/shared_corridor_003/bms_service_001/manufacturer_envelope_assessment.json)):** `TinyBMS v2.1 high power with cooling plate` retains **`10.207125 mm³`** upper-rail (`brake_compact_upper_rail`) and **`6.170008 mm³`** right-rail (`brake_compact_right_rail`) digital overlap at `+Y = 0.0 mm` (`9.020250 mm³` upper-rail overlap in two-solid `nominal_12p4` bound). Logged as an **open Step-2 physical-sample inspection hold** with zero fabricated clearance.
- **Digital Mass Delta for `assembly_finish_005` MCI:** **`+9.60 g`** estimated electrical protection assembly (`4.20 g` 26-part mini-board + `2.80 g` `UMT-H 1 A` & pocket carrier + `2.60 g` `98.04 mm` breakout harness & Micro-Fit tap; excludes San Ace `9WPA0424H30011` fan body).
