import asyncio
import json
from pathlib import Path

from app.agent import runtime
from app.agent.runtime import RUNS, AgentRun, event_stream


def _events(chunks: list[str]) -> list[dict]:
    out = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                out.append(json.loads(line[len("data: "):]))
    return out


async def _collect(run_id: str, last_event_id: str | None = None) -> list[dict]:
    return _events([chunk async for chunk in event_stream(run_id, last_event_id)])


def test_sse_no_duplicate():
    test_sse_event_id_once()


def test_sse_event_id_once():
    async def _run() -> None:
        run = AgentRun("run-sse", "proj", "sse", "auto")
        RUNS[run.id] = run
        run.emit(type="reasoning", title="one")
        run.emit(type="reasoning", title="two")
        run.close()

        chunks = [chunk async for chunk in event_stream(run.id)]
        ids = [ev["id"] for ev in _events(chunks)]
        assert len(ids) == 2
        assert len(set(ids)) == 2
        # Every frame carries an SSE id so EventSource can send Last-Event-ID.
        assert all(chunk.startswith(f"id: {ev_id}\n") for chunk, ev_id in zip(chunks, ids))

    asyncio.run(_run())


def test_sse_fans_out_to_every_subscriber():
    async def _run() -> None:
        run = AgentRun("run-fanout", "proj", "fanout", "auto")
        RUNS[run.id] = run
        first = asyncio.create_task(_collect(run.id))
        second = asyncio.create_task(_collect(run.id))
        await asyncio.sleep(0)
        run.emit(type="reasoning", title="one")
        run.emit(type="reasoning", title="two")
        run.close()
        a, b = await asyncio.wait_for(asyncio.gather(first, second), timeout=2)
        assert [e["title"] for e in a] == [e["title"] for e in b] == ["one", "two"]

    asyncio.run(_run())


def test_sse_replays_after_last_event_id_and_ends_for_closed_run():
    async def _run() -> None:
        run = AgentRun("run-replay", "proj", "replay", "auto")
        RUNS[run.id] = run
        for title in ("one", "two", "three"):
            run.emit(type="reasoning", title=title)
        run.close()
        full = await asyncio.wait_for(_collect(run.id), timeout=2)
        resumed = await asyncio.wait_for(_collect(run.id, full[0]["id"]), timeout=2)
        assert [e["title"] for e in resumed] == ["two", "three"]
        # An unknown id (e.g. from a previous process) replays everything.
        assert len(await asyncio.wait_for(_collect(run.id, "stale-id"), timeout=2)) == 3

    asyncio.run(_run())


def test_run_agent_always_ends_with_run_finished(tmp_path: Path, monkeypatch):
    async def _run() -> None:
        class Resolution:
            status = "unsupported"
            reason = "no adapter"
            adapter = None

        class Registry:
            def detect(self, root):
                return Resolution()

        monkeypatch.setattr(runtime, "project_root", lambda project_id: tmp_path)
        monkeypatch.setattr(runtime, "default_registry", lambda root: Registry())
        monkeypatch.setattr(runtime, "snapshot", lambda root, message: "abc")
        monkeypatch.setattr(runtime, "save_run", lambda *a, **k: None)
        monkeypatch.setattr(runtime, "finish_run", lambda *a, **k: None)
        monkeypatch.setattr(runtime, "save_event", lambda *a, **k: None)

        run = AgentRun("run-finished", "proj", "x", "auto")
        RUNS[run.id] = run
        stream = asyncio.create_task(_collect(run.id))
        await asyncio.sleep(0)
        await runtime.run_agent(run)
        events = await asyncio.wait_for(stream, timeout=2)
        assert events[-1]["type"] == "run_finished"
        assert events[-1]["status"] == "failed"
        assert run.closed

    asyncio.run(_run())
