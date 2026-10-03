# Gorilla internal B separated-tray final read-only review

The previous 7 mm forefoot and 11 mm heel air gaps are now closed in nominal material geometry. The robot still fails material fit: new steel trays intersect retained low rails and heel covers. No whole-foot or physical acceptance is granted. This is the final independent review of the exact snapshot below; neither the old pre-tray report nor a future corrected model may substitute for it.

Input SHA256:

- Scene: `7a6186594f2a47067fe9c38e4cc52833b1c930c93568e5b215a520d195e7621f`
- Spec: `8465d082022caf7195746c1a66f013a957ecc7c5ad59c87bf52209f9db375963`
- Statics: `9f891b915b6ea0731491e331400ac9c4c66d0bacfc3f7f5be98cf8d0fbdf6571`
- Frozen foot input: `064b2e178343a49ed80e64351c054e5e319c5fa03919824759b649bb816351bd`
- Budget assumptions: `646c76f6fada136768ed3ec89fa2c09bd06db04b594e109a5ec56ca608edc5f0`
- Geometry spec: `019bb6feee1d89432b6926bf2804c51f07dd74e87009a04169ce3bb16d7e279e`

Exact input bytes are retained as `input_*.json` with `input_manifest.json`. Only ignored scratch artifacts were written. Conditional robot mass is [1617.515430369342, 2072.7550394250543, 2738.613240361904] kg, nominal **2072.755 kg**. Four main ground pads are explicitly counted at density hypotheses [1100, 1250, 1500] kg/m³, nominal combined mass **34.297 kg**; these are material hypotheses, not selected pad specifications.

## Real material connection and segmentation

Actual pad/steel triangle surfaces meet at Z=.033 m. Forepad/frame has 104 triangle-touch pairs per tested side; heel pad/frame has 184. Strict contained vertices are zero, and the approximately −0.18 nm Z discrepancy is boolean float precision, not a useful interference fit.

All four moving steel segments were independently checked as watertight, consistently wound, and having exactly one positive material component. At 24 actual rib XY samples, +Z rays find a continuous material interval from Z=.033 through the existing frame connection target (.046 forefoot / .051 heel). The connection conclusion therefore uses the real finite tray/rib/frame material, not only rigid-body ownership or a scene metadata assertion. These samples do not qualify plate/rib stresses or manufactured joins.

At Z=.034, .036 and .038 inside the 6 mm tray layer, both fore trays begin at X=.025 and both heel trays end at X=−.104; the X gap is **129 mm**. No tray layer joins the independent front and rear ground groups. Net-metal arch/forefoot and arch/heel intersections were zero volume for both sides at neutral and their isolated unloaded −15°/+10° endpoints (8 checks). This limited steel check excludes retained armor/visual proxies, full body/collider clearance and the continuous folding path.

## Material-fit rejection

Actual native material boolean intersections remain:

| Retained armor part | Steel/armor overlap, cm³ | Intersection Z range, m |
|---|---:|---:|
| left_ivory_inner_low_rail | 107.939 | 0.033000–0.099057 |
| left_ivory_outer_low_rail | 69.226 | 0.033000–0.039000 |
| left_composite_high_heel_shell | 27.799 | 0.033000–0.039000 |
| right_ivory_inner_low_rail | 109.562 | 0.033000–0.099057 |
| right_ivory_outer_low_rail | 68.876 | 0.033000–0.039000 |
| right_composite_high_heel_shell | 27.800 | 0.033000–0.039000 |

Outer-rail and high-heel intersections lie entirely in the new .033–.039 m tray layer. The larger inner-rail intersection reaches .099 m and includes a pre-existing higher frame conflict; its complete volume must not be claimed as newly introduced by the tray. Same-body ownership and frame union do not make two different materials occupying the same space legitimate. The side rail/heel shell can retain its original exterior while the interior mating geometry is made disjoint by the root owner; this review edits no candidate geometry.

## Updated low-foot demand

All 64 local segment cases independently replayed this B bundle's finite unilateral whole-robot contact extrema, with its latest mass allocation and the moving segment's own pad/frame/armor weight. Fore and heel stop-centroid arms remain 30 and 25 mm. No favorable whole-foot load split is selected. Stop-pair division by two is a conditional assumption, not a solved transverse pin/cheek load distribution.

| 3000 kg external pressure condition | Required total segment stop peak | Conditional force per paired stop |
|---|---:|---:|
| Neutral, left forefoot | 433.836 kN | 216.918 kN |
| Neutral, left heel | 357.289 kN | 178.645 kN |
| Maximum: forward_manipulation, left forefoot | **533.373 kN** | **266.687 kN** |

At the maximum stop case the .124 m low-foot pin requires **507.398 kN** vertical reaction on the moving segment. This is a demanded reaction, not an allowable or a certified support. It cannot be assigned to the separate .285 m leg ankle paired bearing envelope.

Compressive stops cannot supply negative demanded reaction. The largest conditional reverse holding torque is **215.052 Nm**, under 100 kg payload and 1.5 load multiplier (neutral, right forefoot); this is a sensitivity, not dynamic impact qualification. In the 3 t pressure cases alone the reverse torque reaches **143.368 Nm**. Fore lock guides still have no actual fixed-steel surface contact, and their support/actuator/retention route remains undefined. Lock capacity is not demonstrated.

The governing segment equations use actual contact and gravity moments at the low axis, with an assumed stop-face pressure centroid: `M_ground+gravity + R_stop * cross(r_stop,n_stop)_Y = 0`; force equilibrium then determines pin reaction. Stop contact pressure/centroid, radial contact/shaft bending, plate/rib/neck stresses, welds, bolts, material/HAZ qualification, buckling, fatigue, friction, faults, dynamics and energy remain red. Both low-foot components and whole-robot physics remain unqualified.

Reproducible native/FBD entry: `.scratch/gorilla_internal_b_foot/review_b_segment_trays.py`. Detailed 64-case extrema and native samples are in `whole_review.json`; material intersections are in `local_armor_material_intersections.json`; `final_review_summary.json` binds the conclusions and source hashes. All selected outputs are bound in `final_artifact_manifest.json`.
