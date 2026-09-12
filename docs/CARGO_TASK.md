# Physical cargo regression

The included task picks up one 100 g box, places it directly into the open cargo
bay, moves the two soft pads inward through one belt drive, then traverses three
separate obstacles. The two cargo sliders retain the original belt relation.
The object is a free rigid body throughout: no weld, attachment, prescribed pose
or hidden support is added after initialization.

## Run

```sh
uv run sai-agent godot --task cargo
uv run sai-agent godot --headless --task cargo --output artifacts/cargo.json
uv run sai-agent godot --task cargo --cargo-obstacle-height .025
```

R restarts the scene and controller together; Esc exits. The demonstration runs
automatically for about 71 simulated seconds. It does not accept simultaneous
WASD steering during this scripted acceptance task.

CPU MuJoCo reproductions from the repository:

```sh
uv run python scripts/evaluate_cargo.py --out artifacts/cargo18 --require-pass
uv run python scripts/evaluate_cargo.py --out artifacts/cargo25 --height .025 --require-pass
uv run python scripts/evaluate_cargo.py --out artifacts/unsecured --no-clamp --require-pass
```

The last command passes only if the object is placed but transport is blocked.
The equivalent Godot `--no-clamp` run intentionally exits with code 3 and writes
`success: false`; that is the expected negative-control outcome.

## Recorded results

| Physics owner | Obstacle height | Transport | Cargo checks | Lost / unclamped steps |
|---|---:|---:|---:|---:|
| CPU MuJoCo | 18 mm | 2.636 m | 22,001 | 0 / 0 |
| CPU MuJoCo | 25 mm | 2.599 m | 22,001 | 0 / 0 |
| Godot/Jolt | 18 mm | 2.691 m | 44,000 | 0 / 0 |
| Godot/Jolt | 25 mm | 2.598 m | 44,000 | 0 / 0 |

All four runs physically contacted all three obstacles and cleared them with
all wheels. Both no-clamp runs stopped before transport. Machine-readable
summaries are in [cargo-regression.json](../evidence/cargo-regression.json).

## Controller boundary

SO101 follows the frozen source-axis path in `models/tasks/pick-place.json` with
model-state inverse kinematics that compensates chassis motion. Motor commands
are torque limited. Godot owns its physics; Python evaluates FK/bias without
stepping a second world or returning body poses.

Loaded movement intentionally preserves the previously verified 57-observation
crawl actor in `policies/legacy-crawl57.json`. It is separate from the new
82-observation WASD actor. The 18/25 mm obstacles are bumps, not substitutes for
the four-riser stair suite. Cargo-on-stairs, arbitrary item sizes, vision-based
target finding and combined interactive pick-and-drive are not validated here.

Godot uses an uncalibrated elastic force approximation for the belt; MuJoCo uses
two joint equalities. Neither result establishes real belt stiffness, gripper
friction, payload capacity or hardware transfer.
