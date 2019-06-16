# -*- coding: utf-8 -*-
""" Приложение АДМИНКА/ПОЛЬЗОВАТЕЛИ """

import logging,re,sys,md5,time,random
from core import mailtools

def dispatch( env ):
	""" Пользователи """
	data = {
		"path" : env.path.current(),
		"session" : env.session.data,
		"error" : {}
	}
	tmpl = env.jinja.get_template("admin/users.html")
	if not env.path.current():
		if env.req.has_key("name"):
		# проверить, не хотим ли завести нового пользователя
			name = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("name",None).decode('utf8').strip().replace(":","").replace('"',"&quot;"))
			if not name:
				data['error']['name']='empty'
			elif name.__len__()>200:
				data['error']['name']='invalid'
			email = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("email",None).decode('utf8').strip().replace(":","").replace('"',"&quot;"))
			if not email:
				data['error']['email']='empty'
			elif not mailtools.is_email(email):
				data['error']['email']='invalid'
			region_id=env.req.getvalue("region",0)
			region = None
			if not region_id:
				data['error']['region']='invalid'
			else:
				if not env.regions['id'].has_key(int(region_id)):
					data['error']['region']='invalid'
			region = env.regions['id'][int(region_id)]
			if not data['error']:
				sql="""SELECT id FROM `users` WHERE email=%s"""
				c=env.db.equery(sql,(email))
				if c.fetchone():
					data['error']['email']='exist'
				else:
					code=md5.md5(str(time.time())+str(random.random())).hexdigest()
					sql=u"""INSERT INTO `users` (`email`,`name`,`code`,`region_id`) VALUES (%s,%s,%s,%s)"""
					env.db.equery(sql,(email,name,code,region_id))
					subject,text=mailtools.loadMail(env,"mail/new.tpl",{"name":name,"code":code,"email":email,"site":env.environ.get("SERVER_NAME"),'region':region['name']})
					mailtools.sendMail(env,env.conf.email,[name+u"<"+email+u">"],subject,text)
			if data['error']:
				data['name']=name
				data['email']=email
		if env.req.has_key("delete"):
		# удалить пользователя
			user_id=int(env.req.getvalue("userid",0))
			sql="""SELECT * FROM `users` WHERE id=%s"""
			c=env.db.equery(sql,(user_id))
			userinfo=c.fetchone()
			sql="""DELETE FROM `users` WHERE id=%s"""
			env.db.equery(sql,(user_id))
			subject,text=mailtools.loadMail(env,"mail/delete.tpl",{"name":userinfo["name"],"email":userinfo["email"],"site":env.environ.get("SERVER_NAME")})
			mailtools.sendMail(env,env.conf.email,[userinfo["name"]+u"<"+userinfo["email"]+u">"],subject,text)
		if env.req.has_key("up"):
		# сделать администратором
			user_id=int(env.req.getvalue("userid",0))
			sql="""UPDATE `users` SET `priv`=%s WHERE id=%s"""
			env.db.equery(sql,(1,user_id))
		if env.req.has_key("down"):
		# сделать редактором
			user_id=int(env.req.getvalue("userid",0))
			sql="""UPDATE `users` SET `priv`=%s WHERE id=%s"""
			env.db.equery(sql,(0,user_id))
		if env.req.has_key("lock"):
		# заблокировать
			user_id=int(env.req.getvalue("userid",0))
			sql="""UPDATE `users` SET `lock`=%s, code=NULL, password=%s WHERE id=%s"""
			env.db.equery(sql,(1,"*",user_id))
			sql="""SELECT * FROM `users` WHERE id=%s"""
			c=env.db.equery(sql,(user_id))
			userinfo=c.fetchone()
			subject,text=mailtools.loadMail(env,"mail/lock.tpl",{"name":userinfo["name"],"email":userinfo["email"],"site":env.environ.get("SERVER_NAME")})
			mailtools.sendMail(env,env.conf.email,[userinfo["name"]+u"<"+userinfo["email"]+u">"],subject,text)
		if env.req.has_key("unlock"):
		# разблокировать
			user_id=int(env.req.getvalue("userid",0))
			sql="""UPDATE `users` SET `lock`=%s, code=NULL, password=%s WHERE id=%s"""
			env.db.equery(sql,(0,"*",user_id))
			sql="""SELECT * FROM `users` WHERE id=%s"""
			c=env.db.equery(sql,(user_id))
			userinfo=c.fetchone()
			subject,text=mailtools.loadMail(env,"mail/unlock.tpl",{"name":userinfo["name"],"email":userinfo["email"],"site":env.environ.get("SERVER_NAME")})
			mailtools.sendMail(env,env.conf.email,[userinfo["name"]+u"<"+userinfo["email"]+u">"],subject,text)
		if env.req.has_key("reset"):
		# сбить пароль
			user_id=int(env.req.getvalue("userid",0))
			sql="""UPDATE `users` SET `password`=%s, code=NULL WHERE id=%s"""
			env.db.equery(sql,("*",user_id))
		else:
			pass
		data['users']=[]
		sql="""SELECT *  FROM `users`"""
		c=env.db.equery(sql)
		line=c.fetchone()
		while (line):
			if line["priv"]==0:
				line["region"]=env.regions['id'][line['region_id']]['name']
			data['users'].append(line)
			line=c.fetchone()
		data['regions']=env.regions['regions']
		content = tmpl.render( data )
	else:
		content = tmpl.render( data )
	return content
