"""Public read-only mode for the SprayLine API.

The normal API (port 8011) serves the Manager UI and Engineer UI, which call
write-capable endpoints from the browser. It must stay on the LAN/VPN.

For outside callers (for example an AI agent), the same image is started a
second time with ``SPRAYLINE_API_MODE=public_readonly``. In that mode:

* only the routes in ``PUBLIC_ROUTE_ALLOWLIST`` are kept; every other route is
  removed, so it returns 404 and does not appear in /openapi.json or /api/routes;
* data routes require an ``X-API-Key`` header matching one of the keys in
  ``SPRAYLINE_PUBLIC_API_KEYS`` (comma separated);
* startup fails when no key is configured.
"""

from __future__ import annotations

import hmac
import os
from typing import Iterable, List

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute


API_MODE_ENV = "SPRAYLINE_API_MODE"
PUBLIC_READONLY_MODE = "public_readonly"
PUBLIC_API_KEYS_ENV = "SPRAYLINE_PUBLIC_API_KEYS"
API_KEY_HEADER = "X-API-Key"

# (method, path template) pairs exposed in public read-only mode.
# Keep this list in sync with SL-KM_1027_v2.md section 7.5.
PUBLIC_ROUTE_ALLOWLIST = frozenset(
    {
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/api/health"),
        ("GET", "/api/routes"),
        ("GET", "/api/alerts/history"),
        ("GET", "/api/alerts/summary"),
        ("GET", "/api/alerts/episodes"),
        ("GET", "/api/alerts/{event_id}"),
        ("GET", "/api/alerts/causes/{cause_id}/responses"),
        ("GET", "/api/service-orchestration/troubleshooting/matrix"),
        ("GET", "/api/service-orchestration/troubleshooting/states/{state}/recommendations"),
        ("POST", "/api/time-series/ui/summary"),
        ("POST", "/api/time-series/ui/station-detail"),
        ("POST", "/api/time-series/ui/component-detail"),
    }
)

# FastAPI's own documentation routes (not APIRoute instances).
DOC_PATHS = frozenset({"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"})

# Paths reachable without an API key: health, specification and route list.
# They only describe the allowlisted routes.
NO_KEY_PATHS = frozenset({"/", "/health", "/api/health", "/api/routes"}) | DOC_PATHS


def get_api_mode() -> str:
    return (os.getenv(API_MODE_ENV) or "").strip().lower() or "internal"


def is_public_readonly_mode() -> bool:
    return get_api_mode() == PUBLIC_READONLY_MODE


def load_public_api_keys(raw: str | None = None) -> List[str]:
    value = os.getenv(PUBLIC_API_KEYS_ENV, "") if raw is None else raw
    return [key.strip() for key in value.split(",") if key.strip()]


def _route_is_public(route: object) -> bool:
    path = getattr(route, "path", None)
    if isinstance(route, APIRoute):
        methods = set(route.methods or ()) - {"HEAD", "OPTIONS"}
        return bool(methods) and all((method, path) in PUBLIC_ROUTE_ALLOWLIST for method in methods)
    return path in DOC_PATHS


def _key_matches(candidate: str | None, keys: Iterable[str]) -> bool:
    if not candidate:
        return False
    candidate_bytes = candidate.encode("utf-8")
    matched = False
    for key in keys:
        # Compare against every key so timing does not reveal which one matched.
        matched = hmac.compare_digest(candidate_bytes, key.encode("utf-8")) or matched
    return matched


def apply_public_readonly(app: FastAPI, keys: List[str]) -> None:
    """Strip non-allowlisted routes from app and require an API key on data routes."""
    if not keys:
        raise RuntimeError(
            f"{API_MODE_ENV}={PUBLIC_READONLY_MODE} requires at least one key in "
            f"{PUBLIC_API_KEYS_ENV}; refusing to start without access control."
        )

    app.router.routes[:] = [route for route in app.router.routes if _route_is_public(route)]
    app.openapi_schema = None
    app.description = (
        "SprayLine public read-only API. Only read endpoints are available. "
        f"Send the {API_KEY_HEADER} header on data endpoints."
    )
    allowed_keys = tuple(keys)

    @app.middleware("http")
    async def _require_api_key(request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "OPTIONS" or request.url.path in NO_KEY_PATHS:
            return await call_next(request)
        if not _key_matches(request.headers.get(API_KEY_HEADER), allowed_keys):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error_code": "api_key_required",
                    "error_message": f"Missing or invalid {API_KEY_HEADER} header.",
                },
            )
        return await call_next(request)
