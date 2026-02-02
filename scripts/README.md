# Crawl4AI Utility Scripts

Helper scripts for managing the WeChat Article Crawler Console and other Crawl4AI services.

## WeChat Console Scripts

### Start Services

Start all WeChat console services (backend + database):

```bash
./scripts/start-wechat-console.sh
```

This script will:
- Check Docker installation
- Create `.env` from template if not exists
- Start PostgreSQL and backend services
- Wait for services to be healthy
- Display access URLs and useful commands

### Stop Services

Stop all running services:

```bash
./scripts/stop-wechat-console.sh
```

To remove all data including database volumes:

```bash
docker compose down -v
```

### Test API

Run integration tests for the WeChat console API:

```bash
./scripts/test-wechat-console.sh
```

This will test:
1. Health check endpoint
2. List tasks
3. Create task
4. Get task details
5. Update task status
6. Delete task

## Manual Docker Commands

If you prefer manual control:

```bash
# Start services in foreground
docker compose up

# Start services in background
docker compose up -d

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f crawl4ai
docker compose logs -f postgres

# Check service status
docker compose ps

# Restart specific service
docker compose restart crawl4ai

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild images
docker compose build

# Pull latest images
docker compose pull
```

## Frontend Development

Start frontend development server:

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:5173

Build for production:

```bash
cd frontend
npm run build
```

Output will be in `frontend/dist/`

## Troubleshooting

### Port Already in Use

If port 11235 or 5432 is already in use:

```bash
# Check what's using the port
lsof -i :11235
lsof -i :5432

# Kill the process or change port in .env
BACKEND_PORT=11236
POSTGRES_PORT=5433
```

### Service Won't Start

```bash
# Check logs
docker compose logs crawl4ai

# Check database logs
docker compose logs postgres

# Restart services
docker compose restart
```

### Database Connection Issues

```bash
# Test database connection
docker compose exec postgres psql -U crawl4ai -d crawl4ai

# Check database tables
docker compose exec postgres psql -U crawl4ai -d crawl4ai -c "\dt"
```

### Reset Everything

```bash
# Stop and remove all data
docker compose down -v

# Remove all related containers and images
docker compose down --rmi all -v

# Start fresh
./scripts/start-wechat-console.sh
```

## Production Deployment

For production deployment, see the comprehensive guides:

- [Docker Deployment Guide](../docs/DOCKER_DEPLOYMENT.md)
- [Task Management Quickstart](../docs/TASK_MANAGEMENT_QUICKSTART.md)

Remember to:
1. Change default passwords in `.env`
2. Set up HTTPS/TLS
3. Configure backups
4. Enable monitoring
5. Review security settings

## Support

- **Documentation**: https://crawl4ai.com/docs
- **GitHub Issues**: https://github.com/unclecode/crawl4ai/issues
- **API Reference**: http://localhost:11235/docs (when running)
