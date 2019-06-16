# -*- coding: utf-8 -*-
""" Обертка для класса MySQLdb.connection.
    Служит для упрощения рутинных операций с базой """

from MySQLdb import connections, escape_string
import MySQLdb.cursors, pickle, logging, time, sys

class AdvancedConnection(connections.Connection):

	def __init__(self, host=None, user=None, passwd=None, db=None):
		super(AdvancedConnection,self).__init__(host=host, user=user, passwd=passwd, db=db, cursorclass=MySQLdb.cursors.DictCursor, charset="UTF8", use_unicode = True )

	def equery(self, *args, **kwargs):
		""" Выполняет запрос в одно действие. Возвращает курсор """
		cursor = self.cursor()
		cursor.execute(*args, **kwargs)
		return cursor

	def insert(self, table, data):
		""" Выполняет INSERT в таблицу table, используя 
		    в качестве имен полей ключи словаря data """
		fields_name = []
		fields_value = []
		for k,v in data.items():
			fields_name.append("`%s`" % str(k))
			fields_value.append("'%s'" % escape_string(str(v)))
		query = "INSERT INTO `%s` (%s) values (%s)" % (table, ",".join(fields_name), ",".join(fields_value))
		self.query(query)

	def update(self, table, data, where_clause=""):
		""" Выполняет UPDATE в таблице table, используя 
		    в качестве имен полей ключи словаря data. Условие WHERE может быть задано в where_clause.
		    Expl: update("sometable", update_data, "`MyKey` = 31337") """
		fields_list = []
		for k,v in data.items():
			fields_list.append("`%s` = '%s'" % (str(k), escape_string(str(v))))
		if where_clause:
			where_clause = "WHERE %s" % where_clause
		query = "UPDATE `%s` SET %s %s" % (table, ", ".join(fields_list), where_clause)
		self.query(query)


class StorageMySQL:
	"""Хранилище сессий в MySQL"""
	def __init__(self,connection):
		# проверить наличие таблицы и пересоздать её если нет
		sql="""CREATE TABLE IF NOT EXISTS `session` (
			`uniq` VARCHAR( 32 ) NOT NULL,                  -- уникальный идентификатор сессии
			`mtime` TIMESTAMP,                              -- время последнего обновления
			`data` VARCHAR(1024),                           -- данные
			UNIQUE (`uniq`)
			) ENGINE = MEMORY
		"""
		self.connection=connection
		self.cursor=self.connection.cursor()
		self.connection.equery(sql)

	def load(self,session):
		# проверить наличие сессии и извлечь метаданные
		sql="""SELECT `uniq`,UNIX_TIMESTAMP(`mtime`) as mtime,`data` FROM `session` WHERE `uniq` LIKE "%s" """
		c=self.connection.equery(sql,(session.sid))
		data=c.fetchone()
		if data:
			if data['mtime'] + session.session_lifetime > time.time():
				try:
					session.data = pickle.loads(data['data'].decode('string_escape'))
				except:
					logging.error("Error reading session data %s: %s", session.sid, sys.exc_value)
					return False
				return True
			else:
				logging.debug("session %s expired", session.sid)
				sql="""DELETE FROM `session` WHERE `uniq` LIKE "%s" """
				self.connection.equery(sql,(session.sid))
				self.purge(session.session_lifetime)
		return False

	def purge(self, session_lifetime):
		sql="""SELECT `uniq` FROM `session` WHERE `mtime`+ %s < %s """ % (session_lifetime,time.time())
		c=self.connection.equery(sql)
		sid=c.fetchone()
		while sid is not None:
			logging.debug("file %s expired", filename)
			# удалить сессию
			sql="""DELETE FROM `session` WHERE `uniq` LIKE "%s" """
			c=self.connection.equery(sql,(sid))
			sid=c.fetchone()

	def store(self,session):
		# проапдейтить данные
		sfp=pickle.dumps(session.data)
		sql="""REPLACE `session` SET `mtime`=NOW(),data="%s",`uniq`="%s" """
		self.connection.equery(sql,(sfp,session.sid))

	def erase(self,session):
		# удалить сессию
		sql="""DELETE FROM `session` WHERE `uniq` LIKE "%s" """
		self.connection.equery(sql,(session.sid))
		session.data = {}

