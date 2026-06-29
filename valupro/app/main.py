"""
app/main.py
============
FastAPI application entry point for ValuPro.

Railway start command:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2

Routes registered:
    GET  /              → landing page
    GET  /health/live   → Railway healthcheck
    GET  /valuation     → DCF input form
    POST /calculate     → JSON valuation endpoint
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers.valuation_router import router as valuation_router

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file so they work from any cwd)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_HERE, "static")
_TEMPLATES_DIR = os.path.join(_HERE, "templates")

_START = time.monotonic()

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    env = os.getenv("APP_ENV", "production").lower()
    is_dev = env in ("development", "dev", "local")

    app = FastAPI(
        title="ValuPro — DCF Valuation Platform",
        description="Professional Discounted Cash Flow Valuation Platform",
        version="1.0.0",
        docs_url="/docs" if is_dev else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    # Templates
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)

    # --- Health ---
    @app.get("/health/live", include_in_schema=False)
    async def health_live():
        return {"status": "ok", "uptime_seconds": round(time.monotonic() - _START, 1)}

    # --- Landing page ---
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def landing(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    # --- Valuation router ---
    app.include_router(valuation_router)

    return app


app = create_app()
