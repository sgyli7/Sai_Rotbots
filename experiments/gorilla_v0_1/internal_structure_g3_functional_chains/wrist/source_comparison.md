# G3 wrist family: source comparison and bounded decision

2026-10-03 UTC. Ignored exploration only; G2 bytes unchanged. Initial domain is **25 kg per hand**, with object local-X offset ±80 mm proposed for the new layout. 50 kg remains a sensitivity and is not inherited as a capability.

| Standard CSG-2UH | 25-100 | 25-120 | 32-100 | 32-120 |
|---|---:|---:|---:|---:|
| Tr at 2000 rpm input, N·m | 87 | 87 | 178 | 178 |
| Limit average Tav, N·m | 140 | 140 | 281 | 281 |
| Repeated peak, N·m | 204 | 217 | 433 | 459 |
| Momentary peak, N·m | 369 | 395 | 841 | 892 |
| OEM mass kg | 1.5 | 1.5 | 3.2 | 3.2 |
| OD / overall B / internal J, mm | 107 / 52 / 4.5 | same | 138 / 62 / 5.5 | same |
| True overall axial length, mm | 52 | same | 62 | same |
| Case installation C / input pilot B, from A mm | 46 /52 | same |57 /62|same|
| WG input bore U H7 / key W JS9, mm | 14 / 5 | same | 14 / 5 | same |
| Source input inertia kg·m² | .0000413 | same | .000169 | same |
| Bearing dp / inward R, mm | 62 / 11.5 | same | 80 / 13 | same |
| Bearing C / C0, N | 9600 / 15100 | same | 15000 / 25000 | same |
| Bearing Mc, N·m | 156 | same | 313 | same |

