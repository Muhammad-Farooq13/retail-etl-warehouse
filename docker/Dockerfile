# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runtime
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY src/ ./src/
COPY sql/ ./sql/
COPY configs/ ./configs/

RUN mkdir -p data/raw data/warehouse artifacts/reports artifacts/figures \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health').read()" || exit 1

# The warehouse is not pre-built at image-build time — run the `etl` service
# in docker-compose.yml (or `make pipeline`) once to populate data/warehouse
# before serving the analytics API.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
