# Gorilla G10 shoulder assembly — rejected, frozen two-macro experiment

B is a newly generated 103-part bilateral shoulder/torso candidate, not a selected layout or a validated robot joint. No old sources, AA3 visible/hidden armor, canonical files, Git, GPU or FEM were changed. A and B are the only macro architectures. B uses the same X=-0.130 m / Z=2.290 m Y-axis lines; each entire stack is retracted inward by 80 mm. The historical Y=±0.560 m point still lies on those axis lines; it does not freeze an axial package datum.

Actual sources are `a/scene.json.gz` and `b/scene.json.gz`, with editable analytic `assembly.brep`, raw original `assembly.step`, and explicitly corrected `assembly_si.step`. Original raw Gmsh STEP wrote SI coordinate values with millimetre declarations; `cad_export_units_receipt.json` refuses those unit labels and records a separate declaration-only metre STEP. Coordinate/entity/topology payloads were not edited. BREP is unitless with an explicit metre contract. OCP BRepCheck confirms the compounds are valid CAD, which does not prove one connected material or fit.

## Complete component scope and source corrections

Both sides retain one complete CSG65 reference at 115 mm overall, 108.5 mm caseface depth; J=8.5 mm is inward, not appended. B uses actual drawing profile Ø232 front / Ø260 fixed flange / Ø170 pilot, not a full-length Ø260 cylinder. A uses a conservative full-front bounding profile. Catalogue mass 20.9 kg includes its integral output support once. The unknown OEM input/output material split, bearing internal geometry and complete inertia remain unknown.

Each QTL210 kit retains 66 mm installation length, complete 5.8 kg stator+rotor mass and an explicit 15 mm terminal protrusion. Rotor ID/OD/height 140/148/41 mm and rotor polar inertia 0.009 kg m² are known, but rotor/stator axial alignment within the complete kit is an installation assumption. Independent two SKF32212 reference bearings per side retain d60/D110/T29.75 and 1.15 kg each; their preload/pressure centers/fit are unqualified and capacities are not added to the CSG bearing rating.

Own shaft, WG key, rotor sleeve/spider, fixed cooling case, brake rotor/friction/pressure/yoke/spring/coil, encoder target/readhead, controller, cable/water stock, bolt envelopes, journals/keepers, arm carrier and main reaction material all exist as explicit finite or reference parts. Unknown spring packs, selected input bearings, controller and connectors keep mass ranges and conservative finite envelopes, not invented catalogue certification. Brake release force/heat/holding torque, driver regen and feedback remain unqualified. Original four missing other hydraulic cylinders remain context unknowns, not removed budget.

## Identity gate and material gate are separate

A original CAD inventory is invalid: eight input-key tools were consumed before recording a surviving final part and their OCC tags were reused. Root independent audit reproduces >0.25% mismatches and aliases. Original A scene, CAD inventory and producer are preserved; `build_shoulder_a_source.py` is byte-identical to the producer hash in A. `a_cad_identity_rejection.json` binds the refusal. A CAD mass/COM/I must not be inherited, even where some rows happen to agree.

B copies every final OCC part before any later consuming Boolean, exports only those unique surviving tags, and records analytic per-part volume/COM/full inertia. Root independently obtains zero rows beyond 0.25% native chord-volume error and no shared OCC tags. This narrowly approves B CAD inventory identity, not its assembly.

B strong native gate still rejects 17 parts:

- Sixteen output bolt envelopes have a producer-created 1 mm gap between head and shank after moving the head to the mating face. They are real two-body pieces in this source and are not repaired for the gate.
- Main torso/shoulder reaction has three actual positive material roots. Its kernel reports 20 signed boundary components, of which 17 are legitimate closed negative cavities. The two forward bearing-housing annuli R118–126 mm do not overlap the rear R132–140 mm annulus at the 24 mm step. The transition end plate was omitted; same-owner naming does not connect them.

The fixed motor cases and rotor holders have actual single connected material in B, unlike A. Two different-owner material intersections nevertheless remain in each checked output pose 0/+30/-30°: each rotor holder against torso material, 21.112233 cm³ per side. Only output carrier/bolts/keepers were transformed rigidly. Actual fast-input rotation, internal gear kinematics and released brake mode are unresolved; these three poses are not a complete driven shoulder motion test.

