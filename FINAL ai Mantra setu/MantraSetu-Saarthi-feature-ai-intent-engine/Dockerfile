# ==============================================================================
# MantraSetu AgentOS Multi-Stage Production Dockerfile
# ==============================================================================

FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt || true

FROM python:3.11-slim as runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN addgroup --system --gid 1001 agentos && \
    adduser --system --uid 1001 --gid 1001 agentos

COPY --from=builder /root/.local /home/agentos/.local
ENV PATH=/home/agentos/.local/bin:$PATH

COPY --chown=agentos:agentos . .

USER agentos

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python scripts/run_production_health_check.py || exit 1

CMD ["python", "-m", "app.main"]
