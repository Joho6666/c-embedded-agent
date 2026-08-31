# Universal AI Gateway

One Gateway. Every Provider. Every Model. One API.

私人 AI API Gateway MVP：控制面（Next.js）+ 数据面（FastAPI）。客户端只连：

```
BASE_URL=http://localhost:8000/v1
API_KEY=sk-gw-xxxx
```

## 启动（本地）

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
copy .env.example .env
cd backend
set PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
```

另开终端：

```bash
npm install
npm run dev
```

- 控制面：http://localhost:3000
- Gateway：http://localhost:8000/v1
- Admin 默认 Key：`gw-admin-dev-key`

## Docker

```bash
docker compose up -d --build
```

SQLite 存在 volume `gateway-data`，重启不丢凭据。

## 添加第一个 Credential

1. 控制面 → Provider → 添加 Custom OpenAI Compatible（或 OpenAI / OpenRouter / DeepSeek）
2. 添加凭据：Base URL + API Key
3. Test Connection
4. 同步模型

## 创建 Gateway API Key

API Keys → Create。明文只显示一次，复制 `sk-gw-…`。

## OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sk-gw-xxxx",
)
print(client.chat.completions.create(
    model="your-model-id",
    messages=[{"role": "user", "content": "hello"}],
))
```

Streaming：

```python
stream = client.chat.completions.create(
    model="coding",
    messages=[{"role": "user", "content": "hello"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

## 测试

```bash
cd backend
pytest -q
```

## 真实 vs Mock

**真实：** 凭据加密存储、Gateway API Key hash、`/v1/models`、`/v1/chat/completions` SSE、`/v1/responses` 基础转换、Virtual Model、failover、熔断、请求日志、Dashboard 今日指标、Health、Playground 真调用。

**仍为 Mock：** Usage 页高级趋势图。OAuth CLI / Antigravity 网页登录未实现（仅 ExternalBridgeAdapter 预留）。

**MVP Adapter：** OpenAI Compatible、Gemini、Ollama。
