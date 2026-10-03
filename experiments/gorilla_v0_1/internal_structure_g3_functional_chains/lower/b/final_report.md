# Gorilla G3 B frozen failure receipt

G3 B is a rejected engineering and packaging candidate. No third geometry is generated. The locked source remains `chain_scene.json`, SHA `8fb41bd85c971d1456543c9660dd123780e3e342846c230ad2751fa5177b2fab`; its six new covers are independently stored in `armor_scene.json` SHA `6b58717476d2e4e2b6f9938eda1b4f6361c4cf868d2a0dcaa91c4273eb9539b5`; interface SHA `b0f57af4f78797798ad8bde892da039d82e8c96ea28e079ba433cf808ae3366e`. Root has independently rendered and rejected its full-machine aesthetics. These covers are not a new visual authority.

The actual scope is one left knee input interface → middle → fold → distal → ankle pitch → ankle roll → fixed arch/high heel → independently folding forefoot. Upper thigh/knee actuator, whole-robot serial system, oil circuit, real bearing fits, fasteners, stiffness and stable SI loops are missing or unqualified. Mirroring has no inherited load qualification.

## Finite geometry and motion

There are 50 declared module pieces (38 finite steel pieces, 10 catalogue bearing-reference envelopes, 2 remaining elastomer pads), plus 6 new finite covers. Five complete custom cylinder envelopes exist: two fold50/25×5mm, one ankle-pitch50/25×5, one roll50/25×5 and one unloaded forefold40/20×4. Each has a finite barrel, end eye, piston/rod eye, fixed and moving fork/pin support. No manufacturer's collapsed length was shortened. Forks and paths are still rejected for geometry/connection, not made qualified by their presence.

| Cylinder | Actual eye range, m | Stroke, m | Zero eye / minimum complete zero, m | Signed J range, m/rad |
|---|---:|---:|---:|---:|
| fold_inner and fold_outer, each | .376265–.459837 | .103572 | .366265 / .279572 | +.226439–+.249864 |
| ankle_pitch | .415271–.443408 | .048137 | .405271 / .224137 | −.162668–−.158812 |
| ankle_roll | .286565–.333449 | .066884 | .276565 / .242884 | −.135000–−.132778 |
| unloaded forefold | .314406–.342235 | .047829 | .304406 / .207829 | +.096863–+.115304 |

The 121-point screen is a sampled length/J calculation, not a continuous material sweep or pressure qualification. Four actual transformed-material poses are neutral, fold−20/pitch−10/roll−10 locked, fold−20/pitch−10/roll+10/fore−15 unloaded, and neutral with fore−15 unloaded. Barrels rotate by actual eye direction; rods slide; braces have two separate finite halves; lock keys really withdraw72mm along opposite Y directions. Per-part material volume and whole declared mass are invariant within floating-point tolerance. No pose cuts or repairs are used. Root Z shift is zero.

The native material gate passes49/50 module pieces, rejects `g3_arch_load_net`: one negative closed boundary has |V|≈1.37349e−13m³ below the1e−10 source threshold. No repair, normal flip, boundary deletion or normalized-source substitution is performed. New covers pass their resource predicates but fail intended arrangement/aesthetics. Kernel decompose counts include negative inner surfaces and are not material connectivity counts.

The G nesting gate reports middle/distal/ankle-carrier each one material root, thigh-interface two separate installation pieces with no qualified upstream attachment, and forefoot frame five actual material roots. The latter includes four brace-support roots whose actual material path to the main carrier is incomplete; assigning all to `forefoot` does not attach them. Ordinary separate pins and bearings need real interfaces, not union connectivity.

| Pose | Verified different-owner material pairs | Rejected-source conditional pairs | Reference envelope pairs | Verified new-cover material pairs |
|---|---:|---:|---:|---:|
| neutral | 9 | 11 | 4 | 38 |
| lower negative locked | 11 | 11 | 4 | 36 |
| lower unloaded forefold | 11 | 10 | 4 | 36 |
| neutral unloaded forefold | 9 | 11 | 4 | 39 |

Verified neutral examples: roll arch pin×ankle fixed carrier43.715cm³, thigh interface×middle42.321cm³, roll rod×ankle carrier23.511cm³, middle×distal21.588cm³, outer fold barrel×middle16.550cm³. The largest arch-related raw Boolean volumes remain conditional because their source fails the gate. Reference-bearing overlap is listed separately and cannot be called steel collision. The old raw field `original_armor_intersections` actually tested the six new B covers; it is not a111-original-armor or AA3 comparison.

