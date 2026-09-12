# Sai_Agent_001 implementation and acceptance

The full user objective is WASD movement, held Shift crouch, ascending and descending continuous stairs, GPU-first training, out-of-box use by the existing Unity and Godot projects, and a public GitHub repository named Sai_Agent_001. Passing an intermediate demo does not complete this objective.

## Fixed decisions

- Preserve the approved front SO101, open blue rear cargo, four independently actuated wheel-legs, cameras and rear touchscreen. Use existing CAD frames, source-derived inertias and labelled approximations. No morphology search.
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

- Public development repository: https://github.com/sgyli7/Sai_Agent_001.
- Flat policy passes eight cases in reduced and articulated CPU MuJoCo; a fresh
  package environment also passes. Godot/Jolt passes actual W/S/A/D/Shift input
  events with all 26 robot bodies, 23 hinges and two cargo sliders retained.
- Godot uses a bounded heading feedback loop to reduce solver-transfer yaw drift.
  It changes wheel speeds only. Exact results are in evidence/godot-flat.json.
- Stair trial 004 passes four-riser 20/40 mm ascent and descent in reduced CPU
  MuJoCo. The same 20/40 mm cases also pass with full MuJoCo articulation and
  in Godot/Jolt. 60 mm remains outstanding. Full-model tread/alignment holdouts
  passed 14/16; two descending cases exceeded the lateral corridor. These cases
  retain their original results and are not reclassified as training successes.
  Trial 005 failed with captured non-finite GPU
  physics; replay isolated the previous acceleration initial guess as the trigger.
  Clearing that numerical guess passed 1,280 captured-contact replays and three
  subsequent five-minute GPU trials (006–008) without non-finite states. Their
  policies regressed existing cases and have not replaced trial 004.
  Trial 009 then encountered a new non-finite state at 157 seconds; the earlier
  replay fix is scoped to that captured trigger, not a general stability claim.
- Legal display assets and notices are published. Explicit GLB normals improve
  rendering without changing contact meshes, inertias or joints.
- Unity draft PR #3 now has the native MJCF/ONNX adapter. Its 82D observation and
  mixed target formulas match 64 Python fixtures in actual .NET execution, but
  the Unity editor is not installed on this Linux ARM machine; editor/runtime
  acceptance is not yet available.
- Godot project profile PR #2 is merged. A fresh GitHub dependency install ran
  the real W input case; the existing 38 MD input tests also passed. The cargo
  extension has also been installed from GitHub commit 6eb18b2 and completed
  the same cargo task through the existing project entry point (merged PR #3).
- Public assets now run the preserved 100 g pickup/clamp/crawl task in both
  MuJoCo and Godot at 18/25 mm obstacles. Each engine's no-clamp negative control
  placed the item but correctly prevented transport. This remains a separate
  frozen 57D crawl task, not the new 82D command policy or camera-based VLA.
- R restart resets both the physics scene and controller; real Godot key-event
  regression passed. Visible VSync throttling was isolated and removed while
  keeping the physics configuration unchanged. Visible W also passed.
- GitHub Actions on Ubuntu x86 passed package installation, contract tests,
  full-articulated flat/20–40 mm stair/cargo tests and the no-clamp control.
- The 0.1.0a2 simulation prerelease packages the verified subset. Unity editor acceptance,
  full 60 mm stair acceptance, and hardware/VLA milestones remain explicit gaps.

The full user objective remains active; this is not a final release checklist.
