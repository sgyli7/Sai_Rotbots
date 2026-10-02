# Gorilla F2 read-in

Read `summary.json` first; release=false. A/B source bytes are failed frozen records.

- `a/module_scene.json`, `b/module_scene.json`: native neutral parts, finite frame primitives, explicit joint tree/axes,121-point cylinder geometry, actual five pose meshes/rigid transforms and actual barrel/rod endpoint transforms. Metres, +X front,+Y left,+Z up; root_shift_z_m=0, already_world_posed=true. Do not add root shift again.
- `closed_cavity_receipt.json`: definitive closed-boundary semantics correction and independently normalized critical material pairs. Reassembly is Boolean outer-minus-solidvoid, not compose.
- `a/boundary_orientation_analysis_scene.json`, `b/boundary_orientation_analysis_scene.json`: analysis-only neutral copies with preserved geometric surfaces and containment-parity boundary correction. They are not accepted replacement CAD and do not constitute third layouts.
- `normalized_scope_checks.json`: actual five-pose all-new-material and original111armor material intersections after analysis normalization. Threshold1e-10 m³. Not bearing-contact/strength approval.
- `invariant_audit.json`: original inputs, historical producer hashes and every recorded pose’s vertex-to-transform/faces/volume invariants. Its raw positive-component lists are boundary partitions, superseded as connectivity evidence by the cavity receipt.
- `a/checks.json`, `b/checks.json`: historical syntactic and raw intersection records only; original volume-based masses and raw component counts are not valid material budgets.
- `a/*png`, `b/*png`: actual same-scale native projections, original armor comparator0mm. No Blender or image generation, no concept/aesthetic approval.

Safe read-only diagnostic re-runs (write only ignored receipts):

```bash
.venv/bin/python .scratch/gorilla_internal_f2_lower_module/audit_invariants.py
.venv/bin/python .scratch/gorilla_internal_f2_lower_module/audit_closed_cavities.py
.venv/bin/python .scratch/gorilla_internal_f2_lower_module/check_normalized_scope.py
.venv/bin/python .scratch/gorilla_internal_f2_lower_module/freeze_receipt.py
```

Do not run builders over frozen A/B. If starting another approved candidate, copy inputs to a new branch and fix the hollow-boundary orientation operation before issuing a new source/hash. Geometry helper `fix_normals()` on a separate closed inner boundary is unsafe. Reused parameters are `AXES`, `TEMPLATES`, `actuator`121-point formulas and explicit source action endpoints; no prior mass/LP/strength qualification follows from reuse.
