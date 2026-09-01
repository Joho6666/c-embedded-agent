# C-Embedded Agent

专注 STM32F103C8T6 的嵌入式 C Agent。判断标准不是功能数量，而是：同一真实任务上，编译成功率、一次成功率、自动修复率是否高于直接问模型。

## 模式

- **DEMO**：后端未启动，顶栏 DEMO，走前端 Mock（不会伪装 LIVE 成功）
- **LIVE**：FastAPI 已启动。没有 `arm-none-eabi-gcc` 时明确报缺失，**不会伪装 Build Successful**
- **OFFLINE**：配置了 API URL 但后端不可达

## 启动

```bash
npm install
npm run dev
```

```bash
pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

打开 http://localhost:3000

环境变量见 `.env.example`。LLM 必须是公网 http/https（拒绝 localhost / 私网）。未配置 LLM 时 Agent 会报不可用，并尝试直接 `make`。

## STM32F103 官方模板

默认工程：`templates/stm32f103_hal_official`（STM32CubeF1 CMSIS + HAL，不是自制 stub）。

- MCU：STM32F103C8T6
- 板：Blue Pill
- LED：**PC13**，500ms toggle
- 同步官方驱动：`python scripts/sync_cubef1.py`

```bash
cd templates/stm32f103_hal_official
make clean && make -j4
```

需要 `arm-none-eabi-gcc` / `objcopy` / `size` / `make`。本机没有工具链时测试会 skip，不编造成绩。

后端也会自动探测用户目录便携工具链：

- `%USERPROFILE%/tools/xpack-arm-none-eabi-gcc-13.3.1-1.1/bin`
- `%USERPROFILE%/tools/xpack-windows-build-tools-4.4.1-3/bin`

或设置 `CEA_TOOLCHAIN_PATH`。官方模板已在本机用 ARM GCC 13.3 真实链接出 `firmware.elf/.hex/.bin`（Flash text+data ≈ 2.9KB）。

Golden 回归夹具：

- LED PC13：`examples/golden/stm32f103_led/`
- USART1 115200 PA9/PA10：`examples/golden/stm32f103_usart/`
- TIM2 PWM PA0：`examples/golden/stm32f103_pwm/`

刷新外设黄金工程：`python examples/golden/sync_overlay.py all`

## Agent 规则

先读工程 → 查 Knowledge / MCU pin → 最小修改 Core → `make` → 按真实 GCC/LD 错误修复。默认禁止改 `Drivers/`、`startup*.s`、`*.ld`、`Makefile`。

## Benchmark

```bash
python benchmarks/benchmark.py
```

输出 `benchmarks/stm32f103/results.json`。无 LLM 或无 ARM GCC 时 skip 并写明原因。

## 测试 / CI

```bash
cd backend && python -m pytest -q
npm run build
```

GitHub Actions：前端 `npm ci && npm run build`，后端 `pytest`。ARM GCC 为 optional。

本轮范围仅 STM32F103。不做 ESP32 / C51 / F407。
