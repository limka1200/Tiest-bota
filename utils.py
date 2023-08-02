import hashlib
import os
import asyncio
import logging
import queue
from dataclasses import dataclass

log = logging.getLogger("MyApp").getChild(__name__)


class DataStore():
	def __init__(self, data={}):
		super().__setattr__("_data", data)

	def __getattr__(self, key):
		if key in self._data:
			return self._data[key]

	def __setattr__(self, key, value):
		self._data[key] = value


@dataclass
class ServerSentEvent:
	data: str
	event: str = None
	id: int = None
	retry: int = None

	def encode(self) -> bytes:
		message = f"data: {self.data}"
		if self.event is not None:
			message = f"{message}\nevent: {self.event}"
		if self.id is not None:
			message = f"{message}\nid: {self.id}"
		if self.retry is not None:
			message = f"{message}\nretry: {self.retry}"

		message = f"{message}\n\n"
		return message.encode('utf-8')


class MyQueue(queue.Queue):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.event = asyncio.Event()
		self.single_use = True

	def put(self, item, block=True, timeout=None):
		if self.full():
			self.get()
		super().put(item, block=block, timeout=timeout)
		self.event.set()
		log.debug(f"new {item=} in queue")

	async def get_changed(self) -> "MyQueue.queue":
		if self.single_use:
			self.single_use = False
		else:
			self.event.clear()
			await self.event.wait()
		return self.queue


def generate_cache_buster(*paths, path_static="static"):
	"""
  Генерирует хеш-сумму MD5 для содержимого указанного файла.

	:param paths: Путь(и) к файлу, для которого нужно сгенерировать хеш-сумму. Может быть указано несколько отдельных
								частей пути, которые будут объединены для формирования полного пути.
	:type paths: str

	:param path_static: Относительный или полный путь к каталогу, где находятся файлы. По умолчанию: "static".
	:type path_static: str, optional

	:return: Хеш-сумма MD5 в виде строки, представляющей собой 32-символьный шестнадцатеричный код.
	:rtype: str

	:raises FileNotFoundError: Если указанный файл не найден.
	:raises IOError: Если возникли проблемы при чтении файла.
  """
	path_file = os.path.join(path_static, *paths)
	with open(path_file, "rb") as f:
		content = f.read()
		return hashlib.md5(content).hexdigest()
