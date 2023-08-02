import asyncio
import threading
import textwrap
import queue
import telethon
from limits import Sleeper
from logging import Handler, LogRecord
from asyncio import AbstractEventLoop, Task
import logging


log = logging.getLogger("MyApp").getChild(__name__)


class TelegramBotHandler(Handler):
  __version__ = "4.0.0"
  def __init__(self, bot_name, api_id, api_hash,
               token, chat, loop: AbstractEventLoop = None):
    super().__init__()
    self.bot_name = bot_name
    self.api_id = api_id
    self.api_hash = api_hash
    self.token = token
    self.chat = chat

    self.event_set_loop = threading.Event()
    if loop is None:
      try:
        self.loop = asyncio.get_running_loop()
      except RuntimeError:
        self.set_loop()
    else:
      self.loop = loop
      self.event_set_loop.set()

    self.event_started_bot = asyncio.Event()
    self.client: telethon.TelegramClient = None
    self.init_bot()

    self.event_identified_chat_type = asyncio.Event()
    self.chat_type = None
    self.init_identify_chat_type()

    self.limiter = Sleeper()
    self.limiter.add_limit("gen", 30, 1)
    self.queue_logs = asyncio.Queue()
    self.init_process_log()

  def set_loop(self):
    def run_loop():
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      self.loop = loop
      self.event_set_loop.set()
      log.debug("starting loop..", extra={"tgh": True})
      loop.run_forever()
    log.debug("creating thread for loop..", extra={"tgh": True})
    thread = threading.Thread(target=run_loop)
    thread.start()

  def init_bot(self):
    async def run_bot():
      log.debug("init bot...", extra={"tgh": True})
      self.client = telethon.TelegramClient(self.bot_name, self.api_id,
                                            self.api_hash, loop=self.loop)
      log.debug("starting bot...", extra={"tgh": True})
      await self.client.start(bot_token=self.token)
      self.event_started_bot.set()
      log.debug("bot started.", extra={"tgh": True})

    log.debug("waiting set loop...")
    self.event_set_loop.wait()
    self.loop.create_task(run_bot())

  def init_identify_chat_type(self):
    async def identify_chat_type():
      log.debug("waiting start bot...", extra={"tgh": True})
      await self.event_started_bot.wait()
      log.debug("identify chat type...", extra={"tgh": True})
      entity = await self.client.get_entity(self.chat)
      if not isinstance(entity, telethon.types.User):
        self.chat_type = "{}#{}".format(entity.title, entity.id)
        self.limiter.add_limit(self.chat_type, 20, 60)
      self.event_identified_chat_type.set()
    self.loop.create_task(identify_chat_type())

  def init_process_log(self):
    async def process_log(logger):
      logger.debug("waiting identify chat type...", extra={"tgh": True})
      await self.event_identified_chat_type.wait()
      logger.debug("starting process log...", extra={"tgh": True})
      task: Task = None
      while True:
        try:
          log: str = await self.queue_logs.get()
          if self.chat_type:
            await self.limiter.use_limits("gen", self.chat_type)
          else:
            await self.limiter.use_limit("gen")

          if task is not None and not task.done():
            await task
          cor = self.client.send_message(self.chat, log)
          task = self.loop.create_task(cor)
        finally:
          self.queue_logs.task_done()
    self.loop.create_task(process_log(log))

  def emit(self, record: LogRecord) -> None:
    message = self.format(record)
    self.queue_logs.put_nowait(message)


class QueueHandler(Handler):
  def __init__(self, queue):
    if isinstance(queue, asyncio.Queue):
      self.type_queue = "async"
    else:
      self.type_queue = "sync"
    self.queue = queue
    super().__init__()
  def emit(self, record):
    item = self.format(record)
    #log.debug(f"putting {item=}")
    if self.type_queue == "sync":
      self.queue.put(item)
    else:
      self.queue.put_nowait(item)
