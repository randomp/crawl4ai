"""
File Parser for WeChat URLs

This module provides functionality to parse Excel and CSV files containing WeChat article URLs.
It automatically detects the file format, finds columns containing WeChat URLs, validates them,
and returns deduplicated results with parsing statistics.
"""

import os
import pandas as pd
from typing import Dict, List, Set
from urllib.parse import urlparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/tmp/uploads')).resolve()


def validate_wechat_url(url: str) -> bool:
    """
    Validate if a URL is a valid WeChat article URL.

    Args:
        url: The URL string to validate

    Returns:
        bool: True if the URL is a valid WeChat article URL, False otherwise

    Examples:
        >>> validate_wechat_url("https://mp.weixin.qq.com/s/abc123")
        True
        >>> validate_wechat_url("https://example.com")
        False
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        # Check if domain is mp.weixin.qq.com and path starts with /s
        return (
            parsed.netloc == "mp.weixin.qq.com" and
            parsed.path.startswith("/s")
        )
    except Exception as e:
        logger.debug(f"Error parsing URL {url}: {e}")
        return False


def parse_wechat_file(file_path: str) -> Dict:
    """
    Parse an Excel or CSV file containing WeChat article URLs.

    This function:
    1. Auto-detects the file format (Excel or CSV)
    2. Reads the file into a DataFrame
    3. Searches all columns for WeChat URLs
    4. Validates and deduplicates URLs
    5. Returns statistics about the parsing process

    Args:
        file_path: Path to the Excel (.xlsx, .xls) or CSV (.csv) file

    Returns:
        Dict containing:
            - total_rows (int): Total number of rows in file
            - url_columns (List[str]): Names of columns containing WeChat URLs
            - urls_found (int): Total WeChat URLs found before deduplication
            - unique_urls (int): Number of unique WeChat URLs after deduplication
            - urls (List[str]): List of unique valid WeChat URLs

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported, path is invalid, or file is too large

    Examples:
        >>> result = parse_wechat_file("articles.xlsx")
        >>> print(f"Found {result['unique_urls']} unique URLs")
    """
    try:
        # Security: Path traversal protection
        file_path_obj = Path(file_path).resolve()

        # Validate path is within allowed upload directory
        try:
            file_path_obj.relative_to(UPLOAD_DIR)
        except ValueError:
            raise ValueError(f"Invalid file path: must be within upload directory")

        # Check if file exists
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Security: File size validation to prevent DoS
        file_size = file_path_obj.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_FILE_SIZE} bytes ({MAX_FILE_SIZE // (1024*1024)}MB)")

        # Detect file format and read file
        file_extension = file_path_obj.suffix.lower()

        if file_extension in ['.xlsx', '.xls']:
            logger.info(f"Reading Excel file: {file_path}")
            df = pd.read_excel(file_path)
        elif file_extension == '.csv':
            logger.info(f"Reading CSV file: {file_path}")
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Only .xlsx, .xls, and .csv are supported.")

        total_rows = len(df)
        logger.info(f"File contains {total_rows} rows and {len(df.columns)} columns")

        # Search for WeChat URLs in all columns
        urls: List[str] = []
        url_columns: Set[str] = set()

        for column in df.columns:
            # Iterate through values in the column
            for value in df[column]:
                # Skip NaN and empty strings using proper pandas NaN detection
                if pd.isna(value) or str(value).strip() == '':
                    continue

                # Convert to string for URL checking
                value = str(value)

                # Check if the value looks like a URL (contains http)
                if 'http' in value.lower():
                    # Validate as WeChat URL
                    if validate_wechat_url(value):
                        urls.append(value.strip())
                        url_columns.add(column)

        # Deduplicate URLs
        unique_urls = list(set(urls))

        result = {
            'total_rows': total_rows,
            'url_columns': list(url_columns),
            'urls_found': len(urls),
            'unique_urls': len(unique_urls),
            'urls': unique_urls
        }

        logger.info(
            f"Parsing complete: {len(unique_urls)} unique URLs found "
            f"from {len(urls)} total URLs in {len(url_columns)} columns"
        )

        return result

    except (FileNotFoundError, pd.errors.ParserError, ValueError) as e:
        logger.error(f"Failed to parse file: {e}")
        raise
