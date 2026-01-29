# deploy/docker/tasks/wechat_scraper.py
"""
WeChat article scraper with incremental crawling
"""

import asyncio
import hashlib
import json
import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from .models import Task, Article, get_existing_urls, get_article_by_hash, get_db

logger = logging.getLogger(__name__)


class ArticleLink:
    """Represents a discovered article link"""
    def __init__(self, url: str, title: str = None, publish_time: datetime = None):
        self.url = url
        self.title = title
        self.publish_time = publish_time


async def discover_wechat_articles(
    crawler: AsyncWebCrawler,
    account_url: str,
    since_time: Optional[datetime] = None
) -> List[ArticleLink]:
    """
    Phase 1: Discover article URLs from WeChat public account

    Args:
        crawler: AsyncWebCrawler instance
        account_url: WeChat account homepage URL
        since_time: Only return articles published after this time

    Returns:
        List of discovered article links
    """
    logger.info(f"Discovering articles from: {account_url}")

    # Anti-bot measure: random delay before starting
    await asyncio.sleep(random.uniform(1, 2))

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        # Scroll to load more articles
        js_code=["""
            (async () => {
                for (let i = 0; i < 3; i++) {
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(r => setTimeout(r, 2000));
                }
            })();
        """],
        wait_for="css:.weui_media_bd",
        delay_before_return_html=2.0
    )

    try:
        result = await crawler.arun(account_url, config=config)

        # Extract article links from HTML
        # This is a simplified version - actual implementation needs DOM parsing
        article_links = extract_article_links_from_html(result.html)

        # Filter by time if specified
        if since_time:
            article_links = [
                link for link in article_links
                if link.publish_time and link.publish_time > since_time
            ]

        logger.info(f"Discovered {len(article_links)} articles")
        return article_links

    except Exception as e:
        logger.error(f"Failed to discover articles from {account_url}: {e}")
        return []


