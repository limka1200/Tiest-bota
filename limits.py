import asyncio
import time
import logging

log = logging.getLogger( "MyApp").getChild(__name__) 
log.setLevel(logging.WARNING)


class Sleeper:
  """
  Класс для реализации ограничения скорости в приложениях asyncio.

  :ivar limits: Словарь с информацией об ограничениях скорости для каждого именованного ограничения.
  :type limits: dict

  :ivar cor_lock: Блокировка для синхронизации доступа к проверке.
  :type cor_lock: asyncio.Lock

  :ivar cor_event: Событие для сигнализации о завершении корутины.
  :type cor_event: asyncio.Event
  """

  def __init__(self):
    self.limits = {}
    self.cor_lock = asyncio.Lock()
    self.cor_event = asyncio.Event()

  def add_limit(self,
                name: str,
                rate_limit: int,
                period: float):
    """
    Добавляет новое ограничение скорости в словарь `limits`.

    :param name: Имя ограничения скорости.
    :type name: str

    :param rate_limit: Максимальное количество маркеров для ограничения скорости.
    :type rate_limit: int

    :param period: Временной период для ограничения скорости.
    :type period: float

    :return: None
    :rtype: None
    """
    lock = asyncio.Lock()
    event = asyncio.Event()
    t = time.monotonic()
    self.limits[name] = {
      "rate": rate_limit, 
      "period": period, 
      "lock": lock, 
      "event": event,
      "time": t,
      "tokens": rate_limit}

  def update_tokens(self, name) -> float:
    """
    Обновляет количество маркеров для указанного ограничения скорости.

    Аргументы:
      name (str): Имя ограничения скорости.

    Возвращает:
      float: Прошедшее время с момента последнего обновления маркеров.
    """
    limit = self.limits[name]
    current_time = time.monotonic()
    elapsed_time = current_time - limit["time"]
    if elapsed_time >= limit["period"]:
      limit["tokens"] = limit["rate"]
      limit["time"] = time.monotonic()
      log.info("'{}' >> обновлены маркеры ({})".format(name, self.limits[name]["tokens"]))
    return elapsed_time

  def consume_token(self, name) -> int:
    """
    Использует маркер для указанного ограничения скорости.

    Аргументы:
      name (str): Имя ограничения скорости.

    Возвращает:
      int: Оставшееся количество маркеров для ограничения скорости.
    """
    self.update_tokens(name)
    self.limits[name]["tokens"] -= 1
    tokens = self.limits[name]["tokens"]
    if tokens < 0:
      log.critical("'{}' >> не имеет маркеров ({}) < 0".format(name, tokens))
    else:
      log.info("'{}' >> имеет {} маркеров".format(name, tokens))
    return tokens

  def calculate_delay(self, name):
    """
    Вычисляет время задержки для указанного ограничения скорости.

    Аргументы:
      name (str): Имя ограничения скорости.

    Возвращает:
      float: Время задержки для ограничения скорости или 0, если задержка не требуется.
    """
    elapsed_time = self.update_tokens(name)
    if self.limits[name]["tokens"] == 0:
      sleep_time = self.limits[name]["period"] - elapsed_time
      return sleep_time
    return 0

  def unlock(self, name):
    """
    Разблокирует указанное ограничение скорости.

    Аргументы:
      name (str): Имя ограничения скорости.

    Возвращает:
      None
    """
    lock = self.limits[name]["lock"]
    lock.release()
    self.cor_event.set()
    log.debug("'{}' >> разблокировано".format(name))

  async def lock(self, name):
    """
    Блокирует указанное ограничение скорости.

    Аргументы:
      name (str): Имя ограничения скорости.

    Возвращает:
      None
    """
    lock = self.limits[name]["lock"]
    await lock.acquire()
    log.debug("'{}' >> заблокировано".format(name))

  async def use_limit(self, name):
    """
    Использует одно ограничение скорости.

    :param name: Имя ограничения скорости.
    :type name: str

    :return: None
    :rtype: None
    """
    await self.lock(name)
    delay = self.calculate_delay(name)
    if delay:
      log.info("'{}' >> задержка {} секунд".format(name, delay))
      await asyncio.sleep(delay)
    self.consume_token(name)
    self.unlock(name)

  async def use_limits(self, *names):
    """
    Использует несколько ограничений скорости.

    Аргументы:
      *names (str): Имена ограничений скорости.

    Возвращает:
      None
    """
    coroutines = [self.lock(name) for name in names]
    while True:
      await self.cor_lock.acquire()
      self.cor_event.clear()
      if all(not self.limits[name]["lock"].locked() for name in names):
        break
      else:
        self.cor_lock.release()
        await self.cor_event.wait()
    await asyncio.gather(*coroutines)
    self.cor_lock.release()

    updated_name = None
    free_names = []
    last_delay = 0
    max_delay = 0
    for name in names:
      delay = self.calculate_delay(name)
      if delay:
        if delay > last_delay:
          updated_name = name
          max_delay = delay
        last_delay = delay
      else:
        free_names.append(name)
    if max_delay:
      for name in free_names:
        self.unlock(name)
      log.info("'{}' >> задержка {} секунд".format(updated_name, max_delay))
      await asyncio.sleep(max_delay)
      log.debug("'{}' >> задержка завершена".format(updated_name))
      for name in names:
        self.consume_token(name)
      self.unlock(updated_name)
    else:
      for name in names:
        self.consume_token(name)
        self.unlock(name)