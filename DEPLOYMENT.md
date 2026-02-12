# 🏥 HHS Patient Portal - Docker & Kubernetes Deployment

Complete containerized setup for the HHS Patient Portal with Docker, Docker Compose, and Kubernetes support.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Docker Setup](#docker-setup)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### Using Docker Compose (Recommended for Development)

```bash
# Clone and setup
git clone https://github.com/nhudson99/HHS-patient-portal.git
cd HHS-patient-portal

# Build and start all services
chmod +x docker-build.sh
./docker-build.sh

# Access the application
# Web Portal: http://localhost
# API: http://localhost:3000
```

### Using Docker Directly

```bash
# Build image
docker build -t hhs-patient-portal:latest .

# Run container
docker run -p 3000:3000 -p 5173:5173 \
  -e DB_HOST=localhost \
  -e FLASK_ENV=production \
  hhs-patient-portal:latest
```

## 🐳 Docker Setup

### Architecture

```
┌─────────────────────────────────────────────────┐
│                   Nginx (Port 80)               │
│              Reverse Proxy & Load Balancer       │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌─────────┐  ┌────────┐  ┌────────┐
│  API    │  │ Static │  │ Health │
│ (3000)  │  │ Files  │  │ Check  │
└────┬────┘  └────────┘  └────────┘
     │
     ├─────────────┬──────────────┐
     │             │              │
┌────────────┐ ┌──────────┐ ┌────────────┐
│ PostgreSQL │ │  Redis   │ │   Audit   │
│  (5432)    │ │ (6379)   │ │   Logs    │
└────────────┘ └──────────┘ └────────────┘
```

### Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| PostgreSQL | postgres:16-alpine | 5432 | Main database |
| Redis | redis:7-alpine | 6379 | Session cache |
| API | hhs-patient-portal:latest | 3000 | Flask backend |
| Nginx | nginx:alpine | 80/443 | Web server |

### Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build configuration |
| `docker-compose.yml` | Service orchestration |
| `.env.example` | Environment template |
| `docker/nginx.conf` | Nginx configuration |
| `docker-build.sh` | One-command setup |
| `docker-clean.sh` | Cleanup script |

## 🎯 Common Docker Commands

```bash
# View all services
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api

# Stop all services
docker-compose stop

# Start services
docker-compose start

# Restart service
docker-compose restart api

# Execute command in container
docker exec -it hhs-api bash

# Database shell
docker exec -it hhs-postgres psql -U postgres -d hhs_portal

# View resource usage
docker stats

# Clean up everything
./docker-clean.sh
```

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Docker image pushed to registry

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f kubernetes.yaml

# Check deployment status
kubectl get pods -n hhs-portal
kubectl get services -n hhs-portal

# View logs
kubectl logs -f deployment/api -n hhs-portal

# Access dashboard
kubectl port-forward svc/api 3000:3000 -n hhs-portal
```

### Kubernetes Features

✅ **3 replicas** for high availability
✅ **Auto-scaling** based on CPU/memory
✅ **Health checks** for pod management
✅ **Secrets management** for sensitive data
✅ **Persistent volumes** for database
✅ **Service discovery** and load balancing
✅ **ConfigMaps** for configuration

### Scale Deployment

```bash
# Manual scaling
kubectl scale deployment api --replicas=5 -n hhs-portal

# Check HPA status
kubectl get hpa -n hhs-portal

# View events
kubectl describe hpa api-hpa -n hhs-portal
```

## 🔧 Environment Configuration

### Development (.env)

```env
FLASK_ENV=development
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hhs_portal
DB_USER=postgres
DB_PASSWORD=postgres
SECRET_KEY=dev-key-change-in-production
```

### Production (.env)

```env
FLASK_ENV=production
DB_HOST=prod-db.example.com
DB_PORT=5432
DB_NAME=hhs_portal_prod
DB_USER=hhs_user
DB_PASSWORD=secure-password-here
SECRET_KEY=production-secret-key-here
MAX_LOGIN_ATTEMPTS=3
ACCOUNT_LOCKOUT_MINUTES=60
SESSION_TIMEOUT_MINUTES=30
```

## 📦 Production Deployment

### Cloud Platforms

#### AWS ECS

```bash
# Create ECR repository
aws ecr create-repository --repository-name hhs-patient-portal

# Build and push image
docker build -t hhs-patient-portal:latest .
docker tag hhs-patient-portal:latest <account>.dkr.ecr.<region>.amazonaws.com/hhs-patient-portal:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/hhs-patient-portal:latest

# Deploy with ECS (use CloudFormation or Terraform)
```

#### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT-ID/hhs-portal

# Deploy
gcloud run deploy hhs-portal \
  --image gcr.io/PROJECT-ID/hhs-portal \
  --platform managed \
  --region us-central1 \
  --set-env-vars FLASK_ENV=production
```

#### Azure Container Instances

```bash
# Build and push to ACR
az acr build --registry <registry-name> \
  --image hhs-portal:latest .

# Deploy container
az container create \
  --resource-group myGroup \
  --name hhs-portal \
  --image <registry-name>.azurecr.io/hhs-portal:latest
```

### SSL/HTTPS Configuration

1. **Generate certificates:**
```bash
# Using Let's Encrypt
certbot certonly --standalone -d yourdomain.com
```

2. **Copy to docker/ssl/:**
```bash
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/key.pem
```

3. **Uncomment HTTPS in nginx.conf** and restart:
```bash
docker-compose restart nginx
```

### Database Backup

```bash
# Local backup
docker exec hhs-postgres pg_dump -U postgres hhs_portal > backup.sql

# Restore backup
docker exec -i hhs-postgres psql -U postgres hhs_portal < backup.sql

# Automated backups (cron job)
0 2 * * * docker exec hhs-postgres pg_dump -U postgres hhs_portal > /backups/hhs-$(date +\%Y\%m\%d).sql
```

### Monitoring & Logging

```bash
# Docker stats
docker stats

# View logs
docker-compose logs --timestamps

# Persistent logging (add to docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs api

# Inspect configuration
docker inspect hhs-api

# Restart container
docker-compose restart api
```

### Database connection error

```bash
# Check database is running
docker-compose ps db

# Test connection
docker exec hhs-api python -c "from api.db.connection import get_db_connection; get_db_connection()"

# View database logs
docker-compose logs db
```

### Port already in use

```bash
# Find process using port
lsof -i :3000

# Change port in docker-compose.yml or .env
API_PORT=3001
```

### Out of memory

```bash
# Check resource limits
docker stats

# Increase Docker memory in settings or modify docker-compose.yml
services:
  api:
    mem_limit: 1g
```

### Permission denied errors

```bash
# Fix volume permissions
docker exec -it hhs-postgres chown -R postgres:postgres /var/lib/postgresql/data

# Or rebuild with proper permissions
docker-compose down -v
docker-compose up -d
```

## 📊 Performance Tuning

### Connection pooling
```python
# In api/app.py
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 10,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}
```

### Nginx caching
```nginx
# In docker/nginx.conf
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;
proxy_cache api_cache;
proxy_cache_valid 200 10m;
```

### Redis optimization
```bash
# Monitor Redis usage
docker exec hhs-redis redis-cli INFO
docker exec hhs-redis redis-cli DBSIZE
```

## 🔐 Security Checklist

- [ ] Change default passwords
- [ ] Set strong SECRET_KEY
- [ ] Enable SSL/HTTPS
- [ ] Configure firewall rules
- [ ] Implement network policies
- [ ] Enable audit logging
- [ ] Set up rate limiting
- [ ] Regular security updates
- [ ] Database backups
- [ ] Access control & RBAC

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Flask Deployment Guide](https://flask.palletsprojects.com/deployment/)
- [PostgreSQL in Docker](https://hub.docker.com/_/postgres)

## 🆘 Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Review `.env` configuration
3. Check network connectivity: `docker network inspect hhs-network`
4. Review DOCKER.md for detailed setup

---

**Last Updated:** 2026-02-12  
**Version:** 1.0.0  
**Status:** Production Ready ✅
