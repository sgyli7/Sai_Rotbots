"""Fail-closed independent release gate for the goose_v02_005_exterior_roles_v1 collision derivative."""
import json
from .closeout_native50 import LITE_RUNTIME_REQUIREMENTS, _source

def validate_lite_contract(contract, root):
    metadata = contract["closeout_native50"]
    lite = metadata["contact_lite"]
    if (metadata.get("runtime_requirements") != LITE_RUNTIME_REQUIREMENTS
            or "production_adoption" in metadata or "production_profile" in metadata
            or lite.get("scope") != "goose005_exterior_roles_two_or_thirty_two_world_standing"):
        raise ValueError("Collision-lite parent, runtime or scope mismatch")
    if not contract.get("training_ready", False):
        return
    if not (root / lite["validation_receipt"]["path"]).exists():
        return
    ref = _source(lite["validation_receipt"], "collision-lite validation", root)
    receipt = json.loads(ref.read_text())
    if (receipt.get("passed") is not True or receipt.get("model_sha256") != contract["model_sha256"]
            or any(value is not True for value in receipt["checks"].values())):
        raise ValueError("Collision-lite validation does not qualify this plant")
