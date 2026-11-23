# syntax=docker/dockerfile:1
# Prod image (R0-15; ADR-0004): multi-stage, root'siz, bog'liqliklar lockfile bo'yicha.
# Build kontekst: repo ildizi (`docker build -f backend/Dockerfile .`) — kontent `content/` ham image'ga kiradi.

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
# Avval faqat bog'liqliklar: kod o'zgarganda bu qatlam keshdan olinadi.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod
# Root'siz foydalanuvchi (UID 10001); yozish faqat /app/staticfiles va /tmp da.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=root:root backend/ ./
COPY --chown=root:root content/ /app/content/
RUN mkdir -p /app/staticfiles && chown app:app /app/staticfiles
USER app
EXPOSE 8000
# Healthcheck compose'da (deploy/compose.prod.yaml): PROD'da HTTPS yo'naltirish Host va X-Forwarded-Proto talab qiladi.
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
