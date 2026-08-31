from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class PublicURLError(ValueError):
    pass


_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
}


def assert_public_http_url(url: str) -> str:
    """Allow only http(s) to a public, non-reserved host. Reject SSRF targets."""
    raw = (url or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise PublicURLError("URL 必须是 http/https")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise PublicURLError("URL 缺少 host")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost") or host.endswith(".local"):
        raise PublicURLError("拒绝 localhost / 环回 host")
    if parsed.username or parsed.password:
        raise PublicURLError("拒绝带用户信息的 URL")
    _assert_public_host(host)
    return raw.rstrip("/")


def _assert_public_host(host: str) -> None:
    try:
        ip = ipaddress.ip_address(host)
        _assert_public_ip(ip)
        return
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise PublicURLError(f"无法解析 host: {host}") from e
    if not infos:
        raise PublicURLError(f"无法解析 host: {host}")
    for info in infos:
        sockaddr = info[4]
        ip = ipaddress.ip_address(sockaddr[0])
        _assert_public_ip(ip)


def _assert_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    ):
        raise PublicURLError(f"拒绝私有/保留地址: {ip}")
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        _assert_public_ip(mapped)
