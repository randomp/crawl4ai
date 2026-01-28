"""
Database models for WeChat article crawler task management
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime,
    Text, ForeignKey, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
import os

Base = declarative_base()

# Singleton engine instance
_engine = None


class Task(Base):
    """Task model for crawler tasks"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    source_file = Column(String(500), nullable=False)
    wechat_urls = Column(JSON, nullable=True)  # Array of WeChat URLs to crawl
    crawl_config = Column(JSON, nullable=True)  # Crawler configuration options
    schedule_type = Column(String(50), nullable=True)  # manual, interval, cron
    schedule_config = Column(JSON, nullable=True)  # Schedule configuration (interval or cron)
    status = Column(String(50), default='active', index=True)  # active, paused, deleted
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Relationships
    articles = relationship("Article", back_populates="task", cascade="all, delete-orphan")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_task_status_next_run', 'status', 'next_run_at'),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<Task(id={self.id}, name={self.name!r}, status={self.status!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'source_file': self.source_file,
            'wechat_urls': self.wechat_urls,
            'crawl_config': self.crawl_config,
            'schedule_type': self.schedule_type,
            'schedule_config': self.schedule_config,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
        }


class Article(Base):
    """Article model for crawled WeChat articles"""
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of content
    title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    publish_time = Column(DateTime, nullable=True)
    content = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    task = relationship("Task", back_populates="articles")

    # Indexes
    __table_args__ = (
        Index('idx_article_task_crawled', 'task_id', 'crawled_at'),
        Index('idx_article_publish_time', 'publish_time'),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<Article(id={self.id}, url={self.url!r}, title={self.title!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'url': self.url,
            'content_hash': self.content_hash,
            'title': self.title,
            'author': self.author,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'crawled_at': self.crawled_at.isoformat() if self.crawled_at else None,
        }


class TaskExecution(Base):
    """Task execution history model"""
    __tablename__ = 'task_executions'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default='running', index=True)  # running, completed, failed
    articles_found = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    articles_updated = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)  # Array of error messages
    execution_log = Column(Text, nullable=True)  # Detailed execution log

    # Relationships
    task = relationship("Task", back_populates="executions")

    # Indexes
    __table_args__ = (
        Index('idx_execution_task_started', 'task_id', 'started_at'),
        Index('idx_execution_status', 'status'),
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, status={self.status!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'articles_found': self.articles_found,
            'articles_new': self.articles_new,
            'articles_updated': self.articles_updated,
            'errors': self.errors,
            'execution_log': self.execution_log,
        }


# Database connection and helper functions

def get_database_url() -> str:
    """Get database URL from environment variables"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/wechat_crawler'
    )


def get_engine(database_url: Optional[str] = None):
    """Get or create singleton database engine"""
    global _engine
    if _engine is None:
        url = database_url or get_database_url()
        _engine = create_engine(url, echo=False, pool_pre_ping=True)
    return _engine


def init_database(database_url: Optional[str] = None):
    """Initialize database and create all tables"""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_db_session(database_url: Optional[str] = None) -> Session:
    """Get database session"""
    engine = get_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


# Helper functions for common queries

def get_task(db: Session, task_id: int) -> Optional[Task]:
    """Get task by ID"""
    return db.query(Task).filter(Task.id == task_id).first()


def get_active_tasks(db: Session) -> List[Task]:
    """Get all active tasks"""
    return db.query(Task).filter(Task.status == 'active').all()


def get_existing_urls(db: Session, task_id: int) -> set:
    """Get set of existing article URLs for a task"""
    articles = db.query(Article.url).filter(Article.task_id == task_id).all()
    return {article.url for article in articles}


def get_article_by_hash(db: Session, content_hash: str) -> Optional[Article]:
    """Get article by content hash"""
    return db.query(Article).filter(Article.content_hash == content_hash).first()
