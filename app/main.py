from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import database
from .config import APP_NAME, APP_VERSION, BASE_DIR, DOWNLOAD_DIR, STATIC_DIR
from .routers import auth, catalog, lab, orders, traffic
from .traffic import traffic_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.init_database()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "A safe, local REST API environment for Postman, JMeter, Burp Suite "
        "and Wireshark practice."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time-Ms",
        "X-Lab-Node",
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
    ],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(lab.router)
app.include_router(traffic.router)


@app.middleware("http")
async def traffic_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    started = time.perf_counter()
    should_track = not (
        request.url.path.startswith("/static/")
        or request.url.path.startswith("/api/traffic")
        or request.url.path == "/favicon.ico"
    )
    if should_track:
        traffic_store.request_started()
    try:
        response = await call_next(request)
    except Exception:
        if should_track:
            traffic_store.record(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=(time.perf_counter() - started) * 1000,
                response_size=0,
            )
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    response.headers["X-Lab-Node"] = "local-api-01"
    if should_track:
        try:
            response_size = int(response.headers.get("content-length", "0"))
        except ValueError:
            response_size = 0
        traffic_store.record(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            response_size=response_size,
        )
    return response


@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/api", tags=["System"], summary="API service metadata")
async def api_root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "ready",
        "docs": "/docs",
        "dashboard": "/",
        "accounts": [
            "customer / customer123",
            "admin / admin123 (administrator + test account)",
            "guest: POST /api/auth/guest",
        ],
    }


@app.get("/api/health", tags=["System"], summary="Readiness and service health")
async def health():
    with database.connection() as conn:
        database_ok = conn.execute("SELECT 1").fetchone()[0] == 1
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "database": "ok" if database_ok else "unavailable",
        "server_time": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "host": os.getenv("TESTLAB_HOST_LABEL", "127.0.0.1"),
    }


def _download(filename: str) -> FileResponse:
    path = (DOWNLOAD_DIR / filename).resolve()
    if DOWNLOAD_DIR.resolve() not in path.parents or not path.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"{filename} is not available")
    return FileResponse(path, filename=filename)


@app.get("/downloads/openapi.json", include_in_schema=False)
async def download_openapi():
    return JSONResponse(app.openapi())


@app.get("/downloads/postman-collection", include_in_schema=False)
async def download_postman():
    path = BASE_DIR / "postman" / "FastAPI_Test_Lab.postman_collection.json"
    return FileResponse(
        path,
        filename="FastAPI_Test_Lab.postman_collection.json",
        media_type="application/json",
    )


@app.get("/downloads/jmeter-plan", include_in_schema=False)
async def download_jmeter():
    path = BASE_DIR / "jmeter" / "FastAPI_Test_Lab.jmx"
    return FileResponse(
        path,
        filename="FastAPI_Test_Lab.jmx",
        media_type="application/xml",
    )


@app.get("/downloads/sample-upload", include_in_schema=False)
async def download_sample_upload():
    return _download("sample-upload.txt")

