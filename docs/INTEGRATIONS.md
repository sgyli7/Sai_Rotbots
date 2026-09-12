# Game integrations

## Robot family update

The core repository is now [Sai_Rotbots](https://github.com/sgyli7/Sai_Rotbots).
001 remains the default. With the new family package, select
`uv run sai-agent godot --robot Sai_Agent_002` or add `--task cargo`.
The existing external Godot and Unity source pins still identify 001 alpha.3;
renaming preserves their old GitHub URLs through redirects. Do not infer 002
support in an old integration checkout merely from the repository rename.
The 002 bundle provides its own MJCF, JSON physical specification and Y-up GLBs.


The model is shared as a version-pinned Python package containing the original
MJCF articulation, public display/contact assets and policy weights. Neither
integration replaces the existing MicroDuck default.

## Godot

In [MicroDuck-Godot-Simi2Sim](https://github.com/sgyli7/MicroDuck-Godot-Simi2Sim):

```sh
uv sync --extra sai
uv run --extra sai sim2sim-play --robot Sai_Agent_001
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
Until the draft PR is merged, use its preview branch in a separate checkout:

```sh
git clone --branch feat/sai-agent-001 --single-branch https://github.com/sgyli7/MicroDuck-Unity-Sim2Sim.git Sai-Unity-preview
cd Sai-Unity-preview
python scripts/setup-sai-agent.py
```

Then open the existing Tuanjie project, run **SaiAgent001 → Build Demo**, and
enter Play mode. The adapter uses the original articulated native MuJoCo model
directly and the exported ONNX actor. W/S drive, A/D turn, held Shift crouches,
and R resets the native model. The display wrapper uses the blue shell and
SO101 meshes while preserving all collision and inertial data.

**SaiAgent001 → Build Stairs** creates separate four-riser 20/40 mm ascent and
descent scenes. The controller uses 24 terrain-only rays, both frozen actors
and the same bounded heading control as the Godot adapter.

The setup script fetched and installed the pinned GitHub assets. The C# control
contract passed 64 flat plus 160 stair/heading Python fixtures under .NET 8;
maximum absolute difference is below 4.2e-7. The expanded suite now covers
384 total formula cases. More importantly, the actual shared
`SaiNativeWorld` source passes eight movement/crouch/reset cases and four stair
cases with MuJoCo 3.12.0 and ONNX Runtime 1.24.4. These passed on Linux ARM64 and
in [Linux/Windows CI](https://github.com/sgyli7/MicroDuck-Unity-Sim2Sim/actions/runs/34680834372).
The Windows run loads the actual project-bundled DLL with its locked SHA-256.
The tests advance real native physics, not prescribed robot poses. The same
C# source now also passes nominal 60 mm up/down locally, using the separately
paired ascent60/descent60 settings. The editor menu exposes those under
**Build Experimental Stairs**. The compact
record is [unity-native-physics.json](../evidence/unity-native-physics.json).

**Unity/Tuanjie editor execution has not been tested on this Linux ARM workstation,
which has no supported editor installed.** The PR remains a draft. A real editor
entry point is now prepared:

```sh
python scripts/run-sai-editor-acceptance.py --editor "/absolute/path/to/editor"
```

Add `--build-windows` on a host with the Windows build module to run that
acceptance first and then build the player. The helper checks a fresh completion
marker, executable and locked native DLL, and writes a file/hash manifest.
This preparation passed Linux/Windows CI at integration commit `f38bd3c`;
the editor build and player execution themselves have not run here.

It imports the real ONNX assets and runs the same physical acceptance suite via
the gameplay Barracuda wrapper, writing an explicit editor report. It has not
yet been executed here. Keyboard input and rendering additionally need Play
acceptance. Cargo pickup/transport has not yet been ported to this Unity demo;
the working Godot task does not establish Unity task support.

## Physics and sensing

Godot/Jolt advances its own rigid bodies; Python uses MuJoCo only for FK and
gravity bias. Unity's adapter advances native MuJoCo and only synchronizes
display transforms. No engine drives the robot by setting the chassis pose.
The terrain observations are simulation height queries/rays. Camera images are
rendered but are not the source of those heights or a trained VLA policy.


Alpha.3 is [released](https://github.com/sgyli7/Sai_Agent_001/releases/tag/v0.1.0-alpha.3).
Godot [PR #4](https://github.com/sgyli7/MicroDuck-Godot-Simi2Sim/pull/4) is merged
with the new exact source pin. Unity's twelve base plus two experimental cases
also pass [Linux/Windows CI](https://github.com/sgyli7/MicroDuck-Unity-Sim2Sim/actions/runs/34685536330).
Editor acceptance remains pending; the repeated lack of an editor host cannot
be resolved by more native-console tests.
