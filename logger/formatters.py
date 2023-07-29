import pytz
import inspect
import threading
import textwrap
import sys
from datetime import datetime 
from colorlog import ColoredFormatter


class MyFormatter(ColoredFormatter):
  def __init__(self, fmt=None, datefmt=None, style='%', no_color=False, log_colors=None,
               tz=pytz.timezone("Europe/Moscow")):
    super().__init__(fmt=fmt, datefmt=datefmt, style=style, log_colors=log_colors)
    self.noColor = no_color
    self.tz = tz
    
  def converter(self, timestamp):
    dt = datetime.fromtimestamp( timestamp, pytz.utc)
    dt = dt.astimezone(self.tz)
    return dt.timetuple()
    
  def format(self, record):
    # Получаем имя модуля, в который была импортирована функция
    info = {"num":0}
    def proc(frame):
      nonlocal info
      info["num"]+=1
      modln = inspect.getmodule( frame).__name__.replace("_","") if inspect.getmodule(frame) else "unknown"
      func = frame.f_code.co_name if not frame.f_code.co_name == "<module>" else "root"
      info.setdefault("modl",{}).setdefault(modln,[]).append(func)
    nxt=0
    for frame, _, _, _, _, _ in inspect.stack():
      if nxt != 2:
        nxt+=1
        continue
      proc(frame)
    info["cur"]={"mark":True, "modl":""}
    info["cal"]={"mark":True, "modl":""}
    for key,value in info["modl"].items():
      def check_module_in_same_package(module_name):
        try:
          if module_name != "logging" and module_name != "unknown":
            if module_name in sys.modules:
              module = sys.modules[module_name]
              return __package__ != getattr(module, '__package__')
            else:
              return True
        except (ModuleNotFoundError, AttributeError):
          return True
        return False
      if check_module_in_same_package(key):
        if info["cur"]["mark"]:
          info["cur"]["mark"] = False
          info["cur"]["modl"] = {key:value[0]}
          if "root" in value:
            info["cal"]["modl"]=key
            info["cal"]["mark"]=False
        else:
          if info["cal"]["mark"]:
            info["cal"]["mark"]=False
            info["cal"]["modl"]=key
        #print(key, value)
    for key,value in info["cur"]["modl"].items():
      record.curretMod, record.curretFunc = key, value
    record.callerMod=info["cal"]["modl"]
    if record.curretMod == record.callerMod or record.callerMod == "":
      record.importMod = record.curretMod
    else:
      record.importMod = record.curretMod+" » "+record.callerMod
    if record.curretFunc != "root":
      record.importMod ="< " +record.importMod+" > "+record.curretFunc+"()"
    #print("result: "+record.importMod)
    # getting name of Thread
    th=threading.current_thread()
    record.thread = th.name
    msg = super().format(record)
    if self.noColor:
      msg = msg[:-4]
    if record.levelname != "ERROR":
      msg = textwrap.TextWrapper( width=43).fill(msg)  
    #print(f"{msg=}")
    return msg