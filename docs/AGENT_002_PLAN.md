# Sai_Agent_002 — flat cargo bay

User scope: preserve Sai_Agent_001; add Sai_Agent_002 by removing the rear
powered moving pads and associated machinery. Preserve the approved blue open
tray, front SO101, four wheel-legs, cameras and rear touchscreen. No new cargo
fixation subsystem. Repository spelling is the user-requested `Sai_Rotbots`.

## Completion checks

- [x] Rename the existing GitHub repository without deleting its history/releases.
- [x] Publish a robot catalog with separate 001/002 models and extensible entries.
- [x] Remove clamp bodies, drive, belt constraints, force-board and dedicated
  cargo servo electronics from 002; restore a flat continuous cargo surface.
- [x] Update mass/COM/inertia estimates, collision shapes and provenance;
  retain the same arm/leg/camera/screen geometry and joint definitions.
- [x] Inspect actual front/top/rear renders against the selected design.
- [x] Enable selection in MuJoCo evaluation/training and standalone Godot.
- [x] Validate 002 locomotion and pickup/transport using physical contact,
  with no dependency on a removed clamp or artificial item attachment.
- [x] Keep 001 regression and old release paths functional.
- [ ] Publish source, robot documentation, reproducible assets and verification.

002 carries unsecured objects on a non-slip floor within the existing walls.
No automatic clamping or guaranteed retention on arbitrary terrain is claimed.
Hardware calibration, touchscreen firmware and Unity editor verification remain
the previously documented project limitations, not new scope for this variant.
