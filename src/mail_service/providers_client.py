"""
providers_client.py — Async provider operations in mail schema via PostgreSQL.
"""
from __future__ import annotations

import os
from typing import Any

from common.database._engine import init_async_db, get_async_session
from common.database._providers_async import (
    get_providers_async,
    upsert_provider_async,
    update_provider_async,
    get_domain_tags_async,
    upsert_domain_tag_async,
)

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    init_async_db(_db_url)


async def list_provider_domains() -> list[dict[str, Any]]:
    async with get_async_session() as session:
        return await get_domain_tags_async(session)


async def list_all_providers(service_tag: str | None = None) -> list[dict[str, Any]]:
    async with get_async_session() as session:
        return await get_providers_async(session, service_tag)


async def patch_provider(provider_id: int, **fields: Any) -> bool:
    async with get_async_session() as session:
        return await update_provider_async(session, provider_id, **fields)


async def set_domain_tags(provider_domain: str, tags: list[str]) -> int:
    async with get_async_session() as session:
        for tag in tags:
            await upsert_domain_tag_async(session, provider_domain, tag)
        return len(tags)


async def cycle_provider_tag(provider_domain: str, service: str) -> list[str]:
    async with get_async_session() as session:
        all_tags = await get_domain_tags_async(session, provider_domain)
        current = next((t for t in all_tags if t.get("tag") == service), None)
        current_tag = current.get("tag", "") if current else ""

        if not current_tag:
            new_tags = [service]
        elif current_tag == "active":
            new_tags = ["blocked", service]
        else:
            new_tags = []

        for tag in new_tags:
            await upsert_domain_tag_async(session, provider_domain, tag)
        return new_tags


async def upsert_provider(
    provider_type: str,
    api_key: str = "",
    server_id: str = "",
    label: str = "",
) -> int:
    async with get_async_session() as session:
        return await upsert_provider_async(session, provider_type, api_key, server_id, label)
