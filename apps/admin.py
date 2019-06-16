# -*- coding: utf-8 -*-
""" Приложение АДМИНКА """

from core import auth
from apps import users,tpl,regions,arch
import logging,sys,re

def dispatch( env ):
	""" Админка """
	content=''
	auth_status = auth.authorize(env)
	if auth_status == auth.SUCCESS:
		data = {
			"path" : env.path.current(),
			"session" : env.session.data,
			"error" : {}
		}
		# авторизован
		if env.path.current() == "l":
		# если хочет выйти - выгнать :)
			content = auth.logout( env )
		elif env.path.current() == "u" and env.session.data['user']['priv']==1:
		# пользователи
			env.path.next()
			content=users.dispatch(env)
		elif env.path.current() == "t":
		# шаблоны
			env.path.next()
			content = tpl.dispatch( env )
		elif env.path.current() == "a":
		# архив
			env.path.next()
			content = arch.dispatch( env )
		elif env.path.current() == "images":
		# картинки архива
			env.path.next()
			img='/arch/'+'/'.join(env.path.pathparts[env.path.pointer:])
			logging.debug("Image: %s" % img)
			env.iredirect(img)
		elif env.path.current() == "r" and env.session.data['user']['priv']==1:
		# города
			env.path.next()
			content = regions.dispatch( env )
		else:
			tmpl = env.jinja.get_template("admin/index.html")
			if env.req.has_key("save"):
				password=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("password",None).decode('utf8').strip())
				password2=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("password2",None).decode('utf8').strip())
				if password and password==password2:
					sql="""UPDATE `users` SET password=%s WHERE id=%s"""
					env.db.equery(sql,(password,env.session.data["user"]["id"]))
					data["error"]["password"]="success"
					content = tmpl.render( data )
				else:
					data["error"]["password"]="missmatch"
					content = tmpl.render( data )
			else:
				content = tmpl.render( data )
	else:
		# не авторизован
		if env.path.current() == "c":
			code=env.path.next()
			auth_status = auth.chkcode(env,code)
			if auth_status == auth.SUCCESS:
				# нарисовать форму смены пароля
				content = auth.chpswd( env )
		elif env.req.has_key("lost"):
			content = auth.renew(env)
		else:
			# нарисовать форму авторизации
			content = auth.form( env, auth_status )
	return content
