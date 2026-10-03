# G1 remote hand-drive allocation — two rejected probes

Frozen exploration, 2026-10-03 UTC. Original C15 three fingers, thumb and armor moved **0 mm**. Two layouts actually contain 426 new native parts (213 per hand), four independent flexion channels and a fifth opposition channel. Neither is mechanically installed or qualified. After two failures this branch returns to macro allocation; no third layout is offered.

| Actual candidate | Added two-hand dry mass low/nominal/high kg | Neutral positive pairs | Original armor pairs | Existing roll/wrist envelope pairs |
|---|---:|---:|---:|---:|
| A | 27.7350 / 34.6762 / 47.0893 | 1335 | 132 | 512 |
| B, packages shifted -25 mm X, outward 18 mm Y, -45 mm Z | 27.6737 / 34.6081 / 47.0041 | 1329 | 158 | 477 |

This is **new inventory**, excluding original hand/armor and without removing old D hand drives. It is not total hand mass or a claimed replacement saving. Every motor, screw, brake, generic thrust support, nut/guide, encoder, controller, force sensor, finite load frame, cover, anchors, pulleys, paired sheath/tendon, connectors and service manifolds has geometry and nonzero mass scope. Generic parts remain custom envelopes. Hollow material uses Boolean voids; source motor cylinders are full outer installation envelopes, not exact hollow OEM geometry. Component rotor/stator ownership and SI inertia remain unqualified.

## Source and actual geometry

`features.json` derives cylinder-cap axes and contact-pad volume centroids from C15 vertices. C15 legacy joint fields identify display groups rather than validated physical axes. For example left finger 1 root is [0.0720414, 0.7428144, 1.0420592] m and pad centroid [0.1736995, 0.6969410, 0.9183683] m. Left palm uniform-volume centroid is [-0.0296228, 0.8062949, 1.0899426] m; this is **not mass COM**. Cap axes are geometric candidates; bearings/load paths and true contact normals require reconstruction.

