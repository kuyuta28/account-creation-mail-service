"""
mail/client.py — Public API + dispatcher + circuit breaker.

Dispatcher route theo box.provider → đúng provider module xử lý.
Circuit breaker: tự động failover và cooldown khi provider lỗi liên tiếp.

Public API:
  create_mailbox(providers=None, cfg=MailCfg()) -> Mailbox
  get_messages(box)                             -> List[Dict]
  get_message_body(box, message_id)             -> str
  wait_for_message(box, ...)                    -> Optional[Dict]
  extract_link(body, contains)                  -> Optional[str]
"""
from __future__ import annotations

import asyncio
import itertools
import re
from collections.abc import Sequence


from ._base import (
    LogFn, MailCfg, Mailbox, _tprint,
    provider_display_name, provider_kind,
    get_mail_tm_bases,
)
from .providers import mail_tm, mailslurp_com, testmail_app, guerrillamail_com, mailosaur_com, gmail, sms_webhook
from .circuit_breaker import CircuitBreakerConfig, CircuitBreakerState

__all__ = [
    "LogFn",
    "MailCfg",
    "Mailbox",
    "create_mailbox",
    "extract_link",
    "get_message_body",
    "get_messages",
    "make_gmail_mailbox",
    "wait_for_message",
]


def _get_circuit_breaker() -> CircuitBreakerState:
    """Read CircuitBreakerState from app context."""
    from common.context import get_app_context
    ctx = get_app_context()
    if ctx.mail_state is None:
        raise RuntimeError("mail_state not initialized in AppContext")
    return ctx.mail_state


# ── Provider routing ──────────────────────────────────────────────────────────

_round_robin_counter = itertools.count()


def _normalize_providers(providers: Sequence[str] | None) -> tuple[str, ...]:
    source = get_mail_tm_bases() if providers is None else providers
    items = tuple(str(p).rstrip("/") for p in source if str(p).strip())
    unique = tuple(dict.fromkeys(items))
    if not unique:
        raise RuntimeError("No temp mail providers configured")
    return unique


def _rotated_providers(providers: Sequence[str] | None) -> tuple[str, ...]:
    """Round-robin: mỗi lần gọi bắt đầu từ provider kế tiếp, đảm bảo phân tán."""
    items = list(_normalize_providers(providers))
    if len(items) <= 1:
        return tuple(items)
    idx = next(_round_robin_counter) % len(items)
    return tuple(items[idx:] + items[:idx])


async def _create_mailbox_on_provider(provider: str, log_fn: LogFn | None = None) -> Mailbox:
    match provider_kind(provider):
        case "mailslurp.com":
            return await mailslurp_com.create_mailbox(provider, log_fn=log_fn)
        case "testmail.app":
            return await testmail_app.create_mailbox(provider)
        case "guerrillamail.com":
            return await guerrillamail_com.create_mailbox(provider, log_fn=log_fn)
        case "mailosaur.com":
            return await mailosaur_com.create_mailbox(provider)
        case "gmail.com":
            # format: "gmail.com:{email}:{base64_json}"
            # base64_json = base64({"s": session_state, "p": password, "t": totp_secret})
            parts = provider.split(":", 2)
            if len(parts) != 3:
                raise ValueError(f"Invalid gmail provider format: {provider!r}. Expected: gmail.com:{{email}}:{{base64_meta}}")
            import base64 as _b64
            import json as _json
            _, email, b64meta = parts
            meta = _json.loads(_b64.urlsafe_b64decode(b64meta + "=="))
            return gmail.make_mailbox(
                email=email,
                google_auth_state=meta.get("s", ""),
                password=meta.get("p", ""),
                totp_secret=meta.get("t", ""),
            )
        case "sms.webhook":
            # format: "sms.webhook:{phone_number}"
            parts = provider.split(":", 1)
            if len(parts) != 2 or not parts[1].strip():
                raise ValueError(f"Invalid sms.webhook provider format: {provider!r}. Expected: sms.webhook:{{phone_number}}")
            return sms_webhook.make_mailbox(parts[1].strip())
        case _:
            return await mail_tm.create_mailbox(provider, log_fn=log_fn)


# ── Public API ────────────────────────────────────────────────────────────────

