"""
WeChat Article Crawler Console - Task Management System

A production-ready task management system for automated crawling
of WeChat public account articles with incremental updates.
"""

__version__ = "1.0.0"
__author__ = "Crawl4AI Team"

from .models import Task, Article, TaskExecution
from .router import router

__all__ = ['Task', 'Article', 'TaskExecution', 'router']
