# Docker Deployment Guide

Complete guide for deploying Crawl4AI with WeChat Task Management Console using Docker Compose.

## Architecture

The Docker deployment consists of:

- **PostgreSQL** - Database for task management and article storage
- **Crawl4AI Backend** - FastAPI server with task scheduler and crawler
- **Frontend** (Optional) - React UI served by Nginx

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- 10GB disk space

### 2. Initial Setup

```bash
# Clone repository (if needed)
git clone https://github.com/unclecode/crawl4ai.git
cd crawl4ai

# Create environment files
cp .env.example .env
cp deploy/docker/.llm.env.example .llm.env

# Edit configuration
nano .env  # Configure database and app settings
nano .llm.env  # Add your LLM API keys
```

### 3. Configure Environment

Edit `.env` file:

```bash
# Database credentials (CHANGE IN PRODUCTION!)
POSTGRES_DB=crawl4ai
POSTGRES_USER=crawl4ai
POSTGRES_PASSWORD=your_secure_password_here

# Application settings
BACKEND_PORT=11235
SCHEDULER_TIMEZONE=Asia/Shanghai
```

**Security Warning**: Always change `POSTGRES_PASSWORD` in production!

### 4. Start Services

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. Verify Deployment

```bash
# Check backend health
curl http://localhost:11235/health

# Check database
docker compose exec postgres psql -U crawl4ai -d crawl4ai -c "\dt"

# Check API
curl http://localhost:11235/api/tasks
```

### 6. Access the Application

- **Backend API**: http://localhost:11235
- **API Documentation**: http://localhost:11235/docs
- **Frontend** (if enabled): http://localhost:8080

## Frontend Deployment (Optional)

### Build Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Output will be in frontend/dist/
```

### Enable Frontend Service

1. Edit `docker-compose.yml` - uncomment the `frontend` service section (lines 92-109)

2. Restart services:

```bash
docker compose up -d
```

3. Access frontend at http://localhost:8080

### Frontend Configuration

The frontend connects to the backend via the Nginx proxy. If you change the backend URL or port, update:

1. `frontend/.env`:
```bash
VITE_API_BASE_URL=http://localhost:11235
```

2. Rebuild frontend:
```bash
cd frontend
npm run build
```

## Production Configuration

### Security Hardening

1. **Database Security**
```bash
# Generate strong password
openssl rand -base64 32

# Update .env
POSTGRES_PASSWORD=<generated_password>
DATABASE_URL=postgresql://crawl4ai:<generated_password>@postgres:5432/crawl4ai
```

2. **Network Isolation**
```yaml
# Only expose necessary ports
services:
  postgres:
    ports: []  # Remove external port exposure
```

3. **Use Docker Secrets** (Swarm mode)
```bash
echo "your_db_password" | docker secret create db_password -
```

### Resource Limits

Adjust resource limits in `docker-compose.yml`:

```yaml
services:
  crawl4ai:
    deploy:
      resources:
        limits:
          memory: 8G      # Increase for heavy workloads
          cpus: '4.0'     # Add CPU limit
        reservations:
          memory: 2G
          cpus: '1.0'
```

### Persistent Storage

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep crawl4ai

# Backup database
docker compose exec postgres pg_dump -U crawl4ai crawl4ai > backup.sql

# Restore database
cat backup.sql | docker compose exec -T postgres psql -U crawl4ai crawl4ai
```

### Logging

Configure logging driver in `docker-compose.yml`:

```yaml
services:
  crawl4ai:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

View logs:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f crawl4ai

# Last 100 lines
docker compose logs --tail=100 crawl4ai
```

## Building from Source

### Local Build

```bash
# Build with default settings
docker compose build

# Build with all ML dependencies
INSTALL_TYPE=all docker compose build

# Build with GPU support (NVIDIA)
ENABLE_GPU=true docker compose build
```

### Multi-Architecture Build

