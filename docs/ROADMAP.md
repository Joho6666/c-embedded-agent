# Roadmap: from Engineering Beta to evidence-backed agent

Baseline: `v0.9.1-beta`. This roadmap turns the post-v0.9.1 audit into ordered phases and records
which open-source projects each change borrows from. Nothing here is a claim of completion; each
phase exits only with test or benchmark evidence.

## Phase A — LIVE path correctness (done in `fix/p0-live-path`)

| # | Problem | Fix | Reference |
|---|---|---|---|
| A1 | auto mode rejected `configure_*`, `register_hal_module`, `apply_error_memory_fix` (no `path` argument ⇒ "not a standard path") | `ToolSpec.path_arg`; path-less writes are *adapter-managed* and authorised by mode only | Codex CLI: sandbox scope and approval policy are separate axes |
| A2 | writable directories hard-coded twice (`runtime.py`, `workspace/paths.py`) as STM32 layout; ESP32 `main/` and flat 8051 `main.c` unwritable | `PlatformAdapter.write_scope` (`writable_prefixes`, `writable_root_suffixes`, `protected_paths`) is the single source for runtime, filesystem, patch and the file API | Codex CLI `writable_roots` |
| A3 | LIVE UI stayed "running": backend never sent a terminal event; one shared queue, no replay, EventSource reconnect hung | every run ends with `run_finished` (or `run_stopped`); per-subscriber fan-out; `id:` on every frame; replay after `Last-Event-ID` | AG-UI `RUN_FINISHED`/`RUN_ERROR`; `vercel/resumable-stream` |
| A4 | each knowledge query deleted the whole FTS table, wiping ingested PDFs | incremental markdown sync tracked by FTS rowid in `knowledge_notes`; PDF rows untouched | — |
| A5 | `httpx` errors escaped as generic "Agent 异常", skipping the build fallback | all transport/HTTP/body errors become `LLMError`; 408/409/429/5xx/timeouts retried with backoff and `Retry-After`; fallback status comes from the build result | LiteLLM / openai-python retry semantics |

## Phase B — Runtime robustness

- Run blocking device/analysis calls (`flash`, `serial_sample`, `hardware_run`, clangd, cppcheck) via
  `asyncio.to_thread` or async subprocesses so Stop can cancel them and SSE never stalls.
- Serial/RTT capture ends as soon as `expect` or a fail marker appears instead of a fixed 8 s window
  (`okhsunrog/flashprobe-mcp`).
- Atomic checkpoints (temp file + `os.replace`); on resume, close dangling `tool_calls` with a truthful
  "interrupted, may have partially run" tool message (LangGraph `INVALID_CHAT_HISTORY` guidance; the
  deepagents/EvoScientist lesson that "cancelled" wording makes models replay side effects).
- Context control: mask all but the last N tool observations (OpenHands `ObservationMaskingCondenser`,
  SWE-agent `last_n_observations`; arXiv 2508.21433 finds masking matches LLM summarisation at lower cost).
- Finish the tool registry: bind handlers and drop the `_exec_sync` if/elif chain, enforce `timeout`,
  filter schemas by `adapter_id` so 8051/ESP32 never see STM32 HAL tools.
- Housekeeping: evict finished `RUNS`, one SQLite connection per thread with schema init once, return
  tool-argument JSON errors to the model, build-scoped diagnostic ids.

## Phase C — Evaluation (the main gap)

1. Run `benchmarks/benchmark.py` against DeepSeek (`https://api.deepseek.com`, `deepseek-chat` and
   `deepseek-reasoner`) to record the first real Agent-vs-Baseline numbers.
2. Add CLI agent arms — `claude -p`, `codex exec`, `gemini -p` — that solve the same fixture copies and are
   graded by the same oracle (Terminal-Bench style: same task, many agents, one grader).
3. Upgrade the oracle from "compiles + keyword checks" to behaviour: Renode (`stm32f103.repl`,
   Robot `Wait For Line On Uart`, `antmicro/renode-test-action`) for STM32F103, Wokwi CI
   (`expect_text`/`fail_text`) for ESP32-S3, SDCC `ucsim` (`s51`) for 8051. This moves hardware evidence
   from `NOT_TESTED` to `SIMULATED` without a bench. EmbedAgent (ICSE 2026) evaluates on Wokwi for the
   same reason: serial text alone can be faked.
4. Report pass@1, tokens, latency and iterations per arm. EmbedAgent reports RAG + compiler feedback
   lifting DeepSeek-R1 from 55.6 % to 65.1 % pass@1 and ESP-IDF migration topping out at 29.4 % — the
   ranges this project should beat or explain.

## Phase D — Knowledge and platforms

- Chinese-aware retrieval: FTS5 built-in `trigram` tokenizer first; `wangfenjin/simple` (jieba + pinyin)
  if needed; OR-joined queries ranked by bm25 instead of implicit AND.
- API grounding: index function signatures extracted from the project's own `Drivers/**/*.h` and ESP-IDF
  headers and require lookups before use (AutoEmbed / EmbedGenius "APIs from real library source").
- Knowledge sources for ESP32-S3 and 8051; hardware intent from `TaskClassifier`/workflow instead of the
  `_wants_device` keyword list.
- Opt-in `CEA_ALLOW_PRIVATE_LLM` for Ollama / vLLM on localhost (the URL comes from local `.env`, so the
  SSRF guard can be relaxed explicitly).

## Phase E — Hardware and ecosystem

- probe-rs for flash/RTT/fault diagnosis alongside OpenOCD (`Adancurusul/embedded-debugger-mcp`).
- Publish the tool registry as an MCP server so Codex / Claude / Gemini CLIs can use the same tools —
  which also enables a "same model, with vs without our tools" benchmark arm.
- Documentation drift: reconcile README support statements and CI description, `PROJECT_STATE.md`,
  `TODO.md`, and remove the unused `unigateway/` graft.

## References

- EmbedAgent / EmbedBench — https://arxiv.org/abs/2506.11003
- AutoEmbed (EmbedGenius) — https://github.com/AutoEmbed/AutoEmbed
- EmbedEval — https://github.com/DeveshM7/EmbedEval
- Renode — https://github.com/renode/renode · testing: https://renode.readthedocs.io/en/latest/introduction/testing.html
- Wokwi CI — https://github.com/wokwi/wokwi-ci-action
- AG-UI events — https://docs.ag-ui.com/sdk/python/core/events
- vercel/resumable-stream — https://github.com/vercel/resumable-stream
- LangGraph INVALID_CHAT_HISTORY — https://langchain-ai.github.io/langgraph/troubleshooting/errors/INVALID_CHAT_HISTORY/
- Observation masking vs summarisation — https://arxiv.org/abs/2508.21433
- LiteLLM reliability — https://docs.litellm.ai/docs/proxy/reliability
- wangfenjin/simple — https://github.com/wangfenjin/simple
- embedded-debugger-mcp — https://github.com/adancurusul/embedded-debugger-mcp
- flashprobe-mcp — https://github.com/okhsunrog/flashprobe-mcp
- Codex sandboxing — https://developers.openai.com/codex/concepts/sandboxing
