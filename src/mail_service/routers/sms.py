"""
sms.py — Router: SMS webhook receiver từ pppscn/SmsForwarder app.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..mailbox_client import (
    delete_sms_phone as delete_sms,
    get_sms_phones as list_sms,
    upsert_sms_phone as upsert_sms,
)
from ...mail.providers.sms_webhook import get_messages, make_mailbox, push_sms

router = APIRouter(prefix="/sms", tags=["sms"])
_log = logging.getLogger(__name__)


class SmsWebhookPayload(BaseModel):
    from_: str | None = None
    content: str | None = None
    sent_time: str | None = None
    sim_slot: str | None = None
    device_name: str | None = None

    model_config = {"populate_by_name": True}

    @classmethod
    def from_raw(cls, data: dict[str, Any]) -> SmsWebhookPayload:
        raw = dict(data)
        if "from" in raw:
            raw["from_"] = raw.pop("from")
        return cls(**{k: v for k, v in raw.items() if k in cls.model_fields})


class UpsertSmsPhoneBody(BaseModel):
    phone: str
    label: str = ""
    disabled: bool = False


class PatchSmsPhoneBody(BaseModel):
    label: str | None = None
    disabled: bool | None = None


@router.get("/phones")
async def list_sms_phones():
    return await list_sms()


@router.post("/phones")
async def create_or_update_sms_phone(body: UpsertSmsPhoneBody):
    phone = body.phone.strip()
    if not phone:
        return {"success": True, "data": {"created": False, "reason": "missing phone"}, "error": None, "meta": {}}
    record = await upsert_sms(phone, body.label, body.disabled)
    return {"success": True, "data": record, "error": None, "meta": {}}


@router.patch("/phones/{phone}")
async def patch_sms_phone(phone: str, body: PatchSmsPhoneBody):
    current = await list_sms()
    current_item = next((item for item in current if item["phone"] == phone), None)
    if not current_item:
        return {"success": True, "data": {"updated": False, "reason": "not found"}, "error": None, "meta": {}}
    record = await upsert_sms(
        phone,
        current_item["label"] if body.label is None else body.label,
        current_item["disabled"] if body.disabled is None else body.disabled,
    )
    return {"success": True, "data": record, "error": None, "meta": {}}


@router.delete("/phones/{phone}")
async def remove_sms_phone(phone: str):
    deleted = await delete_sms(phone)
    return {"success": True, "data": {"deleted": deleted}, "error": None, "meta": {}}


@router.post("/webhook")
async def sms_webhook(request: Request, phone: str):
    content_type: str = request.headers.get("content-type", "")
    if "application/json" in content_type:
        raw: dict[str, Any] = await request.json()
    else:
        form = await request.form()
        raw = dict(form)
        if "timestamp" in raw and "sent_time" not in raw:
            raw["sent_time"] = raw.pop("timestamp")
    _log.debug("[sms_webhook] raw payload: %s", raw)

    payload = SmsWebhookPayload.from_raw(raw)
    sender = payload.from_ or ""
    if not sender:
        raise ValueError("Missing 'from' field in SmsForwarder payload")

    text = payload.content or ""
    if not text:
        raise ValueError(f"Missing 'content' field in SmsForwarder payload from {sender!r}")

    sent_stamp: int = 0
    if payload.sent_time:
        try:
            sent_stamp = int(payload.sent_time)
        except (ValueError, TypeError):
            sent_stamp = 0

    push_sms(phone_number=phone, from_=sender, text=text, sent_stamp=sent_stamp)

    _log.info("[sms_webhook] SMS received → phone=%s from=%s sim=%s device=%s text=%r",
              phone, sender, payload.sim_slot or "", payload.device_name or "", text[:100])

    return {"success": True, "data": {"received": True, "phone": phone, "from": sender}, "error": None, "meta": {}}


@router.get("/messages/{phone_number}")
async def list_sms_messages(phone_number: str):
    box = make_mailbox(phone_number)
    msgs = get_messages(box)
    return {"success": True, "data": {"phone": phone_number, "count": len(msgs), "messages": msgs}, "error": None, "meta": {}}