def extract_article_links_from_html(html: str) -> List[ArticleLink]:
    """
    Extract article links from WeChat account page HTML

    Args:
        html: Page HTML content

    Returns:
        List of article links with metadata
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = []

    # Find article links (WeChat-specific selectors)
    # This is simplified - actual selectors depend on WeChat's HTML structure
    for link_elem in soup.select('a[href*="/s/"], a[href*="__biz="]'):
        url = link_elem.get('href', '')

        if not url.startswith('http'):
            url = 'https://mp.weixin.qq.com' + url

        # Try to extract title
        title_elem = link_elem.select_one('.title, .article_title')
        title = title_elem.text.strip() if title_elem else None

        links.append(ArticleLink(url=url, title=title))

    return links


async def crawl_article_content(
    crawler: AsyncWebCrawler,
    article_url: str
) -> Optional[Dict]:
    """
    Phase 2: Crawl individual article content

    Args:
        crawler: AsyncWebCrawler instance
        article_url: Article URL to crawl

    Returns:
        Dictionary with article data or None if failed
    """
    logger.info(f"Crawling article: {article_url}")

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=50,
        extraction_strategy=JsonCssExtractionStrategy(schema={
            "name": "WeChat Article",
            "baseSelector": "#js_article, .rich_media_area_primary",
            "fields": [
                {"name": "title", "selector": "#activity-name, .rich_media_title", "type": "text"},
                {"name": "author", "selector": "#js_name, .rich_media_meta_text", "type": "text"},
                {"name": "publish_time", "selector": "#publish_time, .publish_time", "type": "text"},
                {"name": "content", "selector": "#js_content, .rich_media_content", "type": "text"}
            ]
        })
    )

    try:
        result = await crawler.arun(article_url, config=config)

        # Validate crawl succeeded
        if not result.success or not result.extracted_content:
            logger.warning(f"No content extracted from {article_url}")
            return None

        # Safe JSON parsing with proper error handling
        try:
            extracted = json.loads(result.extracted_content)
            if not extracted or len(extracted) == 0:
                logger.warning(f"Empty extraction result from {article_url}")
                return None
            data = extracted[0]
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse extracted content from {article_url}: {e}")
            return None

        # Content validation - check minimum length
        content = data.get('content', '').strip()
        if not content or len(content) < 100:
            logger.warning(f"Article content too short ({len(content)} chars): {article_url}")
            return None

        return {
            'url': article_url,
            'title': data.get('title', '').strip(),
            'author': data.get('author', '').strip(),
            'publish_time': parse_wechat_time(data.get('publish_time', '')),
            'content': content,
            'metadata': {
                'word_count': len(result.markdown.split()),
                'images': len(result.media.get('images', [])),
            }
        }

    except Exception as e:
        logger.error(f"Failed to crawl article {article_url}: {e}")
        return None


def parse_wechat_time(time_str: str) -> Optional[datetime]:
    """Parse WeChat publish time string to datetime"""
    if not time_str:
        return None

    # WeChat time formats can vary, add parsing logic here
    # For now, return None and rely on crawl time
    return None


async def incremental_crawl(
    task: Task,
    crawler: AsyncWebCrawler,
    execution_id: int
) -> Dict:
    """
    Main incremental crawling function

    Args:
        task: Task configuration
        crawler: AsyncWebCrawler instance
        execution_id: Current execution ID for logging

    Returns:
        Statistics dictionary with crawl results
    """
    logger.info(f"Starting incremental crawl for task {task.id}")

    stats = {
        'total': 0,
        'new': 0,
        'updated': 0,
        'errors': []
    }

    # Get last crawl timestamp (timezone-aware)
    last_run = task.last_run_at or datetime(1970, 1, 1, tzinfo=timezone.utc)

    # Discover new articles from all accounts
    all_articles = []
    for account_url in task.wechat_urls:
        try:
            articles = await discover_wechat_articles(crawler, account_url, last_run)
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Failed to discover from {account_url}: {e}")
            stats['errors'].append(f"Discovery failed for {account_url}: {str(e)}")

    stats['total'] = len(all_articles)
    logger.info(f"Discovered {stats['total']} articles total")

    # Database session management with proper context handling
    db_generator = get_db()
    db = next(db_generator)

    try:
        # URL deduplication - check existing URLs
        urls_to_check = [a.url for a in all_articles]
        existing_urls = get_existing_urls(db, task.id)
        articles_to_crawl = [a for a in all_articles if a.url not in existing_urls]

        logger.info(f"{len(articles_to_crawl)} new articles to crawl")

        # Crawl new articles
        for article_link in articles_to_crawl:
            try:
                # Anti-bot measure: random delay between articles
                await asyncio.sleep(random.uniform(1, 3))

                # Crawl content
                article_data = await crawl_article_content(crawler, article_link.url)

                if not article_data:
                    continue

                # Calculate content hash
                content_hash = hashlib.sha256(
                    article_data['content'].encode()
                ).hexdigest()

                # Check if content already exists
                existing = get_article_by_hash(db, content_hash)

                if not existing:
                    # Save new article
                    article = Article(
                        task_id=task.id,
                        url=article_data['url'],
                        title=article_data['title'],
                        author=article_data['author'],
                        publish_time=article_data['publish_time'],
                        content=article_data['content'],
                        content_hash=content_hash,
                        metadata=article_data['metadata']
                    )
                    db.add(article)
                    stats['new'] += 1
                else:
                    stats['updated'] += 1
                    logger.info(f"Duplicate content found: {article_link.url}")

            except Exception as e:
                logger.error(f"Failed to process {article_link.url}: {e}")
                stats['errors'].append(f"Failed to crawl {article_link.url}: {str(e)}")

        # Commit all new articles
        try:
            db.commit()
            logger.info(f"Saved {stats['new']} new articles")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save articles: {e}")
            stats['errors'].append(f"Database error: {str(e)}")

    finally:
        # Proper database session cleanup
        db.close()
        try:
            next(db_generator)
        except StopIteration:
            pass

    return stats
