"""
server.py — FastAPI app entry point cho Mail Service (port 8701).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..config.settings import load_config, seed_mail_providers
from .exceptions import AppError, app_error_handler, generic_error_handler, http_exception_handler, validation_error_handler
from .routers import mailbox, providers, sms
from common.database._engine import init_async_db
from common.middleware import add_request_id_middleware, add_tracing_middleware
from common.tracing import init_tracing


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Init async PostgreSQL if DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        init_async_db(db_url)

    cfg = load_config()
    # TODO: migrate seed to PostgreSQL - disable for now
    # seed_mail_providers(cfg)
    yield


_cfg = load_config()
_cors_origins = list(_cfg.api.cors_origins)

app = FastAPI(
    title="Mail Service",
    version="1.0.0",
    description="Mail provider management service.",
    lifespan=_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Tracing & Request ID ──────────────────────────────────────────────────────
add_request_id_middleware(app)
add_tracing_middleware(app)
init_tracing("mail-service")

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_error_handler)
app.include_router(mailbox.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(sms.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mail-service"}
