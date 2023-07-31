import unittest
import asynctest
import os
import logging
import logger


class TestTelegramBotLogger(unittest.TestCase):
	def test_working(self):
		BOT_TOKEN = os.environ['Token']
		BOT_NAME = os.environ["BotName"]
		API_HASH = os.environ['ApiHash']
		API_ID = os.environ['ApiId']
		CHAT = os.environ["Chat"]

		logger.init(level_console=logging.CRITICAL)
		log = logger.get_logger(__name__)
		tgh = logger.active_telegram_handler3(BOT_NAME, API_ID,
															 						API_HASH, BOT_TOKEN, CHAT,
																					fmt="[{levelname}] {message}")
		client_mock = asynctest.MagicMock(spec=tgh.client)
		loop = tgh.loop
		tgh.client = client_mock
		client_mock.send_message.return_value = None

		log.info("test")
		client_mock.send_message.assert_called_once_with(CHAT, "[INFO] test")
		loop.stop()

if __name__ == '__main__':
	unittest.main()
