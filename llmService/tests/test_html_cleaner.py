"""Unit tests for HTML-to-text conversion helpers."""

import os
import tempfile
import unittest

from llmService.HTMLClean.htmlCleaner import content_from_send, html_to_text, subject_from_send


class HtmlCleanerTests(unittest.TestCase):
    """Test cases for HTML cleaner helpers."""

    def test_html_to_text_strips_tags_and_preserves_text_order(self):
        """HTML tags should be removed while text order stays intact."""
        html = "<div>Hello <b>World</b><br/><a href='#'>Link</a></div>"

        result = html_to_text(html)

        self.assertEqual("Hello World\nLink", result)

    def test_html_to_text_handles_empty_input(self):
        """Empty HTML input should return an empty string."""
        self.assertEqual("", html_to_text(""))

    def test_html_to_text_removes_standalone_reference_delimiters(self):
        """HTML-to-text conversion should drop quote/reference delimiter leftovers."""
        html = "<div>From:</div><div>&quot; &lt;</div><div>alex@example.invalid</div><div>&gt;</div><div>Body</div>"

        result = html_to_text(html)

        self.assertEqual("From:\nalex@example.invalid\nBody", result)

    def test_html_to_text_keeps_inline_anchor_text_on_same_line(self):
        """Inline text nodes should not be split into artificial separate lines."""
        html = "<p>Robin <a href='mailto:robin@anon.invalid'>robin@anon.invalid</a> Sample</p>"

        result = html_to_text(html)

        self.assertEqual("Robin robin@anon.invalid Sample", result)

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

    def test_content_from_send_prefers_html_body_and_ignores_attachments(self):
        """Sent `.eml` parsing should use the body part, not attachment content."""

        boundary = "mixed-boundary"
        alternative_boundary = "alt-boundary"
        with tempfile.NamedTemporaryFile("wb", delete=False) as temp_file:
            temp_file.write(
                (
                    "Subject: 12 345 Angebot\r\n"
                    "From: sender@example.invalid\r\n"
                    "To: receiver@example.invalid\r\n"
                    f"Content-Type: multipart/mixed; boundary=\"{boundary}\"\r\n"
                    "\r\n"
                    f"--{boundary}\r\n"
                    f"Content-Type: multipart/alternative; boundary=\"{alternative_boundary}\"\r\n"
                    "\r\n"
                    f"--{alternative_boundary}\r\n"
                    "Content-Type: text/plain; charset=utf-8\r\n"
                    "\r\n"
                    "Plain fallback text\r\n"
                    f"--{alternative_boundary}\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    "\r\n"
                    "<html><body><p>HTML body text</p></body></html>\r\n"
                    f"--{alternative_boundary}--\r\n"
                    f"--{boundary}\r\n"
                    "Content-Type: text/plain; charset=utf-8\r\n"
                    "Content-Disposition: attachment; filename=\"note.txt\"\r\n"
                    "\r\n"
                    "Attachment text must not appear\r\n"
                    f"--{boundary}--\r\n"
                ).encode("utf-8")
            )
            temp_path = temp_file.name

        try:
            self.assertEqual("HTML body text", content_from_send(temp_path))
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
