# -*- coding: utf-8 -*-
# Механизм сессий

import os, os.path, time, sys
import random, md5, pickle
import logging

class StorageFile:
	""" Хранилище сессий в файлах """
	def __init__(self,path):
		self.path = path

	def load(self,session):
		# проверить наличие сессии и извлечь метаданные
		filename = self.path + "/" + str(session.sid)
		if  os.path.exists( filename ):
			if os.path.getmtime( filename ) + session.session_lifetime > time.time():
				try:
					sfp = open( filename, 'r')
					session.data = pickle.load(sfp)
					sfp.close()
				except:
					logging.error("Error reading session file %s: %s", filename, sys.exc_value)
					return False
				return True
			else:
				logging.debug("file %s expired", filename)
				# удалить файл сессии
				os.unlink(filename)
				self.purge(session.session_lifetime)
		return False

	def purge(self, session_lifetime):
		for item in os.listdir(self.path):
			filename = self.path + "/" + str(item)
			# обернуть в try для предотвращения ошибок множественного доступа
			try:
				if os.path.getmtime( filename ) + session_lifetime < time.time():
					logging.debug("file %s expired", filename)
					# удалить файл сессии
					os.unlink(filename)
			except:
				pass

	def store(self,session):
		# проапдейтить данные
		filename = self.path + "/" + str(session.sid)
		if session.data:
			try:
				sfp = open( filename, 'w+')
				pickle.dump(session.data, sfp)
				sfp.close()
			except:
				logging.error("Error writing session file %s: %s", filename, sys.exc_value)
				return False
		return True

	def erase(self,session):
		# удалить сессию
		filename = self.path + "/" + str(session.sid)
		if os.path.exists( filename ):
			os.unlink( filename )
			session.data = {}

class Session:
	""" Сессия пользователя """
	def __init__(self, environ, cookie_in, cookie_out, session_storage, session_lifetime=3600):
	    	""" Инициализация объекта сессий
		cookie_in - Коллекция объектов Morsel . Входящие печеньки.
		cookie_out - Коллекция объектов Morsel . Исходящие печеньки.
		session_storage - Объект хранения сессий
		session_lifetime - Integer. Время жизни сессии в секундах.
		"""
		self.environ = environ
		self.cookie_in = cookie_in
		self.cookie_out = cookie_out
		self.storage = session_storage
		self.session_lifetime = session_lifetime
		self.data = {}
		self.sid = ""
		self.start()

	def start(self):
		""" Создание сессии """
		# вычислить контрольную сумму для предотвращения кражи сессий
		control=md5.md5(self.environ.get("REMOTE_ADDR","localhost")+self.environ.get("HTTP_USER_AGENT","UNKNOWN")).hexdigest()
		# если есть кука с сессией, попытаться загрузить данные
		if self.cookie_in.has_key("PSID"):
			self.sid = self.cookie_in["PSID"].value
			# если не загрузились, то не выставится sid и будет создан по новой
			if self.load_data():
				# если контрольная сумма не совпадает с сохранённой - делаем новую сессию
				if self.data.get("chksum","") != control:
					self.sid = ""
					self.data = {}
			# если не загрузились, то не выставится sid и будет создан по новой
			else:
				self.sid = ""
				self.data = {}
		# создать, если нет sid (или куки нет, или не загрузились данные)
		if not self.sid:
			self.sid = md5.md5(str(int(int(time.time()*100)*1000)+int(random.random()*1000))).hexdigest()
			self.cookie_out["PSID"] = self.sid
			self.cookie_out["PSID"]["path"]="/"
			self.data["chksum"] = control

	def load_data(self):
		""" Загрузка данных сессии """
		if self.sid=="":
			return False
		else:
			return self.storage.load(self)
	
	def store_data(self):
		""" Сохранение данных сессии """
		if self.sid:
			return self.storage.store(self)
		else:
			return False

	def destroy(self):
		""" Удаление сессии """
		self.storage.erase(self)
		self.cookie_out["PSID"] = ""
		self.cookie_out["PSID"]["path"]="/"
		self.cookie_out["PSID"]["expires"]="-3y"
