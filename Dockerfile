# Multi-stage build for HHS Patient Portal

# Stage 1: Build frontend
FROM node:21-alpine AS frontend-builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY . .
RUN npm run build

# Stage 2: Python API runtime
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         postgresql-client \
         libpq-dev \
         curl \
         wget \
     && apt-get clean \
     && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY api/ ./api/
COPY server/ ./server/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/dist ./dist

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 3000 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Default environment
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Run API server with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "4", "--worker-class", "sync", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "api.app:app"]