Existing official [Tecnotion brochure 2.5](https://www.tecnotion.com/wp-content/uploads/2022/05/Torque_Brochure_EN_2-5.pdf), printed pp14–17, calibrated four QTR-A-78-34-Y channels (three fingers plus opposition) and one QTR-A-105-34-Z thumb flexion per hand. Small: OD78 mm, stator height34.8 mm, 0.627 kg, Tc2.10 Nm, 1533 rpm at Tc/48 Vdc. Thumb: OD105 mm, reference axial34.5 mm, 0.964 kg, Tc5.1 Nm, 1061 rpm at Tc/48 Vdc. Source mounting20°C/coil100°C conditions are **not supplied by this forearm**; specifications ±10%. Source rotor IDs29/56 mm have not become validated shaft interfaces. Bare-source Pc sum1055 W/hand is an upper reference, not simultaneous installed heat load. Source PDF remains existing ignored `.scratch/gorilla_internal_d_system/tecnotion_torque_brochure_2_5.pdf`, SHA649c4d4d8a779346f7590b7b91eaf6e3856004a90397804e2d4cce3a03a13dd4.

## Force, stroke and losses — hypotheses, not payload ratings

For opposing sides, 2μN≥mg; three fingers each receive N/3 and thumb N. At 50 kg and μ0.35, each-side N=700.475 N. Actual geometric lever norm |axis×(pad-root)| is a worst orientation lever; it is not a solved grasp. Shared-tendon minimum is max(Troot/rroot,Tdistal/rdistal), necessary only: actual differential, contact equilibrium and self-weight remain unknown.

At route efficiency0.5, screw efficiency0.5, lead2 mm and tendon speed25 mm/s (750 rpm):

| Left channel | Root/distal moment Nm | Screw thrust N | Motor Nm | Source Tc Nm |
|---|---:|---:|---:|---:|
| Finger1 | 37.316 /17.204 |3392.385|2.1597|2.10|
| Finger2 |40.851 /18.045|3713.720|2.3642|2.10|
| Finger3 |38.287 /17.439|3480.603|2.2158|2.10|
| Thumb flexion |87.314 /19.486|7276.181|4.6322|5.10|

Three finger points exceed source Tc; thumb exceeds the own 0.9Tc guard. This bounded sensitivity rejects the chosen working-point margin, not every possible grasp. The source Tc-speed rectangle is not a full thermal/voltage curve; peaks were not substituted. Copper loss proxy3I²R25 is 155–185 W per finger and184 W thumb; hot resistance, iron, controller and brake losses are unknown. Fifth opposition is independently present but its true axis/contact workload is not solved.

Own root/distal radii22/16 mm (thumb24/16) and 90° each require59.690/62.832 mm ideal travel. Candidate screw stroke70 mm has only10.31/7.17 mm left before preload, compliance and wrist compensation. Actual paired routes are about0.67–0.75 m. A nominal2.5 mm metal tendon under the worst screw tension gives full-area0.69–1.48 GPa; effective E20–100 GPa sensitivity gives roughly4.68–49.58 mm elongation. Real wire area, fatigue, terminations and sheath compression are unknown: neither this diameter nor claimed force is qualified.

`routing_owner_review.json` supersedes initial `routing_a/b.json` generic motion semantics. If drive and all anchors truly belong downstream of forearm roll, rigidly rotating the whole route gives ΔL≈0; this owner claim is not mechanically realized. Alternative upstream-driver splits give different length changes. Actual wrist-reference ±45° single-axis splits produce -76.33 to+74.23 mm length changes, already comparable to/exceeding70 mm stroke and additional to finger travel. Native polygonal sheath segments occupy real space but are not qualified moving flexible routes: cross-joint owner/anchors, bend radius, swept lumen, friction, elastic length and force feedback remain red.

## Actual rejection and next macro step

Scope is new neutral parts against selected original C15 forearm/palm/finger/thumb geometry and old complete roll/wrist package envelopes, not whole-machine or new-new/dynamic collision acceptance. No scoped mesh operation returned unknown. A thumb motor envelope intersects each old roll gear by60.96 cm³; B finger2 motor by116.01 cm³. Service guard intersects original blue forearm wrap by57.72/55.70 cm³ (left/right). Original visible mechanisms also intersect; any future replacement requires explicit functional/mass removal, not automatic deletion. These envelope hits establish unavailable installation space, not OEM internal-material collision values.

`native_neutral_projection_a.png` projects exact native facets and original outlines at the same900 pixels/m scale; no armor cut or cosmetic edit. The builder completed both geometry and checks, then optional matplotlib import failed; `postprocess_receipt.py` independently renders the frozen exact scene with Pillow and produces the owner-aware route receipt. A/B source hashes are unchanged.

Return to a shared macro allocation of forearm-roll/wrist packages and five remote channels, with real output/guide interfaces and compensated tendons. The original thick forearm is not an empty cavity. Do not shrink source motors, remove old supports or stretch the shell to conceal this failed probe. Preserve four independent flexion plus opposition exploration until actual contact/tool-task requirements justify a different differential.

Red closure conditions: actual contact/normal and finger dynamics, finite pulley differential and anchor path, screw/thrust-bearing/brake rating and fatigue, tendon/termination strength and compliance, joint-crossing flexible routing and length feedback, mounting heat and bus/drive curves, service/structural attachments, moving collision and SI body/inertia ownership. Custom supply can be yellow only after these physical scopes have credible bounds; procurement absence cannot turn unknown physical capability yellow. No hand payload, grasp success or Bevy task capability is released.

Reproduction: `.venv/bin/python .scratch/gorilla_internal_g1_hand_allocation/build_hand_allocation.py` produces A/B and may exit on unavailable optional matplotlib; `.venv/bin/python .scratch/gorilla_internal_g1_hand_allocation/postprocess_receipt.py` produces the exact native projection and final receipts. See `manifest.json` for source/output hashes. No Git or upstream edits.
