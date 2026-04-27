"""Unit tests for HTML-to-text conversion helpers."""

import os
import tempfile
import unittest

from llmService.HTMLClean.htmlCleaner import html_to_text, subject_from_send


class HtmlCleanerTests(unittest.TestCase):
    """Test cases for HTML cleaner helpers."""

    def test_html_to_text_strips_tags_and_preserves_text_order(self):
        """HTML tags should be removed while text order stays intact."""
        html = "<div>Hello <b>World</b><br/><a href='#'>Link</a></div>"

        result = html_to_text(html)

        self.assertEqual("Hello\nWorld\nLink", result)

    def test_html_to_text_handles_empty_input(self):
        """Empty HTML input should return an empty string."""
        self.assertEqual("", html_to_text(""))

    def test_subject_from_send_reads_subject_header_from_eml(self):
        """Raw `.eml` files should expose their Subject header."""

        with tempfile.NamedTemporaryFile("wb", delete=False) as temp_file:
            temp_file.write(
                b"Subject: 12 345 Angebot\r\n"
                b"From: sender@example.invalid\r\n"
                b"To: receiver@example.invalid\r\n"
                b"\r\n"
                b"Body\r\n"
            )
            temp_path = temp_file.name

        try:
            self.assertEqual("12 345 Angebot", subject_from_send(temp_path))
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