The retained pad ground surfaces and129mm fore/heel ground gap are not joined by a whole-foot bottom skin. Hidden steel intrudes to Z=.014159m in the front pad, so the producer's .017m minimum-rubber statement is false locally. The remaining front pad has3 material roots; the heel pad has2. No elastomer bond/insert/edge-pressure qualification exists. Root/user allowed hidden pad reconstruction, but this is a new signed source, not C15 byte-preservation.

## Complete declared mass and inertia

Steel uses conditional S355J2H density7850kg/m³. The catalogue bearings are mass references, never marker-volume steel. Remaining pad density is900/1100/1400kg/m³. New four-mm covers use explicit950/1400/2200kg/m³ material sensitivities. No arbitrary scale factor or density reduction is used.

| Category | Low, kg | Nominal, kg | High, kg |
|---|---:|---:|---:|
| Net steel union, same rigid owner | 318.608498 | 318.608498 | 318.608498 |
| Remaining fore/heel elastomer | 9.175565 | 11.214579 | 14.273101 |
| 10 catalogue bearing references | 11.500000 | 11.500000 | 15.500000 |
| Declared module before covers | 339.284063 | 341.323078 | 348.381599 |
| Six new covers | 16.377627 | 24.135450 | 37.927135 |
| Declared module including covers | 355.661690 | 365.458527 | 386.308734 |

Root's319.191970kg steel is the correct sum of per-piece signed volumes; the same-owner union removes0.583472kg of overlaps. Two known valid same-owner middle pins intersect their frame by8.037662/7.966945cm³, and two arch pin intersections29.150126/29.172899cm³ are conditional on invalid arch source. The smaller union value is a mathematical ledger convention, not successful assembly or a justified manufacturing weight saving. If retaining separate pieces, the piece-sum subtotal including covers is356.245162/366.041999/386.892206kg. Neither ledger is physically accepted.

The nominal32212 reference is60/110/29.75mm and1.15kg. High1.55kg represents the wider33212 family; its width is not fitted to B. Reference inertia is a uniform annular envelope with catalogue mass, not actual OEM roller/cage distribution, and C0 of two bearings is not added into a joint rating.

`final_report.json` contains every union/pad/bearing/cover COM and full3×3 inertia,22 owner aggregates and all four actual pose aggregates. Nominal complete neutral COM is[−.031977785,.538102592,.386584135]m; its full inertia at COM in world axes is:

```text
[[44.350512986, -2.809175916,  6.700491931],
 [-2.809175916, 47.226258041,  6.466196380],
 [ 6.700491931,  6.466196380, 21.549571264]] kg m²
```

Oil, holding valves/brackets, hoses/fittings, seals, feedback/control hardware, axial keepers/bolts and upstream thigh/knee modules remain uncounted. These are explicit unknown additions; this is not whole-machine mass or a released SI inertia contract. Existing arch source rejection and material intersections make all computed moments conditional.

## Independent3t ground-pressure case

Ground reaction is upward29430N at[.25,.65,0]m, balanced by downward upstream support; this is separate external-pressure sensitivity, not3t carry payload or moving-load capability.1.5× and CoP_y±.1m are separate sensitivity cases, not promised operating domain.

Pitch at[−.080,.520,.310] has9711.9Nm ground moment and J=−.158811958: it needs **61.153455kN retraction**. Single50/25mm annulus yields30.925053kN at21MPa and44.178647kN at30MPa. Ideal required chamber pressure is41.526932MPa, with no friction/loss/safety factor. Adding actual known downstream partial-module gravity gives about59.846kN nominal pull, still fails30MPa. A holding valve cannot increase that force.

At current ground moment, a single50/25 needs |J|≥.3140m/rad at21MPa or≥.2198 at30MPa, versus current.1588. Two such cylinders at21MPa would provide only~1.1% ideal margin for the ground-only case and require a new actual paired installation, reaction path, flow and mass. B has no independent positive mechanical pitch-pressure hold. A larger-family/longer-arm or distinct static mechanical hold is an unbuilt macro choice; pressure-grade qualification remains unknown.

