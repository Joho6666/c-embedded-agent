from typing import Any

from app.providers.base import ChatResult


def responses_from_chat(result: ChatResult) -> ChatResult:
    content = ""
    try:
        content = result.payload["choices"][0]["message"]["content"] or ""
    except Exception:  # noqa: BLE001
        content = ""
    transformed = {
        "id": result.payload.get("id", "resp_gateway"),
        "object": "response",
        "model": result.payload.get("model"),
        "status": "completed",
        "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": content}]}],
        "usage": result.payload.get("usage", {}),
    }
    return ChatResult(status_code=200, payload=transformed)


def chat_body_from_responses(body: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    if body.get("instructions"):
        messages.append({"role": "system", "content": body["instructions"]})
    input_val = body.get("input", "")
    if isinstance(input_val, str):
        messages.append({"role": "user", "content": input_val})
    elif isinstance(input_val, list):
        messages.extend(input_val)
    chat_body = {
        "model": body.get("model"),
        "messages": messages,
        "temperature": body.get("temperature"),
        "max_tokens": body.get("max_output_tokens") or body.get("max_tokens"),
    }
    return {k: v for k, v in chat_body.items() if v is not None}