Source: [Harmonic Drive TI-26024 REV1, July 2026](https://www.harmonicdrive.net/_hd/content/documents1/CSG-CSF_GearUnits.pdf), printed pp11,13–15,32–37. Cached `.scratch/gorilla_internal_g1_oem_installation/csg_csf_gear_units.pdf`, SHA256 `517160deff3bc6272980fef807212d29ee2301ce819b4388df540fcd3ce7d97b`. Exact official [25 drawing](https://www.harmonicdrive.net/_hd/content/caddownloads/dxf/csg-2uh_gearheads/csg-25-xxx-2uh.pdf) was also downloaded and visually checked; source manifest records its hash. **Correction 01:25 UTC:** enlarged dimensioned image establishes J points inward from the overall B datum. The first A/B exploration incorrectly added J to overall length and put the case mounting face at input pilot end B. Those historical source bytes are preserved as rejected probes. Final selected installation corrects overall52/62 and caseC46/57; the input pilot still reachesB52/62. These are distinct mechanical planes. No OEM CAD or reverse-engineered internal material is claimed.

The standard left A face is FS/integrated-bearing inner-race output; right B large-PCD case is fixed CS; right central WG is input. 25 A: eight M8×12 at PCD42, register86; B: ten M5 plus ten Ø5.5 at PCD96, register67. 32 A: eight M10×15 at PCD55, register113; B: twelve M6 plus twelve Ø6.6 at PCD125, register90. Left output-side Ø15/20 references **are not the input bore**; both WG input bores are Ø14H7. Bolt engagement must not exceed threaded depth. Original G2 `20H7 input hub` was not a validated input fit.

Tr is a continuous torque/life rating at 2000 rpm input, not a static absolute ceiling. Tav is speed-weighted cubic duty-cycle torque and cannot be inferred from five static poses; repeated peak concerns routine acceleration/deceleration, and momentary peak concerns rare collisions/emergency stops. For 25 max/average oil rpm 7500/5600, grease5600/3500; for32 oil7000/4600, grease4800/3500. Lubrication, temperature, complete cycle and gear efficiency remain necessary unknowns. CSG L10 reference is 10000h at rated torque and input2000rpm; the bare gear's limit-average rating does not provide an assembled joint's continuous output.

## Existing selected585 gravity comparison

`family_comparison.json` binds actual selected585 hash `1ead0c8d55f6d965b91c615c6e61c1fd3a7f8d2577628a2c094c3922defb9e22` and 24 exact retained native mass/COM rows (7.6400/11.7771/16.8350 kg). It retains all five remote hand drives and all other support/brake/controller/cooling/line masses. Component substitution alone changes 32 gear to25 and yaw QTR105 to78 at existing positions; it does not shrink all joint parts.

For roll32 / pitch25-120+QTR105 / yaw25-120+QTR78, five local poses and object X±100mm: nominal25 pitch135.712 N·m; high-mass25 pitch142.673 N·m. High-mass50 pitch256.658 N·m. The 142.673/140 reference challenge is **not a static absolute failure**; a same-workpoint cycle and temperature are not closed. Keeping Tr87, Tav140 and repeated217 as separate conditions is mandatory. 50 sensitivity additionally gives roll Mc1.078×313 and yaw Mc.958×156: do not call 50 kg approved. The roll axis stays vertical in these local poses, so zero axial gravity torque does not cover upstream shoulder/arm orientations or dynamics.

High-mass25 bearing overturn reference ratios are roll.639, pitch.264, yaw.486; minimum reference static fs4.63/8.65/5.45. These are gravity diagnostics at source pressure-center planes, not combined task/bearing life or actual bolt/structural acceptance. Static reference `P0=Fr+2M/dp+.44Fa`, fs=C0/P0, comes from pp34–35. Source Eq16's printed dynamic equivalent load omits Fr despite the preceding denominator including it; no dynamic lifetime is certified by silently repairing the print.

## Motor matching at the same proposed points

Existing [Tecnotion Torque brochure v2.5](https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf), cached `.scratch/gorilla_internal_d_system/tecnotion_torque_brochure_2_5.pdf`, SHA256 `649c4d4d8a779346f7590b7b91eaf6e3856004a90397804e2d4cce3a03a13dd4`, pp14–17:

| Exact motor | OD / max L / rotor ID mm | mass stator+rotor kg | Tc N·m | 48Vdc speed at Tc rpm | Jr kg·m² | source Pc W |
|---|---|---|---:|---:|---:|---:|
| QTR-A-78-34-Y | 78 /34.8 /29 | .501+.126=.627 | 2.10 |1533|.000038|190|
| QTR-A-105-34-Z |105 /34.5 /56|.746+.218=.964|5.10|1061|.00022|295|

Both rotor active assembly heights are24.6mm on the dimensioned views. Tc/Pc require mounting surface20°C and coil100°C; 78 explicitly covers stall or continuous current, while105 footnote gives continuous-current condition and provides no separately established Ts. These figures are not sealed-limb motor ratings. Motor OD reduction is permitted only with these exact dimensions/masses and same motor-side workpoint; all brake, input bearing, encoder, inverter, seal, connector and mount functions retain nonzero inventory.

At output .1/.3/.5rad/s and ratio120 input speeds114.6/343.8/573.0rpm, below the isolated 48V-at-Tc reference points. That rectangular comparison does not replace the T/n curve/inverter/modulation/current limit. η=.55/.70/.85 are sensitivity assumptions, not measured gear efficiency. At the high25 comparison, η=.55 gives pitch QTR105 .424Tc and yaw QTR78 .157Tc. A QTR78 on pitch instead would approach/exceed its Tc at the worst offset; pitch keeps the real QTR105. The global bus is unresolved, and no old102.4V or arbitrarily chosen400V contract is inherited.

**Decision:** proceed with one actual conditional25 layout, roll32 / pitch25-120+QTR105 / yaw25-120+QTR78, move the pitch axis +15mm X as an explicit lever reduction and use initial object X±80mm. Preserve three serial freedoms and all five hand channels. No 50 kg claim, no inferred rated hand or complete installed thermal capacity. Next receipt must recompute new native positions/mass and disclose any stock/armor/tendon failure; current comparisons alone do not authorize manufacture or physical release.
