# -*- coding: utf-8 -*-
""" Приложение АДМИНКА/АРХИВ """

import logging,re,sys,random,json,os

def dispatch( env ):
	""" Архив """
	data = {
		"path" : env.path.current(),
		"session" : env.session.data,
		"archs" : [],
		"error" : {},
		"regions" : env.regions["regions"],
	}
	content=""
	if not env.path.current():
		if env.session.data['user']["priv"]==1:
			# если админ - сделать редирект на умолчание или ничего
			if env.regions["regions"].has_key("saint-petersburg"):
				env.redirect('/_adm/a/saint-petersburg/')
			else:
				tmpl = env.jinja.get_template("admin/arch.html")
				content = tmpl.render( data )
		else:
			# если координатор - сделать редирект
			region_id=env.session.data['user']['region_id']
			env.redirect('/_adm/a/'+str(env.regions['id'][region_id]['fulluri'])+'/')
	else:
		env.region_current=env.path.current()
		env.path.next()
		# если координатор и не то - сделать редирект
		if env.session.data['user']["priv"]==0:
			region_id=env.session.data['user']['region_id']
			if env.region_current != env.regions['id'][region_id]['fulluri']:
				env.redirect('/_adm/a/'+str(env.regions['id'][region_id]['fulluri'])+'/')
				return ''
		data['cregion'] = env.region_current
		region_id = int(env.regions['regions'][env.region_current]['id'])
		# СЮДА ВСТАВИТЬ ЧТЕНИЕ ШАБЛОНОВ И ВСЯКИЕ ТАМ ФИШКИ ФИЛЬТРОВ

		dirname = env.conf.base_path + env.conf.archive_storage
		# показать выбранный запрос
		if env.path.current()=='v':
			env.path.next()
			aid=env.path.current()
			data["arch"]={}
			sql="""SELECT * FROM `archive` WHERE serial=%s AND region_id=%s"""
			c=env.db.equery(sql,(aid,region_id))
			arch=c.fetchone()
			if arch:
				dirname0=dirname + "/" + str(arch["serial"])[0:2] + "/" + str(arch["serial"])[2:4] + "/" + str(arch["serial"])[4:] 
				try:
					filename = dirname0 + "/data"
					with open(filename) as f:
						arch.update(json.load(f))
						f.close()
					arch["mailtext"]=arch["mailtext"].replace(arch["template"]["fname"],"****").replace(arch["template"]["lname"],"****").replace(arch["template"]["patr"],"****").replace(arch["template"]["email"],"*@***")
				except:
					logging.debug("Cannot open archive: %s",sys.exc_value)
				data["arch"].update(arch)
				data["files"]=[]
				if os.path.exists(dirname0 + "/tumb"):
					files0=os.listdir(dirname0 + "/tumb")
					for f in files0:
						data["files"].append(f)
				sql="""SELECT serial,createdate FROM `archive` WHERE createdate<%s AND region_id=%s ORDER BY createdate DESC LIMIT 0,1"""
				c=env.db.equery(sql,(arch["createdate"],region_id))
				data["prev"]=c.fetchone()
				sql="""SELECT serial,createdate FROM `archive` WHERE createdate>%s AND region_id=%s ORDER BY createdate ASC LIMIT 0,1"""
				c=env.db.equery(sql,(arch["createdate"],region_id))
				data["nxt"]=c.fetchone()
				# logging.debug("%s < %s < %s",data["prev"]["createdate"], data["arch"]["createdate"], data["nxt"]["createdate"])
				tmpl = env.jinja.get_template("admin/arch_view.html")
				content = tmpl.render( data )
			else:
				env.redirect('/_adm/a/'+str(env.region_current)+'/')
				return ''
		# список архива
		else:
			# выдать список
			page=env.path.current()
			if not page:
				page="0"
			astart = int(page) * env.conf.page_records
			# сосчитать всё
			sql="""SELECT COUNT(*) as count FROM `archive` WHERE region_id=%s"""
			c=env.db.equery(sql,(region_id))
			acount=c.fetchone()
			pages = (acount["count"] / env.conf.page_records)
			if (acount["count"] % env.conf.page_records):
				pages+=1
			data["acount"] = acount
			data["pages"] = pages
			data["cpage"] = page
			# взять список
			sql="""SELECT * FROM `archive` WHERE region_id=%s ORDER BY createdate DESC LIMIT %s,%s"""
			c=env.db.equery(sql,(region_id,astart,env.conf.page_records))
			line=c.fetchone()
			while (line):
				try:
					filename = dirname + "/" + str(line["serial"])[0:2] + "/" + str(line["serial"])[2:4] + "/" + str(line["serial"])[4:] + "/data"
					with open(filename) as f:
						line.update(json.load(f))
						f.close()
				except:
					logging.debug("Cannot open archive: %s",sys.exc_value)
				# logging.debug(line)
				data['archs'].append(line)
				line=c.fetchone()
			tmpl = env.jinja.get_template("admin/arch.html")
			content = tmpl.render( data )
	return content
