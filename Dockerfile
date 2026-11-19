# syntax=docker.io/docker/dockerfile:1

FROM docker.io/python:3.15-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-editable

COPY . .
RUN uv sync --locked --no-editable


FROM docker.io/python:3.15-alpine

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    WATCH=true

ENTRYPOINT ["hdns2mikrotik"]
CMD ["sync"]
