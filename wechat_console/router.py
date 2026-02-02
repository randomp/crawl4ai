"""
FastAPI Router for Task Management API

This module provides a complete REST API for managing WeChat article crawler tasks.
Includes endpoints for task CRUD, file upload, execution control, and data export.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import (
    APIRouter, Depends, File, HTTPException, Query, UploadFile
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .models import (
    Task, TaskExecution, Article,
    get_db, get_task
)
from .file_parser import parse_wechat_file, UPLOAD_DIR, MAX_FILE_SIZE
from .scheduler import schedule_task, unschedule_task, execute_task
from .exporter import export_articles

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/tasks", tags=["tasks"])


# ──────────────────── Pydantic Models ────────────────────

class TaskCreate(BaseModel):
    """Model for creating a new task"""
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    schedule_type: str = Field(..., pattern="^(once|interval|cron)$", description="Schedule type")
    schedule_config: Dict = Field(..., description="Schedule configuration")
    wechat_urls: List[str] = Field(..., min_items=1, description="List of WeChat URLs to crawl")
    crawl_config: Optional[Dict] = Field(default_factory=dict, description="Crawler configuration")

    @field_validator('wechat_urls')
    @classmethod
    def validate_wechat_urls(cls, urls):
        """Validate that all URLs are WeChat URLs"""
        for url in urls:
            if not url.startswith('https://mp.weixin.qq.com'):
                raise ValueError(f"Invalid WeChat URL: {url}")
        return urls


class TaskUpdate(BaseModel):
    """Model for updating an existing task"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schedule_type: Optional[str] = Field(None, pattern="^(once|interval|cron)$")
    schedule_config: Optional[Dict] = None
    wechat_urls: Optional[List[str]] = None
    crawl_config: Optional[Dict] = None

    @field_validator('wechat_urls')
    @classmethod
    def validate_wechat_urls(cls, urls):
        """Validate that all URLs are WeChat URLs"""
        if urls is not None:
            for url in urls:
                if not url.startswith('https://mp.weixin.qq.com'):
                    raise ValueError(f"Invalid WeChat URL: {url}")
        return urls


class TaskStatusUpdate(BaseModel):
    """Model for updating task status"""
    status: str = Field(..., pattern="^(active|paused|deleted)$", description="New task status")


class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    filename: str
    urls_found: int
    unique_urls: int
    urls: List[str]


# ──────────────────── Helper Functions ────────────────────

def get_scheduler_from_app():
    """Get scheduler from app.state with proper error handling"""
    try:
        from deploy.docker.server import app
        if hasattr(app.state, 'scheduler'):
            return app.state.scheduler
        else:
            logger.warning("Scheduler not found in app.state")
            return None
    except Exception as e:
        logger.error(f"Failed to get scheduler from app: {e}")
        return None


# ──────────────────── API Endpoints ────────────────────

