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
    supports_native_responses = False

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


async def detect_bridge(base_url: str) -> dict[str, Any]:
    root = cliproxy_root(base_url)
    version = ""
    online = False
    management = False
    async with httpx.AsyncClient(timeout=4.0, follow_redirects=False) as client:
        try:
            health = await client.get(f"{root}/health")
            online = health.status_code < 500
            if health.status_code < 400:
                try:
                    payload = health.json()
                    if isinstance(payload, dict):
                        version = str(payload.get("version") or payload.get("ver") or "")
                except Exception:  # noqa: BLE001
                    version = ""
        except Exception:  # noqa: BLE001
            return {
                "bridgeOnline": False,
                "managementApi": False,
                "oauthManagement": False,
                "version": "",
                "bridge": root,
            }
        try:
            mgmt = await client.get(f"{root}/v0/management")
            management = mgmt.status_code not in {404, 405}
            if mgmt.status_code < 400:
                try:
                    body = mgmt.json()
                    if isinstance(body, dict) and not version:
                        version = str(body.get("version") or "")
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            management = False
    return {
        "bridgeOnline": online,
        "managementApi": management,
        "oauthManagement": management,
        "version": version,
        "bridge": root,
    }


async def start_official_oauth(base_url: str, management_key: str, family: str) -> dict[str, Any]:
    meta = OAUTH_FAMILIES.get(family) or {
        "label": family,
        "login": family,
        "hint": "使用 Provider 官方 OAuth。",
    }
    detected = await detect_bridge(base_url)
    root = detected["bridge"]
    base = {
        "family": family,
        "label": meta["label"],
        "bridge": root,
        "version": detected.get("version") or "",
        "hint": meta["hint"],
        "command": f"请前往 EasyCLIProxy 完成官方 OAuth 登录（{meta['label']}）",
    }
    if not detected["bridgeOnline"]:
        return {
            **base,
            "ok": False,
            "bridgeOnline": False,
            "managementApi": False,
            "oauthManagement": False,
            "manualLoginRequired": True,
            "message": "连不上 CLIProxy/EasyCLIProxy。请确认桥接进程已启动。",
        }
    if not detected["managementApi"]:
        return {
            **base,
            "ok": False,
            "bridgeOnline": True,
            "managementApi": False,
            "oauthManagement": False,
            "manualLoginRequired": True,
            "message": "桥接在线，但当前版本未提供 Management API。请前往 EasyCLIProxy 完成官方 OAuth 登录。",
        }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if management_key:
        headers["Authorization"] = f"Bearer {management_key}"
        headers["X-Management-Key"] = management_key
    login = meta["login"]
    url = f"{root}/v0/management/auth/{login}/login"
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
        try:
            r = await client.post(url, headers=headers, json={"provider": login})
        except Exception as exc:  # noqa: BLE001
            return {
                **base,
                "ok": False,
                "bridgeOnline": True,
                "managementApi": True,
                "oauthManagement": True,
                "manualLoginRequired": True,
                "message": f"Management API 不可用：{exc}",
            }
        if r.status_code in (401, 403):
            return {
                **base,
                "ok": False,
                "bridgeOnline": True,
                "managementApi": True,
                "oauthManagement": True,
                "manualLoginRequired": True,
                "message": "Management Key 无效。请填写 CLIProxy 的 remote-management secret。",
            }
        if r.status_code in (200, 201, 202):
            try:
                body = r.json()
            except Exception:  # noqa: BLE001
                body = {"raw": r.text[:500]}
            login_url = ""
            if isinstance(body, dict):
                login_url = str(body.get("url") or body.get("login_url") or body.get("authUrl") or "")
            return {
                **base,
                "ok": True,
                "bridgeOnline": True,
                "managementApi": True,
                "oauthManagement": True,
                "manualLoginRequired": not bool(login_url),
                "loginUrl": login_url,
                "upstream": body,
                "hint": meta["hint"] + " 在弹出的官方浏览器窗口完成授权。不要粘贴网页 Cookie。",
                "command": f"EasyCLIProxyAPI → Login {meta['label']}",
            }
    return {
        **base,
        "ok": False,
        "bridgeOnline": True,
        "managementApi": False,
        "oauthManagement": False,
        "manualLoginRequired": True,
        "message": "桥接在线，但 Management 登录不可用。请前往 EasyCLIProxy 完成官方 OAuth 登录。",
    }
