import asyncio
import threading
import textwrap
import queue
import telethon
from limits import Sleeper
from logging import Handler, LogRecord
from asyncio import AbstractEventLoop


class TelegramBotHandlerV2(Handler):
  def __init__(self, chat_id, max_length=4096):
    super().__init__()
    self.chat_id = chat_id
    self.max_length = max_length
    self.queue = queue.Queue()
    threading.Thread( target=self._worker).start()
    self.event_start = threading.Event()
    self.limiter = Sleeper()
    self.limiter.add_limit( "gen", 30, 1) 
    self.chat_type = None
    self.task = None
    
  def _set_chat_type(self,chat_id):
    async def aset_chat_type(chat_id):
      await self.limiter.use_limit( "gen")
      entity = await self.bot.get_entity(chat_id)
      if not entity.is_private:
        self.chat_type = "{}#{}".format(entity.title, entity.id)
        self.limiter.add_limit( self.chat_type, 20, 60)
      else:
        self.chat_type = "gen"
      self.task = False
    self.task = self.bot.loop.create_task( aset_chat_type(chat_id))
    
  def start(self, bot):
    self._set_chat_type(self.chat_id)
    self.bot = bot 
    self.event_start.set()
    
    
  
  def emit(self, record):
    log_entry = self.format(record)
    for chunk in textwrap.wrap( log_entry, width=self.max_length):
      self.queue.put(chunk)
      
  async def _send_msg(self, chat, msg):
    if self.task:
      await self.task
    await self.limiter.use_limit( "gen")
    if self.chat_type != "gen":
      await self.limiter.use_limit( self.chat_type)
    await self.bot.send_message( chat, msg)
    
  @staticmethod  
  def _worker(event, bot, queue, id):
    event.wait()
    while True:
      message = queue.get()
      bot.loop.create_task( self._send_msg(id, message))


class TelegramBotHandlerV3(Handler):
  def __init__(self, bot_name, api_id, api_hash, token, chat, loop: AbstractEventLoop = None):
    super().__init__()
    self.loop = loop
    if loop is None:
      self.set_loop()
    self.token = token
    self.chat = chat
    self.api_hash = api_hash
    self.api_id = api_id
    self.bot_name = bot_name
    self.client: telethon.TelegramClient = None
    self.init_bot()
    self.chat_type = ""
    self.identify_chat_type()
    self.limiter = Sleeper()
    self.limiter.add_limit("gen", 30, 1)

  def afunc_to_result(self, afunc, *args, **kwargs):
    event_task = threading.Event()
    async def wrap_func_to_cor():
      #print(f"wrapped {afunc}")
      result = await afunc(*args, **kwargs)
      #print("got result in wrap")
      return result
    def callback(future):
      event_task.set()
    cor = wrap_func_to_cor()
    #print(f"{cor=}")
    #print(f"{self.loop=}")
    task = self.loop.create_task(cor)
    task.add_done_callback(callback)
    #print("waiting callback")
    event_task.wait()
    event_task.clear()
    return task.result()

  def init_bot(self):
    self.client = telethon.TelegramClient(self.bot_name, self.api_id,
                                          self.api_hash, loop=self.loop)
    #print("bot is starting...")
    self.afunc_to_result(self.client.start, bot_token=self.token)
    me = self.afunc_to_result(self.client.get_me)
    #print("bot status: " + str(bool(me)))

  def identify_chat_type(self):
    entity = self.afunc_to_result(self.client.get_entity, self.chat)
    if not isinstance(entity, telethon.types.User):
      self.chat_type = "{}#{}".format(entity.title, entity.id)
      self.limiter.add_limit(self.chat_type, 20, 60)

  def emit(self, record: LogRecord) -> None:
    message = self.format(record)
    """
    Ты вернёшься к этому:
    task = None
    while True:
      try:
        log = await queue_log.get()
        if chat_type:
          await limiter.use_limits("gen", chat_type)
        else:
          await limiter.use_limit("gen")
  
        if task is not None and not task.done():
          await task
        cor = bot.send_message(chat, log)
        task = asyncio.create_task(cor)
      finally:
        queue_log.task_done()
    """
    if self.chat_type:
      self.afunc_to_result(self.limiter.use_limits, "gen", self.chat_type)
    else:
      self.afunc_to_result(self.limiter.use_limit, "gen")
    self.afunc_to_result(self.client.send_message, self.chat, message)

  def set_loop(self):
    event = threading.Event()
    def run_loop(ev: threading.Event):
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      self.loop = loop
      ev.set()
      loop.run_forever()
    thread = threading.Thread(target=run_loop, args=(event,))
    thread.start()
    async def ping_loop():
      #print('pong loop')
      while True:
        await asyncio.sleep(1/20)
    event.wait()
    self.loop.create_task(ping_loop())


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
