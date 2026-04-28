# Enterprise Standards — mail-service

> **Phần lớn đã chuẩn hóa trong [docs/ENTERPRISE-STANDARDS.md](../../docs/ENTERPRISE-STANDARDS.md).**
> File này chỉ ghi những đặc thù riêng của mail-service.

---

## Mail-Specific Standards

### Provider Interface

Tất cả provider implement cùng interface:

```python
async def create_address(cfg: ProviderCfg) -> MailAddress: ...
async def wait_for_mail(cfg: ProviderCfg, addr: str, subject_filter: str, timeout_s: int) -> MailMessage: ...
async def get_inbox(cfg: ProviderCfg, addr: str) -> list[MailMessage]: ...
async def delete_address(cfg: ProviderCfg, addr: str) -> None: ...
```

### Providers Supported

| Provider | Type | Notes |
|----------|------|-------|
| **testmail.app** | REST API | Tag-based |
| **mailslurp** | REST API | Full API |
| **IMAP generic** | aioimaplib | Bất kỳ inbox IMAP |

### IMAP Async Rules

- **`aioimaplib`** — KHÔNG dùng `imaplib` (blocking).
- **Timeout bắt buộc** — `wait_for_mail` PHẢI có timeout.
- **Graceful close** — `LOGOUT` trước khi close.
- **CẤM** `asyncio.to_thread` với `imaplib`.

### Database

- PostgreSQL (production) hoặc SQLite (development).
- NullPool — không connection pooling.
- Retry cho "database is locked".

### Monitoring

- Log provider name theo mỗi request.
- KHÔNG log nội dung mail (GDPR, privacy).
