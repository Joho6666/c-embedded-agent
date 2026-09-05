from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.workspace.manager import create_project, project_root


client = TestClient(app)


def test_project_id_cannot_escape_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    for project_id in ("..", "../outside", "..\\outside", "a/b"):
        try:
            project_root(project_id)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError(f"unsafe project id accepted: {project_id}")


def test_import_ioc_strips_directory_components(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    response = client.post(
        "/api/projects/import-ioc",
        json={"content": "Mcu.Name=STM32F103C8Tx", "filename": "../safe.ioc", "name": "safe"},
    )
    assert response.status_code == 200
    root = project_root(response.json()["projectId"])
    assert (root / "safe.ioc").is_file()
    assert not (tmp_path / "safe.ioc").is_file()


def test_http_file_write_keeps_protected_paths_protected(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_root", tmp_path)
    meta = create_project("protected")
    response = client.put(
        f"/api/projects/{meta['id']}/file",
        json={"path": "Makefile", "content": "unsafe"},
    )
    assert response.status_code == 400
    assert "protected" in response.json()["detail"]
