# C-Embedded Agent

专注 C 语言与嵌入式开发的 AI 工程师。当前仓库包含：

- **前端**：Next.js 15 工作台（Timeline / 代码 / 终端 / 问题）
- **后端**：FastAPI Agent Runtime（真实文件系统 + make + OpenAI 兼容 LLM）

## 模式

- **DEMO**：后端未启动时，顶栏显示 DEMO，走前端 Mock 剧本（不会伪装成 LIVE 成功）
- **LIVE**：启动 FastAPI 后顶栏显示 LIVE。Run Agent 会创建真实工程并请求 `/api/runs`
- 本机没有 `arm-none-eabi-gcc` 时，LIVE 会明确报「未检测到编译器」，**不会伪装 Build Successful**

## 启动

前端：

```bash
npm install
npm run dev
```

后端：

```bash
pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

打开 http://localhost:3000

## 环境变量

见 `.env.example`：

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

LLM 使用本机已配置的 OpenAI 兼容接口。未配置时 Agent 会报 LLM 不可用，并尝试直接 `make`（仍受编译器检测约束）。

## MVP

- STM32F103C8T6 + HAL 风格模板（`templates/stm32f103_hal`，可被 ARM GCC 编译）
- Agent 循环最多 8 轮：读文件 / 写文件 / make / 知识检索
- SSE：`GET /api/runs/{id}/events`
- GCC 错误解析 → Problems
- 工具检测：`GET /api/tools/status`

即将推出：ESP32、C51、Keil 真编译、OpenOCD 烧录。

## 测试

```bash
cd backend && python -m pytest -q
npm run build
```
