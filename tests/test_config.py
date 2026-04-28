"""Tests cho mail-service config loading — single source of truth."""
from __future__ import annotations

import sys
from pathlib import Path

# common path is in conftest.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config.settings import (
    AppConfig,
    ApiConfig,
    MailConfig,
    load_config,
)


# ── Test: MailConfig defaults ─────────────────────────────────────────────

class TestMailConfigDefaults:
    """Khi không có config, MailConfig phải trả default values."""

    def test_default_http_timeout(self):
        cfg = MailConfig()
        assert cfg.http_timeout_sec == 15

    def test_default_wait_timeout(self):
        cfg = MailConfig()
        assert cfg.wait_timeout_sec == 120

    def test_default_poll_interval(self):
        cfg = MailConfig()
        assert cfg.poll_interval_sec == 5

    def test_default_max_retries(self):
        cfg = MailConfig()
        assert cfg.max_retries == 3

    def test_default_retry_max_delay(self):
        cfg = MailConfig()
        assert cfg.retry_max_delay_sec == 30

    def test_default_cooldown(self):
        cfg = MailConfig()
        assert cfg.cooldown_sec == 120

    def test_default_retryable_codes(self):
        cfg = MailConfig()
        assert cfg.retryable_status_codes == (429, 500, 502, 503, 504)


# ── Test: ApiConfig defaults ──────────────────────────────────────────────

class TestApiConfigDefaults:
    """ApiConfig CORS origins defaults."""

    def test_default_cors_origins(self):
        cfg = ApiConfig()
        assert len(cfg.cors_origins) >= 3
        assert "http://localhost:1420" in cfg.cors_origins
        assert "tauri://localhost" in cfg.cors_origins


# ── Test: Full config loading ─────────────────────────────────────────────

class TestFullConfigLoading:
    """Load config từ YAML files thực tế."""

    def test_load_config_returns_appconfig(self):
        cfg = load_config()
        assert isinstance(cfg, AppConfig)

    def test_mail_config_has_new_fields(self):
        cfg = load_config()
        assert hasattr(cfg.mail, "http_timeout_sec")
        assert hasattr(cfg.mail, "wait_timeout_sec")
        assert hasattr(cfg.mail, "poll_interval_sec")
        assert hasattr(cfg.mail, "max_retries")
        assert hasattr(cfg.mail, "retry_max_delay_sec")

    def test_mail_http_timeout_from_yaml(self):
        cfg = load_config()
        assert cfg.mail.http_timeout_sec == 15

    def test_mail_wait_timeout_from_yaml(self):
        cfg = load_config()
        assert cfg.mail.wait_timeout_sec == 120

    def test_mail_poll_interval_from_yaml(self):
        cfg = load_config()
        assert cfg.mail.poll_interval_sec == 5

    def test_mail_max_retries_from_yaml(self):
        cfg = load_config()
        assert cfg.mail.max_retries == 3

    def test_mail_retry_max_delay_from_yaml(self):
        cfg = load_config()
        assert cfg.mail.retry_max_delay_sec == 30

    def test_cors_origins_from_yaml(self):
        cfg = load_config()
        assert "https://tauri.localhost" in cfg.api.cors_origins