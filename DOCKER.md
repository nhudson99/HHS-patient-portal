# HHS Patient Portal - Deployment Guide

## Docker Setup

This project is fully containerized for easy deployment. All services run in Docker containers for consistency across development, testing, and production environments.

### Prerequisites

- Docker (20.10+)
- Docker Compose (2.0+)
- 2GB+ available RAM
- 5GB+ available disk space

### Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/nhudson99/HHS-patient-portal.git
cd HHS-patient-portal
```

2. **Build and start the application:**
```bash
chmod +x docker-build.sh
./docker-build.sh
```

This script will:
- Check for Docker and Docker Compose
- Create a `.env` file from `.env.example`
- Build the Docker image
- Start all services (API, Database, Redis, Nginx)
- Display service status and access URLs

3. **Access the application:**
- Web Portal: `http://localhost`
- API: `http://localhost:3000`
- Database: `localhost:5432`

### Services

The Docker Compose setup includes:

1. **PostgreSQL (hhs-postgres)**
   - Port: 5432
   - Database: hhs_portal
   - Credentials: postgres/postgres (change in production)
   - Volume: postgres_data

2. **Redis (hhs-redis)**
   - Port: 6379
   - Used for session management and caching

3. **API (hhs-api)**
   - Port: 3000
   - Flask application
   - Auto-restarts on failure
   - Health checks enabled

4. **Nginx (hhs-nginx)**
   - Port: 80 (HTTP)
   - Port: 443 (HTTPS - when configured)
   - Reverse proxy for API
   - Static file serving
   - Rate limiting

### Environment Configuration

Edit `.env` file to customize:

```env
# Database
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_NAME=hhs_portal

# Security
SECRET_KEY=your-secret-key-here
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=30

# Ports
API_PORT=3000
WEB_PORT=80
SSL_PORT=443
```

### Common Commands

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api

# Stop all services
docker-compose stop

# Start services
docker-compose start

# Restart a service
docker-compose restart api

# Execute command in container
docker exec -it hhs-api bash

# View running containers
docker ps

# Check service status
docker-compose ps
```

### Database Management

```bash
# Access PostgreSQL CLI
docker exec -it hhs-postgres psql -U postgres -d hhs_portal

# Backup database
docker exec -it hhs-postgres pg_dump -U postgres hhs_portal > backup.sql

# Restore database
docker exec -i hhs-postgres psql -U postgres hhs_portal < backup.sql

# View database logs
docker-compose logs -f db
```

### SSL/HTTPS Setup

To enable HTTPS:

1. Place SSL certificate and key in `docker/ssl/`:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key

2. Uncomment the HTTPS server block in `docker/nginx.conf`

3. Restart Nginx:
   ```bash
   docker-compose restart nginx
   ```

### Production Deployment

For production deployment:

1. **Security:**
   - Change all default passwords in `.env`
   - Generate strong `SECRET_KEY`
   - Set `FLASK_ENV=production`
   - Enable SSL/HTTPS

2. **Database:**
   - Use managed PostgreSQL (RDS, Cloud SQL, etc.)
   - Update DB_HOST in `.env`
   - Enable automated backups

3. **Scaling:**
   - Use Docker Swarm or Kubernetes for orchestration
   - Use load balancer for multiple API instances
   - Enable Redis for distributed caching

4. **Monitoring:**
   - Set up logging (ELK stack, CloudWatch, etc.)
   - Enable health checks
   - Set up alerts for failures

5. **Cleanup:**
   ```bash
   ./docker-clean.sh
   ```

### Troubleshooting

**Container fails to start:**
```bash
docker-compose logs -f api
```

**Database connection error:**
- Check DB_HOST, DB_USER, DB_PASSWORD in `.env`
- Ensure database service is healthy: `docker-compose ps`

**Port already in use:**
- Change ports in `.env` or `docker-compose.yml`
- Or stop other services using those ports

**Build fails:**
- Clear Docker cache: `docker system prune -a`
- Rebuild: `docker-compose build --no-cache`

**Persistent data:**
- All data is stored in `postgres_data` volume
- Remove with: `docker volume rm hhs-patient-portal_postgres_data`

### API Documentation

Once running, API documentation is available at:
- `http://localhost:3000/api/docs` (if Swagger is configured)

Test endpoints:
```bash
# Health check
curl http://localhost:3000/health

# Get salt for login
curl -X POST http://localhost:3000/api/auth/salt \
  -H "Content-Type: application/json" \
  -d '{"username":"patient1"}'
```

### Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review configuration: `.env`
- Check network: `docker network ls`

---

**Last Updated:** 2026-02-12
**Version:** 1.0.0