@router.post("/upload", response_model=FileUploadResponse, status_code=200)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and parse Excel/CSV file containing WeChat URLs

    Accepts .xlsx, .xls, or .csv files and extracts WeChat article URLs.
    The file is saved to the upload directory and parsed automatically.

    Args:
        file: Uploaded file (Excel or CSV format)

    Returns:
        FileUploadResponse with parsed URLs and statistics

    Raises:
        HTTPException 400: Invalid file extension or parsing error
        HTTPException 500: Server error during file processing
    """
    try:
        # Validate file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.xlsx', '.xls', '.csv']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension: {file_extension}. Only .xlsx, .xls, and .csv are supported."
            )

        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename

        try:
            # Read file content
            content = await file.read()

            # Validate file size before writing
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                )

            # Write to disk
            with open(file_path, 'wb') as f:
                f.write(content)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

        # Parse file
        try:
            result = parse_wechat_file(str(file_path))
        except Exception as e:
            logger.error(f"Failed to parse file {file.filename}: {e}")
            # Clean up uploaded file on parse failure
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleaned up failed upload: {file_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up file {file_path}: {cleanup_error}")
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

        logger.info(f"Successfully parsed {file.filename}: {result['unique_urls']} unique URLs found")

        return FileUploadResponse(
            filename=file.filename,
            urls_found=result['urls_found'],
            unique_urls=result['unique_urls'],
            urls=result['urls']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in file upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", status_code=201)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new crawler task

    Creates a task record in the database and schedules it for execution
    based on the provided schedule configuration.

    Args:
        task_data: Task creation data
        db: Database session

    Returns:
        Created task as dictionary

    Raises:
        HTTPException 400: Invalid task data or duplicate task name
        HTTPException 500: Database or scheduler error
    """
    try:
        # Check for duplicate task name
        existing = db.query(Task).filter(Task.name == task_data.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Task with name '{task_data.name}' already exists"
            )

        # Create task record
        task = Task(
            name=task_data.name,
            description=task_data.description,
            source_file='api',  # Mark as API-created
            wechat_urls=task_data.wechat_urls,
            crawl_config=task_data.crawl_config,
            schedule_type=task_data.schedule_type,
            schedule_config=task_data.schedule_config,
            status='active'
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"Created task {task.id}: {task.name}")

        # Schedule task
        scheduler = get_scheduler_from_app()
        if scheduler:
            try:
                await schedule_task(task, scheduler)
                logger.info(f"Scheduled task {task.id}")
            except Exception as e:
                logger.error(f"Failed to schedule task {task.id}: {e}")
                # Don't fail the request if scheduling fails
        else:
            logger.warning(f"Scheduler not available, task {task.id} not scheduled")

        return task.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/")
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, pattern="^(active|paused|deleted)$", description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List tasks with pagination and optional status filter

    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records (default: 20, max: 100)
        status: Optional status filter (active, paused, deleted)
        db: Database session

    Returns:
        Dictionary with total count and list of tasks
    """
    try:
        # Build query
        query = db.query(Task)

        # Apply status filter if provided
        if status:
            query = query.filter(Task.status == status)

        # Get total count
        total = query.count()

        # Apply pagination
        tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

        return {
            'total': total,
            'tasks': [task.to_dict() for task in tasks]
        }

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@router.get("/{task_id}")
async def get_task_details(task_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific task

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Task as dictionary

    Raises:
        HTTPException 404: Task not found
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return task.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task details")


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing task

    Updates only the fields provided in the request.
    If schedule configuration is changed, the task will be rescheduled.

    Args:
        task_id: Task ID
        task_data: Task update data
        db: Database session

    Returns:
        Updated task as dictionary

    Raises:
        HTTPException 404: Task not found
        HTTPException 400: Invalid update data
        HTTPException 500: Database or scheduler error
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Track if schedule changed
        schedule_changed = False

        # Update fields
        if task_data.name is not None:
            # Check for duplicate name
            existing = db.query(Task).filter(
                Task.name == task_data.name,
                Task.id != task_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task with name '{task_data.name}' already exists"
                )
            task.name = task_data.name

        if task_data.description is not None:
            task.description = task_data.description

        if task_data.schedule_type is not None:
            task.schedule_type = task_data.schedule_type
            schedule_changed = True

        if task_data.schedule_config is not None:
            task.schedule_config = task_data.schedule_config
            schedule_changed = True

        if task_data.wechat_urls is not None:
            task.wechat_urls = task_data.wechat_urls

        if task_data.crawl_config is not None:
            task.crawl_config = task_data.crawl_config

        # Update timestamp
        task.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(task)

        logger.info(f"Updated task {task_id}")

        # Reschedule if needed
        if schedule_changed and task.status == 'active':
            scheduler = get_scheduler_from_app()
            if scheduler:
                try:
                    await schedule_task(task, scheduler)
                    logger.info(f"Rescheduled task {task_id}")
                except Exception as e:
                    logger.error(f"Failed to reschedule task {task_id}: {e}")

        return task.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Delete a task

    Unschedules the task and removes it from the database.
    All associated articles and executions are also deleted (cascade).

    Args:
        task_id: Task ID
        db: Database session

    Raises:
        HTTPException 404: Task not found
        HTTPException 500: Database or scheduler error
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Unschedule first
        scheduler = get_scheduler_from_app()
        if scheduler:
            try:
                await unschedule_task(task_id, scheduler)
                logger.info(f"Unscheduled task {task_id}")
            except Exception as e:
                logger.error(f"Failed to unschedule task {task_id}: {e}")

        # Delete from database
        db.delete(task)
        db.commit()

        logger.info(f"Deleted task {task_id}")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update task status

    Changes task status and handles scheduling accordingly:
    - active: Schedule the task
    - paused: Unschedule the task
    - deleted: Mark as deleted (use DELETE endpoint instead)

    Args:
        task_id: Task ID
        status_data: Status update data
        db: Database session

    Returns:
        Updated task as dictionary

    Raises:
        HTTPException 404: Task not found
        HTTPException 500: Database or scheduler error
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        old_status = task.status
        new_status = status_data.status

        # Update status
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(task)

        logger.info(f"Updated task {task_id} status: {old_status} -> {new_status}")

        # Handle scheduling
        scheduler = get_scheduler_from_app()
        if scheduler:
            try:
                if new_status == 'paused':
                    # Unschedule
                    await unschedule_task(task_id, scheduler)
                    logger.info(f"Unscheduled paused task {task_id}")
                elif new_status == 'active' and old_status == 'paused':
                    # Reschedule when activating a paused task
                    await schedule_task(task, scheduler)
                    logger.info(f"Scheduled task {task_id}")
            except Exception as e:
                logger.error(f"Failed to update schedule for task {task_id}: {e}")

        return task.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")


@router.post("/{task_id}/execute")
async def execute_task_manual(task_id: int, db: Session = Depends(get_db)):
    """
    Manually execute a task

    Starts task execution in the background without waiting for scheduled time.
    The task will run asynchronously and results can be checked via execution history.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Confirmation message with task ID

    Raises:
        HTTPException 404: Task not found
        HTTPException 400: Task is not active
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if task.status != 'active':
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not active (status: {task.status})"
            )

        # Execute in background with error handling
        async def execute_with_error_handling(tid: int):
            """Execute task with error handling to prevent silent failures"""
            try:
                await execute_task(tid)
            except Exception as e:
                logger.error(f"Background task execution failed for task {tid}: {e}", exc_info=True)

        asyncio.create_task(execute_with_error_handling(task_id))

        logger.info(f"Started manual execution of task {task_id}")

        return {
            "message": "Task execution started",
            "task_id": task_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.get("/{task_id}/executions")
async def get_task_executions(
    task_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get execution history for a task

    Returns paginated list of task executions ordered by most recent first.

    Args:
        task_id: Task ID
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records (default: 20, max: 100)
        db: Database session

    Returns:
        Dictionary with total count and list of executions

    Raises:
        HTTPException 404: Task not found
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Query executions
        query = db.query(TaskExecution).filter(TaskExecution.task_id == task_id)

        total = query.count()

        executions = query.order_by(
            TaskExecution.started_at.desc()
        ).offset(skip).limit(limit).all()

        return {
            'total': total,
            'executions': [execution.to_dict() for execution in executions]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get executions for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get execution history")


@router.get("/{task_id}/export")
async def export_task_articles(
    task_id: int,
    format: str = Query("excel", pattern="^(excel|csv|json)$", description="Export format"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db)
):
    """
    Export articles for a task

    Exports all articles for a task in the specified format (Excel, CSV, or JSON).
    Optional date filters can be applied to limit the export to a specific time range.

    Args:
        task_id: Task ID
        format: Export format (excel, csv, json)
        start_date: Optional start date filter
        end_date: Optional end date filter
        db: Database session

    Returns:
        StreamingResponse with exported data

    Raises:
        HTTPException 404: Task not found
        HTTPException 500: Export error
    """
    try:
        task = get_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Build filters
        filters = {}
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date

        # Export articles
        try:
            buffer = await export_articles(task_id, format, filters)
        except Exception as e:
            logger.error(f"Export failed for task {task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

        # Set proper content type and filename
        content_types = {
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv',
            'json': 'application/json'
        }

        extensions = {
            'excel': 'xlsx',
            'csv': 'csv',
            'json': 'json'
        }

        filename = f"task_{task_id}_articles_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.{extensions[format]}"

        logger.info(f"Exporting task {task_id} articles as {format}")

        return StreamingResponse(
            buffer,
            media_type=content_types[format],
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export articles for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export articles")
