# Multi-stage build for HHS Patient Portal

# Stage 1: Build frontend
FROM node:21-alpine AS frontend-builder

WORKDIR /app

ARG VITE_AZURE_CLIENT_ID
ARG VITE_AZURE_TENANT_ID
ARG VITE_AZURE_REDIRECT_URI

ENV VITE_AZURE_CLIENT_ID=${VITE_AZURE_CLIENT_ID}
ENV VITE_AZURE_TENANT_ID=${VITE_AZURE_TENANT_ID}
ENV VITE_AZURE_REDIRECT_URI=${VITE_AZURE_REDIRECT_URI}

COPY package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY . .
RUN npm run build

# Stage 2: Python API runtime
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including nginx
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         postgresql-client \
         libpq-dev \
         curl \
         wget \
         nginx \
         bash \
         gettext-base \
     && apt-get clean \
     && rm -rf /var/lib/apt/lists/*

RUN rm -f /etc/nginx/sites-enabled/default

# Copy Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY api/ ./api/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/dist ./dist

# Copy nginx config
COPY docker/nginx.azure.conf.template /etc/nginx/templates/default.conf.template
COPY docker/start-nginx-azure.sh /start-nginx-azure.sh

# Set up nginx to serve static files and proxy API
RUN mkdir -p /usr/share/nginx/html && \
    cp -r ./dist/* /usr/share/nginx/html/

# Create non-root user for security (for gunicorn)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# nginx runs as root, gunicorn runs as appuser


# Expose ports
EXPOSE 80 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Default environment
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV API_UPSTREAM="http://127.0.0.1:3000"

# Start both nginx and gunicorn
RUN chmod +x /start-nginx-azure.sh
CMD ["/start-nginx-azure.sh"]

