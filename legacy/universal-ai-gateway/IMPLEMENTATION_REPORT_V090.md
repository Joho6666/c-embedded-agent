# IMPLEMENTATION_REPORT_V090

Universal AI Gateway **0.9.0-rc.1** — Self-hosted RC. 工作目录：`universal-ai-gateway`（不是 C-Embedded Agent 的 `default` 工作区）。

## 1. 完成项

- Credential RPM 检查与消耗分离（eligibility 只 peek）
- Virtual Model：Resolve Candidates → Strategy Engine → Execution
- Smooth Weighted Round Robin（Nginx 风格，StateBackend 保存 current_weight）
- Redis StateBackend：RPM/TPM/RR/WRR；未配置或连不上则 Memory
- API Key 与 Credential 完整配额：RPM、TPM 预扣、Daily Request/Token、Monthly Budget
- Streaming RequestLog：pending → routing/connecting/streaming → ok/error/cancelled
- Native Responses + Chat fallback
- Provider capabilities registry 与 Admin CRUD 定价
- Usage 分 Provider/Model/Credential/API Key/Errors
- CLIProxy：health/version 探测，Management 不支持则明确 `manualLoginRequired`
- SSRF / production 弱密钥拒绝启动 / Alembic 首迁 / 日志清理 / SQLite backup

## 2. 修复 Bug

- Router 扫描 A/B/C/D 时不再给未选中 Credential 记 RPM
- `candidate_queue` 不再按 priority 提前钉死顺序；绑定 `credentialId` 后策略仍作用在全集
- WRR 不再 `weight // 10` 复制列表
- `quota_exhausted` 拆成 daily/monthly/rate_limited，跨天/跨月可恢复
- `begin_log` 真正接入；stream 结束后写最终状态（独立 Session，避免 pending 被请求 session 写回）
- `/v1/responses` 对不支持的上游回退 Chat，failover 仍有效
- Serializer 不再把 `monthlySpend` / `cachedTokens` 写死为 0

## 3. Routing 实现

Resolve → `ResolvedCandidate` → `apply_strategy`：

| 策略 | 行为 |
| --- | --- |
| priority / failover | priority |
| round_robin | StateBackend cursor |
| weighted_round_robin | Smooth WRR |
| least_latency | avg_latency_ms |
| highest_success | 真实成功率 |
| quota_aware | daily + RPM peek + budget |
| health_aware | status + success + latency |
| hybrid | 可解释加权分 |

Trace 记录 strategy、candidate scores、Selected。

## 4. Quota 实现

- API Key：Auth → reset → RPM → daily request → daily token → monthly budget → TPM 预估占用 → 执行 → 按实际补差
- Credential：静态额度只检查；选中后 `consume_credential_quota`；失败切下一个；全部不可用 `all_credentials_quota_exhausted` / `no_healthy_credential`
- 错误 envelope：`{error:{message,type,code}}`

## 5. Redis 状态

- `MemoryStateBackend` / `RedisStateBackend`
- `REDIS_URL` 或 Docker DNS `redis:6379` 可达则 Redis
- `/health` 与 `/admin/health` 显示 `stateBackend` 与 `redis=connected|disabled|error`
- SQLite 仍是业务库

## 6. Streaming 状态

pending → routing → connecting → streaming → ok | error | cancelled。客户端断开走 `request.is_disconnected` / `CancelledError`。Requests 页 2 秒轮询。

## 7. Responses API 状态

OpenAI Compatible：`supports_native_responses=true`，先 `/v1/responses`，404/网络失败 fallback Chat。Gemini / Ollama / CLIProxy fallback。不实现 Background Responses。

## 8. Security 状态

- `APP_ENV=production` 拒绝短/默认密钥
- SSRF：仅 http/https；本地只给 Ollama/CLIProxy 或非生产 `ALLOW_LOCAL_UPSTREAM`
- `SECURITY.md`：反向代理、TLS、防火墙、备份

## 9. Tests

`cd backend && pytest -q` → **32 passed**（原 14 + v0.9：RPM 误计数、TPM、daily、WRR 分布、least_latency、SSRF、pricing、cost、health Redis component、streaming log）。

## 10. Build

- `npm ci` / `npm run lint` / `npm run build` 通过
- `python -m compileall app` 通过

## 11. Docker

compose：`restart: unless-stopped`、healthcheck、redis profile healthcheck。`REDIS_URL` 空时 backend 会尝试 `redis:6379`。本环境未注入用户密钥，未实际 `docker compose up --build`。

## 12. Experimental

- CLIProxy Management API 随版本变化；不支持时要求去 EasyCLIProxy 官方 OAuth
- Redis 在无 URL 且 DNS 失败时保持 Memory
- 模型定价需手工维护，否则 cost=0

## 13. 下一版本建议

- WebSocket Request Trace
- Background Responses
- PostgreSQL 正式部署与 CI matrix
- `least_load` / live `lowest_cost`
- Embeddings / images / audio 数据面
- OIDC 登录
