# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt  ./shared-requirements.txt
COPY agent2/requirements.txt  ./agent2-requirements.txt

RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels \
      -r shared-requirements.txt \
      -r agent2-requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
 && rm -rf /wheels

COPY shared/ ./shared/
COPY agent2/app/ ./app/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')"

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8002", \
     "--workers", "2", \
     "--log-config", "/dev/null"]
