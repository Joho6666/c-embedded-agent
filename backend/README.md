# C-Embedded Agent Backend

STM32F103 + ARM GCC 真实编译与 Agent 循环。

```bash
cd backend
pip install -r requirements.txt
cd ..
uvicorn app.main:app --reload --app-dir backend --port 8000
```

环境变量（仓库根或 `backend/.env`）：

```
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

无 ARM GCC 时 `/api/tools/status` 会显示未安装，编译接口返回明确错误，不会伪装成功。
