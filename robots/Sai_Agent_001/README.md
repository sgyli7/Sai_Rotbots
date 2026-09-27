# Sai_Agent_001

Preserved powered-clamp variant. It remains the default robot.
Its model data is unchanged by the directory migration; no 002 geometry is
substituted into 001. The catalog maps its stable ID to [`models/`](models).

| Material | Entry |
|---|---|
| Simulation and historical acceptance | [Simulation guide](design/simulation_guide.md) |
| Design and implementation record | [Implementation plan](design/implementation_plan.md) |
| Physical cargo task | [Cargo task](design/cargo_task.md) |
| Geometry and appearance concepts | [Concept study](design/concepts/design_presentation.md) |
| Open-source scope and missing hardware/CAD | [Scope and limitations](design/open_source_status.md) |
| Actual model and simulation images | [Images](images) |
| Frozen models and asset provenance | [Models](models) |
| Robot-specific verification | [Evidence](evidence) |
| Shared deployed policies | [Shared policies](../../shared/policies) |
| Historical experimental profiles | [Stair experiments](../../experiments/Sai_Agent_001/stair_profiles) |

Hardware has not been built or calibrated. The public clone contains audited
simulation assets, not the complete editable manufacturing CAD used historically.
Missing original design inputs remain documented rather than reconstructed
from presentation images.

From the repository root: `uv run sai-agent godot --robot Sai_Agent_001`.
