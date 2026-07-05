# Mail Module (`src/mail/`)

Tạo temp email và poll inbox từ nhiều provider. Provider config lưu trong SQLite DB — không cần sửa code khi thêm/xoá provider.

---

## Cấu trúc module

```
src/mail/
├── _base.py              # Shared types: Mailbox, MailCfg, HTTP helper, constants
├── client.py             # Public API + dispatcher + circuit breaker
└── providers/
    ├── mail_tm.py        # mail.tm — free, no API key
    └── testmail_app.py   # testmail.app — namespace + API key
```

Registrars chỉ gọi qua `client.py`. Không import provider modules trực tiếp.

---

## `_base.py` — Shared types

### Dataclass `Mailbox`

```python
@dataclass(frozen=True)
class Mailbox:
    email:      str
    token:      str
    account_id: str
    base_url:   str
    provider:   str = "mail.tm"   # "mail.tm" | "testmail.app"
    api_key:    str = ""
```

Immutable — sau khi tạo, không mutate. `token` và `account_id` chỉ dùng nội bộ bởi provider.

### Dataclass `MailCfg`

```python
@dataclass(frozen=True)
class MailCfg:
    cooldown_sec:          int = 120
    max_consecutive_fails: int = 3
```

Tham số cho circuit breaker — truyền vào `create_mailbox()`.

### Provider prefix constants

| Constant | Giá trị | Ý nghĩa |
|---|---|---|
| `MAIL_TM_BASES` | `("https://api.mail.tm",)` | Base URL mail.tm |
| `TESTMAIL_PREFIX` | `"testmail.app:"` | Prefix để nhận diện testmail provider string |

### `provider_kind(provider_str) → str`

Nhận diện loại provider từ provider string:

```python
provider_kind("testmail.app:ns:key")           # → "testmail.app"
provider_kind("https://api.mail.tm")           # → "mail.tm"
```

---

## `client.py` — Public API

### `create_mailbox(providers, cfg) → Mailbox`

Tạo inbox mới. Tự động shuffle + failover qua các provider, có circuit breaker.

```python
from src.mail.client import create_mailbox, Mailbox

# Lấy provider từ DB qua config
providers = cfg.mail.providers_for("elevenlabs")  # → ("testmail.app:ns:key", ...)
mailbox: Mailbox = await create_mailbox(providers, cfg.mail_cfg)
# Output: "Temp mail (testmail.app): abc123@inbox.testmail.app"
```

| Parameter | Type | Default | Mô tả |
|---|---|---|---|
| `providers` | `Sequence[str] or None` | `None` | Danh sách provider strings — nếu `None` dùng `mail.tm` |
| `cfg` | `MailCfg` | `MailCfg()` | Circuit breaker config |

**Luồng xử lý:**
1. Shuffle providers để phân tải (tránh cùng provider bị hit liên tục)
2. Bỏ qua providers đang trong cooldown (circuit breaker mở)
3. Thử từng provider còn lại — trả về `Mailbox` khi thành công
4. Nếu tất cả alive providers lỗi → đợi cooldown ngắn nhất, retry
5. Raise `RuntimeError` nếu không provider nào phục hồi

**Raises**: `RuntimeError("All temp mail providers failed: ...")` khi không provider nào khả dụng.

---

### `get_messages(box) → List[Dict]`

Trả về danh sách messages trong inbox (không kèm body đầy đủ).

```python
messages = await get_messages(box)
# [{"id": "msg_id", "from": {...}, "subject": "Verify your email", ...}]
```

---

### `get_message_body(box, message_id) → str`

Lấy nội dung HTML/text của 1 message cụ thể.

```python
body = await get_message_body(box, messages[0]["id"])
# → "<html>...</html>" hoặc text
```

---

### `wait_for_message(box, from_contains, subject_contains, timeout, poll_interval) → Optional[Dict]`

Poll inbox cho đến khi tìm được email match hoặc timeout.

| Parameter | Type | Default | Mô tả |
|---|---|---|---|
| `from_contains` | str | `""` | Substring phải có trong sender address (case-insensitive) |
| `subject_contains` | str | `""` | Substring phải có trong subject (case-insensitive) |
| `timeout` | int | `120` | Timeout tính bằng giây |
| `poll_interval` | int | `5` | Interval poll (chỉ áp dụng cho mail.tm) |

**Returns**: Dict đầy đủ kèm field `body` (đã lấy từ `get_message_body()`), hoặc `None` nếu hết timeout.

