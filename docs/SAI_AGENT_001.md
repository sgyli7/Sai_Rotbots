# Sai_Agent_001

A four-wheel-leg cargo robot with a front SO101 arm, an open blue cargo bay,
camera mounts and a rear touchscreen layout. The same named joints and physical
model are used across training and game integration.

**Development preview.** WASD and held-Shift crouch pass eight-case checks in
CPU MuJoCo (reduced and fully articulated models) and Godot/Jolt. Continuous
20/40 mm stairs pass the reduced/full MuJoCo and Godot development suites.
Opt-in 60 mm ascent/descent profiles pass the nominal four-riser course under
an explicitly declared 45-second budget. The new descent profile additionally
passes 15/15 development parameter checks in both full MuJoCo and Godot.
These do not establish arbitrary-terrain reliability; the default actor stays
at its 20/40 mm scope. See [experimental profiles](../experiments/stair_profiles/README.md).
Hardware has not been built or measured.

| Capability | Current evidence |
|---|---|
| Forward/reverse, left/right yaw, combined turning | MuJoCo reduced/full + real Godot key events passed |
| Shift crouch, release recovery, crouched driving | Passed; approximately 35–40 mm lowering |
| Zero movement input | Bounded-torque braking and height IK |
| Continuous stairs | Four 20/40 mm risers up/down passed in MuJoCo reduced/full and Godot |
| Pickup → secure → transport | 100 g item, 18/25 mm obstacles, MuJoCo + Godot; unsecured cargo prevents departure |
| GPU training | MuJoCo Warp + PPO on GB10; CPU threads capped at two |
| Godot | One-command launcher, full articulation, camera views; flat acceptance passed |
| Unity | Dedicated native-model adapter in draft PR; editor execution unverified |
| Hardware | Source/envelope and provisional inertia model; not measured validation |

![Actual Godot viewport](images/godot-preview.png)

## 直接启动 Godot / Run Godot

Install Godot 4.7.2 and Python 3.12 with `uv`, then from this checkout:

```sh
uv sync
uv run sai-agent godot
```

W/S 前进后退，A/D 左右转向，按住 Shift 下蹲、松开恢复，R 重新开始，Esc 退出。
The launcher starts the policy service and Godot together. Godot/Jolt owns the
physics; Python supplies motor targets and uses MuJoCo only for arm bias/FK.
No separate training process is needed to play. `--godot-bin` selects an executable.

For a recorded headless input test:

```sh
uv run sai-agent godot --headless --case W --output artifacts/godot-W.json
```

Experimental stair scene: `uv run sai-agent godot --stairs .02` (add
`--descending` for descent). A simulated ground raycast selects the stair policy
and a slower approach speed. The four-riser 20/40 mm development cases pass;
this is **not** camera-based VLA or validation on arbitrary stairs. Cameras
render separate observation views.

The wheel also includes the experimental profiles; no checkpoint download or
training environment is required to try them:

```sh
uv run sai-agent godot --stairs .06 --stair-skill ascent60
uv run sai-agent godot --stairs .06 --descending --stair-skill descent60
```

The descent profile lowers the body halfway and uses known-route steering at
y=0; A/D overrides that steering while held. Both profiles are for the declared
straight test flights. They are explicit choices, not an automatic classifier
for every stair direction or arbitrary game terrain.

Run the preserved physical pickup, cargo clamp and loaded transport demo:

```sh
uv run sai-agent godot --task cargo
```

The demo uses model-state inverse kinematics for the SO101 and a frozen crawl
policy after the load is secured. It does not weld the item to the gripper or
cargo bay. This is a separate regression task, not general object recognition
or learned visual manipulation. See [task and evidence details](CARGO_TASK.md).

The existing [Godot project integration](https://github.com/sgyli7/MicroDuck-Godot-Simi2Sim/pull/3)
provides `sim2sim-play --robot Sai_Agent_001` through an optional dependency.
The [Unity integration PR](https://github.com/sgyli7/MicroDuck-Unity-Sim2Sim/pull/3)
contains setup and a native-model demo; its editor/runtime acceptance is pending.
See [integration instructions and limits](INTEGRATIONS.md).

See [the active plan](PLAN.md), [control contract](CONTROL_CONTRACT.md),
[evaluation evidence](../evidence), and [experiment ledger](../experiments/ledger.jsonl).
The [geometry-based appearance study](DESIGN_PRESENTATION.md) is separate
from the [open-source and hardware maturity record](OPEN_SOURCE_STATUS.md).

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
separately checked for invariance. See [third-party notices](../THIRD_PARTY_NOTICES.md)
and [part-level provenance](../models/asset_provenance.json).

Inspired by [MicroDuck](https://github.com/pollen-robotics/microduck)'s functional
approach to characterful robots; the wheel-leg cargo chassis is an independent
design. The bounded experiment loop takes inspiration from
[autoresearch](https://github.com/karpathy/autoresearch).
