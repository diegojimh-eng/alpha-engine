# =============================================================================
# ValuPro — Production Dockerfile
# Pure Python stack — no C-extension compilation required.
# Build time: ~30 seconds on Railway.
# =============================================================================

FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout (better Railway logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (cached layer — only re-runs if requirements.txt changes)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy the full application source
COPY . .

# Non-root user for security
RUN addgroup --system --gid 1000 appgroup \
 && adduser  --system --uid 1000 --ingroup appgroup --no-create-home appuser \
 && chown -R appuser:appgroup /app

USER appuser

# PORT is injected by Railway at runtime
EXPOSE 8080
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2
