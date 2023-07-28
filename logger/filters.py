from logging import Filter


class MyFilter(Filter):
  '''Фильтр предназначен для консоли, чтобы выводились сообщения моих логгеров.'''
  def __init__(self, logger_name):
    super().__init__()
    self.logger_name = logger_name
  def filter(self, record):
    return record.name.startswith( self.logger_name)

class ExtraFilter(Filter):
  '''Фильтр не пропускает сообщения с определенным параметром'''
  def __init__(self, param):
    super().__init__()
    self.param = param
  def filter(self, record):
    return getattr(record, self.param, True)
    
class FilterModule(Filter):
  '''Фильтр предназначен чтобы исключить логгирование определенного модуля.'''
  def __init__(self, module_name):
    super().__init__()
    self.module_name = module_name
  def filter(self, record):
    return record.module != self.module_name

class levelFilter(Filter):
  def __init__(self, level):
    super().__init__()
    self.level = level
  def filter(self, record):
    return record.levelno == self.level


class MinLevelFilter(Filter):
    def __init__(self, min_level):
        super().__init__()
        self.min_level = min_level

    def filter(self, record):
        return record.levelno >= self.min_level