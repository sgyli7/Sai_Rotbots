# G7 single-carrier assembly review

This replaces only `g4_child_load_carrier` in G4 source `9a88efe8…`. The other 29 parts, material assumptions, catalogue bearing masses, gravity owners, and stored four-pose transforms remain exactly unchanged. This is one pitch bench, not the new leg/foot illustration or an assembled robot. No exterior was adopted or changed.

## New-source identity

World-SI exact-circle OCC BREP/STEP is a new source. The coarse boundary is induced directly from 376,820 positive tetrahedra; all 139,606 supplied faces match the independently extracted outward cyclic orientation. Incidence is at most two. All 96,645 coordinates are retained, including 26,854 unused interior nodes. There was no normal repair, splitting, merging, tiny-face deletion, or reuse of the old resource/collision pass. The finite native signed-material contract passes all 30 parts, with one material root in the new child. This predicate is not a manufacturing or strength certificate.

Boundary SHA: `108b6c0eea55bd9758d58819ae4ab70f3186bdbe588a64bb791962735503b728`. Tetra SHA: `cd35725c93510c8392f0c7d3663a83cb329f71f5389cbfb45bf7cc9ddee6a2c3`. Assembly receipt SHA: `c67750a4e76479c6c93b0d14992bfa838c1892d79dbb6af5b6f6cd999c924f27`.

## Actual assembly queries

Neutral closed, neutral open, pitch +25° open, and pitch −25° open each have **zero** positive-volume native material pairs and **zero** bearing-reference-envelope pairs at `1e−10 m³`. The +X 0–280 mm shoe withdrawal has zero collisions in 21 samples. These are discrete queries; continuous motion, tolerance stacks, and tool/stow paths are not thereby qualified.

Both neutral shoes have zero gap to parent and child, with intersection volume below the declared tolerance. Shoe release still requires full unload; lateral retention and loaded contact pressure are open. New child–bearing-envelope minimum gaps are about 13.864 µm, versus a fresh old-source query of 49.940 µm. This difference comes from true-circle child against the retained faceted bearing envelope and **is not an SKF fit/preload result**. Actual circle-circle nominal radial clearance remains a separate conditional dimensional assumption.

## Geometry and same-scope mass

Nominal axes and planar port positions moved 0 mm. Existing hollow-box, through-journal, keeper, and fork-pin void functions remain; no new route/axis void is introduced. True-circle faces replace old polygonal circles, so this does change local material and bore surfaces. Old 64-facet radial chord bounds are 24.33–66.25 µm for the documented pin bore, journal, boss, and fork rounds.

| Scope | Old G4 | New exact CAD | New coarse boundary |
|---|---:|---:|---:|
| Child conditional steel mass | 31.977019357 kg | 31.985320113 kg | 31.984892824 kg |
| Same 30-item neutral total | 133.480662456 kg | 133.488963212 kg | 133.488535923 kg |

Exact-CAD child change is +8.301 g. Coarse tessellation differs from exact CAD by −0.427 g and volume −0.001336%. Its tetra-integrated COM/full inertia agrees with independently integrated boundary values within 8.49e-15 m / 1.05e-13 kg·m². Full per-piece and four-pose COM/full-I changes are in the JSON receipts; exact CAD and native-boundary values are never silently substituted.

The two bearing masses are counted once (2.3 kg total); their inertia remains a uniform reference-envelope approximation. No oil, fittings, holding, hoses, retention/stow tools, upstream mounting bolts, full-leg or whole-robot mass was added or declared complete.

## Remaining gates and next use

Physical acceptance remains false: real bearing/contact traction and preload, paired-cylinder pressure/holding, load-dependent stiffness and local strength, bolt/keeper and shoe retention, upstream interfaces, continuous swept clearance, and full-leg/system integration are open. This source may support root's separate FE-boundary choice and same-version load mapping. No FE result or capacity claim is made here, and this limited evidence does not require a change to AA3 exterior.

Reproduction order: `prepare_mass_and_inventory.py` → `check_replaced_assembly.py` → `verify_boundary_export.py` → `finalize_review.py`, using the source hashes in `snapshot_manifest.json`. Only the present G7 review directory is written.
