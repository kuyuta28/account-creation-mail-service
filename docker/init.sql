-- Mail Service Database Init
-- Schema auto-created by SQLAlchemy on first run

-- Create services catalog
CREATE TABLE IF NOT EXISTS services (
    name VARCHAR(64) PRIMARY KEY,
    has_registrar BOOLEAN NOT NULL DEFAULT FALSE
);

-- Create accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    service VARCHAR(64) NOT NULL,
    email VARCHAR(256) NOT NULL,
    password TEXT DEFAULT '',
    disabled BOOLEAN NOT NULL DEFAULT FALSE,
    api_key TEXT DEFAULT '',
    credits INTEGER DEFAULT 0,
    refresh_token TEXT DEFAULT '',
    access_token TEXT DEFAULT '',
    account_id VARCHAR(256) DEFAULT '',
    id_token TEXT DEFAULT '',
    expired VARCHAR(64) DEFAULT '',
    last_refresh VARCHAR(64) DEFAULT '',
    token_type VARCHAR(32) DEFAULT '',
    created_at VARCHAR(64) NOT NULL,
    updated_at VARCHAR(64) NOT NULL,
    check_status VARCHAR(32) DEFAULT '',
    quota_pct VARCHAR(16) DEFAULT '',
    last_checked VARCHAR(64) DEFAULT '',
    last_error TEXT DEFAULT '',
    session_state TEXT DEFAULT '',
    totp_secret TEXT DEFAULT '',
    app_password TEXT DEFAULT '',
    source_email TEXT DEFAULT '',
    label TEXT DEFAULT '',
    CONSTRAINT uq_service_email UNIQUE (service, email)
);

CREATE INDEX IF NOT EXISTS idx_accounts_service ON accounts(service);
CREATE INDEX IF NOT EXISTS idx_accounts_service_disabled ON accounts(service, disabled);

-- Create mail_providers table
CREATE TABLE IF NOT EXISTS mail_providers (
    id SERIAL PRIMARY KEY,
    provider_type VARCHAR(64) NOT NULL,
    api_key TEXT NOT NULL DEFAULT '',
    server_id TEXT NOT NULL DEFAULT '',
    label TEXT DEFAULT '',
    disabled BOOLEAN NOT NULL DEFAULT FALSE,
    fail_count INTEGER NOT NULL DEFAULT 0,
    cooldown_until VARCHAR(64) DEFAULT '',
    last_used VARCHAR(64) DEFAULT '',
    created_at VARCHAR(64) NOT NULL,
    updated_at VARCHAR(64) NOT NULL,
    CONSTRAINT uq_mail_provider UNIQUE (provider_type, api_key, server_id)
);

CREATE INDEX IF NOT EXISTS idx_mail_providers_type ON mail_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_mail_providers_disabled ON mail_providers(disabled);

-- Create provider_domain_tags table
CREATE TABLE IF NOT EXISTS provider_domain_tags (
    id SERIAL PRIMARY KEY,
    provider_type VARCHAR(64) NOT NULL,
    tag VARCHAR(128) NOT NULL,
    CONSTRAINT uq_domain_tag UNIQUE (provider_type, tag)
);

CREATE INDEX IF NOT EXISTS idx_domain_tag ON provider_domain_tags(tag);

-- Create mailbox_service_blocks table
CREATE TABLE IF NOT EXISTS mailbox_service_blocks (
    email VARCHAR(256) NOT NULL,
    service VARCHAR(64) NOT NULL,
    reason TEXT DEFAULT '',
    blocked_at VARCHAR(64) NOT NULL,
    PRIMARY KEY (email, service)
);

CREATE INDEX IF NOT EXISTS idx_msb_service ON mailbox_service_blocks(service);

-- Seed default providers
INSERT INTO mail_providers (provider_type, api_key, server_id, label, disabled, created_at, updated_at)
VALUES
    ('mail.tm', '', 'https://api.mail.tm', 'mail.tm', FALSE, NOW()::text, NOW()::text),
    ('guerrillamail.com', '', '', 'Guerrilla Mail', FALSE, NOW()::text, NOW()::text)
ON CONFLICT DO NOTHING;