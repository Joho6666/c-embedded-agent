from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

LOCAL_ADAPTER_TYPES = {"ollama", "external_bridge", "cliproxy"}

PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_host(host: str) -> bool:
    h = (host or "").strip("[]").lower()
    if h in {"localhost", "0.0.0.0", "::", "metadata.google.internal"}:
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return any(ip in net for net in PRIVATE_NETS)


def validate_upstream_url(url: str, adapter_type: str = "") -> str:
    raw = (url or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("upstream URL must be http or https")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("upstream URL missing host")
    from app.core.config import get_settings

    allow_local = adapter_type in LOCAL_ADAPTER_TYPES or get_settings().allow_local_upstream
    if _is_private_host(host) and not allow_local:
        raise ValueError("private/loopback upstream is not allowed for this provider type")
    return raw
