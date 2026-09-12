# Changelog

## 0.1.0a2 — simulation preview

- Packaged the physical 100 g SO101 pickup, cargo securing and loaded crawl task
  with public assets and no object attachments. MuJoCo and Godot pass 18/25 mm
  obstacle courses and no-clamp negative controls.
- Added R restart for the entire Godot scene/controller and fixed the observed
  visible-window VSync throttle without changing physics.
- Retained the validated WASD/held-Shift flat actor and 20/40 mm stair actor.
  Trials 006–009 did not replace them; 60 mm remains unpassed. Raw full-model
  tread/yaw holdouts passed 14/16. A paired check with the already deployed
  heading layer passed 15/16; one descent still leaves the lateral corridor.
- Updated the existing Godot project's optional profile; fresh GitHub install
  and cargo launch pass, alongside 38 original MD input tests.
- Added Ubuntu x86 CI for installation, physical regressions and wheel build.
  Included front/rear CAD-constrained material studies and actual game views.
- Unity asset setup and the portable C# contract have passing checks in draft
  PR #3. Actual editor/runtime and Unity stair/cargo acceptance remain pending.

Hardware manufacture, measured physical parameters, touchscreen firmware and
camera-based VLA are not part of this simulation preview's validated scope.
