# syntax=docker/dockerfile:1
# Sandbox image (ADR-0007; AGR-03; I3-05): talaba kodi va yashirin testlar shu yerda bajariladi.
# Build kontekst: repo ildizi (`docker build -f sandbox/Dockerfile -t mlab-sandbox:dev .`) — datasetlar content/ dan.
# Cheklovlar (tarmoq yo'q, read-only, xotira, pids, vaqt) image'da emas, launcher `docker run` parametrlarida.

FROM python:3.14.10-slim@sha256:22eafb370920ad8b429e0aec3fff433e0669968519f5d60469d83729c138b28b AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY sandbox/requirements.txt /tmp/requirements.txt
# Faqat tayyor wheel'lar va hash tekshiruvi: versiyalar Pyodide 314.0.7 bilan bir xil (requirements.in).
RUN /opt/venv/bin/pip install --require-hashes --only-binary=:all: -r /tmp/requirements.txt \
 && /opt/venv/bin/pip uninstall -y pip setuptools

FROM python:3.14.10-slim@sha256:22eafb370920ad8b429e0aec3fff433e0669968519f5d60469d83729c138b28b AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
# Root'siz foydalanuvchi (ADR-0007: UID 10003); uy katalogi yo'q, yozish faqat launcher bergan /tmp tmpfs'ga.
RUN groupadd --system --gid 10003 sandbox \
 && useradd --system --uid 10003 --gid sandbox --no-create-home --shell /usr/sbin/nologin sandbox \
 && rm -rf /usr/local/lib/python3.14/ensurepip /usr/local/bin/pip* /usr/local/lib/python3.14/site-packages/pip*
COPY --from=builder /opt/venv /opt/venv
COPY sandbox/mlab.py /opt/venv/lib/python3.14/site-packages/mlab.py
COPY sandbox/runner.py /opt/mlab/runner.py
COPY content/datasets/*.csv /opt/mlab/datasets/
# Sinov paytida matplotlib shriftlar keshini oldindan yaratib qo'yamiz (read-only image'da qayta yozilmaydi).
RUN MPLCONFIGDIR=/opt/mlab/mpl python -c "import matplotlib.pyplot" && chmod -R a+rX /opt/mlab /opt/venv
ENV MPLCONFIGDIR=/opt/mlab/mpl
USER 10003:10003
WORKDIR /tmp
# -I: PYTHON* muhit o'zgaruvchilari, foydalanuvchi site va joriy katalog sys.path'ga kirmaydi.
ENTRYPOINT ["python", "-I", "/opt/mlab/runner.py"]
