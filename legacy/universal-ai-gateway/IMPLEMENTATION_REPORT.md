# IMPLEMENTATION_REPORT — MVP Hardening

## 1. 修改了什么

- Streaming：首包前 429/timeout 仍 failover；已向客户端写出后再失败不再换 credential。日志在 stream `finally` 写入；key 计数在 stream 结束后 bump。
- `/v1/responses` 与 chat 共用 `execute_chat`（含 failover），不再 `queue[0]`。
- Router：priority / failover / round_robin（持久化 cursor）/ weighted_round_robin / least_latency / highest_success / quota_aware / health_aware / random / hybrid。`GET /admin/capabilities` 为策略来源；前端隐藏 least_load / lowest_cost。
- Quota：API Key RPM + daily token；Credential 超限标记 `quota_exhausted` 并切下一个。ApiKey `stats_day` 跨天重置。
- SSRF：远程 Provider 拒绝环回/私有地址；local adapter 或 `ALLOW_LOCAL_UPSTREAM=true` 才允许本机。
- 删除 `NEXT_PUBLIC_ADMIN_API_KEY`。浏览器只打 `/api/control/*`。可选 `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` + HttpOnly Cookie。
- Usage 页改为 `/admin/usage/trend` + 真实 totals。
- CLIProxy OAuth：探测失败返回 `ok: false`，不再假成功。
- CI workflow、compose Redis profile、`.env.example` 去掉可用密钥字面量。

## 2. 真实实现

Chat/Responses/SSE、Virtual Model、failover、circuit、RPM、daily token、strategies 列表、BFF、Usage 趋势、RequestLog。

## 3. Experimental

CLIProxy OAuth（依赖 EasyCLIProxy 版本）、Redis URL 预留（进程内 limiter 已工作）、模型定价表（无定价则 cost=0）。

## 4. 测试结果

`cd backend && pytest -q` → **14 passed**（含 capabilities、RPM 429、Responses failover）。

## 5. Build 结果

`npx tsc --noEmit` 通过；`npm run lint` 通过。`npm run build` 见本次运行输出。

## 6. Docker 结果

compose 已改为无默认密钥、frontend healthcheck、`depends_on: service_healthy`、`--profile redis`。未在本机用真实密钥跑完整 `docker compose up --build`（缺少用户提供的密钥）。

## 7. 下一阶段

- 把 Redis limiter 真正接到 RPM/RR cursor
- CLIProxy 按官方 Management 文档做版本探测
- 模型定价 Admin UI
- 生产强制登录 + 弱密钥拒绝启动
