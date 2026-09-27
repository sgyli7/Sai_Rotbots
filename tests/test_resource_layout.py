"""Resource discovery must work in both robot-organized source and wheels."""
import json
from pathlib import Path

import pytest

from sai_agent import paths
from sai_agent.cli import prepare_godot


@pytest.mark.parametrize("bundled", [False, True], ids=["checkout", "wheel"])
def test_resource_root_uses_robot_catalog_without_root_model(tmp_path, monkeypatch, bundled):
    module = tmp_path / "src" / "sai_agent" / "paths.py"
    root = module.parent / "bundle" if bundled else tmp_path
    (root / "robots").mkdir(parents=True)
    (root / "robots" / "catalog.json").write_text(json.dumps({
        "default_robot": "Sai_Agent_001",
        "robots": {"Sai_Agent_001": {"models": "robots/Sai_Agent_001/models"}},
    }))
    monkeypatch.setattr(paths, "__file__", str(module))
    assert paths.resource_root() == root
    assert paths.model_root(root=root) == root / "robots/Sai_Agent_001/models"


@pytest.mark.parametrize("robot_id", ["Sai_Agent_001", "Sai_Agent_002"])
def test_robot_models_and_godot_export_are_self_contained(tmp_path, robot_id):
    root = Path(__file__).resolve().parents[1]
    models = paths.model_root(robot_id, root)
    assert models == root / "robots" / robot_id / "models"
    project = prepare_godot(root, tmp_path / robot_id, robot_id)
    assert (project / "project.godot").is_file()
    assert (project / "sai_agent/robot.json").read_bytes() == (models / "full/robot.json").read_bytes()
    for asset in (models / "full/assets").glob("*.glb"):
        assert (project / "sai_agent/assets" / asset.name).read_bytes() == asset.read_bytes()


def test_default_robot_and_unknown_robot_remain_compatible(monkeypatch):
    monkeypatch.delenv("SAI_ROBOT_ID", raising=False)
    assert paths.model_root() == paths.model_root("Sai_Agent_001")
    monkeypatch.setenv("SAI_ROBOT_ID", "Sai_Agent_002")
    assert paths.model_root() == paths.model_root("Sai_Agent_002")
    with pytest.raises(ValueError, match="Unknown robot"):
        paths.model_root("unknown")
