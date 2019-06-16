# -*- coding: utf-8 -*-
""" Приложение составления письма """

import logging,os,sys,re,json,md5,time,random,datetime,fcntl,tempfile,pickle
from core import mailtools
from PIL import Image

BLOCK_SIZE=1024

# загрузить конфиг региона
def getrconf(env):
	rconf={
		"name":"",
		"name1":"",
		"text1":"",
		"text21":"",
		"text22":"",
		"text3":"",
		"contact":"",
		"email":"",
		"footer":"",
	}
	rconffile=env.conf.base_path+env.conf.region_conf+"/"+env.region_current+".conf"
	if os.path.exists(rconffile):
		with open(rconffile) as f:
			rconf=pickle.load(f)
			f.close()
	return rconf

def dispatch( env ):
	content=''
	data= {
		"template":{},
		"error":{},
		"regions":env.regions["regions"],
	}
	# принять код проверки
	if env.path.current()=='accept':
		code = env.path.next()
		dirname=env.conf.base_path+env.conf.reqs_storage+"/"+code
		filename=dirname+"/data"
		if os.path.exists(dirname) and os.path.exists(filename):
			fp = open( filename, 'r')
			template=json.load(fp)
			fp.close()
			data.update(template)
			try:
				env.region_current=env.regions["id"][data["template"]["region_id"]]["fulluri"]
			except:
				env.region_current=str("saint-petersburg")
		else:
			data["error"]["code"]='unknown'
			env.region_current=str("saint-petersburg")
		# загрузить конфиг региона
		data["rconf"] = getrconf(env)
		data["cregion"] = env.region_current
		# обработать при наличии кода
		if not data["error"]:
			data["code"]=code
			data["files"]=[]
			if os.path.exists(dirname+"/tumb"):
				files0=os.listdir(dirname+"/tumb")
				for f in files0:
					data["files"].append(f)
			if env.req.has_key("delete"):
				if os.path.exists(dirname):
					files=os.listdir(dirname)
					for f in files:
						if f=="tumb":
							ifiles=os.listdir(dirname+"/tumb")
							for img in ifiles:
								os.unlink( dirname+"/tumb/"+img)
							os.rmdir( dirname +"/"+f)
						else:
							os.unlink( dirname+"/"+f )
					os.rmdir( dirname )
				if data["template"].has_key("id"):
					env.redirect("/app/%s" % (data["template"]["id"]))
				else:
					env.redirect("/%s/",env.region_current)
				return "";
			# отправить сообщение в органы
			elif env.req.has_key("send"):
				files=[]
				if os.path.exists(dirname):
					files0=os.listdir(dirname)
					for f in files0:
						if f=="data":
							os.unlink( dirname+"/"+f )
						elif f=="tumb":
							pass
						else:
							files.append(dirname+"/"+f)
				to=[data["template"]["whom"]+"<"+data["template"]["aemail"]+">"]
				if data["template"].has_key("foreigns"):
					for foreign in data["template"]["foreigns"]:
						to.append(foreign["whom"]+"<"+foreign["email"]+">")
				if env.conf.debug==1:
						to=[u'Филипп Кулин <schors@gmail.com>',u'Дарья Табачникова <daria.tabachnikova@gmail.com>']
				subject,mailtext=mailtools.loadMail(env,"mail/final.tpl",{"title":data["template"]["title"],"name":data["template"]["name"],"fname":data["template"]["fname"],"lname":data["template"]["lname"],"email":data["template"]["email"],"whom":data["template"]["whom"],"text":data["mailtext"],"rname":data["rconf"]["name"],"fulluri":env.region_current})
				mailtools.sendMail(env,data["template"]["fname"]+u" "+data["template"]["lname"]+u" <"+data["template"]["email"]+u">",to,subject,mailtext,files)
				sql="""INSERT INTO `archive` (serial,email,region_id,template_id,createdate) VALUES (%s,%s,%s,%s,NOW())"""
				env.db.equery(sql,(data["template"]["sernum"],data["template"]["email"],env.regions["regions"][env.region_current]["id"],data["template"]["id"]))
				sql="""UPDATE `templates` SET cnt=cnt+1 WHERE id=%s"""
				env.db.equery(sql,(data["template"]["id"]))
				dirname0=env.conf.base_path+env.conf.archive_storage+"/"+data["template"]["sernum"][0:2]
				if not os.path.exists(dirname0):
					os.mkdir(dirname0)
				dirname1=dirname0+'/'+data["template"]["sernum"][2:4]
				if not os.path.exists(dirname1):
					os.mkdir(dirname1)
				dirname2=dirname1+'/'+data["template"]["sernum"][4:]
				if not os.path.exists(dirname2):
					os.mkdir(dirname2)
				dirname3=dirname2+"/tumb"
				if not os.path.exists(dirname3):
					os.mkdir(dirname3)
				filename=dirname2+"/data"
				fp=open( filename, 'w')
				json.dump(template,fp)
				fp.close()
				# удалить запрос на запрос
				if os.path.exists(dirname):
					files0=os.listdir(dirname)
					for f in files0:
						# перекинуть вложения
						if f!="data":
							os.rename(dirname+"/"+f, dirname2+"/"+f)
						if os.path.exists(dirname+"/"+f) and os.path.isfile(dirname+"/"+f):
							os.unlink( dirname+"/"+f )
						elif os.path.exists(dirname+"/"+f) and os.path.isdir(dirname+"/"+f):
							os.rmdir( dirname+"/"+f )
					os.rmdir( dirname )
				# увеличить общий счётчик
				sql="""SELECT COUNT(*) as `cnt` FROM `archive`"""
				c=env.db.equery(sql)
				cnt=c.fetchone()
				fcnt=env.conf.base_path+env.conf.archive_storage+"/counter"
				fp=open(fcnt,"w")
				fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
				fp.write(str(cnt['cnt']))
				fp.close()
				# увеличить региональный счётчик
				sql="""SELECT COUNT(*) as `cnt` FROM `archive` WHERE region_id=%s"""
				c=env.db.equery(sql,(env.regions["regions"][env.region_current]["id"]))
				cnt=c.fetchone()
				fcnt=env.conf.base_path+env.conf.archive_storage+"/"+env.region_current+"_counter"
				fp=open(fcnt,"w")
				fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
				fp.write(str(cnt['cnt']))
				fp.close()
				# завершить
				tmpl = env.jinja.get_template("customers/final.html")
				return tmpl.render( data )
		tmpl = env.jinja.get_template("customers/code.html")
		return tmpl.render( data )
	# если не код, то номер шаблона
	tplid=env.path.current()
	# заполнить данные из шаблона, если он вообще есть
	if tplid:
		sql="""SELECT * FROM `templates` WHERE id=%s"""
		c=env.db.equery(sql,(tplid))
		template=c.fetchone()
		if template:
			del template["updatetime"]
			data["template"].update(template)
			filename=env.conf.base_path+env.conf.statements_storage+"/"+str(data["template"]["region_id"])+"/"+str(tplid)
			if os.path.exists(filename):
				fp = open( filename, 'r')
				template=json.load(fp)
				fp.close()
				data["template"].update(template)
		# загрузить конфиг региона
		try:
			env.region_current=env.regions["id"][data["template"]["region_id"]]["fulluri"]
		except:
			env.redirect("/saint-petersburg/")
			return ''
	try:
		data["cregion"]=env.region_current
	except:
		env.region_current="/saint-petersburg/"
	data["rconf"] = getrconf(env)
	data["cregion"] = env.region_current
	# если шаблон таки есть
	if data["template"].has_key("id"):
		# убрать <br> из названия шаблона
		if data["template"].has_key("name"):
			data["template"]["namez"]=re.compile(r'<br>',re.S|re.U).sub(' ',data["template"]["name"])
		# обходим вариант не заданного типа
		if not data["template"].has_key("title"):
			data["template"]["title"]=" "
		if env.req.has_key("cancel"):
			env.redirect("/"+str(env.region_current)+"/")
			return "";
		elif env.req.has_key("send"):
			fname = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("fname",None).decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not fname:
				data['error']['fname']='empty'
			elif fname.__len__()>200:
				data['error']['fname']='invalid'
			lname = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("lname",None).decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not lname:
				data['error']['lname']='empty'
			elif lname.__len__()>200:
				data['error']['lname']='invalid'
			patr = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("patr",None).decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not patr:
				data['error']['patr']='empty'
			elif patr.__len__()>200:
				data['error']['patr']='invalid'
			email = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("email",None).decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not email:
				data['error']['email']='empty'
			elif not mailtools.is_email(email):
				data['error']['email']='invalid'
			secure=env.req.getvalue("secure","0")
			if secure not in ("0","1"):
				secure="0"
			site=env.environ.get("SERVER_NAME")
			if secure=="1":
				expires = datetime.datetime.utcnow() + datetime.timedelta(days=365)
				expires = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
				env.cookie_out["fname"]=fname.encode('utf8')
				env.cookie_out["fname"]["path"]="/"
				env.cookie_out["fname"]["domain"]=site
				env.cookie_out["fname"]["expires"]=expires
				env.cookie_out["lname"]=lname.encode('utf8')
				env.cookie_out["lname"]["path"]="/"
				env.cookie_out["lname"]["domain"]=site
				env.cookie_out["lname"]["expires"]=expires
				env.cookie_out["patr"]=patr.encode('utf8')
				env.cookie_out["patr"]["path"]="/"
				env.cookie_out["patr"]["domain"]=site
				env.cookie_out["patr"]["expires"]=expires
				env.cookie_out["email"]=email.encode('utf8')
				env.cookie_out["email"]["path"]="/"
				env.cookie_out["email"]["domain"]=site
				env.cookie_out["email"]["expires"]=expires
			else:
				env.cookie_out["fname"]=""
				env.cookie_out["fname"]["path"]="/"
				env.cookie_out["fname"]["domain"]=site
				env.cookie_out["fname"]["expires"]="-3y"
				env.cookie_out["lname"]=""
				env.cookie_out["lname"]["path"]="/"
				env.cookie_out["lname"]["domain"]=site
				env.cookie_out["lname"]["expires"]="-3y"
				env.cookie_out["patr"]=""
				env.cookie_out["patr"]["path"]="/"
				env.cookie_out["patr"]["domain"]=site
				env.cookie_out["patr"]["expires"]="-3y"
				env.cookie_out["email"]=""
				env.cookie_out["email"]["path"]="/"
				env.cookie_out["email"]["domain"]=site
				env.cookie_out["email"]["expires"]="-3y"
			data["template"].update({"fname":fname,"lname":lname,"patr":patr,"email":email,"secure":secure})
			if data["template"].has_key("texts"):
				text=env.req.getvalue("text","")
				if type(text) != list:
					text = [text]
				for i in range(text.__len__()):
					text[i]=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",text[i].decode('utf8').strip())
				files=[]
				if env.req.has_key("files"):
					files=env.req["files"]
				if type(files) != list:
					files = [files]
				j=0
				for i in range(data["template"]["texts"].__len__()):
					if data["template"]["texts"][i]["type"]==1:
						data["template"]["texts"][i]["itext"]=text[j]
						if not text[j]:
							data['error']['text']=1
							data["template"]["texts"][i]["error"]='empty'
						elif text[j].__len__()>10240:
							data['error']['text']=1
							data["template"]["texts"][i]["error"]='invalid'
						j += 1
					if data["template"]["texts"][i]["type"]==2:
						if files:
							uploadfile=files.pop(0)
							if uploadfile.filename.decode("utf8")=='':
								continue
							tf=tempfile.TemporaryFile(dir=env.conf.base_path+env.conf.tmp_path)
							buf=uploadfile.file.read(BLOCK_SIZE)
							while buf:
								tf.write(buf)
								buf=uploadfile.file.read(BLOCK_SIZE)
							ext=uploadfile.filename.decode("utf8").lower().split('.').pop();
							if ext not in env.conf.image_ext:
								data["template"]["texts"][i]["error"]='invalid'
								data['error']['text']=1
								tf.close()
								logging.debug("Bad image %s",ext)
							else:
								data["template"]["texts"][i]["tf"]=tf
								data["template"]["texts"][i]["filename"]="image-"+str(i)+"."+ext
								logging.debug("file %s",data["template"]["texts"][i]["filename"])
			if not data['error']:
				createdate=datetime.date.today().isoformat()
				fserial=env.conf.base_path+env.conf.serial_storage+"/"+createdate[2:4]+createdate[5:7]
				fsn=None
				sernum="0"
				if os.path.exists(fserial):
					fsn=open(fserial,"r+")
					fcntl.flock(fsn.fileno(), fcntl.LOCK_EX)
					sernum=fsn.readline()
					fsn.seek(0)
					fsn.truncate()
				else:
					fsn=open(fserial,"w")
					fcntl.flock(fsn.fileno(), fcntl.LOCK_EX)
				sernum=str(int(sernum)+1)
				fsn.write(sernum)
				fsn.close()
				data["template"]["sernum"]=createdate[2:4]+createdate[5:7]+sernum
				data["template"]["createdate"]=createdate
				tmpl = env.jinja.get_template("customers/mail.txt")
				restext = tmpl.render( data )
				code=md5.md5(str(time.time())+str(random.random())).hexdigest()
				dirname=env.conf.base_path+env.conf.reqs_storage+"/"+str(code)
				os.mkdir(dirname)
				# так, файлики разложить
				files1=[]
				if data["template"].has_key("texts"):
					for i in range(data["template"]["texts"].__len__()):
						if data["template"]["texts"][i]["type"]==2:
							if data["template"]["texts"][i].has_key("tf"):
								tf=data["template"]["texts"][i]["tf"]
								tf.seek(0)
								f=open(dirname+"/"+data["template"]["texts"][i]["filename"],"w")
								buf=tf.read(BLOCK_SIZE)
								while buf:
									f.write(buf)
									buf=tf.read(BLOCK_SIZE)
								tf.close()
								f.close()
								del data["template"]["texts"][i]["tf"]
								files1.append(dirname+"/"+data["template"]["texts"][i]["filename"])
								# сделать превьюшку
								try:
									with open(dirname+"/"+data["template"]["texts"][i]["filename"],"r") as f0:
										image = imageResize(f0, env.conf.tumb_size)
										if not os.path.exists(dirname+"/tumb"):
											os.mkdir(dirname+"/tumb")
										with open(dirname+"/tumb/"+data["template"]["texts"][i]["filename"],"w") as f:
											image.save(f, 'JPEG', quality=85)
											f.close()
										f0.close()
								except:
									logging.debug("Preview error: %s",sys.exc_value)
				filename=dirname+"/data"
				fp = open( filename, 'w')
				json.dump({"template":data["template"],"mailtext":restext},fp)
				fp.close()
				# надо чистилку наверное тут сделать
				subject,mailtext=mailtools.loadMail(env,"mail/customer.tpl",{"title":data["template"]["title"],\
				"name":data["template"]["namez"],"fname":fname,"lname":lname,"code":code,"email":email,\
				"site":env.environ.get("SERVER_NAME"),"text":restext,"fulluri":env.region_current,"rname":data["rconf"]["name"],})
				mailtools.sendMail(env,data["rconf"]["name"]+env.conf.email,[fname+u" "+lname+u" <"+email+u">"],subject,mailtext,files1)
				tmpl = env.jinja.get_template("customers/sent.html")
				return tmpl.render( data )
		else:
			if env.cookie_in.has_key("fname") and env.cookie_in["fname"].value:
				data["template"]["fname"]=env.cookie_in["fname"].value.decode('utf8')
				data["template"]["secure"]="1"
			if env.cookie_in.has_key("lname") and env.cookie_in["lname"].value:
				data["template"]["lname"]=env.cookie_in["lname"].value.decode('utf8')
				data["template"]["secure"]="1"
			if env.cookie_in.has_key("patr") and env.cookie_in["patr"].value:
				data["template"]["patr"]=env.cookie_in["patr"].value.decode('utf8')
				data["template"]["secure"]="1"
			if env.cookie_in.has_key("email") and env.cookie_in["email"].value:
				data["template"]["email"]=env.cookie_in["email"].value.decode('utf8')
				data["template"]["secure"]="1"
		tmpl = env.jinja.get_template("customers/form.html")
		content = tmpl.render( data )
	else:
		# и таки если нету (или глагне)
		data["templates"]=[]
		sql="""SELECT * FROM `templates` WHERE pub=%s AND region_id=%s"""
		c=env.db.equery(sql,(1,env.regions["regions"][env.region_current]["id"]))
		line=c.fetchone()
		while (line):
			data['templates'].append(line)
			line=c.fetchone()
		# считать сортировку
		sortfilename=env.conf.base_path+env.conf.statements_storage+"/"+str(env.regions["regions"][env.region_current]['id'])+"-sort"
		sort=[]
		if os.path.exists(sortfilename):
			with open(sortfilename,'r') as f:
				sort=json.load(f)
				f.close()
			# отсортировать
			if sort:
				data['templates'].sort(key=lambda x: sort.index(str(x['id'])))
		# считать общий счётчик
		fcnt=env.conf.base_path+env.conf.archive_storage+"/counter"
		try:
			with open(fcnt,"r") as fp:
				data['counter']=fp.readline()
				fp.close()
		except:
			data['counter']='0'
		# считать региональный счётчик
		fcnt=env.conf.base_path+env.conf.archive_storage+"/"+env.region_current+"_counter"
		try:
			with open(fcnt,"r") as fp:
				data['rcounter']=fp.readline()
				fp.close()
		except:
			data['rcounter']='0'
		# файл с сортировкой регионов
		sortfilename=env.conf.base_path+env.conf.region_conf+"/.region_sort"
		sort=[]
		if os.path.exists(sortfilename):
			with open(sortfilename,'r') as f:
				sort=json.load(f)
				f.close()
		# сортировка регионов
		data['aregions']=[]
		for i in sort:
			data['aregions'].append(env.regions['id'][i])
		tmpl = env.jinja.get_template("customers/index.html")
		content = tmpl.render( data )
	return content

def imageResize(data, output_size):
	"""
	  Resize image for thumbnails and preview
	  data — image for resize
	  output_size — turple, contains width and height of output image, for example (200, 500)
	"""
	image = Image.open(data)
	m_width = float(output_size[0])
	m_height = float(output_size[1])
	if image.mode not in ('L', 'RGB'):
		image = image.convert('RGB')
	w_k = image.size[0]/m_width
	h_k = image.size[1]/m_height
	if output_size < image.size:
		if w_k > h_k:
			new_size = (int(m_width), int(image.size[1]/w_k))
		else:
			new_size = (int(image.size[0]/h_k), int(m_height))
	else:
		new_size = image.size
	return image.resize(new_size,Image.ANTIALIAS)