async def create_mailbox(
    providers: Sequence[str] | None = None,
    cfg: MailCfg = MailCfg(),
    log_fn: LogFn | None = None,
) -> Mailbox:
    _log = log_fn or _tprint
    errors: list[str] = []
    all_providers = _rotated_providers(providers)
    if not all_providers:
        raise RuntimeError("No usable temp mail providers configured")

    cb = _get_circuit_breaker()

    alive = [p for p in all_providers if not cb.is_down(p)]
    down  = [p for p in all_providers if cb.is_down(p)]

    for provider in alive:
        label = provider_display_name(provider)
        try:
            mailbox = await _create_mailbox_on_provider(provider, log_fn=log_fn)
            cb.mark_ok(provider)
            _log(f"Temp mail ({label}): {mailbox.email}")
            return mailbox
        except Exception as exc:  # noqa: BLE001 — batch collector: per-item error isolation
            triggered = cb.mark_fail(provider, log_fn=log_fn)
            errors.append(f"{label}: {exc}")
            if not triggered:
                _log(f"  [mail] {label} fail -> swap provider...")

    if down:
        await asyncio.sleep(1)  # brief wait then retry down providers
        return await create_mailbox(providers, cfg, log_fn=log_fn)

    if any(not cb.is_down(p) for p in all_providers):
        return await create_mailbox(providers, cfg, log_fn=log_fn)

    stats = cb.get_stats()
    if stats["cooldown_providers"]:
        await asyncio.sleep(1)
        return await create_mailbox(providers, cfg, log_fn=log_fn)

    raise RuntimeError("All temp mail providers failed: " + " | ".join(errors))


def make_gmail_mailbox(email: str, app_password: str) -> Mailbox:
    """Tạo Mailbox từ Gmail address + App Password (không qua create_mailbox)."""
    return gmail.make_mailbox(email, app_password)


async def get_messages(box: Mailbox) -> list[dict]:
    match box.provider:
        case "mailslurp.com":
            return await mailslurp_com.get_messages(box)
        case "testmail.app":
            return await testmail_app.get_messages(box)
        case "guerrillamail.com":
            return await guerrillamail_com.get_messages(box)
        case "mailosaur.com":
            return await mailosaur_com.get_messages(box)
        case "gmail.com":
            return await gmail.get_messages(box)
        case "sms.webhook":
            return sms_webhook.get_messages(box)
        case _:
            return await mail_tm.get_messages(box)


async def get_message_body(box: Mailbox, message_id: str) -> str:
    match box.provider:
        case "mailslurp.com":
            return await mailslurp_com.get_message_body(box, message_id)
        case "testmail.app":
            return await testmail_app.get_message_body(box, message_id)
        case "guerrillamail.com":
            result = await guerrillamail_com.get_message_body(box, message_id)
            return result.get("body", "")
        case "mailosaur.com":
            return await mailosaur_com.get_message_body(box, message_id)
        case "gmail.com":
            return await gmail.get_message_body(box, message_id)
        case "sms.webhook":
            # SMS không có body riêng — trả text trực tiếp từ message dict
            msgs = sms_webhook.get_messages(box)
            hit = next((m for m in msgs if m["id"] == message_id), None)
            return hit["text"] if hit else ""
        case _:
            return await mail_tm.get_message_body(box, message_id)


async def wait_for_message(
    box: Mailbox,
    from_contains: str = "",
    subject_contains: str = "",
    timeout: int = 120,
    poll_interval: int = 5,
    log_fn: LogFn | None = None,
) -> dict | None:
    match box.provider:
        case "mailslurp.com":
            return await mailslurp_com.wait_for_message(box, from_contains, subject_contains, timeout, log_fn=log_fn)
        case "testmail.app":
            return await testmail_app.wait_for_message(box, from_contains, subject_contains, timeout, log_fn=log_fn)
        case "guerrillamail.com":
            return await guerrillamail_com.wait_for_message(box, from_contains, subject_contains, timeout, log_fn=log_fn)
        case "mailosaur.com":
            return await mailosaur_com.wait_for_message(box, from_contains, subject_contains, timeout, log_fn=log_fn)
        case "gmail.com":
            return await gmail.wait_for_message(box, from_contains, subject_contains, timeout, poll_interval, log_fn=log_fn)
        case "sms.webhook":
            return await sms_webhook.wait_for_message(
                box,
                from_contains=from_contains,
                body_contains=subject_contains,
                timeout=timeout,
                poll_interval=float(poll_interval),
                log_fn=log_fn,
            )
        case _:
            return await mail_tm.wait_for_message(box, from_contains, subject_contains, timeout, poll_interval, log_fn=log_fn)


def extract_link(body: str, contains: str = "") -> str | None:
    """Extract first URL tu body text, co the filter theo substring."""
    urls = re.findall(r"https?://[^\s'\"<>]+", body)
    if contains:
        urls = [url for url in urls if contains.lower() in url.lower()]
    return urls[0] if urls else None