Same-owner pairs were also separately inspected: B has 18 positive finite-material pairs, including case bolt-head/cooling-case interference (~0.578456 cm³ each) and lining/case contact. They are not accepted merely because both are labelled torso. Expected friction or mounting contact needs an actual seating/fastener model.

## Actual armor/system checks and visual inspection

`b/check_report.json` records 49 mixed original-armor probes and 72 old-nine-group probes. Original reference hull/profile intersections are distinguished from own finite material; they are not inferred OEM net metal. Largest original-armor reference challenge is the CSG profile against rear blue shoulder guard (~172.21 cm³ right /167.77 cm³ left). Own main reaction intersects each ivory shoulder cap ~102.39 cm³; output carrier ~65.41 cm³ left. Current-position complete energy groups also intersect cases/connectors: upper energy pack vs each cooling case ~151.30 cm³, lower pack vs service stock ~170.23 cm³. This is a rejected joint+core+current-module co-layout, not evidence that AA3 itself is physically impossible.

Actually viewed B bare and original-armor four-view images, and all three literal triangle-section images (XZ at Y=.310/.480, YZ at X=-.130). Cameras have the same 560 px/m bare/armor scale, source geometry unchanged; shoulder-scope crops and hidden old context are recorded. Front/rear armor occludes much of the internal assembly; that image cannot prove fit. The Y=.310 section visibly shows energy/module space and a rotor/material overlap; Y=.480 shows the shoulder armor/gear profile overlap. All original armor-role geometry is shown in the context image, with both source hashes bound. No AI redraw or hidden component deletion was used.

## Mass and inertia scope

B own native material is unioned once per owner and density only as a diagnostic inventory (not as source repair or a bolted-joint proof): **160.992158 kg** under the stated 7850 kg/m³ steel, 2710 kg/m³ aluminium and effective friction/coil material assumptions. B analytic CAD per-piece sum is **161.114735 kg**; it differs from diagnostic net material due to chord discretization and overlapping same-owner component material. `b/inventory_scope.json` provides own net COM and complete world full-I matrix and each owner/density contribution. These are not whole-joint OEM inertias.

Complete catalogue/reference mass range is **61.356 /63.296 /66.660 kg**, including gear/motor/independent bearings once. Conditional accounting total is **222.348 /224.288 /227.652 kg** for bilateral new assembly **including the rebuilt main core**. It is not two isolated shoulder masses and not the whole robot. Actual remaining hose/fluid, fittings, wire supports, service and fastening details remain unknown. Global COM/full inertia remain unknown because OEM internal mass partition is unavailable; gross uniform gear/motor profile inertia must not substitute for actual inertia. Source material-density/thermal/capacity qualification is false.

## Integration and exit

`integration_contract.json` records actual fixed/output/fast-input owners, candidate mating planes, pitch axes, precise old shoulder package IDs, and the two actual F1 torso pieces (`f1_torso_load_shell_piece_0/1`) that a future accepted new core would replace. G9 probe `g9_torso_core_b` is an alternative baseline identity, not an extra copy to retain. Original 77.937 kg `e2_upper_net_torso` bridge remains a challenge; its shoulder-support scope has not been replaced by assumption.

WG/input/independent-bearing fit gaps are explicit hypotheses; no certified tolerance, bearing distribution, journal torque capacity or bolt load transfer is claimed. Manual inward 240 mm maintenance withdrawal is a keepout candidate only; actual swept removal and drainage/disconnection sequence were not performed.

The next complete macro needs the known correct OEM fixed-face and output-face datums **together with** a finite shoulder reaction transition and an actual core motor window, and must jointly repartition all nine complete functions. Moving a full stack inward alone trades armor exposure for core/energy conflict. Do not perpetuate the old Z=2.360 /123.5 mm wrong-axis package, or solve these conflicts by deleting brakes/cooling/drivers, deleting the upper bridge without replacing its function, or by assuming the old fixed battery placement is the only admissible layout. Both current candidates are frozen rejected. No third geometry was generated.
