# WeChat Article Crawler Console

Backend application package for the WeChat Article Crawler task management system.

## Structure

```
wechat_console/
├── __init__.py           # Package initialization
├── main.py               # Standalone entry point (development)
├── models.py             # Database models (Task, Article, TaskExecution)
├── file_parser.py        # Excel/CSV file parser with security
├── wechat_scraper.py     # Two-phase article crawler
├── scheduler.py          # APScheduler integration
├── exporter.py           # Multi-format data export
└── router.py             # FastAPI REST API endpoints
```

## Usage

### As Part of Crawl4AI (Production)

The WeChat console is integrated into the main Crawl4AI server:

```python
# In deploy/docker/server.py
from wechat_console.router import router as task_router
from wechat_console.models import Base, get_engine
from wechat_console.scheduler import create_scheduler, start_scheduler, stop_scheduler

# Initialize database and scheduler
engine = get_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
app.state.scheduler = create_scheduler(database_url=DATABASE_URL)
await start_scheduler(app.state.scheduler)

# Mount API router
app.include_router(task_router, prefix="/api")
```

### Standalone (Development/Testing)

For development and testing without the full Crawl4AI server:

```bash
# Set environment variables
export DATABASE_URL="postgresql://crawl4ai:changeme@localhost:5432/crawl4ai"
export SCHEDULER_TIMEZONE="Asia/Shanghai"

# Run standalone server
python -m wechat_console.main
```

Or with uvicorn directly:

```bash
uvicorn wechat_console.main:app --reload --port 11235
```

## Dependencies

All dependencies are listed in `deploy/docker/requirements.txt`:

- fastapi
- sqlalchemy
- psycopg2-binary
- apscheduler
- pandas
- openpyxl
- crawl4ai

## API Endpoints

All endpoints are prefixed with `/api`:

- `POST /api/tasks/upload` - Upload Excel/CSV file
- `POST /api/tasks` - Create task
- `GET /api/tasks` - List tasks
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `PATCH /api/tasks/{id}/status` - Update status
- `POST /api/tasks/{id}/execute` - Execute task
- `GET /api/tasks/{id}/executions` - Get execution history
- `GET /api/tasks/{id}/export` - Export articles

## Configuration

### Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (required)
- `SCHEDULER_TIMEZONE` - Timezone for scheduler (default: Asia/Shanghai)
- `UPLOAD_DIR` - Directory for uploaded files (default: /tmp/uploads)

### Database

PostgreSQL 12+ with the following tables:

- `tasks` - Task definitions and configuration
- `articles` - Crawled article content
- `task_executions` - Execution history and statistics

Tables are created automatically on first run.

## Development

### Running Tests

```bash
# Unit tests (if available)
pytest wechat_console/

# Integration tests
./scripts/test-wechat-console.sh
```

### Code Structure

- **models.py**: SQLAlchemy ORM models, database session management
- **file_parser.py**: Excel/CSV parsing with security validation
- **wechat_scraper.py**: Two-phase crawler (discovery + content extraction)
- **scheduler.py**: APScheduler integration with database job store
- **exporter.py**: Export to Excel, CSV, and JSON formats
- **router.py**: FastAPI routes and Pydantic request/response models

## Security

- Input validation with Pydantic v2
- Path traversal prevention in file uploads
- File size limits (10MB default)
- SQL injection prevention via SQLAlchemy ORM
- Timezone-aware timestamps

## Documentation

- [Task Management Quickstart](../docs/TASK_MANAGEMENT_QUICKSTART.md)
- [Docker Deployment Guide](../docs/DOCKER_DEPLOYMENT.md)
- [Implementation Summary](../docs/WECHAT_CONSOLE_SUMMARY.md)

## License

MIT - See main project LICENSE file
