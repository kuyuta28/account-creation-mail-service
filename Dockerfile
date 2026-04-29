FROM python:3.12-slim

WORKDIR /app

# Install system deps for playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install playwright browser
RUN pip install playwright \
    && playwright install chromium --with-deps

# Copy project files (context = project root)
COPY mail-service/pyproject.toml ./pyproject.toml
COPY mail-service/src ./src
COPY mail-service/main.py .
COPY common/src ./common/src

# Install dependencies
RUN pip install --no-cache-dir -e . --no-deps \
    && pip install --no-cache-dir fastapi uvicorn httpx pydantic PyYAML sqlalchemy requests aioimaplib aiofiles sentry-sdk

# Create data directory
RUN mkdir -p /app/data /app/logs

EXPOSE 8701

ENV MAIL_HOST=0.0.0.0
ENV MAIL_PORT=8701
ENV PYTHONPATH=/app/common/src:/app/src

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:8701/api/health || exit 1

CMD ["python", "main.py"]
