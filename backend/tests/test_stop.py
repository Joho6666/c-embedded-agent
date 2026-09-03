import asyncio

from app.agent.runtime import RUNS, AgentRun, request_stop


def test_stop_cancels_task_and_blocks_further_emits():
    async def _run() -> None:
        run = AgentRun("run-stop", "proj", "stop me", "auto")
        RUNS[run.id] = run
        wrote = {"n": 0}

        async def worker(r: AgentRun) -> None:
            try:
                await asyncio.sleep(30)
                r.emit(type="file_diff", title="should not write", original="", proposed="x")
                wrote["n"] += 1
            except asyncio.CancelledError:
                r.status = "cancelled"
                raise

        run.task = asyncio.create_task(worker(run))
        await asyncio.sleep(0.05)
        await request_stop(run)
        assert run.status == "cancelled"
        assert run.task.done()
        assert wrote["n"] == 0
        types = [e["type"] for e in run.events]
        assert "run_stopped" in types
        assert "file_diff" not in types

    asyncio.run(_run())
