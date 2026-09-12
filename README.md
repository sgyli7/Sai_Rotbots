# Sai_Agent_001

A four-wheel-leg cargo robot with a front SO101 arm, an open blue cargo bay,
camera mounts and a rear touchscreen layout. The same named joints and physical
model are used across training and game integration.

**Development preview.** The eight-case WASD/crouch suite passes in CPU MuJoCo
with both the reduced training robot and the fully articulated robot. Stair
training and the Unity/Godot integrations are still in progress. This is not yet
a tested hardware kit or a completed game integration release.

| Capability | Current evidence |
|---|---|
| Forward/reverse, left/right yaw, combined turning | Passed reduced and full-model MuJoCo checks |
| Shift crouch, release recovery, crouched driving | Passed; approximately 35–39 mm body lowering |
| Zero movement input | Explicit bounded-torque braking and height IK |
| Continuous stairs | Experimental; one four-riser 20 mm descent passed, complete suite not passed |
| GPU training | MuJoCo Warp + PPO on GB10; PyTorch CPU threads capped at two |
| Unity / Godot packages | Integration in progress |
| Hardware | Source/envelope and provisional inertia model; not measured validation |

See [the active plan](docs/PLAN.md), [control contract](docs/CONTROL_CONTRACT.md),
[evaluation evidence](evidence), and [experiment ledger](experiments/ledger.jsonl).

## Current MuJoCo checks

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required. From this checkout:

```sh
uv sync --extra test
uv run python scripts/evaluate_flat.py --policy policies/flat-v1.onnx --out artifacts/check-flat --require-pass
uv run python scripts/evaluate_flat.py --policy policies/flat-v1.onnx --out artifacts/check-full --full-robot --require-pass
```

Optional training dependencies:

```sh
uv sync --extra train
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=2 uv run python scripts/benchmark_gpu.py
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=2 uv run python scripts/train.py --worlds 256 --seconds 300 --name my-flat-trial
```

Training rejects silent CPU fallback. Trials retain configuration, source hashes,
checkpoint metadata and iteration metrics. Reward alone is not acceptance.

## Models and provenance

- `models/locomotion.xml`: fixed arm/cargo training reduction; collision proxies
  and unchanged total mass are documented in its manifest.
- `models/full/robot.xml`: full arm/cargo articulation and original contacts;
  two cargo belt couplings, no attachment constraint on the carried item.
- `models/full/visual.xml`: the same model with redistributable displays.
- `models/full/assets`: Y-up GLB display parts for the game adapters.
- `policies/flat-v1.onnx`: deterministic actor with normalization included.

SO101 and Raspberry Pi material retain their licenses. Vendor CAD without
confirmed redistribution permission is replaced only in the display layer by
independent dimensional envelopes. Contacts, inertia and joint frames are
separately checked for invariance. See [third-party notices](THIRD_PARTY_NOTICES.md)
and [part-level provenance](models/asset_provenance.json).

Inspired by [MicroDuck](https://github.com/pollen-robotics/microduck)'s functional
approach to characterful robots; the wheel-leg cargo chassis is an independent
design. The bounded experiment loop takes inspiration from
[autoresearch](https://github.com/karpathy/autoresearch).
