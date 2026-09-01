# UniGateway

统一管理多个 AI 上游服务的 API Gateway 控制台（前端原型）。

用户只需要一个 Base URL + 一个 API Key，即可调用多个上游 Provider。当前阶段全部走 Mock API，不请求真实上游。

## 启动

```bash
cd unigateway
npm install
npm run dev
```

打开 http://localhost:3001

## 技术栈

Next.js 15 · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui · Recharts

## 说明

- 数据在 `src/lib/mock`，页面只通过 `src/lib/api` 访问
- 连通性测试 / 拉模型 / 查余额为模拟结果，不会对公网或内网发请求
- 示例 Key 使用 `ug_live_` 前缀，不是可用凭据
