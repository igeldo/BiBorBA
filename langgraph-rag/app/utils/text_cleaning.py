"""
Text cleaning utilities for StackOverflow data

This module provides functions to clean HTML content from StackOverflow
API responses, converting HTML to clean plain text.
"""

import html
import re
from typing import Optional


def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities from text

    Args:
        text: Raw text potentially containing HTML tags and entities

    Returns:
        Clean plain text with HTML removed and entities decoded

    Examples:
        >>> clean_html('<p>Hello &quot;world&quot;</p>')
        'Hello "world"'
        >>> clean_html('<code>SELECT * FROM users</code>')
        'SELECT * FROM users'
    """
    if not text:
        return text

    # Remove HTML tags first (while they're still actual tags)
    # Pattern: <tag>content</tag> → content
    text = re.sub(r'<[^>]+>', '', text)

    # Then decode HTML entities (&quot; → ", &lt; → <, etc.)
    # This preserves entities in code content like &lt;value&gt; → <value>
    text = html.unescape(text)

    # Clean up multiple newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()
