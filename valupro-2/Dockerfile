# =============================================================================
# ValuPro — Production Dockerfile
# Pure Python, no C-extensions. Railway builds this from the repo root
# (or from the valupro/ subdirectory if root directory is set in Railway).
# =============================================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies layer (cached unless requirements.txt changes)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Application source
COPY . .

# Non-root user
RUN addgroup --system --gid 1000 appgroup \
 && adduser  --system --uid 1000 --ingroup appgroup --no-create-home appuser \
 && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

# Single worker on startup — avoids race conditions on Railway free tier.
# PYTHONPATH=/app ensures `app.main` and `valuation_engine` are always found.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level info