Fold pair each requires25.343915kN push under the same ground-only neutral case, not cap/pull interchange; this is below21MPa ideal41.233404kN per cap, but assembly/self-weight/duty/safety are not qualified. Roll needs19.620kN push for nominal CoP_y=.65; lateral pressure domain is coupled to wide hinge/braces. Forefold40/20 is **unloaded motion only**. If mistakenly asked to hold ground pressure directly,51.651204kN exceeds even its30MPa cap37.699112kN; the loaded path is mechanical braces/stops and the wide fore hinge.

Actual neutral B brace endpoints A[.020,y,.250]→B[.330,y,.105] and H[.080,.650,.115] give per-brace25.825602kN under equal compression. The main hinge then takes total[−46.786154,0,−7.546154]kN, so the large horizontal internal force has not disappeared. Two explicit roll/yaw allocations are supplied; neither is uniquely established by geometry. If braces take all roll, CoP_y±.1 produces a peak42.979060kN brace; main hinge seat radial force can reach49.752731kN. Each40mm pin has actual80mm fork-center span: neutral-center bending sensitivity82.205MPa and the peak1× case136.807MPa, before1.5 factor, fit and stress concentration. The60/28mm hollow hinge shaft has actual240mm bearing-center span; central-load bending sensitivity is only a conditional beam estimate, not solved shaft/contact/FEM.

Equivalent straight-end brace forces require finite overcenter stop reaction; the two-half linkage and keeper/contact compliance are still unknown. A source-positive material chain cannot replace fork, shaft, bearing, fastener or pressure checks. Unlock is only after unloading.

Per-cylinder121-sample J and cap/annulus flow branches are included. Positive fold q supplies cap; positive ankle-pitch/roll q supplies annulus. At |qdot|=.5, each fold cap uses13.338–14.718L/min, pitch annulus7.016–7.186, roll annulus5.866–5.964; unloaded fore cap3.652–4.347. No pump, thermal, flow simultaneity, regeneration, seal or duty qualification is claimed.

## Actual image review and architecture exit

All11 uncropped native images were actually viewed: neutral bare and new-cover FRONT/LEFT/REAR/TOP, plus three endpoint LEFT. They share1250px/m and frozen8fb41 source. Earlier1200×1300 images clipped the knee top and remain historical only. The new2000×2000 `_full.png` files and `native_full_view_manifest.json` are the complete native projections. Root's Blender views independently confirm the same candidate failure.

AA3 has sculpted blue shank faces, tight layered dark joint organization and a low tapered ivory toe against a distinct dark heel. B adds broad closed blue walls, a high broad white forefoot slab, exposed boxed-stock joins and bracket fragments. Its six shields are closed finite cavities: a source comment says rear opening, but no opening cutter exists. They cannot be reported as maintainable open covers. The new lower-end redesign was authorized, but neither aesthetics nor functional packaging is accepted.

Exit this A/B timebox without a third patch. First verify one complete **fixed dual-bearing housing → actual journal/shaft → short wide output box carrier → drive/stop** joint module, with finite access/keepers, actual bearing spacing and moment load share. Its fixed and moving material must pass neutral and endpoint separation, fit/contact and functional attachment checks before joining repeated modules into the Z chain. Use deliberate bulkhead/closed-shell transitions and finite mounts; do not add isolated rings or fill missing paths with thin bars.

Keep the fixed arch/high heel plus one foldable forefoot topology available; it removes unnecessary dual moving-heel windows while preserving separated fore/heel contact. A complete independent segment pressure path and unloaded-release lock remain necessary. Ankle pitch and roll cannot be deleted to make space or weight look better. They may be placed jointly with the actual load carrier within the user's authorized lower-end redesign, with updated FK, J, load cases and packaging.

Compare one proximal-drive arrangement for fold/ankle pitch against one integrated short wide joint drive, using an actual linkage/transmission and swept/torque/zero-length model. Moving only drawn cylinders or deleting pump/brake/bearing/holding/thermal hardware is not a mass saving. Any reused load shell must be regenerated and counted by real finite volume. Recompute whole-machine contact LP and exact gravity wrench with the new axes/mass before declaring a route adequate. The present failures do not prove AA3 fundamentally impossible.

## Replay and identity

From repository root, `.venv/bin/python .scratch/gorilla_internal_g3_foot_chain/b/final_review.py` replays the final read-only mass/FBD receipt against the hardcoded locked SHA; `render_native_full.py` replays only the native projections. Neither writes geometry. `freeze_manifest.json` binds final files, historical A/G1/G2/C15 and producer references; it does not grant physical/aesthetic acceptance.
