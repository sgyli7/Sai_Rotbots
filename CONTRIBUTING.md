# Contributing

Keep the approved robot geometry and named physical contract stable. Changes
to masses, contacts, axes, limits, motor semantics or observation order need a
new contract/version and the affected engine regressions. Visual-only changes
must not silently change collision meshes or inertia.

Run `uv sync --extra test` and `uv run pytest -q`. For locomotion changes, run
the reduced/full flat and stair evaluators. For arm, cargo or coupling changes,
run cargo positive and no-clamp negative controls. Record both successful and
failed cases; a reward increase is not a passed physical task.

Use a focused branch and pull request. Keep generated runtime caches, local
training runs, private paths and vendor CAD with unresolved redistribution
permission out of Git. Preserve third-party license notices. New policies must
include normalization, model/actor hashes, control metadata and evaluation
evidence; failed candidates must not overwrite the current released actor.
