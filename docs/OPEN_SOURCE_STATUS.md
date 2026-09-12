# Open-source scope and remaining hardware work

This is a simulation alpha, with reusable model data and control software.
It is not a complete manufacturing kit or a validated hardware controller.
The current model mass is approximately 9.276 kg, including estimated
allocations. That is a model value, not a weighed robot or an MD-sized payload
claim. The physical task evidence covers one 100 g item.

## Compared with the MicroDuck delivery pattern

The reference audit read MicroDuck runtime commit
[`6507d2e`](https://github.com/pollen-robotics/microduck/tree/6507d2e960417aaa4ecd38eccf59b2dcf586ecd2)
and its separate RL project at
[`53b8971`](https://github.com/pollen-robotics/microduck_rl/tree/53b8971b61baf5b7f3c16d135dd7cac37623de4b).
These are fixed source references, not a claim that we independently ran their
robot. Our comparison concerns deliverables, not copying their model or shape.

| Deliverable | Sai current scope | Still needed |
|---|---|---|
| Robot/model contract | Named joints, SI frames, full and training models, actor manifests and hashes | Hardware model revision tied to measurements |
| Training + actor export | Bounded GPU PPO, source snapshots, ONNX with normalizer, fixed evaluations | Reliable 60 mm stairs; broader terrain/loads and actuator randomization |
| Reproducible tasks | WASD/Shift, 20/40 mm four-riser tests, separate physical cargo task | Interactive general picking and loaded stair tasks |
| Game runtime | Godot/Jolt package and merged existing-project entry point | Unity editor acceptance and full task integration |
| Source/asset release | Public code, permitted meshes, policy weights, licenses and provenance | Editable manufacturing CAD package and complete assembly instructions |
| Physical I/O | Candidate interfaces and simulated motor commands | CAN/servo/PWM drivers, IMU/state estimator, timestamped calibrated cameras |
| Maintenance/UI | Rear touchscreen mounting geometry | Touch UI firmware, telemetry, device diagnostics and real operation tests |
| Hardware evidence | Source dimensions plus labelled physical estimates | Weighed mass/inertia, torque/thermal/voltage measurements, joint calibration and fault recovery |

MicroDuck's software and RL model licenses are separately stated upstream. No
MicroDuck geometry or policy weights are copied into this robot package. SO101
and Raspberry Pi derived assets retain their own notices here.

## Existing design choices retained

- Four wheel legs: twelve AK45-36 joint motor candidates and four AK40-10 wheel
  motor candidates. Public display meshes use independently created dimensional
  envelopes for vendor CAD whose redistribution permission was not established.
- Front SO101: its actual six-axis servo chain including the gripper, with the
  frozen upstream source geometry, rather than a generic industrial arm model.
- Open cargo bay: two opposed pads driven through one belt mechanism. Controls,
  transmission and wiring are below/around the bay; simulated payload bounds
  are explicit. This is not a crate placed inside another crate.
- Two nominal camera placements: chassis and wrist. Simulation views have
  recorded frames/FOV assumptions. Package-front coordinates are not measured
  optical centres; lens distortion, focus and hardware calibration are pending.
- Rear Nextion touch display layout remains in the shell. A visible screen mesh
  does not mean its touch application or hardware driver has been implemented.

## Physical parameters and limits

`models/full/robot.json` records body masses/inertias, joints, camera frames and
limitations. Arm inertia comes from the registered upstream model; chassis,
legs and accessory allocations remain estimates. Link-to-link self-collision
is currently disabled and must be enabled and validated before using this
model as a collision-safe planner. Display geometry is not the contact model.

The model's torque limits and gains are simulation controls, not continuous
motor ratings. Power distribution, branch protection, regenerative current,
wiring, actuator thermal limits, calibration and the real load-cell signal path
are unfinished. No released command connects to or enables physical motors.

The public package runs independently of private CAD downloads. The historical
CAD-to-display preparation scripts document the local source pipeline; a fresh
clone consumes the included audited assets. Rebuilding all editable CAD from a
fresh clone is not yet supported. Vendor source links and individual provenance
are in [asset_provenance.json](../models/asset_provenance.json).
