# CURRENT_STATE — C-Embedded Agent 审计基线（2026-09-05）

本文档是 v0.10 升级前的真实状态审计。所有结论来自本机实测，不是文档转述。

- 版本：`0.9.0-alpha-mcp`（VERSION / README / CHANGELOG 一致；**RELEASE_REPORT.md 仍写 0.8.0-beta，已过期** → 本轮修复）
- 定位：Embedded Engineering Runtime for AI coding agents（Web Workbench / MCP / CLI 共用 CEA Core）

## 1. 已实现（代码存在且有测试）

| 能力 | 位置 | 说明 |
|---|---|---|
| CEA Core 门面 | `backend/app/core/` | Web/MCP/CLI 唯一能力层，`envelope(status, side_effect)` 统一返回 |
| STM32 平台适配 | `backend/app/core/platforms/stm32.py` | 唯一真实 adapter；`detect_adapter()` 仅返回 STM32 |
| 真实编译 | `backend/app/tools/compiler.py` | arm-none-eabi-gcc + make，流式 SSE，GCC/LD 诊断解析 |
| 烧录 | `backend/app/tools/flash.py` | OpenOCD 固定 argv（stlink.cfg + stm32f1x.cfg），chip-id 家族校验，烧录预算 |
| 串口 | `backend/app/tools/serialutil.py` | pyserial，自适应等待（token/quiet/上限） |
| 故障寄存器 | `backend/app/tools/debug_read.py` | OpenOCD halt dump：CFSR/HFSR/MMFAR/BFAR（只读，不算 PASS） |
| Error Memory | `backend/app/tools/error_memory.py` | 16 个硬编码模板 + 机械修复（HAL 注册/Makefile 去重/IRQ stub），SQLite 统计 |
| 语义验证 | `backend/app/validation/` | 按外设选择 validator，score≥0.8；ISR 安全审查 |
| IOC/引脚 | `backend/app/core/project.py`, `mcu/stm32f103.py` | IOC 解析（clock/pins/NVIC/DMA）、引脚冲突、Board Profile |
| Agent 运行时 | `backend/app/agent/runtime.py` | 23 工具 LLM loop、code 模式审批、stop、git snapshot/undo |
| MCP Server | `backend/app/mcp/server.py` | 11 工具，confirm 门，fabricated→FAIL |
| Benchmark | `benchmarks/benchmark.py` | Agent vs Baseline 完整实现，LLM 缺失时诚实 SKIP |

## 2. 真正验证了什么（本机实测 2026-09-05）

| 项 | 结果 |
|---|---|
| backend pytest | **110 passed, 1 skipped**（symlink 特权跳过）— 修复 `mcp` v2 兼容后（见 §7） |
| frontend lint / vitest / build | **lint 0 错误；23/23 通过；Next build 成功** |
| Golden 编译（11 个） | **11/11 PASS**（STM32F103 LED/EXTI/TIM/PWM/USART/USART_IT/USART_DMA/ADC/ADC_DMA/I2C/SPI，真实 size 记录） |
| Benchmark smoke | 诚实 SKIP：`LLM not configured`，`template_build: true` |
| MCP 测试 | 5/5（mcp 1.29.1） |

工具链现状（本机）：ARM GCC 13.3.1 ✅ / make 4.4.1 ✅ / **arm-none-eabi-gdb 14.2 ✅** / OpenOCD ❌ / st-info ❌ / cppcheck ❌ / clangd ❌ / Renode ❌ / ESP-IDF ❌ / SDCC ❌
硬件现状：**CH340 USB 串口 COM7（1A86:7523）在线；无 ST-Link** → 烧录/调试链路当前 UNAVAILABLE。

## 3. 只编译验证了什么

- 全部 11 个 Golden：仅证明 `make` 成功、ELF 尺寸合理。**没有任何硬件运行证据**（无 ST-Link/OpenOCD）。
- 模板 `templates/stm32f103_hal_official`：同上。
- benchmark 的 20 个任务：harness 完整但从未用真实 LLM 跑过；`benchmarkScore` 全为 null。

