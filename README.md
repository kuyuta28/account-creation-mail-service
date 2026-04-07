# mail-service

Mail inbox management service. Cung cấp mailbox tạm thời để nhận email xác minh. Chạy ở port 8801.

**Stack**: FastAPI · aioimaplib · Playwright · SQLAlchemy · Pydantic

## Run

```bash
python main.py
# Override:
MAIL_HOST=0.0.0.0 MAIL_PORT=9001 python main.py
```

## Mail Providers supported

| Provider | Protocol | Notes |
|----------|----------|-------|
| testmail.app | REST API | Free tier, namespace + API key |
| mailslurp.com | REST API | Free tier, API key |
| mail.tm | REST API | Free, no-auth |
| IMAP | IMAP/aioimaplib | Bất kỳ IMAP mailbox |
| any-auto-register | adapter | External provider |

## API Endpoints

### Mailbox `GET /api/v1/`

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/mailboxes` | List mailboxes |
| POST | `/mailboxes` | Tạo mailbox mới |
| DELETE | `/mailboxes/{id}` | Xóa mailbox |
| GET | `/mailboxes/{id}/messages` | Đọc messages |
| GET | `/mailboxes/{id}/messages/{msg_id}` | Message details |

### Providers

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/providers` | List providers + config |
| POST | `/providers` | Thêm provider |
| PUT | `/providers/{name}` | Update config |

### SMS

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/sms` | List SMS providers |
| POST | `/sms` | Thêm SMS provider |

## Structure

```
src/mail_service/
  routers/
    mailbox.py          ← email CRUD + messages
    providers.py        ← provider config + tags
    sms.py              ← SMS provider management
  services/
    mailbox_service.py  ← business logic
  server.py
  schemas.py
```

## Docs

See [docs/](docs/).
