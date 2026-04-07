# MailSlurp  Nghiên cứu kỹ thuật toàn diện

> Tổng hợp từ: docs.mailslurp.com, github.com/mailslurp/mailslurp-client-python, app.mailslurp.com/pricing

---

## 1. Tổng quan

MailSlurp là dịch vụ **email API trả phí** cho phép tạo real inbox theo chương trình. Khác hoàn toàn với mail.tm (no-auth, disposable), MailSlurp yêu cầu **API key** và có giới hạn theo gói.

| Tiêu chí | mail.tm | MailSlurp Free |
|---|---|---|
| Cần API key | Không | Có |
| Inboxes | Tạo thoải mái | 5 inbox tồn tại cùng lúc, 30/tháng |
| Inbound emails | Không giới hạn | 200/tháng, 150/ngày |
| Permanent inbox | Có | Không (disposable only) |
| Python SDK | Không chính thức | Có (`mailslurp-client`) |
| Blocking wait | Không (poll thủ công) | Có (`wait_for_latest_email`) |
| Gửi email | Không | Không (free tier) |

**Kết luận**: MailSlurp free tier rất hạn chế với 200 inbound/tháng. Để dùng thực sự, cần trả phí hoặc dùng nhiều API key (nhiều tài khoản).

---

## 2. Authentication

```http
GET https://api.mailslurp.com/inboxes
x-api-key: YOUR_API_KEY_HERE
```

Mọi request đều cần header `x-api-key`. Lấy key tại: app.mailslurp.com/settings/developers

---

## 3. Pricing

| Plan | Giá | Inboxes/tháng mới | Tổng inbox | Inbound/tháng | Inbound/ngày | Outbound/tháng | Storage |
|---|---|---|---|---|---|---|---|
| **Free** | $0 | 30 | **5** | **200** | 150 | 0 | 50 MB |
| **Starter** | $19.99/tháng | 1,000 | Unlimited | 5,000 | Unlimited | 1,000 | 1 GB |
| **Pro** | $69/tháng | 2,000 | Unlimited | 10,000 | Unlimited | 2,000 | 5 GB |
| **Growth** | $249/tháng | 10,000 | Unlimited | 20,000 | Unlimited | 5,000 | 20 GB |

### Lưu ý quan trọng Free tier:
- **Chỉ 5 inbox tồn tại cùng lúc**  phải xóa sau khi dùng
- **200 inbound/tháng**  đủ ~200 lần đăng ký/tháng/1 API key
- **Không có permanent inbox**  inbox bị expire
- Email domain: `@mailslurp.biz` (random subdomain)

---

## 4. Python SDK

### Cài đặt

```bash
pip install mailslurp-client
# Version hiện tại: 16.2.4 (Jul 2025)
# Hỗ trợ Python 2 & 3
```

Windows SSL fix:
```bash
pip install python-certifi-win32
```

### Cấu hình

```python
import mailslurp_client

configuration = mailslurp_client.Configuration()
configuration.api_key["x-api-key"] = "YOUR_API_KEY"
```

---

## 5. Workflow cơ bản cho account creation

```python
import mailslurp_client

def create_temp_email_and_wait(api_key: str, timeout_sec: int = 120) -> dict:
    configuration = mailslurp_client.Configuration()
    configuration.api_key["x-api-key"] = api_key

    with mailslurp_client.ApiClient(configuration) as api_client:
        inbox_ctrl = mailslurp_client.InboxControllerApi(api_client)
        wait_ctrl = mailslurp_client.WaitForControllerApi(api_client)

        # 1. Tạo inbox
        inbox = inbox_ctrl.create_inbox_with_defaults()
        email_address = inbox.email_address  # vd: abc123@mailslurp.biz
        inbox_id = inbox.id

        # 2. Dùng email_address để đăng ký service...

        # 3. Chờ email verification (CAUTION: timeout là milliseconds!)
        email = wait_ctrl.wait_for_latest_email(
            inbox_id=inbox_id,
            timeout=timeout_sec * 1000,
            unread_only=True
        )

        body = email.body
        subject = email.subject

        # 4. Xóa inbox sau khi dùng (giữ giới hạn 5 inbox/free tier)
        inbox_ctrl.delete_inbox(inbox_id=inbox_id)

        return {"email": email_address, "body": body, "subject": subject}
```

