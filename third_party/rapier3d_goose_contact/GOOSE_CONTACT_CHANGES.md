# Goose contact variant

Baseline: the existing Sai_Lab/Bevy_Sim2Sim Rapier 0.35.3 fork, including its
read-only observation and explicit physical-normal-contact facilities. Published
crate provenance and Apache-2.0 license remain in UPSTREAM_SOURCE.json and LICENSE.
The published crate's git SHA alone is not an exact identity (its metadata says
`dirty=true`). LOCAL_CHANGES.md describes the inherited fork changes.

This variant adds only the opt-in `sim2sim-physical-friction-contact` feature:

- It enables the already implemented physical normal-spring row with the native
  Coulomb tangent solver for articulated non-bouncy contacts. The old feature's
  frictionless guard is unchanged when this new feature is disabled.
- After a free multibody root's rotation increment, it normalizes quaternion
  scale to maintain SO(3) under f32 arithmetic. It does not project position,
  velocity, contacts, or the robot toward a desired pose.

The caller supplies K/C divided among actual sole manifold points. The standalone
Goose receiver opts in explicitly and verifies its new plant/control identity.
Production Sai_Lab code and its condensed-model rejection guard are unchanged.
Qualification is limited to the recorded M0 profiles and the load/friction
fixtures. It does not certify arbitrary contacts, terrain, policies or material.
