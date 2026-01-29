# deploy/docker/tasks/scheduler.py
"""
Task scheduler with APScheduler integration
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from crawl4ai import BrowserConfig
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.docker import crawler_pool
from .models import Task, TaskExecution, get_db, get_task, get_database_url
from .wechat_scraper import incremental_crawl

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure APScheduler instance with PostgreSQL job store

    Returns:
        Configured AsyncIOScheduler instance
    """
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    # Get database URL for job store
    database_url = get_database_url()

    # Configure job stores
    jobstores = {
        'default': SQLAlchemyJobStore(url=database_url, tablename='apscheduler_jobs')
    }

    # Job execution settings
    job_defaults = {
        'coalesce': True,  # Combine missed runs into one
        'max_instances': 1,  # Only one instance of a job at a time
        'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
    }

    # Create scheduler
    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults=job_defaults,
        timezone='UTC'
    )

    logger.info("Created APScheduler instance with PostgreSQL job store")
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    """
    Get existing scheduler instance or create new one

    Returns:
        AsyncIOScheduler instance
    """
    if _scheduler is None:
        return create_scheduler()
    return _scheduler


async def execute_task(task_id: int):
    """
    Main task execution function called by scheduler

    This function:
    1. Loads task configuration from database
    2. Creates TaskExecution record
    3. Gets crawler from pool
    4. Runs incremental crawl
    5. Updates task and execution records

    Args:
        task_id: ID of task to execute
    """
    logger.info(f"Starting execution for task {task_id}")

    # Get database session
    db_generator = get_db()
    db = next(db_generator)

    execution = None

    try:
        # Load task
        task = get_task(db, task_id)

        if not task:
            logger.error(f"Task {task_id} not found")
            return

        if task.status != 'active':
            logger.info(f"Task {task_id} is not active (status={task.status}), skipping")
            return

        # Create execution record
        execution = TaskExecution(
            task_id=task_id,
            started_at=datetime.now(timezone.utc),
            status='running'
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        logger.info(f"Created execution {execution.id} for task {task_id}")

        # Get crawler configuration from task
        crawl_config = task.crawl_config or {}
        browser_config = BrowserConfig(
            headless=crawl_config.get('headless', True),
            verbose=crawl_config.get('verbose', False),
            user_agent=crawl_config.get('user_agent')
        )

        # Get crawler from pool
        try:
            crawler = await crawler_pool.get_crawler(browser_config)
        except Exception as e:
            logger.error(f"Failed to get crawler from pool: {e}")
            raise

        # Run incremental crawl
        try:
            stats = await incremental_crawl(task, crawler, execution.id)

            # Update execution with results
            execution.completed_at = datetime.now(timezone.utc)
            execution.status = 'completed'
            execution.articles_found = stats.get('total', 0)
            execution.articles_new = stats.get('new', 0)
            execution.articles_updated = stats.get('updated', 0)
            execution.errors = stats.get('errors', [])

            # Update task timestamps
            task.last_run_at = datetime.now(timezone.utc)

            # Calculate next run time
            if task.schedule_type in ['interval', 'cron']:
                task.next_run_at = calculate_next_run(task)

            db.commit()

            logger.info(
                f"Task {task_id} completed: "
                f"found={stats.get('total', 0)}, "
                f"new={stats.get('new', 0)}, "
                f"updated={stats.get('updated', 0)}"
            )

        except Exception as e:
            logger.error(f"Crawl failed for task {task_id}: {e}")

            # Update execution as failed
            execution.completed_at = datetime.now(timezone.utc)
            execution.status = 'failed'
            execution.errors = [str(e)]

            db.commit()
            raise

    except Exception as e:
        logger.error(f"Task execution failed for task {task_id}: {e}")

        # Rollback on error
        db.rollback()

        # Update execution if it was created
        if execution:
            try:
                execution.completed_at = datetime.now(timezone.utc)
                execution.status = 'failed'
                execution.errors = [str(e)]
                db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to update execution record: {commit_error}")
                db.rollback()

    finally:
        # Close database session
        db.close()
        try:
            next(db_generator)
        except StopIteration:
            pass


def calculate_next_run(task: Task) -> Optional[datetime]:
    """
    Calculate next run time based on task schedule configuration

    Args:
        task: Task with schedule configuration

    Returns:
        Next run datetime or None if not scheduled
    """
    if not task.schedule_type or not task.schedule_config:
        return None

    now = datetime.now(timezone.utc)

    if task.schedule_type == 'interval':
        # Interval schedule: add interval to current time
        interval_config = task.schedule_config

        # Support weeks, days, hours, minutes
        delta_kwargs = {}
        if 'weeks' in interval_config:
            delta_kwargs['weeks'] = interval_config['weeks']
        if 'days' in interval_config:
            delta_kwargs['days'] = interval_config['days']
        if 'hours' in interval_config:
            delta_kwargs['hours'] = interval_config['hours']
        if 'minutes' in interval_config:
            delta_kwargs['minutes'] = interval_config['minutes']

        if delta_kwargs:
            return now + timedelta(**delta_kwargs)

    elif task.schedule_type == 'cron':
        # Cron schedule: use cron expression to calculate next run
        cron_config = task.schedule_config

        try:
            trigger = CronTrigger(
                year=cron_config.get('year'),
                month=cron_config.get('month'),
                day=cron_config.get('day'),
                week=cron_config.get('week'),
                day_of_week=cron_config.get('day_of_week'),
                hour=cron_config.get('hour'),
                minute=cron_config.get('minute'),
                second=cron_config.get('second', 0),
                timezone='UTC'
            )

            # Get next fire time
            next_run = trigger.get_next_fire_time(None, now)
            return next_run

        except Exception as e:
            logger.error(f"Failed to calculate cron next run: {e}")
            return None

    return None


async def schedule_task(task: Task):
    """
    Add or update task in scheduler

    Creates appropriate trigger based on task schedule type:
    - once: DateTrigger for one-time execution
    - interval: IntervalTrigger for periodic execution
    - cron: CronTrigger for cron-like scheduling

    Args:
        task: Task to schedule
    """
    scheduler = get_scheduler()

    # Skip if task is not active or has no schedule
    if task.status != 'active':
        logger.info(f"Task {task.id} is not active, skipping schedule")
        return

    if not task.schedule_type:
        logger.info(f"Task {task.id} has no schedule type, skipping")
        return

    # Job ID is task-{task_id}
    job_id = f"task-{task.id}"

    # Remove existing job if present
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed existing job {job_id}")

    # Create trigger based on schedule type
    trigger = None
    schedule_config = task.schedule_config or {}

    if task.schedule_type == 'once':
        # One-time execution at specified time
        run_date = schedule_config.get('run_date')

        if run_date:
            # Convert string to datetime if needed
            if isinstance(run_date, str):
                run_date = datetime.fromisoformat(run_date)

            trigger = DateTrigger(run_date=run_date, timezone='UTC')
            logger.info(f"Created DateTrigger for task {task.id} at {run_date}")

    elif task.schedule_type == 'interval':
        # Periodic execution
        interval_kwargs = {}

        if 'weeks' in schedule_config:
            interval_kwargs['weeks'] = schedule_config['weeks']
        if 'days' in schedule_config:
            interval_kwargs['days'] = schedule_config['days']
        if 'hours' in schedule_config:
            interval_kwargs['hours'] = schedule_config['hours']
        if 'minutes' in schedule_config:
            interval_kwargs['minutes'] = schedule_config['minutes']
        if 'seconds' in schedule_config:
            interval_kwargs['seconds'] = schedule_config['seconds']

        if interval_kwargs:
            trigger = IntervalTrigger(**interval_kwargs, timezone='UTC')
            logger.info(f"Created IntervalTrigger for task {task.id}: {interval_kwargs}")

    elif task.schedule_type == 'cron':
        # Cron-like scheduling
        cron_kwargs = {
            'timezone': 'UTC'
        }

        # Add cron fields
        for field in ['year', 'month', 'day', 'week', 'day_of_week', 'hour', 'minute', 'second']:
            if field in schedule_config:
                cron_kwargs[field] = schedule_config[field]

        trigger = CronTrigger(**cron_kwargs)
        logger.info(f"Created CronTrigger for task {task.id}: {cron_kwargs}")

    # Add job to scheduler
    if trigger:
        scheduler.add_job(
            execute_task,
            trigger=trigger,
            args=[task.id],
            id=job_id,
            name=f"Task: {task.name}",
            replace_existing=True
        )

        # Update next_run_at in database
        db_generator = get_db()
        db = next(db_generator)

        try:
            task.next_run_at = calculate_next_run(task)
            db.commit()
        finally:
            db.close()
            try:
                next(db_generator)
            except StopIteration:
                pass

        logger.info(f"Scheduled task {task.id} with job ID {job_id}")
    else:
        logger.warning(f"Failed to create trigger for task {task.id}")


async def unschedule_task(task_id: int):
    """
    Remove task from scheduler

    Args:
        task_id: ID of task to unschedule
    """
    scheduler = get_scheduler()
    job_id = f"task-{task_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Unscheduled task {task_id}")

        # Clear next_run_at in database
        db_generator = get_db()
        db = next(db_generator)

        try:
            task = get_task(db, task_id)
            if task:
                task.next_run_at = None
                db.commit()
        finally:
            db.close()
            try:
                next(db_generator)
            except StopIteration:
                pass
    else:
        logger.warning(f"No job found for task {task_id}")


async def start_scheduler():
    """
    Start the scheduler and load all active tasks
    """
    scheduler = get_scheduler()

    # Start scheduler if not running
    if not scheduler.running:
        scheduler.start()
        logger.info("Started APScheduler")

    # Load all active tasks
    db_generator = get_db()
    db = next(db_generator)

    try:
        from .models import get_active_tasks
        tasks = get_active_tasks(db)

        for task in tasks:
            try:
                await schedule_task(task)
            except Exception as e:
                logger.error(f"Failed to schedule task {task.id}: {e}")

        logger.info(f"Loaded {len(tasks)} active tasks into scheduler")

    finally:
        db.close()
        try:
            next(db_generator)
        except StopIteration:
            pass


async def stop_scheduler():
    """
    Stop the scheduler gracefully
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Stopped APScheduler")
        _scheduler = None