### Điểm khác biệt so với mail.tm:

| | mail.tm (hiện tại) | MailSlurp |
|---|---|---|
| Timeout unit | **giây** | **mili-giây (x1000)** |
| Polling | `time.sleep(5)` loop thủ công | Built-in blocking wait |
| Tạo inbox | POST /accounts + POST /token | `create_inbox_with_defaults()` |
| Đọc email | GET /messages?token=... | `wait_for_latest_email(inbox_id=...)` |
| Xóa sau dùng | Không cần | Nên xóa để khỏi vượt giới hạn 5 inbox |

---

## 6. API Controllers quan trọng

### InboxControllerApi

```python
inbox_ctrl = mailslurp_client.InboxControllerApi(api_client)

inbox = inbox_ctrl.create_inbox_with_defaults()

opts = mailslurp_client.CreateInboxDto()
opts.name = "test-inbox"
opts.inbox_type = "SMTP_INBOX"  # hoặc "HTTP_INBOX"
inbox = inbox_ctrl.create_inbox_with_options(opts)

inboxes = inbox_ctrl.get_all_inboxes(page=0)

inbox_ctrl.delete_inbox(inbox_id=inbox.id)
```

### WaitForControllerApi (quan trọng nhất)

```python
wait_ctrl = mailslurp_client.WaitForControllerApi(api_client)

# Blocking wait
email = wait_ctrl.wait_for_latest_email(
    inbox_id=inbox.id,
    timeout=120_000,    # 120 giây = 120,000 ms
    unread_only=True
)

# Wait với filter subject
matched = wait_ctrl.wait_for_matching_emails(
    inbox_id=inbox.id,
    count=1,
    timeout=60_000,
    match_options=mailslurp_client.MatchOptions(
        matches=[
            mailslurp_client.MatchOption(
                field="SUBJECT",
                should="CONTAIN",
                value="Verify"
            )
        ]
    )
)
```

### EmailControllerApi

```python
email_ctrl = mailslurp_client.EmailControllerApi(api_client)

email = email_ctrl.get_email(email_id=email_id)
body = email.body
subject = email.subject

# Extract verification codes tự động
codes = email_ctrl.get_email_codes(email_id=email.id)
# codes.codes -> list các code tìm được trong email

# Extract links từ HTML
links = email_ctrl.get_email_links(email_id=email.id)
# links.links -> list URLs
```

---

## 7. Chiến lược multi-key rotation

Vì free tier chỉ có 200 inbound/tháng, dùng **nhiều API key**:

```yaml
# config.yaml
mail:
  mailslurp_enabled: false
  mailslurp_api_keys:
    - "key1_abc123..."
    - "key2_def456..."
```

- Round-robin qua các keys
- 1 key = 200 inbound/tháng  3 keys = 600 registrations/tháng miễn phí

---

## 8. REST API trực tiếp (không dùng SDK)

```python
import httpx

BASE_URL = "https://api.mailslurp.com"
HEADERS = {"x-api-key": "YOUR_API_KEY"}

# Tạo inbox
resp = httpx.post(f"{BASE_URL}/inboxes/withDefaults", headers=HEADERS)
inbox = resp.json()
inbox_id = inbox["id"]
email_address = inbox["emailAddress"]

# WaitFor latest email (blocking long-poll)
# QUAN TRỌNG: httpx timeout (giây) phải > mailslurp timeout (ms)
resp = httpx.get(
    f"{BASE_URL}/waitForLatestEmail",
    headers=HEADERS,
    params={"inboxId": inbox_id, "timeout": 120000, "unreadOnly": True},
    timeout=130
)
email = resp.json()
body = email["body"]

# Xóa inbox
httpx.delete(f"{BASE_URL}/inboxes/{inbox_id}", headers=HEADERS)
```

