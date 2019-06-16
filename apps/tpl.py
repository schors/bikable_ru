# -*- coding: utf-8 -*-
""" Приложение АДМИНКА/ШАБЛОНЫ """

import logging,re,sys,md5,time,random,json,os,fcntl
from core import mailtools

symb='QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm0123456789'
l=len(symb)

def dispatch( env ):
	""" Шаблоны """
	data = {
		"path" : env.path.current(),
		"session" : env.session.data,
		"templates" : [],
		"error" : {},
		"regions" : env.regions["regions"],
	}
	content=""
	if not env.path.current():
		if env.session.data['user']["priv"]==1:
			# если админ - сделать редирект на умолчание или ничего
			if env.regions["regions"].has_key("saint-petersburg"):
				env.redirect('/_adm/t/saint-petersburg/')
			else:
				tmpl = env.jinja.get_template("admin/tpl.html")
				content = tmpl.render( data )
		else:
			# если координатор - сделать редирект
			region_id=env.session.data['user']['region_id']
			env.redirect('/_adm/t/'+str(env.regions['id'][region_id]['fulluri'])+'/')
	else:
		env.region_current=env.path.current()
		env.path.next()
		# если координатор и не то - сделать редирект
		if env.session.data['user']["priv"]==0:
			region_id=env.session.data['user']['region_id']
			if env.region_current != env.regions['id'][region_id]['fulluri']:
				env.redirect('/_adm/t/'+str(env.regions['id'][region_id]['fulluri'])+'/')
				return ''
		data['cregion'] = env.region_current
		region_id = int(env.regions['regions'][env.region_current]['id'])
		# считать сортировку или создать её
		sortfilename=env.conf.base_path+env.conf.statements_storage+"/"+str(region_id)+"-sort"
		sort=[]
		if os.path.exists(sortfilename):
			with open(sortfilename,'r') as f:
				sort=json.load(f)
				f.close()
		# список шаблонов
		if not env.path.current():
			# проверить, не хотим ли завести новый шаблон
			if env.req.has_key("name"):
				name = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("name",None).decode('utf8').strip().replace(":","").replace('"',"&quot;"))
				if not name:
					data['error']['name']='empty'
				elif name.__len__()>200:
					data['error']['name']='invalid'
				funiq=env.req.getvalue("funiq",None)
				# завести новый шаблон
				if not data['error']:
					sql="""SELECT * from `templates` WHERE `region_id`=%s AND `name` LIKE %s"""
					c=env.db.equery(sql,(region_id,name))
					# если такого нет - внести в базу
					if not c.fetchone():
						uniq=md5.md5(str(time.time())+str(random.random())).hexdigest()
						sql=u"""INSERT INTO `templates` (`name`,`uniq`,`who`,`funiq`,`region_id`) VALUES (%s,%s,%s,%s,%s)"""
						env.db.equery(sql,(name,uniq,"",funiq,region_id))
						sort.append(str(env.db.insert_id()))
						write_sort_file(env,sort)
			# поднять выше
			elif env.req.has_key("up"):
				tplid=env.req.getvalue("tplid",None)
				if tplid:
					i=sort.index(tplid)
					if i>0:
						tmp=sort[i]
						sort[i]=sort[i-1]
						sort[i-1]=tmp
						write_sort_file(env,sort)
			# опустить ниже
			elif env.req.has_key("down"):
				tplid=env.req.getvalue("tplid",None)
				if tplid:
					i=sort.index(tplid)
					if i<len(sort)-1:
						tmp=sort[i]
						sort[i]=sort[i+1]
						sort[i+1]=tmp
						write_sort_file(env,sort)
			# опубликовать
			elif env.req.has_key("pub"):
				tplid=env.req.getvalue("tplid",None)
				if tplid:
					sql="""UPDATE `templates` SET `pub`=1 WHERE `id`=%s"""
					env.db.equery(sql,(tplid))
			# спрятать
			elif env.req.has_key("hide"):
				tplid=env.req.getvalue("tplid",None)
				if tplid:
					sql="""UPDATE `templates` SET `pub`=0 WHERE `id`=%s"""
					env.db.equery(sql,(tplid))
			funiq=""
			for i in range(8):
				funiq+=symb[random.randint(1,l)-1]
			data["funiq"]=funiq
			# выдать список
			data['templates']=[]
			sql="""SELECT * FROM `templates` WHERE region_id=%s"""
			c=env.db.equery(sql,(region_id))
			line=c.fetchone()
			while (line):
				data['templates'].append(line)
				line=c.fetchone()
			if sort:
				data['templates'].sort(key=lambda x: sort.index(str(x['id'])))
			else:
				for line in data['templates']:
					sort.append(str(line['id']))
				write_sort_file(env,sort)
			tmpl = env.jinja.get_template("admin/tpl.html")
			content = tmpl.render( data )
		# показать выбранный шаблон
		else:
			tplid=env.path.current()
			data["template"]={}
			filename=env.conf.base_path+env.conf.statements_storage+"/"+str(region_id)+"/"+str(tplid)
			if not os.path.exists(env.conf.base_path+env.conf.statements_storage+"/"+str(region_id)):
				os.mkdir(env.conf.base_path+env.conf.statements_storage+"/"+str(region_id))
			# удалить шаблон
			if env.req.has_key("delete"):
				# убрать из сортировки
				try:
					sort.remove(tplid)
					write_sort_file(env,sort)
				except:
					pass
				# удалить файл
				if os.path.exists(filename):
					os.unlink(filename)
				# удалить запись в базе
				sql="""DELETE FROM `templates` WHERE `id`=%s"""
				env.db.equery(sql,(tplid))
				env.redirect('/_adm/t/'+str(env.region_current)+'/')
				return ''
			else:
				fauthority=env.req.getvalue("fauthority",None)
				fwhom=env.req.getvalue("fwhom",None)
				femail=env.req.getvalue("femail",None)
				text=env.req.getvalue("text",None)
				ttype=env.req.getvalue("type",None)
				fdel=env.req.getvalue("fdel",[])
				tdel=env.req.getvalue("tdel",[])
				if env.req.has_key("save") or env.req.has_key("addcopy") or env.req.has_key("addtext") or env.req.has_key("addutext") or env.req.has_key("addfile"):
					authority = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("authority",None).decode('utf8').strip().replace('"',"&quot;"))
					if not authority:
						data['error']['authority']='empty'
					elif authority.__len__()>200:
						data['error']['authority']='invalid'
					name = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("name",None).decode('utf8').strip().replace('"',"&quot;"))
					if not name:
						data['error']['name']='empty'
					elif name.__len__()>200:
						data['error']['name']='invalid'
					whom = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("whom",None).decode('utf8').strip().replace('"',"&quot;"))
					if not whom:
						data['error']['whom']='empty'
					elif whom.__len__()>200:
						data['error']['whom']='invalid'
					email = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("aemail",None).decode('utf8').strip().replace('"',"&quot;"))
					if not email:
						data['error']['aemail']='empty'
					elif not mailtools.is_email(email):
						data['error']['aemail']='invalid'
					title = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("title",None).decode('utf8').strip().replace('"',"&quot;"))
					if not title:
						data['error']['title']='empty'
					elif title.__len__()>200:
						data['error']['title']='invalid'
					if env.req.has_key("text"):
						if type(text) != list:
							text = [text]
						if type(ttype) != list:
							ttype = [ttype]
						if env.req.has_key("tdel"):
							if type(tdel) != list:
								tdel = [tdel]
						data["template"]["texts"]=[]
						for i in range(text.__len__()):
							if str(i) in tdel:
								continue
							data["template"]["texts"].append({"error":{}})
							text[i] = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",text[i].decode('utf8').strip())
							if not text[i]:
								data["template"]["texts"][i]['error']['text']='empty'
								data["error"]["text"]=1
							ttype[i]=int(ttype[i])
							if ttype[i] not in [0,1,2]:
								ttype[i]=0
					if env.req.has_key("fauthority"):
						if type(fauthority) != list:
							fauthority = [fauthority]
						if type(fwhom) != list:
							fwhom = [fwhom]
						if type(femail) != list:
							femail = [femail]
						data["template"]["foreigns"]=[]
						if env.req.has_key("fdel"):
							if type(fdel) != list:
								fdel = [fdel]
						for i in range(fauthority.__len__()):
							if str(i) in fdel:
								continue
							data["template"]["foreigns"].append({"error":{}})
							fauthority[i] = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",fauthority[i].decode('utf8').strip().replace('"',"&quot;"))
							if not fauthority[i]:
								data["template"]["foreigns"][i]['error']['authority']='empty'
								data["error"]["foreign"]=1
							elif fauthority[i].__len__()>200:
								data["template"]["foreigns"][i]['error']['authority']='invalid'
								data["error"]["foreign"]=1
							fwhom[i] = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",fwhom[i].decode('utf8').strip().replace('"',"&quot;"))
							if not fwhom[i]:
								data["template"]["foreigns"][i]['error']['whom']='empty'
								data["error"]["foreign"]=1
							elif fwhom[i].__len__()>200:
								data["template"]["foreigns"][i]['error']['whom']='invalid'
								data["error"]["foreign"]=1
							femail[i] = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",femail[i].decode('utf8').strip().replace('"',"&quot;"))
							if not femail[i]:
								data["template"]["foreigns"][i]['error']['email']='empty'
								data["error"]["foreign"]=1
							elif not mailtools.is_email(femail[i]):
								data["template"]["foreigns"][i]['error']['email']='invalid'
								data["error"]["foreign"]=1
					data["template"].update({"authority":authority,"whom":whom,"aemail":email,"title":title,"name":name})
					if data["template"].has_key("texts"):
						j=0
						for i in range(text.__len__()):
							if str(i) in tdel:
								continue
							data["template"]["texts"][j]["text"]=text[i]
							data["template"]["texts"][j]["type"]=ttype[i]
							j+=1
					if data["template"].has_key("foreigns"):
						j=0
						for i in range(fauthority.__len__()):
							if str(i) in fdel:
								continue
							data["template"]["foreigns"][j]["authority"]=fauthority[i]
							data["template"]["foreigns"][j]["whom"]=fwhom[i]
							data["template"]["foreigns"][j]["email"]=femail[i]
							j+=1
					if not data["error"]:
						fp = open( filename, 'w')
						json.dump(data["template"],fp)
						fp.close()
						sql="""UPDATE `templates` SET `name`=%s WHERE `id`=%s"""
						env.db.equery(sql,(data["template"]["name"],tplid))
						if env.req.has_key("addcopy"):
							foreign={"authority":"","whom":"","email":"","title":"","error":{}}
							if data["template"].has_key("foreigns"):
								data["template"]["foreigns"].append(foreign)
							else:
								data["template"]["foreigns"]=[foreign]
						if env.req.has_key("addtext"):
							txt={"text":"","type":0,"error":{}}
							if data["template"].has_key("texts"):
								data["template"]["texts"].append(txt)
							else:
								data["template"]["texts"]=[txt]
						if env.req.has_key("addutext"):
							txt={"text":"","type":1,"error":{}}
							if data["template"].has_key("texts"):
								data["template"]["texts"].append(txt)
							else:
								data["template"]["texts"]=[txt]
						if env.req.has_key("addfile"):
							txt={"text":"","type":2,"error":{}}
							if data["template"].has_key("texts"):
								data["template"]["texts"].append(txt)
							else:
								data["template"]["texts"]=[txt]
				else:
					if os.path.exists(filename):
						fp = open( filename, 'r')
						template=json.load(fp)
						fp.close()
						data["template"].update(template)
			sql="""SELECT * FROM `templates` WHERE id=%s AND region_id=%s"""
			c=env.db.equery(sql,(tplid,region_id))
			template=c.fetchone()
			if template:
				data["template"].update(template)
				tmpl = env.jinja.get_template("admin/edit_tpl.html")
				content = tmpl.render( data )
			else:
				env.redirect('/_adm/t/'+str(env.region_current)+'/')
				return ''
	return content


# записать файл с сортировкой
def write_sort_file(env,sort):
	region_id=env.regions["regions"][env.region_current]['id']
	filename=env.conf.base_path+env.conf.statements_storage+"/"+str(region_id)+"-sort"
	with open(filename,'w') as f:
		fcntl.flock(f.fileno(), fcntl.LOCK_EX)
		json.dump(sort,f)
		fcntl.flock(f.fileno(), fcntl.LOCK_UN)
		f.close()

