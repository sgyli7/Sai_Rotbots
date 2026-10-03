# G8 source-bound material layout review

This reads G7 actual case20 fields and exact CAD, plus the unchanged other 29 G4 parts. It creates no CAD, exterior, new loads, FE solve or topology result. G7 sources remain frozen. The new leg/foot illustration has not been adopted by this single-carrier bench.

Coarse max is at `[0.11939537649719985, 0.5969525452651959, 0.36225305041180655]` m, near negative-Y stop toe corner `[.12,.5975,.36]`, CAD surfaces 20/22. Fine max is at `[0.06058375739381218, 0.7030842620057963, 0.36201894777679033]` m, near **positive-Y** opposite toe `[.06,.7025,.36]`, CAD surfaces 23/25. These feature positions are from the actual CAD construction and tagged boundary triangles, not an exterior rendering. Stop load plane is z=.388; box top is z=.360, inner top z=.354; the lug overlaps the top skin down to z=.355, with no toe fillet.

## What the fields say

Case20 is the prescribed-reaction neutral static stop allocation, 3t, load factor1, CoP lateral +100mm. Each stop applies −30,411N; bearing reactions and the downstream mount preserve the complete six-dimensional wrench. Gravity and real contact are absent. Factor1.5, the other CoP side, four poses, drive cases and full-system loads remain required next validation scope; they are not removed because this field only samples one case.

| Diagnostic | Coarse | Fine |
|---|---:|---:|
| Max element VM | 461.35 MPa | 571.28 MPa |
| Compliance | 29.3732 J | 31.8973 J |
| Rigid-removed max displacement | 0.7816 mm | 0.8556 mm |
| Selected top-wall region energy fraction | 37.29% | 38.08% |
| 20mm neighborhood volume-average VM | 84.41 MPa | 88.95 MPa |

The peak rises 23.83% and moves between corresponding sharp corners. Compliance rises 8.59%, so two levels do not establish stress/displacement convergence. A reentrant-corner singularity is a risk, not a proven explanation for all deformation. The selected top-wall region holds about 37–38% of total strain energy, while a 20mm sphere around each mesh's max holds only 2.88/3.09%. The load-introduction area is broader than one maximum element. Element-integrated energy matches the root energy ledger (half compliance), not a new capacity result.

## Two bounded routes

**A — finite local transition.** Retain loaded pad, port and body positions; compare an actual 6–12mm toe transition/fillet and 10–12mm local top patch. This tests whether smoothing and local section address the concentration. It may regularize a corner without fixing the compliant stop→lid→sidewall/floor→mount route. A full-path compliance and contact comparison is required; reducing one reported max is insufficient.

**B — redistribute the wide closed-section material.** The next useful comparator is two continuous 4–6mm longitudinal webs directly beneath child-local y=±75mm stop pads, tied to top, floor and actual downstream end wall. Keep a conditional 4–6mm closed skin; do not freeze all old walls or the whole main cavity. Rib ends are tied to each corresponding inner end wall in the analytical budget, not floating. A manufactured/continuous junction, bores and tool exclusions must be built before FE. This is a material-allocation hypothesis, not a selected final architecture or an optimization outcome.

Exact gross closed-box budget (including both endcaps): 6mm current outer box gives 18.097kg before boss/bores/junction deductions. A 4mm closed skin plus two 6mm full-height webs gives 16.545kg; 6mm skin plus 6mm webs gives 22.257kg. These are **box-only gross budgets**, not child/robot mass claims. Existing child mass is separately about31.985kg.

For ideal load directly over a 60mm rib footprint, a 6mm web gives84.475MPa compression at factor1,126.713MPa at1.5; the 4mm value is126.713/190.069MPa. This assumes actual direct load and supporting junction. Plate-buckling sensitivity spans k=.43 to4; for a6mm×138mm web that is154–1435MPa, demonstrating the importance of edge restraint instead of granting strength. The JSON also keeps box bending/torsion and cantilever top-strip challenges; they are conditional formulas, not substitutes for actual 3D/contact calculations.

## Design space must be allocated

The actual box inner dimensions413×228×138mm enclose12.995L. This is **not certified free volume**. Querying all29 retained components in the actual child frame at all four stored poses finds only the two moving pins intruding into this raw inner box,15.917cm³ combined at each pose. No claim is made that the rest is vacant throughout continuous motion or available for arbitrary material.

Keep non-design interface patches and adequate surrounding bearing/pin/stop/mount boss material. Reserve actual journal through bore14.1mm, keeper hole/seat functions and20.2mm fork pin holes; preserve pin material and rod-eye movement. Pin extraction, bolt tools, shoe retention/stow, real wire/hose/fitting bend domains and loaded contact motion remain explicit missing exclusions. The main hollow box was created by the old producer; it is not independently established as an essential permanent void. Walls/ribs may be redistributed within the real 3D component envelope after these exclusions are closed. Outer armor AABB is not used as an available cavity.

Root decides whether to build A or B next. Neither route changes the exterior or grants S355 strength, real bearing fit, whole-leg/robot capacity, fatigue, heat, drive, or operation qualification. Complete robot/system integration must resume after this component study.

`material_layout_review.json` contains exact field/input hashes, tagged hot-neighborhood rows,29-item occupancy, finite section formulas and exclusions. `review_material_layout.py` is the bounded read-only reproducer.
