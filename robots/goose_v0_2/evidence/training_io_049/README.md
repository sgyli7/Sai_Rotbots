# Candidate15 physical training I/O acceptance

The framework-neutral `GooseTrainingIO` loads and verifies the frozen runtime ZIP, exposes NumPy actions/state and optional RGB, and records language/RGB/proprio/action chunks. It does not implement rewards, episode termination, a learning algorithm or policy migration. Existing candidate15 source physics and motor limits remain authoritative. Legacy08 jaw-coordinate policies are incompatible with motor-input axis5.

```python
from sai_agent.goose_training_io import GooseTrainingIO
io = GooseTrainingIO(
    "robots/goose_v0_2/evidence/hardware_closeout_040/candidate15/candidate15_runtime_only.zip",
    expected_manifest_sha256="41ee30e7eeb004986daa9ee55d67c4ae74b638615bb2c29f6dcc3c314197df89",
)
proprio, state = io.reset()
# Keep the pre-action observation for a rollout; action is a finite NumPy [18].
proprio_after, state_after = io.step(action)
rgb = io.rgb()  # same actual state, 240x320 RGB uint8
io.close()
```

The source package handles normalized clipping, physical ROM/reference slew, 200 Hz torque-speed/power limiting and 2 kHz integration. Each public step advances exactly20 ms. Errors propagate with the actual terminal state retained; there is no automatic reset or invisible support. RGB is a declared simulator debug viewpoint, not an onboard-camera calibration. Exact world camera axes/positions and frustum are in `sample_schema.json`.

The bounded smoke completed two explicit resets and100 small deterministic actions (2 simulated seconds total), with nonzero articulated motion, finite observations, actual effort caps, zero applied hidden forces and maximum loop residual0.0871 µm. The same-state RGB and a language/proprio/action-chunk record were read back, as was the actual state-action trajectory. No PPO update, GPU training, reward change, task-success or learning-convergence test occurred. Rendering and trace readback after the smoke did not advance time.

Re-run only when deliberately allocating another physical check:

```bash
python scripts/evaluation/check_goose_training_io_049.py \
  --zip robots/goose_v0_2/evidence/hardware_closeout_040/candidate15/candidate15_runtime_only.zip \
  --out artifacts/goose_v0_2/training_io_049/new_smoke \
  --evidence robots/goose_v0_2/evidence/training_io_049/new_smoke
```

Runtime dependencies are NumPy and MuJoCo3.10; the check additionally uses Pillow for the selected PNG. There is no Gym/RSL/LeRobot dependency. Raw state-action arrays and the sample NPZ remain in the receipt's artifacts directory rather than Git.

## Latest aligned acceptance: smoke002

The original smoke001 artifacts, selected receipt and exact executed source snapshots are retained. They tested proposed-chunk serialization only. Latest acceptance is `smoke_002/receipt.json` and `smoke_002/execution_receipt.json`: immediately before the second episode’s last four actions (actual time0.92 s), the checker captured same-state RGB/proprio/q/qdot and the exact next4 deterministic actions. Those actions were executed within the same100-step budget. Command times are0.92/0.94/0.96/0.98 s and poststate times0.94/0.96/0.98/1.00 s. Exact action equality and pre/post timestamps are verified. Every raw trajectory row now explicitly includes observation_before/time_before and observation_after/time_after. This is physically executed alignment evidence, not just an unexecuted instruction sample; it does not establish BC task quality.
