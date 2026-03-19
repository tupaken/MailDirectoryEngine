import unittest

from llm_service.HTMLClean.htmlCleaner import html_to_text


class HtmlCleanerTests(unittest.TestCase):
    def test_html_to_text_strips_tags_and_preserves_text_order(self):
        html = "<div>Hello <b>World</b><br/><a href='#'>Link</a></div>"

        result = html_to_text(html)

        self.assertEqual("Hello\nWorld\nLink", result)

    def test_html_to_text_handles_empty_input(self):
        self.assertEqual("", html_to_text(""))


if __name__ == "__main__":
    unittest.main()
