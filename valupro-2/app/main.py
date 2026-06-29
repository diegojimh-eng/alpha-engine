"""
app/main.py — ValuPro FastAPI entry point

Railway runs: uvicorn app.main:app --host 0.0.0.0 --port $PORT
PYTHONPATH=/app is set in the Dockerfile so all imports resolve correctly.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import asynccontextmanager

# Ensure the project root (/app inside Docker, repo root locally) is on the path.
# This makes both `app.*` and `valuation_engine.*` importable everywhere.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers.valuation_router import router as valuation_router

# Absolute paths — work regardless of cwd
_HERE          = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR    = os.path.join(_HERE, "static")
_TEMPLATES_DIR = os.path.join(_HERE, "templates")

_START = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    yield


def create_app() -> FastAPI:
    env    = os.getenv("APP_ENV", "production").lower()
    is_dev = env in ("development", "dev", "local")

    app = FastAPI(
        title="ValuPro — DCF Valuation Platform",
        description="Professional Discounted Cash Flow Valuation Platform",
        version="1.0.0",
        docs_url="/docs" if is_dev else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files & templates — mounted before routes
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)

    # ── Health (must respond instantly — Railway polls this) ──────────────────
    @app.get("/health/live", include_in_schema=False)
    async def health_live():
        return JSONResponse(
            {"status": "ok", "uptime_seconds": round(time.monotonic() - _START, 1)},
            status_code=200,
        )

    # ── Landing page ──────────────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def landing(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    # ── Valuation router (GET /valuation, POST /calculate) ───────────────────
    app.include_router(valuation_router)

    return app


app = create_app()
