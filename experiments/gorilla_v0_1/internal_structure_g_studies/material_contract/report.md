# Gorilla G native signed-material contract prototype

**This is an ignored reusable resource prior, not accepted robot geometry or physical release. Old F1/F2 sources, runtime/scripts and controlled documents are unchanged.**

## Entry and input

`native_signed_material.py` exposes `validate_part(part, tolerances, require_single_material_component=False, diagnose_parity=False)` and `validate_scene(scene, ...)`. A finite material part has a globally unique nonempty `name`, `vertices_world_m` as finite N×3 SI coordinates, and native indexed triangular `faces`. No implicit mm conversion, polygon fan triangulation, vertex merging or array rewriting occurs. Callers must explicitly select the finite-material scope; role metadata, density, parent body names and enclosing reference objects are not converted into material or connection proof.

A scene supplies `parts`; duplicate identifiers reject the scene even when both individual meshes pass. Non-triangle polygons must be triangulated upstream by an explicitly bound operation. Invalid arrays/indices/nonfinite coordinates/open indexed edges/inconsistent edge winding reject. All source tolerances must be finite positive SI numbers.

CLI (only writes inside this ignored prototype folder):

```bash
.venv/bin/python .scratch/gorilla_internal_g_material_contract/check_scene.py --scene PATH_TO_NATIVE_SCENE.json --output .scratch/gorilla_internal_g_material_contract/scene_contract_report.json
```

Optional `--require-single-material-component` enforces the caller’s declared single-material requirement. Optional `--diagnose-parity` adds an explicitly unaccepted volume diagnostic; it never repairs source, flips its verdict, or issues accepted CAD. The CLI records source/script hashes and asserts source file immutability. Exit0 means the listed resource contract passed; exit2 rejects the native scene, with a written reason report. Both remain physically unqualified.

## Method and resource verdict

1. Validate the original indexed native closed faces. A manually enumerated face-adjacency graph partitions **closed boundaries**, not material solids. `process=False` is used; no fix_normals, default split/repair or compose is called.
2. Compute each boundary’s signed volume from original oriented faces with a translated numerical origin. Preserve its original sign. Instantiate float64 Mesh64 without merging or normal repair; record kernel status and native/kernel volume disagreement.
3. Create positive boundary query solids only for containment analysis, while keeping original input untouched. Use exact Mesh64 Boolean intersection volumes and explicitly recorded absolute/relative tolerances. The smallest-volume fully containing boundary is the candidate immediate parent. Crossing or equal-volume overlapping boundaries reject.
4. Check the source’s parent separation tolerance by querying inner-to-finite-outside-parent minimum gap, capped at2× the declared threshold. Volume containment with unresolved/touching parent boundaries rejects rather than guesses. The gap query is capped evidence, not a measured manufacturing clearance.
5. A legitimate closed-boundary nesting tree alternates +outer material / −closed void / +material island. Same-sign nested inner surfaces and orphan negative boundaries reject. Two separated hollow materials and a positive island inside a void have two actual material components, distinct from negative inner skin boundaries. Optional single-material requirement rejects them.
6. Components or native triangles below source thresholds reject; they are not discarded from the native validity decision. When explicit parity diagnosis is requested, analysis may continue after invalid tiny triangles if native edges remain closed and Mesh64 accepts the query. The prior rejection persists. This diagnostic cannot certify material or design intent.

Default source tolerances: minimum boundary volume1e-10 m³; minimum native triangle area1e-16 m²; exact-containment absolute volume1e-12 m³ and relative1e-8; broadphase bounding tolerance1e-9 m; minimum parent gap1e-8 m; native/kernel volume discrepancy1e-8 m³. These are declared computational tolerances, not robot strength, machining or bearing clearance specifications.

Diagnostic parity, when requested, uses Boolean positive root minus positive odd-depth void plus positive even-depth island. It does not call Manifold.compose, and it does not infer that an invalid designer intended a cavity instead of two overlapping solids. The input remains rejected under the declared material-boundary contract.

