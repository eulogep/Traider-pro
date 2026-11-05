"""Local-request guard — outermost ASGI middleware of the quant API (audit Codex V0.3, I3 + I4).

Runs BEFORE routing and BEFORE any body parsing (multipart included):

* **Host** must be a loopback name (``localhost``, ``127.0.0.1``, ``::1``, + ``ATO_ALLOWED_HOSTS``)
  -> otherwise 421. Defeats DNS rebinding (a foreign domain resolving to 127.0.0.1 keeps its own Host).
* **Mutations** (POST/PUT/PATCH/DELETE):
  - ``Sec-Fetch-Site: cross-site`` -> 403;
  - an ``Origin`` header, when present, must be a loopback origin (exact URL parsing, any port) or listed
    in ``ATO_CORS_ORIGINS`` -> otherwise 403;
  - header ``X-ATO-Request: 1`` is required -> otherwise 403. A custom header forces a CORS preflight
    for cross-origin browser requests, which the CORS policy refuses: a foreign page cannot send it.
* **Body size**: a declared ``Content-Length`` above the route limit is refused (413) without reading
  a single byte; bodies without length are counted while being received and cut at the limit (413).
  Limits: ``ATO_MAX_UPLOAD_MB`` (import, default 50) and ``ATO_MAX_JSON_KB`` (other routes, default 256).

This is a local, single-user tool: these checks reduce browser-borne attacks; they are not
authentication. Any process of the same machine can still call the API.
"""

from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
UPLOAD_PATHS = {"/api/v1/datasets/import", "/api/v1/ea-reports/analyze", "/api/v1/external-sims"}
LOCAL_HEADER = "x-ato-request"


def _allowed_hosts() -> set[str]:
    extra = {h.strip().lower() for h in os.environ.get("ATO_ALLOWED_HOSTS", "").split(",") if h.strip()}
    return LOOPBACK_HOSTS | extra


def _host_name(host_header: str) -> str:
    host = host_header.strip().lower()
    if host.startswith("["):  # [::1]:8765
        return host[1:host.index("]")] if "]" in host else host
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def is_local_origin(origin: str) -> bool:
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or parts.path not in ("", "/") or parts.query or parts.username:
        return False
    if (parts.hostname or "") in LOOPBACK_HOSTS:
        return True
    listed = {o.strip().rstrip("/") for o in os.environ.get("ATO_CORS_ORIGINS", "").split(",") if o.strip()}
    return origin.rstrip("/") in listed


def max_upload_bytes() -> int:
    return int(float(os.environ.get("ATO_MAX_UPLOAD_MB", "50")) * 1024 * 1024)


def max_json_bytes() -> int:
    return int(float(os.environ.get("ATO_MAX_JSON_KB", "256")) * 1024)


class _BodyTooLarge(Exception):
    pass


class LocalRequestGuard:
    def __init__(self, app):
        self.app = app

    @staticmethod
    async def _reply(send, status: int, message: str) -> None:
        body = json.dumps({"error": message, "detail": None}, ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        if _host_name(headers.get("host", "")) not in _allowed_hosts():
            return await self._reply(send, 421, "Hôte non autorisé : l'API n'accepte que des requêtes locales.")
        method = scope.get("method", "GET").upper()
        if method not in MUTATING:
            return await self.app(scope, receive, send)

        if headers.get("sec-fetch-site", "").lower() == "cross-site":
            return await self._reply(send, 403, "Requête inter-sites refusée.")
        origin = headers.get("origin")
        if origin is not None and not is_local_origin(origin):
            return await self._reply(send, 403, "Origine non autorisée pour une modification.")
        if headers.get(LOCAL_HEADER) != "1":
            return await self._reply(send, 403, "En-tête X-ATO-Request manquant : requête de modification refusée.")

        limit = max_upload_bytes() if scope.get("path") in UPLOAD_PATHS else max_json_bytes()
        declared = headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > limit:
                    return await self._reply(send, 413, f"Corps de requête trop volumineux (> {limit} octets).")
            except ValueError:
                return await self._reply(send, 400, "Content-Length invalide.")

        received = 0
        exceeded = False

        async def limited_receive():
            nonlocal received, exceeded
            msg = await receive()
            if msg.get("type") == "http.request":
                received += len(msg.get("body", b""))
                if received > limit:
                    exceeded = True  # stop reading here: the rest of the body is never consumed
                    raise _BodyTooLarge
            return msg

        async def guarded_send(message):
            if not exceeded:  # once over the limit, the app's own answer (often a 400) is discarded
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            pass
        if exceeded:
            await self._reply(send, 413, f"Corps de requête trop volumineux (> {limit} octets).")
