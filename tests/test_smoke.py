"""tests/test_smoke.py — Smoke tests cho mail-service: import app, config loads, common exports.

Chạy < 2s. Mục đích: phát hiện ngay nếu module-level import crash,
config load lỗi, hoặc server.py không tạo được FastAPI app.

NOTE: server.py dùng relative imports (from ..config.settings) nên phải
import qua absolute path "src.mail_service.server" thay vì trực tiếp.
"""
from __future__ import annotations

import importlib

import pytest


# ── Server import smoke test ────────────────────────────────────────────────

class TestServerImport:
    """server.py phải import được qua absolute path — phát hiện circular import,
    missing dependency, hoặc module-level code chết."""

    def test_import_server_module(self):
        mod = importlib.import_module("src.mail_service.server")
        app = mod.app
        assert app.title == "Mail Service"

    def test_app_has_health_route(self):
        mod = importlib.import_module("src.mail_service.server")
        app = mod.app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/health" in routes

    def test_app_has_mailbox_routes(self):
        mod = importlib.import_module("src.mail_service.server")
        app = mod.app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/mailbox" in r for r in routes)


# ── Config smoke test ──────────────────────────────────────────────────────

class TestConfigSmoke:
    """load_config() phải chạy được."""

    def test_load_config_no_crash(self):
        from config.settings import load_config
        cfg = load_config()
        assert cfg is not None

    def test_load_config_returns_appconfig(self):
        from config.settings import load_config, AppConfig
        cfg = load_config()
        assert isinstance(cfg, AppConfig)

    def test_cors_origins_not_empty(self):
        from config.settings import load_config
        cfg = load_config()
        assert len(cfg.api.cors_origins) > 0


# ── Common database exports smoke test ───────────────────────────────────────

class TestCommonDatabaseExports:
    """common.database phải export đủ functions mà mail-service dùng."""

    def test_import_sms_phone_functions(self):
        from common.database import delete_sms_phone, get_sms_phones, upsert_sms_phone
        assert callable(delete_sms_phone)
        assert callable(get_sms_phones)
        assert callable(upsert_sms_phone)

    def test_import_mail_provider_functions(self):
        from common.database import get_mail_providers, upsert_mail_provider
        assert callable(get_mail_providers)
        assert callable(upsert_mail_provider)

    def test_import_init_db(self):
        from common.database import init_db
        assert callable(init_db)


# ── Mail base smoke test ────────────────────────────────────────────────────

class TestMailBaseSmoke:
    """mail._base phải import được."""

    def test_import_mail_base(self):
        from mail._base import request_with_retry
        assert callable(request_with_retry)