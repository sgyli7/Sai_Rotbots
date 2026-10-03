# Gorilla G4B ankle-pitch bench — conditional interface prototype

Final native source `9a88efe894625e7ed3d3f15e544ead7b574382035594ab8d4b81f530fbb7b21a`. This is an internal single-joint bench with example world pivot [-0.060,0.650,0.300]m, not the pending leg/foot design or an adopted exterior. Geometry stopped before handoff. No Git/canonical/old source changes.

## Material, interface and movement

- 30/30 strong signed finite-material sources pass. Parent and output carrier each have **one actual material root** after native CSG construction; negative closed cavities are preserved. No repair, normal flipping, component composition or relaxed tolerance.
- Every pair of all 30 actual parts checked, including separate caps/bolts/pins. Neutral closed/open and ±25° unlocked endpoints: **0 verified material intersections and 0 bearing-envelope intersections** above 1e-10m³. This is four-pose sampling, not a continuous sweep certificate.
- Both compression shoes contact actual child lugs and parent deck at neutral with zero positive volume and zero gap. Original Y±0.180m withdrawal fails 12/21 actual positions; source cd436657 is preserved in `y_withdraw_failure_02_35/`.
- Only the removal interface was revised: same two shoes, same Y±0.075m, unload then translate +X0.280m. **0 material intersections at 21 sampled withdrawal positions**. No automatic release, lateral retention, handles, stowage or bearing-cap tool clearance has been qualified.
- Two short 59.9/28.2mm journals are only 25mm from the carrier wall to each bearing center, span290mm. Drive torque goes through integral paired fork/webs and wide closed output box, not a long60mm torsion shaft. Catalog32212d60/D110/T29.75 reference parts are counted1.15kg each once; actual rings/rollers/pressure centers/preload/fits are unknown.

## Load and pressure domain

29430N upward ground load at [0.25,0.65±0.1,0] is an external3t-pressure sensitivity, not payload or walking capacity. Six-dimensional equations retain both cylinder forces and paired radial reactions for two stated allocations, including opposite lateral offsets. No robot/module gravity, friction, contact dynamics or full-machine LP is certified here.

Initial arm x0.280m gives minJ0.19258m/rad and is rejected before finite construction. One macro B arm x0.320m gives signed J0.207792..0.313904m/rad across121 q samples [-25,+25]°. Finite50/25/wall5mm cylinders have eye496.133..729.968mm, working stroke253.834mm, zeroeye486.133mm and minimum finite zero429.834mm. No manufacturer cylinder has been shortened; no selected OEM pressure rating exists.

Maximum required nominal3t force over the stated q/CoP/allocation cases is 32798.834N, pushing on cap side. At21MPa×0.8, available cap32986.723N leaves only0.57% worst-case nominal margin before gravity/unknowns. All18 nominal cases pass this force-only inequality; 1.5factor rejects6/18 at21MPa×0.8 and2/18 at30MPa×0.8. Full per-case signed pressure/pin/journal reactions are in `report.json`; nominal stress screens are not joint/pressure/stiffness acceptance.

At neutral centerCoP with equal cylinder load: each cylinder pushes16805.484N. Actual upstream mount datum[-0.230,0.650,0.910]m must supply **F=[0,0,-29430]N and M=[0,14126.4,0]Nm**. Ground torque at pitch axis is -9123.3Nm. Cylinder fixed-eye, moving-eye, bearing and stop loads are retained separately. `optimization_handoff.json` has all exact parent6D ports, output6D equivalent at actual carrier end, native non-design face selectors, mother material references, outer design envelope primitives and functional/motion/tool voids. The actual upstream leg/downstream foot attachment is omitted and remains a red interface.

## Mass, stiffness and unresolved scope

Finite conditional steel net mass 131.180662kg + catalog bearing2.300kg = **133.480662kg**. Parent 74.990774kg, child 31.977019kg. This includes the long fixed bench backbox and finite stops, not the previous23.9–43.2kg housing-only planning scope; no weight reduction is claimed. Oil/valves/seals/hoses/stop retainers/tooling/upstream mounting and whole leg remain uncounted unknowns. Full per-part/all-pose COM and3×3 inertia are in `report.json`; catalog-envelope inertia is a stated approximation.

Geometry/resource: sampled conditional evidence as above. **Pressure qualification, stiffness/displacement, material/process, welded/bolted/pinned interfaces, bearing load/life, maintenance and persistent hydraulic/thermal capability remain unqualified and block physical release.** Full3D topology optimization has not started. Wide mother domains may be redistributed only with preserved actual bosses/load interfaces/voids and a new bound source/load solve; density scaling or arbitrary holes are not improvement evidence.

The very long eye at worldZ0.820 and entire upstream enclosure are unintegrated. Pending independent Gorilla leg/foot design must re-establish axes, carrier interfaces, mass and load allocation. No claim that AA3 must change follows from this bench.
