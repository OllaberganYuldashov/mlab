# syntax=docker/dockerfile:1
# Frontend + Caddy (R0-15; ADR-0004): React build → Caddy (statik + reverse proxy + avtomatik HTTPS).
# Build kontekst: repo ildizi (`docker build -f frontend/Dockerfile .`).

FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2-alpine AS runtime
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv/frontend
# Caddy 80/443 ni tinglaydi: root'siz ishlashi uchun bind imkoniyati image'da (cap_net_bind_service) bor.
RUN addgroup -S -g 10002 web && adduser -S -u 10002 -G web -H -s /sbin/nologin web \
 && mkdir -p /data /config && chown -R web:web /data /config \
 && setcap -r /usr/bin/caddy 2>/dev/null; setcap cap_net_bind_service=+ep /usr/bin/caddy
USER web
EXPOSE 80 443
