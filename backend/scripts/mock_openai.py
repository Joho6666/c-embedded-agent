"""Local OpenAI-compatible mock for MVP acceptance tests."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()


@app.get("/v1/models")
def models():
    return {"data": [{"id": "mock-small"}, {"id": "mock-code"}]}


@app.post("/v1/chat/completions")
async def chat(body: dict):
    if body.get("stream"):

        async def gen():
            yield b'data: {"id":"m","object":"chat.completion.chunk","choices":[{"delta":{"content":"mock-ok"}}]}\n\n'
            yield b"data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")
    return JSONResponse(
        {
            "id": "chat-mock",
            "object": "chat.completion",
            "model": body.get("model", "mock-small"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "mock-ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4},
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9000)
