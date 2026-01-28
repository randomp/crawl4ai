"""
Test database models

NOTE: This test requires a running PostgreSQL instance.
To run: python test_models.py
"""

import os
from models import init_database, get_db_session, Task, Article, TaskExecution
from datetime import datetime, timezone

def test_models():
    """Test database models creation and basic operations"""
    # Set test database URL
    os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5432/wechat_crawler_test'

    # Initialize database
    print("Initializing database...")
    init_database()

    # Get session
    db = get_db_session()

    try:
        # Create a test task
        task = Task(
            name="test_task",
            description="Test task for model verification",
            source_file="/path/to/urls.txt",
            wechat_urls=["https://mp.weixin.qq.com/s/test1", "https://mp.weixin.qq.com/s/test2"],
            crawl_config={"wait_time": 2000, "user_agent": "custom"},
            schedule_type="cron",
            schedule_config={"cron": "0 */6 * * *"},
            status="active"
        )
        db.add(task)
        db.commit()
        print(f"Created task: {task.to_dict()}")

        # Create a test article
        article = Article(
            task_id=task.id,
            url="https://mp.weixin.qq.com/s/test123",
            content_hash="abc123def456",
            title="Test Article",
            author="Test Author",
            publish_time=datetime.now(timezone.utc)
        )
        db.add(article)
        db.commit()
        print(f"Created article: {article.to_dict()}")

        # Create a test execution
        execution = TaskExecution(
            task_id=task.id,
            status="completed",
            articles_found=1,
            articles_new=1,
            errors=[],
            execution_log="Task executed successfully"
        )
        db.add(execution)
        db.commit()
        print(f"Created execution: {execution.to_dict()}")

        print("\nAll models created successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    test_models()
