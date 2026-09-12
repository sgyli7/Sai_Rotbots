# Sai_Agent_001 implementation and acceptance

The full user objective is WASD movement, held Shift crouch, ascending and descending continuous stairs, GPU-first training, out-of-box use by the existing Unity and Godot projects, and a public GitHub repository named Sai_Agent_001. Passing an intermediate demo does not complete this objective.

## Fixed decisions

- Preserve the approved front SO101, open blue rear cargo, four independently actuated wheel-legs, cameras and rear touchscreen. Use existing CAD frames, measured/source inertias and labelled approximations. No morphology search.
- W/S = signed forward velocity; A/D = signed yaw rate; held Shift = lower body-height target, release = return to normal. Train zero input, reverse, turning in place, simultaneous move/turn, crouched movement and transitions.
- Use the existing local CUDA PyTorch + MuJoCo Warp stack without modifying other projects' environments. Limit PyTorch/BLAS CPU threads to two; benchmark GPU physics and learning, record actual device and timing. Keep compilation distinct from training budgets.
- Stairs initially use command-conditioned RL and local terrain sensing. A language model is not required to solve low-level stair contacts. Sensor assumptions and deployment mappings must be explicit.
- The initial staircase target suite contains separate ascent/descent flights with four consecutive risers of 20, 40 and 60 mm, nominal 180 mm tread and 1 m width. Training may use a curriculum; no single bump substitutes for a staircase, and no untested height is reported as passed. Direction, tread variation and initial alignment holdouts are separate from tuning cases.
- Existing 100 g grasp/cargo/transport remains a regression requirement; new locomotion must also be checked on the articulated full robot, not only a training surrogate.

## Work packages

1. Build a versioned model/control package and GPU smoke test. Pin names, frames, actuator modes, model/observation hashes and approximations. Preserve full-articulation source and trace any fixed-arm locomotion reduction.
2. Train and evaluate commanded movement + crouch. Export ONNX with exact observation preprocessing and mixed position/velocity control semantics. Rehearse in CPU MuJoCo.
3. Train stair ascent/descent and transitions using a fixed trial/holdout suite. Record physical contact/progress, upright state, all wheel clearance, height, velocity tracking and failures, not reward alone.
4. Integrate the same package/version in existing Godot/Jolt and Unity/native-MuJoCo projects. Include input, reset, sensors, state/command adapters, mesh loading and runtime dependencies. Verify old MD compatibility and new robot tasks.
5. Publish source, permitted assets, weights, startup instructions, tested install path and evidence to sgyli7/Sai_Agent_001. Validate the remotely fetched package. Unresolved asset licensing cannot be covered by a blanket software license.

## Experiment loop

Inspired by [autoresearch](https://github.com/karpathy/autoresearch): fixed evaluation, bounded GPU trials, one named hypothesis per trial, source/config/seed/checkpoint hashes, keep/discard/failure ledger. The LLM-training code and its indefinite-loop instructions are not imported as project rules.

Start with 64 parallel worlds and a short smoke run. Baseline throughput and physics stability are checked before five-minute training trials. Tune on the development suite; use held-out stair parameters only for acceptance, not reward tuning. A failed experiment does not replace the last working policy. Runtime and training contracts must remain aligned.

## Completion evidence

- Recorded input events cause W/S travel, A/D turning, Shift lowering and release recovery in both delivered game integrations.
- Ascent and descent each finish real multi-step flights under the stated suite, with no object/base pose forcing and no hidden physical supports.
- GPU physics/training activity and bounded CPU usage are measured; model and full-robot transfer results are retained.
- Fresh install/startup from the published package works for both project paths; required dependencies are documented or bundled as legally permitted.
- GitHub source/tag/release exists and matches verified local content. Current development checks alone are not release evidence.

## Current status

The GB10 GPU backend and PPO run with two CPU threads. The final flat candidate
passes eight command/crouch cases in both the 16-actuator reduced model and the
23-actuator articulated model. Zero input has an explicit physical braking/IK
mode. See evidence/flat-reduced.json and evidence/flat-articulated.json.

Public display assets have been generated with licenses and per-part provenance.
Unknown vendor CAD is replaced by independent dimensional envelopes; physical
model invariance passes. Display-only simplification reduces GLB data to about
31 MB; no contact meshes or inertia values are simplified.

Stair work remains experimental: four 20 mm descending risers passed in one
development case; ascent and the complete 20/40/60 mm suite have not passed.
Lane exits now terminate training episodes. A late non-finite state in the
second stair trial is under reproduction with state capture and checkpoints.

Unity integration has a focused branch and draft PR (#3). Godot integration has
an isolated branch, preserving another task's ongoing local edits. Their runtime
adapters, end-to-end acceptance and public Sai_Agent_001 repository/release remain
outstanding. The full user objective is still active.
