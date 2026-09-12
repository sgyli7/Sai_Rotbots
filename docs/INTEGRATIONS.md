# Game integrations

The model is shared as a version-pinned Python package containing the original
MJCF articulation, public display/contact assets and policy weights. Neither
integration replaces the existing MicroDuck default.

## Godot

In [MicroDuck-Godot-Simi2Sim](https://github.com/sgyli7/MicroDuck-Godot-Simi2Sim):

```sh
uv sync --extra sai
uv run sim2sim-play --robot Sai_Agent_001
```

Use Python 3.12 and Godot 4.7.2. The optional dependency pins an exact Sai source
commit; inspect that project's `pyproject.toml` for the currently selected
version. The launcher imports GLBs and starts the local policy service itself.
It supports the dedicated Sai scene; MicroDuck forest presets are not yet a
drop-in terrain conversion for this robot.

The initial integration was checked by a fresh remote package install, actual
Godot W key input and all 38 existing MD input tests. Dedicated Sai acceptance
also covers S/A/D/Shift, continuous 20/40 mm stairs and the cargo task. Those are
separate tests, not claims that every MD scene or user PC has been verified.

## Unity / Tuanjie

[Integration PR #3](https://github.com/sgyli7/MicroDuck-Unity-Sim2Sim/pull/3)
contains `scripts/setup-sai-agent.py`, the native-model controller, display
import and the `SaiAgent001/Build Demo` editor menu.

```sh
python scripts/setup-sai-agent.py
```

Then open the existing Tuanjie project, run **SaiAgent001 → Build Demo**, and
enter Play mode. The adapter uses the original articulated native MuJoCo model
directly and the exported ONNX actor. W/S drive, A/D turn, held Shift crouches,
and R resets the native model. The display wrapper uses the blue shell and
SO101 meshes while preserving all collision and inertial data.

The setup script fetched and installed the pinned GitHub assets. The C# control
contract passed 64 randomized Python fixtures under .NET 8, with maximum
absolute difference below 3.9e-7. **Unity/Tuanjie editor execution has not been
tested on this Linux ARM workstation, which has no supported editor installed.**
This PR remains a draft. Barracuda execution, scene rendering, input acceptance,
stairs and cargo in Unity still need editor-side verification and completion;
the Godot evidence does not establish them.

## Physics and sensing

Godot/Jolt advances its own rigid bodies; Python uses MuJoCo only for FK and
gravity bias. Unity's adapter advances native MuJoCo and only synchronizes
display transforms. No engine drives the robot by setting the chassis pose.
The terrain observations are simulation height queries/rays. Camera images are
rendered but are not the source of those heights or a trained VLA policy.
