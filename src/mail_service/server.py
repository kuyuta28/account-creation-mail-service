"""
server.py — FastAPI app entry point cho Mail Service (port 8701).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import AppError, app_error_handler, generic_error_handler, http_exception_handler, validation_error_handler
from .routers import mailbox, providers, sms

app = FastAPI(title="Mail Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://localhost:1421",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
