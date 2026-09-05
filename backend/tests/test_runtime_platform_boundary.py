from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

from app.agent import runtime
from app.platforms.base import DetectionEvidence, PlatformAdapter, PlatformDescriptor, PlatformResult


class RecordingAdapter(PlatformAdapter):
    descriptor = PlatformDescriptor("recording", "Recording", "TEST", "TEST1", "SDK", "ready")

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.task = None

    @property
    def template_path(self) -> Path:
        return self.repo_root

    def detect_project(self, root: Path) -> DetectionEvidence:
        return DetectionEvidence(self.adapter_id, True, 1.0)

    def create_template(self, destination: Path, *, name: str, board=None, metadata=None) -> PlatformResult:
        return PlatformResult("PASS", "create", self.adapter_id)

    def load_context(self, root: Path) -> dict:
        return {"facts": {"adapterId": self.adapter_id, "mcu": "TEST1"}}

    def toolchain_status(self) -> dict:
        return {"status": "available"}

    def build(self, root: Path) -> PlatformResult:
        return PlatformResult("PASS", "build", self.adapter_id)

    def hardware_run(self, root: Path, **kwargs) -> PlatformResult:
        self.task = kwargs.get("task")
        return PlatformResult.unavailable("hardware-run", self.adapter_id, "no device")


def test_runtime_generic_module_has_no_direct_f103_execution_imports() -> None:
    source = inspect.getsource(runtime)
    assert "from app.mcu.stm32f103" not in source
    assert "from app.tools.compiler" not in source
    assert "from app.tools.flash" not in source
    assert "from app.tools.hardware_run" not in source
    assert "TOOLS = [" not in source


def test_runtime_passes_real_task_to_hardware_adapter(tmp_path: Path) -> None:
    adapter = RecordingAdapter(tmp_path)
    run = runtime.AgentRun("r1", "p1", "validate ADC sampling on device", "auto")
    asyncio.run(runtime._maybe_run_on_device(run, tmp_path, adapter))
    assert adapter.task == run.prompt


def test_run_emits_public_routing_event(tmp_path: Path, monkeypatch) -> None:
    adapter = RecordingAdapter(tmp_path)

    class Resolution:
        status = "resolved"
        reason = None

        def __init__(self):
            self.adapter = adapter

    class Registry:
        def detect(self, root):
            return Resolution()

    async def fake_loop(run, root, selected_adapter, workflow, schemas):
        assert selected_adapter is adapter
        assert schemas
        run.status = "success"

    monkeypatch.setattr(runtime, "project_root", lambda project_id: tmp_path)
    monkeypatch.setattr(runtime, "default_registry", lambda root: Registry())
    monkeypatch.setattr(runtime, "snapshot", lambda root, message: "abc")
    monkeypatch.setattr(runtime, "save_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime, "finish_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime, "_llm_loop", fake_loop)
    run = runtime.AgentRun("r2", "p2", "add gpio output", "auto")
    asyncio.run(runtime.run_agent(run))
    routing = next(event for event in run.events if event["type"] == "routing")
    assert routing["adapterId"] == "recording"
    assert routing["contextLevel"] in {"FOCUSED", "PROJECT", "DEEP"}
    assert routing["classification"]["task_type"] == "feature"
