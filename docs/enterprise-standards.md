# Enterprise Standards — mail-service

> Tài liệu chuẩn hóa. Mọi module mới **PHẢI** tuân thủ trước khi merge.

---

## 1. Error Hierarchy

### Nguyên tắc
- **CẤM** dùng `RuntimeError` trực tiếp.
- **CẤM** match lỗi bằng string — phải dùng `isinstance()`.
- **CẤM** nuốt lỗi (`except: pass`) — phải raise hoặc log + raise.

### Hierarchy

```
MailServiceError (base)
├── FatalMailError             → dừng ngay, không retry
│   ├── NoProviderError        → không có provider nào configured
│   └── InvalidConfigError     → config sai/thiếu
├── RetryableMailError         → retry với provider khác
│   ├── IMAPTimeoutError       → IMAP connection timeout
│   ├── ProviderDownError      → provider không phản hồi
│   └── AuthFailedError        → IMAP auth thất bại
└── PermanentMailError         → trả lỗi về client
    ├── MailboxExpiredError    → temp mail đã hết hạn
    ├── MailNotFoundError      → không tìm thấy mail
    └── InvalidAddressError    → địa chỉ email không hợp lệ
```

### File: `src/mail_service/errors.py`

---

## 2. API Response Envelope

Mọi endpoint trả cùng 1 format:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "request_id": "uuid",
    "ts": "2026-04-03T06:37:09Z"
  }
}
```

Khi lỗi:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "MAILBOX_EXPIRED",
    "message": "Temp mailbox has expired or been deleted"
  },
  "meta": { ... }
}
```

### File: `src/mail_service/schemas.py`, `src/mail_service/errors.py`

---

## 3. Provider Interface

### Nguyên tắc
- Tất cả provider implement cùng interface.
- Không gọi provider trực tiếp từ router — phải qua interface.
- Provider failover: nếu provider chính fail → raise `RetryableMailError`, không tự fallback.

### Interface

```python
# Pure function pattern — không OOP
async def create_address(cfg: ProviderCfg) -> MailAddress: ...
async def wait_for_mail(cfg: ProviderCfg, addr: str, subject_filter: str, timeout_s: int) -> MailMessage: ...
async def get_inbox(cfg: ProviderCfg, addr: str) -> list[MailMessage]: ...
async def delete_address(cfg: ProviderCfg, addr: str) -> None: ...
```

### Providers supported
- **testmail.app** — tag-based, API
- **mailslurp** — full API
- **IMAP generic** — aioimaplib, bất kỳ inbox IMAP nào

### File: `src/mail_service/providers/`

---

## 4. Config

- **Frozen dataclass** — immutable sau khi load.
- **Strict parsing** — validate schema khi load.
- **CẤM hardcode** — mọi giá trị từ YAML hoặc env var.
- Provider creds KHÔNG log ra.

---

## 5. Service Architecture

### Nguyên tắc
- **FP only** — pure functions, không OOP, không global state.
- **Async & concurrent** — cấm blocking IO. IMAP async bắt buộc dùng `aioimaplib`.
- **Dependency injection** — inject cfg, provider. Không import global.
- **SRP** — mỗi file ≤ 200 dòng.
- **CẤM fallback** — flow sai = raise exception.

---

## 6. IMAP Async Rules

- **`aioimaplib`** — KHÔNG dùng `imaplib` (blocking).
- **Timeout bắt buộc** — `wait_for_mail` PHẢI có timeout, raise `IMAPTimeoutError` khi timeout.
- **Connection pooling tối giản** — 1 connection per request, close sau khi xong.
- **Graceful close** — `LOGOUT` trước khi close connection.
- **CẤM** `asyncio.to_thread` với `imaplib` — phải dùng async-native.

---

## 7. Testing

```
tests/
├── unit/        # Mock IMAP/HTTP responses
├── integration/ # Dùng config sandbox (testmail.app test mode)
└── conftest.py
```

- Mock `aioimaplib.IMAP4_SSL` trong unit tests.
- Test timeout path: `wait_for_mail` timeout → `IMAPTimeoutError`.
- Test provider routing: đúng provider được gọi theo config.

---

## 8. Monitoring

### Đã có
- **Sentry** — error tracking.
- **File logs** — rotation 10MB × 5 backups.
- **`/health`** endpoint bắt buộc.

### Mail-specific
- Log provider name theo mỗi request — dễ debug khi provider fail.
- Không log nội dung mail (GDPR, privacy).

---

## 9. Code Quality

- **Ruff** — BLE001, E722, UP.
- **FP style** — tránh OOP.
- Mỗi file ≤ 200 dòng.
- Không dùng `Any`.
