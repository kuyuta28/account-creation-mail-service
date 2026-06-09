# syntax=docker/dockerfile:1.7
# --- builder ---------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# OS deps needed at build time only
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

# Layer 1: deps (cache hit on pyproject.toml change only)
COPY mail-service/pyproject.toml ./pyproject.toml
COPY common/src ./common/src
RUN pip install --no-cache-dir \
        "fastapi>=0.111.0" "uvicorn[standard]>=0.30.0" "httpx>=0.25.0" \
        "pydantic>=2.0.0" "PyYAML>=6.0" "sqlalchemy>=2.0" "asyncpg>=0.29.0" \
        "requests>=2.31.0" "aioimaplib>=2.0.0" "aiofiles>=23.0.0" \
        "playwright>=1.50.0" "sentry-sdk[fastapi]>=2.0.0"

# Layer 2: source
COPY mail-service/src ./src
COPY mail-service/main.py ./main.py

# --- runtime ---------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MAIL_HOST=0.0.0.0 \
    MAIL_PORT=8701 \
    PYTHONPATH=/app/common/src:/app/src

# Non-root user first so mkdir chown sticks
RUN groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && apt-get update \
 && apt-get install -y --no-install-recommends wget ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy site-packages and stdlib from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=app:app mail-service/src ./src
COPY --chown=app:app mail-service/main.py ./main.py
COPY --chown=app:app common/src ./common/src

# Playwright browsers (chromium only, no shell)
USER root
RUN pip install --no-cache-dir playwright \
 && playwright install --no-shell chromium \
 && rm -rf /var/cache/ms-playwright/* /tmp/* /root/.cache

# Runtime dirs
RUN mkdir -p /app/data /app/logs /tmp/app \
 && chown -R app:app /app/data /app/logs /tmp/app
VOLUME ["/app/data", "/app/logs"]

USER app
EXPOSE 8701

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8701/api/health || exit 1

CMD ["python", "main.py"]
