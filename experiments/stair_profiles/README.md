# Experimental 60 mm profiles

These are development profiles, not replacements for `stairs-dev40` or part of
the alpha.2 release. The two ONNX files are exported from the already-recorded
GPU trials 008 and 006; their JSON files retain training metadata and actor
hashes. No new training is claimed for the controller diagnostics below.

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
