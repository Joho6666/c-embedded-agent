# C-Embedded Agent Repository Map (AGENTS.md)

Welcome to `Joho6666/c-embedded-agent`. This file serves as the primary navigation harness and architectural law for all AI agents working on this repository.

---

## 1. 项目使命 (Project Mission)

**C-Embedded Agent** 是面向嵌入式 C 语言的 **AI 固件工程智能体 (AI Firmware Engineering Agent)**：
```text
Requirement
  ↓
Understand Project (Context Router & Facts)
  ↓
Plan (Structured Action Plan & Approval Policy)
  ↓
Generate / Patch (Minimal AST-aligned Diffs)
  ↓
Compile (Real Cross-Compiler & Exit Codes)
  ↓
Diagnose (Error Memory & Diagnostics)
  ↓
Auto Fix (Controlled 3-Iteration Repair Loop)
  ↓
Flash (Hardware Debug Probe & Verify Reset)
  ↓
Serial / Hardware Evidence (Marker Capture & Telemetry)
  ↓
Validate (Static + Behavioral Acceptance)
```
不要将项目退化为普通 AI Chat、代码生成玩具或空壳前端。

---

## 2. 架构核心与设计法则 (Core Architecture)

```text
Agent Runtime
      ↓
Tool Registry / Skill Registry / Approval Policy
      ↓
PlatformAdapter Boundary
      ↓
Native Toolchain (ARM GCC / ESP-IDF) & Hardware Probes (ST-Link / Serial)
```

1. **统一平台抽象 (`PlatformAdapter`)**:
   所有与具体单片机、厂商库、构建系统相关的逻辑全部收敛在 `app.platforms.*` 中。严禁在 Runtime 中随处使用 `if platform == "stm32":`。
2. **两平台证明接口，三平台证明架构**:
   * STM32F103 (CubeF1 HAL) — Reference Platform (Beta)
   * ESP32-S3 (ESP-IDF 6.1) — Second Platform (Experimental)
   * 8051 (C51/SDCC) — Third Platform Candidate (Planned Roadmap)
3. **集中式审批策略 (`ApprovalPolicyManager`)**:
   * `SAFE`: 只读/检索/编译/静态校验
   * `WRITE`: 修改工作区/打补丁
   * `HARDWARE`: 物理烧录/复位
   * `DANGEROUS`: 擦除Flash/烧写eFuse/修改Option Bytes（绝对禁止自主执行）

---

## 3. 核心准则：严禁事项 (Forbidden Behaviors / NO FAKE PASS)

1. **NO FAKE PASS**: 代码写了 ≠ 功能完成。严禁在没有真实产物、没有真实探针、没有真实运行结果时标记 PASS。
2. **严禁删除测试造绿**: 严禁删除、skip 失败测试或弱化断言以制造绿色 CI。
3. **严禁使用 Mock 代替真实编译器**: 必须调用真实 `arm-none-eabi-gcc` 与 `idf.py`。
4. **严禁编造 Benchmark 指标**: 缺少 LLM 凭据时必须返回 `SKIPPED`，各项比率置为 `null`。
5. **严禁将 OpenOCD 存在误报为 ST-Link 已连接**: 工具已安装 ≠ 物理硬件已连接。
6. **严禁硬编码敏感凭据**: 绝不允许将 API Key、Token 提交至代码、日志、Run 留痕或 Git。

---

## 4. 目录职责划分 (Directory Layout)

* `backend/app/agent/`: Agent 核心运行时、结构化 Planner、任务分类、技能与工作流路由、审批策略。
* `backend/app/platforms/`: 平台适配器规范与实现 (`base.py`, `registry.py`, `stm32f103/`, `esp32s3/`)。
* `backend/app/tools/`: 统一原子工具集 (`compiler.py`, `flash.py`, `hardware_run.py`, `error_memory.py`, `registry.py`)。
* `backend/app/skills/`: 外设专业技能知识与模板映射 (`stm32f103/`, `esp32s3/`)。
* `backend/app/release/`: 统一发布门禁与证据模型 (`gates.py`, `evidence.py`)。
* `examples/golden/`: STM32 官方 HAL 11 个 Golden 验证工程。
* `examples/golden_esp32/`: ESP32-S3 7 个官方 ESP-IDF Golden 样例工程。
* `benchmarks/`: 50 个 STM32 benchmark task 定义与 Agent vs Baseline 对比评测框架。
* `src/`: Next.js 现代化工程工作台 UI。
* `scripts/`: 工程验证、发布门禁、代码质量与漂移检查脚本。
* `docs/`: 详细技术规范、架构文档与路线图。

---

## 5. 关键文档索引 (Key Documentation)

* 综合索引: `docs/INDEX.md`
* 架构规范: `docs/platform-adapters.md`, `ARCHITECTURE.md`, `CURRENT_ARCHITECTURE.md`
* 硬件测试: `docs/hardware-testing.md`
* 评测基准: `docs/benchmark.md`
* 8051 路线图: `docs/platforms/8051-roadmap.md`
* 当前执行计划: `docs/exec-plans/active/v0.9-release-hardening.md`
* 架构决策记录: `docs/adr/`

---

## 6. 标准测试与验证命令 (Verification Commands)

### 6.1 后端单元与集成测试
```bash
cd backend && python -m pytest -q
```

### 6.2 前端构建与代码检查
```bash
npm run lint
npm run build
```

### 6.3 质量守卫与文档漂移检测
```bash
python scripts/secret_scan.py
python scripts/project_state.py --check
python scripts/quality_gate.py
```

### 6.4 STM32 Golden 11/11 真实构建
```bash
python scripts/golden_build.py
```

---

## 7. 深入领域 AGENTS.md 路径 (Deeper AGENTS.md)

* 运行时规则: `backend/app/agent/AGENTS.md`
* 平台适配器规则: `backend/app/platforms/AGENTS.md`
