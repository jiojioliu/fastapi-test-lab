from __future__ import annotations

import asyncio
import hashlib
import random
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, RedirectResponse

from .. import database
from ..config import MAX_UPLOAD_BYTES
from ..dependencies import require_test_access
from ..traffic import traffic_store


router = APIRouter(
    prefix="/api/lab",
    tags=["Network Lab"],
    dependencies=[Depends(require_test_access)],
)


class DemoRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int = 5, window: float = 10.0) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window:
                events.popleft()
            allowed = len(events) < limit
            if allowed:
                events.append(now)
            remaining = max(0, limit - len(events))
            reset_in = max(0.0, window - (now - events[0])) if events else window
        return {
            "allowed": allowed,
            "limit": limit,
            "remaining": remaining,
            "reset_in_seconds": round(reset_in, 1),
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = DemoRateLimiter()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.get("/ping", summary="Fast health check for load tests")
async def ping() -> dict[str, str]:
    return {
        "message": "pong",
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
    }


async def echo(request: Request) -> dict[str, Any]:
    body: Any = None
    raw_body = await request.body()
    if raw_body:
        try:
            body = await request.json()
        except Exception:
            body = raw_body.decode("utf-8", errors="replace")
    return {
        "request_id": _request_id(request),
        "method": request.method,
        "path": request.url.path,
        "query": dict(request.query_params),
        "headers": dict(request.headers),
        "body": body,
        "client": request.client.host if request.client else "unknown",
        "received_at": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
    }


for _echo_method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
    router.add_api_route(
        "/echo",
        echo,
        methods=[_echo_method],
        operation_id=f"lab_echo_{_echo_method.lower()}",
        summary="Echo method, headers, query string and body",
    )


@router.get("/slow", summary="Add controlled latency to a response")
async def slow(
    delay_ms: int = Query(default=800, ge=0, le=10_000),
) -> dict[str, Any]:
    started = time.perf_counter()
    await asyncio.sleep(delay_ms / 1000)
    return {
        "message": "Response completed after the requested delay",
        "requested_delay_ms": delay_ms,
        "measured_delay_ms": round((time.perf_counter() - started) * 1000, 1),
    }


@router.get("/flaky", summary="Randomly return success or an upstream failure")
async def flaky(
    failure_rate: float = Query(default=0.3, ge=0, le=1),
    mode: str = Query(default="500", pattern=r"^(429|500|502|503)$"),
) -> Response:
    await asyncio.sleep(random.uniform(0.015, 0.09))
    if random.random() < failure_rate:
        status_code = int(mode)
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": "Simulated intermittent upstream failure",
                "status": status_code,
                "failure_rate": failure_rate,
                "request_id": "generated-by-middleware",
            },
        )
    return JSONResponse(
        {
            "ok": True,
            "attempt_note": "A retry may produce a different result",
            "failure_rate": failure_rate,
        }
    )


@router.get("/status/{status_code}", summary="Return a selected HTTP status code")
async def status_code_response(status_code: int) -> Response:
    allowed = {400, 401, 403, 404, 409, 418, 422, 429, 500, 503}
    if status_code not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Choose one of: {', '.join(map(str, sorted(allowed)))}",
        )
    headers: dict[str, str] = {}
    if status_code == 401:
        headers["WWW-Authenticate"] = 'Bearer realm="test-lab"'
    if status_code == 429:
        headers["Retry-After"] = "10"
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "simulated_status": status_code,
            "detail": "This response was deliberately generated for test assertions",
        },
    )


@router.get(
    "/rate-limit",
    summary="A five-requests-per-ten-seconds rate-limit demo",
)
async def rate_limit(request: Request) -> Response:
    client_key = request.headers.get("X-Lab-Client") or (
        request.client.host if request.client else secrets.token_hex(4)
    )
    result = rate_limiter.check(client_key, limit=5, window=10)
    headers = {
        "X-RateLimit-Limit": str(result["limit"]),
        "X-RateLimit-Remaining": str(result["remaining"]),
        "X-RateLimit-Reset": str(result["reset_in_seconds"]),
    }
    if not result["allowed"]:
        headers["Retry-After"] = str(max(1, round(result["reset_in_seconds"])))
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
            content={
                "detail": "Rate limit exceeded. Wait for the reset window.",
                "limit": result["limit"],
                "remaining": result["remaining"],
            },
        )
    return JSONResponse(
        content={
            "ok": True,
            "client_key": client_key,
            "limit": result["limit"],
            "remaining": result["remaining"],
            "reset_in_seconds": result["reset_in_seconds"],
        },
        headers=headers,
    )


@router.get("/redirect", summary="Return a 302 redirect")
async def redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=status.HTTP_302_FOUND)


@router.post(
    "/form",
    summary="Accept an application/x-www-form-urlencoded contact form",
)
async def contact_form(
    name: str = Form(min_length=2, max_length=80),
    email: str = Form(min_length=5, max_length=120),
    subject: str = Form(min_length=2, max_length=80),
    message: str = Form(min_length=5, max_length=1000),
) -> dict[str, Any]:
    return {
        "ok": True,
        "submission_id": f"FORM-{secrets.token_hex(4).upper()}",
        "accepted": {
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
        },
        "content_type": "application/x-www-form-urlencoded",
    }


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a small file (512 KiB maximum)",
)
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 512 KiB lab limit",
        )
    return {
        "ok": True,
        "stored": False,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "note": "The lab inspects upload metadata but does not persist submitted files.",
    }


@router.get("/cookies", summary="Set cookies and echo the request cookies")
async def cookies(request: Request, response: Response) -> dict[str, Any]:
    response.set_cookie(
        "lab_session",
        secrets.token_urlsafe(12),
        httponly=True,
        samesite="lax",
        max_age=300,
    )
    response.set_cookie(
        "lab_preference",
        "dark",
        samesite="lax",
        max_age=300,
    )
    return {
        "request_cookies": dict(request.cookies),
        "set_cookie_headers": [
            "lab_session=<HttpOnly token>",
            "lab_preference=dark",
        ],
    }


@router.get("/export", summary="Download a generated CSV response")
async def export_csv() -> Response:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = (
        "product_id,sku,name,stock\n"
        "1,KB-204,Nimbus 75,184\n"
        "2,MS-118,Orbit M2,220\n"
        f'0,EXPORTED,Generated at {generated},0\n'
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="testlab-products.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/reset", summary="Reset demo data and traffic metrics")
async def reset_lab() -> dict[str, Any]:
    database.reset_database()
    traffic_store.clear()
    rate_limiter.clear()
    return {
        "ok": True,
        "message": "Catalog, users, orders and traffic metrics were reset",
        "accounts": [
            "customer / customer123",
            "admin / admin123 (administrator + test account)",
            "guest: POST /api/auth/guest",
        ],
    }

