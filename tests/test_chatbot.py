import sys
import os
import unittest

DIR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(DIR_ROOT)

from chatbot import ChatBot

class TestChatbot(unittest.TestCase):
    def test_chatbot(self):
        self.assertIsInstance(ChatBot().show_help_message(), str)
