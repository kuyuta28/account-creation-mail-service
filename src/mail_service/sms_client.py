"""
sms_client.py — Async SMS phone operations via PostgreSQL.
"""
from __future__ import annotations

import os
from typing import Any

from common.database._engine import init_async_db, get_async_session
from common.database._mailboxes_async import (
    get_sms_phones_async,
    upsert_sms_phone_async,
    delete_sms_phone_async,
)

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    init_async_db(_db_url)


async def get_sms_phones() -> list[dict[str, Any]]:
    async with get_async_session() as session:
        return await get_sms_phones_async(session)


async def upsert_sms_phone(phone: str, label: str = "", disabled: bool = False) -> dict[str, Any]:
    async with get_async_session() as session:
        return await upsert_sms_phone_async(session, phone, label, disabled)


async def delete_sms_phone(phone: str) -> bool:
    async with get_async_session() as session:
        return await delete_sms_phone_async(session, phone)
