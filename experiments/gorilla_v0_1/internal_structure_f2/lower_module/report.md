# Gorilla F2 lower-module failure receipt

**A and B are frozen rejected candidates. Neither is a physical, SI, manufacturing, whole-robot mass, or aesthetic release.**

Only two macro layouts were built. Each has 29 native records: five finite frame unions, eight finite pins, eight unqualified bearing reference envelopes, and four finite actuator barrels plus four moving rod assemblies. Incoming knee fixed/output interfaces and arch flange are present; the thigh/knee drive and independent forefoot/heel complete foot are outside this module scope.

Axes and neutral material are stored in each `module_scene.json`. Ankle returns to C15 z=0.285 m, 80 mm below F1; foot-roll x axis is the new candidate z=0.210 m. No physical/SI contract was changed. Fresh whole-robot FK, contact LP, dynamic shaft forces, actuator qualification, fluid/thermal response and assembly interfaces remain unknown. Original C15 scene and all 111 original armor records are unchanged; this comparator does not approve C15 aesthetics or prove AA3 must change.

## Resource semantics correction

`trimesh.fix_normals()` flipped completely closed negative inner boundaries in seven parts per layout. Syntactic watertight/consistent-winding/positive-volume tests passed all 29 parts and all five poses, but these tests missed the nested-boundary error. Historical raw `solid_component_failures`/positive-component counts in `checks.json` and `invariant_audit.json` are superseded for material connectivity; nested positive islands are not automatically disconnected material. Historical listed steel masses are invalid physical budgets.

Independent normalization used exact Manifold Mesh64 component containment and nesting parity: add positive outer material, subtract positive closed voids, add true nested even-depth islands. It **does not use Manifold.compose**. Analysis copies are separately hashed, never substituted for the frozen source. The 100 mm outer / 50 mm cavity regression is 0.000875 m³ correct, 0.001125 m³ after fix_normals, and 0.000875 m³ after the same normalizer; the regression asserts actual values.

| Layout | Source-derived invalid steel kg | Analysis-only boundary-normalized steel kg | Neutral corrected material pairs | Neutral original armor pairs |
|---|---:|---:|---:|---:|
| A | 158.080345 | 142.508837 | 16 | 25 |
| B | 149.990155 | 131.528049 | 23 | 21 |

Density is a conditional 7850 kg/m³ steel assumption, not a procurement/material qualification. Eight reference bearings contribute a provisional 2.4/4.8/9.6 kg. Normalized volumes are diagnostic copies of still-incompatible geometry; subtracting their difference is not approved robot weight reduction. Different-motion parts physically overlap and cannot be treated as a realizable mass budget.

## Independent corrected material rejection

After reorienting the participating closed boundaries in analysis copies, four independently selected positive-volume pairs remain:
- A `f2_a_left_distal_shank_net_frame` × `f2_a_left_ankle_barrel`: original Mesh64 226.949980 → normalized 93.576672 cm³. Different rigid owners or endpoint-driven barrel motion, not nominal bearing reference contact.
- A `f2_a_left_distal_shank_net_frame` × `f2_a_left_ankle_pitch_carrier_net_frame`: original Mesh64 79.058018 → normalized 40.059397 cm³. Different rigid owners or endpoint-driven barrel motion, not nominal bearing reference contact.
- B `f2_b_left_ankle_pitch_carrier_net_frame` × `f2_b_left_foot_roll_pair_1_barrel`: original Mesh64 133.288003 → normalized 113.561312 cm³. Different rigid owners or endpoint-driven barrel motion, not nominal bearing reference contact.
- B `f2_b_left_distal_shank_net_frame` × `f2_b_left_ankle_pitch_carrier_net_frame`: original Mesh64 126.709994 → normalized 69.164794 cm³. Different rigid owners or endpoint-driven barrel motion, not nominal bearing reference contact.

Historical original pair volumes can differ slightly from the old float32 trimesh Boolean checker; the receipt directly compares original and normalized **Mesh64** within one method. Full five-pose material and original-armor checks were repeated on normalized copies in `normalized_scope_checks.json`; their pair counts happen to match the raw counts, but original volumes and raw connectivity are not inherited.

