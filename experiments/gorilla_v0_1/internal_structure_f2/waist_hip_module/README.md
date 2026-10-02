# Gorilla F2 waist / hip module: two rejected native stack probes

This is a bounded module study, not a new complete robot or an accepted architecture. Both candidates retain the same 111 C15 armor parts with **0 mm shape change**. AA3 remains the appearance authority. The native four-view PNGs are diagnostic projections of this incomplete module and the original armor, at the same 226.229508 px/m; they are not proposed replacement concept art.

The candidate sources remain unchanged. A has 515 rows / 499 unique IDs; B has 519 rows / 503 unique IDs. A prefix-selection mistake duplicated all four hip-roll cylinder context groups: 16 rows share existing IDs and identical geometry. This is a resource rejection, explicitly preserved instead of silently repairing the candidate. Each of the four complete electric groups has all ten source functions exactly once, with no scaling: gear, motor, fixed housing, cooling, input hub, output adapter, brake, feedback, controller and connector. `resource_identity_and_mass_receipt.json` verifies original/translated vertices, exact faces, source IDs and mass ranges.

A keeps all F1 axes and translates whole kits along their own axes: waist yaw −60 mm Z, waist roll +50 mm X, hip yaw +240 mm Z. B moves those whole groups by −140 mm Z, −100 mm X and +270 mm Z, and moves the waist pitch axis from Z=1.82 to 1.75 m. B separates the pitch output cheeks from the fixed yaw fork rather than repeatedly patching individual pieces. Both use finite coaxial shafts, actual race proposals, shell plates and side returns. Neither has a proven bearing assembly, bolt/flange interface, lubrication, seal, stiffness, fatigue or strength rating.

| Candidate | Native neutral finite-material pairs | Original armor intersections | Largest verified neutral material conflict | Largest verified sampled motion conflict |
|---|---:|---:|---|---|
| A | 227 | 106 | 140.823487 cm³: waist B mount / actual rod | 144.281044 cm³ at waist pitch +25°: same pair |
| B | 232 | 97 | 81.574300 cm³: complete waist-roll output adapter / fixed outer race | 92.929803 cm³ at left hip roll +6°: hip cap ear / actual roll-cylinder barrel |

The pair counts are the original single-mesh Manifold float32 screen, deduplicated by ID pair. The largest witnesses were independently rechecked using directly joined single `Mesh64` input, with preserved signed surface orientation and actual pose transforms. Their rejection remains real. Thirty-four sampled poses per layout are finite sweep diagnostics, not continuous clearance proof or new joint ratings. B violates the source waist-cylinder stroke window at both waist pitch ±25°. Old LP results, oil routes and installation qualifications are not inherited.

The initial signed-surface audit v1 and v2 incorrectly classified ~1e-13–1e-12 m³ degenerate tetrahedra as nested cavities because its containment tolerance exceeded their volume. **That finding is withdrawn.** The final v3 audit uses unrepaired source face components, a declared meaningful-volume threshold of 1e-10 m³, and direct `Mesh64` material operations; neither candidate has an incorrectly oriented meaningful closed cavity. Imported cylinder faces and vertices are exactly equal to F1 source. The old audit outputs stay here to explain the correction. `Manifold.compose` is never used to reconstruct signed hollow material.

The final read-only `Mesh64` material ledger is split by inventory rather than inherited union-row IDs:

| Candidate | Intrinsic finite module material | Temporary eight-cylinder/pin context | Combined per-owner net material | 24 complete component references |
|---|---:|---:|---:|---:|
| A | 274.793453 kg | 87.053444 kg | 360.383878 kg | 97.493 / 102.813 / 113.213 kg |
| B | 283.572996 kg | 87.053444 kg | 369.238731 kg | 97.493 / 102.813 / 113.213 kg |

Material masses use the existing 7,850 kg/m³ candidate assumption. Intrinsic/context subtotals overlap at shared fixed-owner pins, so their sum must not be used as the combined net material. Separate moving-owner intersections remain rejected rather than being subtracted. Reference envelopes are not exact OEM material or accepted inertia. These are module inventory values, not whole-robot mass or ability ratings. The prior float32 ledger is retained as historical diagnostic output, superseded for this split by the receipt.

Four hip-roll B eyes at X=−0.075 m, Y=±0.20/±0.50 m, Z=1.34 m have no continuous reaction bridge. Adding long rods through the independent thigh would fail the intended serial motion. The torso output saddle also ends at a proposed mating interface; it is not the missing complete shoulder reaction bridge. Positive union-component counts in the receipt describe actual material continuity only; owner names and rolling contact do not certify a force path.

The next bounded module action should jointly change the output-adapter / shaft / bearing axial stack and the actual cylinder eye supports, with a complete independent hip-roll output carrier that reaches its lower eyes without crossing the thigh sweep. If the waist pitch axis moves, the entire matching cylinder eye/stroke package must change together. Bearings need a finite axially separated flange and roller envelope; current collar/race intersections cannot be accepted as intended contact. Only after this module is physically installable should it reconnect to a complete torso/shoulder bridge and the full body.

Neither failed candidate proves AA3 needs reshaping. Internal whole-group reordering at **0 mm external change remains first priority**. Any later shell adjustment needs a concrete residual conflict, a minimum change budget and a same-source four-view proposal for the user's aesthetic acceptance. No physical, SI, real-contact, strength, installation or aesthetic gate is closed here. No Git change, GPU training or procurement decision was made.