## Independent regressions

Fixtures are independently constructed analytic boxes with explicit signed face joins and a polygonal annulus. Expected volumes derive from geometry, not from the validator’s own construction or repair. Assertions cover:

- Legal100 mm outer /50 mm cavity: .000875 m³, one material component and one negative closed void.
- Wrong same-positive-sign hollow: .001125 m³, resource rejection; explicit diagnostic .000875 m³ without acceptance or mutation.
- Two spatially separate hollow materials: .00175 m³, two roots/material components; resource contract can pass, declared single-material requirement rejects.
- A20 mm positive material island inside the50 mm void: .000883 m³, valid +/−/+ nesting with two separate material components.
- A50 µm isolated particle: rejected by the effective-volume threshold, retained as an input error.
- A finite64-section through-hole annulus: one connected boundary and no separate closed void; volume checked against the polygonal annulus formula.
- A5 µm parent skin gap: passes default resource tolerance, fails explicitly stricter20 µm source threshold.
- A crossing negative closed boundary: rejected rather than guessed.
- Duplicate actual identifiers: entire scene rejected; unchanged source-array assertions pass.

Ten case records plus duplicate and input-immutability assertions passed. The mixed-fixture CLI correctly rejects the three intentionally invalid native parts. Syntax compilation and CLI operation were checked.

## Historical sampling

F1 structure source is hash90b62e0135a724fb9cb7df9909d58f3b618d40f6f5be922b516e1d83ca073ee6. F2 A/B source hashes and existing cavity receipt are bound in `historical_sample_report.json`. Twenty parts were sampled, not the whole robot or every historic pose.

| Historical group | Samples | Result |
|---|---:|---|
| F1 separate fore/heel trays, both sides |4|All reject same-sign closed inner boundaries|
| F1 yaw/roll gear load shells |2|Pass listed resource predicates; finite through-hole shells, no physical acceptance|
| F2 A known affected lower parts |7|All reject; known same-sign inner boundaries reproduced|
| F2 B known affected lower parts |7|All reject; known same-sign inner boundaries reproduced|

Several F2 sources also contain below-threshold triangles/closed micro-boundaries, native/kernel volume differences, crossing boundaries or unresolved parent gaps. The diagnostic continues only to expose subsequent known problems; it preserves the invalid result. In particular, signed nesting is not automatically normalized into accepted material.

An intentional duplicate copy of an actual legal F1 waist source reproduces duplicate-ID rejection. **The sampled original F1 source has no literal duplicate identifiers**; functional aliases with different identifiers are outside this exact-ID check. No claim of an original duplicate was manufactured.

## Limits and next use

This prototype verifies listed topology, signed nesting and finite Boolean containment predicates under explicit source tolerances. It does not comprehensively certify within-one-connected-boundary self-intersection/embedding; Mesh64 NoError alone is insufficient. Boundary-touching cases are conservative rejects. Connected material is not proof of a rigid connection, bearing race contact, weld/thread qualification, load path, fatigue, collision-free motion, stable SI or 3 t support. Full acceptance remains false even when this early contract passes.

The next complete chain can use this as an early gate before computing mass or doing contact/drive tests. Reject invalid native source and rebuild that producer’s finite material representation explicitly; do not substitute a diagnostic parity result. Exact material collisions, assembly interfaces, physical mass/inertia and load/stability analysis remain separate required work.

## Files and reproduction

`summary.json`, `regression_report.json`, `historical_sample_report.json`, `cli_fixture_report.json` and `manifest.json` bind results and source hashes. All prototype code and artifacts remain within `.scratch/gorilla_internal_g_material_contract/`.

```bash
.venv/bin/python .scratch/gorilla_internal_g_material_contract/run_regressions.py
.venv/bin/python .scratch/gorilla_internal_g_material_contract/check_historical_samples.py
.venv/bin/python .scratch/gorilla_internal_g_material_contract/freeze_report.py
```
