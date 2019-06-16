# -*- coding: utf-8 -*-
# Ответка для WSGI 

import sys, os, cgi, Cookie, traceback, logging, pickle
from core import dispatcher, session
from core import mysql
import jinja2

application_loglevel = os.environ.get("LOGLEVEL","debug")
if application_loglevel == "error":
	logging.basicConfig(level=logging.ERROR)
elif application_loglevel == "critical":
	logging.basicConfig(level=logging.CRITICAL)
elif application_loglevel == "warning":
	logging.basicConfig(level=logging.WARNING)
elif application_loglevel == "info":
	logging.basicConfig(level=logging.INFO)
else:
	logging.basicConfig(level=logging.DEBUG)

class Responder:
	""" WSGI-коннектор """
	def __init__(self):
		""" Разовые действия при загрузке приложения """
		self.weblog = os.environ.get("WEBLOG","YES")
		try:
			__import__("conf.%s" % os.environ["APPLICATION_CONFIG"])
			self.config = sys.modules["conf.%s" % os.environ["APPLICATION_CONFIG"]]
			self.config.base_path = os.environ["BASE_DIR"]
			self.config_error = None
		except:
			self.config = None
			self.config_error = 'Could not load config %s:\n%s' % (os.environ["APPLICATION_CONFIG"],traceback.format_exc())
			logging.critical(self.config_error)
		else:
			# создать журналы
			pass

	def __call__(self, environ, start_response):
		""" Обработка запросов """
		try:
			# рубануть если не было конфига
			if self.config_error:
				raise NameError(self.config_error)
			# заполнить всё окружение
			application_environment = AppEnv( environ=environ, conf=self.config )
			# отправить диспетчеру
			response = dispatcher.dispatch( application_environment )
			# завершить всё
			application_environment.finalize()
			# отправить заголовки
			start_response( application_environment.return_code, application_environment.headers)
			# вернуть текст
			return [response.encode("utf-8")]
		except:
			# отправить заголовки
			start_response("500 Internal server error", [("Content-type","text/plain")])
			# взять информацию об ошибке
			exc_type, exc_value, exc_traceback = sys.exc_info()
			result=traceback.format_exception(exc_type, exc_value, exc_traceback)
			# зарисовать в лог
			logging.critical("".join(result))
			# вернуть наружу если сказано
			if self.weblog == "YES":
				return result
			else:
				return []

class AppEnv:
	"""  Объект Окружение. Передается на всем протяжении обработки запроса.
	     Содержит некоторые глобальные сущности ( шаблонизатор, хэндлер к базе, конфиг, 
	     сессию пользователя, данные запроса )
	     Умеет сам подхватывать и создавать сессию. """
	def __init__(self, environ=None, conf=None):
		# конфиг из конфигурационного файла
		self.path = self.req = self.session = self.environ = self.db = None
		self.conf = conf
		# входящие и исходящие печеньки
		self.cookie_in = Cookie.SimpleCookie()
		self.cookie_out = Cookie.SimpleCookie()
		# шаблонизатор
		self.jinja = jinja2.Environment(loader=jinja2.FileSystemLoader(self.conf.base_path+self.conf.template_path, 'utf-8'))
		# подключение MySQL, сюда можно что угодно вставить
		if self.conf.db_name and self.conf.db_user:
			self.db = mysql.AdvancedConnection(host=self.conf.db_host, user=self.conf.db_user, passwd=self.conf.db_passwd, db=self.conf.db_name )
		# код ответа
		self.return_code = "200 OK" 
		# коллекция заголовков
		self.headers = [("Content-type", "text/html; charset=utf-8")]
		if environ:
			self.environ = environ
			# разбрать QUERY_STRING
			if self.environ.has_key("wsgi.input"):
				self.req = cgi.FieldStorage(fp=self.environ["wsgi.input"], environ=self.environ, keep_blank_values=True)
			# разобрать PATH_INFO
			if self.environ.has_key("PATH_INFO"):
				self.path = webpath( self.environ["PATH_INFO"] )
			# подхватить печеньки
			if self.environ.has_key("HTTP_COOKIE"):
				self.cookie_in.load(self.environ["HTTP_COOKIE"])
			# создать сессию
			self.session = session.Session( self.environ, self.cookie_in, self.cookie_out, session.StorageFile(self.conf.base_path+self.conf.session_storage),self.conf.session_lifetime)
#			self.session = session.Session( self.environ, self.cookie_in, self.cookie_out, mysql.StorageMySQL(self.db),self.conf.session_lifetime)
		self.regions={ 'regions':{}, 'id':{} }
		filename=self.conf.base_path+self.conf.region_conf+"/.regions_db"
		try:
			with open( filename, 'r') as f:
				self.regions=pickle.load(f)
				f.close()
		except:
			# ничего не делать при остуствии базы
			pass

	def set_return_code(self, code):
		self.return_code = code

	def set_header(self, header, value):
		self.headers.append( (header,value) )

	def set_cookie(self, name, value, expire="+1h", path="/", domain=""):
		pass

	def finalize(self):
		""" Завершение запрос """
		# закрыть сессию
		if self.session:
			self.session.store_data()
		# печеньки на выход
		if self.cookie_out:
			for c in self.cookie_out.keys():
				self.headers.append( ("Set-cookie", self.cookie_out[c].output(header = "")) )
		if self.db:
			self.db.close()

	def redirect(self, where, code=302):
		""" Обертка для HTTP-редиректа """
		self.set_return_code("302 Found")
		self.set_header("Location", where)

	def iredirect(self, where):
		""" Обертка для X-Accel-Redirect """
		self.set_return_code("200 OK")
		self.set_header("X-Accel-Redirect", where)

class webpath:
	""" Служит для разбора и обработки пути, полученного из URL """
	def __init__(self, pathstring):
		try:
			# отсечь QUERY_STRING, если он есть
			qpos = pathstring.find("?")
			if qpos != -1:
				pathstring = pathstring[0:qpos]
			# "разбить"путь по слешам
			self.pathparts = pathstring.split("/")
			self.pointer = 0
		except:
			return None
		try:
			while 1: self.pathparts.remove('')
		except:
			pass

	def current(self):
		""" Текущий элемент пути """
		try:
			return self.pathparts[self.pointer]
		except:
			return False

	def next(self):
		""" Перейти к следующему элементу пути """
		self.pointer+=1
		return self.current()
