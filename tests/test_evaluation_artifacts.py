"""Evaluation must not rewrite assets that will be bundled for deployment."""
import hashlib
from pathlib import Path
import subprocess
import sys

import mujoco
import pytest

from sai_agent.paths import model_root


@pytest.mark.parametrize("robot_id", ["Sai_Agent_001", "Sai_Agent_002"])
def test_full_evaluation_keeps_owned_models_unchanged(tmp_path, robot_id):
    root = Path(__file__).resolve().parents[1]
    models = model_root(robot_id, root)
    before = {p.relative_to(models): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in models.rglob("*") if p.is_file()}
    run = subprocess.run([
        sys.executable, str(root / "scripts/evaluation/evaluate_flat.py"),
        "--robot", robot_id, "--policy", str(root / "shared/policies/flat-v1.onnx"),
        "--full-robot", "--out", str(tmp_path), "--require-pass",
    ], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    after = {p.relative_to(models): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in models.rglob("*") if p.is_file()}
    assert after == before, "Evaluation modified the deployment model directory"
    scene = tmp_path / "locomotion_articulated.xml"
    assert scene.is_file(), "Generated evaluation scenes belong with run artifacts"
    assert mujoco.MjModel.from_xml_path(str(scene)).nu == (23 if robot_id.endswith("001") else 22)
