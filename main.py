import logging
import logger
import asyncio
import os
import sys
import random
import threading
import queue
from telethon import TelegramClient
from utils import DataStore, ServerSentEvent as SSE, MyQueue, generate_cache_buster
from quart import Quart, render_template, abort, Response, request
from hypercorn.config import Config
from hypercorn.asyncio import serve


store = DataStore()
APP = Quart(__name__)
BOT_TOKEN = os.environ['Token']
BOT_NAME = os.environ["BotName"]
API_HASH = os.environ['ApiHash']
API_ID = os.environ['ApiId']
CHAT = os.environ["Chat"]
LOOP = asyncio.new_event_loop()
LOOP.name = "MainLoop"
store.log_queue_site = MyQueue(maxsize=20)
store.count = 0


async def main():
	log.info("start")
	log.info("end")


@APP.before_serving
async def startup():
	await main()
	log.info("server started")


@APP.after_serving
async def shutdown():
	log.info("server shutdown")


@APP.route('/')
async def index():
	cache_console = generate_cache_buster("js", "console.js", path_static=APP.static_folder)
	cache_styles = generate_cache_buster("css", "styles.css", path_static=APP.static_folder)
	template = await render_template('index.html', cache_console=cache_console, cache_styles=cache_styles)
	return template


store.sse_clients = {}


@APP.route("/log-stream")
async def sse_log_stream():
	if "text/event-stream" not in request.accept_mimetypes:
		abort(400)

	async def log_stream():
		while True:
			logs = list(await store.log_queue_site.get_changed())
			data = "".join(logs)
			data = data.replace("\n", "<br>")
			log.debug(data, extra={"qh": False})
			event = SSE(data)
			yield event.encode()
			await asyncio.sleep(1)

	return Response(log_stream(), content_type="text/event-stream")


async def start_server():
	hypercorn_quart_cfg = Config()
	if sys.platform.startswith('win'):
		log.info(f"Используется адрес по умолчанию для {sys.platform}")
	else:
		hypercorn_quart_cfg.bind = ["0.0.0.0:8080"]
	hypercorn_quart_cfg.startup_timeout = 200
	await serve(APP, hypercorn_quart_cfg)


if __name__ == '__main__':
	asyncio.set_event_loop(LOOP)

	if sys.platform.startswith('win'):
		logger.init(view_replit=False)
	else:
		logger.init()
	log = logger.get_logger(__name__)

	if sys.gettrace() is not None:
		log.info("Программа запущена в режиме отладки.")
	else:
		logger_main = logging.getLogger(logger.name_log)
		logger_main.setLevel(logging.INFO)
		log.info("Программа запущена в обычном режиме.")

	logger.active_file_handler()
	logger.active_queue_handler(store.log_queue_site)
	logger.active_telegram_handler(BOT_NAME, API_ID, API_HASH,
																 BOT_TOKEN, CHAT)

	try:
		LOOP.run_until_complete(start_server())
	except:
		log.exception("#" * (44 - 16) + "\nEnd program cause error:")
