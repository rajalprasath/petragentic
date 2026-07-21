# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY orchestrate/requirements.txt ./requirements.txt

RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels \
       -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
 && rm -rf /wheels

COPY orchestrate/ ./orchestrate/

# Create root __init__ shim for the package namespace
RUN echo "" > /app/orchestrate/__init__.py

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')"

CMD ["uvicorn", "orchestrate.app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8003", \
     "--workers", "2", \
     "--log-config", "/dev/null"]
