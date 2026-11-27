# syntax=docker/dockerfile:1
# sandbox-launcher image (ADR-0007 2-band; I3-18a, #202): Docker soketi faqat shu konteynerda.
# Build: `docker build -f sandbox/launcher.Dockerfile -t mlab-launcher:dev .` (repo ildizidan).
# Soket guruhi xostga bog'liq — compose'da `group_add` bilan beriladi (#203); konteyner root emas.
# Tashqariga port ochilmaydi: faqat ichki tarmoqda worker `POST /run` yuboradi.

FROM docker:29.10.0-cli@sha256:34507eb5069d8be82c95dd3b6987d4250fd5fee49b82e2509b7d7a7030740d6d
RUN apk add --no-cache python3 \
 && addgroup -S -g 10004 launcher \
 && adduser -S -D -H -u 10004 -G launcher -s /sbin/nologin launcher
COPY sandbox/launcher.py /opt/mlab/launcher.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10004:10004
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"
ENTRYPOINT ["python3", "-I", "/opt/mlab/launcher.py"]
