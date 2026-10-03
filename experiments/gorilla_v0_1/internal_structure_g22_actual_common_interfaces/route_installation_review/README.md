# G22 route installation review

The frozen three-net prototype was bound to actual root V2 `3190ec7d03019ed2d74a5f812b85a15f93d7f03104f98235e5107986e7f1a50b` (2958 IDs). Its already-world-SI vertices were independently transformed back to pack0 local and then forward with Rz90/C[.30,0,2.145]; maximum difference 0 m. No second rotation was applied. All 257 original pack0 members remain byte-identical in vertex/face arrays; none of the other16 potential nets was removed.

Actual subset world bounds are X[.179,.453], Y[-.43,-.15375], Z[2.088,2.268] m. Combined with the original complete mounted pack, world dimensions are 274×781.05×220.5 mm. Extensions from the original actual slot are low X58.650239 mm/high X90.925 mm, low Y71.25 mm and high Z24.7 mm. This is only one terminal/two sense nets and cannot substitute for all return/tap/series routes.

The AABB broad phase produced 294 pairs against 83 actual target resources. Every candidate pair has a literal result or explicit unknown in `foreign_installation_queries.json`. Two valid finite-material conflicts exist with **e_right_original_intake**, a real1.5 mm open-ended duct backed by E metadata and nonzero finite-volume/mass assumptions:

- sense net01 Cu: **0.0290938874 cm³** positive intersection.
- sense net01 jacket: **0.0016916313 cm³** positive intersection.

The two-pin bank also occupies **0.384 cm³** of pack1's removed-cover service reserve. Twelve intersections with the G16 computational design domain are region membership, not installed solid clashes. There are 59 original pack0 internal positive/unknown pairs, kept in a separate own-pack scope; immutable old skin/TIM/plate and old paths were not swapped for the five bored analysis copies.

Twelve queried old visible-geometry targets have polygon/mixed face schemas rejected by the strict native-triangle contract. Their **81 route-pairs remain unknown**; no implicit triangulation, zero assumption or fit claim was applied. A retained legacy waist-pitch barrel has tiny native triangles and remains resource-rejected even though the kernel can answer a volume query. Root's two known actual-joint receiver resource rejections (`g21_b_roll_reaction_receiver`, `g21_b_yaw_reaction_receiver`) are separately retained, not confused with the prior17-part prototype contract pass. NoError alone never closes an installation gate.

`world_route_subset_probe.json.gz` contains the12 unchanged route/lug/sleeve/bank parts in world coordinates and context hashes, with no original whole-pack deletion and no bored source barriers installed. Subset mass remains **0.1424164934 kg** once; full pack mass, foreign-function mass, COM/I and stable SI are not assigned or released.

`check_installation.py` is the exact readonly executable. Replay in a copied directory using `.venv/bin/python check_installation.py --root /home/ethan/Projects/Sai_Rotbots/.scratch/gorilla_internal_g22_root_assembly/scene.json.gz --expected-sha 3190ec7d03019ed2d74a5f812b85a15f93d7f03104f98235e5107986e7f1a50b`. Two implementation-scope corrections are preserved as exact earlier producers/reports: originally missing per-route unknown exception rows, and finite duct metadata classification. No geometry/source repair was performed. `summary.json` and `freeze_manifest.json` are the bounded receipt.

Installation remains rejected/unknown. Root must jointly provide duct separation or a true typed feedthrough, complete remaining nets and service space, admissible source geometry, real cell/polarity contact, dielectric/ampacity/thermal/pressure ratings, and complete pack/robot clearance.
