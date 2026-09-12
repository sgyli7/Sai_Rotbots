# Control contract (development v1)

The robot has sixteen locomotion actuators: FL, FR, RL, RR, each ordered HAA,
hip, knee, wheel. The articulated model additionally retains five SO101 arm
axes, its gripper and the cargo belt drive. Two cargo pads are passive slide
joints coupled to that drive. The object remains free during manipulation.

W/S requests signed body-forward velocity; A/D requests yaw rate. Shift sets a
35 mm lower nominal chassis-height reference, slewed over half a second. Releasing
Shift returns to normal. Zero movement input explicitly commands wheel braking
and analytical standing/crouch IK, rather than allowing a residual-policy bias to
move the vehicle. This uses bounded motor torque; it does not fix the base pose.

All shared state is SI, right-handed X-forward/Y-left/Z-up. Quaternions are wxyz.
The policy runs at 50 Hz. Wheels use velocity feedback with gain 0.4 and a 1.3 Nm
cap; leg position feedback is 80/2 with an 8 Nm cap. These are simulation settings,
not measured continuous hardware ratings. Full-model arm holding uses the existing
998.22/2.731 settings, gravity feedforward and 2.94 Nm (1.4 Nm gripper) caps.

The ONNX actor takes one float32 `obs` tensor, shape [batch,82], and returns one
`actions` tensor, shape [batch,16]. Observation normalization is inside the model.
Never normalize it a second time. The deterministic actor outputs are clipped to
[-1,1] before reference construction and filtered to zero on a stop command.

| Slice | Meaning |
|---|---|
| 0:3 | World up expressed in body coordinates |
| 3:6 | Body linear velocity |
| 6:9 | Body angular velocity |
| 9:12 | Forward command, yaw command, current slewed crouch fraction |
| 12:24 | Twelve leg joint positions in manifest order, excluding wheels |
| 24:36 | Twelve leg velocities × 0.1 |
| 36:40 | Four wheel velocities × side sign × 0.1 |
| 40:56 | Previous applied/filtered action |
| 56:58 | sin/cos reference phase; flat 2.4 s, stair reference 3.2 s |
| 58:82 | 24 local height samples, transformed by the rule below |

The sampling grid has x = [-0.36,-0.18,0,0.18,0.36,0.54,0.72,0.90] and
y = [-0.24,0,0.24] metres, x-major order, aligned to body yaw. Each sample is
`clip(5*(ground_height - (base_z - 0.2192)), -2, 2)`.
The simulation height field is an explicit privileged terrain sensor. A camera
depth/height reconstruction backend has not been implemented or validated;
the package does not claim RGB-only/VLA stair navigation or real-hardware transfer.

Flat reference and the experimental stair gait are in `src/sai_agent/control.py`.
They have different phase/reference semantics even though their tensor sizes match;
a stair actor must not be loaded into a flat controller solely because the shapes fit.
The policy must be selected by its contract identifier and hash.