```python
msg = await wait_for_message(
    box,
    from_contains="elevenlabs",
    subject_contains="verify",
    timeout=120,
)
if msg:
    link = extract_link(msg["body"], contains="verify")
```

---

### `extract_link(body, contains) → Optional[str]`

Extract URL đầu tiên trong body text, có thể filter theo substring.

```python
extract_link(body, contains="verify")
# → "https://elevenlabs.io/verify?token=abc123"

extract_link(body)
# → URL đầu tiên bất kỳ

extract_link("no links here")
# → None
```

---

## Circuit Breaker

Module-level state theo dõi failures per provider:

```python
_provider_fail_counts:    Dict[str, int]   = {}
_provider_cooldown_until: Dict[str, float] = {}
```

**Cơ chế:**
- Mỗi lần provider lỗi → `_mark_provider_fail()` tăng counter
- Khi counter >= `max_consecutive_fails` → provider vào cooldown `cooldown_sec` giây
- `_is_provider_down(provider)` check deadline — nếu hết hạn thì tự reset
- Thành công → `_mark_provider_ok()` clear toàn bộ state của provider đó

| Config | Default | Ý nghĩa |
|---|---|---|
| `cooldown_sec` | `120` | Thời gian cooldown khi provider fail liên tiếp |
| `max_consecutive_fails` | `3` | Số lần fail liên tiếp trước khi vào cooldown |

---

## Provider Strings

Mỗi provider được identify bằng một string duy nhất:

| Provider | Format | Ví dụ |
|---|---|---|
| mail.tm | `https://api.mail.tm` | `https://api.mail.tm` |
| testmail | `testmail.app:<namespace>:<api_key>` | `testmail.app:im4vw:eyJhbGci...` |

Provider strings được lấy từ DB qua `cfg.mail.providers_for(service_name)`. Không hardcode trong registrar.

---

## Provider modules (`src/mail/providers/`)

Mỗi provider module export đúng 4 async functions với cùng interface:

```python
# create_mailbox nhận provider string đầy đủ, parse thông tin từ đó
async def create_mailbox(provider: str) -> Mailbox: ...
async def get_messages(box: Mailbox) -> List[Dict]: ...
async def get_message_body(box: Mailbox, message_id: str) -> str: ...
async def wait_for_message(box: Mailbox, ...) -> Optional[Dict]: ...
```

### mail.tm (`mail_tm.py`)

- **Auth**: Không cần API key trước. Create account on-the-fly.
- **Luồng `create_mailbox`**: `GET /domains` → random username → `POST /accounts` → `POST /token` → trả `Mailbox`
- **Lưu ý**: hay bị 502, circuit breaker sẽ failover sang provider khác

### testmail.app (`testmail_app.py`)

- **Auth**: Namespace + API key (lấy từ provider string `testmail.app:<namespace>:<api_key>`)
- **Email pattern**: `<namespace>.<random_tag>@inbox.testmail.app`
- **`wait_for_message`**: Poll `GET /api/json?apikey=...&namespace=...&tag=...`

---

## DB-based Provider Config

Provider strings được quản lý trong SQLite (`data/accounts.db`):

```
mail_providers table:
  id, provider_domain, api_key, label, disabled, created_at

provider_domain_tags table:
  provider_domain, tag
```

Lấy providers cho một service:

```python
providers = cfg.mail.providers_for("elevenlabs")
# → ("testmail.app:ns:key1", "testmail.app:ns:key2")
```

Khi `tags = ["any"]` → provider serve tất cả services.
Khi `tags = ["elevenlabs", "chatgpt"]` → provider chỉ serve 2 service đó.

Quản lý qua API:
- `GET /api/v1/providers` → danh sách provider types với stats
- `PUT /api/v1/providers/{type}/tags` → cập nhật tags

---

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Xử lý |
|---|---|---|
| `RuntimeError: All temp mail providers failed` | Tất cả providers đang cooldown hoặc lỗi | Kiểm tra DB có providers active không, chờ cooldown |
| `RuntimeError: No usable temp mail providers configured` | `providers` list trống | Kiểm tra `cfg.mail.providers_for(service)` có trả dữ liệu không |
| `wait_for_message` trả về `None` | Email chưa đến trong timeout | Tăng `timeout` hoặc kiểm tra email thực sự được gửi |
| mail.tm 502 | Server side issue | Circuit breaker tự failover — bình thường |
