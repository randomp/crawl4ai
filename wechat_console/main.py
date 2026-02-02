"""
Standalone entry point for WeChat Article Crawler Console.

This can be used for development/testing without the full Crawl4AI server.
For production, use deploy/docker/server.py which integrates this with Crawl4AI.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router as task_router
from .models import Base, get_engine
from .scheduler import create_scheduler, start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crawl4ai:changeme@localhost:5432/crawl4ai"
)
SCHEDULER_TIMEZONE = os.environ.get("SCHEDULER_TIMEZONE", "Asia/Shanghai")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan manager."""
    # Initialize database
    logger.info("Initializing database...")
    engine = get_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    # Initialize and start scheduler
    logger.info("Starting task scheduler...")
    app.state.scheduler = create_scheduler(
        database_url=DATABASE_URL,
        timezone=SCHEDULER_TIMEZONE
    )
    await start_scheduler(app.state.scheduler)
    logger.info("Task scheduler started successfully")

    yield

    # Cleanup on shutdown
    logger.info("Stopping task scheduler...")
    try:
        await stop_scheduler(app.state.scheduler)
        logger.info("Task scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Scheduler cleanup failed: {e}")


# Create FastAPI application
app = FastAPI(
    title="WeChat Article Crawler Console",
    description="Task management system for WeChat article crawling",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include task management router
app.include_router(task_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "WeChat Article Crawler Console",
        "version": "1.0.0",
        "docs": "/docs",
        "api": "/api/tasks"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "wechat_console.main:app",
        host="0.0.0.0",
        port=11235,
        reload=True,
        log_level="info"
    )
