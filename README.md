# Universal AI Gateway

One Gateway. Every Provider. Every Model. Every Credential. One API.

把 OpenAI / Gemini / Claude / GLM / Kimi / DeepSeek / OpenRouter / 火山方舟 / 百炼 / 混元 / SiliconFlow / Ollama 以及自定义 OpenAI Compatible 上游，统一到：

```
BASE_URL=http://localhost:8000/v1
API_KEY=sk-gw-xxxx
```

当前仓库是可运行的 Control Plane 前端 Prototype。Mock 数据 + Zustand 可变状态 + `lib/services` 预留 REST 延迟，方便以后接真实 Gateway。

## 启动

```bash
npm install
npm run dev
```

打开 http://localhost:3000 。默认 Dark Mode。`Ctrl+K` 打开命令面板。

## 概念

```
Client → Gateway API → Virtual Model → Router → Provider → Credential → Real Model
```

- **Provider**：服务商
- **Credential**：官方支持的认证（API Key / OAuth / Project / Local）。不做 Cookie / Session 窃取
- **Real Model**：上游模型
- **Virtual Model**：客户端别名（`coding` / `fast` / `cheap`）
- **Routing Policy**：权重、Failover、熔断规则
- **API Key**：谁可以调用你的 Gateway

## 页面

概览 · Provider · 凭据池 · 模型中心 · 虚拟模型 · 路由策略 · API Keys · 请求日志 · 用量与成本 · 额度 · 健康状态 · 熔断中心 · API Playground · 开发者接入 · 系统设置

## 技术栈

Next.js 15 · React 19 · TypeScript · Tailwind 4 · shadcn/ui · Zustand · Recharts · Lucide
