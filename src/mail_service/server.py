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

from ..config.settings import load_config
from .exceptions import AppError, app_error_handler, generic_error_handler, http_exception_handler, validation_error_handler
from .routers import mailbox, providers, sms
from common.context import init_app_context, get_app_context
from common.database._engine import init_async_db
from common.middleware import add_request_id_middleware, add_tracing_middleware
from common.tracing import init_tracing
from ..mail.circuit_breaker import CircuitBreakerState
from .services.mailbox_store import MailboxStore


_cfg = load_config()
_cors_origins = list(_cfg.api.cors_origins)

# Init state managers
mail_state = CircuitBreakerState()
mailbox_store = MailboxStore()

# Set app context before creating FastAPI app so lifespan can access it
init_app_context(config=_cfg, db_engine=None, mail_state=mail_state, mailbox_store=mailbox_store)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Mail service lifespan — init → yield dict → shutdown."""
    ctx = get_app_context()

    # Startup: init all state managers
    if ctx.mail_state:
        await ctx.mail_state.init()
    if ctx.mailbox_store:
        await ctx.mailbox_store.init()

    yield {"mail_state": ctx.mail_state, "mailbox_store": ctx.mailbox_store}

    # Graceful shutdown in reverse order
    if ctx.mailbox_store:
        await ctx.mailbox_store.shutdown()
    if ctx.mail_state:
        await ctx.mail_state.shutdown()


app = FastAPI(
    title="Mail Service",
    version="1.0.0",
    description="Mail provider management service.",
    lifespan=lifespan,
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


@app.on_event("startup")
async def _startup():
    # Init async PostgreSQL if DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        init_async_db(db_url)
