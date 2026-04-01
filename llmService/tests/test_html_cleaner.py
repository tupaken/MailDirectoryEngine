"""Unit tests for HTML-to-text conversion helpers."""

import unittest

from llmService.HTMLClean.htmlCleaner import html_to_text


class HtmlCleanerTests(unittest.TestCase):
    """Test cases for :func:`html_to_text`."""

    def test_html_to_text_strips_tags_and_preserves_text_order(self):
        """HTML tags should be removed while text order stays intact."""
        html = "<div>Hello <b>World</b><br/><a href='#'>Link</a></div>"

        result = html_to_text(html)

        self.assertEqual("Hello\nWorld\nLink", result)

    def test_html_to_text_handles_empty_input(self):
        """Empty HTML input should return an empty string."""
        self.assertEqual("", html_to_text(""))


if __name__ == "__main__":
    unittest.main()
