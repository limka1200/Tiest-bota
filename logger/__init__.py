import logging
from .handlers import QueueHandler, TelegramBotHandlerV2
from .filters import MyFilter, ExtraFilter, levelFilter, FilterModule
from .formatters import MyFormatter

name_log = "MyApp"

def active_file_handler( level=logging.INFO):
  fh = logging.FileHandler("logs.txt")
  fh.setLevel(level)
  fh.addFilter(ExtraFilter("fh"))
  logging.getLogger( name_log).addHandler(fh) 

def active_queue_handler(queue):
  log = logging.getLogger(name_log)
  
  qh_info = QueueHandler(queue)
  qh_info.addFilter(ExtraFilter("qh"))
  info_filter = levelFilter( logging.INFO)
  qh_info.addFilter(info_filter)
  qh_info.setLevel(logging.INFO)
  formatter = MyFormatter('<p class="log_info">[{asctime}] [{levelname}] {importMod}: <b>{message}</b></p>',
                          datefmt="%d.%m.%Y %H:%M:%S", style='{',
                          no_color=True)
  qh_info.setFormatter(formatter)
  log.addHandler(qh_info)
  
  qh_warn = QueueHandler(queue)
  qh_warn.addFilter(ExtraFilter("qh"))
  warn_filter = levelFilter( logging.WARNING)
  qh_warn.addFilter(warn_filter)
  qh_warn.setLevel(logging.WARNING)
  formatter = MyFormatter('<p class="log_warn">[{asctime}] [{levelname}] {importMod}: <b>{message}</b></p>',
                          datefmt="%d.%m.%Y %H:%M:%S", style='{',
                          no_color=True)
  qh_warn.setFormatter(formatter)
  log.addHandler(qh_warn)
  
  qh_err = QueueHandler(queue)
  qh_err.addFilter(ExtraFilter("qh"))
  error_filter = logging.Filter()
  error_filter.filter = lambda record: record.levelno >= logging.ERROR
  qh_err.addFilter(error_filter)
  qh_err.setLevel(logging.ERROR)
  formatter = MyFormatter('<p class="log_error">[{asctime}] [{levelname}] {importMod}: <b>{message}</b></p>',
                          datefmt="%d.%m.%Y %H:%M:%S", style='{', no_color=True)
  qh_err.setFormatter(formatter)
  log.addHandler(qh_err)


def active_telegram_handler(chat, level=logging.INFO):
  log = logging.getLogger(name_log)
  tgh = TelegramBotHandlerV2(chat)
  tgh.setLevel(level)
  tgh.addFilter( FilterModule("logger.handlers"))
  tgh.addFilter(ExtraFilter("tgh"))
  formatter = MyFormatter( "```[{levelname}] {importMod}:``` **{message}**", style='{', no_color=True)
  tgh.setFormatter(formatter)
  log.addHandler(tgh)
  return tgh

def active_telegram_handler2(queue, level=logging.INFO):
  log = logging.getLogger(name_log)
  tgh = QueueHandler(queue)
  tgh.setLevel(level)
  tgh.addFilter( FilterModule("logger.handlers"))
  tgh.addFilter(ExtraFilter("tgh"))
  formatter = MyFormatter( "```[{levelname}] {importMod}:``` **{message}**", style='{', no_color=True)
  tgh.setFormatter(formatter)
  log.addHandler(tgh)
  return tgh 

def init(name="", level_console=logging.DEBUG, level_log=logging.DEBUG):
  global name_log
  if not name:
    name = name_log
  else:
    name_log = name
  logger = logging.getLogger(name)
  handler = logging.StreamHandler()
  handler.addFilter(MyFilter(name))
  handler.setLevel(level_console)
  formatter = MyFormatter('%(log_color)s [%(levelname)s] %(importMod)s: \033[1m%(message)s\033[0m',log_colors={
        'DEBUG': 'white',
        'INFO': 'blue',
        'WARNING': 'red',
        'ERROR': 'red',
        'CRITICAL': 'red,bold',
})
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.setLevel(level_log)

def get_logger(name):
  return logging.getLogger( "MyApp").getChild(name)
