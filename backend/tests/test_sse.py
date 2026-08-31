import asyncio

from app.agent.runtime import RUNS, AgentRun, event_stream


def test_sse_event_id_once():
    async def _run() -> None:
        run = AgentRun("run-sse", "proj", "sse", "auto")
        RUNS[run.id] = run
        run.emit(type="reasoning", title="one")
        run.emit(type="reasoning", title="two")
        run.queue.put_nowait(None)

        chunks: list[str] = []
        async for chunk in event_stream(run.id):
            chunks.append(chunk)

        ids = []
        for c in chunks:
            marker = '"id": "'
            if marker in c:
                start = c.find(marker) + len(marker)
                ids.append(c[start : start + 10])
        assert len(ids) == 2
        assert len(set(ids)) == 2

    asyncio.run(_run())