```bash
# Build for multiple platforms
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t crawl4ai:latest .
```

## Maintenance

### Update Services

```bash
# Pull latest images
docker compose pull

# Restart services
docker compose up -d

# Remove old images
docker image prune
```

### Database Maintenance

```bash
# Access database shell
docker compose exec postgres psql -U crawl4ai

# Check database size
docker compose exec postgres psql -U crawl4ai -c "\l+"

# Vacuum database
docker compose exec postgres psql -U crawl4ai -d crawl4ai -c "VACUUM ANALYZE;"
```

### Scaling

```bash
# Scale crawler workers (if configured)
docker compose up -d --scale crawl4ai=3
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs crawl4ai

# Check health status
docker compose ps

# Restart service
docker compose restart crawl4ai
```

### Database Connection Issues

```bash
# Test database connection
docker compose exec crawl4ai python -c "
from wechat_console.models import get_engine
engine = get_engine('postgresql://crawl4ai:changeme@postgres:5432/crawl4ai')
print('Connected successfully!')
"

# Check postgres logs
docker compose logs postgres
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Memory: 6GB+

# Or reduce crawler concurrency in server.py
```

### Port Already in Use

```bash
# Check what's using port 11235
lsof -i :11235

# Change port in .env
BACKEND_PORT=11236
```

### Permission Denied

```bash
# Fix volume permissions
docker compose exec crawl4ai chown -R appuser:appuser /app/uploads

# Or recreate volumes
docker compose down -v
docker compose up -d
```

## Monitoring

### Health Checks

```bash
# Check all health statuses
docker compose ps

# Backend health endpoint
curl http://localhost:11235/health

# Database health
docker compose exec postgres pg_isready -U crawl4ai
```

### Metrics

```bash
# Resource usage
docker stats crawl4ai-backend crawl4ai-postgres

# Disk usage
docker system df
```

### Performance Tuning

1. **PostgreSQL**
```bash
# Edit postgresql.conf (inside container)
docker compose exec postgres vi /var/lib/postgresql/data/postgresql.conf

# Recommended settings for 4GB RAM:
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
```

2. **Crawler Pool**

Edit `deploy/docker/server.py`:
```python
POOL_SIZE = 5  # Reduce if out of memory
MAX_SESSION_AGE = timedelta(minutes=20)
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec -T postgres pg_dump -U crawl4ai crawl4ai | gzip > "backup_${DATE}.sql.gz"
# Keep last 7 days
find . -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Restore database
gunzip -c backup_20250130_020000.sql.gz | \
  docker compose exec -T postgres psql -U crawl4ai crawl4ai

# Restart services
docker compose up -d
```

## Migration from Development

### Export Development Data

```bash
# From development environment
cd frontend
npm run build

# Export database (if applicable)
pg_dump -U crawl4ai crawl4ai > dev_export.sql
```

### Import to Docker

```bash
# Import database
cat dev_export.sql | docker compose exec -T postgres psql -U crawl4ai crawl4ai

# Copy frontend build
cp -r frontend/dist/* /path/to/docker/frontend/dist/
```

## Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v

# Restart service
docker compose restart crawl4ai

# View logs
docker compose logs -f crawl4ai

# Execute command in container
docker compose exec crawl4ai python -c "import crawl4ai; print(crawl4ai.__version__)"

# Access shell
docker compose exec crawl4ai bash

# Check resource usage
docker stats

# Remove everything (including volumes)
docker compose down -v
docker system prune -a
```

## Next Steps

- Set up HTTPS with reverse proxy (Nginx, Traefik)
- Configure backup automation
- Set up monitoring (Prometheus, Grafana)
- Enable authentication for the frontend
- Configure log aggregation (ELK stack)
- Set up CI/CD pipeline

## Support

- Documentation: https://crawl4ai.com/docs
- GitHub Issues: https://github.com/unclecode/crawl4ai/issues
- API Reference: http://localhost:11235/docs
