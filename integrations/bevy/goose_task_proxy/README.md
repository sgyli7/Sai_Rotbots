# Goose task proxy receiver

Standalone native receiver for `goose_task_proxy_11_v1`. It constructs the real
Rapier multibody, all 11 exterior collision leaves, full SI inertias and actual
jaw loop. It does not modify Sai_Lab's existing production receiver or install a
policy. Python and Rust keep one 20 ms controller update and one integration.

From the repository or extracted handoff root:

```bash
python -m pip install -r integrations/bevy/goose_task_proxy/requirements.txt
cargo test --manifest-path integrations/bevy/goose_task_proxy/Cargo.toml --release --locked
cargo build --manifest-path integrations/bevy/goose_task_proxy/Cargo.toml --release --locked
PYTHONPATH=src python -m pytest tests/test_goose_task_proxy.py -q
PYTHONPATH=src python -m pytest tests/test_goose_collision_filters.py -q
PYTHONPATH=src python scripts/evaluation/check_goose_collision_filters.py \
  --native-probe integrations/bevy/goose_task_proxy/target/release/goose_task_proxy_native_probe
PYTHONPATH=src python scripts/evaluation/check_goose_task_proxy.py \
  --native-probe integrations/bevy/goose_task_proxy/target/release/goose_task_proxy_native_probe
PYTHONPATH=src python scripts/models/build_goose_task_proxy.py --out artifacts/goose_proxy_reproduced
python scripts/models/package_goose_task_proxy.py --out artifacts/Goose_V0.1/goose_task_proxy_11_v1.zip
```

After extracting the ZIP into a fresh directory, run
`python scripts/models/package_goose_task_proxy.py --verify .` there, then repeat
the build, tests and evaluation above. The manifest hashes each package input;
the ZIP/extraction test report is outside the archive to avoid a hash cycle.

On Windows, append `.exe` and set `PYTHONPATH` with the shell's environment syntax.
The Python runtime is `sai_agent.goose.task_proxy_runtime.TaskProxyRuntime`, loaded
with the model and contract paths from the unique entry JSON. Locomotion/recovery
use 65 observations; pickup uses the typed `TaskGoal` extension to 82. The motor
input rotor is driven; jaw output feedback remains the sixth policy axis.

This entry passes bounded M0 engineering checks. It does not certify learned
walking, recovery, pickup/dragging, terrain, hardware or other engines. The custom
contact branch is explicit and pinned. The four flat-floor sole integration
points per foot are material samples, not additional collision shapes. Source
contact quadrature assumes a horizontal plane and an upright sole; other poses
must be independently validated before task acceptance.

The new receiver checks the exact plant/control binding and candidate revision.
It also rejects an exclusion list that differs from the source contract. The
companion collision policy lists all 55 role pairs, including implicit direct
parent filtering: nine connected pairs ignored, 46 retained. Each backend's
97 deliberate-overlap fixtures verify internal, ground, object and cross-robot
filtering. These fixtures are diagnostic placements, not physical pose tests.
The fork's opt-in frictional spring path retains the native Coulomb solver, with
load/slip regression fixtures. PGS passes converge one integration, without
subdividing physical time. See the contact fork's `GOOSE_CONTACT_CHANGES.md` and
Goose's task-proxy design note for provenance and approximations.