---

## 9. Tích hợp vào dự án này

### Kế hoạch: MailSlurp là fallback khi mail.tm fail

```
mail.tm (primary) --consecutive fails--> MailSlurp (fallback, opt-in)
```

### Đề xuất: `src/mail/mailslurp.py`

```python
import mailslurp_client

def _make_cfg(api_key: str) -> mailslurp_client.Configuration:
    cfg = mailslurp_client.Configuration()
    cfg.api_key["x-api-key"] = api_key
    return cfg

def create_mailslurp_inbox(api_key: str) -> tuple[str, str]:
    """Returns (email_address, inbox_id)"""
    with mailslurp_client.ApiClient(_make_cfg(api_key)) as client:
        ctrl = mailslurp_client.InboxControllerApi(client)
        inbox = ctrl.create_inbox_with_defaults()
        return inbox.email_address, inbox.id

def wait_for_mailslurp_email(api_key: str, inbox_id: str, timeout_sec: int = 120) -> dict | None:
    """Blocking wait. Returns {"body": ..., "subject": ...} or None."""
    with mailslurp_client.ApiClient(_make_cfg(api_key)) as client:
        ctrl = mailslurp_client.WaitForControllerApi(client)
        try:
            email = ctrl.wait_for_latest_email(
                inbox_id=inbox_id,
                timeout=timeout_sec * 1000,
                unread_only=True
            )
            return {"body": email.body or "", "subject": email.subject or ""}
        except Exception:
            return None

def delete_mailslurp_inbox(api_key: str, inbox_id: str) -> None:
    with mailslurp_client.ApiClient(_make_cfg(api_key)) as client:
        ctrl = mailslurp_client.InboxControllerApi(client)
        ctrl.delete_inbox(inbox_id=inbox_id)
```

### Thêm vào `config.yaml`:
```yaml
mail:
  mailslurp_enabled: false
  mailslurp_api_keys: []
```

### Thêm vào `settings.py`:
```python
@dataclass
class MailConfig:
    # ... existing fields ...
    mailslurp_enabled: bool = False
    mailslurp_api_keys: list = field(default_factory=list)
```

---

## 10. Giới hạn & cảnh báo

| Vấn đề | Chi tiết |
|---|---|
| Timeout đơn vị ms | `timeout=120_000` không phải `120` |
| Free: 5 inbox max | Phải `delete_inbox()` sau mỗi lần dùng |
| Free: 200 inbound/tháng | Cần nhiều API keys |
| Email domain | `@mailslurp.biz` random, không customize trên free |
| `unread_only=True` | Quan trọng  nếu False có thể trả ngay email cũ |
| Daily cap free | 150 inbound/ngày |
| SDK size | `mailslurp-client` nặng (generated OpenAPI) |

---

## 11. So sánh cuối cùng

| | mail.tm | MailSlurp Free | MailSlurp Starter |
|---|---|---|---|
| Cost | $0 | $0 | $19.99/tháng |
| Volume/tháng | Không giới hạn | 200 inbound | 5,000 inbound |
| Số inbox đồng thời | Nhiều | 5 | Unlimited |
| Blocking wait | Không | Có | Có |
| Reliability | Hay downtime | Ổn định hơn | Ổn định |
| Python SDK | Không | Có | Có |

**Khuyến nghị**: Tiếp tục dùng mail.tm làm primary. Thêm MailSlurp làm fallback opt-in qua config. Cần 2-3 API keys miễn phí để có ~400-600 registrations/tháng.

---

## 12. Links tham khảo

- Python SDK: github.com/mailslurp/mailslurp-client-python
- API Reference: docs.mailslurp.com/api/
- Python docs: python.mailslurp.com
- PyPI: pypi.org/project/mailslurp-client/
- Pricing: app.mailslurp.com/pricing
- Sign up: app.mailslurp.com/sign-up/
