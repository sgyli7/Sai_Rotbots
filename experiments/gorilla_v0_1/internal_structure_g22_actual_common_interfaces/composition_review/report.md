# Gorilla G22 composition audit entry

Read v1_rejected_signed_rest/report.md for the preserved first-source rejection, and v2_limited_rest_correction/report.md for corrected limited identity/placement scope. report.json files bind exact raw sources/receipts/root producers and independent reviewer producers. v1_to_v2_delta_and_moment_scope.json enumerates actual changes and stale mirrored finite moments. This audit does not create or repair geometry, and does not close load-transfer or whole mass.

Reproduce the v2 limited check with:

```bash
.venv/bin/python .scratch/gorilla_internal_g22_composition_review/review_composition.py --source-dir .scratch/gorilla_internal_g22_root_assembly --version v2_limited_rest_correction
```

Already bound input snapshots are immutable; the script refuses overwriting them with changed source bytes. A later root source version requires a new review version.