## 4. 没有验证什么（诚实缺口）

- **Hardware Execution：NOT_TESTED**。hardware-session.json 仅 5 字段（debugger/serialDevice/baud/board/mcu），无设备模型、无 VID/PID 发现、无 probe 序列号。
- **GDB/MI：不存在**。只有一次性 OpenOCD mdw 读取，无断点/单步/表达式求值/回溯。
- **仿真层：不存在**（Renode/QEMU/esp-emu 零引用）。
- **Agent vs Baseline：从未真实运行**（无 LLM 配置，comparison-summary 记录 skip 原因）。
- ESP32 / 8051 / RP2040 / Host C：**无后端 adapter**，仅前端 Planned 元数据。readme 支持矩阵一致。
- Checkpoint/Resume：无（只有 pre-run git snapshot + undo）。
- MAP/ELF 分段解析、flash/RAM 预算门、固件 diff 报告：无（只有 text/data/bss 三个数）。

## 5. Experimental / Planned（不得宣传为可用）

- clangd/cppcheck：可选集成，`shutil.which` 探测，缺失时报告 Unavailable，不阻塞。
- MyOS P0（`/api/os/*`）：Work OS 覆盖层，与固件执行无关。
- 前端 Platform Catalog 中 esp32/c51/rp2040/host-c：UI Preview，`disabledReason` 门控，诚实标注 Planned。

## 6. 技术债

1. `mcp>=1.2.0` 未设上限 → pip 装 2.1.1 后 MCP Server 崩溃（本轮已 pin `<2` 并降级；迁移到 mcp 2.x API 是后续项）。
2. `detect_adapter()` 无条件返回 STM32 — 单平台注册表，多平台需重构。
3. OpenOCD argv 硬编码在 `tools/flash.py`，无 DebugProbe 抽象。
4. Error Memory 无 `hardwareVerifiedCount`、不从真实 run 学习（仅 16 个内置模板 + 计数器）。
5. Approval 是模式级（auto/plan/code）而非权限级；`SAFE_READ/.../DANGEROUS_HARDWARE` 分级不存在。
6. Planner 输出仅展示（无 action/tool/permission/expectedEvidence）。
7. 混合工作区：仓库根目录 `pytest` 会收集无关项目（hallotickets 缺 uiautomator2）→ 必须按文档 `cd backend` 运行。
8. 模板与 Golden 提交了构建产物（firmware.elf/.o 等），建议后续 `.gitignore` 化。
9. Windows 上并发对同一 golden 目录跑 make 会产生瞬时 `-j` 竞态（观测一次，clean rebuild 通过）。

## 7. 文档漂移（本轮修复记录）

| 项 | 状态 |
|---|---|
| RELEASE_REPORT.md 写 `0.8.0-beta` + 过期测试计数（64 passed） | ❌ 已过期 → 本轮重写 |
| 需求书假设「当前版本 v0.9.1-beta」 | 实际 `0.9.0-alpha-mcp` |
| 需求书假设「当前已有 esp32s3-idf / 8051-sdcc adapter」 | 实际无后端 adapter，仅 UI 元数据 |
| 需求书假设「Benchmark 50 个任务」 | 实际 20 个（v0.10 扩到 50） |
| README「This release is STM32F103 only」与支持矩阵 | ✅ 一致，无漂移 |
| `backend/tests/test_gateway.py`、`test_v090.py` | 引用已删除模块（app.gateway.* / app.models.database / app.core.limiter），被 pytest.ini 无限期忽略 → 本轮删除 |

## 8. 结论分级（基于证据）

**当前 = Engineering Alpha（偏上）**：单平台管线真实可用且测试覆盖良好，诚实性执行到位；但无硬件执行证据、无调试会话、无仿真、benchmark 无真实跑分、能力矩阵靠前端手写 — 距离「Engineering Beta」的核心差距就是 v0.10 的主题：Hardware Lab + Probe/GDB/MI + Evidence + 真实 Benchmark。
