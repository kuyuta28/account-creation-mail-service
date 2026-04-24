"""
providers.py — Router: quản lý mail provider domains + service tags.
Response: unified ApiResponse envelope.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..providers_client import (
    list_provider_domains,
    list_all_providers,
    patch_provider,
    set_domain_tags,
    cycle_provider_tag,
)
from ..exceptions import AppError, ErrorCode

router = APIRouter(prefix="/providers", tags=["providers"])


class SetTagsBody(BaseModel):
    tags: list[str]


class UpdateProviderBody(BaseModel):
    disabled: bool | None = None
    label: str | None = None


@router.get("")
async def list_provider_domains_endpoint():
    return await list_provider_domains()


@router.get("/all")
async def list_all_providers_endpoint(service_tag: str | None = None):
    return await list_all_providers(service_tag)


@router.patch("/{provider_id}")
async def patch_provider_endpoint(provider_id: int, body: UpdateProviderBody):
    fields: dict[str, Any] = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise AppError(ErrorCode.VALIDATION, "No fields to update", 400)
    updated = await patch_provider(provider_id, **fields)
    if not updated:
        raise AppError(ErrorCode.NOT_FOUND, "Provider not found", 404)
    return {"success": True, "data": {"updated": True}, "error": None, "meta": {}}


@router.put("/{provider_domain}/tags")
async def set_domain_tags_endpoint(provider_domain: str, body: SetTagsBody):
    count = await set_domain_tags(provider_domain, body.tags)
    return {"success": True, "data": {"updated": count}, "error": None, "meta": {}}


@router.post("/{provider_domain}/tag/{service}/cycle")
async def cycle_tag_endpoint(provider_domain: str, service: str):
    """Cycle tri-state: (empty) → active → blocked → (empty). Trả về tags mới."""
    next_tags = await cycle_provider_tag(provider_domain, service)
    return {"success": True, "data": {"tags": next_tags}, "error": None, "meta": {}}
