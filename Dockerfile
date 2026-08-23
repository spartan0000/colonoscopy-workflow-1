# ---- Build stage: install dependencies with uv ----
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# psycopg2 builds from source, so it needs gcc and the libpq headers
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies from the lockfile only (cached until pyproject/uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- Runtime stage ----
FROM python:3.13-slim

# psycopg2 needs the libpq runtime library
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv ./.venv
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
