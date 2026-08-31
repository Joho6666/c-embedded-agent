from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers.base import AdapterContext, ChatResult, UpstreamError
from app.providers.openai_compatible import OpenAICompatibleAdapter


def cliproxy_root(base_url: str) -> str:
    root = (base_url or "http://127.0.0.1:8317").rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    return root


def cliproxy_v1(base_url: str) -> str:
    return cliproxy_root(base_url) + "/v1"


class ExternalBridgeAdapter(OpenAICompatibleAdapter):
    """OpenAI-compatible client for CLIProxyAPI / EasyCLIProxy after official OAuth."""

    name = "external_bridge"

    def _v1_ctx(self, ctx: AdapterContext) -> AdapterContext:
        return AdapterContext(
            base_url=cliproxy_v1(ctx.base_url),
            api_key=ctx.api_key,
            headers=ctx.headers,
            timeout_s=ctx.timeout_s,
        )

    async def list_models(self, ctx: AdapterContext) -> list[str]:
        return await super().list_models(self._v1_ctx(ctx))

    async def health_check(self, ctx: AdapterContext) -> tuple[bool, str, int]:
        try:
            models = await self.list_models(ctx)
            return True, f"CLI Proxy 在线 · {len(models)} models", 200
        except UpstreamError as exc:
            return False, f"桥接不可用：{exc.message}", exc.status_code
        except Exception as exc:  # noqa: BLE001
            return False, f"无法连接 CLIProxy（默认 :8317）：{exc}", 0

    async def chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        return await super().chat_completion(self._v1_ctx(ctx), body)

    async def stream_chat_completion(self, ctx: AdapterContext, body: dict[str, Any]) -> AsyncIterator[bytes]:
        async for chunk in super().stream_chat_completion(self._v1_ctx(ctx), body):
            yield chunk

    async def responses(self, ctx: AdapterContext, body: dict[str, Any]) -> ChatResult:
        return await super().responses(self._v1_ctx(ctx), body)


OAUTH_FAMILIES = {
    "gemini-cli": {
        "label": "Gemini CLI",
        "login": "gemini",
        "hint": "使用 Google 官方账号 OAuth（Gemini CLI / AI Studio 授权）。",
    },
    "claude-code": {
        "label": "Claude Code",
        "login": "claude",
        "hint": "使用 Anthropic 官方 Claude Code OAuth。",
    },
    "openai-codex": {
        "label": "OpenAI Codex",
        "login": "codex",
        "hint": "使用 OpenAI 官方 Codex / ChatGPT 订阅 OAuth。",
    },
    "antigravity": {
        "label": "Google Antigravity",
        "login": "antigravity",
        "hint": "使用 Google 官方 Antigravity / AI Studio OAuth。",
    },
    "kimi": {
        "label": "Kimi CLI",
        "login": "kimi",
        "hint": "使用 Moonshot 官方 CLI OAuth。",
    },
}


async def start_official_oauth(base_url: str, management_key: str, family: str) -> dict[str, Any]:
    meta = OAUTH_FAMILIES.get(family) or {
        "label": family,
        "login": family,
        "hint": "使用 Provider 官方 OAuth。",
    }
    root = cliproxy_root(base_url)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if management_key:
        headers["Authorization"] = f"Bearer {management_key}"
        headers["X-Management-Key"] = management_key

    tried: list[str] = []
    login = meta["login"]
    payloads = [
        ("POST", f"{root}/v0/management/login/{login}", {"provider": login}),
        ("POST", f"{root}/v0/management/auth/{login}/login", {"provider": login}),
        ("POST", f"{root}/v0/management/oauth/start", {"provider": login, "type": login}),
        ("GET", f"{root}/v0/management/auth-files", None),
    ]
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
        for method, url, json_body in payloads:
            tried.append(url)
            try:
                r = await client.request(method, url, headers=headers, json=json_body)
            except Exception as exc:  # noqa: BLE001
                return {
                    "ok": False,
                    "bridgeOnline": False,
                    "family": family,
                    "label": meta["label"],
                    "bridge": root,
                    "tried": tried,
                    "message": f"连不上 CLIProxy/EasyCLIProxy：{exc}",
                    "hint": meta["hint"],
                    "command": f"在 EasyCLIProxyAPI 中对 {meta['label']} 执行官方 Login / OAuth",
                }
            if r.status_code in (200, 201, 202):
                body: Any
                try:
                    body = r.json()
                except Exception:  # noqa: BLE001
                    body = {"raw": r.text[:500]}
                login_url = ""
                if isinstance(body, dict):
                    login_url = str(body.get("url") or body.get("login_url") or body.get("authUrl") or "")
                return {
                    "ok": True,
                    "bridgeOnline": True,
                    "family": family,
                    "label": meta["label"],
                    "bridge": root,
                    "loginUrl": login_url,
                    "upstream": body,
                    "hint": meta["hint"] + " 在弹出的官方浏览器窗口完成授权。不要粘贴网页 Cookie。",
                    "command": f"EasyCLIProxyAPI → Login {meta['label']}",
                }
            if r.status_code in (401, 403):
                return {
                    "ok": False,
                    "bridgeOnline": True,
                    "family": family,
                    "label": meta["label"],
                    "bridge": root,
                    "message": "Management Key 无效。请填写 CLIProxy 的 remote-management secret。",
                    "hint": meta["hint"],
                    "command": f"EasyCLIProxyAPI → Login {meta['label']}",
                }

    return {
        "ok": True,
        "bridgeOnline": True,
        "family": family,
        "label": meta["label"],
        "bridge": root,
        "loginUrl": "",
        "message": "桥接在线，但当前 CLIProxy 版本未暴露 Management 登录 API。请在 EasyCLIProxyAPI 托盘里对应该账号点官方 OAuth Login。",
        "hint": meta["hint"] + " 授权完成后回到本页点「同步模型」。",
        "command": f"EasyCLIProxyAPI → Login {meta['label']}",
        "tried": tried,
    }
