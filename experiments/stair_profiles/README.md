# Experimental 60 mm profiles

These are development profiles, not replacements for `stairs-dev40` and were not part of
the alpha.2 release. The original two ONNX files are exported from GPU trials
008 and 006. The additional `descent60-trial010` actor is a new five-minute GPU
trial. Each JSON retains its own training metadata and actor hash.

| Case | Articulated MuJoCo | Godot/Jolt |
|---|---|---|
| Ascent, trial 008 | Completes in 33.38 s including final stop, under an explicit 45 s diagnostic budget; original 30 s test still fails | Completes in 27.18 s with motion-relative phase |
| Descent, trial 006 with half crouch and route steering | Completes in 15.46 s | Fails lane containment: maximum lateral displacement 0.658 m |

Both use a fixed four-riser flight, 60 mm risers, 180 mm treads and no payload.
These are tuning cases, not held-out terrain. Success requires every wheel to
clear, three seconds stopped, final height, support, uprightness and a 0.3 m
centerline corridor. Failed attempts remain in
[the complete diagnostic record](../../evidence/stairs-60-diagnostics.json).

From a source checkout, run the actual Godot ascent experiment:

```sh
uv run sai-agent godot --stairs .06 --stair-profile experiments/stair_profiles/ascent60.json
```

The descent profile can be reproduced with `--descending` and
`experiments/stair_profiles/descent60.json`; it currently fails acceptance.
The profiles remain in the source experiments directory, outside the bundled
wheel assets. The default CLI continues to use the accepted flat/20–40 mm
actors unless a profile is explicitly selected.

The descent controller requests half crouch and a heading toward the known
straight route at world y=0. Steering modifies wheel speeds; it never moves
the base or feet directly. This uses simulated odometry, not a demonstrated
camera/VLA localization pipeline. A/D overrides route steering while held.

Experimental gait phase starts at 0.5 seconds of the reference cycle when
forward motion begins, independent of when W is pressed. This aligns the
initial phase with the CPU diagnostic. It improved the Godot descent from a
fall to a lane failure; it did not make that case pass. No physics parameters,
motor limits, robot geometry or acceptance corridor were changed.

## Crouched descent training: trial 010

Trial 010 starts from checkpoint 006 and trains the deployed half-crouch plus
known-route steering, with a 0.6 rad/s heading correction bound. It completed
5,849,088 steps in 300.29 seconds on GB10 with two CPU threads. ONNX parity
passed at batches 1, 17 and 256, maximum absolute difference 1.91e-6.

At 0.08 m/s the full articulated MuJoCo suite passes 15/15 and Godot passes
14/15: three riser heights (20/40/60 mm), nominal 180 mm tread/yaw zero and
160/200 mm treads with initial yaw ±0.08 rad. The failed Godot case is 60 mm,
160 mm tread, +0.08 rad. It loses support before the three-second stop starts.
Reducing swing lift from 55 to 30 mm also fails. Reducing speed to 0.06 m/s
fixes that start angle but fails the opposite angle; its Godot total is again
14/15. Neither tuning change is promoted. These are now development regression
cases, not untouched holdouts. All original results remain in
[the trial record](../../evidence/stairs-010-crouched-descent.json).

```sh
uv run sai-agent godot --stairs .06 --descending --stair-profile experiments/stair_profiles/descent60-trial010.json
```

For the failing variation add `--stair-tread .16 --initial-yaw .08`. A recorded
run additionally uses `--headless --case W --duration 45 --output artifacts/run.json`.
The renderer, sensors, full articulation and motors run normally; yaw is applied
only to the complete initial state before the first physics tick.


## Placement variation training: trial 011 / packaged descent60

Trial 011 continues from 010, changes the training tread to 160 mm, and samples
initial yaw within ±0.12 rad and start distance within ±80 mm. It completed
5,816,320 steps in 300.39 seconds on GB10, with two CPU threads. Robot geometry,
actuator torque limits and acceptance criteria are unchanged.

At the trained 0.08 m/s command, **all 15 full-MuJoCo and all 15 Godot descent
regressions pass**, including both previously failing narrow-tread start
angles. Nominal 60 mm Godot descent completes in 16.48 simulated seconds. The
cases have been used in development, so they are not described as untouched
holdouts. No loaded stairs or camera-based terrain reconstruction is claimed.
See [complete results](../../evidence/stairs-011-descent-placement.json).

Alpha.3 bundles this actor as `--stair-skill descent60`, with matching crouch,
phase and route-steering settings. `--stair-skill ascent60` bundles trial 008
and its earlier nominal-course result. Both remain explicit experimental
options; `stairs-dev40` remains the default. Trial 010 and its failed controller
diagnostics remain available for reproducibility.
