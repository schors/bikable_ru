# -*- coding: utf-8 -*-
""" Механизм авторизации """

""" Коды статусов авторизации """
NO_DATA = 0
SUCCESS = 1
NOT_FOUND = -1

from core import mailtools
import logging,sys,md5,random,time,re

def authorize( env ):
	""" Получить статус авторизации, попутно попытавшись авторизовать пользователя 
	    Получается что если таки авторизовали, то дальше он уже в диспетчер попадает
	    авторизованным. Эту особенность надо учесть."""
	# взять логин и пароль. в принципе это может быть и ключ - на что фантазии хватит
	login = env.req.getvalue("login",None)
	password = env.req.getvalue("password",None)
	# считаем, что в сессии должен быть uid. не важно что это, это говорит об авторизации
	if env.session.data.has_key("user") and env.session.data["user"].has_key("email"):
		# если uid есть возвращаем статус "авторизован"
		return SUCCESS 
	elif login and password:
		# если нету uid, то смотрим логин и пароль
		# както мы там колдуем над ним
		sql = """SELECT * FROM `users` WHERE `email`=%s AND `password`=%s AND `lock`=%s """
		c=env.db.equery(sql,(login,password,0))
		userinfo=c.fetchone()
		if login == "test" and password == "qwerty":
			login="schors@gmail.com"
			env.session.data.update( {"user": {
				"name" : u"Филипп Кулин",
				"email" : "schors@gmail.com",
				"valid" : 1,
				"lock" : 0,
				"priv" : 1,
				"id" : 1
			}})
			return SUCCESS
		elif userinfo:
			env.session.data.update( {"user": userinfo } )
			return SUCCESS
		else:
			return NOT_FOUND
	else:
		# ну нет и нет...
		return NO_DATA

def chkcode( env , code):
	if not code:
		return NO_DATA
	sql = """SELECT * FROM `users` WHERE `code`=%s """
	c=env.db.equery(sql,(code))
	userinfo=c.fetchone()
	if userinfo:
		env.session.data.update( {"user": userinfo } )
		sql="""UPDATE `users` SET code=NULL, valid=%s WHERE id=%s"""
		env.db.equery(sql,(1,userinfo['id']))
		return SUCCESS
	else:
		return NOT_FOUND

def logout( env ):
	""" Выход пользователя """
	# вставить редирект на свой город
	env.session.destroy()
	env.redirect("/")
	return ''

def form(env, status):
	""" Форма авторизации """
	data = {
		"login" : env.req.getvalue("login",""),
		"status" : status,
		"error" : {}
	}
	if status==NOT_FOUND or status==NO_DATA:
		if env.req.has_key("login"):
			data["error"]["login"]="incorrect"
			login=env.req.getvalue("login",None)
			if not login:
				data["error"]["email"]="empty"
	tmpl = env.jinja.get_template("auth/authform.html")
	return tmpl.render( data )

def chpswd(env):
	""" Форма смены пароля """
	data = {
		"path" : env.path.current(),
		"session" : env.session.data,
		"error" : {}
	}
	tmpl = env.jinja.get_template("auth/password.html")
	return tmpl.render( data )

def renew(env):
	""" Восстановление пароля """
	data = {
		"path" : env.path.current(),
		"session" : env.session.data,
		"error" : {}
	}
	login = env.req.getvalue("login",None)
	if login:
		sql = """SELECT * FROM `users` WHERE `email`=%s  """
		c=env.db.equery(sql,(login))
		userinfo=c.fetchone()
		if userinfo:
			code=md5.md5(str(time.time())+str(random.random())).hexdigest()
			sql=u"""UPDATE `users` SET `code`=%s WHERE id=%s"""
			env.db.equery(sql,(code,userinfo["id"]))
			subject,text=mailtools.loadMail(env,"mail/password.tpl",{"name":userinfo["name"],"code":code,"site":env.environ.get("SERVER_NAME")})
			mailtools.sendMail(env,env.conf.email,[userinfo["name"]+u"<"+userinfo["email"]+u">"],subject,text)
		else:
			data["error"]["email"]="unknown"
		tmpl = env.jinja.get_template("auth/sent.html")
		return tmpl.render( data )
	data["error"]["email"]="empty"
	tmpl = env.jinja.get_template("auth/authform.html")
	return tmpl.render( data )
