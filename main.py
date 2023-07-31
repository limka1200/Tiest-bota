import logging
import logger
import asyncio
import os
import sys
import random
import threading
import queue
from telethon import TelegramClient
from utils import DataStore, ServerSentEvent as SSE, MyQueue
from quart import Quart, render_template, abort, Response, request
from hypercorn.config import Config
from hypercorn.asyncio import serve
import hashlib
from limits import Sleeper


def generate_cache_buster(filename):
	"""
    Генерирует хеш-сумму MD5 для содержимого указанного файла.

    :param filename: Имя файла, для которого нужно сгенерировать хеш-сумму.

    :return: Хеш-сумма MD5 в виде строки, представляющей собой 32-символьный шестнадцатеричный код.
    :rtype: str

    :raises FileNotFoundError: Если указанный файл не найден.
    :raises IOError: Если возникли проблемы при чтении файла.
  """
	with open(filename, "rb") as f:
		content = f.read()
		return hashlib.md5(content).hexdigest()


# exit("Program stopped by "+__name__)
console_debug_mode = 0
if bool(console_debug_mode):
	lv = logging.DEBUG
else:
	lv = logging.INFO

logger.init(level_console=lv)
logger.active_file_handler()

log = logger.get_logger(__name__)

store = DataStore()
APP = Quart(__name__)
BOT_TOKEN = os.environ['Token']
BOT_NAME = os.environ["BotName"]
API_HASH = os.environ['ApiHash']
API_ID: str = os.environ['ApiId']
CHAT = os.environ["Chat"]
LOOP = asyncio.new_event_loop()
LOOP.name = "MainLoop"
asyncio.set_event_loop(LOOP)
BOT: TelegramClient = None
store.log_queue = MyQueue(maxsize=20)
store.count = 0
logger.active_queue_handler(store.log_queue)
store.tglog = asyncio.Queue()
tgh = logger.active_telegram_handler2(store.tglog)


async def main():
	log.info("start")

	async def run_bot():
		global BOT
		try:
			log.info("bot is starting..")
			BOT = TelegramClient(BOT_NAME, API_ID, API_HASH, loop=LOOP)
			await BOT.start(bot_token=BOT_TOKEN)
			me = await BOT.get_me()
			log.info("bot status: " + str(bool(me)))
		except Exception as e:
			log.error(f"bot terminated: {e}\n", exc_info=True)

	#await run_bot()
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
	file = os.path.join(APP.static_folder, "js", "console.js")
	cache_console = generate_cache_buster(file)
	file = os.path.join(APP.static_folder, "css", "styles.css")
	cache_styles = generate_cache_buster(file)
	template = await render_template('index.html', cache_console=cache_console, cache_styles=cache_styles)
	return template


store.sse_clients = {}


@APP.route("/log-stream")
async def sse_log_stream():
	if "text/event-stream" not in request.accept_mimetypes:
		abort(400)

	async def log_stream():
		while True:
			logs = list(await store.log_queue.get_changed())
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
	try:
		LOOP.run_until_complete(start_server())
	except:
		log.exception("#" * (44 - 16) + "\nEnd program cause error:")
