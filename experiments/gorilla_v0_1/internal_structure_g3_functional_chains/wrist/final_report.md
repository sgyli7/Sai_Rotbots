# G3 wrist family and actual three-axis candidate

**Rejected for assembly; retained as a source-bound conditional25kg engineering probe.** Final selected native scene SHA256 `5d6e224b552ce2293e734e25eeda251a4423ba6c2696e075867e82220eda7c80`;640 parts/640 mass rows. Original armor change0mm. G2 and the two macro A/B sources remain unchanged.

CSG32-100+QTR105 forearm roll, CSG25-120+QTR105 wrist pitch, CSG25-120+QTR78 wrist yaw retain all three serial freedoms and all five remote hand drives. Bare three-gear mass6.2kg, three wrist-motor mass2.555kg, complete **new** inventory37.192/43.599/55.788kg. Every actual part has a mass row; exact retained24 native rows add7.640/11.777/16.835kg but still do not include all original palm/finger mechanism materials. OEM gear/motor internal mass partition and full inertia remain proxies. Hypothetical same-material union is only a diagnostic, never deletion credit.

The 53 exact older replacement IDs correspond to45.033/52.159/66.415kg; their functional substitution/removal is conditional and has not been integrated or accepted. Five hand channels keep real180mm carriage/guide/screw geometry and complete motor, brake, encoder, controller, force-feedback and nonzero support functions. Carriage-to-tendon termination, passive differential/contact mechanism and true flexible route are unfinished.

| Final high-mass gravity envelope | pitch torque N·m | yaw torque N·m | pitch /yaw input Tc ratio at η.55 | roll/pitch/yaw Mc reference ratios |
|---|---:|---:|---|---|
|25kg, object localX±80mm, five local poses|103.576|50.435|.308 /.364|.523 /.290 /.438|
|50kg sensitivity, same probes|189.469|95.863|.563 /.692|.878 /.532 /.846|

Pitch25 Tav140 comparison is .740 at25kg and1.353 at50kg. Tr87 at2000rpm input, Tav140 duty-cycle limit, repeated217 and momentary395 are separate source conditions. These gravity values do not establish a real duty cycle, rated continuous joint or payload. Roll remains vertical upstream in these probes, hence zero axial gravity torque does not cover shoulder configurations or dynamics. At .1/.3/.5rad/s ratio120 needs114.6/343.8/573.0rpm; source48V-at-Tc reference points105=1061/78=1533rpm do not prove a complete installed T/n curve. η.55/.70/.85 are assumptions; source mount20°C/coil100°C, source Ts/current, inverter/globalbus/regeneration, brake and heat remain red-line unknowns.

The final yaw axis `[1,1,0]/√2` at `[.005,.805,1.270]`, pitchY at `[-.138,.801,1.232]` and rollZ at `[-.235,.812,1.706]` give serial-parent-FK angular rank3 at27 sampled combinations of±45°/0. Neutral condition number2.414; maximum sampled3.732. Pitch±90° is singular. A's inheritedZ/Y/Z neutral chain had rank2; neither three joint labels nor geometric animation proved three orientation freedoms. These angular samples are not a collision-free workspace.

The final installation distinguishes three OEM domains: **overallB52/62mm**, **case fixed faceC46/57mm**, and **input WG Ø14H7 / key-slot radialV16.3+0.1mm / widthW5JS9**. J4.5/5.5 is inward, not an extra axial projection. A/B preserve the earlier mistaken B+J profiles; selected corrects native profile, case mounts, input cradles and reaction endpoints. OutputL.5/1mm recessed face remains a conditional mate-plane hypothesis; nominal macroA pressure-center evidence is separately perturbed by L, giving≤.323N·m overturn change in these samples. This does not establish the actual output interface. WG six-mm engagement, rotorID holder/bond-film and input bearing/brake ratings are custom physical unknowns, not OEM permission.

The five material failures that guide the next macro step are:

1. Forearm roll gear intersects retained proximal frame52.731cm³, old elbow output adapter21.898cm³ and elbow carrier27.670cm³. Those functions remain counted; they cannot be removed merely to clear the new kit.
2. Original blue forearm armor intersects roll/pitch/yaw gears52.462/28.474/32.485cm³ and yaw motor13.925cm³. Zero shell change has not fit the complete modules; new axis/macro-carrier placement is required before proposing a measured minimal shell allowance.
3. Thumb/finger-three remote motors intersect original blue armor25.160/24.366cm³. The five full drivers and180mm real sweeps cannot be treated as a freely available empty forearm.
4.39 original C15 palm/finger mechanical references add435–487 route/pulley intersections over five poses; thumb root pulley→real root pin21.523cm³. These are not automatically normal contact. The moving-anchor polyline grows up to77.488mm; it is not a verified invariant tendon/Bowden length or a completed compensator.
5. Neutral selected input shaft/key/holder versus their own OEM stocks and controllers versus their supports no longer have positive core penetrations in this coarse probe; nevertheless yaw aluminium input cradle→steel reaction bridge .0795cm³ remains an actual different-material overlap. Output adapter/bridge lap joints, bearing restraint, bolts, rotor attachment, clutch/brake holding and reaction strength are unqualified. No “joined” label closes them.

Native input close-up `native_input_path_selected.png` shows actual finite shafts, keys, holders, paired input bearings, seats, brake and encoder against OEM wire envelopes; `native_wrist_selected.png` shows all selected native parts against original armor. Wire rendering is diagnostic only and changes no collision inventory. Local five-pose new-new+exact E2a context screens have2592/2591/2684/2535/2438 positive pairs, zero solver errors; counts include all unclassified contacts and conservative OEM fill. They are not full-machine screens or acceptance. Separate C15 route screens and all vectors are in JSON.

Root's independent complete `native_signed_material.validate_scene` resource check on final5d6e accepts639/640 resources and rejects `g3_forearm_roll_gear`: two closed boundaries a0/b1 touch at gap2.22e-16m, `touching_or_unresolved_disjoint_boundary_gap`. Our `layout_material_selected.invalid_ids=[]` only means the earlier Manifold kernel/material routine reported no status errors; it is not the stronger resource result. The gear coarse OEM proxy's detailed boundary representation remains rejected. Frozen geometry is preserved, with no third patch or claim that all640 native resources passed.

Primary source facts, versions, pages and cache hashes are in `source_facts.json` and `source_comparison.md`. No additional product families, purchases, industrial CAD, canonical models, contracts, Git or GPU were changed. Reproduce the **final** selected derivative with:

```bash
.venv/bin/python .scratch/gorilla_internal_g3_wrist_family/build_selected_installation.py
.venv/bin/python .scratch/gorilla_internal_g3_wrist_family/screen_wrist_layout.py --layout selected
.venv/bin/python .scratch/gorilla_internal_g3_wrist_family/build_receipt.py
.venv/bin/python .scratch/gorilla_internal_g3_wrist_family/render_input_path.py
```

Historical A/B producers and pre-datum source/facts are preserved separately; replay requires their recorded pre-datum dependency mapping. Current corrected family facts must not be used to claim byte-identical replay of the earlier mistaken profiles. No geometry or physical gate is passed by this receipt.