Containment reduces most purported multi-islands to a single material root containing closed voids. Both actual arch assemblies still have **two disjoint root material solids**: the outer FR0 crank is X[-0.264,-0.250] m, while the hollow output shaft ends at X=-0.245 m, leaving a real 5 mm gap. Giving both the same body name cannot transmit load. No patch or third geometry was made.

## Finite drive and immutable motion

All four cylinders explicitly retain bore63 mm / rod30 mm / wall5 mm / pin40 mm; no vendor zero length or angle range was truncated. Custom minimum zero eye length is stroke +170 mm (two 30 mm ears, two20 mm caps, piston20 mm, seal20 mm, exposed rod30 mm). The extra allocated eye length is a charged finite hollow sleeve. It is a custom dimensional hypothesis, not an OEM assembly fit or rating. B adds a 0.5 mm material lap to candidate joins; real joining, pressure integrity and sealing remain unqualified.

| Layout / cylinder | Working range deg | Eye range mm | Stroke mm | Allocated zero mm | Minimum zero mm | Minimum absolute J mm/rad |
|---|---|---:|---:|---:|---:|---:|
| A left_fold | -20..0 | 271.978–305.164 | 53.186 | 261.978 | 223.186 | 71.553 |
| A left_ankle | -10..0 | 518.786–543.369 | 44.583 | 508.786 | 214.583 | 138.488 |
| A left_foot_roll_pair_0 | -10..10 | 260.171–290.207 | 50.036 | 250.171 | 220.036 | 75.439 |
| A left_foot_roll_pair_1 | -10..10 | 260.171–290.207 | 50.036 | 250.171 | 220.036 | 75.439 |
| B left_fold | -20..0 | 268.560–314.841 | 66.282 | 258.560 | 236.282 | 130.006 |
| B left_ankle | -10..0 | 475.105–493.011 | 37.905 | 465.105 | 207.905 | 100.609 |
| B left_foot_roll_pair_0 | -10..10 | 260.171–290.207 | 50.036 | 250.171 | 220.036 | 75.439 |
| B left_foot_roll_pair_1 | -10..10 | 260.171–290.207 | 50.036 | 250.171 | 220.036 | 75.439 |

Each joint range is sampled at121 points. Five poses use only source rigid transformations and actual A–B barrel orientation / rod translation, never per-pose cutting or rebuilding. Recorded vertices match the stated transform, faces remain identical and volumes remain constant in both raw and normalized analysis material. The barrel is not rigidly attributed to a parent body transform. Root shift is0.

Own-frame material and original-armor failure counts by pose are recorded in `summary.json` and `normalized_scope_checks.json`; no sampled pose passes. Native source projections `a/` and `b/` show neutral front/left/rear both bare and overlaid with original armor at930 px/m, plus both coupled roll endpoint left views. They are geometry diagnostics, not retouched concept art or aesthetic approval.

Pins have 1 mm radial nominal air clearance inside Ø42 mm eye holes (Ø40 mm pin), requiring a real bushing/fit solution. Fork reaction centers are±32 mm, cheek14 mm and eye44 mm, leaving3 mm axial side clearance per side. Reference journal fit/preload/race contacts, pin retention, mounting interfaces and fatigue are unknown. Full force closure, 3 t pressure requirement and stability were not solved or inherited from E2/F1. Conditional force arithmetic uses20.4 MPa supply,0.3 MPa return and0.9 mechanical factor (push56.582/pull43.413 kN); this is separate from sources agent’s21 MPa single-chamber rough pressure/pin case and is not actuator qualification.

## Read-in and provenance

See `read_in.md`, `summary.json`, `closed_cavity_receipt.json`, `normalized_scope_checks.json`, `invariant_audit.json` and `final_manifest.json`. A producer was byte-archived as `build_module_a_producer.py` before the single B macro revision; the current `build_module.py` generated B. Both producer bindings and original source hashes are verified. Historical A checker archive is kept as `check_module_a_producer.py`; current checker generated B. All files are ignored scratch, no controlled model/docs/Git source were modified.
