# Benchmark Methodology

Each task declares platform, category, fixture, oracle, requirements and expected evidence. Agent and plain-LLM baselines use the same model, temperature 0, prompt and output budget; the default is one run per task. Raw per-task output is retained.

Missing LLM, compiler, SDK or hardware produces `SKIPPED` with a reason. Zero percentages are not emitted as if runs occurred. A single run is descriptive and does not establish statistical significance.
