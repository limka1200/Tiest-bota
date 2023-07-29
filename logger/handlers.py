import asyncio
import threading
import textwrap
import queue
from limits import Sleeper
from logging import Handler


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
