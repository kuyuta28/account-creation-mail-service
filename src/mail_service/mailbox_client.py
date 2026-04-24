"""
mailbox_client.py — Async mailbox operations via PostgreSQL.
"""
from __future__ import annotations

import os
from typing import Any

from common.database._engine import init_async_db, get_async_session
from common.database._mailboxes_async import (
    get_mailbox_record_async,
    upsert_mailbox_async,
    delete_mailbox_async,
    get_available_mailboxes_async,
    save_mailbox_google_auth_state_async,
    get_mailbox_google_auth_state_async,
    upsert_sms_phone_async,
    get_sms_phones_async,
    delete_sms_phone_async,
)

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    init_async_db(_db_url)


async def get_mailbox(email: str) -> dict[str, Any] | None:
    async with get_async_session() as session:
        return await get_mailbox_record_async(session, email)


async def upsert_mailbox(
    email: str,
    app_password: str = "",
    totp_secret: str = "",
    password: str = "",
    source_email: str = "",
    label: str = "",
    disabled: bool = False,
) -> dict[str, Any]:
    async with get_async_session() as session:
        return await upsert_mailbox_async(
            session, email,
            app_password=app_password,
            totp_secret=totp_secret,
            password=password,
            source_email=source_email,
            label=label,
            disabled=disabled,
        )


async def delete_mailbox(email: str) -> bool:
    async with get_async_session() as session:
        return await delete_mailbox_async(session, email)


async def get_available_mailboxes(service: str) -> list[dict[str, Any]]:
    async with get_async_session() as session:
        return await get_available_mailboxes_async(session, service)


async def save_mailbox_google_auth_state(email: str, auth_state_json: str) -> bool:
    async with get_async_session() as session:
        return await save_mailbox_google_auth_state_async(session, email, auth_state_json)


async def get_mailbox_google_auth_state(email: str) -> str | None:
    async with get_async_session() as session:
        return await get_mailbox_google_auth_state_async(session, email)


async def get_sms_phones() -> list[dict[str, Any]]:
    async with get_async_session() as session:
        return await get_sms_phones_async(session)


async def upsert_sms_phone(phone: str, label: str = "", disabled: bool = False) -> dict[str, Any]:
    async with get_async_session() as session:
        return await upsert_sms_phone_async(session, phone, label, disabled)


async def delete_sms_phone(phone: str) -> bool:
    async with get_async_session() as session:
        return await delete_sms_phone_async(session, phone)
