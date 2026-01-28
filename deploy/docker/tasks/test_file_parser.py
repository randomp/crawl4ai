"""
Tests for File Parser

This module contains tests for the WeChat URL file parser functionality.
Tests cover URL validation, Excel file parsing, and CSV file parsing.
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os

from file_parser import validate_wechat_url, parse_wechat_file


def test_validate_wechat_url():
    """Test WeChat URL validation function."""
    # Valid WeChat URLs
    assert validate_wechat_url("https://mp.weixin.qq.com/s/abc123") is True
    assert validate_wechat_url("https://mp.weixin.qq.com/s/xyz789?param=value") is True
    assert validate_wechat_url("http://mp.weixin.qq.com/s/test") is True

    # Invalid URLs
    assert validate_wechat_url("https://example.com") is False
    assert validate_wechat_url("https://weixin.qq.com/s/abc") is False
    assert validate_wechat_url("https://mp.weixin.qq.com/other/path") is False
    assert validate_wechat_url("not a url") is False
    assert validate_wechat_url("") is False
    assert validate_wechat_url(None) is False
    assert validate_wechat_url(123) is False

    # Edge cases
    assert validate_wechat_url("  https://mp.weixin.qq.com/s/abc  ") is True  # With whitespace
    assert validate_wechat_url("https://mp.weixin.qq.com/") is False  # Missing /s path


def test_parse_excel_file():
    """Test parsing Excel file containing WeChat URLs."""
    # Create temporary Excel file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create test data
        test_data = {
            'Title': ['Article 1', 'Article 2', 'Article 3', 'Article 4'],
            'URL': [
                'https://mp.weixin.qq.com/s/article1',
                'https://mp.weixin.qq.com/s/article2',
                'https://example.com/invalid',
                'https://mp.weixin.qq.com/s/article1'  # Duplicate
            ],
            'Author': ['Author A', 'Author B', 'Author C', 'Author D']
        }

        df = pd.DataFrame(test_data)
        df.to_excel(tmp_path, index=False)

        # Parse the file
        result = parse_wechat_file(tmp_path)

        # Assertions
        assert result['total_rows'] == 4
        assert result['urls_found'] == 3  # 3 valid URLs found (invalid URL is excluded)
        assert result['unique_urls'] == 2  # 2 unique valid URLs (one duplicate removed)
        assert 'URL' in result['url_columns']
        assert len(result['urls']) == 2
        assert 'https://mp.weixin.qq.com/s/article1' in result['urls']
        assert 'https://mp.weixin.qq.com/s/article2' in result['urls']

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_parse_csv_file():
    """Test parsing CSV file containing WeChat URLs."""
    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as tmp:
        tmp_path = tmp.name

    try:
        # Create test data
        test_data = {
            'ID': [1, 2, 3, 4, 5],
            'Article_URL': [
                'https://mp.weixin.qq.com/s/test1',
                'https://mp.weixin.qq.com/s/test2',
                '',  # Empty
                'https://mp.weixin.qq.com/s/test3',
                'not a url'
            ],
            'Category': ['Tech', 'News', 'Blog', 'Tech', 'News']
        }

        df = pd.DataFrame(test_data)
        df.to_csv(tmp_path, index=False)

        # Parse the file
        result = parse_wechat_file(tmp_path)

        # Assertions
        assert result['total_rows'] == 5
        assert result['urls_found'] == 3  # 3 valid URLs found
        assert result['unique_urls'] == 3  # 3 unique valid URLs
        assert 'Article_URL' in result['url_columns']
        assert len(result['urls']) == 3
        assert 'https://mp.weixin.qq.com/s/test1' in result['urls']
        assert 'https://mp.weixin.qq.com/s/test2' in result['urls']
        assert 'https://mp.weixin.qq.com/s/test3' in result['urls']

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_parse_nonexistent_file():
    """Test parsing a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        parse_wechat_file('/nonexistent/path/file.xlsx')


def test_parse_unsupported_format():
    """Test parsing a file with unsupported format."""
    # Create temporary .txt file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write("Some text content")

    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            parse_wechat_file(tmp_path)

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
