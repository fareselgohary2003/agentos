"""Simple in-memory rate limiter (spec §25). Swap the counter store for Redis
(INCR + EXPIRE) to work across multiple API replicas — the interface below
doesn't change, only `_store`.
"""
from __future__ import annotations

import ipaddress
import time
import urllib.parse

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_WINDOW = 120
_store: dict[str, list[float]] = {}


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await call_next(request)

        key = _client_key(request)
        now = time.monotonic()
        window_start = now - _WINDOW_SECONDS
        timestamps = [t for t in _store.get(key, []) if t > window_start]

        if len(timestamps) >= _MAX_REQUESTS_PER_WINDOW:
            return _too_many_requests()

        timestamps.append(now)
        _store[key] = timestamps
        return await call_next(request)


def _too_many_requests():
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Try again shortly."},
    )


# ---------------------------------------------------------------------------
# SSRF protection — any tool that fetches a URL supplied by an LLM or a
# retrieved document must validate it through this first (spec §25).
# ---------------------------------------------------------------------------

_BLOCKED_HOST_PREFIXES = ("169.254.", "127.", "10.", "192.168.")


class SSRFError(Exception):
    pass


def assert_safe_outbound_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Blocked non-HTTP(S) scheme: {parsed.scheme}")

    host = parsed.hostname or ""
    if host in ("localhost",) or host.startswith(_BLOCKED_HOST_PREFIXES):
        raise SSRFError(f"Blocked request to internal/loopback host: {host}")

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise SSRFError(f"Blocked request to non-public IP: {host}")
    except ValueError:
        pass  # host is a hostname, not a literal IP — DNS-level rebinding
              # protection belongs at the network/proxy layer in production
