from pathlib import Path

import pytest

from app.config.settings import settings
from app.tools.compiler import compile_project
from app.tools.detect import gcc_installed, make_installed
from app.workspace.manager import create_project, project_root


@pytest.mark.skipif(
    not gcc_installed() or not make_installed(),
    reason="ARM GCC or make not installed",
)
def test_create_project_make(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    meta = create_project("golden-led")
    result = compile_project(project_root(meta["id"]))
    assert result["success"], result.get("combined", "")[-2000:]
    root = project_root(meta["id"])
    assert (root / "firmware.elf").is_file()
    assert (root / "firmware.hex").is_file()
    assert (root / "firmware.bin").is_file()
