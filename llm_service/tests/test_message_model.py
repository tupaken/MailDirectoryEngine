import unittest

from llm_service.DB.messageModel import Message


class MessageModelTests(unittest.TestCase):
    def test_message_allows_content_only(self):
        message = Message(id=1, content="hello")

        self.assertEqual(1, message.id)
        self.assertEqual("hello", message.content)
        self.assertIsNone(message.path)

    def test_message_allows_path_only(self):
        message = Message(id=2, path="C:/tmp/2.eml")

        self.assertEqual(2, message.id)
        self.assertIsNone(message.content)
        self.assertEqual("C:/tmp/2.eml", message.path)


if __name__ == "__main__":
    unittest.main()
