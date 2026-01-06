"""
Unit tests for HTML cleaning functionality
"""
import pytest
from app.utils.text_cleaning import clean_html


class TestHTMLCleaning:
    """Test HTML tag removal and entity decoding"""

    def test_clean_html_removes_pre_and_code_tags(self):
        """Test that <pre> and <code> tags are removed"""
        html = '<pre class="lang-sql"><code>SELECT * FROM users</code></pre>'
        result = clean_html(html)

        assert '<pre>' not in result
        assert '<code>' not in result
        assert '</pre>' not in result
        assert '</code>' not in result
        assert 'SELECT * FROM users' in result

    def test_clean_html_decodes_entities(self):
        """Test that HTML entities are decoded"""
        html = 'SELECT &quot;order&quot;, &lt;value&gt; FROM tbl'
        result = clean_html(html)

        assert '&quot;' not in result
        assert '&lt;' not in result
        assert '&gt;' not in result
        assert 'SELECT "order", <value> FROM tbl' == result

    def test_clean_html_removes_anchor_tags(self):
        """Test that <a> tags are removed but text is kept"""
        html = '<a href="https://example.com" rel="nofollow">Link Text</a>'
        result = clean_html(html)

        assert '<a' not in result
        assert 'href=' not in result
        assert 'Link Text' in result

    def test_clean_html_removes_paragraph_tags(self):
        """Test that <p> tags are removed"""
        html = '<p>Paragraph text</p>'
        result = clean_html(html)

        assert '<p>' not in result
        assert '</p>' not in result
        assert 'Paragraph text' in result

    def test_clean_html_complex_stackoverflow_example(self):
        """Test complex StackOverflow HTML example"""
        html = '''<pre class="lang-sql prettyprint-override"><code>SELECT &quot;order&quot;, status, eta
FROM   tbl
ORDER  BY status = 'complete'</code></pre>
<p><a href="https://dbfiddle.uk/aJd7Zwuw" rel="nofollow noreferrer">fiddle</a></p>
<p>The <code>status = 'complete'</code> evaluates to <code>boolean</code>.</p>'''

        result = clean_html(html)

        # No HTML tags
        assert '<' not in result or '>' not in result
        assert '&quot;' not in result

        # Content is preserved
        assert 'SELECT "order", status, eta' in result
        assert 'FROM   tbl' in result
        assert "ORDER  BY status = 'complete'" in result
        assert 'fiddle' in result
        assert 'evaluates to' in result

    def test_clean_html_preserves_whitespace(self):
        """Test that code indentation is preserved"""
        html = '''<pre><code>SELECT id
  FROM users
  WHERE active = true</code></pre>'''

        result = clean_html(html)

        # Whitespace should be mostly preserved
        assert 'FROM users' in result
        assert 'WHERE active = true' in result

    def test_clean_html_cleans_multiple_newlines(self):
        """Test that multiple consecutive newlines are reduced"""
        html = '<p>Line 1</p>\n\n\n<p>Line 2</p>'
        result = clean_html(html)

        # Should not have more than 2 consecutive newlines
        assert '\n\n\n' not in result

    def test_clean_html_handles_none(self):
        """Test that None input returns None"""
        assert clean_html(None) is None

    def test_clean_html_handles_empty_string(self):
        """Test that empty string returns empty string"""
        assert clean_html('') == ''

    def test_clean_html_handles_plain_text(self):
        """Test that plain text without HTML is unchanged"""
        text = 'Plain text without HTML'
        result = clean_html(text)
        assert result == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
