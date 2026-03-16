# Docker Modernization Update

## Summary
Updated the Docker and Docker Compose setup to use modern, production-ready standards. Removed legacy workarounds and improved reliability with better health checks and resource management.

## Key Changes

### 1. **docker-compose.yml** (Version 3.8 → 3.9)

#### Database Service
- ✅ Added UTF-8 encoding initialization: `POSTGRES_INITDB_ARGS: "--encoding=UTF8"`
- ✅ Improved healthcheck to verify database name: `-d ${DB_NAME:-hhs_patient_portal}`
- ✅ Added `start_period: 10s` for delayed health checks
- ✅ Added `restart: unless-stopped` for automatic recovery

#### Redis Service
- ✅ Enabled persistence with `command: redis-server --appendonly yes`
- ✅ Added volume for data persistence: `redis_data:/data`
- ✅ Added `start_period: 10s` for delayed health checks
- ✅ Added `restart: unless-stopped` for automatic recovery

#### API Service
- ✅ Fixed environment variable: `SESSION_SECRET` (was `SECRET_KEY`)
- ✅ Fixed database name default: `hhs_patient_portal` (was `hhs_portal`)
- ✅ Added `DB_SSLMODE: ${DB_SSLMODE:-disable}` for secure connections
- ✅ Added `FORCE_HTTPS: ${FORCE_HTTPS:-false}` for proxy compatibility
- ✅ Made `ALLOWED_ORIGINS` configurable

#### Nginx Service
- ✅ Updated image: `nginx:1.27-alpine` (latest stable)
- ✅ Improved dependency: `api: condition: service_healthy` (was just `service_started`)
- ✅ Added health check: `wget --spider http://localhost/health`
- ✅ Added `restart: unless-stopped` for automatic recovery

#### Volumes
- ✅ Added Redis persistent storage: `redis_data:`

### 2. **Dockerfile** (Node 20 → 21, Python 3.12 → 3.13)

#### Frontend Builder
- ✅ Updated Node: `node:21-alpine` (latest LTS)
- ✅ Improved npm install: `npm ci --prefer-offline --no-audit` (faster, reproducible builds)

#### Runtime
- ✅ Updated Python: `python:3.13-slim` (latest, better performance)
- ✅ Added `wget` to system dependencies (for nginx health checks)
- ✅ Improved pip: `pip install --upgrade pip setuptools wheel`

#### Security
- ✅ Added non-root user: `useradd -m -u 1000 appuser`
- ✅ Set proper file ownership and switched to appuser

#### Logging
- ✅ Added gunicorn logging: `--access-logfile "-"` and `--error-logfile "-"`
- ✅ All logs now visible in `docker compose logs`

### 3. **docker-build.sh** (Complete Rewrite)

#### Modern Approach
- ✅ Docker Compose v2 plugin required (no legacy v1 fallback)
- ✅ Cleaner command-line interface with subcommands
- ✅ Better error messages and help text
- ✅ Colored output for better readability

#### Available Commands
```bash
./docker-build.sh build              # Build images
./docker-build.sh start              # Start services
./docker-build.sh stop               # Stop services
./docker-build.sh restart            # Restart all
./docker-build.sh logs [service]     # View logs
./docker-build.sh status             # Show status & resources
./docker-build.sh clean              # Remove volumes
./docker-build.sh reset              # Hard reset everything
./docker-build.sh help               # Show help
```

#### Improvements
- ✅ Removed unnecessary image pruning and no-cache rebuilds (slower)
- ✅ Simplified sudo detection
- ✅ Added resource usage monitoring
- ✅ Better startup sequencing and health checks
- ✅ Safer cleanup with confirmation prompts

## Breaking Changes

### Required Actions
1. **Install Docker Compose v2 Plugin**
   ```bash
   # Linux
   sudo apt-get update && sudo apt-get install docker-compose-plugin
   
   # macOS
   brew install docker-compose
   
   # Windows (Docker Desktop)
   # Already included
   ```

2. **Update .env Variables** (if upgrading)
   ```
   # Old → New
   SECRET_KEY → SESSION_SECRET
   DB_NAME: hhs_portal → hhs_patient_portal
   ```

## Testing

### Validate Installation
```bash
# Check Docker Compose v2
docker compose version

# Check script works
cd /home/nate/linux-repos/HHS-patient-portal
./docker-build.sh help
```

### Build & Run
```bash
./docker-build.sh build
./docker-build.sh start
./docker-build.sh status
```

### Verify Services
```bash
# All should show "healthy"
docker compose ps

# Check logs for errors
docker compose logs -f

# Test API
curl http://localhost:3000/health
```

## Performance Benefits

- **Faster Builds**: `npm ci` is deterministic, Python build cache improvements
- **Better Resource Management**: Health checks prevent zombie containers
- **Auto-Recovery**: `restart: unless-stopped` handles transient failures
- **Persistent Cache**: Redis now persists data across restarts
- **Better Logging**: All service output visible in one place

## Migration from Legacy Setup

If you have containers running on the old setup:
```bash
# Stop and clean old containers
docker compose down -v

# Remove old images
docker rmi hhs-patient-portal:latest

# Start fresh
./docker-build.sh build
./docker-build.sh start
```

## Security Improvements

- ✅ Non-root container user (appuser uid 1000)
- ✅ Proper health checks prevent hung containers
- ✅ Auto-restart policy prevents service degradation
- ✅ Configurable SSL mode for secure database connections

## Support

For issues with Docker Compose v2:
- Check installation: `docker compose version`
- Update Docker: `sudo apt update && sudo apt upgrade docker.io`
- Verify plugin: `ls -la ~/.docker/cli-plugins/docker-compose`

See `docker-compose.yml` and `Dockerfile` for full configuration details.
