"""Verify the editable-mesh gate catches useful topology failures."""

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/diagnostics/check_goose_editable_quad_mesh.py"
SPEC = importlib.util.spec_from_file_location("goose_quad_check", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


CUBE = """\
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
f 4 3 2 1
f 5 6 7 8
f 1 2 6 5
f 2 3 7 6
f 3 4 8 7
f 4 1 5 8
"""


def test_closed_quad_shell_passes(tmp_path: Path) -> None:
    source = tmp_path / "cube.obj"
    source.write_text(CUBE, encoding="utf-8")
    result = MODULE.inspect_obj(source)
    assert result["passed"]
    assert result["connected_components"] == 1


def test_triangle_and_open_shell_fail(tmp_path: Path) -> None:
    source = tmp_path / "broken.obj"
    source.write_text(CUBE.replace("f 4 3 2 1", "f 4 3 2"), encoding="utf-8")
    result = MODULE.inspect_obj(source)
    assert not result["passed"]
    assert result["face_sides"]["3"] == 1
    assert result["open_edges"] > 0


def test_reversed_quad_fails_winding(tmp_path: Path) -> None:
    source = tmp_path / "reversed.obj"
    source.write_text(CUBE.replace("f 5 6 7 8", "f 8 7 6 5"), encoding="utf-8")
    result = MODULE.inspect_obj(source)
    assert not result["passed"]
    assert result["winding_conflicts"] == 4
